# WALLETS AND PUBLIC NODES

## GUI wallet: download and features

The official desktop wallet is XEQMLabs-GUI: download from github.com/XEQMLabs/XEQMLabs-GUI/releases. Latest: v2.3.3 (Oct 12, 2026), which bundles core v1.1.2. Update before block 236,920: a wallet running the bundled local node on an older version stops syncing there. Platforms: Windows x64 (.exe installer), Linux x64 (.AppImage), macOS Apple Silicon (.dmg, codesigned and notarized). Every file has a .sha256 to verify. It bundles xeqm-d, xeqm-rpc and xeqm-wallet, so no separate setup.
Features: create, restore or import wallets (25-word seed, wallet file, view-only); send and receive with QR codes; service node staking and management; network stats and explorer integration; history with proof generation and verification; address book; mainnet and testnet (switch on the wallet-select screen or in Network Settings); automatic wallet backup.

Sources: [XEQMLabs GUI Wallet](https://github.com/XEQMLabs/XEQMLabs-GUI), [XEQMLabs GUI Wallet Releases](https://github.com/XEQMLabs/XEQMLabs-GUI/releases)

## GUI wallet install and fixes

- Windows: download `XEQM-GUI-<version>-win.exe`, create a dedicated folder (e.g. C:\XEQM), run the installer from it. No other dependencies.
- Linux: install the runtime libraries once: `sudo apt-get install -y libboost-all-dev libsodium23 libfuse2t64 libzmq5 libzstd1 libhidapi-libusb0 libhidapi-hidraw0 libusb-1.0-0` (on Ubuntu 22.04 and older use `libfuse2` instead of `libfuse2t64`), then `chmod +x XEQM-GUI-<version>-linux.AppImage` and run it. A sandbox error: run it with `--no-sandbox`.
- macOS: open the .dmg and drag XEQM GUI to Applications. "App is damaged" or "unidentified developer": run `xattr -cr "/Applications/XEQM GUI.app"` once, then open it again.
v2.3.3 also fixed the file and folder pickers (broken since v2.2.0) and stopped "WRONG DATA CONVERSION" spam in wallet-rpc.log.

Sources: [XEQMLabs GUI Wallet](https://github.com/XEQMLabs/XEQMLabs-GUI), [XEQMLabs GUI Wallet Releases](https://github.com/XEQMLabs/XEQMLabs-GUI/releases)

## GUI wallet files, seed and backups

Locations, inside the app's install folder: wallet files `wallets/<network>/`; configuration `data/`; blockchain `data/lmdb/` (mainnet) or `data/testnet/lmdb/`; logs `wallets/<network>/logs/` and `data/logs/`. Back up the 25-word seed before installing, reinstalling or moving the install folder: reinstalling or installing elsewhere can overwrite wallet files, and a lost seed means unrecoverable funds. Set Network Settings > Wallet Backup Path to mirror the wallet folder, and keep your own off-machine backup of the folder or the seed. Restoring: the GUI restores from the 25-word seed or a wallet file.

Source: [XEQMLabs GUI Wallet](https://github.com/XEQMLabs/XEQMLabs-GUI)

## CLI wallet commands

The CLI wallet is `xeqm-wallet` (in the Docker image at /usr/local/bin/xeqm-wallet). Commands: `address`, `balance` (total and unlocked), `refresh` (resync), `status`, `exit` (close safely). Staking: `stake <service_node_pubkey> <amount>` or `... <percent>%`. Registering a node: paste the `register_service_node ...` command. Received funds unlock after 10 confirmations (~10 minutes). Addresses start with XEQM. The seed is 25 words.

Source: [SN Operator Guide](https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide)

## Community public nodes (cpn)

Community operators run public nodes published as `cpn-N.xeqmlabs.com` that wallets connect to. Wallets from v1.1.0 default to HTTPS endpoints, so a cpn node needs TLS on 443. Design: the cpn records are DNS-only A records (XEQMLabs keeps the IP-to-operator mapping); each node terminates its own TLS with Caddy and Let's Encrypt; the RPC is deliberately not proxied through Cloudflare. Setup: point cpn-N at your host (ask XEQMLabs), public RPC answering on 127.0.0.1:9232 (`rpc-public=127.0.0.1:9232`), ports 80 and 443 open in both OS and cloud firewalls, then `curl -fsSLO https://raw.githubusercontent.com/XEQMLabs/xeqm-community-nodes/main/setup-rpc-tls.sh`, review it, `sudo bash setup-rpc-tls.sh cpn-N.xeqmlabs.com`. If the certificate won't issue, 80/443 is almost always blocked or the A record is stale (test `curl -sI http://cpn-N.xeqmlabs.com`). Remove any `rpc-bind-ip` / `confirm-external-bind` public RPC so 443 is the only public surface.

Source: [XEQM Community Public Nodes](https://github.com/XEQMLabs/xeqm-community-nodes)

## Wallet privacy and security fixes in v1.1.0

v1.1.0 (Sep 2026) wallets no longer fetch rings from untrusted daemons (a remote daemon could otherwise learn every outgoing transaction id). `init(use_ssl=true)` connects over HTTPS, with `setDaemonSslCaFile` / `setDaemonSslAllowAnyCert` for embedded wallets. Public node operators serving wallets should put TLS in front of the RPC port.

Source: [XEQM Core Releases](https://github.com/XEQMLabs/xeqm-core/releases)
