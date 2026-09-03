# EXIOM KNOWLEDGE CONFLICT AND CHANGE LOG

This file records important cases where official EXIOM/XEQM information
changed, conflicted, or requires status-sensitive interpretation.

EXIOM AI must not silently combine contradictory claims.

---

# 2026-07 — XEQM SUPPLY MODEL

## Older official statement

The XEQMLabs AI Instructions page dated July 18, 2026 described the
approximately 276 million XEQM supply using fixed-supply language and
stated that no future mints were planned.

## Newer official statement

XEQMLabs Technical Whitepaper Draft v11 dated July 26, 2026 states that:

- 276,917,604 XEQM was the starting mainnet supply
- total supply grows through scheduled protocol emissions
- service-node rewards create protocol emissions
- governance emissions also increase supply
- the model is uncapped
- there is no intended arbitrary/discretionary issuance

## Resolution

Use the July 26, 2026 technical whitepaper for current supply-model
explanations.

Do NOT describe 276,917,604 XEQM as the permanent maximum supply.

Explain that it was the starting mainnet supply.

---

# 2026-07 — "NO MINTING" TERMINOLOGY

Some older material can make "no minting" sound equivalent to
"no new XEQM can ever be created."

That interpretation is incompatible with the newer documented emission
model.

## Resolution

Distinguish:

DISCRETIONARY ISSUANCE:
Someone arbitrarily creating additional XEQM outside the scheduled
protocol rules.

PROTOCOL EMISSIONS:
New XEQM created according to predetermined network rules such as
service-node and governance emissions.

Current documentation rejects discretionary issuance but includes
scheduled protocol emissions.

---

# 2026-07 — MAINNET VS FUTURE PLATFORM FEATURES

EXIOM mainnet, the service-node network, wallet, and explorer are live.

However, several ecosystem components described by XEQMLabs are not all
production-live.

## Current status interpretation

Developer API:
ACTIVE DEVELOPMENT

Privacy Oracle:
DESIGNED / PRE-IMPLEMENTATION

RFQ platform:
IN DEVELOPMENT

HF22:
TESTNET / DEVELOPMENT STATUS ACCORDING TO THE JULY 26 WHITEPAPER

HF23:
DESIGN PHASE

Lokinet:
CODE EXISTS / ACTIVATION UNDER ENGINEERING ASSESSMENT

Formal on-chain governance:
PLANNED

## Resolution

Never describe the existence of documentation or source code as proof
that a feature is already active on mainnet.

---

# 2026-07 — HF21 REWARD DISTRIBUTION

The mandatory XEQM Core v1.0.7 release activated HF21 at block 99,000.

HF21 changed service-node reward batching to a 10,080-block cycle,
approximately seven days at the documented 60-second block interval.

It also established a 1 XEQM minimum batch payout threshold according to
the release information.

## Resolution

Do not tell users that service-node rewards necessarily arrive daily.

Separate:

reward accrual

from:

reward payout/batching.

---

# DYNAMIC NETWORK VALUES

Official documents contain dated snapshots of values such as:

- active service-node count
- number of operators
- Nakamoto coefficient
- supply
- software version
- network concentration

These values can change.

## Resolution

When the user asks:

"right now"
"today"
"current"
"latest"
"how many nodes are there"
"what is the price"
"what version is EXIOM running"

do not use a dated snapshot as though it were live.

Use the future live-data layer or explicitly say live verification is
required.

---

# EXCHANGE AVAILABILITY

Official historical material references XEQM trading availability,
including NonKYC.

Exchange markets, deposits, withdrawals, and pairs can change.

## Resolution

Stored knowledge can explain historical availability.

Current buying instructions require live verification.

Never send a user to an exchange or trading pair based solely on a stale
stored record.

---

# SERVICE-NODE COMMUNITY CONTRIBUTION

The current documented minimum community contributor amount is:

10,000 XEQM.

This has sometimes been misunderstood as meaning a contributor can only
provide exactly 10,000 XEQM.

## Resolution

10,000 XEQM is the minimum contributor-slot amount.

It is not inherently the maximum contribution.

A participant may contribute more where sufficient unfilled stake remains
within the service node's total 200,000 XEQM requirement.

---

# PROCEDURAL KNOWLEDGE

Knowing a protocol requirement does not automatically establish the exact
user procedure.

Example:

Knowing that community participation can begin at 10,000 XEQM does not
prove which address, command, wallet screen, transaction type, or
registration procedure must be used.

## Resolution

EXIOM AI must not invent operational steps.

Procedural instructions require verified EXIOM-specific documentation.

---

# SOURCE PRIORITY

When information conflicts, use this order unless a specific case requires
different treatment:

1. newer mandatory XEQM Core production release / implementation
2. newer XEQMLabs technical whitepaper
3. newer official technical documentation
4. official live explorer for dynamic network state
5. older official explanatory material

A newer source does not automatically make every older fact false.

Only supersede the conflicting fact.

---

# WHITEPAPER STATUS

The July 26, 2026 whitepaper is Draft v11.

Therefore future architecture, economics, hard-fork parameters, roadmap
dates, and platform designs can change.

## Resolution

EXIOM AI should use the whitepaper as authoritative technical design
documentation while preserving its draft status.

When production implementation later differs from the draft, production
implementation wins.