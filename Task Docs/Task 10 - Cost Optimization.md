# EXIOM AI — Token and Cost Optimization

How EXIOM AI keeps answer quality while spending as little
as possible per question.

Every measurement below is an approximation of ~4 characters
per token, which is what the code uses for budgeting.


## Where the money went before

Every `/ask` request made two AI calls:

| Call | Input |
| --- | --- |
| Semantic router | ~1,750 tokens of prompt, **plus the question twice**, plus up to 6 history messages of 3,000 characters each |
| Main answer | ~7,300 tokens of static instructions, the selected Explorer facts, the retrieved knowledge, plus up to 10 history messages of 3,000 characters each |

Worst case, a single question could send more than 20,000
input tokens. None of it was cacheable, because the parts
that change every 30 seconds came first.


## What changed

### 1. Deterministic $0 responses (`fast_path.py`)

Some questions never needed an AI call at all:

* greetings, thanks and goodbyes
* "Who made you?", "What are you?", "Are you official?" —
  the documented answer is fixed (Xrypto, the channel link,
  and the independence statement), so generating it was both
  slower and riskier than stating it
* explicit requests for one verified Explorer value, such as
  "What is the current block height?"

These skip **both** AI calls and cost nothing.

The rules are deliberately conservative. A question falls
through to the semantic AI router whenever there is any
doubt, and the existing documented distinction is preserved
exactly:

* "What is staking?" → AI router (explanation)
* "What is the staking requirement?" → $0 Explorer value
* "What does block height mean?" → AI router (explanation)
* "What is the current block height?" → $0 Explorer value

A fact name on its own usually reads as a concept question,
so **a value cue is required by default**: "current",
"latest", "how many", "how much", "right now". "What is the
total supply?" goes to the AI router; "What is the total
supply right now?" is free.

The only exceptions are the named thresholds — the staking
requirement and the minimum operator contribution — whose
everyday name *is* the value being asked for. The project
documentation gives the first of those as its worked example
of a direct live fact.

Identity questions are matched just as narrowly. "Are you
made by XEQMLabs?" has a documented fixed answer; "Are you
related to Bitcoin?" does not, and reaches the AI.

Two facts in one question, a follow-up pronoun, an unknown
word, a missing Explorer value, or a long question all hand
the question back to the AI router.

### 2. Prompt caching by construction (`app.py`)

The provider bills a cached prompt prefix at a fraction of
the normal input rate, but only when the identical text comes
**first**.

The system prompt was reordered into:

1. `STATIC_SYSTEM_PROMPT` — identity, personality, teaching
   rules, knowledge policy, the changelog and the project
   instructions. ~7,300 tokens, byte-identical on every
   request, built once at import.
2. A short `THIS REQUEST` section — routing decision,
   selected Explorer values, retrieved knowledge.

Same content, same quality, an order of magnitude cheaper on
the repeated part.

### 3. A cheaper semantic router (`query_router.py`)

* The question is no longer embedded in the router prompt and
  also sent as the user turn. It is sent once.
* Explorer fact **values** were removed from the router
  prompt. The router picks fact keys; it never needed the
  numbers. Their removal also makes the prompt identical
  between requests instead of changing every 30 seconds,
  which is what made it cacheable.
* Redundant example lists were compressed. Every routing rule
  is unchanged and covered by tests.
* Router history is capped at 2 messages of 240 characters —
  enough to resolve "and the other one?", nothing more.

Router prompt: **~1,750 → ~1,190 tokens**, before the saved
duplicate question and the history reduction.

### 4. Reasoning effort as a cost lever (`ai_provider.py`)

Reasoning tokens are billed as output tokens.

| Call | Effort | Output ceiling |
| --- | --- | --- |
| Router | `minimal` | 300 |
| Answer | `low` | 1,600 |
| Off-topic banter | `minimal` | 200 |

The router emits a three-field JSON object and needs no
deliberation. Each is overridable with
`EXIOM_ROUTER_REASONING_EFFORT`, `EXIOM_MAIN_REASONING_EFFORT`
and `EXIOM_OFF_TOPIC_REASONING_EFFORT`.

If a model or SDK rejects one of these options, the provider
disables it and retries the plain request. A cost control can
never break a response.

### 5. Bounded conversation and knowledge

* History: 10 messages × 3,000 characters → 8 messages ×
  1,200 characters, hard-capped at 6,000 characters total.
  The newest turn is always kept.
* Retrieved knowledge is capped at 7,000 characters total and
  2,200 per section, and sections far weaker than the best
  match are dropped. On today's knowledge base this changes
  nothing — retrieval already returns ~700 tokens — so it is
  a guard rail that keeps the cost flat as the knowledge base
  grows, not a cut to current traffic.
* Explorer facts sent to the model carry only `label`,
  `value` and `unit`. Bookkeeping fields are dropped and all
  JSON is serialised without decorative whitespace.

### 6. Safe reuse (`cache.py`)

Two caches, both of which only ever return a result when the
inputs are provably identical.

* **Router decisions** (15 minutes) keyed by the normalised
  question and which facts exist.
* **Answers** (5 minutes) keyed by the normalised question,
  the routing decision, the **values** of every Explorer fact
  used, the Explorer's availability and connection state, and
  the retrieved knowledge.

Never cached:

* anything asked inside a conversation — the same words mean
  different things after different context
* off-topic banter — it is required to stay varied
* failed calls

A changed Explorer value changes the key, so a stale number
can never be served.

### 7. Usage control (`usage_control.py`)

`UsageController` is checked only before paid work. Free
deterministic answers never consume anyone's budget.

| Limit | Default | Environment variable |
| --- | --- | --- |
| Requests per minute, per client | 15 | `EXIOM_REQUESTS_PER_MINUTE` |
| Requests per day, per client | 300 | `EXIOM_REQUESTS_PER_DAY` |
| Tokens per day, per client | 400,000 | `EXIOM_CLIENT_TOKENS_PER_DAY` |
| Tokens per day, service-wide | 20,000,000 | `EXIOM_GLOBAL_TOKENS_PER_DAY` |

A blocked request gets a friendly in-character message, HTTP
429 and a `Retry-After` header.

`CostMeter` records tokens and estimated spend per route.
Counters only — no question text is stored anywhere.

`GET /api/usage` exposes provider calls, free responses, the
free-response rate, cached-input rate, estimated USD, cache
hit rates and the active limits. It answers 404 until
`EXIOM_USAGE_TOKEN` is set, and then only to a caller sending
that value in an `X-Usage-Token` header.

Callers are identified by the entry `EXIOM_TRUSTED_PROXY_HOPS`
from the right of `X-Forwarded-For` (default 1, for a single
platform load balancer), falling back to the socket address.
The leftmost entry is caller-controlled and would let anyone
forge a fresh budget per request.


## Quality protection

Nothing in this work changes what a full answer is allowed to
say. Specifically:

* Every routing rule, teaching rule, Explorer-data rule and
  safety rule is still sent, in full, on every answered
  question.
* The fast path only answers cases whose correct answer is
  already fixed by the documentation or by a verified
  Explorer value.
* The concept-versus-statistic distinction is enforced twice:
  once in the fast path and once in the router prompt.
* 155 tests cover the routing boundaries, the cache-safety
  rules, the budget arithmetic and the failure paths.


## Known trade-offs

* **Free responses are not rate limited.** They cost nothing
  in AI spend, so charging them against a caller's budget
  would only penalise ordinary users. Flooding protection for
  free responses belongs in front of the application.
* **The caches are per process.** With several workers, each
  warms its own. That is intentional: a shared cache would
  add a dependency and a new failure mode to save a small
  number of calls.
* **Counters are per process too**, so `/api/usage` reports
  one worker's view and the global token ceiling is enforced
  per worker. Size `EXIOM_GLOBAL_TOKENS_PER_DAY` accordingly.


## Running the tests

```
pip install -r requirements-dev.txt
pytest
```
