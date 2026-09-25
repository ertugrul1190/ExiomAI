# EXIOM / XEQM TECHNICAL KNOWLEDGE

Knowledge snapshot: August 2026

This file contains verified technical and protocol-level knowledge about
EXIOM and XEQM.

SOURCE PRIORITY RULE:

When official sources disagree, prefer:

1. newer EXIOM/XEQM core implementation and mandatory release information
2. newer XEQMLabs technical whitepaper
3. newer official technical documentation
4. official explorer/live network data
5. older official explanatory or marketing material

Never silently merge contradictory claims.

Always distinguish:

- LIVE
- ACTIVE DEVELOPMENT
- TESTNET
- DESIGNED
- PLANNED
- HISTORICAL

Do not infer EXIOM implementation details merely because EXIOM is derived
from CryptoNote, Monero, Oxen, or another codebase.


# NETWORK IDENTITY

EXIOM is a privacy-preserving Layer 1 blockchain network and developer
platform built by XEQMLabs.

Its native Layer 1 coin is XEQM.

XEQM is not an ERC-20 token.

XEQM is not a wrapped token.

XEQM is not described by current official documentation as a bridged asset.

Users interact with the EXIOM blockchain itself rather than an Ethereum
token contract.

The project was formerly known as Equilibria with ticker XEQ.

The legacy XEQ identity was replaced through the Horizon migration.

The current network/platform identity is EXIOM and the native coin ticker
is XEQM.


# MAINNET STATUS

STATUS: LIVE

EXIOM mainnet has been operational since May 6, 2026.

The mainnet is also associated with the Ragnarok network generation/name.

The service-node network is live.

The GUI wallet is live.

The public blockchain explorer is live.

The developer API is not yet to be described as fully launched production
functionality unless newer official information confirms that status.


# CONSENSUS

STATUS: LIVE

EXIOM uses Proof-of-Stake consensus.

Current documentation describes it as 100% or pure Proof-of-Stake.

There is no Proof-of-Work mining component in the current EXIOM mainnet
consensus model.

Service nodes participate in operating and securing the network.


## What Proof-of-Stake means

Proof-of-Stake is a blockchain consensus model in which network
participants commit or lock cryptocurrency as economic collateral rather
than using mining hardware to perform Proof-of-Work calculations.

That committed cryptocurrency is called a stake.

The act of committing it is called staking.

In EXIOM, service-node operators stake XEQM as part of operating service
nodes.


# BLOCK PRODUCTION

STATUS: LIVE

Current documented target block interval:

60 seconds.

Current documented service-node block reward:

8.25 XEQM per block.

At a 60-second block interval:

1,440 blocks are expected approximately per day.

8.25 XEQM × 1,440 blocks gives approximately:

11,880 XEQM per day

in service-node block emissions across the network.

This is a network-wide emission figure.

It is NOT the expected daily reward of one individual node.


# XEQM SUPPLY MODEL

STATUS: LIVE PROTOCOL MODEL

Verified starting mainnet supply:

276,917,604 XEQM.

This was the starting supply created through completion of the legacy
XEQ-to-XEQM migration.

IMPORTANT:

This number is NOT the permanent maximum supply.

Current newer official technical documentation describes XEQM as an
uncapped-supply blockchain with predictable protocol emissions.

Total supply therefore grows over time.

There are two documented protocol emission streams:

1. service-node block rewards
2. governance emissions

The project distinguishes predictable protocol emissions from
discretionary issuance.

"Fixed supply discipline" in newer documentation means there is no
arbitrary or discretionary creation of coins by a person or organization.

It does NOT mean that total XEQM supply is permanently capped at
276,917,604.


# SUPPLY CONFLICT WITH OLDER DOCUMENTATION

An older official AI-information page described approximately 276 million
XEQM as fixed and stated that no future mints were planned.

A newer XEQMLabs technical whitepaper dated July 26, 2026 instead states
that:

- 276,917,604 XEQM was the launch/start supply
- supply grows through scheduled protocol emissions
- XEQM follows an uncapped emission model
- discretionary issuance is not part of the intended supply model

For current technical answers, use the newer whitepaper interpretation.

Do not repeat the older "hard fixed supply" claim without explaining that
newer official documentation supersedes it.


# SERVICE NODES

STATUS: LIVE

A service node is a computer/server participating in EXIOM network
infrastructure.

A user should not be expected to understand the term automatically.

Beginner explanation:

A service node is basically a computer that stays online and helps the
EXIOM network operate.

The person responsible for creating and maintaining a service node is
called its operator.


# FULL SERVICE-NODE STAKE

Current total stake required for one service node:

200,000 XEQM.

This 200,000 XEQM may be supplied by one operator or, under the shared-node
model, by the operator together with community contributors.


# SOLO SERVICE NODE

A solo operator can supply the complete:

200,000 XEQM

required for the service node.

In that case the operator does not require community participants to fill
the node's stake requirement.


# SHARED SERVICE NODE

A shared service node allows several people to contribute XEQM toward the
same 200,000 XEQM service-node requirement.

The operator is the person responsible for registering/running the node.

Current minimum operator stake:

100,000 XEQM.

This represents 50% of the full 200,000 XEQM service-node stake.


# COMMUNITY CONTRIBUTORS

Other participants can contribute toward the remaining service-node stake.

These participants can be described as community contributors or
community stakers.

Current minimum community contribution per contributor slot:

10,000 XEQM.

IMPORTANT:

10,000 XEQM is a MINIMUM.

It is not a rule saying every participant must contribute exactly
10,000 XEQM.

A contributor may be able to provide more than 10,000 XEQM if enough
unfilled stake remains in that node.


# CONTRIBUTOR SLOTS

Current documented maximum contributor slots:

11 total slots including the operator.

This means:

1 operator slot

plus up to:

10 community contributor slots.

The community portion of a shared node can occupy up to approximately
100,000 XEQM because the operator must provide at least 100,000 XEQM of
the 200,000 XEQM total.


# OPERATOR FEE

Current documented maximum operator fee:

10%.

Do not describe this as a mandatory 10% fee.

It is a maximum permitted operator fee according to current documentation.

The operator fee and the operator's own share of rewards are separate
concepts.

Do not invent the exact payout formula if it has not been retrieved from
verified protocol documentation for the question.


# SERVICE-NODE REWARDS

Service nodes participate in the network reward system.

Do not promise a fixed amount of XEQM to an individual service node.

Individual reward expectations depend on factors including:

- active service-node population
- protocol reward-selection mechanics
- stake participation
- network conditions
- current protocol version

Historical/current snapshots in a whitepaper must not be presented as
permanent future earnings.

Any APY or estimated monthly reward in dated documentation must be
identified as a dated estimate rather than guaranteed yield.


# HF21

STATUS: LIVE / ACTIVATED

Hard Fork 21 activated at block 99,000.

The official v1.0.7 XEQM Core release was a mandatory consensus-changing
upgrade for HF21.

Infrastructure that validates the chain needed to upgrade to the HF21
compatible version.

HF21 changed service-node reward batching.


# HF21 WEEKLY REWARD BATCHING

Before HF21, reward batches were distributed on a much shorter interval.

HF21 increased the service-node reward batching interval to:

10,080 blocks.

At approximately 60 seconds per block:

10,080 blocks ≈ 7 days.

Each wallet has a deterministic/fixed payout position within the weekly
cycle according to the current release description.

HF21 also raised the minimum batch payout threshold to:

1 XEQM.

A reward balance below the threshold is not described as lost.

Instead it continues accumulating until it meets the payout threshold and
can be paid at the wallet's applicable payout position.

Do not tell users that service-node rewards necessarily arrive every day.

Under HF21 they are batched on the weekly mechanism.


# UNBONDING

Unbonding is the waiting period involved when previously committed stake
is being released.

For beginners:

A person's XEQM is committed while participating in the service-node
system. When they exit, there can be a waiting period before that stake
becomes available again. That waiting process is called unbonding.


# VOLUNTARY UNBONDING

Current documented voluntary service-node unbonding period:

14 days.

Current documentation says rewards continue during voluntary unbonding.


# FORCED DEREGISTRATION

A node can also leave the active service-node set because it is
deregistered by the protocol rather than because the operator voluntarily
leaves.

Current technical design states a:

14-day forced-deregistration unbonding period.

Rewards do not continue during forced-deregistration unbonding according
to the current documentation.


# HF22

STATUS: ENTERING TESTNET / VALIDATED DESIGN IN CURRENT WHITEPAPER

Do not describe HF22 functionality as mainnet-active unless newer official
release information confirms activation.

Current HF22 work includes:

- operator-wallet-key quorum deduplication
- unbonding-period unification

The stated purpose is partly to improve network survivability and reduce
concentration risks.


# HF22 OPERATOR-WALLET QUORUM DEDUPLICATION

Current HF22 design:

At most one node associated with the same operator wallet address should
hold a validator seat in the same quorum round.

This is intended to reduce the ability of one operator controlling many
nodes under one wallet to dominate quorum participation.

It applies to relevant quorum selection such as:

- Pulse rounds
- oracle sessions
- obligations quorums

according to current design documentation.

If multiple selected nodes belong to the same operator wallet, duplicate
selection is replaced with a node from a different operator.


# HF22 LIMITATION

Wallet-key deduplication does not fully prove that two wallet addresses
belong to different humans or organizations.

An operator can potentially split infrastructure across multiple wallet
addresses.

Current documentation explicitly treats this as a limitation that HF23
is intended to address through infrastructure/proximity clustering.


# QUORUMS

A quorum is a selected group of network participants used to collectively
perform or verify some network decision.

For beginners:

Instead of trusting one computer to make a decision, a blockchain can
select a group of nodes and require that group to participate.

That selected group is called a quorum.

Current future-design documentation uses a quorum size of:

12 seats per round

for the discussed survivability/deduplication design.

Do not automatically apply this number to every possible EXIOM subsystem
unless the relevant source establishes it.


# PULSE

Current official technical documentation refers to Pulse rounds as part
of EXIOM quorum/consensus operation.

Do not invent low-level Pulse mechanics unless verified by EXIOM-specific
core documentation.

If asked for internals beyond the stored documentation, say that the
available EXIOM material does not specify enough detail and distinguish
general explanation from verified EXIOM implementation.


# NETWORK CONCENTRATION

XEQMLabs' current technical design treats infrastructure concentration as
a network-survivability risk.

The concern is that many nominally separate nodes may actually depend on
the same:

- physical datacenter
- hosting facility
- routing infrastructure
- operator
- failure domain

If too many nodes depend on the same infrastructure, one outage may remove
a large portion of the network simultaneously.


# NAKAMOTO COEFFICIENT

The Nakamoto coefficient is a decentralization/resilience metric.

In simple terms, it estimates how many independent entities would need to
combine or fail before they could seriously affect the network.

The July 2026 whitepaper reported:

Nakamoto coefficient: 7

with a stated target of:

8 or higher.

This is a DATED NETWORK SNAPSHOT.

Never present 7 as the guaranteed current value without live verification.


# NETWORK NODE COUNTS

The July 2026 whitepaper included dated snapshots such as:

693 active nodes

and:

184 operators.

Other dated snapshots in the same evolving documentation may use slightly
different counts such as 700+ nodes.

These are historical/date-specific values.

Do not answer "How many nodes are there right now?" from this file.

That requires live explorer/network data.


# HF23

STATUS: DESIGN PHASE

Do not describe HF23 as currently active.

Current HF23 design depends significantly on Lokinet engineering and
activation.

Planned HF23 concepts include:

- proximity-cluster analysis
- cluster registration limits
- reward modification for excessive concentration
- proximity-cluster quorum deduplication
- Lokinet as network transport


# HF23 PROXIMITY CLUSTERS

The planned system attempts to identify nodes that appear to share the
same physical/network failure domain.

Current design discusses using characteristics such as:

- routing behavior
- path overlap
- latency relationships

to group physically or infrastructurally close nodes into proximity
clusters.

The purpose is to make sybil/concentration controls less dependent only
on wallet identity.


# HF23 CLUSTER CAP

Current design target:

A single proximity cluster should not contain more than:

30% of active nodes.

The exact numerical node count represented by 30% changes as the network
size changes.

Do not permanently store a specific node-count equivalent as current.


# HF23 REGISTRATION CONTROL

Under the current planned design, a new node registration associated with
an already-overconcentrated cluster may be rejected.

This is planned behavior.

It is NOT currently to be described as active mainnet behavior unless an
HF23 activation release confirms it.


# HF23 ZERO-REWARD MODIFIER

Current design proposes that nodes exceeding the permitted cluster
concentration receive zero service-node block rewards.

Within a concentrated cluster, current design ranks nodes using
registration age so older nodes within the allowed threshold retain normal
rewards and excess nodes lose block rewards.

A planned 30-day grace period is described for HF23 activation before the
zero-reward mechanism takes effect.

This is DESIGN information, not current mainnet behavior.


# HF23 QUORUM CLUSTER DEDUPLICATION

Current design intends to upgrade HF22's wallet-based quorum deduplication
to proximity-cluster-based deduplication.

Target rule:

normally no more than one node from the same proximity cluster should
occupy a quorum seat in the same round.


# HF23 QUORUM FALLBACK

A 12-seat quorum requires enough distinct clusters to populate 12 unique
seats.

Current design therefore includes a fallback if fewer than 12 distinct
clusters are available.

The fallback favors additional seats from smaller/less concentrated
clusters before giving additional representation to highly concentrated
clusters.

Current design also proposes exposing/logging fallback frequency as a
concentration-risk indicator.


# LOKINET

STATUS: PRESENT IN CODEBASE / ACTIVATION UNDER ENGINEERING ASSESSMENT

Lokinet is based on LLARP:

Low Latency Anonymous Routing Protocol.

It is a network-routing technology using onion-routing concepts.

The EXIOM codebase contains Lokinet/LLARP-related code according to
current documentation.

However, Lokinet must NOT be described as fully active EXIOM network
transport merely because its code exists.


# PLANNED LOKINET ROLE

Current HF23 design plans to use Lokinet as EXIOM's primary network
transport.

The intended direction includes moving away from publicly announced node
IP addressing toward cryptographic Lokinet identities.

Planned uses include:

- service-node network communication
- developer API hidden-service access
- RFQ platform hidden-service access
- Privacy Oracle communication

These are planned/future behaviors dependent on Lokinet activation.


# ONION ROUTING

Onion routing is a networking technique where traffic travels through
multiple intermediate hops while layers of routing information are
progressively removed.

The general privacy goal is that no single intermediate routing node needs
to know both:

- the original sender
- the final destination

This is a general explanation of the concept.

Do not claim an exact EXIOM routing path length or cryptographic packet
format unless verified.


# PRIVACY TECHNOLOGY

EXIOM is derived from the CryptoNote/Monero privacy lineage.

Current official explanatory documentation identifies privacy mechanisms
including:

- ring signatures
- stealth addresses
- confidential transaction amounts

EXIOM is a distinct blockchain and should not be described simply as
Monero.


# RING SIGNATURES

General concept:

A ring signature allows a cryptographic signature to be associated with a
group of possible signers rather than publicly identifying one obvious
signer.

This helps obscure which participant actually authorized a transaction.

Do not assume EXIOM currently uses the exact same ring-signature version,
ring size, CLSAG implementation, or parameters as current Monero unless
EXIOM-specific implementation evidence verifies it.


# STEALTH ADDRESSES

General concept:

A stealth-address system allows transactions to use one-time destination
information so that blockchain observers cannot trivially link every
payment to the recipient's publicly shared address.

Do not invent EXIOM-specific key-derivation details without verified
technical documentation.


# CONFIDENTIAL AMOUNTS

Current official material describes EXIOM transaction amounts as private.

The high-level purpose is to avoid publicly revealing transaction values.

Do not claim a specific range-proof system or exact cryptographic
construction unless verified from EXIOM-specific implementation sources.


# CRYPTONOTE LINEAGE

CryptoNote is the privacy-protocol family from which Monero and a number
of other privacy networks evolved.

EXIOM inherits technology from this lineage but has its own:

- network
- consensus
- economics
- service-node system
- roadmap
- developer-platform architecture

Never infer that every feature present in modern Monero automatically
exists in EXIOM.


# DEVELOPER PLATFORM

STATUS: ACTIVE DEVELOPMENT

EXIOM Private Developer API is being developed as a programmable privacy
platform.

Its purpose is to expose privacy capabilities to applications through an
API rather than limiting privacy functionality only to direct wallet
transactions.

Do not describe the API as fully production-launched until newer official
information confirms launch.


# DEVELOPER STAKING

The planned developer-access model requires developers to stake XEQM to
unlock certain platform tiers.

The stake is described as an access commitment rather than simply an API
purchase fee.

Current planned developer-stake unbonding period:

7 days.

Current documentation says developer-platform stake does not earn normal
service-node rewards merely because it is committed for API access.


# PLANNED DEVELOPER API TIERS

STATUS: PLANNED / IN DEVELOPMENT

Current documented tier design:

FREE

- no XEQM stake
- up to 10,000 testnet calls per month

BUILDER

- 1,000 XEQM stake
- up to 100,000 mainnet calls per month

PRODUCTION

- 10,000 XEQM stake
- up to 1,000,000 calls per month
- webhook functionality is planned/described

ENTERPRISE

- 50,000 XEQM stake
- unlimited usage under the described design
- SLA support is described

These specifications belong to an in-development platform.

They are not guaranteed permanent commercial terms.


# API PLATFORM FEES

Current planned platform fee distribution:

35% to API node operators

35% to XEQMLabs treasury

30% to community governance.

This describes planned platform economics.

Do not confuse API platform fees with ordinary blockchain service-node
block rewards.


# API NODE OPERATORS

The developer-platform design includes API node operators that serve API
traffic.

They are conceptually different from a user merely calling the API.

Official design material states API node operators can receive part of
platform fees.

Do not invent operator onboarding requirements or hardware requirements
unless verified.


# PRIVACY ORACLE

STATUS: DESIGNED / PRE-IMPLEMENTATION

The EXIOM Privacy Oracle is a planned privacy-first oracle system.

An oracle is a mechanism that allows blockchain/software systems to use
information originating outside the blockchain.

The EXIOM Privacy Oracle is specifically intended to prove facts about
private external data without revealing all of the underlying data.


# ORACLE GOAL

Example concept:

Instead of revealing an exact private value, an application might prove
that a condition is true.

Examples in current project design include concepts such as:

- proving a price crossed a threshold without exposing the precise private
  value
- proving an account condition without exposing credentials
- proving a compliance statement without revealing the underlying record

These are use-case/design descriptions rather than claims that every
example is currently deployed.


# ORACLE PROOF DESIGN

Current project design says the Privacy Oracle is intended to use
zero-knowledge-proof techniques for provenance/proof of data obtained from
standard HTTPS sources.

The stated design goal is to avoid requiring special cooperation from the
source website and avoid reliance on trusted hardware.

Because the Oracle is pre-implementation, do not claim a final proof
system, circuit architecture, cryptographic library, or security model
unless newer technical material confirms it.


# ORACLE PHASES

Current design describes staged rollout:

1. internal proof of concept
2. federated oracle testnet
3. mainnet oracle with internal EXIOM consumers
4. external developer/consumer access

External oracle access is therefore not currently a live general-purpose
service.


# ORACLE VERIFIERS

The planned architecture includes verifier nodes/quorums.

Indicative hardware requirements published in the design include roughly:

- 8 CPU cores
- 16 GB RAM
- 200 GB SSD
- 500 Mbps low-latency network connection

These are indicative future requirements and may change before production.


# ORACLE REWARDS

Current design considers multiple possible verifier revenue streams:

- ordinary service-node block rewards
- API-node fee share where applicable
- oracle-session fees
- supplemental governance incentives during early/low-volume operation

These are platform-design concepts.

Do not calculate expected oracle-verifier income as though the Oracle were
already operating at production scale.


# RFQ TRADING PLATFORM

STATUS: IN DEVELOPMENT

EXIOM's planned RFQ system is a peer-to-peer over-the-counter trading
platform.

RFQ means:

Request for Quote.

In simple terms, a trader asks counterparties for a price to make a trade
rather than simply submitting an order to a conventional public order
book.


# RFQ FIRST PLANNED PAIR

Current roadmap identifies:

XEQM/BTC

as the intended first trading pair.

Both are native Layer 1 assets in the stated design.

Do not claim that the EXIOM RFQ platform is already live unless newer
official information confirms production launch.


# RFQ SETTLEMENT / ORACLE RELATIONSHIP

The planned RFQ system is intended to use cryptographic settlement
attestations.

The Privacy Oracle is planned to support private price attestations.

The design goal includes proving that a trade satisfied a reference-price
condition without unnecessarily revealing the exact private transaction
details.


# RFQ DEVELOPMENT DEPENDENCIES

Current documentation states the full production RFQ platform depends on
progress in:

- the EXIOM Developer API
- the Privacy Oracle
- associated Phase 2 / Phase 3 work

Do not describe future dependency components as already deployed.


# GOVERNANCE EMISSIONS

Current documented governance emission rate is approximately:

17,857 XEQM per day.

This is separate from the approximately:

11,880 XEQM per day

of service-node block emissions.

Both contribute to protocol-driven XEQM supply growth.


# GOVERNANCE

STATUS: CURRENTLY FOUNDING-TEAM LED WITH COMMUNITY INPUT

Current documentation describes governance as presently involving the
founding team with community input through public/community channels.

Formal fully on-chain governance is not yet to be described as active.


# TREASURY ALLOCATION DESIGN

Current whitepaper allocation framework for governance emissions includes
categories such as:

- core development
- marketing and awareness
- ecosystem/community support
- security and audits
- long-term reserve

Do not present allocation percentages as immutable constitutional rules;
the governing whitepaper is explicitly a draft and may change.


# FORMAL GOVERNANCE ROADMAP

STATUS: PLANNED

Formal governance is associated with later roadmap phases.

Current roadmap describes structured proposal processes before eventual
weighted voting.

Phase 6 is associated with formal governance involving operator voting
rights weighted using factors such as stake and tenure.

This is planned functionality.


# MIGRATION FROM XEQ

STATUS: COMPLETED / HISTORICAL

The project previously used the Equilibria identity and XEQ ticker.

The Horizon migration moved the project to EXIOM/XEQM.

The XEQ-to-XEQM migration has completed.

Current documentation describes a 35-day production migration period.


# MIGRATION AUDITABILITY

Official project documentation states that the migration was designed to
be independently auditable.

The migration records were associated with published cryptographic audit
material including SHA-256 fingerprinting and published wallet/spend-key
information.

The verified result used for the new chain's starting supply was:

276,917,604 XEQM.


# COIN SWAP PRODUCT

XEQMLabs describes the migration technology/process as a coin-swap product
that can potentially be used for other projects requiring auditable chain
migration.

Do not confuse that product with an active bridge between EXIOM and the
legacy XEQ chain.

The XEQ migration is completed.


# EXCHANGE AVAILABILITY

Exchange availability changes over time.

Older official documentation identifies a NonKYC XEQM market.

Do NOT answer:

"Where can I buy XEQM right now?"

solely from stored knowledge.

That question requires current verification of:

- exchange availability
- trading pair
- deposit status
- withdrawal status

before describing a venue as currently usable.


# PRICE

XEQM market price is live data.

Never treat a stored historical price as current.

Any frontend number such as:

$0.016

must not be presented as a live XEQM price unless it is coming from a
verified current price source.

If live data is unavailable, label the value appropriately or omit it.


# ACTIVE NODE COUNT

Active service-node count is live network data.

Do not answer a "right now" node-count question from dated whitepaper
snapshots.

Retrieve it from the current explorer/network data layer.


# BLOCK HEIGHT

Block height changes continuously.

Never store a block height in this document as a current fact.

Use the live-network layer.


# CURRENT SOFTWARE VERSION

Software version changes over time.

The official v1.0.7 release is important historically because it was the
mandatory HF21 release.

Do not claim v1.0.7 is still the latest version without checking the
current official release feed.


# LIVE VS STATIC DATA RULE

STATIC KNOWLEDGE appropriate for this corpus includes:

- what EXIOM is
- how service nodes conceptually work
- current documented staking rules
- protocol architecture
- privacy concepts
- migration history
- hard-fork behavior
- planned system architecture

LIVE DATA must eventually come from runtime sources:

- XEQM price
- active node count
- block height
- total/current supply
- current network version
- latest core release
- exchange status
- real-time reward estimates
- current market pairs
- current network concentration measurements


# FINANCIAL CALCULATIONS

ExiomAI can perform neutral arithmetic when sufficient data is available.

For example it may explain:

8.25 XEQM/block × 1,440 blocks/day = approximately 11,880 XEQM/day
network-wide.

But it must not turn that into promises such as:

"You will earn X XEQM."

Investment-return calculations must clearly state assumptions and must not
be presented as guaranteed outcomes.


# NODE EARNINGS

If a user asks:

"How much does one node earn?"

the assistant should determine whether current network data is available.

A dated whitepaper estimate may be discussed only with its date and
assumptions.

For a current answer, live active-node count and the verified reward
mechanism should be used.

Do not automatically divide daily emissions by node count unless the
protocol's reward-selection mechanics justify that approximation.


# SECURITY / SYBIL RESISTANCE

A Sybil attack involves one real actor creating or controlling many
apparently independent identities in order to gain disproportionate
influence.

EXIOM's documented architecture uses economic stake requirements as one
Sybil-resistance mechanism.

Additional planned controls include:

- operator-wallet quorum deduplication
- infrastructure/proximity analysis
- concentration caps
- quorum diversity rules

Do not claim these planned controls are all currently active.


# OPERATOR CAPITAL REQUIREMENT

Each full service node requires 200,000 XEQM total stake.

For shared nodes the operator must provide at least 100,000 XEQM.

Therefore an operator controlling many service nodes needs substantial
stake committed across those registrations.

This is part of the project's economic Sybil-resistance approach.


# INFRASTRUCTURE CONCENTRATION SIGNALS

Current technical design discusses possible indicators of shared
infrastructure such as:

- tightly correlated uptime-proof timing
- network proximity
- routing overlap
- Autonomous System / provider concentration

Treat these as analysis/design mechanisms, not proof that the protocol
currently uses every signal automatically.


# NETWORK SURVIVABILITY

The current design goal is to prevent one hosting facility or network
failure domain from taking too large a fraction of EXIOM offline.

HF23's proposed 30% cluster cap is part of this survivability strategy.

The stated reasoning is engineering resilience rather than merely a
marketing measure of decentralization.


# DOCUMENT STATUS

The July 26, 2026 XEQMLabs whitepaper is explicitly marked:

Draft v11.

Therefore:

- roadmap timing can change
- planned parameters can change
- implementation status can change
- economic design can change
- future hard-fork designs can change

When a later official core release contradicts a draft whitepaper,
production implementation/release information should take priority.


# ACCURACY RULES FOR ExiomAI

ExiomAI must distinguish between:

1. verified current mainnet behavior
2. verified historical behavior
3. active development
4. testnet behavior
5. planned/design behavior
6. general blockchain explanation
7. unsupported assumptions

Never convert categories 3-7 into category 1.


# WHEN INFORMATION IS MISSING

If an EXIOM-specific implementation detail is not available, say:

"The available verified EXIOM documentation does not specify that
implementation detail."

If helpful, continue with:

"Generally, this concept works like this..."

Then explain the general concept separately.


# DO NOT HALLUCINATE PROCEDURES

Do not invent steps such as:

- which wallet address a user should send stake to
- which command they must run
- what RPC endpoint exists
- what port number is required
- what registration command is used
- what exact transaction field is required

unless those steps are retrieved from verified EXIOM-specific
documentation.

Knowing that a user can contribute 10,000 XEQM does NOT by itself prove
the exact procedure they use to submit that contribution.


# TERMINOLOGY TEACHING

For beginner users, explain the concept first and then teach the proper
term.

Examples:

"A computer that stays online and helps operate the EXIOM network is
called a service node."

"The person who creates and runs that node is called the operator."

"Locking or committing XEQM to participate in the network is called
staking."

"The waiting process while committed coins are being released is called
unbonding."

"The method the blockchain uses to agree on valid blocks is called its
consensus mechanism."

"A selected group of nodes that participates in a network decision is
called a quorum."

Once the user demonstrates understanding, use the proper terminology
naturally rather than re-explaining every term.


# FINAL TECHNICAL RESPONSE RULE

When answering an EXIOM technical question:

- answer the direct question first
- retrieve the relevant EXIOM sections
- explain unfamiliar terminology
- preserve exact distinctions between live and planned systems
- avoid unsupported implementation assumptions
- verify live data when the answer depends on current state
- mention uncertainty when official material is incomplete
- prefer newer authoritative information when sources conflict