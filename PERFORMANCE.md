# EXIOM AI — Performance and Reliability

Task 11. How EXIOM AI stays fast under load and fails
predictably when OpenAI or the Explorer does not.


## 1. OpenAI timeouts and retries (`reliability.py`, `ai_provider.py`)

The SDK's own retries stay off (`max_retries=0`); every retry
decision is made in `reliability.py`, which mirrors the OpenAI
Python SDK's documented policy:

| Failure | Retried? |
| --- | --- |
| timeout, connection error | yes |
| 408, 409, 429, 5xx | yes |
| other 4xx | no |
| 429 `insufficient_quota` | **no** (waiting cannot refill an account) |
| `x-should-retry: true/false` | as the server says |

The wait is `Retry-After` / `Retry-After-Ms` (seconds, ms or
an HTTP date) when the server sends one, otherwise
0.5s → 1s → 2s … capped at 8s, shortened by up to 25% jitter.

Deliberate differences from the SDK: `insufficient_quota` is
final even when `x-should-retry: true`, and a `Retry-After`
over 10s means no retry (the SDK waits up to two minutes, but
a person is watching a spinner).

Each call has its own limits. `read` is the longest silence
tolerated in one attempt (for a stream, between events).
`deadline` is the window in which attempts may start: no
retry begins that could not finish inside it. A stream that
is already delivering text is never cut off; its
output-token ceiling bounds it.

| Call | read | deadline | env override |
| --- | --- | --- | --- |
| router | 10s | 15s | `EXIOM_ROUTER_TIMEOUT` / `_DEADLINE` |
| answer | 45s | 60s | `EXIOM_ANSWER_TIMEOUT` / `_DEADLINE` |
| off-topic | 15s | 20s | `EXIOM_OFF_TOPIC_TIMEOUT` / `_DEADLINE` |

Connect timeout is 5s (`EXIOM_OPENAI_CONNECT_TIMEOUT`);
attempts per call are 2 (`EXIOM_OPENAI_MAX_ATTEMPTS`).

The router fails fastest because its failure is never fatal:
the pipeline falls back to a default route and still answers.
Dropping a rejected cost-control option no longer uses up a
retry. Streams keep their rule: once text is on screen, no
retry.


## 2. Explorer (`live_data.py`)

The Explorer is fetched on the request path, so:

* **Single flight.** Requests that miss the cache together
  share one fetch instead of stampeding the Explorer.
* **Refresh ahead.** In the last 10s of a 30s reading, one
  background fetch renews it while callers keep the
  still-valid reading. Under steady traffic nobody waits.
* **Failures are remembered for 10s.** A down Explorer costs
  one timeout, not one per question. A failed refresh-ahead
  keeps the still-valid reading and waits 10s before trying
  again.
* **Never stale.** An expired reading is never served, even
  while the Explorer is down: values are presented as
  current.
* Timeouts are (3s connect, 6s read), over a keep-alive
  session.


## 3. Server work

* Knowledge sections are indexed once at startup;
  retrieval went from ~3.7ms to ~0.08ms per question with
  identical results (tested).
* `gunicorn.conf.py` (loaded automatically by
  `gunicorn app:app`) uses threaded workers: requests spend
  their time waiting on I/O, and an SSE stream would
  otherwise hold a whole process. Tune with
  `WEB_CONCURRENCY` (processes, default 2) and
  `GUNICORN_THREADS` (default 8). Prefer more threads over
  more processes: caches and limits are per process, so one
  client's per-minute allowance is effectively multiplied by
  the number of workers.
* Under gthread, gunicorn's `timeout` only detects a hung
  worker; it does not limit requests. Requests are bounded by
  the provider timeouts above.
* Worker recycling (`max_requests`) is **off**. Usage limits
  live in worker memory, so recycling would hand every client
  a fresh daily budget.


## 4. Frontend (Jinja, `templates/index.html`)

* Streamed text is drawn at most once per animation frame
  instead of once per token (each draw re-formats the whole
  answer).
* The stylesheet URL carries a content digest and is cached
  for a year (`immutable`); any edit changes the URL. Bare
  `/static/` URLs keep Flask's default revalidation.

**Recommendation: ship the Jinja frontend.** It is what
Flask serves at `/`, and it has every functional feature the
React client has (chat history, streaming toggle). It also
has two the React client lacks: the live Explorer panel and
the Explorer source link on answers. It needs no build step
and no second deployment. It loads ~43KB (25KB page with its
script inline, plus a 17KB stylesheet), versus ~321KB for
React (a 310KB JavaScript bundle with React and GSAP, plus
11KB of CSS) before its page shell. The React client also
replaces the server's own error messages (usage limit,
timeout) with a generic "could not connect", and its dev
proxy does not forward `/api/`. It is only worth it if richer
animation or a much larger UI is planned. If so, port the
live panel and the error handling first.


## 5. Measuring

**Server-Timing.** Every response carries
`Server-Timing: app;dur=<ms>` (visible in browser DevTools →
Network → Timing). For a stream it is the time until the
stream opened, which is what a user waits through before
text appears. Requests slower than `EXIOM_SLOW_REQUEST_MS`
(5000) are logged without question text.

**Response-time tests** (`tests/test_response_time.py`) hold
the app's own overhead, with the provider faked, under wide
budgets to catch regressions. Measured: ~0.5ms p95 for fast
paths, ~0.8ms for the full pipeline.

**Concurrency tests** (`tests/test_concurrency.py`) start a
real threaded server and check that concurrent answers never
cross, that streams arrive progressively, that caches stay
correct under identical concurrent questions, and that the
rate limit admits exactly its allowance under a burst.

**Load testing a real deployment** (`loadtest.py`):

```
python loadtest.py --url http://127.0.0.1:8000 --concurrency 20 --requests 400
python loadtest.py --url https://host --stream --question "what is staking" --max-p95-ms 8000
```

The default question is a free fast-path greeting; any
`--question` that reaches the AI is billed. All traffic
comes from one machine, so 429s from the usage limiter are
expected and reported separately. The exit status is 1 on
any 5xx or transport failure, on a stream that broke
part-way (still HTTP 200, but ending in an error frame), or
when `--max-p95-ms` is exceeded.

Local gunicorn smoke run (fast path, 16 concurrent): 400/400
OK, p95 13ms, ~300 req/s. The p99 was the cold first Explorer
fetch; refresh-ahead keeps later fetches off the request path.
