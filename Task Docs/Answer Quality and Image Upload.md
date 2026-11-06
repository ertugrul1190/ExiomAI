# EXIOM AI — Answer Quality and Image Upload

What was built on 6 November 2026, following
`Answer Quality and Image Upload - Plan.md`. §1–5 cover
Parts 1 and 2 (answer quality); §6 covers Part 3 (image
upload).

Not deployed yet: deploy with `cloudflare/deploy.sh` (plan
step 8), then re-ask the three repro questions live and send
one image from a phone.


## 1. The three repros, after

| Repro (plan §1) | Before | After (real model, `live_eval.py --checks`) |
| --- | --- | --- |
| "whats the coin price" | $0.0196 from a web search's stale CoinGecko copy | the live NonKYC price from the tracker API, no search, no Explorer footer |
| "what does nonkyc and coinpaprika say" | "I can guide you to the exact pages" | each tracker's own live figures, side by side |
| "can i stake 60k coins" | "Short answer: not by itself", Explorer footer, plain-text sources | "Yes, as a contributor to a pool node": options, steps, risks, linked sources. Reliably so with `gpt-5-mini` (§2.8), not yet on the default nano |


## 2. What changed

### 2.1 Router: no more "explanation" default

- The OUTPUT example is now a placeholder,
  `{"scope":"<scope>","intent":"<intent>","facts":[<keys>],"search":<true|false>}`,
  so a router at minimal reasoning has no real intent to echo.
- New WORKED EXAMPLES section: coin price, tracker names,
  "and now?", "can I stake 60k?", "I have 50000 xeqm",
  "what does market cap mean?".
- Measured on `evals/questions.txt` (nano router): 28
  direct_live_fact, 22 explanation, 5 mixed, 4 general. It
  was all "explanation".

### 2.2 Prices: the live price whenever one is wanted

- `app.py` no longer reads the router's intent to decide on a
  price. `query_router.asks_what_it_means()` (mean, define,
  explain, "how is … calculated", "what is a market cap")
  decides it from the wording.
- `PRICE_PATTERN` knows the trackers: nonkyc, coinpaprika,
  coingecko, coinmarketcap/cmc, livecoinwatch, "trackers".
- "worth" no longer means price in "is it worth running a
  node?" or "is staking worth it". Before, only the
  explanation guard kept those away from market data.
- Named trackers get their own quote:
  `MarketData.get_quotes(["nonkyc", "coinpaprika"])`, cached
  per tracker. "What does CoinPaprika say?" is answered with
  CoinPaprika's figures. Other questions still get the
  freshest tracker (`get_quote()`).
- Found in the live eval: the router twice sent "what does
  nonkyc and coinpaprika say" and "whats the coin price"
  off-topic. `query_router.names_xeqm_price()` (a tracker
  name, "coin price", "price of the coin") now makes an
  "unrelated" route relevant, the same way `names_exiom()`
  already did.

### 2.3 Never "go look it up yourself"

- Prompt: `LOOKUP_SECTION` no longer exempts concepts. It now
  asks for `[[LOOKUP]]` whenever a figure, price, date,
  release, person or fact is missing, and forbids sending the
  user to a site. `WEB_SEARCH_RULES` rule 5 and
  `WEB_SEARCH_UNAVAILABLE_SECTION` say: what was found, the
  closest verified facts, then at most one link.
- `REMINDER` gets a deflection line. On a step that can look
  further it says "ask for it with [[LOOKUP]]". On the last
  step it only says "never tell the user to search for it",
  so the model isn't asked for a signal that would turn into
  "not found".
- Code backstop: `query_router.is_deflection()` checks the
  answer's first 160 characters (`app.DEFLECTION_WINDOW`)
  for "I don't have … in this chat / right now", "check the
  price on", "visit … for the latest", "I can guide you to"
  and "search for … on their site".
  - At a step that can look further, a deflection counts as
    `[[LOOKUP]]`: the next step runs.
  - At the last step, a deflection stays only if a real web
    search ran. Otherwise the answer is `NOT_FOUND_ANSWER`.
  - Streaming: `watch_for_lookup(…, hold_opening=True)` holds
    the opening 160 characters, only on those steps (about
    0.3 s of first-token latency). Both transports check the
    same 160 characters, so they give the same answer.

### 2.4 "Can I …?" answers

- `knowledge/instructions.md`: new **CAN I …? QUESTIONS**
  section with its shape (direct answer, Your options, How to
  do it, Good to know, Sources), today's 60k answer as BAD and
  the right one as GOOD.
- ANSWER LENGTH, in `instructions.md` and the static prompt:
  "1-2 sentences" now applies to "a single current value"
  only, and a "can I…?" question is never a bare yes or no.
- `test_every_number_in_the_instructions_is_in_the_knowledge`:
  every figure in `instructions.md` must appear in the
  knowledge files. The only exceptions are the example
  Explorer counts (933, 932) and the user amounts in the
  examples (60k, 120k).

### 2.5 Retrieval: rarity-weighted scoring (BM25)

`retrieval.py`. No API call, deterministic.

- **BM25**: a word or concept counts more the fewer sections
  contain it. Title matches count triple
  (`TITLE_WEIGHT`), a concept counts as two words
  (`CONCEPT_WEIGHT`), and section length is normalised
  (k1 1.2, b 0.75). Statistics are computed from the
  sections passed in, so a raw section list and the startup
  index still rank the same.
- **Stemmer**: a final "e" is dropped after the suffix, so
  stake/stakes/staked/staking are all `stak`.
- **Synonyms**: coin, token → xeqm.
- **Amounts** (`STAKE_AMOUNT`): "60k", "60,000", "150k xeqm",
  "50000 coins" add the concept "stake amount". Sections get
  it by naming 200,000/100,000/10,000 XEQM. A bare number
  ("9231", "block 236920") never counts.
- **Tie-break**: on equal scores, more title words matched
  wins. File order only comes after that.
- Results: ties at the 6th place fell from 74 of 92 eval
  questions to 0 of 92 (a test now keeps it at 0). All 66
  existing golden questions pass. The 6 staking questions
  ("can i stake 60k coins", "i have 50000 xeqm what can i
  do", "can i run a node with 120k", "minimum to contribute",
  "how do i join a pool node", "whats the minimum to stake")
  each retrieve both staking sections.
- Embeddings were not needed.

### 2.6 Sources: always links, never the wrong one

`source_additions(answer, evidence, web_sources)`, where
`evidence` is what the answer was given: Explorer text,
knowledge text, market text.

- **Explorer footer** only when the answer quotes the
  Explorer:
  - one of its figures that the Explorer alone supplied (a
    figure the knowledge or market data also has may have
    come from there), or
  - an unlinked "Source: … Explorer".

  Never when the answer cites a page that isn't a knowledge
  source or the Explorer (a web page, a tracker). This
  replaces "any digit".
- **Plain-text titles become links.** In a source line
  ("Sources:", "**Source:**", "📚 Sources:"), a known title
  becomes its link. Titles come from the knowledge files'
  Source links plus `sources.json` names
  (`app.SOURCE_TITLES`).
  - Non-streaming: `link_source_lines`.
  - Streaming: `stream_linking_source_lines`. It holds back
    only a line that opens like a source line, and its output
    is identical to the non-streaming version (tested at
    several chunk sizes).
- **Missing citation**: when an answer cites nothing,
  `knowledge_links()` adds "Sources:" from the retrieved
  sections it drew on, at most two. A section counts when it
  holds one of the answer's `commands` or a figure that is
  100 or over or has decimals, and that the Explorer didn't
  also supply. Smaller figures ("50 nodes") are too common to
  tell, so they add nothing rather than a wrong source.

### 2.7 Grounding check (`grounding.py`)

- `unsupported_numbers(answer, context, question)` returns
  the answer's numbers that nothing supplied contains.
  - Forms are normalised (100k = 100,000 = 100000; -8.2% =
    8.2).
  - A rounded price counts ($0.0203 for $0.02029).
  - So does a sum or difference of the user's own amount and
    a supplied figure (the other 80,000 for "120k").
  - Single-digit integers and versions (v1.1.2) are ignored.
- Production log, a monitor only: `EXIOM grounding:
  route=… unsupported_numbers=N`. It gives the count only,
  never the question (Task 13). Searched answers are skipped,
  since their pages are never seen here.
- Seen in the full eval: derived figures (blocks remaining,
  a country's share of nodes). Seen with nano: `stake
  <pubkey> 120000000000000`, an invented amount in atomic
  units. That is the kind of error it exists to surface.

### 2.8 Answer model

- New `EXIOM_ANSWER_MODEL`, for answers only. The router and
  off-topic banter stay on `gpt-5-nano`. Metering records the
  model each call used. `MODEL_RATES["gpt-5-mini"]` = $0.25 /
  $0.025 cached / $2.00 per 1M tokens (checked on OpenAI's
  pricing page, 6 Nov 2026).
- **The default stays `gpt-5-nano`.** Results on
  `evals/answer_checks.json`:

  | Model | Runs | Passed |
  | --- | --- | --- |
  | gpt-5-nano | 3 | 5/8, 4/8, 7/8 |
  | gpt-5-mini | 6 | 5/8, 8/8, 7/8, 8/8, 8/8, 8/8 |

  Mini's misses were the router and eval-check issues fixed
  in §2.2 and §2.9. The last three mini runs (JSON, stream,
  JSON after the review fixes) passed 8/8. Nano still opens "can I…?" answers with "Short
  answer: no", and invented the atomic-unit stake above.
- **Decision (6 Nov 2026): answers stay on gpt-5-nano.** The
  client pays the OpenAI bill, so switching models is their
  call. `EXIOM_ANSWER_MODEL` is set nowhere (`.env`,
  wrangler). Setting `EXIOM_ANSWER_MODEL=gpt-5-mini` switches
  answers over with no code change.
- **Measured cost** on the 59 questions of
  `evals/questions.txt`, from the app's cost meter:

  | | gpt-5-nano | gpt-5-mini |
  | --- | --- | --- |
  | Tokens (router + answer) | $0.023 | $0.120 |
  | Web searches ($0.01 each) | $0.10 (10) | $0.14 (14) |
  | Per answer, all in | ≈ $0.0021 | ≈ $0.0044 |

  - 50 / 100 / 200 answers a day cost $0.11 / $0.21 / $0.42
    on nano, and $0.22 / $0.44 / $0.88 on mini.
  - At 50–100 answers a day, that is about $5 a month on nano
    and about $10 on mini.
  - Worst case at the daily caps: the 20M-token cap is about
    $0.75 on nano and $3.60 on mini, plus up to $5 for the
    500-search cap. That makes about $5.75 a day on nano and
    $8.60 on mini.
  - The eval set has more price and market questions than
    real traffic probably does, so it overstates searches.

### 2.9 Answer eval set

- `evals/answer_checks.json`: 8 questions with
  `must_contain`, `must_match`, `must_not_contain` and
  `must_not_start` checks.
  - Zero unsupported numbers is required too, unless the
    check says `"grounded": false` (illustrative arithmetic
    in a concept answer).
  - `only_if_tracker` applies `must_contain` only while that
    tracker is the live source.
- `python live_eval.py --checks evals/answer_checks.json
  --parallel 2 [--stream]` prints PASS/FAIL and the grounding
  count per answer, and exits 1 on any failure. Plain runs
  print the grounding count too.


## 3. Tests changed on purpose

- `test_router_prompt_asks_for_the_search_flag`: checks the
  new placeholder, `"search":<true|false>`.
- `test_explorer_figures_without_naming_it_still_get_the_source`:
  now quotes a real Explorer value. "Canada has 49 nodes"
  with no 49 in the Explorer data no longer gets the footer.
  That is §2.6.
- `test_streamed_answer_arrives_as_deltas`,
  `test_a_failure_after_the_first_token_arrives_in_band` and
  the concurrency stream tests: their fake answers start
  with an opening longer than `DEFLECTION_WINDOW`. A 26-
  character answer is now held whole, by design.

`pytest`: 877 passed. Run it with `EXIOM_USAGE_TOKEN=` set
empty: a token in the local `.env` makes two usage-page tests
fail, before and after this work.


## 4. Code review

A two-axis review (standards, spec) ran after the build. The
fixes:

- Tracker words matched unrelated questions: "whats the best
  fitness tracker", "is the cmc api free". The pattern is now
  "the trackers" / "price trackers" only, and the off-topic
  backstop never uses bare "cmc".
- The grounding check took the whole prompt as evidence, so
  a figure copied from an instructions example (933, 60k)
  passed. It now reads only the request's material plus the
  conflict notes (`app.grounding_inputs`), and only the
  user's own turns count as "their amounts". Earlier
  assistant answers count as neither. A lowercase "30m" is
  minutes, not 30 million.
- Smaller cleanups:
  - `source_links()` replaces three copies of the
    Source-line loop.
  - `evidence` is built once per step.
  - `retrieval.SECTION_SEPARATOR` is shared with
    `knowledge_links`.
  - `_link_line` is shared by both linking functions.
  - `concept` is renamed `asks_meaning`.

Kept as they are, on purpose:

- **"A real search ran" means a search was requested.**
  Searches are requested with `tool_choice: "required"`, so a
  requested search always runs.
- **Only the first 160 characters are checked for a
  deflection,** in both transports, so the two give the same
  answer. A deflection later in an answer is left to the
  prompt rules.
- **A named tracker that fails falls back to the freshest
  tracker.** Its figures are labelled with their real
  source.
- **Not refactored:** tracker names live in both
  `query_router` and `market_data`. Only three exist.


## 5. Files

| File | Change |
| --- | --- |
| `query_router.py` | placeholder example + worked examples; `asks_what_it_means`, `named_trackers`, `names_xeqm_price`, `is_deflection`; tracker names and "worth it" in the patterns |
| `app.py` | price decision; named-tracker quotes; prompt sections; deflection diversion; `source_additions` by evidence; `knowledge_links`; source-title linking; grounding log |
| `retrieval.py` | BM25, stemmer, synonyms, stake amounts, tie-break |
| `market_data.py` | per-tracker cache, `get_quotes(names)` |
| `answer_filters.py` | `link_source_lines`, `stream_linking_source_lines` |
| `grounding.py` | new: the grounding check |
| `ai_provider.py`, `usage_control.py`, `.env.example` | `EXIOM_ANSWER_MODEL`, gpt-5-mini rates |
| `knowledge/instructions.md` | CAN I …? QUESTIONS, ANSWER LENGTH |
| `live_eval.py`, `evals/answer_checks.json` | `--checks`, grounding count |


## 6. Image upload (plan Part 3)

PNG, JPEG or WebP, up to 3 per message, **5 per visitor IP
per UTC day** (`EXIOM_CLIENT_IMAGES_PER_DAY`). An image is
used for that one answer and never stored, logged or cached.
Follow-ups carry `[image]` in its place.

### 6.1 Backend

- **Allowance** (`usage_control.py`): `claim_images(client,
  count)` → `(allowed, left)`. All or nothing: 3 with 2 left
  takes none. It is claimed after the usage check passes and
  before any AI call, like a web search, so a failed call
  still counts. A request the usage check refuses uses no
  images. The limit shows in `snapshot()`.
- **Workers**: a `claim_images` op on the hub
  (`usage_hub.py`). `RemoteUsageController.claim_images`
  returns `(False, None)` when the hub can't be reached. The
  app then refuses with the ordinary capacity message, not
  "you've used today's 5".
- **Validation** (`app.read_images`, inside
  `read_ask_request`, before anything else sees the request):
  - a list of at most 3 strings;
  - each `data:image/(png|jpeg|webp);base64,…`, strictly
    decoded;
  - at most 1.5 MiB decoded, checked on the string length
    before decoding;
  - the first bytes must match the declared type.

  The 400 error types are `invalid_image`, `too_many_images`
  and `image_too_large`. An empty question with images
  becomes "What's in this image?". A pasted recovery phrase
  is still refused when images come with it.
- **Body limit**: only `/ask` and `/ask/stream` take
  `MAX_ASK_REQUEST_BYTES`, set in `guard_request` before
  anything reads the body. That is 256 KB plus three
  largest-size images as base64, about 6.5 MB. The plan's
  "about 5 MB" would turn three valid 1.5 MB images into a
  413. `guard_request` now also refuses any declared
  `Content-Length` over the route's limit up front. Before
  this, a route that never reads its body (`GET
  /api/network-stats`) accepted 1 MB.
- **Pipeline**: a question with images skips:
  - the fast path ("hi" with an image is a real question);
  - the router (it can't see the image): the route is fixed
    to `scope: mixed`, `intent: general`;
  - both caches.

  It then runs the normal EXPLORER → WEB_SEARCH steps, so
  all of Part 2 applies, and the images go with every step.
  The grounding check is skipped for these answers, because
  numbers read off an image aren't in any text context.
- **Over the limit**: 429 with `error_type: "image_limit"`,
  `images_left`, and `Retry-After` set to midnight UTC. The
  text isn't answered. The message:
  - with none left: "You've used today's 5 image uploads 🙏
    They reset at midnight UTC. You can still ask in text.";
  - with too few left: "You have N image uploads left today
    🙏 Please attach fewer, or ask in text."
- **`images_left`** is in the `done` / `whole` metadata of
  image answers, and only theirs.
- **Provider** (`ai_provider.user_turn`): with images, the
  user turn is `input_text` followed by `input_image` parts
  with `detail: "auto"`. `generate`, `stream_generate` and
  the off-topic pair take `images=None`. Image tokens come
  back in `usage`, so metering and the token caps count them.

### 6.2 Frontend

See Task 16, §16.17.

### 6.3 Verified

- `pytest`: 916 passed, with `EXIOM_USAGE_TOKEN=` empty (see
  §3).
- **End to end against the real Flask app**, with a stub
  provider so the client's key wasn't spent:
  - two images, then two more, then one: `images_left` was
    3, then 1, then 0;
  - two more after that: 429 "You have 1 image upload
    left…";
  - with none left: 429 "You've used today's 5…";
  - `GET /api/network-stats` with a 1 MB body: 413;
  - the server log contains no image data.
- Not yet tried against the real model: the first live check
  is part of the deploy step above.

### 6.4 Code review

A two-axis review (standards, spec) ran after the build. It
found every 3.1–3.4 item present. The fixes:

- **Chip order**: resized images were added as each one
  finished, so the order could change. They now keep the
  order they were picked in.
- **Hub outage**: it read "you've used today's 5". It now
  gets the capacity message (`(False, None)`, §6.1).
- **Image refusal**: the question was lost on an image
  refusal, although the message says "you can still ask in
  text". It now goes back in the box.
- **Tidy-ups**:
  - `image_error(answer, error_type)` now takes its
    arguments in payload order.
  - The "too large" refusal is built once.
  - Docstring on `is_image_of_type`.

Kept as they are, on purpose:

- **`IMAGES_PER_DAY` in `app.py`** reads the same variable as
  the hub, only for the message wording. The Worker and its
  Durable Object share one set of vars.
- **No global image ceiling**: the global daily token cap
  already bounds spend.
- **The left-count shows only while images are attached**
  ("under the chips"), so the composer gets no permanent
  extra line.
- **The plan's "claiming 3 when 4 are left fails"** is
  impossible as written. The test claims 3 with 2 left.

### 6.5 Known limits (plan §3.5)

- **Per-IP counters live in the Durable Object's memory**:
  if the object is evicted, today's counts reset.
- **One shared IP shares 5**: an office, or a carrier's NAT.
- **No recovery-phrase detection inside an image**: the
  small print warns instead.
- **Each extra answer step re-sends the images**: a search
  after an Explorer `[[LOOKUP]]` pays their tokens twice.
  The token caps count both.

### 6.6 Files

| File | Change |
| --- | --- |
| `usage_control.py` | `client_images_per_day`, `claim_images`, `images_today`, snapshot limit |
| `usage_hub.py`, `remote_usage.py` | `claim_images` op; refuses with no count when the hub is unreachable |
| `ai_provider.py` | `user_turn`; `images=None` on the four answer calls |
| `app.py` | `read_images`, the ask-only body limit, the declared-length check, `image_limit_payload`, image route through the pipeline |
| `templates/index.html`, `static/style.css` | attach button, chips, resize, paste and drop, thumbnails, left-count, small-print line (Task 16, §16.17) |
| `.env.example` | `EXIOM_CLIENT_IMAGES_PER_DAY` |
| tests | `test_usage_control`, `test_usage_hub`, `test_ai_provider`, `test_ask_endpoint`, `test_security` |
