# Answer Quality and Image Upload — Implementation Plan

Status: Parts 1–2 **built** 2026-11-06, see `Answer Quality and Image Upload.md`; Part 3 not built yet.

Two pieces of work, in this order:

1. **Answer quality** — ExiomAI must answer from what we feed it
   (verified knowledge, Explorer, live market data, web search),
   never send the user off to look it up, and never invent
   EXIOM facts.
2. **Image upload** — images only, 5 per day per IP.

Answer quality goes first: image questions run through the same
pipeline, so they inherit every fix.

---

## Part 1 — What is wrong today (reproduced)

All three cases were reproduced locally against the real model
with `answer_pipeline` (same code as production; `cloudflare/src`
matches the source files).

### 1.1 "whats the coin price" → stale CoinGecko price from a web search

- All three trackers work: NonKYC $0.020293, CoinPaprika
  $0.020272, CoinGecko $0.020274 at the time of the test.
- The answer said **$0.0196, "Source: CoinGecko"** and quoted
  LiveCoinWatch: figures from a web search's old copies of
  those pages.
- **Cause:** the router returned `intent: "explanation"`.
  `app.py:1890-1894` skips live market data for "explanation"
  (the guard exists so "what does market cap mean?" doesn't
  fetch a price). With no market data, the model searched the
  web. The stale-price note was not added either, because it
  only applies when `wants_price` is true.
- **Why the router said "explanation":** the router prompt's
  OUTPUT example is literally
  `{"scope":"relevant","intent":"explanation",...}`
  (`query_router.py:297`). At minimal reasoning the router
  echoes it: all three test questions came back as
  "explanation".

### 1.2 "what does nonkyc and coinpaprika say" → "go check yourself"

- `PRICE_PATTERN` (`query_router.py:39`) doesn't know tracker
  names, so no market data and no search.
- The router picked unrelated facts (`nodes_by_country`,
  `block_height`), so the answer ran at the EXPLORER step.
- The model is told to reply `[[LOOKUP]]` when something is
  missing, **"never for a concept or explanation"**
  (`LOOKUP_SECTION`, `app.py:1190`). The question was labelled
  "explanation", so the model refused to escalate and wrote "I
  can guide you to the exact pages" instead.
- In the local repro it reached a search and then said it
  "couldn't fetch the live price due to a 403", citing GitHub
  for NonKYC: a search was used for something our own API call
  answers in under a second.

### 1.3 "can i stake 60k coins" → "Short answer: not by itself"

- The answer leads with "no". It never says plainly **"yes —
  as a contributor to a pool node (minimum 10,000 XEQM)"**,
  never says how to find an open node, and implies you could
  team up as the operator (the operator needs 100,000).
- **Cause 1, retrieval:** neither "Staking requirements, pool
  nodes and operator fee" nor "Staking as a contributor in a
  pool node" (`knowledge/service_nodes.md`) was retrieved.
  - The stemmer turns "staking" into `stak` but leaves "stake"
    as `stake`, so the question never matches those headings
    (`retrieval.py` `stem`).
  - Many sections tie on the "staking" concept score, and ties
    keep file order, so `core.md` and `history.md` sections
    take the slots first.
  - The model built its answer from the 200k/100k/10k example
    in `knowledge/instructions.md` ("RELATIONSHIPS BETWEEN
    NUMBERS") plus guesswork.
- **Cause 2, prompt:** "Simple factual question: usually 1-2
  sentences" and "Answer only what was asked" push a
  "can I…?" question towards a bare yes/no. Nothing tells the
  model to lay out the legitimate routes.
- **Cause 3, sources:** it wrote "Sources: EXIOM Tokenomics
  Whitepaper; XEQM Core Releases" as plain text (not links),
  and the code then added "Source: Official EXIOM Explorer",
  though no Explorer figure was used.

### 1.4 Explorer source line on answers that didn't use the Explorer

`source_additions` (`app.py:1271-1277`) adds the Explorer
footer to any answer containing a digit once Explorer data was
in the prompt. A web-searched price and the staking answer both
got it. That tells the user a wrong source.

---

## Part 2 — Fixes for answer quality

Each fix lists files, change, and the test that proves it.

### 2.1 Router: stop the "explanation" default

- `query_router.py`: replace the OUTPUT example with a
  placeholder that is not a valid intent (e.g.
  `{"scope":"<scope>","intent":"<intent>","facts":[<keys>],"search":<true|false>}`),
  and add worked examples for price, tracker names, "can I…"
  and amounts ("can I stake 60k?" → `general`, search false).
- Test: `tests/test_query_router.py` checks the example JSON in
  the prompt names no real intent.
- Eval: re-run the router on `evals/questions.txt` and check
  the intent spread is no longer all "explanation".

### 2.2 Prices: the live price whenever a price is wanted

- `app.py:1890`: replace `intent != "explanation"` with a
  code-side concept check, `query_router.asks_what_it_means()`
  ("mean", "meaning", "define", "definition", "explain", "how
  is … calculated", "what is a market cap"). The router's label
  no longer decides whether we fetch the price.
- `query_router.py` `PRICE_PATTERN`: add tracker and exchange
  names: nonkyc, coinpaprika, coingecko, coinmarketcap/cmc,
  livecoinwatch, and "trackers".
- Follow-ups ("and now?", "what do the others say?") already
  search; they must also fetch market data. `market_quote` is
  fetched when `wants_search` is true, so this is covered once
  2.2 sets `wants_price`.
- Optional, small: when the question names a tracker, fetch
  that tracker's quote specifically
  (`market_data.get_quote(prefer="coinpaprika")`). This
  answers "what does CoinPaprika say" truthfully. Recommended:
  only three sources and they're already written.
- Tests: `tests/test_query_router.py` for the new patterns;
  `tests/test_ask_endpoint.py` asserts that "whats the coin
  price" with router intent "explanation" still yields
  `web_search_state == "market"` and no search call.

### 2.3 Never "go look it up yourself"

The model must use the next step instead of deflecting. Three
layers:

1. **Prompt** (`app.py`):
   - `LOOKUP_SECTION`: drop "Never do this … for a concept or
     explanation". Replace it with: "If any part needs a
     figure, price, date, release, person or fact that isn't
     above, reply `[[LOOKUP]]`. Never tell the user to look it
     up or visit a site instead."
   - `WEB_SEARCH_RULES` rule 5 and
     `WEB_SEARCH_UNAVAILABLE_SECTION`: keep "never fill the gap
     from memory", but say what *was* found, give the closest
     verified facts, then at most one link. Never "search for
     it on their site".
   - Add one line to `REMINDER` (the end of the prompt, where
     a small model weighs it most): "Never tell the user to
     check, search or visit a site for something you could be
     given: ask for it with [[LOOKUP]]."
2. **Code backstop** (`app.py`):
   - Add `query_router.is_deflection(answer)`, a regex for
     "I don't have … (in this chat|right now)", "check (it|the
     price) (on|at)", "visit … for the latest", "I can guide
     you to", "search for … on their site".
   - Non-streaming: a deflecting answer at a step that can look
     further is treated like `[[LOOKUP]]` (`continue`).
   - Streaming: `watch_for_lookup` already holds back the
     opening characters. Extend it to hold the first sentence
     (up to about 160 characters) and divert on a deflection
     opener. Deflections almost always open the answer, as in
     both repros. This costs about 0.3 s of first-token latency
     only on steps that can still look further.
3. **Last step:** a deflection at the final step is allowed
   only after a real search ran. It's then the honest "couldn't
   find it", which `NOT_FOUND_ANSWER` already words.

Tests: `tests/test_ask_endpoint.py` with a fake provider whose
first answer is "I don't have the current figures from NonKYC in
this chat…" asserts that the pipeline moves to the next step,
streaming and not.

### 2.4 Helpful, complete answers ("can I stake 60k?")

`knowledge/instructions.md` and the static prompt:

- New section **"CAN I … ? QUESTIONS"**: lead with what the
  user *can* do, never a bare "no". Shape:
  1. Direct answer in one line ("Yes — not as a solo node, but
     as a contributor to a pool node.")
  2. **Your options**: every legitimate route the supplied
     knowledge gives, each with its numbers and who it suits.
     For staking: solo 200k; pool operator ≥100k; contributor
     ≥10k (up to 10 contributors, operator cut 0–10%, no
     hosting cost).
  3. **How to do it**: the concrete steps from the knowledge
     (find an open node on the Explorer, `stake <pubkey>
     <amount>` in the CLI wallet, GUI also works).
  4. **Good to know**: risks and locks (operator uptime, 14-day
     unstake).
  5. Source links.
- Narrow "Simple factual question: 1–2 sentences" to "a single
  current value", so it no longer applies to yes/no
  eligibility questions.
- Add the 60k answer as a GOOD example and the current answer
  as BAD, the same way the file already teaches with examples.
- Fix the "RELATIONSHIPS BETWEEN NUMBERS" example so it matches
  `service_nodes.md` exactly (it does today; add a test that
  every number in `instructions.md` appears in the knowledge
  files, so the hidden example can never drift).

### 2.5 Retrieval: find the right sections

This is a global scoring fix, not a staking patch.

**Measured problem:** in 74 of the 92 eval questions
(`evals/*.txt`), sections tie for the last of the 6 places sent,
so file order decides what the model sees. Every match counts
the same, however common the word: a concept is a flat 12 points
although "service node" tags 35 of 78 sections, "wallet" 33 and
"staking" 27. Every word counts the same too, so "node" weighs
as much as "contributor".

`retrieval.py`:

- **Rarity-weighted scoring (BM25):** a word or concept counts
  more the fewer sections contain it, title matches count
  triple, and long sections don't win by length alone. This is
  the standard keyword-search ranking: no API call, no latency,
  deterministic, testable.
- **Stemmer:** stake/staked/staking/stakes all become `stak`
  (today "stake" and "staking" never match).
- **Synonyms:** "coins", "tokens" → xeqm. With rarity weighting,
  a rare everyday word ("coins") would otherwise pull in the
  coin-burn sections.
- **Amounts:** "60k", "60,000", "150k xeqm" count as a staking
  amount (staking requirement and contributor sections). Only
  numbers with "k", thousands separators or "xeqm" next to them
  count, never a bare number: "is 9231 safe to expose" is a
  port.
- **Tie-break:** on equal scores, the section whose title
  matches more question words wins, never file order.

**Prototype result** (scratch code, 2026-11-06): ties at the
cutoff 74/92 → 0/92. "can i stake 60k coins", "can i run a node
with 120k", "whats the minimum to stake", "i have 50000 xeqm
what can i do" and "how do i join a pool node" all retrieve both
staking sections first. 63/66 existing golden questions passed.
The 3 failures came from the over-broad amount pattern; the real
version must pass all of them.

**Not chosen first: embeddings (semantic search).** It would
need an OpenAI embeddings call per question (extra latency, a
second dependency on the provider), and its misses are harder to
explain and test. Add it only if the golden set and eval still
fail after BM25.
- **Golden questions** (`tests/test_knowledge.py` `GOLDEN`):
  "can i stake 60k coins", "i have 50000 xeqm what can i do",
  "can i run a node with 120k", "minimum to contribute", "how
  do i join a pool node". Each must retrieve both staking
  sections.

### 2.6 Sources: always links, never the wrong one

- `source_additions` (`app.py:1249`):
  - Add the Explorer footer only if an Explorer value actually
    appears in the answer: match the Explorer fact values (as
    formatted) against the answer text, instead of "any digit".
  - No Explorer footer when the answer cites a web page or the
    market tracker.
  - Citation repair: when the answer names a source title from
    `knowledge/sources.json` as plain text, turn it into its
    link. When an answer used knowledge sections but cites
    none, add "Sources:" from the retrieved sections' own links
    (at most two).
- Tests in `tests/test_ask_endpoint.py` for each rule, using
  today's two bad answers as fixtures.

### 2.7 Grounding check (anti-hallucination monitor)

- New `grounding.py`: `unsupported_numbers(answer, context)`
  returns every number in the answer (amounts, percentages,
  days, prices) that doesn't appear in the supplied context
  (knowledge, Explorer, market data, web results). Number
  forms are normalised: 100k = 100,000 = 100000.
- **Use 1, eval:** `live_eval.py` prints and counts them per
  answer. Zero is the bar for the golden set.
- **Use 2, production log:** print a one-line warning with the
  route and the count (never the question text, per the Task 13
  privacy rules). It doesn't block the answer. Blocking would
  hurt more than help with a small model until the eval shows
  how often it fires.

### 2.8 Answer model

The answers come from `gpt-5-nano` at "low" reasoning
(`ai_provider.py:353`, `MAIN_REASONING_EFFORT`). Both the
"guide you to the page" deflection and the plain-text sources
are typical small-model rule-skipping.

- Recommendation: keep `gpt-5-nano` for the router, and try
  `gpt-5-mini` for answers only (new `EXIOM_ANSWER_MODEL`, with
  a `MODEL_RATES` entry in `usage_control.py`; check the
  current price on OpenAI's pricing page first).
- Decide with the eval in 2.9: run the golden set on both and
  compare the grounding count and the checks. At about 10 AI
  answers a day the cost difference is a few cents a day.
- Note: a bigger model does not replace 2.1–2.7. Those fix
  what the model is given; this only helps it follow the rules.

### 2.9 Answer eval set

- New `evals/answer_checks.json`: question → must-contain /
  must-not-contain checks, e.g.
  - "can i stake 60k coins": must contain "10,000" and
    "contribut"; must not start with "No" or "Short answer:
    not".
  - "whats the coin price": must cite nonkyc.io (when NonKYC is
    up); must not contain "coingecko" or "livecoinwatch".
  - "what does nonkyc and coinpaprika say": must contain a
    price; must not contain "I don't have", "guide you" or
    "check".
- `live_eval.py --checks evals/answer_checks.json` prints
  pass/fail and the grounding count per answer. Run with
  `--parallel 2` (OpenAI 200K TPM cap).
- Done = every check passes on two consecutive runs.

---

## Part 3 — Image upload

### 3.1 Scope

- Images only: PNG, JPEG, WebP. Up to 3 per message.
- **5 images per day per IP**, `EXIOM_CLIENT_IMAGES_PER_DAY=5`.
  The client key is already the visitor IP (`CF-Connecting-IP`
  on Workers, IPv6 per /64; `client_identifier`, `app.py:478`).
- Images are used for that one answer and never stored, logged
  or cached. Follow-up questions don't resend them; the chat
  history records "[image]" in their place.

### 3.2 Backend

- `usage_control.py`: `client_images_per_day`;
  `claim_images(client_id, count)` → `(allowed, left)`. Claimed
  before the AI call, like web searches (a failed call still
  counts). `images_today` in client state; the limit appears in
  `snapshot()`.
- `usage_hub.py`: a `claim_images` op on the Durable Object.
  `remote_usage.py`: `RemoteUsageController.claim_images`, which
  refuses when the hub is unreachable.
- `app.py`:
  - `read_ask_request` also returns `images`: a list of data
    URLs, `data:image/(png|jpeg|webp);base64,…`. Each is
    decoded and its magic bytes checked; at most 3; each
    decoded image ≤ 1.5 MB. An empty question with images
    becomes "What's in this image?".
  - The body limit is raised only for `/ask` and `/ask/stream`:
    `request.max_content_length` set in `guard_request` to about
    5 MB. Every other route keeps 256 KB.
  - Pipeline with images: skip the fast path and both caches;
    skip the router and use `scope: mixed`, `intent: general`
    (the router can't see the image, and a vague "what's this?"
    must not be routed off-topic). Then the normal
    EXPLORER → WEB_SEARCH steps, so all of Part 2 applies.
  - Over the limit: 429 with `error_type: "image_limit"` and a
    friendly message ("You've used today's 5 image uploads 🙏
    They reset at midnight UTC. You can still ask in text.").
    The text question isn't answered in that case, so the user
    isn't charged a text answer they didn't expect.
  - `images_left` goes in the `done` / `whole` metadata so the
    page can show it.
- `ai_provider.py`: `generate`, `stream_generate` and the
  off-topic pair take `images=None`. With images, the user turn
  becomes `[{"type":"input_text",…}, {"type":"input_image",
  "image_url": <data URL>, "detail": "auto"}]`. Image tokens
  come back in `usage`, so token metering and daily token caps
  count them with no extra work.

### 3.3 Frontend (`templates/index.html`, `static/style.css`)

Production serves `templates/index.html`, not `frontend/`.

- An attach button in `.composer` (left of the send button)
  with a hidden `<input type="file" accept="image/png,image/jpeg,image/webp" multiple>`.
  Paste into the textarea and drag-drop onto the composer also
  work.
- Resize in the browser before upload: longest side 1024 px,
  re-encoded as JPEG 0.85 (WebP/PNG with transparency on a
  white background). Typical upload is 150–400 KB.
- A row of preview chips above the textarea, each with a remove
  ✕. Thumbnails are `data:` URLs (CSP already allows
  `img-src 'self' data:`, `security.py:47`).
- The sent message shows the thumbnails in the user bubble.
- "N image uploads left today" appears under the chips after
  the first use (from `images_left`).
- Small print gets one line: "Never upload a screenshot of a
  recovery phrase or private key."
- Phone layout: the button stays at least 44 px; chips scroll
  horizontally.
- Document the UI in `Task 16 - Vibrant Redesign.md` as a new
  numbered section when built.

### 3.4 Tests

- `tests/test_usage_control.py`: 5 allowed then refused per
  client; another client unaffected; reset at the day roll;
  claiming 3 when 4 are left fails as a whole.
- `tests/test_usage_hub.py`: `claim_images` through `call()`.
- `tests/test_ask_endpoint.py`: bad type, bad base64, a fake
  PNG header, a 4th image and an oversize image are each
  refused with 400; over the limit → 429 `image_limit`; an
  image question skips fast path, router and caches; the
  provider receives `input_image` parts; `/api/network-stats`
  still refuses a 1 MB body.
- `tests/test_security.py`: the raised body limit applies only
  to the two ask routes.

### 3.5 Known limits

- Per-IP counters live in the Durable Object's memory. If
  Cloudflare evicts it, today's per-IP counts reset (web
  searches behave the same today). The global daily token cap
  still bounds spend.
- People behind one shared IP (an office, mobile carrier NAT)
  share 5.
- The app can't detect a recovery phrase inside an image. The
  small print warns instead.

---

## Order of work

| Step | What | Size |
|------|------|------|
| 1 | 2.9 eval set first, so every fix is measured against today's answers | S |
| 2 | 2.1 router example + 2.2 prices + 2.6 source footer | S |
| 3 | 2.5 retrieval + golden questions | M |
| 4 | 2.3 deflection (prompt + code backstop) | M |
| 5 | 2.4 "can I" answers + instructions examples | S |
| 6 | 2.7 grounding check | S |
| 7 | 2.8 answer-model comparison on the eval set | S |
| 8 | Deploy part 1 (`cloudflare/deploy.sh`), re-check the three repro questions live | S |
| 9 | Part 3 backend, then frontend, then deploy | M |

Each step: `pytest`, then `live_eval.py --checks … --parallel 2`
before moving on.
