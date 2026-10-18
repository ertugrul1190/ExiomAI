# EXIOM AI — Official Sources: Knowledge Refresh

The client wants accurate answers on EXIOM/XEQM technical
topics. They sent 17 official sources and what each covers,
and asked us to add the ones we didn't have, check the logic,
and test the AI with technical questions from the docs.

What they asked for: completely reliable answers, as few
tokens as possible, and answers faithful to the docs.

Result: on 64 golden technical questions written from the
docs, the AI receives the passage with the answer 12 times
before this change and 66 out of 66 after (2 questions were
added by the review). Tests: 720 → 752. The 2 usage-page
tests that fail locally fail before and after, because the
local `.env` sets `EXIOM_USAGE_TOKEN`. Live check: 32
technical questions against the real model (section 6).


## 1. What was wrong

The knowledge base (`core.md`, `technical.md`) was written
in August from whitepaper Draft v11 and core v1.0.7. Both had
been superseded, and most of the client's sources were never
read:

| Topic | The AI said | Official now |
| --- | --- | --- |
| Developer API | "in development"; Builder/Production/Enterprise tiers unlocked by staking 1,000 / 10,000 / 50,000 XEQM | **Live in beta**; prepaid per-call usage, no stake (whitepaper Draft v12, Sep 27) |
| Platform fees | 35% API nodes / 35% treasury / 30% governance | **70% oracle sidecar operators / 30% platform** |
| EXIOM Oracle | "designed / pre-implementation" | **Live** on Robinhood Chain (chainId 4663), 12-member committee, 8-of-12 |
| HF22 | "entering testnet" | **Live** since block 219,120 (Oct 5); Pulse-recovery at block 236,920 (v1.1.1/v1.1.2) |
| Forced deregistration lock | 14 days (from v11) | 14 days, but only since HF22; GitBook still says 7 |
| Latest core | "v1.0.7, can't say if latest" | **v1.1.2** (Oct 12); GUI v2.3.3 |
| Uptime, credits, penalties, ports, setup, troubleshooting, GUI, samples, community nodes | nothing; the AI was told not to give any procedure | all documented now |

The logic had gaps too:

* **Retrieval** (keyword scoring) had no stemming, so
  "deregistered" never matched "deregistration" and "earn"
  never matched "earnings". Concept variants matched as raw
  substrings: `pos` matched "purpose" and "post".
* **The router** sent operator questions that don't name
  EXIOM off-topic: "Which ports do I need to open?" and "What
  is Pulse-recovery?" got the off-topic banter.
* **Sources**: the prompt said knowledge answers need no
  source, and the instructions forbid pointing to a doc that
  isn't verified, so the AI could never link the operator
  guide.


## 2. The sources

All 17 client URLs are registered in `knowledge/sources.json`,
along with the pages they point to (core releases, GUI
releases, sybil-resistance repo, API docs at
api.exiom.network/docs). Each entry has a type, a check date,
what it covers and its known stale points. The priority order
for conflicts is: core releases > whitepaper > technical docs
> source code > Explorer (for live values) > explanatory
pages.

How they were read: GitBook in full via its `llms-full.txt`
(147 KB), GitHub READMEs and release notes via `gh api`, and
the website pages as HTML converted to text.

Deliberately **left out**: GitBook's "Guides > Mainnet /
Testnet" pages. They are legacy Equilibria testnet guides
(port 18091, `xeq-wallet-cli`, 100k / 25k XEQ stakes), and
the AI would have given them as XEQM mainnet steps. The
legacy swap walkthroughs are reduced to their dates and
audit facts (the swap closed in April).


## 3. The knowledge base

`technical.md` is removed and everything is rewritten as 10
files and 74 sections:

| File | Covers |
| --- | --- |
| `core.md` | identity, names, live vs planned, privacy, Pulse/Blink, links, where it trades |
| `tokenomics.md` | supply, burns, emissions, treasury, earnings/APY, HF21 payouts |
| `service_nodes.md` | stakes, pool staking, uptime proofs, credits, decommission vs deregistration, locks, quorum tests, post-fork grace |
| `operator_guide.md` | hardware, ports, Docker, Linux/Windows startup, wallet, registration, status, update, 5 troubleshooting cases, wallet RPC, backups |
| `hard_forks.md` | latest release, HF21, HF22, Pulse-recovery, HF23, Lokinet, binaries |
| `developer.md` | API, prepaid pricing, 70/30, samples, Oracle, sidecar, Privacy Oracle, RFQ, reference apps |
| `wallets.md` | GUI download/install/fixes/files, CLI commands, community public nodes, v1.1.0 wallet fixes |
| `network.md` | Nakamoto coefficient, 30% cap, sybil resistance, governance, roadmap |
| `history.md` | Equilibria → EXIOM, the swap, mission, vision, regulatory context |
| `changelog.md` | 9 conflict rulings (system prompt) |

Rules the files follow:

* **Dense, dated facts.** One fact per line with its date or
  snapshot ("943 nodes on Sep 27, 2026"). The old files spread
  each fact over 3 to 5 lines of "do not…" warnings, which ate
  the 7,000-character retrieval budget.
* **Every section ends with its official link**:
  `Source: [SN Operator Guide](https://…)`. A test checks that
  every cited URL is in `sources.json`, so no invented links.
  The prompt (`app.py`, SOURCES) now says: answers with steps,
  commands, settings or figures end with that link, at most
  two; a short concept explanation needs none.
* **Conflicts are named, not merged.** Superseded figures
  appear only as "replaced" (a test enforces this for tiers,
  35% and the 7-day lock). `changelog.md` dropped from 5.6K
  to 2.0K characters.
* **Where the docs disagree, the answer says so.** Example:
  the hardware figures from the whitepaper, both operator
  guide pages and the core README are listed side by side,
  with the whitepaper baseline recommended.
* **Nothing beyond the docs.** "No slashing" is stated only as
  what the docs say: a deregistered stake is locked, then
  withdrawable.


## 4. Logic changes

* **`retrieval.py`**
  * `stem()` drops `ings/ing/ed/s` on both sides.
  * Concept variants match whole words (a trailing `*` marks
    a stem: `deregist*`).
  * 9 operator concepts added: penalties, uptime, earnings,
    payout, registration, setup, ports, upgrade, wallet.
  * The relevance cut goes from 0.2 to 0.6 of the best
    score. Every golden answer, plus 10 questions not used
    for tuning, still passes up to 0.7.
* **`query_router.py`**
  * The router prompt now counts node, wallet, oracle and API
    operations as relevant, with 4 examples.
  * The keyword backstop (`EXIOM_TOPIC`) gains only
    unambiguous terms: Pulse-recovery, uptime proof,
    decommission, deregist…, registration command, operator
    fee, unbond, pool node, GUI/CLI wallet, wallet RPC,
    oracle sidecar, Lokinet. Plain "port", "oracle", "stake"
    and "blink" were tried and dropped: the review showed
    they match "what port does Postgres use" and "what's at
    stake".
* **`ai_provider.py`**: the web search domains add
  xeqmlabs.gitbook.io, exiom.network and nonlogs.io (listed
  in the core README). The search prompt prefers the GitBook
  docs after xeqmlabs.com.

Token cost per answer call:

* Retrieved knowledge averages ~3,900 characters, up from
  ~2,600, because sections now carry the answer.
* The system prompt is ~3,600 characters smaller (changelog),
  and it is the cached part.
* Net input is about the same; correct retrievals go from
  12/64 to 66/66.


## 5. Tests (`tests/test_knowledge.py`, router tests)

* **66 golden questions**, each with the text its answer must
  contain, retrieved exactly as `app.py` does. They cover
  credits, deregistration, ports, registration, Windows RPC,
  APY, payouts, HF22, Pulse-recovery, prepaid API, 70/30,
  Oracle, samples, GUI fixes, cpn nodes and history. 21 of
  them use casual wording ("node keeps getting decomm'd", "is
  my stake slashed").
* **Integrity:**
  * no section is long enough to be truncated;
  * every section has a Source line;
  * every cited URL and every client URL is registered;
  * source ids are unique and their types are known;
  * superseded facts appear only as replaced.
* **Matching:** whole-word concepts ("happy" isn't "apy",
  "purpose" isn't "pos").
* **Router:** 13 operator questions count as EXIOM topics;
  10 everyday ones (Postgres ports, Oracle SQL, car
  registration, "what's at stake") don't.

Run the live check with
`python live_eval.py evals/technical_questions.txt --parallel 2`
(32 questions, a few cents).


## 6. Live check (real model, gpt-5-nano)

**First run:**

* 2 operator questions went off-topic (router).
* The model confused "decommissioned" with "deregistered".
* It said rewards stop during a contributor's unstake.
* It hedged "UDP or TCP?" on 9232.
* It gave the daily emission without governance.

Each was fixed at the source (router prompt and backstop,
clearer knowledge lines) and asked again.

**Final run:** all 32 answered from the docs, 29 fully
accurate with official links. What remains is model
phrasing, not missing knowledge:

* One "what do I need to run a node?" answer opens muddled
  ("the operator must provide 200,000") before giving the
  right split (operator ≥100,000, contributors ≥10,000).
* Small slips: "majority" instead of two-thirds for Oracle
  forgery; "pre HF22" instead of "before v1.1.0".
* The router is not deterministic: "What sample apps are
  there for the API?" went off-topic once in two runs. After
  adding it as a router example it passed twice.

A larger answer model would remove most of the phrasing
slips, at a higher cost per answer. That is the client's
call.


## 7. Keeping it current

The knowledge is a snapshot from 2026-10-18. Dated values
(node counts, Nakamoto 9, latest v1.1.2, Pulse-recovery at
block 236,920) go stale. To refresh:

1. Re-read the sources in `sources.json`.
2. Update the sections and `changelog.md`.
3. Update the golden expectations that changed.
4. Run `pytest` and the live eval.

Live values (nodes, supply, height, price) always come from
the Explorer and the trackers, never from these files.
