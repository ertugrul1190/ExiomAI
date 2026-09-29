# EXIOM AI — Live Data First: Query Handling

The client found four problems with how questions are
answered:

1. Mixed and reworded questions worked only when they were
   close to the examples in `What EXIOM AI Can Answer.md`.
2. "How many nodes have been added or removed in the last 24
   hours?" got "I can't answer that".
3. "Nodes by country" worked, but "nodes of Canada" said it
   couldn't fetch the figure, although it is on the Explorer.
4. Answers used technical terms, and often gave the source as
   plain text instead of a link.

What they asked for: the Explorer's live data first, then a
web search as a backup, and a gentle "couldn't find it" only
when both fail. Plain language, linked sources, and testing
across many question types.

Tests: 542 → 623. The 2 usage-page tests that fail locally
fail before and after this change, because the local `.env`
sets `EXIOM_USAGE_TOKEN`. Checked against the real model with
60 questions (63 answers, counting follow-ups), in both
transports (section 7).


## 1. What was actually wrong

A baseline run of 47 questions against the live Explorer and
the real model (before any change) found these causes:

| Symptom | Cause |
| --- | --- |
| "Average block time over the last **12 hours**" → the 24-hour figure. "Blocks in the last **hour**" → the 24-hour count. "Transactions in the last 24 hours" → blocks plus the all-time total. "Nodes in **Germany**" → all 15 countries. "Is that a lot?" → a bare number | The router's **direct answer**. When the router picked facts and called the question `direct_live_fact`, those facts went to the user as a template with no AI answer. At minimal reasoning its pick was often wrong or too broad, and nothing checked it. |
| "Nodes of Canada" sometimes failed; "and Germany?" after it failed | The answer model saw **only the facts the router picked**. A narrow pick, or a follow-up the router misread, left it without the number. |
| "Added or removed in 24 hours" → "can't answer" | Not read: the Explorer's node list shows each node's registration block, but only its header counts were read. Removals are **not published anywhere** on the Explorer. |
| "When is the next hard fork?" → "no announced date" | Not read: the dashboard shows "Upcoming HF v22 … block 219120 … Blocks Remaining … Estimated Activation". |
| No web search for "Who runs XEQMLabs?" and similar | A search ran only for price, listings, releases and news. |
| "Source: Official EXIOM Explorer." as plain text | The prompt and the teaching instructions gave the source as plain text. |
| "Sources: core.md, technical.md", later `https://docs.exiom.org/core.md` | Every knowledge section was labelled `SOURCE FILE: core.md`, so the model cited, and then invented URLs for, internal files. |
| "All-time high price of XEQM" → off-topic banter | Router error (it varies between identical calls). |


## 2. How a question is answered now (`app.py`)

Unchanged in front: request checks, the fast path (greetings,
identity, and the plainest one-fact phrasings, answered
free), usage control, ID lookups and the router.

After the router, the answer climbs up to three steps. Each
step adds the source the one before lacked:

| Step | The model gets | Starts here when |
| --- | --- | --- |
| `KNOWLEDGE_ONLY` | verified knowledge | a concept question: `explanation`, no facts picked, no value words |
| `EXPLORER` | + **every** live Explorer value | the router picked any fact, intent is `direct_live_fact`/`mixed`, scope is `mixed`, an ID was looked up, or the question has a value word ("how many", "current", "now", …) |
| `WEB_SEARCH` | + a web search | market questions (router flag or keyword backstop, as in Task 15) |

* A step that can't answer from what it has replies with
  only `[[LOOKUP]]`, and the next step runs. The user never
  sees the signal: on the stream, only the opening characters
  are held back, and only while they could still be the
  signal (`watch_for_lookup`).
* **The web-search step**: market questions search the listed
  sites (Task 15). Anything else searches the **open web**
  (`ai_provider.OPEN_WEB`, no domain filter), as the client
  allowed for the backup. The prompt: pages must name XEQM or
  XEQMLabs (the open web search once cited a different company
  called Exiom). Prefer XEQMLabs' own sites. For any figure the
  Explorer has, use the Explorer's, because pages can be old.
* **Last step**: no signal instruction. The prompt says to say
  kindly that it couldn't find the answer, share anything
  related, and link the Explorer. If the model sends the
  signal anyway, `NOT_FOUND_ANSWER` is sent.
* Search allowance used up: a market question still gets the
  web step without a search (`WEB SEARCH: UNAVAILABLE`, which
  points to CoinGecko). A backup search that can't run ends
  free with `NOT_FOUND_ANSWER`, because a paid call would have
  nothing to add. With search off in the provider, `EXPLORER`
  is the last step for everything but market questions.
* Backup searches draw on the same daily search allowance as
  price searches (Task 15: 20 per client, 500 in total).
* **The router's direct answer is gone.** Its fact pick now
  only chooses the starting step. Every router-picked number
  is worded by the model, which sees all the values. The fast
  path still answers its exact phrasings for free.
* **Scope backstops** (`query_router.py`): a question naming
  EXIOM/XEQM/XEQMLabs is never off-topic, and one naming
  network terms (nodes, staking, quorum, hard fork, …) is at
  least `mixed`. "How many calories in rice" stays off-topic.
* **Reuse**: only a first step's answer is reused, and its key
  includes every Explorer value it saw. A searched or
  escalated answer is never reused.

**Explorer data format.** All values as one compact line
each (`- Label: value`), about 670 tokens. It is sent only
from the `EXPLORER` step on, so concept questions don't pay
for it and their answers can still be reused.


## 3. New Explorer facts (`live_data.py`, `node_history.py`)

| Fact | Source |
| --- | --- |
| `nodes_registered_24h` — new nodes, last 24 hours | Node list page (already fetched in the background): rows whose registration block is within 1,440 blocks of the page's own height. Active and awaiting tables, e.g. "45 (1 still awaiting contributions)". If even the oldest row on page 1 is recent, "at least N". Checked against the page's own "Lifespan" column. |
| `node_count_change_24h`, `nodes_left_24h` | **Not on the Explorer.** `node_history.py` samples the registered count every 10 minutes. A day later: change = now − a day ago; left = new − change. Until then both say "not known yet …" in words. Left out, the model had filled the gap with "Removed: 0". |
| `next_hard_fork` | Dashboard "Upcoming HF …" box: version, name, block, blocks to go, estimated date |
| `nodes_by_region` | `/api/node_map` regions grouped by country ("United States: New York 48, Missouri 33, …"), so "what states?" works |
| `blocks_1h`, `blocks_12h`, `average_block_time_12h` | `/api/live_slow` (12-hour ones also from the dashboard) |

Relabelled to stop misreadings seen in testing: "Total
transactions (all time)", "Maximum contributors per node
(operator included)", "Mainnet version (current software
release)".

**On Workers** the count history must survive restarts, so
the usage hub keeps it in the Durable Object's SQL storage
(`node_counts` table). Every Explorer reading the Cron
Trigger stores passes through it (`UsageHub.put_reading`).
Under gunicorn it is kept in memory, per worker, and
restarts with the process: the change figures then need a
day of uptime again.

Fast-path phrases were added for every new registry fact, as
the Task 14 test requires.


## 4. Sources are always links

* Prompt: when Explorer values are used, end with
  `Source: [Official EXIOM Explorer](https://explorer.xeqmlabs.com/)`.
  Web pages are cited as `[site](URL)`, links only, and never
  made up. Explanations from knowledge need no source line,
  and file names are never a source. The teaching
  instructions' two examples now use the link form.
* **Backstops** (`source_additions`), in both transports:
  * An answer that used Explorer data and mentions the
    Explorer without linking it gets the linked "Source:
    Official EXIOM Explorer ↗" line under the answer (the
    existing `source` field).
  * A searched answer with no link gets up to three of the
    pages the provider cited, as `Sources: [site](url)`.
    `ai_provider.cited_sources` reads the response's
    `url_citation` notes, http(s) only.
* `retrieval.py` no longer labels sections with their file
  name. That is also a few tokens less per answer.


## 5. Plain language and tone

* A `PLAIN LANGUAGE` section: everyday words, short
  sentences, and any technical term explained in a few words.
  It keeps the existing TEACHING rules.
* A three-line reminder at the very end of the prompt, where
  a small model weighs instructions most: plain words, linked
  sources, no "the data you provided", no closing offer.
* **Closing offers** ("If you'd like, I can pull the block
  list…") promised things EXIOM AI can't do, whatever the
  prompt said. `answer_filters.py` drops a final paragraph
  that opens like an offer and promises or asks something.
  Source lines after it stay. It works mid-stream too: only
  a paragraph that opens like an offer is held back, and only
  until it's clear it isn't the last one. A test checks that
  every way of splitting the stream gives the same text as
  the whole answer.
* Xrypto is mentioned only when the user asks about EXIOM AI.
  One test answer had added a "P.S." about Xrypto.


## 6. Cost

* Concept questions: unchanged (router + one answer, and
  reuse still works).
* Questions the fast path doesn't catch, which the router
  used to answer directly for free, now cost one answer call.
  That is the price of correct answers: of the 8 baseline
  questions that took the router's direct route, 3 got a
  wrong figure and 3 an unhelpful dump of related values. An answer call is about 9–10K input
  tokens, mostly the cached static prompt, so well under
  $0.001.
* An escalation adds one call per step. In the two final
  runs (63 answers each) the model sent the signal 4 and 8
  times, and 4 and 5 answers reached the open web search
  (about $0.01 each, within the existing daily search
  allowance).

**Rate limit to know about.** The OpenAI project behind the
current key allows 200K tokens per minute for gpt-5-nano.
With ~10K tokens per answer call, that is about 15–20 AI
answers a minute across all users. Testing hit it at three
questions in parallel. Users past it get the existing "too
much attention, try again" message. The client's own key
(already planned, see the Cloudflare doc) sets their own
limit.


## 7. Testing

`live_eval.py` (new, manual, not deployed) asks every question
in `evals/questions.txt` against the live Explorer and the
real model. It prints the route, each answer call with its
search mode, and the answer. `--stream` uses the site's
transport.

Checked on 2026-09-29, both transports:

| Question | Before | After |
| --- | --- | --- |
| nodes of canada | sometimes "can't fetch" | "49 service nodes: Quebec 45, British Columbia 4" + link |
| … and germany? (follow-up) | "I don't have a Germany-specific count" | "70 … Bavaria 31, Baden-Württemberg 22, …" |
| added or removed in last 24 hours | "can't answer" | "45 new (1 still awaiting contributions); the number that left isn't known yet" |
| average block time, last 12 hours | the 24-hour figure | the 12-hour figure |
| blocks in the last hour | 24-hour count | 60 |
| transactions in the last 24 hours | "blocks + total" as the answer | says the Explorer doesn't publish it, after searching, and gives what it does show |
| when is the next hard fork | "no announced date" | HF v22 at block 219,120, blocks to go, estimated date |
| nodes still to upgrade | correct | correct (681 of 953 upgraded → 272) |
| what states? (after US) | "no breakdown" | the 8 states with counts |
| all-time high price of XEQM | off-topic banter | $0.04691 on 2026-06-01, linked to CoinGecko |
| who is the CEO of XEQMLabs | "not in verified docs" | backup search. Official pages name no CEO, so it says so gently |
| how many wallets hold XEQM | — | searches, then says kindly it isn't published, with related live figures |
| weather in Paris + how many nodes | sometimes off-topic | node count + link, a light line about the weather |
| what is staking / a service node | explanation | explanation, no stray numbers, no file names |

In both final runs, every answer that quoted the Explorer
carried a linked source, inline or through the backstop.

Still seen occasionally (a small model's variance, not
wiring):

* A searched answer can still prefer a stale page over the
  Explorer value (once: a 2.36% APY against the live 2.28%).
  The prompt now says so explicitly.
* An offer inside a paragraph, rather than as its own closing
  paragraph, is not removed.
* Some explanations keep a technical term ("Sybil") while
  explaining it.


## 8. Code review

Two-axis review (standards, spec) by parallel reviewers. The
repo documents no coding standards, so the standards axis
used the existing code's conventions plus the code-smell
baseline.

Fixed:

| Finding | Fix |
| --- | --- |
| A day of counts, but new nodes "at least N" or disagreeing: the facts said "counting started less than 24 hours ago", which was false | Separate `NOT_KNOWN` wording |
| The offer filter read "I can't fetch them" as an offer | `I can` no longer matches `I can't` / `I cannot` |
| Explorer figures without the word "Explorer" got no source | The linked source is added to any answer with a figure that saw Explorer values and doesn't link it |
| The Explorer's own link stopped the web sources being added | Only a link to another site counts as citing the web |
| Allowance used up on a backup search: a paid call just to say so | Ends free with `NOT_FOUND_ANSWER` |
| An answer written with nowhere further to look (search off) could be reused after search came back | Whether a further step existed is part of the reuse key |
| `` `[[LOOKUP]]` `` in backticks was not recognised; a signal mid-answer was shown | Backticks allowed; a stray signal is removed from a whole answer |
| `live_eval.py` mixed up the calls of a question asked on two lines | Calls are kept per line |
| Doc: "search off → EXPLORER is the last step" was wrong for market questions; gunicorn history is per worker | Corrected above |

Reviewed and kept:

* Market questions start at the search step, not the
  Explorer step. The Explorer has no price data, and the
  Explorer values go into that step's prompt anyway.
* The reuse key includes every Explorer value, so answers at
  the Explorer step are reused only while the values stay the
  same (about a minute, because the block height changes).
  Correct over cheap.
* The `web_search` values (`False`/`True`/`"open"`) and
  plain-string states follow the codebase's convention: none
  of it uses enums (as in Task 14).
* `_nodes_by_region` repeats `_nodes_by_country`'s spelling
  merge. Merging them would change a fact Task 14 tested.


## 9. Not done

* **Transactions in the last 24 hours.** The Explorer doesn't
  publish it. It could be counted like the node change: sample
  "Total transactions (all time)" and subtract. Left out to
  keep this change focused.
* **Nodes that left** is only exact for nodes that were
  registered a day ago. One that joined and left within the
  day is in neither number.
* **Deploy.** Not deployed. Use `cloudflare/deploy.sh` as
  usual. The new `node_counts` table is created on first use.
  The node change figures start 24 hours after the Durable
  Object first stores a reading.


## 10. Follow-up: the price came from a stale page

**Reported.** The owner, the client and a user all asked "What
is the price of xeqm" and got the same answer: $0.01960, up
6.8%. CoinGecko showed it down about 8% at the time.

**Cause.** The price came from the provider's `web_search`
tool. That tool reads the search index's copy of the CoinGecko
page, which can be hours old. Everyone got the same old copy.
Searched answers were never cached, so the answer cache was
not the cause.

**Fix (`market_data.py`).** The price is now read from a
tracker's API when the question is asked:

* CoinGecko `simple/price` (`xeqm-labs`) first, then
  CoinPaprika `tickers/xeqm-xeqm-labs`. CoinGecko's keyless
  API often answers 403 or 429 from shared IPs like
  Cloudflare's. CoinPaprika needs no key.
* Optional `EXIOM_COINGECKO_API_KEY` (a free CoinGecko "Demo"
  key) is sent as `x-cg-demo-api-key`. Set it with
  `npx wrangler secret put EXIOM_COINGECKO_API_KEY`.
* Then NonKYC `api/v2/market/getbysymbol/XEQM_USDT`, the
  exchange's own XEQM/USDT market. No key. Its price is in
  USDT and its time is the last trade, so the prompt says
  "(USDT)" and "Last trade: N min ago". A paused or inactive
  market is not used.
* A quote is reused for 60 s. A tracker that fails is skipped
  for 5 minutes. With no quote, the old web search still runs.

**Rate limits (checked 2026-09-29, 40-request bursts):**

| Source | Key | Limit seen | Burst result |
|---|---|---|---|
| CoinGecko | none | 403/429 from this machine after a few calls; likely the same from Cloudflare's shared IPs | blocked |
| CoinPaprika | none | `ratelimit-limit: 20000` per period, per IP. Its edge cache holds a ticker 30 s, and cached hits don't count | 40 × 200, quota unchanged |
| NonKYC | none | no rate-limit headers | 40 × 200 |

Our own load is small. Only price and search questions fetch,
at most once a minute per Worker instance. So 20,000 calls
per period is far more than we need. The open question is how
much of that per-IP quota other Cloudflare customers use up.
That's why NonKYC is behind it, and the web search behind
that.

**In `app.py`:**

* Any question that would search fetches the quote. It goes
  into the prompt as `MARKET DATA (live …)`, with rules that it
  beats any page or memory for price, 24h change, volume and
  market cap.
* A question that only asks the price (`asks_for_price`, and
  not `asks_beyond_price`: exchanges, news, releases,
  all-time high, predictions) runs no search at all
  (`WEB_SEARCH: NOT NEEDED`). It uses no search allowance, and
  it is cheaper and faster.
* Movement questions ("is xeqm up today?") count as price
  questions, even when the router doesn't flag them.

**Tested.** `tests/test_market_data.py` covers parsing,
fallback, caching, backoff and formatting. New tests in
`tests/test_ask_endpoint.py` cover the live-price path. Full
suite: 641 passed. The only 2 failures come from the local
`.env` usage token (`test_usage_*_is_off_without_a_token`),
and they fail the same way without this change. A live local
run answered "$0.02215, down 8.2% over the last 24 hours",
from CoinPaprika, matching the tracker.

**Source order, revised (owner's request): CoinGecko is last.**
The order is now NonKYC (real trades on the exchange), then
CoinPaprika, then CoinGecko, then the web search. The owner
doesn't trust CoinGecko's figures to be fresh, so a
CoinGecko quote is marked `last_resort`:

* The prompt calls it a backup source and tells the model
  never to call it live.
* The code adds `STALE_PRICE_NOTE` under the answer: "⚠️ This
  price comes from a backup source and may be out of date.
  For the live price, check NonKYC." The code adds it, not
  the model, so the model can't leave it out. It works the
  same streamed or whole.
* A price answered by the web search (no tracker answered)
  gets the same note. A "couldn't find it" reply and
  searches that aren't about the price don't.

Tests: 648 passed. The same 2 `.env` usage-token failures
remain.
