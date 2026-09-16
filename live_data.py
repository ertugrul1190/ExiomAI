import html
import re
import time
import requests


class LiveData:
    def __init__(self):
        self.cache = {}
        self.cache_seconds = 30

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

        if time.time() - item["time"] > self.cache_seconds:
            return None

        return item["data"]


    def _save_cache(self, key, data):
        self.cache[key] = {
            "time": time.time(),
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
        response = requests.get(
            self.explorer_url,
            headers=self.headers,
            timeout=8
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


    def get_network_stats(self):
        cached = self._get_cached("network_stats")

        if cached:
            return cached

        try:
            data = self._get_from_explorer()

            self._save_cache(
                "network_stats",
                data
            )

            return data

        except requests.RequestException:
            return {
                "status": "unavailable",
                "connection_state": "unknown",
                "source": "Official EXIOM Explorer",
                "source_url": self.explorer_url,
                "facts": {},
                "message": (
                    "EXIOM Explorer data is temporarily unavailable."
                ),
            }


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