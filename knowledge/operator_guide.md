# SERVICE NODE OPERATOR GUIDE

## Setup steps overview

The official setup path uses Docker, about 30 to 60 minutes the first time: 1) install Docker; 2) create a working folder and pull the image `ghcr.io/xeqmlabs/xeqm-node:latest`; 3) start the service node daemon; 4) wait for sync; 5) create a wallet and fund it (solo: 200,000 XEQM; pool node: the operator at least 100,000, then contributors fill the rest with at least 10,000 each; plus a small fee); 6) generate the registration command from the daemon; 7) paste it into the wallet CLI and confirm. A self-built binary follows the same steps without Docker (same flags). The core README also documents a `prepare_registration` daemon command that prompts for the fee and reserved contributors and prints a command for the wallet.

Sources: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide), [XEQM Core](https://github.com/XEQMLabs/xeqm-core)

## Hardware and hosting requirements

Every official page wants an always-on machine with a public static IP (a home connection whose IP changes drops the node) and stable internet. The figures differ by page:
- Whitepaper baseline (node plus oracle sidecar): 4 CPU cores, 8 GB RAM, 100 GB SSD, 100 Mbps.
- Operator guide, startup page: 8 GB RAM, 2+ CPU cores, 200 GB disk recommended ("smaller works for now").
- Operator guide, intro: 2 GB RAM minimum, 4 GB recommended, 10 to 20 GB free disk.
- Core README: 2 vCPU, 4 GB RAM, 80 GB SSD, 1 Gbps is comfortable; CPU is low once synced, RAM is mostly the LMDB database.
Recommend the whitepaper baseline for a new node. Oracle verifier duty needs more (8 cores, 16 GB, 200 GB SSD, 500 Mbps). Typical providers: DigitalOcean, Hetzner, Vultr.

Sources: [EXIOM Tokenomics Whitepaper](https://github.com/XEQMLabs/whitepaper), [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide), [XEQM Core](https://github.com/XEQMLabs/xeqm-core)

## Ports and firewall

- 9230/TCP P2P: public, must be reachable from the internet.
- 9231 admin RPC: local only, never expose it publicly.
- 9232/TCP quorumnet (SN-to-SN messaging for Pulse, votes, timestamp tests): public, must be reachable by other service nodes.
- 9233 public OMQ: optional, public if enabled.
- 9234 wallet RPC: local only.
Open inbound 9230/TCP and 9232/TCP in the machine's firewall and the router/cloud firewall. To run several nodes on one host, give each daemon its own quorumnet port (9232, 9242, 9252...). Several nodes on one host is a documented setup: each needs its own full stake and keeps earning block rewards. Since HF22 one operator's nodes share one quorum seat per round (a quorum-seat limit, not a ban, and rewards are unaffected); spreading large fleets across machines makes failed Pulse rounds less likely. Community public nodes serve wallet RPC over HTTPS on 443 instead (see Community public nodes).

Sources: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide), [XEQM Core](https://github.com/XEQMLabs/xeqm-core)

## Install Docker

- Windows: install Docker Desktop from docker.com, restart, launch it and wait for the whale icon; check with `docker --version` in PowerShell.
- Linux (Ubuntu/Debian): `curl -fsSL https://get.docker.com | sh`, then `sudo usermod -aG docker $USER`, then `newgrp docker` (or log out and in), then `docker --version`.
"Cannot connect to the Docker daemon" on Linux: `sudo systemctl start docker` and `sudo systemctl enable docker`. "Permission denied": add your user to the docker group as above and log in again.

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Start the service node daemon (Linux)

```
mkdir -p ~/xeqm-sn01 && cd ~/xeqm-sn01
docker pull ghcr.io/xeqmlabs/xeqm-node:latest
docker run -d --name sn01 --restart unless-stopped --network host \
  -v "$(pwd)/data:/data" ghcr.io/xeqmlabs/xeqm-node:latest \
  --service-node --data-dir=/data --p2p-bind-ip=0.0.0.0 --p2p-bind-port=9230 \
  --rpc-admin=127.0.0.1:9231 --service-node-public-ip=YOUR_PUBLIC_IP \
  --quorumnet-port=9232 --add-priority-node=seeds.xeqmlabs.com:9230 \
  --log-level=2 --non-interactive
```
Replace YOUR_PUBLIC_IP (find it with `curl ifconfig.me`). Watch it sync with `docker logs -f sn01` (Ctrl+C leaves the container running).

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Start the service node daemon (Windows)

Windows Docker has no host networking, so ports are mapped and the admin RPC binds differently: in PowerShell, `mkdir C:\xeqm-sn01; cd C:\xeqm-sn01`, then `docker run -d --name sn01 --restart unless-stopped -p 9230:9230 -p 127.0.0.1:9231:9231 -p 9232:9232/udp -v "${PWD}/data:/data" ghcr.io/xeqmlabs/xeqm-node:latest` with the same flags as Linux except `--rpc-admin=0.0.0.0:9231` (PowerShell continues lines with a backtick). The `127.0.0.1:9231:9231` mapping keeps the admin RPC on the host's loopback, while `0.0.0.0:9231` inside the container lets Docker's forwarding reach it; binding the daemon to 127.0.0.1 here makes RPC calls fail. (This Windows example maps 9232 as /udp; the guide's port list and intro say to open 9230 and 9232 as TCP.)

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Check the daemon is synced

```
curl -s http://127.0.0.1:9231/json_rpc -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"0","method":"get_info"}' | jq '.result | {height, target_height, status_line}'
```
Synced when height equals target_height (or target_height is 0). Usually 15 to 60 minutes. A fresh or far-behind node can start from the snapshot at bootstrap.xeqmlabs.com.

Sources: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide), [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)

## Create or open the operator wallet

Create: `docker exec -it sn01 /usr/local/bin/xeqm-wallet --generate-new-wallet=/data/WALLETNAME --password=MYPASSWORD --daemon-address=127.0.0.1:9231 --use-english-language-names`. It prints the 25-word recovery seed exactly once (write it down offline; anyone with it controls the wallet) and the address, which starts with XEQM.
Open: `docker exec -it sn01 /usr/local/bin/xeqm-wallet --wallet-file=/data/WALLETNAME --password=MYPASSWORD --daemon-address=127.0.0.1:9231`.
Wallet commands: `address`, `balance` (total and unlocked), `refresh`, `status`, `exit`. Received funds unlock after 10 confirmations (~10 minutes). The whole operator stake plus the fee must be unlocked before you register.

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Generate the registration command

Ask the daemon (amounts in atomic units: 1 XEQM = 1,000,000,000, so 200,000 XEQM = 200000000000000):
```
curl -s http://127.0.0.1:9231/json_rpc -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"0","method":"get_service_node_registration_cmd","params":{"operator_cut":"0","contributor_addresses":["YOUR_WALLET_ADDRESS"],"contributor_amounts":[200000000000000],"staking_requirement":200000000000000}}' \
  | jq -r '.result.registration_cmd'
```
Solo node: contributor_amounts [200000000000000]. Pool node: [100000000000000] (the operator minimum); contributors fill the rest after registration. staking_requirement is always 200000000000000, for solo and pool nodes alike. operator_cut is "0" to "10": the percent of rewards the operator takes from contributors (it only matters for pool nodes). Without jq, pipe to `grep -o '"registration_cmd":"[^"]*"' | cut -d'"' -f4`. The output is one long line starting `register_service_node`.

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Submit the registration

Open the wallet CLI (`xeqm-wallet`), paste the whole `register_service_node ...` line exactly as copied (one line, all spaces, no line breaks), type `Yes` to confirm the stake. It is included in a block within 1 to 2 minutes. A registration command expires after 14 days if not submitted: generate a new one. Keep enough unlocked XEQM for the stake plus the fee (a fraction of an XEQM).

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Check service node status and health

- Pubkey: RPC method `get_service_node_key` (`.result.service_node_pubkey`), or `get_service_node_status`.
- State: `get_service_nodes` with your pubkey shows `active`, `funded`, `payable` (all should be true) and `registration_height`.
- Watch: `decommission_count` should stay flat; `earned_downtime_blocks` (credit) should grow; `last_uptime_proof` should be recent; `pulse_votes` and `checkpoint_votes` should approach 8 voted, ~0 missed.
- Quick health: `get_info`'s status line, e.g. `Height: 1234, SN: active, proof: 2m3s`.
- Log level without restart: RPC `set_log_level` with `{"categories":"*:warn"}`.
The Explorer shows every node's status too.

Sources: [XEQM Core](https://github.com/XEQMLabs/xeqm-core), [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Update the node

Docker: `docker stop sn01`, `docker rm sn01`, `docker pull ghcr.io/xeqmlabs/xeqm-node:latest` (or pin a release tag such as `:v1.1.2`), then re-run the same `docker run` command. Registration, keys and chain data stay in the mounted `data/` folder. Binaries: stop the daemon, replace them, start it. No resync and no config change are needed. Mandatory releases must be installed before their fork height or the node forks off and gets decommissioned. Restart a node after upgrading to v1.1.1 or newer to drop the old RandomX memory.

Sources: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide), [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)

## Troubleshooting: RPC "connection closed" or "unable to connect"

The admin RPC bind does not match the port mapping: on Windows the daemon must use `--rpc-admin=0.0.0.0:9231` with the `127.0.0.1:9231:9231` mapping; on Linux with host networking use `--rpc-admin=127.0.0.1:9231`. Quick workaround: run the call inside the container, `docker exec sn01 curl -s http://127.0.0.1:9231/json_rpc -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":"0","method":"get_info"}'`. Proper fix: recreate the container with the right `--rpc-admin`.

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Troubleshooting: registration command fails

- "No operator contribution given" or "Failed to make registration command": contributor_amounts must be atomic units (1 XEQM = 1,000,000,000), no commas or decimals; the address must start with XEQM and have no spaces.
- Can't get a command: funds must be unlocked (`balance`) and the daemon fully synced.
- Registration rejected: copy the entire line (it is very long), check funds are unlocked, read `docker logs sn01`.

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Troubleshooting: node not active, not payable or decommissioned

- `funded: false`: the registration hasn't confirmed or the operator stake isn't fully committed; wait a few blocks.
- `active: true, payable: false`: normal for the first 4 blocks.
- `active: false` with `decommission_count > 0`: decommissioned for missed uptime proofs. Restart the daemon and fix networking; once proofs resume, the chain recommissions it within ~30 minutes.
- `decommission_count` rising in cycles on old versions: a bug fixed in v1.0.2; update.
- Since HF22, a node below v1.1.0 has its uptime proofs refused and gets decommissioned; before block 236,920 every node needs v1.1.1 or newer (v1.1.2 recommended).

Sources: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide), [XEQM Core](https://github.com/XEQMLabs/xeqm-core)

## Troubleshooting: last uptime proof is over 30 minutes old

The node risks decommission. Common causes: the daemon crashed or stopped (`docker ps`); port 9230 or 9232 is blocked by a firewall; `--service-node-public-ip` doesn't match the real public IP. Fix the cause, then send a fresh proof:
```
curl -s http://127.0.0.1:9231/json_rpc -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"0","method":"send_uptime_proof"}'
```

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Troubleshooting: daemon won't start or keeps crashing

Read `docker logs sn01 --tail 100`. Common causes: a port already in use (another process on 9230/9231/9232: stop it or change ports); volume permission errors on Linux (the data folder must be writable by the container); wrong image tag; Docker Desktop not running; a folder path with spaces not in quotes. "Segfault on startup" or "GLIBC_2.x not found": use the static release tarballs (v1.0.2+) or the Docker image. Still stuck: post `docker logs sn01 --tail 200` in the XEQMLabs community channels (Telegram t.me/XEQCommunity).

Sources: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide), [XEQM Core](https://github.com/XEQMLabs/xeqm-core)

## Wallet RPC and backups

Wallet RPC (`xeqm-rpc`) is only needed for the explorer's web wallet integration, scripts, or JSON-RPC registration; most operators use the interactive CLI. Linux: `docker run -dit --name wallet-rpc --network host -v "$(pwd)/wallets:/data" --entrypoint /usr/local/bin/xeqm-rpc ghcr.io/xeqmlabs/xeqm-node:latest --wallet-dir=/data --rpc-bind-port=9234 --daemon-address=127.0.0.1:9231 --disable-rpc-login --non-interactive --log-level=1`. On Windows map `-p 127.0.0.1:9234:9234` and use `--daemon-address=host.docker.internal:9231`. Keep it on 127.0.0.1, never public.
Hot backup of a running node's database: `xeqm-mdb_copy -c <data-dir>/lmdb <dest>` (ships in every package since v1.0.7; stock mdb_copy fails with MDB_VERSION_MISMATCH).

Sources: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide), [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)
