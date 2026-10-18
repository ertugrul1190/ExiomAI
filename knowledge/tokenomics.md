# XEQM TOKENOMICS

## Supply: starting supply and growth

276,917,604 XEQM is the verified starting supply at mainnet launch (May 6, 2026), issued once at the end of the swap to match the verified legacy deposits. It is NOT a maximum. XEQM is uncapped, with predictable emissions like Monero's tail emission: total supply grows through two scheduled protocol streams, service node block rewards and governance emissions, that anyone can compute from public parameters. "Fixed-supply discipline" means no discretionary issuance: no ad-hoc mints, manual supply changes or off-schedule mints. Older pages call the ~276M supply "fixed" with "no future mints planned"; whitepaper v12 supersedes that wording. The Explorer has the current supply.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## No coin burns

XEQM does not burn coins and XEQMLabs does not claim burns. The Monero-based architecture cannot prove a burn: an address is only as unspendable as its key is demonstrably destroyed, so no wallet is ever presented as a burn address. Legacy XEQ not swapped during the migration window stayed on the inactive legacy chain and is not part of XEQM supply.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Block reward and daily emissions

- Block time: 60 seconds (about 1,440 blocks a day).
- Service node block reward: 8.25 XEQM per block, paid to the selected service node and split among its operator and contributors. That is 11,880 XEQM a day across the whole network, not per node.
- Foundation / governance: 12.4 XEQM per block, so 20.65 XEQM in total per block.
- All new XEQM per day, both streams: 20.65 x 1,440 = 29,736 XEQM (11,880 to service nodes + ~17,857 to governance).
11,880 assumes exactly 1,440 blocks a day. The Explorer's "SN rewards (24h)" is what was actually paid in the last 24 hours (blocks produced x 8.25), so it can differ: for a live figure, use the Explorer's.

Sources: [Tokenomics](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/tokenomics), [Service Nodes (SN)](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn)

## Governance emission and treasury allocation

The treasury receives ~17,857 XEQM a day (~124,999 a week), the operating budget of a commercial development team while the platform is pre-revenue. It is reviewed and reduced as products earn revenue; the goal is for platform revenue to replace it. The governance wallet address and view key are published, so anyone can verify the balance.

Emission allocation (target shares; governance can adjust them):
- Service node rewards 40%
- Core protocol development 25% (blockchain, API, oracle, RFQ)
- Marketing and awareness 15% (listings, content, growth)
- Ecosystem and community 10% (grants, bounties, integrations)
- Security and audits 5%
- Long-term reserve 5%

Sources: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper), [Tokenomics](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/tokenomics)

## Node earnings, staking APY and hosting cost

Dated estimate, not a promise: per-node block rewards scale inversely with the active node count. At 943 active nodes (Sep 27, 2026): 11,880 / 943 is about 12.6 XEQM per node per day, about 380 XEQM per month. Because reward and stake are both in XEQM, the block-reward APY of a solo node is about 2.3%, whatever the price (it was ~3.1% at 700 nodes). Today's figure is 11,880 divided by the Explorer's active node count, split among the node's stakers minus any operator fee.

Hosting: many cloud free tiers can run a node at no cost; a ~$5.28/month VPS can run 10 nodes (~$0.53 per node per month); managed hosting through Pecunia costs $1.76 per node per month. Contributors pay no hosting. Running the oracle sidecar adds a usage-based second income (see EXIOM Oracle).

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Reward payouts: weekly batching (HF21)

Since HF21 (block 99,000, July 2026), service node rewards accrue every block but are paid in weekly batches: each 10,080-block window (~7 days). Each wallet has a fixed payout slot in the cycle, computed from its address. The minimum batch payout is 1 XEQM (was 0.1); smaller balances are never lost, they keep accruing until they pass 1 XEQM and pay at the next slot. Before HF21, rewards were paid every 20 blocks. Total emission did not change, only the payment rhythm. (An older pool-staking page says "every 3.5 days"; HF21's weekly cycle is current.)

Source: [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)

## Staked and circulating supply

At 943 active nodes (Sep 27, 2026), about 188,600,000 XEQM (~68% of the starting supply) is locked in service node stakes, leaving ~88,300,000 freely circulating, growing with emissions. XEQM demand comes from three places: node staking (the largest share), developers paying for API usage in XEQM, and oracle access for heavy users. The Explorer has the live locked and circulating figures.

Source: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper)

## Long-term inflation strategy

Emissions are predictable but not meant to stay at today's level forever. As the platform earns fee revenue, governance emissions are meant to come down so the network relies less on issuance: "the more useful the platform becomes, the less it needs to dilute holders". XEQMLabs presents this as a design principle, not a promise.

Source: [Tokenomics](https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/tokenomics)
