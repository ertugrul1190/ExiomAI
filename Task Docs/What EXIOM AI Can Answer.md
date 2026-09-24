# EXIOM AI — What You Can Ask

A guide to what EXIOM AI can answer, with example questions.
Wording is flexible: users can ask in their own words, and
these are only examples.

Live numbers come from the **Official EXIOM Explorer**
(`explorer.xeqmlabs.com`) at the moment of the question. Each
answer names the Explorer as its source.


## 1. Live network numbers

Plain questions for one number (for example "How many active
nodes are there?") are answered instantly from the Explorer.
Questions that need an explanation too ("How many active
nodes are there, and is that a lot?") get a full answer that
uses the live number.

### Service nodes

| You can ask about | Example question |
| --- | --- |
| Active nodes | How many active nodes are there? |
| Inactive (decommissioned) nodes | How many inactive nodes are there? |
| Registered nodes | How many registered service nodes? |
| Nodes awaiting contribution | How many nodes are waiting for contributions? |
| Open pool nodes | How many open pool nodes? |
| Active swarms | How many swarms are there? |
| Nodes on the latest software release | How many nodes are on the latest version? |
| Countries with nodes | How many countries have nodes? |
| Nodes in each country | Nodes by country |

"Nodes by country" returns the full list, largest first:

> **Service nodes by country:**
>
> - France: 323
> - The Netherlands: 255
> - United States: 121
> - …

Follow-ups also work, such as "How many nodes are in
Germany?" or "Which countries have the most nodes?".

### Quorums

| You can ask about | Example question |
| --- | --- |
| Testing quorums | How many testing quorums? |
| Pulse quorums | How many pulse quorums are there? |
| Checkpoint quorums | How many checkpoint quorums? |
| Blink quorums | How many blink quorums? |

### Supply

| You can ask about | Example question |
| --- | --- |
| Total supply | What is the total supply right now? |
| Circulating supply | What is the current circulating supply? |
| Locked (staked) supply | How much is locked right now? |
| Percentage of supply locked | What percentage of supply is locked right now? |
| Unlocked supply | What is the unlocked supply now? |

### Staking and rewards

| You can ask about | Example question |
| --- | --- |
| Staking requirement | What's the staking requirement? |
| Minimum operator contribution | What's the minimum operator contribution? |
| Maximum contributors per node | What's the max contributors? |
| Service node reward (per block) | What is the service node reward per block? |
| Daily service node emission | How much do service nodes earn in total per day? |
| Current APY | What is the current APY? |
| Daily reward per node | What is the current daily reward per node? |
| Annual reward per node | What is the current annual reward per node? |

Reward figures are the Explorer's current numbers. EXIOM AI
never promises returns.

### Blocks and chain

| You can ask about | Example question |
| --- | --- |
| Block height | What is the current block height? |
| Average block time (last hour) | Average block time in the last hour right now |
| Average block time (last 24 hours) | Current average block time |
| Average block time (last 7 days) | Current average block time this week |
| Target block time | What is the target block time? |
| Blocks in the last 24 hours | How many blocks in the last 24 hours? |
| Hashrate | What is the current hashrate? |
| Total transactions ever | How many total transactions? |
| Blockchain database size | What is the current database size? |
| Mainnet version | What is the current mainnet version? |
| Active hard fork | What is the current hard fork? |

### Mempool (transactions waiting to be confirmed)

| You can ask about | Example question |
| --- | --- |
| Number of waiting transactions | How many transactions are in the mempool? |
| Mempool size | Current mempool size |

### Several numbers at once

Users can ask for more than one value in a single question,
for example "What's the block height and how many nodes are
active?". The answer includes each value.


## 2. Looking up one node, block or transaction

Paste an ID from the Explorer into a question and EXIOM AI
reads that item directly.

| Ask about | Example question | What the answer can include |
| --- | --- | --- |
| A service node (by its 64-character public key) | What's the status of service node `<public key>`? | Status (active, decommissioned, awaiting contributions), how much is staked, contributors and open spots, operator fee, operator address, software version, last uptime proof, last reward, allowed downtime, swarm, and whether an unlock was requested |
| A block (by number or hash) | What's in block 500000? | Hash, timestamp, number of transactions, size, reward, how deep it is, and the service node that won it |
| A transaction (by its 64-character hash) | Look up transaction `<hash>` | The block it's in, type, timestamp, fee, size and confirmations |

- Up to three IDs can go in one question.
- If an ID doesn't exist, EXIOM AI says it wasn't found. If
  the Explorer can't be reached, it says that instead. It
  never guesses.
- A node's IP address and ports are never shown, in line with
  the Explorer's own privacy promise.


## 3. Explanations and general questions

EXIOM AI also explains EXIOM in plain language, for complete
beginners and experienced users alike. Topics include:

- What EXIOM is and how XEQM works as a native coin
- What a service node is, and solo vs. shared nodes
- How staking works, how to withdraw, and how rewards and
  operator fees work
- XEQM supply and governance emissions
- Privacy, the EXIOM Privacy Oracle and Lokinet
- The developer platform, platform fees and the RFQ trading
  platform
- Current mainnet status and migration history
- Buying and trading XEQM
- General crypto ideas (what a blockchain, block height,
  quorum or hashrate is) as they apply to EXIOM
- EXIOM AI itself: what it is and who made it

Example questions:

- What is a service node?
- How does staking work on EXIOM?
- What is a pulse quorum?
- Why does the node count matter?
- What's the difference between a solo and a shared node?

Answers can mix explanation and live data, for example
"What is the staking requirement, and what does it mean for
me?".

Conversation context carries over, so follow-ups like "and
what about last week?" or "explain that more simply" work.


## 4. Prices, markets and other current information

Some current information isn't on the Explorer: the XEQM
price, market cap and volume, where XEQM is traded, the latest
software release and recent announcements. For these, EXIOM AI
runs a quick web search limited to XEQMLabs' own sites, its
GitHub and the price trackers and exchanges that list XEQM,
and names the site each figure comes from.

| You can ask about | Example question |
| --- | --- |
| XEQM price | Exiom coin price |
| Market cap and volume | What's XEQM's market cap? |
| Where to buy right now | Where can I buy XEQM right now? |
| Latest software release | What's the latest XEQM release? |
| Recent announcements | Any recent XEQMLabs news? |

- Prices differ slightly between sites and exchanges, and the
  answer says so.
- Network numbers (supply, nodes, block height) always come
  from the Explorer, never from a web page.
- No price predictions, and no advice to buy or sell.
- Searches take a few seconds longer than other answers.
- Searches have a daily limit. Past it, EXIOM AI says it can't
  check right now and points to CoinGecko or the exchange.


## 5. What it won't do

- **Off-topic questions** (unrelated to EXIOM, XEQM or crypto)
  get a friendly decline.
- **Financial advice**: it gives no price predictions and
  never promises profits, yields or returns.
- **Made-up numbers**: if a live value is unavailable, it says
  so and points to the Explorer. It never invents a value or
  passes off an old one as current.
- **Private details**: it never shows node IP addresses or
  ports.


## 6. Good to know

- **Numbers are live.** Most values refresh every 30 seconds.
  Quorum counts and "nodes on the latest release" change
  slowly and refresh every 2 minutes.
- **Right after a restart**, quorum counts and "nodes on the
  latest release" can take up to a minute to appear, because
  they come from larger Explorer pages that load in the
  background. Until then, questions about them get a
  "not available right now" answer.
- **If the Explorer changes**, most values have a backup
  source. Inactive and registered nodes, country figures and
  total transactions have no backup. If the Explorer changes
  how it provides them, the bot says they're unavailable
  (never a wrong number) until the code is updated.
