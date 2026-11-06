# HARD FORKS AND CORE RELEASES

## Latest core release and upgrade deadline

The latest XEQM Core release is v1.1.2 "Ragnarok" (Oct 12, 2026). It is mandatory before HF22 revision 1 (Pulse-recovery) activates at mainnet block 236,920 (~Oct 18, 2026 19:00 UTC). Nodes on v1.1.0 go straight to v1.1.2; nodes on v1.1.1 must update again (both behave the same until that block). v1.1.2 fixes the reward of signed fallback blocks: under v1.1.1 they were missing the service node reward (only transaction fees), so other nodes would have rejected them and the chain would have stalled at the first failover. GUI wallet v2.3.3 bundles it. Docker: `ghcr.io/xeqmlabs/xeqm-node:v1.1.2` (also `latest`). Newer releases may exist: the release page has the current one.

Release history: v1.0.5 (Jun 2), v1.0.6 (Jun 15), v1.0.7 (Jul 7, HF21), v1.1.0 (Sep 23, HF22), v1.1.1 (Oct 8, Pulse-recovery), v1.1.2 (Oct 12).

Source: [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)

## HF21: weekly reward batching

HF21 activated at block 99,000 (~Jul 14, 2026) with the mandatory v1.0.7 release. Reward batching went from every 20 blocks (~20 minutes) to every 10,080 blocks (~7 days); each wallet keeps a fixed payout slot computed from its address; the minimum batch payout rose from 0.1 to 1 XEQM (smaller balances keep accruing, never lost). This cut on-chain transactions and dust outputs. v1.0.7 also fixed node wedging under transaction bursts and self-decommission during heavy sync, and added the xeqm-mdb_copy and xeqm-mdb_stat tools.

Source: [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)

## HF22: one seat per operator (sn_policy)

LIVE since mainnet block 219,120 (~Oct 5, 2026), with mandatory v1.1.0. Consensus changes:
- One validator seat per operator: Pulse, obligations, checkpoint and blink quorums count distinct operator wallets; a duplicate seat is refilled with a node from a different operator, so quorum sizes stay 10/20/10. Pulse skips a block when fewer than 12 distinct operators are available. Block rewards are unaffected (wait-time ordering).
- Forced deregistration lock raised from 7 to 14 days, matching voluntary unlock.
- Authorized fallback blocks: if two Pulse rounds fail (60 s), the chain accepts a block only from one of three authorized fallback miners on independent hosts (mined with proof-of-work, which took minutes). HF22 itself kept these 2 rounds and mined fallback blocks: the 4 rounds and instantly signed fallback blocks came later, with revision 1 (Pulse-recovery, below).
- Uptime proofs require v1.1.0.
Known limit: an operator using several wallet addresses still gets several seats; HF23 closes this. v1.1.0 also stopped wallets fetching rings from untrusted daemons and made `use_ssl` wallets connect over HTTPS. Validated on testnet: nine stall/recovery cycles, 100% recovery.

Sources: [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases), [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## HF22 revision 1: Pulse-recovery

Activates at block 236,920 (~Oct 18, 2026 19:00 UTC / 12:00 PT); needs v1.1.1 or newer (v1.1.2 fixes its fallback reward). Changes:
- Pulse gets 4 rounds instead of 2 before handing off; each round draws a fresh quorum and leader.
- When Pulse gives up, an authorized fallback host signs the next block and publishes it at once, with no proof-of-work mining (same fallback-key signature HF22 required).
- A non-Pulse block without a valid authorized signature is rejected before it is stored.
Effect: stall recovery goes from minutes to seconds, and the chain no longer depends on a fallback host staying up. A node still on v1.1.0 at that block rejects the new blocks, forks off, has its uptime proofs refused and gets decommissioned.
v1.1.1 also fixed memory: nodes that verified a mined fallback block held a 256 MB RandomX cache forever (the 3x RAM jump since HF22); it is freed after 10 idle minutes. Restart after upgrading. Operators running many nodes on few machines should spread them out: concentrated fleets that swap or restart together cause most failed Pulse rounds.

Source: [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)

## HF23: proximity clusters (planned)

IN DESIGN, targeted Q4 2026; depends on Lokinet as the network transport (committed to HF23, implementation begins Q4 2026). Planned:
- Cluster registration cap: nodes that look physically co-located on Lokinet (sub-millisecond mutual latency, high path overlap) form a proximity cluster; a registration into a cluster already holding 30% or more of active nodes is rejected (~283 nodes at 943).
- Zero-reward modifier: nodes above the cap earn zero block rewards until moved; within a cluster the oldest nodes (registration age) up to the cap keep full rewards. A 30-day grace period with full rewards applies at activation.
- Quorum dedup by proximity cluster instead of wallet: one node per cluster per round, closing the wallet-splitting gap. With fewer than 12 distinct clusters, extra seats go to the smallest clusters first; fallback frequency is logged and published on the explorer as a concentration-risk indicator.
None of this is active on mainnet yet.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Lokinet and EXIOMnet

Lokinet (LLARP, Low Latency Anonymous Routing Protocol) is a layer 3 onion-routing protocol: IP traffic goes through several service nodes, and no single node in the path knows both origin and destination. The LLARP code is in the EXIOM repository; it is NOT active yet. It is committed as HF23's network transport (target Q4 2026). Once active: service nodes are addressed by Lokinet cryptographic IDs instead of public IPs; the developer API and the RFQ platform become hidden services at `.loki` addresses, hiding users' IPs; oracle prover-verifier traffic is onion-routed. EXIOMnet is the platform name for this private multi-hop transport for EXIOM services.

Sources: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper), [EXIOM Platform Whitepaper](https://xeqmlabs.com/blog/exiom-platform-whitepaper)

## Core binaries, Docker image and building

XEQM Core ships three binaries: `xeqm-d` (daemon: full node or service node), `xeqm-wallet` (CLI wallet) and `xeqm-rpc` (wallet RPC server). Releases cover Linux x86_64 (Ubuntu 24.04+ and 22.04), Linux aarch64, Windows x64, and macOS Apple Silicon and Intel (signed, notarized .pkg). Each file has a `.sha256` companion to verify. Linux builds are statically linked (need only glibc and libstdc++). Docker image: `ghcr.io/xeqmlabs/xeqm-node:<tag>`. Build from source: `git clone --recursive --branch core-v1.1.2 https://github.com/XEQMLabs/xeqm-core.git`, then `cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_STATIC_DEPS=ON -DBoost_NO_BOOST_CMAKE=ON` and `make` in a build folder; binaries land in build/bin/. A plain full node (not a service node) needs P2P 9230 and RPC 9231. License: BSD 3-Clause.

Source: [XEQM Core](https://github.com/XEQMLabs/xeqm-core)
