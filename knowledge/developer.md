# EXIOM DEVELOPER PLATFORM

## Developer API: status and features

LIVE IN BETA (Phase 2, active, as of Sep 27, 2026). The EXIOM Developer API exposes the platform's compliance and verification features: platform-signed compliance claims and a verification engine (signed claims, TLSNotary and zero-knowledge mechanisms). Self-serve access: a DID plus an API key. OpenAPI 3.1 specification at api.exiom.network/docs; base URL https://api.exiom.network. It supports webhooks and idempotent requests. Every XEQMLabs application uses the same public API as outside developers. Still to come in Phase 2: prepaid consumption billing, the operator revenue share, first production integrations.

Sources: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper), [EXIOM API Sample Applications](https://github.com/XEQMLabs/exiom-samples)

## API pricing and access tiers (prepaid usage)

Current model (whitepaper v12): build free, pay per call in XEQM. There is no stake to unlock access.
- Free: build and evaluate at no cost, a generous monthly call allowance, no deposit.
- Production: prepaid usage. Deposit XEQM and pay per call; webhooks and higher limits.
- Enterprise: custom limits, SLA, support, volume terms.
Deposits are non-refundable and count as platform revenue as they are used. Prepaid per-call billing was still rolling out on Sep 27, 2026. The earlier design gated tiers behind a refundable XEQM stake (Free none / Builder 1,000 / Production 10,000 / Enterprise 50,000 XEQM, with call quotas); whitepaper v12 replaced it, though older pages (FAQ, developer-platform blog, GitBook tokenomics) still show it.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Platform revenue and fee split

The XEQM that developers spend on production usage is platform revenue, split:
- 70% to oracle sidecar operators (service node operators running the oracle sidecar, in proportion to the oracle duties they serve).
- 30% to platform operations and development.
The 70/30 ratio is the starting value and governance can adjust it. It is paid on the same weekly 10,080-block cycle as block rewards. It replaces the earlier 35% API node operators / 35% XEQMLabs treasury / 30% community governance split that older pages show.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## API sample applications (exiom-samples)

Runnable, copy-ready samples for the API (github.com/XEQMLabs/exiom-samples):
- kyc-gate: issue a platform-signed compliance claim (jurisdiction eligibility) behind a backend and gate an action on it (TypeScript, Python).
- policy-verification: call the verification engine (`/v1/verifications`) and handle every outcome (TypeScript, Python).
- wallet-ownership: prove a user controls an external wallet (MetaMask) and bind it to a DID (TypeScript).
- credentials: issue a credential and present selected fields only, selective disclosure (TypeScript, Python).
- confidential-envelope: end-to-end encrypted store-and-forward with libsodium sealed boxes (TypeScript, Python).
API key: header `X-XEQM-Api-Key`, keys start with `xeqm_live_`. Rules the samples follow: never put the key in browser code (keep it on a backend); send an `Idempotency-Key` on writes; handle `application/problem+json` errors (check status, read `detail`); raw fetch/requests, light on dependencies. CI smoke-tests them against the live API.

Source: [EXIOM API Sample Applications](https://github.com/XEQMLabs/exiom-samples)

## EXIOM Oracle (live)

LIVE ON MAINNET. The platform's first oracle: a committee of XEQM service node operators, each running a lightweight oracle sidecar, producing BLS-aggregate, EIP-712 signed attestations about compliance facts, mainly whether an address is eligible for a given jurisdiction. Apps consume them through the developer API and can submit the signed result on-chain. Deployed on Robinhood Chain (chainId 4663) with a 12-member operator committee as of Sep 28, 2026 and a two-thirds signing threshold (8 of 12).

Security model: every registered member signs every round (no sampled committee). Forgery needs k = ceil(2N/3) colluding members (an operator-concentration question); a halt needs floor(N/3)+1 members offline at once (an infrastructure question). Honest current state: on Sep 28, 2026 all members were run by the project operator, so its operator coefficient is 1 and forgery resistance rests on trust in one operator. It hardens as independent operators on distinct facilities enroll; admission keeps every operator below k and every facility at or below floor(N/3), and the forgery and liveness margins are published.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Oracle sidecar for node operators

A service node operator can run the oracle sidecar alongside the node to earn extra, usage-based revenue on top of block rewards: their share of the 70% of platform revenue, paid weekly with block rewards. The sidecar is deliberately light: it holds only its own signing key, reads its node's identity locally and never touches the operator's spend keys. Baseline hardware for a node plus its sidecar: 4 CPU cores, 8 GB RAM, 100 GB SSD, 100 Mbps. Future verifier revenue streams: block rewards, platform revenue share, oracle session fees, and an oracle duty bonus from governance emission during low-volume periods. The docs do not publish sidecar install steps.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## EXIOM Privacy Oracle (Phase 3)

Foundations live (verification engine, oracle sessions); the full product is a Phase 3 deliverable, after Phase 2 stabilizes and a cryptography consultation. It proves facts about private web data from standard HTTPS sources with TLSNotary and zero-knowledge techniques, needing no cooperation from the source server and no trusted hardware. Uses: price thresholds without revealing prices, balances without exposing credentials, compliance without disclosing records.
- Prover: holds the data access; commits to the TLS response without revealing it.
- Verifier: a rotating quorum of service nodes learns only the result (true/false, above/below).
- Consumer: gets only a boolean, threshold, signed attestation or small derived value.
Rollout: internal proof of concept, federated testnet, mainnet with internal consumers (fees start), then external access (Phase 4, Production and Enterprise developers). Verifier hardware: 8 CPU cores, 16 GB RAM, 200 GB SSD, 500 Mbps low latency.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## EXIOM RFQ trading platform

IN DEVELOPMENT. A peer-to-peer over-the-counter (Request for Quote) trading platform with cryptographic settlement attestations, built on the EXIOM API. First pair: XEQM/BTC, both native Layer 1 assets (no wrapping, no bridge). The oracle lets a counterparty prove a fill was at or better than a reference price without revealing the exact price. Specification and data model are complete; API-layer work is in Phase 2; production is a Phase 3 deliverable. With Lokinet it becomes a hidden service hiding requester and liquidity provider IPs.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Platform architecture: EXIOMoracle, EXIOMnet, service network

The platform whitepaper describes three capabilities: EXIOMnet (private multi-hop network transport, built on LLARP), developer infrastructure exposing network services, and EXIOMoracle (quorum-backed answers about external information with minimal disclosure). Flow: application request, external data or proof, service node quorum, verified result back to the app: a boolean, threshold, derived value or signed attestation. Service nodes evolve from securing the chain to serving paid workloads (oracle quorums, attestations, private transport). EXIOM is positioned as privacy-focused B2B infrastructure for builders, a narrower segment than Chainlink rather than a replacement for it. Development is driven by a first, undisclosed application integration.

Source: [EXIOM Platform Whitepaper](https://xeqmlabs.com/blog/exiom-platform-whitepaper)

## What you can build: reference applications

XEQMLabs plans privacy-native reference apps on the same public API: EXIOMswap (chain migration, used for XEQ to XEQM), EXIOMoracle (signed feeds, proof of reserve, private conditional execution), EXIOMproof (proof an event happened), EXIOMaccess (private-token access control), EXIOMident (credential, age or membership proofs), EXIOMballot (private voting), EXIOMsource (confidential document submission), EXIOMsurvey (anonymous verified feedback), EXIOMpulse (private data aggregation), EXIOMvault (dead man's switch), EXIOMpay (one-time payment links), EXIOMpayroll (private disbursements), EXIOMhold (private escrow). These come from the vision document; besides the swap and the oracle, treat them as planned.

Source: [The XEQMLabs Vision](https://xeqmlabs.com/blog/xeqmlabs-vision)
