# EXIOM AI — Privacy Review

Task 13. What personal data the service touches, where it
goes, how long it lives, what was fixed, and what an operator
must check before going live. The new piece is `privacy.py`
(with `wordlists/`); tests are in `tests/test_privacy.py`.


## 13.1 Data-handling review

Every route, log line, cache, counter, outbound call and the
page's storage were traced. The full inventory:

| Data | Where it goes | How long | Notes |
| --- | --- | --- | --- |
| Question + last 8 turns | AI provider, per request | Not kept by EXIOM AI. The provider keeps nothing retrievable (`store: false`, see finding 1); OpenAI's API policy allows up to 30 days of abuse-monitoring retention | Never logged, never in a URL |
| Stateless answer text | `answer_cache`, in memory | 5 min, max 256 entries | Keyed by a SHA-256 digest. Only returned to someone asking the identical question with identical facts. Answers that depend on conversation history are never cached |
| Routing decision | `router_cache`, in memory | 15 min, max 512 | Scope/intent/fact keys only, keyed by digest |
| Client key (IPv4, or IPv6 /64) | Flood guard, usage controller, answer slots | Until evicted, restart, or daily reset; max 50,000 | Counters only. Never logged, never returned by `/api/usage` |
| Access log | stdout | Platform retention | Time, method, path, status, bytes, ms. No IP, User-Agent, referrer or query string (finding 2) |
| Error / slow-request logs | stdout | Platform retention | Exception class + redacted provider text, or path + timing. No question text (tested). gunicorn's own error log names the URL of a failed request. Questions are never in a URL |
| Browser | JS memory of the tab | Until the tab closes | `localStorage` holds one value: `exiom.streaming` = on/off |
| Explorer calls | `explorer.xeqmlabs.com` | — | Fixed URL, fixed User-Agent. No user data |
| Cookies | none | — | No route sets one (tested) |

Findings:

| # | Finding | Severity | Status |
| --- | --- | --- | --- |
| 1 | The Responses API **stores every response by default** (retrievable for 30 days), so every question and answer was being kept by the provider. Nothing reads a stored response back. | High | Fixed: `store: false` on every call, never dropped by the cost-control fallback |
| 2 | gunicorn's **default access-log format logs the client IP, Referer and User-Agent**. The config comment said "method, path and status only", which was wrong. | Medium | Fixed: explicit `access_log_format` |
| 3 | Nothing stopped a user **pasting a recovery phrase or private key**. It was forwarded to the AI provider and, if stateless, the answer to it was cached. On a crypto assistant this is the most likely way real secrets leak. | High | Fixed (13.2) |
| 4 | The page read `localStorage` unguarded. With storage blocked (private browsing, strict privacy settings) it throws and **the whole chat script died**. Privacy-conscious users couldn't use it at all. | Medium | Fixed: guarded reads/writes (Jinja page and the dev React app) |
| 5 | Users were never told their questions go to a third-party AI service. | Low | Fixed: notice under the input (13.2) |

Verified fine as-is: questions only travel in POST bodies;
`Referrer-Policy: no-referrer` and `rel="noopener noreferrer"`
on answer links, so nothing leaks to linked sites; the CSP
blocks every third-party script, so no analytics or tracking
can be injected; `/api/usage` returns aggregates only;
router/answer cache keys are digests, not text; answers are
`no-store`.


## 13.2 Conversation privacy

**Wallet-secret guard** (`privacy.py`). Detected:

* a **recovery phrase**: 12+ consecutive words from the
  BIP-39 English list or Monero's English list. XEQM uses
  CryptoNote (Monero-style) wallets, and users may also hold
  BIP-39 wallets. The lists are committed verbatim
  (`wordlists/`). `bip39-english.txt` matches the SHA-256 in
  the BIP-39 spec (`2f5eed53…24dbda`). Neither list contains
  "the", "is", "my", "how", "a", "to"…, so an ordinary
  sentence breaks the run well before 12 words. Some common
  words ("what", "can", "you", "coin") are in a list, hence
  the 12-word threshold. Case,
  commas, numbering and control characters do not stop a
  match.
* a **BIP-32 extended private key** (`xprv`/`yprv`/`zprv`/`tprv`…)
  or a **WIF private key**.
* **64 hex characters directly after a key's name** ("view
  key: …", "spend key is …"). Without that name the same
  shape is normally a transaction or block hash, and "use my
  view key to check transaction <hash>" is a question, not a
  paste. Both still go through.

Behavior:

* **A question** carrying a secret is refused with 400
  `sensitive_content` before the fast path, the usage
  controller, the router, any cache or any log sees it. It is
  checked before the length limit, so an oversized paste
  still gets the right warning. The reply tells the user
  never to share it and, if they already did, to move their
  funds. The Jinja page does not add a refused question to
  its history. The dev-only React app does, and the server
  drops the turn again (next point).
* **History turns** carrying a secret are dropped before
  trimming, so clipping can't cut a phrase short enough to
  slip past the detector. This covers old or modified clients
  resending one.

**Notice** under the input (linked by `aria-describedby`):
questions go to an AI service, the chat lives only in the tab,
never share a recovery phrase, private key or personal
details. It does not name the provider: the system prompt
forbids that (Task 12). A category of recipient is enough
for transparency.


## 13.3 Production privacy checks

Automated (`tests/test_privacy.py` and
`tests/test_gunicorn_config.py`, 38 tests; run with the suite):

* every provider call, streamed or not, sends `store: false`
* a question never reaches stdout, even when the router and
  the provider fail
* no route sets a cookie
* the access-log format has no address, User-Agent, referrer,
  query string or request-header atom
* seed / key refusal on both transports, with zero provider
  calls, zero cache entries and nothing logged
* ordinary questions (including long ones, and tx hashes) are
  not refused

Smoke run under gunicorn: access log lines read
`[24/Sep/2026:21:24:41 +0500] "POST /ask" 400 289 0ms`,
with a custom User-Agent, a referrer and a query string all
absent. A pasted seed returns `sensitive_content`. The notice
renders.

Tests: 342 pass (Task 13 adds 38).

**Before going live (operator):**

1. **OpenAI project settings:** confirm data sharing for
   training is off (off by default for the API). If
   provider-side abuse retention is unacceptable, request
   Zero Data Retention from OpenAI. `store: false` does not
   cover that.
2. **Platform / Cloudflare logs** record client IPs on their
   own, outside this app. Set the shortest retention that
   still works for debugging. Never enable request-body
   logging or payload capture (e.g. Logpush with bodies, WAF
   payload logging).
3. **Leave Cloudflare's script injection off:** Web Analytics
   auto-injection, Rocket Loader, Email Obfuscation, Zaraz.
   They add third-party scripts and beacons, and the CSP
   blocks them anyway.
4. **Privacy policy:** if the service is offered to people in
   the EU/UK, publish one. Include: questions are processed
   by an AI provider; IP addresses are held in memory as
   rate-limit keys, never written to disk, until the process
   restarts or the entry is evicted; no cookies; no accounts. The
   in-page notice is a notice, not a policy.
5. **Ship `wordlists/`** with the app. `privacy.py` loads it
   at import, so a missing list stops the app at boot instead
   of silently disabling the guard.
6. **Never add question logging** "for debugging". If it is
   ever truly needed, log `privacy.contains_wallet_secret`
   results and lengths, not text.


## Accepted risks

* **The guard is a safety net, not a filter.** It catches
  accidental pastes in English wordlists. A phrase in another
  BIP-39 language, a seed split across several messages,
  words typed with no separators, a bare `0x`+64-hex key, or
  a deliberately disguised one is not detected. Only the
  user who does that is exposed.
* **The provider still sees every other question.** A user
  who types personal details sends them to the AI provider.
  The notice asks them not to.
* **The answer cache is shared between users** for identical
  stateless questions (5 minutes). It returns only what the
  asker would have got anyway. `Server-Timing` reveals a
  cache hit, and so that someone asked the same question
  recently (Task 12 accepted risk).
* **Client IPs are held in memory** as limit keys. That is
  necessary for abuse control, bounded, and never written
  anywhere.
