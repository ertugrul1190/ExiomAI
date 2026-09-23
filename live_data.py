import html
import re
import threading
import time
import requests


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

        self._now = time.time

        # One fetch at a time. Requests that miss the cache
        # together wait for that fetch instead of each
        # starting their own (and the Session is only ever
        # used by one thread at a time).
        self._fetch_lock = threading.Lock()

        # Keep-alive: reuses the TCP + TLS connection between
        # fetches instead of renegotiating every 30 seconds.
        self.session = requests.Session()

        self.explorer_url = "https://explorer.xeqmlabs.com/"

        self.headers = {
            "User-Agent": "EXIOM-AI/1.0"
        }

        # These define FACTS available from the Explorer.
        # They are NOT lists of possible user questions.
        self.fact_definitions = {
            "block_height": {
                "label": "Block height",
                "meaning": "latest EXIOM blockchain block height",
                "unit": "",
                "dynamic": True,
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
                "patterns": [
                    r"Active Service Nodes\s*[:\-]?\s*([\d,]+)",
                    r"Active Nodes\s*[:\-]?\s*([\d,]+)",
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
                "patterns": [
                    r"Awaiting Contribution\s*[:\-]?\s*([\d,]+)"
                ],
            },

            "total_supply": {
                "label": "Total supply",
                "meaning": "total XEQM supply shown by the Explorer",
                "unit": "XEQM",
                "dynamic": True,
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
                "patterns": [
                    r"Locked\s*[:\-]?\s*([\d,.]+[KMB]?)\s*XEQM"
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
                "patterns": [
                    r"Min Operator Contribution\s*[:\-]?\s*"
                    r"([\d,]+)\s*XEQM",
                    r"Min Operator\s*[:\-]?\s*"
                    r"([\d,]+)\s*XEQM",
                ],
            },

            "service_node_reward": {
                "label": "Service node reward",
                "meaning": (
                    "XEQM reward paid to service nodes per block"
                ),
                "unit": "XEQM per block",
                "dynamic": False,
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
                "patterns": [
                    r"SN Rewards \(24h\)\s*[:\-]?\s*"
                    r"([\d,.]+)\s*XEQM",
                    r"Daily SN Emission\s*[:\-]?\s*"
                    r"([\d,.]+)\s*XEQM",
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
                "patterns": [
                    r"Mempool\s*[:\-]?\s*([\d,]+)\s*tx"
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


    def _detect_connection_state(self, text):
        lower_text = text.lower()

        disconnected_markers = [
            "explorer is not connected to a daemon",
            "showing placeholder data",
            "disconnected",
        ]

        for marker in disconnected_markers:
            if marker in lower_text:
                return "disconnected"

        return "connected"


    def _get_from_explorer(self):
        response = self.session.get(
            self.explorer_url,
            headers=self.headers,
            timeout=self.timeout
        )

        response.raise_for_status()

        text = self._clean_html(response.text)

        connection_state = self._detect_connection_state(text)

        facts = {}

        for fact_key, definition in self.fact_definitions.items():
            value = self._extract(
                text,
                definition["patterns"]
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
            }

        return {
            "status": "available",
            "connection_state": connection_state,
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