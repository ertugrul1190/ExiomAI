# EXIOM / XEQM CORE KNOWLEDGE

SOURCE PRIORITY:
1. Official XEQMLabs whitepaper / GitHub
2. Official XEQMLabs website
3. Official EXIOM explorer
4. Other official XEQMLabs documentation

If sources conflict, prefer the newest official source and clearly distinguish LIVE, IN DEVELOPMENT, and PLANNED features.

---

## WHAT EXIOM IS

EXIOM is a privacy-focused Layer 1 blockchain network and developer platform created by XEQM Labs.

XEQM is the native coin used on the EXIOM network.

EXIOM was previously known as Equilibria, whose ticker was XEQ. The project migrated from XEQ to XEQM and launched the EXIOM mainnet on May 6, 2026.

EXIOM uses 100% Proof-of-Stake consensus. It does not currently use Proof-of-Work mining.

The main idea behind EXIOM is to make privacy useful not only for private cryptocurrency transactions, but also for software and applications built by developers.

---

## SIMPLE EXPLANATION OF A SERVICE NODE

A service node is a computer running EXIOM software that stays connected to the network and helps operate and secure it.

People lock XEQM into a service node as a commitment to the network.

The locked XEQM is called a stake.

A service node can be funded by one person or by several people together.

---

## SERVICE NODE STAKING

One complete EXIOM service node requires:

200,000 XEQM total.

There are two common ways to reach that amount.

### SOLO NODE

One person provides the full 200,000 XEQM.

That person operates the node alone.

### SHARED NODE

Several people can combine their XEQM to reach the same 200,000 XEQM total.

The person who creates and runs the shared node is called the operator.

The operator must personally provide at least:

100,000 XEQM.

Other people may then contribute XEQM toward the remaining space in the node.

These people are community contributors.

The minimum contribution for one community contributor slot is:

10,000 XEQM.

IMPORTANT:

10,000 XEQM is the minimum contribution, not a rule saying every contributor must contribute exactly 10,000 XEQM.

A contributor may be able to contribute more than 10,000 XEQM as long as the shared node still has room available before reaching its 200,000 XEQM total.

A shared node can have up to 10 community contributor slots in addition to the operator.

The total community contribution space is up to 100,000 XEQM because the operator must provide at least half of the 200,000 XEQM node requirement.

---

## WITHDRAWING FROM A SERVICE NODE

The current voluntary unbonding period is 14 days.

In simple terms:

If someone chooses to remove their XEQM stake from a service node, the coins are not immediately released.

They enter a waiting period of about 14 days before becoming available again.

According to the current whitepaper, rewards continue during voluntary withdrawal's 14-day unbonding period.

Forced deregistration also uses a 14-day unbonding period, but rewards do not continue during that period.

---

## SERVICE NODE REWARDS

EXIOM creates a new block approximately every 60 seconds.

The current protocol block reward is 8.25 XEQM per block.

This results in approximately 11,880 XEQM of service-node block emissions per day across the network.

Rewards depend on network conditions and the number of active nodes.

Do not guarantee any user's earnings or future return.

Starting with HF21, accumulated block rewards are paid on approximately weekly batches rather than every few minutes.

---

## OPERATOR FEE

A shared-node operator may charge an operator fee.

The current maximum operator fee is 10%.

The operator fee should not be confused with the operator's stake.

The stake is XEQM locked into the node.

The operator fee is the percentage arrangement used when distributing rewards from a shared node.

---

## XEQM SUPPLY

At EXIOM mainnet launch on May 6, 2026, the verified starting supply was:

276,917,604 XEQM.

This was created after the migration from legacy XEQ holdings.

XEQM does NOT have a hard maximum supply.

The total supply grows over time through scheduled protocol emissions.

There are currently two protocol-level emission streams:

- service-node block rewards
- governance emissions

There are no discretionary or arbitrary mints according to the current design.

In simple words:

The team cannot simply decide to create any amount of XEQM whenever it wants.

New XEQM enters supply according to predefined network rules.

XEQM does not use a conventional provable coin-burn mechanism.

---

## GOVERNANCE EMISSIONS

The current whitepaper describes governance emissions of approximately:

17,857 XEQM per day.

These emissions fund areas such as:

- core development
- marketing and awareness
- ecosystem/community work
- security and audits
- long-term reserves

These parameters may change as the project develops, so current values should be checked against the newest official documentation when necessary.

---

## PRIVACY

EXIOM is designed around privacy-preserving technology.

Its privacy architecture builds on CryptoNote/Monero-derived cryptographic technology.

Relevant concepts include:

- ring signatures
- stealth addresses
- confidential transaction amounts

Do not tell a beginner only the names of these technologies.

Explain what they mean in simple language when they are relevant.

For example:

A stealth address helps prevent an observer from easily linking a payment on the blockchain to the recipient's normal public address.

---

## DEVELOPER PLATFORM

STATUS: IN DEVELOPMENT

The EXIOM Private Developer API is currently described by XEQM Labs as being in active development.

Its goal is to let developers use EXIOM's privacy capabilities through software APIs.

Do not describe the developer API as fully live today unless newer official information confirms that status.

Current planned access tiers in the whitepaper are:

Free:
- no XEQM stake
- 10,000 testnet calls per month

Builder:
- 1,000 XEQM staked
- 100,000 mainnet calls per month

Production:
- 10,000 XEQM staked
- 1,000,000 calls per month
- webhooks
- priority support

Enterprise:
- 50,000 XEQM staked
- unlimited calls
- custom rate limits
- SLA

Developer-tier stakes are described as access commitments rather than payments.

The current planned developer-tier unbonding period is 7 days.

---

## PLATFORM FEES

For the planned EXIOM developer platform, the current fee distribution model is:

35% to API node operators

35% to the XEQM Labs treasury

30% to community governance

Because the developer platform is still in development, do not imply that all platform fee flows are already operating at full production scale.

---

## EXIOM PRIVACY ORACLE

STATUS: DESIGNED / PRE-IMPLEMENTATION

The Privacy Oracle is not currently a finished public product.

Its intended purpose is to let an application prove something about private data without exposing the underlying private data itself.

Example:

Instead of revealing someone's exact account balance, an application might prove only that the balance is above a required amount.

The current roadmap places the Privacy Oracle after the developer API work.

---

## EXIOM RFQ TRADING PLATFORM

STATUS: IN DEVELOPMENT

The EXIOM RFQ trading platform is intended to be a peer-to-peer over-the-counter trading system built on the EXIOM API.

The first planned pair is XEQM/BTC.

Do not describe it as a currently finished public exchange unless newer official information confirms that.

---

## LOKINET

STATUS: ENGINEERING ASSESSMENT / FUTURE NETWORK TRANSPORT

Lokinet technology exists in the EXIOM codebase, but its activation is still being assessed according to the current whitepaper.

The intended future goal is to hide direct network addresses by routing traffic through privacy-preserving paths.

Do not tell users Lokinet is already fully active on EXIOM unless current official information confirms it.

---

## CURRENT MAINNET STATUS

The EXIOM mainnet is live.

It launched on May 6, 2026.

The service-node network is live.

The GUI wallet is live.

The node explorer is live.

The developer API is still in development.

The Privacy Oracle is designed but not yet implemented as a finished public product.

The RFQ trading platform is in development.

---

## XEQM AS A NATIVE COIN

XEQM is the native coin of the EXIOM Layer 1 blockchain.

It is not an ERC-20 token.

It is not simply a token running on Ethereum.

It is not a wrapped asset or bridged representation according to the current whitepaper.

---

## MIGRATION HISTORY

The project previously operated as Equilibria using ticker XEQ.

The legacy XEQ-to-XEQM migration has been completed and closed.

The migration ran for 35 days.

The project says the migration records were published in a cryptographically auditable ledger.

---

## BUYING / TRADING XEQM

Exchange availability and market pairs can change.

Never treat an old exchange listing as guaranteed current information.

When the user asks where XEQM can currently be bought or what its current price is, live/current information should be checked rather than relying only on this knowledge file.

---

## ACCURACY RULES

Never invent an XEQM fact.

Never guarantee price appreciation, node profit, staking profit, or investment returns.

Clearly distinguish:

LIVE
IN DEVELOPMENT
PLANNED

If a value may have changed, say so and use current official data when live-data access is available.

When newer official documentation conflicts with older information, use the newer official documentation.

The current official whitepaper is a draft and may itself be updated as EXIOM develops.