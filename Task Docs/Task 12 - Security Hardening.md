# EXIOM AI — Security Hardening

Task 12. What was reviewed, what was fixed, and what an
operator must get right when deploying. The new pieces live
in `security.py`; tests are in `tests/test_security.py`.


## 12.1 API / security review

Every route, the page's JavaScript, the prompt pipeline,
logging and the deployment files were reviewed. Findings:

| # | Finding | Severity | Status |
| --- | --- | --- | --- |
| 1 | Answer links: `escapeHTML` did not escape `"`, and URLs in answers are put inside `href="…"`. Model text such as `https://x"onmouseover="…` broke out of the attribute (XSS). | High | Fixed |
| 2 | A JSON list or string body, a non-string `question`, or deeply nested JSON (`RecursionError`) crashed `/ask` and `/ask/stream` with a 500 and an HTML traceback page. | Medium | Fixed |
| 3 | No limit on body size: any size was read into memory. | Medium | Fixed (256 KiB) |
| 4 | Free routes (fast path, `/api/network-stats`, the page) had no rate limit at all. | Medium | Fixed (flood guard) |
| 5 | One client could hold many slow streams, and so many server threads, while staying inside its per-minute limit. | Medium | Fixed (answer slots) |
| 6 | One IPv6 subscriber (a /64) could rotate addresses past every per-client limit, and grow the usage table without bound. | Medium | Fixed |
| 7 | No security headers (CSP, framing, sniffing, HSTS…). | Medium | Fixed |
| 8 | `/api/usage`: a non-ASCII `X-Usage-Token` made `compare_digest` raise (500); any short token was accepted. | Low | Fixed |
| 9 | OpenAI echoes part of a rejected key in its error text, which was printed to the logs. | Low | Fixed (redacted) |
| 10 | `python app.py` always started the Werkzeug debugger (code execution if ever exposed). | Low | Fixed (opt-in) |
| 11 | Dependencies unpinned: a deploy could pick up an unreviewed release. | Low | Fixed (direct deps pinned) |
| 12 | `X-Forwarded-For` was trusted from any peer. With gunicorn reachable directly, a new forged value per request bypassed every per-client limit (found in code review). | High | Fixed |

Verified fine as-is: `.env` has never been committed (git
history checked) and is mode 600; the API never returns
exception text; `X-Forwarded-For` is read from the right
(Task 10); the Explorer URL is fixed (no SSRF); no CORS
headers are sent; React `npm audit`: 0 vulnerabilities.


## 12.2 Environment-secret protection

* `.gitignore` now covers every `.env.*` variant, keys and
  certificates, `.venv/` and `.pytest_cache/`. Only
  `.env.example` (committed, no values) is exempt. It lists
  every variable with its default.
* Log lines that can carry provider error text go through
  `security.redact_secrets` (`sk-…` → `sk-***`,
  `Bearer …` → `Bearer ***`).
* `EXIOM_USAGE_TOKEN` must be at least 32 characters, or the
  endpoint stays off (404) and a warning is logged. The token
  is compared as bytes in constant time. Usage responses are
  `Cache-Control: no-store`.
* Debug mode only with `FLASK_DEBUG=1`, and never in
  production.


## 12.3 Request / input hardening

* **Body size:** `MAX_CONTENT_LENGTH` =
  `EXIOM_MAX_REQUEST_BYTES` (256 KiB). Werkzeug refuses a
  larger body before it is parsed; the reply is JSON 413
  `request_too_large`. The page now sends only the last 8
  turns, all the server keeps anyway.
* **Shape:** `/ask` and `/ask/stream` accept only an
  `application/json` object whose `question` is a string.
  Anything else, including nested JSON that exhausts the
  parser, is a 400 `invalid_request`, and no AI work is done.
* **CSRF / cross-site use:** requiring `application/json` means
  a cross-site form or `sendBeacon` cannot post a question.
  A cross-site `fetch` needs a CORS preflight, which this
  service never approves.
* **Control characters:** C0/C1 control characters (except
  tab and newlines) and the Unicode bidi controls used in
  "Trojan Source" attacks are removed from the question and
  history.
* **Unhandled errors** return JSON 500 `unknown` with no
  details; Flask still logs the traceback.
* **Headers on every response:** a CSP with a fresh nonce per
  request (`script-src 'nonce-…'` only, `object-src 'none'`,
  `base-uri 'none'`, `frame-ancestors 'none'`,
  `connect-src 'self'`), plus `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
  `Permissions-Policy`, COOP/CORP `same-origin` and HSTS
  (one year; browsers ignore it over plain HTTP). Answers are
  `no-store`.
* **Page:** the one inline script carries the nonce, and the
  five `onclick=` attributes became `addEventListener`,
  because a nonce CSP blocks inline handlers. `escapeHTML`
  now escapes quotes (finding 1).


## 12.4 Rate / abuse protection

Three layers, all per process:

| Layer | Covers | Default | Env |
| --- | --- | --- | --- |
| Flood guard (token bucket) | every route except `/static/` | 120 req/min per client, burst 120 | `EXIOM_FLOOD_REQUESTS_PER_MINUTE` |
| Answer slots | `/ask`, `/ask/stream` in flight | 4 per client | `EXIOM_MAX_CONCURRENT_ANSWERS` |
| Usage controller (Task 10) | paid AI work | 15/min, 300/day, token ceilings | see `.env.example` |

* Refusals are JSON 429s with `Retry-After`, using
  `too_many_requests` and `too_many_concurrent`. The page
  already shows the server's own message.
* A stream holds its slot until the server closes the
  response. WSGI guarantees the close even when the client
  disconnects. Refusals and failures before the first token
  release the slot at once.
* **Client identity:** `X-Forwarded-For` is only believed
  when the connecting peer is private, loopback or
  link-local, which is where a platform load balancer
  connects from. A client that reaches gunicorn directly
  from the internet is keyed by its real address. For a
  proxy on public addresses (e.g. a CDN), set
  `EXIOM_TRUST_PUBLIC_PROXY=1`. An address that is not an IP
  (a forged hop) falls back to the peer. IPv6 is keyed by /64, and
  IPv4-mapped IPv6 by its IPv4 address.
* **Bounded memory:** the flood guard and the usage
  controller keep at most 50,000 clients each
  (`EXIOM_MAX_TRACKED_CLIENTS`) and evict the least recently
  active first. An evicted client only
  gets a fresh allowance; the global daily token ceiling
  still bounds total spend.


## 12.5 Production server configuration

`gunicorn.conf.py` now sets request-head limits explicitly:
request line 4094 bytes, 50 header fields, 8190 bytes per
field. Oversized heads are refused (431) before reaching
Flask. Unchanged from Task 11: gthread workers, worker
recycling off, logs to stdout.

**Dependencies:** direct dependencies are pinned in
`requirements.txt` to the tested versions. Upgrade
deliberately, then run the tests.

Tests: 304 pass (`tests/test_security.py` adds 75).

Smoke run under gunicorn: CSP/HSTS/frame headers present,
list body → 400, 300 KB body → 413, 9 KB header → 431,
flood limit → 429.


## 12.6 Deployment security checklist

1. **TLS at the load balancer**, with HTTP redirected to
   HTTPS. HSTS then takes effect.
2. **`EXIOM_TRUSTED_PROXY_HOPS` must equal the number of
   proxies** in front of gunicorn: 1 behind one platform load
   balancer, 0 if exposed directly. If it is too high, a
   client can forge its identity. If it is too low, every
   user shares the balancer's address and one budget. If
   the proxy connects from a public address, also set
   `EXIOM_TRUST_PUBLIC_PROXY=1`, otherwise every user shares
   the proxy's budget.
3. **`OPENAI_API_KEY` goes into the platform's secret store**,
   not a file in the image. Use a dedicated OpenAI project
   key with a monthly budget cap, and rotate it at once if it
   ever appears in a log or a commit.
4. **Start with `gunicorn app:app`**, never
   `python app.py`. Leave `FLASK_DEBUG` unset.
5. **The proxy should buffer request bodies** (slow-client
   protection; gunicorn's own documentation recommends a
   buffering proxy) and may cap them at 256 KiB. It must
   **not** buffer `/ask/stream` responses
   (`X-Accel-Buffering: no` is already sent).
6. **Keep `WEB_CONCURRENCY` small**, because every limit
   above is per process (Task 11 §3).
7. **Deploy the Jinja frontend only** (Task 11 §4).
   `frontend/` (React/Vite) is development-only: it is not
   served with these headers.
8. **Do not ship** `test_explorer.py`, `loadtest.py`,
   `tests/` or `.env` in the image.
9. **`EXIOM_USAGE_TOKEN`**, if used, is at least 32 random
   characters:
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`.


## Accepted risks

* **Conversation history is client-supplied.** A user can
  forge earlier "assistant" turns to steer their own answer.
  Only that user's answer is affected, and it stays inside
  their budget. Fixing this would need server-side sessions.
* **The system prompt's "never reveal" rules are best-effort.**
  The prompt contains no secrets, so a leak exposes only
  wording.
* **Users behind one NAT share limits.** The defaults are
  generous for humans, and each limit is an environment
  variable.
* **Limits are in memory:** they reset on restart and are
  multiplied by `WEB_CONCURRENCY`. A shared store (e.g.
  Redis) is the upgrade path if the service scales out.
* **Only direct dependencies are pinned.** Transitive ones
  (Werkzeug, Jinja2, httpx…) still float. To pin them too,
  add a lock file (`pip-compile` / `pip freeze` of a clean
  production venv).
* **An attacker with 50,000+ addresses can evict other
  clients' counters.** That gives them a fresh allowance,
  but the global daily token ceiling still caps spend.
* **`Server-Timing` (Task 11) is sent on every route.** It
  reveals the app's own processing time, including whether
  an answer came from the cache. Total response time
  already reveals this. Remove it if that matters.
* **gunicorn sends `Server: gunicorn`.** It has no option to
  remove the header, and it reveals no version.
