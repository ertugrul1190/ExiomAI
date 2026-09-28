# EXIOM AI — Cloudflare Workers Deployment

What was built and deployed on 28 September 2026 to host the
app on the client's Cloudflare account, following
`Handoff - Cloudflare Workers Hosting.md` (§4). The Flask app
itself is unchanged; gunicorn/Railway still work as before.

**Live:** `https://xeqm-hub.danylahori.workers.dev`
(Worker `xeqm-hub`, account "Danylahori@gmail.com's Account",
**Workers Paid**, confirmed because the deploy sets
`limits.cpu_ms`, which Cloudflare refuses on the free plan.)


## 1. How it fits together

```
visitor ──► Worker copy (any number, Cloudflare scales them)
              fetch: Flask app via the WSGI adapter
              │  every limit / counter call
              ▼
            UsageHubObject — ONE Durable Object, SQLite storage
              flood guard · answer slots · usage limits
              cost meter · daily ledger · latest Explorer reading
              ▲
Cron Trigger (every minute) ── reads the Explorer 3× (every 20s)
```

| Handoff item | Done as |
| --- | --- |
| §4.1 entry point, config, pinned versions | `cloudflare/worker.py`, `wrangler.jsonc`, `pyproject.toml` (same pins as `requirements.txt`: openai 3.16.2, Flask 3.1.3, requests 2.34.2, python-dotenv 1.2.3) |
| §4.2 threads → Cron Trigger | `scheduled()` reads the Explorer every 20s into the hub; requests read that copy (`remote_usage.share_live_readings`) |
| §4.3 limits + ledger → one Durable Object | `usage_hub.py` (runs the existing `UsageController`, `FloodGuard`, `AnswerSlots`, `CostMeter`, `UsageLedger` classes inside the object) + `remote_usage.py` (drop-in stand-ins app.py calls) |
| §4.4 client IP | `REMOTE_ADDR` = `CF-Connecting-IP`, `EXIOM_TRUSTED_PROXY_HOPS=0` |
| §4.5 gunicorn | not used on Workers; `gunicorn.conf.py` kept for local/Railway |
| §4.6 static files | still served by Flask from the bundle (see §3.1) |


## 2. Files

| File | Role |
| --- | --- |
| `usage_hub.py` | The hub: limits, ledger (DO SQL storage), Explorer reading. Plain Python, unit-tested |
| `remote_usage.py` | Stand-ins for app.py's `flood_guard`, `answer_slots`, `usage_controller`, `cost_meter`, `usage_ledger`; `install()` swaps them in after `import app` |
| `tests/test_usage_hub.py` | 12 tests: shared limits across copies, eviction, fail-safe behaviour, slot leases, readings |
| `usage_control.py` | Three public methods for the hub: `record_tokens(..., count_global=False)`, `record_global_tokens`, `restore_today` |
| `cloudflare/worker.py` | Entry point: `fetch`, `scheduled`, `UsageHubObject` |
| `cloudflare/wrangler.jsonc` | Worker config (DO binding + migration, cron, CPU limit, bundle rules) |
| `cloudflare/build.sh` | Copies only the app's modules and data into `cloudflare/src/` (never tests, `.env`, the local ledger) |
| `cloudflare/deploy.sh` | Build → dry run → **refuses to deploy if any built file is missing from the bundle** → deploy |


## 3. Problems found and fixed on the way

### 3.1 Knowledge base and static files were not uploaded

Python Workers bundle only `.py`, `.txt` and `.html` by default.
`knowledge/*.md` (the system instructions and the knowledge
base), `sources.json`, CSS, JS, PNG and fonts were silently
left out. `retrieval.load_markdown_file` returns `""` for a
missing file, so the app ran **without its instructions**,
with no error. (The Handoff prototype had the same gap; its
"serves `/`" check could not show it.) Fixed with `rules` in
`wrangler.jsonc` (Text for md/json/css/js, Data for png/woff2),
verified byte-for-byte, and guarded by `deploy.sh`.

### 3.2 Streamed answers ended in an error

The WSGI adapter pulls every chunk of a streamed body in a
new asyncio task, each with its own copy of the context
variables. Flask's request context, pushed in the first
chunk, was missing in the last one: `LookupError:
flask.app_ctx` after the `done` event. `worker._OneContextBody`
runs every step of one response in one context.

### 3.3 Requests interleave inside one copy

A copy runs many requests on one thread, switching at every
network wait (JSPI). Two consequences:

* `live_data._fetch_lock` is held across the Explorer fetch;
  a second request reaching it would block the copy forever.
  Replaced by `remote_usage.OpenLock` (the lock only saved a
  duplicate fetch).
* `AIProvider._thread_state` (`threading.local`) is one object
  on one thread, so request B could overwrite A's token usage
  before A charged it. Replaced by `remote_usage.TaskLocal`
  (per asyncio task, via `contextvars`). The hub also counts
  the **global** token total from the provider's own numbers
  (`record_usage`), so the spend ceiling stays exact even if a
  client is ever mis-attributed.


## 4. Safety rules

* **Workers has no spending cap**, so the app's limits are the
  spend guard, and they are now global (one Durable Object),
  exactly like the single gunicorn process.
* The ledger lives in the object's SQLite storage. After an
  eviction or a deploy, today's global token and web-search
  totals are read back from it, so the **daily ceilings survive
  restarts** (checked live: after a redeploy the global total
  equalled the ledger's). Until that read succeeds, paid work
  is refused. Per-client counters, the flood guard and slots
  restart (a fresh allowance, as `UsageController`'s own
  eviction does). Restored web searches are those performed,
  slightly fewer than those claimed.
* **Answer slots expire after 5 minutes.** On gunicorn, WSGI's
  `close()` always released them; on Workers a copy can be
  killed mid-stream, and a lost release would otherwise lock a
  client out until the next deploy.
* If the hub cannot be reached: **paid work is refused**
  ("daily capacity" message), web searches are not claimed;
  the page, Explorer stats and bookkeeping carry on.
* A failed Explorer read never replaces a good reading still
  inside its 30s window; no reading older than its window is
  ever served (a copy fetches the Explorer itself if the cron
  reading is stale).
* Secrets (`OPENAI_API_KEY`, `EXIOM_USAGE_TOKEN`) are Worker
  secrets, never in files or the bundle. Only the app gets the
  OpenAI key; the Durable Object and the cron see `EXIOM_*`
  settings only. The key set now is the
  one from the local `.env`; replace it with the client's own
  project key (with a monthly budget limit in the OpenAI
  dashboard): `npx wrangler secret put OPENAI_API_KEY`.


## 5. Measured on Workers Paid (`wrangler tail`, 28 Sep 2026)

Answers the open questions in Handoff §7.

| Event | CPU | Wall |
| --- | --- | --- |
| Cold copy, first page | 1.9–2.4 s | 2.2–2.7 s |
| Warm page / static file | 8–20 ms | 20–270 ms |
| `/api/network-stats` from the cron reading | 9 ms | 0.27 s |
| Streamed question (router + answer, long) | 2.8 s | 7–19 s |
| One Durable Object call | ~1 ms | 25–130 ms |
| Cron run (3 Explorer reads) | 0.46–0.73 s | 43 s |

* Startup snapshot: accepted at 3.4–3.9 s.
* Bundle: 20.0 MB, 4.1 MB gzipped (limit 64 MiB).
* The cron alone uses about 26M of the 30M CPU-ms included
  each month. Beyond that CPU costs $0.02 per million ms, so the
  cron costs at most about $0.50/month and questions a few
  cents per thousand.
* Durable Object requests: about 10 per streamed question
  (flood guard, slot, check, one record per provider call,
  client tokens, release) and 1 per page or stats request, not
  the 3 Handoff §5 assumed. 1M are included (about 80,000
  questions a month), then $0.15 per million. Duration is billed
  only while the object handles a call, not while idle
  (developers.cloudflare.com/durable-objects/platform/pricing).
* **Expected bill: $5/month plus cents** (OpenAI separate), as
  Handoff §5 estimated.
* Checked live: streaming, fast-path answers, off-topic
  deflection (instructions loaded), 4-answer cap per client
  (5th refused), `/api/usage` (401 without the token), security
  headers, daily ledger.


## 6. Operating it

Needs Node and `uv` (`~/.local/bin/uv`). From `cloudflare/`:

```
./deploy.sh                              # build, check bundle, deploy
uv run pywrangler dev                    # local, port 8787, secrets from .dev.vars
npx wrangler secret put OPENAI_API_KEY   # or EXIOM_USAGE_TOKEN
npx wrangler tail --format json          # live logs with cpuTime / wallTime
npx wrangler rollback                    # previous version
```

Limits are changed the same way as on Railway: add an
`EXIOM_*` variable to `vars` in `wrangler.jsonc` (or as a
secret) and redeploy. The hub reads them when it starts.

Not done (optional in the Handoff): SDK-free stream parsing
(§3; would cut the 2 s `openai` import and per-piece CPU),
moving `static/` to Workers Static Assets (§4.6), connecting
the GitHub repo for automatic deploys.
