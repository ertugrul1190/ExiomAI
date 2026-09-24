# EXIOM AI — Explorer Data

Task 14. Most of what the Official EXIOM Explorer
(`explorer.xeqmlabs.com`) shows is now answerable: network-wide
values, and any service node, block or transaction a question
names by ID. Each value comes from the Explorer's JSON where
it has any, with the page's text as the fallback. The new
piece is `explorer_lookup.py`; `live_data.py` was reworked.
Tests are in `tests/test_live_data.py`,
`tests/test_explorer_lookup.py` and `tests/test_ask_endpoint.py`,
against real Explorer pages in `tests/fixtures/explorer/`.


## 14.1 What the Explorer offers

Every page was read, and every JSON endpoint the Explorer's
own pages call was found:

| Source | Kind | Used for |
| --- | --- | --- |
| `/api/live_slow` | JSON | Height, node counts (active, inactive, registered, awaiting, open pool), swarms, supply (total, locked, unlocked, % locked), staking requirement, SN reward and 24 h rewards, average block time (1 h, 24 h, 7 d), blocks and hashrate over 24 h, database size |
| `/api/networkinfo` | JSON | Height, hard fork, min operator contribution, max contributors, target block time, total transactions, mempool count |
| `/api/node_map` | JSON | Country count, nodes by country |
| `/` dashboard | HTML | Fallback for everything it shows; APY, daily and annual reward per node, mainnet version (these exist nowhere else) |
| `/txpool` | HTML | Mempool size |
| `/service_nodes` | HTML | Nodes on the current release; swarm fallback |
| `/quorums` | HTML | Testing, Pulse, checkpoint and Blink quorum counts |
| `/sn/<key>/1` | HTML with the daemon's raw JSON embedded | One service node |
| `/block/<height or hash>/1` | HTML with raw JSON embedded | One block |
| `/tx/<hash>` | HTML only | One transaction |

There is no JSON feed for nodes, blocks, transactions, quorums
or the mempool (`/api/service_nodes`, `/api/mempool`… are 404;
`/api/block/…` and `/tx/<hash>/1` redirect to the dashboard).
The feeds are undocumented and can change without notice,
which is why every fact the pages also show keeps a page
fallback.

Registry: 16 facts before, 39 now. The router needed no
change: it reads the registry. The fast path gained phrases
for the new facts (14.7).


## 14.2 Source layer and fallback (`live_data.py`)

* Each fact lists its sources in order: feed extractors
  (`"api"`), then page `"patterns"` on a named page (`"page"`,
  default the dashboard). **A fact falls back on its own**: a
  renamed feed field moves only that fact to the page.
* A feed counts only if it parses as JSON **and** reports
  `status: OK`. A value of the wrong type (a string, a bool
  where a number belongs) is rejected, and the fact falls back.
* Feed values are formatted the way the page shows them
  (`184,400,000`, `59s` / `1m 00s`, `16.66 kH/s`), so an answer
  reads the same from either source. Supply is atomic ÷ 10⁹,
  confirmed against the staking requirement (200,000 XEQM).
* Total and circulating supply are one figure on this
  Explorer: `/api/emission` gives circulating supply equal to
  total emission, and its tokenomics note says there are no
  burns. The "Circulating Supply 276,786,542" in its Tokenomics
  box is the fixed genesis premint, not a live value.
* All foreground sources (3 feeds, dashboard, mempool page)
  are fetched **in parallel**, each on its own Session, within
  an 8 s budget. A cold reading costs about one request
  (≈2 s), and a down Explorer costs one timeout, not five.
* The quorum and node-list pages (≈0.5 MB and 0.17 MB) are
  fetched **in the background**, never on a question's path.
  A copy is used for 120 s, renewal starts at 60 s, and a copy
  is dropped, never reused, when a fetch fails. Their facts
  are missing only until the first copy arrives after start-up.
* Nothing recognisable in any source → `unavailable`. Before,
  that case reported "available" with no facts.
* A source that breaks or recovers is logged **once** per
  change (`live_data` logger), not every 30 s.

Verified against the live Explorer with every feed pointed at
a dead URL: 27 of the dashboard's facts still came from the
page. The rest (inactive and registered nodes, countries,
nodes by country, total transactions) are not rendered as
text on any page, so they have no fallback and go missing
rather than being guessed.

**Bug fixed.** The connection state was always
`disconnected`. The dashboard carries its "Disconnected…"
banner at all times and hides it while the daemon is up, and
the old check matched the banner's text. It now reads whether
the banner is hidden.


## 14.3 Lookups by ID (`explorer_lookup.py`)

* `find_ids` parses the question for 64-hex IDs and block
  heights (`block 203140`, `block #5`, `#203140`). A number
  followed by a unit is not a height ("block height 2 days
  ago"), and `#` needs three digits ("the #1 coin"). At most
  three IDs per question, each kept as its own fact.
* A 64-hex ID says nothing about what it is, so it is tried as
  a node, then a transaction, then a block.
* **Nodes and blocks**: the embedded raw JSON is read first,
  and must be for the ID asked (a payload for another node is
  rejected). The page labels are the fallback. **Transactions**:
  page labels only.
* **Allowlist.** The raw node payload includes the node's IP,
  ports and key images. The Explorer's own UI promises not to
  expose IPs. Only named fields are read, so none of these can
  reach an answer (tested). The IP in the committed fixture was
  replaced with a documentation address (203.0.113.7).
* Three outcomes: found; **not found** (the Explorer said so);
  **could not be read / reached**. A page the code no longer
  recognises is never reported as "does not exist".
* A label that is missing is left out, never guessed: a
  transaction page without "In block" is not reported as
  unconfirmed.
* URLs are built only from validated IDs. Redirects are not
  followed. One question shares an 8 s budget, and no request
  may run past it (each timeout is capped at the time left).
  Results are cached 30 s (failures 10 s), bounded at 256
  entries. A lookup that throws costs the answer its lookup,
  never the answer.

**In `/ask`**: IDs are parsed first. A question naming one
skips the fast path, which knows only network-wide values:
"block height of block N" must not be answered with the chain
height. The fetch happens **after usage control**, so a
refused caller cannot make the server fetch pages. Results
join the selected facts, so they reach the prompt and the
answer-reuse key: a changed value is never served from cache.
A question naming an ID is never routed off-topic, and never
short-circuited by the direct-fact route.


## 14.4 Not done

* **Facts with no fallback.** Inactive and registered nodes,
  countries, nodes by country and total transactions exist
  only in the feeds. If a feed changes they go missing (never
  guessed) until the code is updated.
* **Quorum members and the pending-transaction list.** Only
  the quorum counts and mempool count and size are read. A
  node's own lookup gives its next uptime test. The mempool
  was empty throughout this task, so a pending-transaction row
  could not be seen to write a parser against it.
* **The full service-node list.** It is about 10 pages of
  ~100 rows, with no feed. Network-wide counts, release
  adoption and single-node lookups cover the questions seen so
  far. Crawling the list belongs in a background job if a real
  need appears.
* **Follow-ups without the ID.** "What about its fee?" after
  asking about a node does not look the node up again: IDs are
  read from the current question only.
* The Explorer's node map lists both "Turkey" and "Türkiye".
  That is their data, passed through as-is.


## 14.5 Operator checklist

* Watch the `live_data` logger for "Explorer source … is
  unusable". It means the Explorer changed a feed or page, and
  the affected facts are on their fallback, or gone.
* `tests/fixtures/explorer/` holds real pages. When the
  Explorer is redesigned, refresh them and rerun the tests.


## 14.6 Code review

Two-axis review (standards and spec), run as parallel
reviewers. The repo documents no coding standards, so the
standards axis used the existing code's conventions plus the
code-smell baseline. The spec axis used the task requests and
checked claims against the live Explorer.

Fixed:

| Finding | Fix |
| --- | --- |
| Sub-minute block times ("59s" on the live page) matched neither the fallback patterns nor the feed format ("0m 59s") | Patterns accept both forms; the feed formatter writes what the page writes |
| Transaction page without "In block" was reported "not yet in a block", a wrong fact | Left out instead |
| An absurd timestamp raised `OSError`/`OverflowError`, which escaped the fallback | Turned into `ValueError`, so the lookup falls back to the page |
| A lookup that threw would abort the answer | Caught in `/ask`; the answer goes ahead without it |
| A hex ID's three attempts could overrun the 8 s budget by a full timeout | Each timeout is capped at the time left |
| Banner check matched `aria-hidden="false"` as hidden | Reads the `hidden` attribute, the `is-hidden` class or `display:none` only |
| Fact keys used 16 hex characters; two IDs sharing them collided | Full ID in the key |
| Background page start was check-then-act across two lock holds; `_pages_failed` read unlocked | One lock hold; locked read |
| `explorer_lookup.py` imported underscore-private helpers | `as_number`, `format_count`, `format_xeqm`, `format_decimal` are public |
| Dead `&lsaquo;` regex branch; `raise` without `from`; inline `__import__` in a test; a duplicated comment | Cleaned up |

Reviewed and kept:

* Total and circulating supply read the same field: that is
  the Explorer's own data (14.2).
* Shared constants and fakes between `live_data.py` and
  `explorer_lookup.py`, and between their tests. The two
  modules have different concurrency models (a locked reading
  versus per-question lookups), and merging them would couple
  them for little gain.
* String outcomes ("found", "absent", "unreadable") and `via`
  values: kept as plain strings, matching the rest of the
  codebase. None of it has enums.

Tests: 342 → 405, all passing.


## 14.7 Fast path for the new facts

Every registry fact now has phrases in `fast_path.py`, so the
plainest question for it ("how many pulse quorums are there",
"current mempool size") is answered from the Explorer with no
AI call. A test fails if a future registry fact has no phrase.

The existing rules are unchanged: a value cue ("how many",
"current", "now"…) is required, and two facts, extra words,
pronouns or an explanation cue ("what is a pulse quorum") send
the question to the AI router. Max contributors and target
block time join the value-cue exemptions, alongside the
staking requirement: they are named thresholds.

Left to the router on purpose, because they are ambiguous:

* "quorums" (four kinds)
* "block time" (target or measured average)
* "total nodes" (the dashboard means active nodes, the feed
  means registered ones)
* the singular "pulse quorum" (usually a concept question)

Tests: 405 → 441.


## 14.8 Nodes by country, fixed from a real chat

A test chat showed three faults:

* **"Turkey 30 … Türkiye 4".** The feed spells some countries
  two ways. Regions are now grouped by `country_code` and
  shown under the spelling with the most nodes, so the list
  agrees with the "countries" count (14, not 15).
* **"I don't have it… want me to fetch it?"** Plain "Nodes by
  country" had no value cue, so it went to the router, which
  selected no fact. It is now exempt from the value cue (a
  breakdown has no concept to explain), the router prompt
  gives it as an example, and the answer prompt forbids
  offering to fetch or check anything: the AI can't.
* **One long comma line.** The value is now one country per
  line, and a direct answer shows it as a bulleted list. In a
  multi-fact snapshot it folds back onto one line.

Tests: 441 → 447.
