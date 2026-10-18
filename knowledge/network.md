# NETWORK SECURITY, DECENTRALIZATION AND ROADMAP

## Nakamoto coefficient and operator count

The operator Nakamoto coefficient is the minimum number of operators who together control a majority of active nodes. On Sep 27, 2026: 9 across 943 active service nodes and 204 operators, meeting the target of 8 or more (up from 7 across 693 nodes and 184 operators in July 2026). Physical concentration is a separate, sharper problem: one datacenter region still hosts a majority of nodes, which HF23's cluster cap targets. These are dated snapshots; the Explorer has the live node count.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Network survivability and the 30% cap

EXIOM promises developers reliability, so no single facility, datacenter or routing cluster may host more than 30% of active nodes. At 943 nodes that is ~283: losing one facility leaves at least 660 nodes, enough to keep producing blocks and forming quorums without cascading decommissions. It is an engineering requirement, not a decentralization preference. Enforcement comes in two stages: HF22 (live: one quorum seat per operator wallet) and HF23 (planned: proximity cluster cap, zero-reward modifier, cluster dedup over Lokinet).

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Sybil resistance

A Sybil attack is one actor running many nodes as seemingly separate identities. On a privacy chain, wallet-graph analysis cannot expose common funding, so EXIOM relies on other defenses:
- Capital per identity: every node needs 200,000 XEQM, at least 100,000 from the operator; N nodes need at least N x 100,000 XEQM. Wallet splitting doesn't lower that.
- Unbonding friction: 14 days for voluntary and forced exits.
- Public registry: every node's registration key and operator wallet are public.
Concentration signals: registration-key clustering (same operator wallet = same operator); IP and subnet clustering; uptime-proof timing (nodes on one host send proofs within ~10 ms); ASN concentration (shared provider); and, after HF23, Lokinet routing proximity. Also a governance-managed blocklist of registration keys, and contributor-slot graph analysis.
Two attack types: consensus influence (too many quorum seats) and failure domain (too many nodes in one facility).

Source: [Sybil Risk and EXIOM's Mitigation Model](https://github.com/XEQMLabs/xeqm-sybil-resistance)

## Wallet splitting: the residual risk

An operator spreading nodes across many wallets at one facility is still exposed by proof timing, IP/ASN and (after HF23) Lokinet proximity. An operator genuinely spread across different providers and countries looks like separate operators: that is the residual risk. It is bounded: HF23 dedup gives each proximity cluster at most one quorum seat per round, and such an operator's block rewards only scale with the capital they staked. Some large deployments (58 and 51 nodes from single IPs) were confirmed single operators through registration keys (July 2026).

Source: [Sybil Risk and EXIOM's Mitigation Model](https://github.com/XEQMLabs/xeqm-sybil-resistance)

## Governance

Today governance is led by the founding team, with community input in open Telegram channels and GitHub discussions. The governance wallet address and view key are published. Phase 3 brings a formal proposal and comment process; Phase 6 brings weighted voting, where service node and API node operators hold formal rights in proportion to stake and tenure, and a long-term move away from founding-team governance. Formal on-chain governance is PLANNED, not live.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Roadmap phases

- Phase 1, network stabilization: COMPLETE (943 nodes on Sep 27, 2026; the swap ran and closed).
- Phase 2, developer API and EXIOM Oracle: ACTIVE. Oracle live with an operator committee; API in beta. Remaining: prepaid billing, operator revenue share, first production integrations. RFQ development in parallel.
- Phase 3: Privacy Oracle rollout (internal proof of concept, federated testnet, mainnet with internal consumers) and RFQ in production; formal proposal process.
- Phase 4: external oracle access for Production and Enterprise developers (the Nakamoto threshold of 6 is already met; waits for Phase 3).
- HF22: live since Oct 5, 2026; Pulse-recovery revision at block 236,920. HF23: target Q4 2026.
- Phase 6: formal governance with weighted operator voting.
XEQMLabs aims to finish the current decentralization work by the end of 2026. Roadmap dates are intended design and can change.

Sources: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper), [EXIOM Platform Whitepaper](https://xeqmlabs.com/blog/exiom-platform-whitepaper)
