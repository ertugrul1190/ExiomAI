# SERVICE NODES

## What a service node does

A service node is an always-online server that stakes XEQM and operates the network: it validates and relays transactions, enforces privacy at the network layer, takes part in Pulse consensus and checkpoints, powers Blink fast transactions, and handles routing, peer discovery and sync. Regular nodes observe the network; service nodes operate it. The person who registers and runs one is its operator. Service nodes are also the base of the platform: the EXIOM Oracle sidecar runs alongside them.

Source: [Service Nodes (SN)](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn)

## Staking requirements, pool nodes and operator fee

The stake is a flat 200,000 XEQM per node, the same across all hard forks.
- Solo node: the operator stakes all 200,000 XEQM.
- Pool (open / shared) node: the operator stakes at least 100,000 XEQM (50%); up to 10 contributors fill the remaining 100,000. Maximum 11 stakers including the operator.
- Minimum community contribution: 10,000 XEQM per contributor slot (100,000 is the operator's minimum, never a contributor's). That is a minimum, not a fixed amount: a contributor can stake more while the node has room.
- Operator fee (operator cut): 0% to 10% of the node's rewards (not of the stake), so contributors keep at least 90% of their proportional share. The 10% cap plus the 50% operator stake stop the "100% fee" capture attack seen on some networks.

Sources: [Service Nodes (SN)](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn), [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Staking as a contributor in a pool node

With less than 200,000 XEQM you can contribute to another operator's open node (minimum 10,000 XEQM per contributor) and earn rewards in proportion to your stake, minus the operator's cut (stake 10% of the node, earn roughly 10% of the post-fee reward). Contributors pay no hosting costs.

How, per the operator guide: find open nodes on the Explorer (explorer.xeqmlabs.com) or with the daemon's get_service_nodes RPC (nodes whose total_contributed is below staking_requirement), then in the XEQM CLI wallet run `stake <service_node_pubkey> <amount>` (e.g. `stake <pubkey> 50000`) or `stake <service_node_pubkey> 50%` (50% of the remaining stake), and confirm. The GUI wallet also supports service node staking.

Risks: rewards depend on the operator's uptime (a decommissioned node earns nothing); the stake stays locked while the node runs; you cannot withdraw part of a contribution on demand, and an unstake takes 14 days (rewards keep coming during those 14 days). Choose operators with solid uptime history on the Explorer.

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## When a node starts earning

After the registration transaction confirms, `get_service_nodes` shows active, funded and payable. A node is active once fully staked (a pool node usually about 10 blocks after the final contribution). `payable: false` while `active: true` is normal for the first 4 blocks: a short grace period before rewards begin. Rewards then accrue each block and pay out weekly (HF21 batching). Nodes have no renewal: they run indefinitely until the operator or a contributor unstakes.

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Uptime proofs

The daemon submits an uptime proof every 10 minutes. If no proof has been accepted within 21 minutes, the obligations quorum considers the node offline. Short blips are absorbed; an outage over ~20 minutes starts using decommission credits. In `get_info`'s status line, `proof: 2m3s` is the age of the last accepted proof: healthy is under 2 minutes, over 30 minutes risks decommission. Since HF22, uptime proofs require v1.1.0 or newer, so an outdated node gets decommissioned.

Sources: [Service Nodes (SN)](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn), [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Decommission credits (outage budget)

Credits are an outage budget earned by staying online:
- New node: 2 hours of credit.
- Earned: 48 minutes per day online.
- Cap: 48 hours.
- Threshold: 2 hours. A node that fails a test is only decommissioned if it still has at least 2 hours of credit; with less than 2 hours it is deregistered.

So a new node can be offline up to 2 hours right after registering with no permanent consequence, and a long-running node with maxed credits up to 48 hours and still recover. In `get_service_nodes`, `earned_downtime_blocks` is this credit and should grow over time.

Source: [Service Nodes (SN)](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn)

## Decommission vs deregistration (penalties)

Decommissioned and deregistered are different: a decommissioned node keeps its stake in place and comes back by itself; only a deregistered node has its stake locked for 14 days. How long a node can stay offline depends on its decommission credits: 2 hours for a new node, up to 48 hours once maxed.
- Temporary decommission: the node failed a test but still had credits. It stops earning, the stake stays in place, and once it is back online with fresh proofs a quorum automatically recommissions it (usually within ~30 minutes). It can be fixed without penalty; this replaced the legacy chain's 28-day lockout, and there are no reward lockouts for minor downtime.
- Permanent (forced / involuntary) deregistration: the credits ran out. The node leaves the network, its credits are forfeited, pending rewards are lost, and its key images are blacklisted from re-registering until the stake lock ends.

The official docs describe no slashing: a deregistered node's stake is locked (14 days since HF22) and can then be withdrawn; what is lost is the credits, the pending rewards and the earnings while offline.

Sources: [Service Nodes (SN)](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn), [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Hard fork grace period and deactivation safeguards

- Post-fork grace period: for 5 days after any hard fork, only temporary decommissions happen, never permanent deregistrations, so operators have time to upgrade without risking their stake.
- At most 1 service node can be decommissioned or deregistered per block, even if many fail at once. This prevents cascades and gives operators time to react.
- Pulse needs at least 12 active service nodes, which is why the rate limit matters most during bootstrap and right after forks.

Source: [Service Nodes (SN)](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn)

## Stake lock and unbonding periods

- Voluntary unstake: 14 days. The node keeps operating and earning rewards during the wind-down.
- Forced deregistration: 14 days with no rewards. HF22 (Oct 5, 2026) unified it with the voluntary period; it was 7 days before HF22, which older docs still show.
A contributor who unstakes: their portion enters the 14-day unlock before it can be spent.

Sources: [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases), [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Quorum tests a node must pass

Rotating quorums test every service node on:
- Uptime proofs: reachable and submitting fresh proofs (21-minute validity).
- Pulse votes: taking part in block production, at most 4 missed out of the last 8.
- Checkpoint votes: signing chain checkpoints, at most 4 missed out of the last 8.
- Timestamp votes: clock agrees with the network, at most 4 missed out of the last 8.
Failing any one test uses credits; with credits left, the worst outcome is a temporary decommission. Since HF22, Pulse, obligations, checkpoint and blink quorums count distinct operator wallets; dropped duplicate seats are refilled so quorum sizes stay 10/20/10, and a Pulse round has 12 seats.

Sources: [Service Nodes (SN)](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn), [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)
