import html
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait

import requests


logger = logging.getLogger(__name__)


# The Explorer's JSON feeds report XEQM in atomic units.
ATOMIC_PER_XEQM = 10 ** 9


# ---------------------------------------------------------
# FEED VALUE FORMATTERS
# ---------------------------------------------------------
#
# Feed values are turned into the same text the Explorer
# page shows, so an answer reads the same whichever source
# supplied it.
#
# Anything that is not the expected shape raises, and the
# fact falls through to its next source.
# ---------------------------------------------------------

def as_number(value):
    # bool is an int in Python: a field that starts sending
    # true/false must not be read as 1/0.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"not a number: {value!r}")

    return value


def format_count(value):
    return f"{int(as_number(value)):,}"


def format_xeqm(atomic):
    return f"{as_number(atomic) / ATOMIC_PER_XEQM:,.0f}"


def format_decimal(value):
    return f"{as_number(value):,.2f}".rstrip("0").rstrip(".")


def _percent(part, whole):
    return f"{as_number(part) / as_number(whole) * 100:.1f}"


def _duration(seconds):
    total = int(round(as_number(seconds)))

    # As the page writes it: "59s", "1m 00s".
    if total < 60:
        return f"{total}s"

    return f"{total // 60}m {total % 60:02d}s"


def _hashrate(hashes_per_second):
    return f"{as_number(hashes_per_second) / 1000:.2f} kH/s"


def _gigabytes(size_bytes):
    return f"~{as_number(size_bytes) / 10 ** 9:.2f}GB"


def _nodes_by_country(feeds):
    counts = {}
    spellings = {}

    # The map lists nodes per region, so a country can appear
    # several times, and not always under the same name
    # ("Turkey" and "Türkiye" are both TR). Regions are
    # grouped by country code and shown under the spelling
    # that carries the most nodes.
    for place in feeds["node_map"]["data"]["nodes"]:
        name = place["country"]
        count = int(as_number(place["count"]))
        code = place.get("country_code") or name

        counts[code] = counts.get(code, 0) + count

        names = spellings.setdefault(code, {})
        names[name] = names.get(name, 0) + count

    if not counts:
        raise ValueError("node map is empty")

    ranked = sorted(
        (
            (
                min(names, key=lambda n: (-names[n], n)),
                counts[code],
            )
            for code, names in spellings.items()
        ),
        key=lambda item: (-item[1], item[0])
    )

    # One country per line, so a direct answer can show it
    # as a list.
    return "\n".join(
        f"{country}: {count:,}" for country, count in ranked
    )


class LiveData:
    def __init__(self):
        self.cache = {}
        self.cache_seconds = 30

        # A failed fetch is remembered briefly so a down
        # Explorer costs one timeout, not one per question.
        # Kept short so recovery is noticed quickly.
        self.failure_cache_seconds = 10

        # Shortly before a good reading expires, one request
        # starts a background fetch and every caller keeps the
        # still-valid reading. Under steady traffic nobody
        # waits for the Explorer, and nothing older than
        # cache_seconds is ever served.
        self.refresh_ahead_seconds = 10

        # When a refresh-ahead fails, the next one waits as
        # long as a failure is remembered, so a down Explorer
        # is not retried on every request.
        self._early_refresh_failed_at = None

        # (connect, read). The fetch sits on the request path
        # of every question, so it must fail fast.
        self.timeout = (3.05, 6)

        # A reading's requests run in parallel. Once this much
        # time has gone, the reading is built from what has
        # arrived.
        self.fetch_budget_seconds = 8

        self._now = time.time

        # One reading at a time. Requests that miss the cache
        # together wait for that reading instead of each
        # starting their own.
        self._fetch_lock = threading.Lock()

        # Every request gets its own Session: a reading's
        # sources are fetched in parallel, background pages
        # alongside them, and a Session is not shared between
        # threads.
        self.session_factory = requests.Session

        self.explorer_url = "https://explorer.xeqmlabs.com/"

        self.headers = {
            "User-Agent": "EXIOM-AI/1.0"
        }

        # The JSON feeds the Explorer's own dashboard reads.
        # They are undocumented and may change without
        # notice, so every fact that the page also shows keeps
        # a page pattern as its fallback.
        self.feeds = {
            "live_slow": "api/live_slow",
            "networkinfo": "api/networkinfo",
            "node_map": "api/node_map",
        }

        # Server-rendered pages, read with page patterns.
        #
        # The quorum and node-list pages are large (up to
        # 0.5 MB) and change slowly. They are fetched in the
        # background, never on a question's request path, and
        # a copy is used for max_age seconds; renewal starts
        # halfway through. A copy is dropped when a fetch
        # fails, never reused. Their facts are missing only
        # until the first copy arrives.
        self.pages = {
            "dashboard": {"path": ""},
            "txpool": {"path": "txpool"},
            "service_nodes": {
                "path": "service_nodes",
                "background": True,
                "max_age": 120,
            },
            "quorums": {
                "path": "quorums",
                "background": True,
                "max_age": 120,
            },
        }

        # name -> (fetched_at, raw html), background pages only
        self._page_copies = {}
        self._pages_failed = set()
        self._pages_refreshing = {}
        self._page_lock = threading.Lock()

        # What each source delivered on the last reading, so
        # a source breaking or recovering is logged once, not
        # every refresh.
        self._source_health = {}

        # These define FACTS available from the Explorer.
        # They are NOT lists of possible user questions.
        #
        # Each fact is read from its "api" extractors first,
        # in order, then from its page "patterns". A fact
        # falls back on its own: one renamed feed field moves
        # only that fact to the page.
        #
        # Patterns are read from the dashboard unless "page"
        # names another entry of self.pages. Facts without
        # "patterns" are not server-rendered on any page, so
        # they have no fallback.
        self.fact_definitions = {
            "block_height": {
                "label": "Block height",
                "meaning": "latest EXIOM blockchain block height",
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(f["live_slow"]["height"]),
                    lambda f: format_count(
                        f["networkinfo"]["data"]["height"]
                    ),
                ],
                "patterns": [
                    r"Block Height\s*[:\-]?\s*([\d,]+)"
                ],
            },

            "active_nodes": {
                "label": "Active service nodes",
                "meaning": (
                    "number of active EXIOM service nodes "
                    "currently shown by the Explorer"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(f["live_slow"]["active_sns"]),
                ],
                "patterns": [
                    r"Active Service Nodes\s*[:\-]?\s*([\d,]+)",
                    r"Active Nodes\s*[:\-]?\s*([\d,]+)",
                ],
            },

            "inactive_nodes": {
                "label": "Inactive service nodes",
                "meaning": (
                    "number of registered EXIOM service nodes "
                    "that are currently decommissioned or "
                    "otherwise not active"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(
                        f["live_slow"]["inactive_sns"]
                    ),
                ],
            },

            "registered_nodes": {
                "label": "Registered service nodes",
                "meaning": (
                    "total number of registered EXIOM service "
                    "nodes, active and inactive together"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(f["live_slow"]["total_sns"]),
                ],
            },

            "awaiting_contribution": {
                "label": "Nodes awaiting contribution",
                "meaning": (
                    "number of EXIOM service nodes currently "
                    "waiting for staking contributions"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(f["live_slow"]["awaiting_sns"]),
                ],
                "patterns": [
                    r"Awaiting Contribution\s*[:\-]?\s*([\d,]+)"
                ],
            },

            "open_pool_nodes": {
                "label": "Open pool nodes",
                "meaning": (
                    "number of EXIOM service nodes open for "
                    "other people to contribute stake to"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(
                        f["live_slow"]["open_pool_sns"]
                    ),
                ],
                "patterns": [
                    r"([\d,]+)\s*pool nodes available",
                    r"Open Nodes\s*([\d,]+)\s*nodes",
                ],
            },

            "active_swarms": {
                "label": "Active swarms",
                "meaning": (
                    "number of active service node swarms "
                    "on the EXIOM network"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(
                        f["live_slow"]["active_swarms"]
                    ),
                ],
                "page": "service_nodes",
                "patterns": [
                    r"Swarms:\s*([\d,]+)"
                ],
            },

            "nodes_on_current_release": {
                "label": "Service nodes on the current release",
                "meaning": (
                    "how many active EXIOM service nodes run the "
                    "current software release, out of all active "
                    "nodes"
                ),
                "unit": "",
                "dynamic": True,
                "page": "service_nodes",
                "patterns": [
                    r"v[\d.]+ Nodes:\s*([\d,]+/[\d,]+)"
                ],
            },

            "testing_quorums": {
                "label": "Testing quorums",
                "meaning": (
                    "number of quorums currently testing that "
                    "EXIOM service nodes meet their obligations"
                ),
                "unit": "",
                "dynamic": True,
                "page": "quorums",
                "patterns": [
                    r"Testing Quorums\s*([\d,]+)"
                ],
            },

            "pulse_quorums": {
                "label": "Pulse quorums",
                "meaning": (
                    "number of Pulse quorums, which produce "
                    "EXIOM blocks"
                ),
                "unit": "",
                "dynamic": True,
                "page": "quorums",
                "patterns": [
                    r"Pulse Quorums\s*([\d,]+)"
                ],
            },

            "checkpoint_quorums": {
                "label": "Checkpoint quorums",
                "meaning": (
                    "number of checkpoint quorums, which "
                    "validate and checkpoint the EXIOM chain"
                ),
                "unit": "",
                "dynamic": True,
                "page": "quorums",
                "patterns": [
                    r"Checkpoint Quorums\s*([\d,]+)"
                ],
            },

            "blink_quorums": {
                "label": "Blink quorums",
                "meaning": (
                    "number of Blink quorums, which approve "
                    "instant EXIOM transactions"
                ),
                "unit": "",
                "dynamic": True,
                "page": "quorums",
                "patterns": [
                    r"Blink Quorums\s*([\d,]+)"
                ],
            },

            "node_countries": {
                "label": "Countries with service nodes",
                "meaning": (
                    "number of countries EXIOM service nodes "
                    "are located in"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(
                        f["node_map"]["data"]["summary"]["countries"]
                    ),
                ],
            },

            "nodes_by_country": {
                "label": "Service nodes by country",
                "meaning": (
                    "how many EXIOM service nodes are in each "
                    "country, largest first"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    _nodes_by_country,
                ],
            },

            # The Explorer reports one supply figure: its
            # /api/emission gives circulating supply equal to
            # total emission (no burns, per its tokenomics
            # note). The page shows it as both "Total Supply"
            # and "Circulating Supply".
            "total_supply": {
                "label": "Total supply",
                "meaning": "total XEQM supply shown by the Explorer",
                "unit": "XEQM",
                "dynamic": True,
                "api": [
                    lambda f: format_xeqm(
                        f["live_slow"]["circulating_supply_atomic"]
                    ),
                ],
                "patterns": [
                    r"Total Supply\s*[:\-]?\s*([\d,.]+[KMB]?)\s*XEQM"
                ],
            },

            "circulating_supply": {
                "label": "Circulating supply",
                "meaning": (
                    "amount of XEQM shown as circulating "
                    "by the Explorer"
                ),
                "unit": "XEQM",
                "dynamic": True,
                "api": [
                    lambda f: format_xeqm(
                        f["live_slow"]["circulating_supply_atomic"]
                    ),
                ],
                "patterns": [
                    r"Circulating Supply\s*[:\-]?\s*"
                    r"([\d,.]+[KMB]?)\s*XEQM"
                ],
            },

            "locked_supply": {
                "label": "Locked supply",
                "meaning": "amount of XEQM shown as locked in staking",
                "unit": "XEQM",
                "dynamic": True,
                "api": [
                    lambda f: format_xeqm(
                        f["live_slow"]["total_locked_atomic"]
                    ),
                ],
                "patterns": [
                    r"Locked\s*[:\-]?\s*([\d,.]+[KMB]?)\s*XEQM"
                ],
            },

            "locked_supply_percent": {
                "label": "Share of supply locked",
                "meaning": (
                    "percentage of the XEQM supply locked in "
                    "service node staking"
                ),
                "unit": "%",
                "dynamic": True,
                "api": [
                    lambda f: _percent(
                        f["live_slow"]["total_locked_atomic"],
                        f["live_slow"]["circulating_supply_atomic"],
                    ),
                ],
                "patterns": [
                    r"([\d.]+)%\s*Locked"
                ],
            },

            "unlocked_supply": {
                "label": "Unlocked supply",
                "meaning": (
                    "amount of XEQM not locked in staking, "
                    "free to move"
                ),
                "unit": "XEQM",
                "dynamic": True,
                "api": [
                    lambda f: format_xeqm(
                        as_number(
                            f["live_slow"]["circulating_supply_atomic"]
                        )
                        - as_number(
                            f["live_slow"]["total_locked_atomic"]
                        )
                    ),
                ],
                "patterns": [
                    r"Circulating\s+([\d,]+)\s*XEQM\s*[\d.]+%"
                ],
            },

            "staking_requirement": {
                "label": "Staking requirement",
                "meaning": (
                    "XEQM required to fully fund one EXIOM "
                    "service node"
                ),
                "unit": "XEQM",
                "dynamic": False,
                "api": [
                    lambda f: format_xeqm(
                        f["live_slow"]["staking_requirement_atomic"]
                    ),
                    lambda f: format_xeqm(
                        f["networkinfo"]["data"]["staking_requirement"]
                    ),
                ],
                "patterns": [
                    r"Staking Requirement\s*[:\-]?\s*"
                    r"([\d,]+)\s*XEQM",
                    r"Staking Req\s*[:\-]?\s*"
                    r"([\d,]+)\s*XEQM",
                ],
            },

            "minimum_operator_contribution": {
                "label": "Minimum operator contribution",
                "meaning": (
                    "minimum XEQM amount the operator must "
                    "contribute to a service node"
                ),
                "unit": "XEQM",
                "dynamic": False,
                "api": [
                    lambda f: format_xeqm(
                        f["networkinfo"]["data"][
                            "min_operator_contribution"
                        ]
                    ),
                ],
                "patterns": [
                    r"Min Operator Contribution\s*[:\-]?\s*"
                    r"([\d,]+)\s*XEQM",
                    r"Min Operator\s*[:\-]?\s*"
                    r"([\d,]+)\s*XEQM",
                ],
            },

            "max_contributors": {
                "label": "Maximum contributors per node",
                "meaning": (
                    "most wallets, operator included, that can "
                    "stake into one EXIOM service node"
                ),
                "unit": "",
                "dynamic": False,
                "api": [
                    lambda f: format_count(
                        f["networkinfo"]["data"]["max_contributors"]
                    ),
                ],
                "patterns": [
                    r"Max Contributors\s*[:\-]?\s*(\d+)"
                ],
            },

            "service_node_reward": {
                "label": "Service node reward",
                "meaning": (
                    "XEQM reward paid to service nodes per block"
                ),
                "unit": "XEQM per block",
                "dynamic": False,
                "api": [
                    lambda f: format_decimal(
                        f["live_slow"]["sn_reward_per_block"]
                    ),
                ],
                "patterns": [
                    r"SN Reward\s*[:\-]?\s*"
                    r"([\d,.]+)\s*XEQM",
                    r"SN Reward / Block\s*[:\-]?\s*"
                    r"([\d,.]+)\s*XEQM",
                ],
            },

            "daily_service_node_emission": {
                "label": "Daily service node emission",
                "meaning": (
                    "XEQM distributed to service nodes "
                    "during a 24 hour period"
                ),
                "unit": "XEQM",
                "dynamic": False,
                "api": [
                    lambda f: format_decimal(
                        f["live_slow"]["sn_rewards_24h"]
                    ),
                ],
                "patterns": [
                    r"SN Rewards \(24h\)\s*[:\-]?\s*"
                    r"([\d,.]+)\s*XEQM",
                    r"Daily SN Emission\s*[:\-]?\s*"
                    r"([\d,.]+)\s*XEQM",
                ],
            },

            "average_block_time_1h": {
                "label": "Average block time (last hour)",
                "meaning": (
                    "average time between EXIOM blocks over "
                    "the last hour"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: _duration(f["live_slow"]["avg_1h"]),
                ],
                "patterns": [
                    r"Avg Block \(1h\)\s*((?:\d+m )?\d+s)"
                ],
            },

            "average_block_time_24h": {
                "label": "Average block time (last 24 hours)",
                "meaning": (
                    "average time between EXIOM blocks over "
                    "the last 24 hours"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: _duration(f["live_slow"]["avg_24h"]),
                ],
                "patterns": [
                    r"Avg Block \(24h\)\s*((?:\d+m )?\d+s)"
                ],
            },

            "average_block_time_7d": {
                "label": "Average block time (last 7 days)",
                "meaning": (
                    "average time between EXIOM blocks over "
                    "the last 7 days"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: _duration(f["live_slow"]["avg_7d"]),
                ],
                "patterns": [
                    r"\b7d\s+((?:\d+m )?\d+s)\s+[\d,]+\s"
                ],
            },

            "target_block_time": {
                "label": "Target block time",
                "meaning": (
                    "block time the EXIOM protocol aims for"
                ),
                "unit": "seconds",
                "dynamic": False,
                "api": [
                    lambda f: format_count(
                        f["networkinfo"]["data"]["target"]
                    ),
                ],
                "patterns": [
                    r"Block Time\s*(\d+)\s*seconds"
                ],
            },

            "blocks_24h": {
                "label": "Blocks in the last 24 hours",
                "meaning": (
                    "number of EXIOM blocks produced in the "
                    "last 24 hours"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(f["live_slow"]["blocks_24h"]),
                ],
                "patterns": [
                    r"\b24h\s+(?:\d+m )?\d+s\s+([\d,]+)\s"
                ],
            },

            "hashrate_24h": {
                "label": "Average hashrate (last 24 hours)",
                "meaning": (
                    "average network hashrate the Explorer "
                    "reports for the last 24 hours"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: _hashrate(
                        f["live_slow"]["hashrate_24h"]
                    ),
                ],
                "patterns": [
                    r"\b24h\s+(?:\d+m )?\d+s\s+[\d,]+\s+"
                    r"([\d.]+ [kMG]?H/s)"
                ],
            },

            "total_transactions": {
                "label": "Total transactions",
                "meaning": (
                    "number of transactions recorded on the "
                    "EXIOM blockchain since genesis"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(
                        f["networkinfo"]["data"]["tx_count"]
                    ),
                ],
            },

            "mempool_transactions": {
                "label": "Mempool transactions",
                "meaning": (
                    "number of transactions currently waiting "
                    "in the EXIOM mempool"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: format_count(
                        f["networkinfo"]["data"]["tx_pool_size"]
                    ),
                ],
                "patterns": [
                    r"Mempool\s*[:\-]?\s*([\d,]+)\s*tx"
                ],
            },

            "mempool_size": {
                "label": "Mempool size",
                "meaning": (
                    "combined size of the transactions waiting "
                    "in the EXIOM mempool"
                ),
                "unit": "",
                "dynamic": True,
                "page": "txpool",
                "patterns": [
                    r"Total Size\s*([\d.,]+\s*[kKMG]?B)\b"
                ],
            },

            "database_size": {
                "label": "Blockchain database size",
                "meaning": (
                    "size of the EXIOM blockchain database "
                    "reported by the daemon"
                ),
                "unit": "",
                "dynamic": True,
                "api": [
                    lambda f: _gigabytes(
                        f["live_slow"]["database_size"]
                    ),
                ],
                "patterns": [
                    r"Database Size\s*(~?[\d.]+\s*[KMGT]?B)"
                ],
            },

            "network_version": {
                "label": "Mainnet version",
                "meaning": (
                    "EXIOM mainnet version shown by the Explorer"
                ),
                "unit": "",
                "dynamic": False,
                "patterns": [
                    r"Mainnet\s*-\s*v([\d.]+)"
                ],
            },

            "hard_fork": {
                "label": "Active hard fork",
                "meaning": (
                    "currently active EXIOM hard fork shown "
                    "by the Explorer"
                ),
                "unit": "",
                "dynamic": False,
                "api": [
                    lambda f: format_count(
                        f["networkinfo"]["data"]["hard_fork"]
                    ),
                ],
                "patterns": [
                    r"Currently\s*:\s*HF\s*v?([\d.]+)",
                    r"HF\s*v([\d.]+)"
                ],
            },

            "current_apy": {
                "label": "Current service node APY",
                "meaning": (
                    "estimated current annual percentage yield "
                    "for an EXIOM service node"
                ),
                "unit": "%",
                "dynamic": True,
                "patterns": [
                    r"APY \(current\)\s*[:\-]?\s*([\d.]+)%"
                ],
            },

            "daily_reward_per_node": {
                "label": "Daily reward per node",
                "meaning": (
                    "estimated XEQM earned by one service node "
                    "per day"
                ),
                "unit": "XEQM",
                "dynamic": True,
                "patterns": [
                    r"Daily Reward / Node\s*[:\-]?\s*"
                    r"([\d,.]+)\s*XEQM"
                ],
            },

            "annual_reward_per_node": {
                "label": "Annual reward per node",
                "meaning": (
                    "estimated XEQM earned by one service node "
                    "per year"
                ),
                "unit": "XEQM",
                "dynamic": True,
                "patterns": [
                    r"Annual Reward / Node\s*[:\-]?\s*"
                    r"([\d,.]+)\s*XEQM"
                ],
            },
        }


    def _get_cached(self, key):
        item = self.cache.get(key)

        if not item:
            return None

        if self._now() - item["time"] > item["ttl"]:
            return None

        return item["data"]


    def _save_cache(self, key, data, ttl=None):
        self.cache[key] = {
            "time": self._now(),
            "ttl": self.cache_seconds if ttl is None else ttl,
            "data": data
        }


    def _clean_html(self, raw_html):
        text = re.sub(
            r"<script.*?</script>",
            " ",
            raw_html,
            flags=re.I | re.S
        )

        text = re.sub(
            r"<style.*?</style>",
            " ",
            text,
            flags=re.I | re.S
        )

        text = re.sub(r"<[^>]+>", " ", text)

        text = html.unescape(text)

        text = re.sub(r"\s+", " ", text)

        return text.strip()


    def _extract(self, text, patterns):
        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.I
            )

            if match:
                return match.group(1).strip()

        return None


    def _read_fact(self, definition, feeds, page_texts):
        """
        Return (value, source) from the first source that
        has the fact, or (None, None).
        """

        for extractor in definition.get("api", []):
            try:
                return extractor(feeds), "api"

            # A missing feed, a renamed field or a value of
            # the wrong type: try the next source.
            except (
                KeyError,
                IndexError,
                TypeError,
                ValueError,
                ZeroDivisionError,
            ):
                continue

        page_text = page_texts.get(
            definition.get("page", "dashboard")
        )

        if page_text:
            value = self._extract(
                page_text,
                definition.get("patterns", [])
            )

            if value is not None:
                return value, "page"

        return None, None


    def _detect_connection_state(self, feeds, raw_page):
        # The page carries its "Disconnected" banner at all
        # times and hides it while the daemon is connected, so
        # the banner's text alone says nothing.
        if raw_page is not None:
            banner = re.search(
                r"<[^>]*\bid=[\"']offline-banner[\"'][^>]*>",
                raw_page,
                flags=re.I
            )

            if banner:
                hidden = re.search(
                    r"(?<![\w-])hidden(?![\w-]|\s*=\s*[\"']?false)"
                    r"|\bis-hidden\b|display\s*:\s*none",
                    banner.group(0),
                    flags=re.I
                )

                return "connected" if hidden else "disconnected"

        # A feed is only kept when it reports status OK.
        if feeds:
            return "connected"

        if raw_page is None:
            return "unknown"

        lower_text = self._clean_html(raw_page).lower()

        disconnected_markers = [
            "explorer is not connected to a daemon",
            "showing placeholder data",
        ]

        for marker in disconnected_markers:
            if marker in lower_text:
                return "disconnected"

        return "connected"


    def _fetch(self, path):
        session = self.session_factory()

        try:
            response = session.get(
                self.explorer_url + path,
                headers=self.headers,
                timeout=self.timeout
            )

            response.raise_for_status()

            return response

        finally:
            session.close()


    def _fetch_sources(self):
        """
        Fetch every feed and every foreground page at once;
        read background pages from their copies.

        A source that errors or answers in an unexpected
        shape is skipped. Whatever has not answered within
        fetch_budget_seconds is left behind.

        Returns (feeds, pages): the usable feed payloads and
        page HTML, by name.
        """

        jobs = {("feed", name): path for name, path in self.feeds.items()}

        for name, page in self.pages.items():
            if not page.get("background"):
                jobs[("page", name)] = page["path"]

        executor = ThreadPoolExecutor(max_workers=len(jobs))

        try:
            futures = {
                executor.submit(self._fetch, path): job
                for job, path in jobs.items()
            }

            done, _ = wait(
                futures,
                timeout=self.fetch_budget_seconds
            )

        finally:
            # Stragglers finish on their own, bounded by
            # self.timeout; nobody waits for them.
            executor.shutdown(wait=False, cancel_futures=True)

        feeds = {}
        pages = {}
        unreachable = None

        for future in done:
            kind, name = futures[future]

            try:
                response = future.result()

                if kind == "page":
                    pages[name] = response.text
                    continue

                payload = response.json()

            except requests.ConnectionError as error:
                unreachable = error
                continue

            except (requests.RequestException, ValueError):
                continue

            if (
                isinstance(payload, dict)
                and payload.get("status") == "OK"
            ):
                feeds[name] = payload

        for name, page in self.pages.items():
            if page.get("background"):
                copy = self._fresh_page_copy(
                    name,
                    page,
                    may_fetch=unreachable is None
                )

                if copy is not None:
                    pages[name] = copy

        if not feeds and not pages:
            raise unreachable or requests.RequestException(
                "No Explorer source answered."
            )

        return feeds, pages


    def _fresh_page_copy(self, name, page, may_fetch):
        """
        The current copy of a background page, or None;
        starts a background fetch when one is due and the
        Explorer was reachable.
        """

        with self._page_lock:
            copy = self._page_copies.get(name)

        age = None if copy is None else self._now() - copy[0]

        if may_fetch and (age is None or age >= page["max_age"] / 2):
            self._refresh_page_in_background(name, page["path"])

        if age is not None and age < page["max_age"]:
            return copy[1]

        return None


    def _refresh_page_in_background(self, name, path):

        def run():
            try:
                response = self._fetch(path)

                with self._page_lock:
                    self._page_copies[name] = (
                        self._now(),
                        response.text
                    )
                    self._pages_failed.discard(name)

            except requests.RequestException:
                with self._page_lock:
                    self._page_copies.pop(name, None)
                    self._pages_failed.add(name)

            finally:
                with self._page_lock:
                    self._pages_refreshing.pop(name, None)

        thread = threading.Thread(target=run, daemon=True)

        with self._page_lock:
            if name in self._pages_refreshing:
                return

            self._pages_refreshing[name] = thread

        try:
            thread.start()

        except RuntimeError:
            # No new threads (interpreter shutting down).
            with self._page_lock:
                self._pages_refreshing.pop(name, None)


    def wait_for_page_refreshes(self):
        """
        Block until background page fetches finish. For
        tests and shutdown; requests never call this.
        """

        with self._page_lock:
            threads = list(self._pages_refreshing.values())

        for thread in threads:
            thread.join()


    def _log_source_changes(self, health):
        for source, state in health.items():

            previous = self._source_health.get(source)

            if state == previous:
                continue

            if state != "ok":
                logger.warning(
                    "Explorer source %s is %s; its facts fall "
                    "back to the next source.",
                    source,
                    state
                )

            elif previous is not None:
                logger.info(
                    "Explorer source %s has recovered.",
                    source
                )

        self._source_health = health


    def _get_from_explorer(self):
        feeds, pages = self._fetch_sources()

        page_texts = {
            name: self._clean_html(raw)
            for name, raw in pages.items()
        }

        facts = {}

        health = {
            f"feed {name}": "ok" if name in feeds else "unusable"
            for name in self.feeds
        }

        with self._page_lock:
            failed = set(self._pages_failed)

        for name, page in self.pages.items():

            # A background page not fetched yet is not broken.
            if (
                page.get("background")
                and name not in pages
                and name not in failed
            ):
                continue

            health[f"page {name}"] = (
                "ok" if name in pages else "unusable"
            )

        for fact_key, definition in self.fact_definitions.items():
            value, via = self._read_fact(
                definition,
                feeds,
                page_texts
            )

            # With every feed answering, a fact that still did
            # not come from one had its field renamed or moved.
            if definition.get("api") and len(feeds) == len(self.feeds):
                health[f"fact {fact_key}"] = (
                    "ok" if via == "api"
                    else "on the page fallback" if via
                    else "missing"
                )

            if value is None:
                continue

            facts[fact_key] = {
                "key": fact_key,
                "value": value,
                "label": definition["label"],
                "meaning": definition["meaning"],
                "unit": definition["unit"],
                "dynamic": definition["dynamic"],
                "source": "Official EXIOM Explorer",
                "via": via,
            }

        self._log_source_changes(health)

        # Sources answered but none held a recognisable fact:
        # the Explorer changed shape, and nothing can be
        # presented as current.
        if not facts:
            raise requests.RequestException(
                "No Explorer facts could be read."
            )

        return {
            "status": "available",
            "connection_state": self._detect_connection_state(
                feeds,
                pages.get("dashboard")
            ),
            "source": "Official EXIOM Explorer",
            "source_url": self.explorer_url,
            "facts": facts,
        }


    def _refresh_locked(self):
        """
        Fetch and cache a reading. The caller holds
        _fetch_lock.
        """

        try:
            data = self._get_from_explorer()

            self._save_cache(
                "network_stats",
                data
            )

        except requests.RequestException:

            # A refresh-ahead that failed leaves the current
            # reading in place: it is still inside its window.
            still_valid = self._get_cached("network_stats")

            if still_valid:
                self._early_refresh_failed_at = self._now()
                return still_valid

            # Never an expired reading: Explorer values are
            # presented as current, so an old one must not be
            # served as if it still were.
            data = {
                "status": "unavailable",
                "connection_state": "unknown",
                "source": "Official EXIOM Explorer",
                "source_url": self.explorer_url,
                "facts": {},
                "message": (
                    "EXIOM Explorer data is temporarily "
                    "unavailable."
                ),
            }

            self._save_cache(
                "network_stats",
                data,
                ttl=self.failure_cache_seconds
            )

        return data


    def _refresh_in_background(self):

        # Someone is already fetching; nothing to add.
        if not self._fetch_lock.acquire(blocking=False):
            return

        def run():
            try:
                self._refresh_locked()
            finally:
                self._fetch_lock.release()

        try:
            threading.Thread(target=run, daemon=True).start()

        except RuntimeError:
            # No new threads (interpreter shutting down). The
            # next request after expiry fetches normally.
            self._fetch_lock.release()


    def _needs_refresh_ahead(self):
        item = self.cache.get("network_stats")

        failed_at = self._early_refresh_failed_at

        if (
            failed_at is not None
            and self._now() - failed_at < self.failure_cache_seconds
        ):
            return False

        return (
            item is not None
            and item["data"].get("status") == "available"
            and (
                self._now() - item["time"]
                > self.cache_seconds - self.refresh_ahead_seconds
            )
        )


    def get_network_stats(self):
        cached = self._get_cached("network_stats")

        if cached:

            if self._needs_refresh_ahead():
                self._refresh_in_background()

            return cached

        with self._fetch_lock:

            # Another request may have refreshed the cache
            # while this one waited for the lock.
            cached = self._get_cached("network_stats")

            if cached:
                return cached

            return self._refresh_locked()


    def get_fact_registry(self):
        data = self.get_network_stats()

        return data.get("facts", {})


    def get_live_context(self):
        data = self.get_network_stats()

        return {
            "status": data.get("status"),
            "connection_state": data.get(
                "connection_state",
                "unknown"
            ),
            "source": data.get(
                "source",
                "Official EXIOM Explorer"
            ),
            "facts": data.get("facts", {}),
        }


    def _format_fact_answer(self, fact):
        label = fact["label"]
        value = fact["value"]
        unit = fact.get("unit", "")

        if unit:
            value_text = f"{value} {unit}"
        else:
            value_text = value

        return (
            f"{label}: {value_text}.\n\n"
            f"Source: Official EXIOM Explorer"
        )


    def answer_live_question(self, fact_key):
        """
        Compatibility method for the current app.py.

        Later, the new semantic fact matcher will call the
        registry directly instead of depending on old
        hard-coded question matching.
        """

        registry = self.get_fact_registry()

        fact = registry.get(fact_key)

        if not fact:
            return None

        return self._format_fact_answer(fact)