# EXIOM AI — Hosting on Cloudflare Workers (Handoff)

Findings from testing this app on Cloudflare Python Workers,
28 September 2026, and what it takes to ship it there. The
client strongly prefers Workers; the budget is about $5/month
for 50–200 users at once.

**Verdict: Workers can host this app, on the Workers Paid
plan ($5/month). The free plan cannot run it.** The Flask app
runs with small changes. The real work is moving the in-memory
usage limits into a Durable Object and the background refresh
into a Cron Trigger (about 1–2 days).


## 1. What was tested

A copy of the app (every non-test `.py`, `knowledge/`,
`templates/`, `static/`, `wordlists/`, `xeqm_knowledge.txt`)
ran as a Python Worker, both locally (`pywrangler dev`) and
deployed as `xeqm-hub-test` on the free account
`workwithismaeel` (`https://xeqm-hub-test.workwithismaeel.workers.dev`).
The repo itself was not changed. The prototype's files are in
§8.

| Check | Result |
| --- | --- |
| Flask on Workers (WSGI adapter, added 2 Sep 2026) | ✅ runs |
| Blocking `requests` / `openai` calls | ✅ work: the adapter runs the app under JSPI (`run_sync`), so no async rewrite is needed |
| Streamed answers (`/ask/stream`) | ✅ streamed piece by piece, not buffered (a long answer arrived gradually over about 7s) |
| Live Explorer data (`/api/network-stats`) | ✅ works once threads run inline (§4) |
| `sqlite3` | ✅ imports and writes, but the disk is temporary (§4) |
| Bundle size | ✅ 20.0 MB, 4.1 MB gzipped. The limit is 64 MiB on both plans |
| Startup snapshot | ✅ accepted ("Worker Startup Time: 3316 ms") |
| 128 MB memory per copy | ✅ a cold copy loaded everything and served `/` |
| Threads | ❌ `RuntimeError: can't start new thread` |
| **Free plan (10 ms CPU per request)** | ❌ **every request fails** ("Worker exceeded CPU time limit", errors 1102/1101/503) |

Speed, measured locally: first word 8.2s on Workers against
5.2s on gunicorn for the same question; page loads about 14ms
once a copy is warm. Live timings on Paid are still unmeasured
(§7).


## 2. Why the free plan cannot work

Live log for a cold copy (`wrangler tail`):

```
ok        cpu 1793 ms  GET /           ← first request tolerated
exception cpu 2014 ms  GET /           ← CpuLimitExceeded while importing openai
exceededCpu            GET /
```

* **Importing the `openai` SDK costs about 2s of CPU** on every
  new copy: it builds hundreds of pydantic models at import.
* It **cannot go into the startup snapshot**. `openai/lib/bedrock.py`
  calls `os.urandom(32)` at import, and Workers forbid randomness
  during startup ("Randomness is not allowed while a Worker is
  starting"). Its dependencies can be snapshotted (§8), so only
  the SDK itself loads during a request.
* Even with a warm copy, a streamed answer uses 50–1000+ ms of
  CPU (§3), about 100× the free limit.

Workers Paid allows **30s of CPU per request by default** (up
to 5 minutes via `limits.cpu_ms`), which covers both.


## 3. CPU per request (measured natively, gunicorn app, Python 3.13)

| Request | CPU |
| --- | --- |
| `import app` (cold) | 1,044 ms |
| `GET /`, static file (warm) | about 1 ms |
| `/api/network-stats` (Explorer fetch / cached) | 129 ms / 0.6 ms |
| Fast-path answer (e.g. block height) | 3 ms |
| First streamed answer in a process | 700–770 ms |
| Warm streamed answer, short (35–90 pieces) | 47–200 ms |
| Warm streamed answer, long (385 / 1,008 pieces) | 389 / 1,037 ms |

**Warm CPU grows by about 1 ms per streamed piece, and the
OpenAI SDK causes it, not the app.** Profiling a warm 812-piece
answer (2.2s under the profiler): 1.25s in
`openai/_models.py:construct_type`, 0.24s in pydantic
`validate_python`, and roughly 0.4s more in typing helpers
called from them. The SDK turns every stream event into a typed
model (`ai_provider.py:859-867`, `responses.stream(...)`). The
first answer in a process also pays for building those models
lazily (`model_rebuild`).

Python on Workers (Pyodide/WebAssembly) is slower than native;
estimate 2–3× these numbers until measured on Paid.

### Recommended: parse the OpenAI stream without the SDK

Calling the Responses API with `requests` (`stream=True`),
parsing each SSE `data:` line with `json.loads`, and reading
`type` / `delta` directly would:

* cut per-piece CPU from about 1 ms to tens of microseconds
  (long answers go from about 1s to well under 100 ms natively),
* remove the 2s `openai` import from every Workers cold start,
* help Railway just as much (§6).

`reliability.py`'s retry policy already works from status codes
and headers, so it carries over; the SDK exception classes
imported by `app.py` (`RateLimitError`, `APITimeoutError`,
`APIConnectionError`, `APIError`) would be replaced by the
module's own. This is optional for Workers Paid, but it is the
biggest cost and speed win available.


## 4. Changes needed for Workers

### 4.1 Entry point and config (new files)

`src/worker.py` and `wrangler.jsonc` as in §8, plus a
`pyproject.toml` for `pywrangler`. **Pin the versions from
`requirements.txt`**: the unpinned test resolved `openai` 3.19.2,
not the tested 3.16.2 (Task 12 rule). Vendored names differ
from PyPI (`httpx` is bundled as `httpx2`).

`app.py` must be imported **inside the first request**, not at
the top level: it builds the OpenAI client (`AIProvider`,
`app.py:357`) and reads every limit from `os.environ` at
import, and secrets only arrive with a request (`self.env`).
The prototype copies `OPENAI_API_KEY` and `EXIOM_*` from
`self.env` into `os.environ`, then imports.

### 4.2 Threads → Cron Trigger (`live_data.py`)

Workers cannot start threads. Three places use them:

* `live_data.py:1051`: `ThreadPoolExecutor` fetches the
  Explorer feeds and pages in parallel.
* `live_data.py:1160`: background page refresh.
* `live_data.py:1360`: refresh-ahead of the 30s reading.

The prototype runs them inline, which works but made a cold
`/api/network-stats` take 23s. For production, a **Cron
Trigger** (every minute, the shortest interval) fetches the
Explorer and stores the reading in the Durable Object or KV,
and the request path only reads that copy. Crons allow 30s of
CPU and 15 minutes of wall time, and fetching one source at a
time is fine there. The locks in `cache.py`, `security.py` and
`usage_control.py` are harmless no-ops (one thread per copy)
and can stay.

### 4.3 Usage limits and ledger → one Durable Object

Cloudflare runs as many copies (isolates) as traffic needs and
recycles them freely. Everything Task 10–12 keeps in process
memory is therefore per copy, so the **limits multiply with the
number of copies and reset whenever one is recycled**:

* `UsageController` (per-client minute/day counts, token and
  web-search ceilings, `usage_control.py:368-634`)
* `FloodGuard` and `AnswerSlots` (`security.py`, `app.py:135-145`)
* `CostMeter` totals, and the `UsageLedger` SQLite file
  (`usage_ledger.py`). `/tmp` is temporary on Workers.

Move them into **one Durable Object with SQLite storage**. One
object means one global counter, which gives exact limits,
the same guarantee the single gunicorn process gives today. Per
question: one `check` call before answering, then
`record_tokens` / `claim_web_search` after (about 3 DO requests).
The `/usage` page (Task 15) reads the ledger from the same
object.

The response caches (`TTLCache` in `app.py:367-376`,
`explorer_lookup` cache) can stay per copy (a miss only costs
an OpenAI call) or move to the Workers Cache API later.

### 4.4 Client IP

The WSGI adapter sets no `REMOTE_ADDR`, so every visitor would
share the key `"unknown"` and one allowance. The prototype sets
`REMOTE_ADDR` from `CF-Connecting-IP` (set by Cloudflare, a
client cannot forge it) and `EXIOM_TRUSTED_PROXY_HOPS=0`.
`security.client_key` then keys IPv6 by /64 as before.

### 4.5 gunicorn

**None needed.** gunicorn does not run on Workers:
`gunicorn.conf.py`, `WEB_CONCURRENCY` and `GUNICORN_THREADS`
don't apply, and Cloudflare handles concurrency by starting more
copies. Keep `gunicorn.conf.py` for local runs and the Railway
fallback (§6). The `max_requests = 0` rule (Task 10) has its
Workers counterpart in §4.3: copies are recycled by Cloudflare,
which is why the counters must leave process memory.

### 4.6 Front end and static files

`templates/` and `static/` are served by Flask from the bundle
today (this works). Optionally move `static/` to Workers Static
Assets (free, no Python CPU spent) with `run_worker_first` for
the API routes.


## 5. Pricing (checked 28 Sep 2026, developers.cloudflare.com)

| Item | Workers Paid ($5/month per account) |
| --- | --- |
| Requests | 10M/month included, then $0.30/M |
| CPU time | 30M CPU-ms/month included, then $0.02 per M CPU-ms |
| CPU per request | 30s default, up to 5 min (`limits.cpu_ms`) |
| Waiting on `fetch` (OpenAI, Explorer) | **not counted** as CPU |
| Durable Objects | 1M requests/month and 400,000 GB-s included; SQLite: 25B rows read, 50M rows written, 5 GB included |
| Cron Triggers | included |
| Spending cap | **none**, so the app's own limits are the only spend guard |
| Domain, HTTPS, DDoS | Cloudflare free plan |

**Estimate for this app:** at a pessimistic 1s of Workers CPU
per question (the 2–3× native estimate), 30M CPU-ms covers
about 30,000 questions a month; each further 1,000 questions
costs about $0.02. Cold starts add about 2s of CPU each (a few
cents per thousand). DO requests: about 3 per question, so 1M
covers about 330,000 questions. **Expected bill: $5/month plus
cents.** OpenAI is billed separately, as today.

200 simultaneous streams are no problem on Workers: each
request has its own CPU budget and Cloudflare adds copies
as needed. The limits that matter are **OpenAI's rate limits
for the client's tier** and the 6 simultaneous outgoing
connections per request (the app uses 1–2).


## 6. Railway fallback, corrected

Earlier advice said one gunicorn process with
`GUNICORN_THREADS=200` could serve 200 streams at once. **The
§3 numbers don't support that.** A stream spends about 1 ms of
CPU per piece, and Python runs one thread at a time per process
(the GIL), so a single process delivers roughly 1,000 pieces/s
across all streams. At 200 simultaneous streams that is about 5
pieces/s each: answers keep arriving, but visibly slower.
`WEB_CONCURRENCY=1` is still required for exact limits
(Task 10). The SDK-free stream parsing in §3 removes this
bottleneck, and is the fix to make if the client ends up on
Railway.


## 7. What is not verified yet

* **CPU and speed on Workers Paid.** On the free plan, requests
  are killed before `wrangler tail` can report warm CPU. After
  upgrading, run `npx wrangler tail --format json` in the
  prototype folder while asking questions; each event carries
  `cpuTime` / `wallTime`.
* Memory under many simultaneous streams in one copy (128 MB limit).
* The startup snapshot: it was accepted at 3.3s. Adding more
  imports risks deploy error 10021 ("Script startup exceeded
  CPU time limit").
* Whose account it deploys to. The test ran on the developer's
  free account. Production should be the client's account on
  Workers Paid, with the GitHub repo connected once the Workers
  changes are on `main`.

Next step: upgrade an account to Workers Paid (the client's
account preferably), redeploy the prototype, and measure §7
before starting §4.2–4.3.


## 8. Prototype files

`wrangler.jsonc`:

```jsonc
{
  "name": "xeqm-hub-test",
  "main": "src/worker.py",
  "compatibility_date": "2026-09-28",
  "compatibility_flags": ["python_workers"],
  "vars": { "EXIOM_USAGE_DB": "/tmp/usage.sqlite3" },
  "observability": { "enabled": true }
}
```

`pyproject.toml` (pin these for production):

```toml
[project]
name = "xeqm-worker"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["flask", "openai", "requests", "python-dotenv"]

[dependency-groups]
dev = ["workers-py", "workers-runtime-sdk"]
```

`src/worker.py` (the test version; §4.2 and §4.3 replace the
thread shim):

```python
import concurrent.futures
import os
import threading

# Snapshotted at deploy. openai itself cannot be (os.urandom
# at import), its heavy dependencies can.
import anyio  # noqa: F401
import flask  # noqa: F401
import httpx2  # noqa: F401
import pydantic  # noqa: F401
import requests  # noqa: F401
import werkzeug  # noqa: F401

from workers import WorkerEntrypoint, wsgi


class _InlineExecutor(concurrent.futures.Executor):
    def __init__(self, *args, **kwargs):
        pass

    def submit(self, fn, /, *args, **kwargs):
        future = concurrent.futures.Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as error:
            future.set_exception(error)
        return future


def _inline_start(self):
    self.run()


concurrent.futures.ThreadPoolExecutor = _InlineExecutor
threading.Thread.start = _inline_start

_ENV_NAMES = ("OPENAI_API_KEY", "EXIOM_USAGE_TOKEN", "EXIOM_USAGE_DB")
_app = None


def _with_client_address(app):
    def wrapped(environ, start_response):
        environ["REMOTE_ADDR"] = environ.get("HTTP_CF_CONNECTING_IP", "")
        return app(environ, start_response)

    return wrapped


def _load_app(env):
    global _app
    if _app is None:
        for name in _ENV_NAMES:
            value = getattr(env, name, None)
            if value is not None and name not in os.environ:
                os.environ[name] = str(value)
        os.environ.setdefault("EXIOM_TRUSTED_PROXY_HOPS", "0")
        from app import app
        _app = _with_client_address(app)
    return _app


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await wsgi.fetch(_load_app(self.env), request, self.env)
```

Commands (needs Node and `uv`; log in once with `npx wrangler login`):

```
uv run pywrangler dev        # local, port 8787, secrets from .dev.vars
uv run pywrangler deploy
npx wrangler secret put OPENAI_API_KEY
npx wrangler tail --format json
npx wrangler delete          # remove the test Worker
```


## Sources

* [Python Workers: WSGI frameworks (changelog, 2 Sep 2026)](https://developers.cloudflare.com/changelog/post/2026-09-02-python-workers-web-framework-support/)
* [Python Workers GA (blog)](https://blog.cloudflare.com/python-workers-ga/)
* [Flask on Python Workers](https://developers.cloudflare.com/workers/languages/python/packages/flask/)
* [Python Workers standard library (threading)](https://developers.cloudflare.com/workers/languages/python/stdlib/)
* [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
* [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)
* [Python Workers cold starts and snapshots (blog)](https://blog.cloudflare.com/python-workers-advancements/)
