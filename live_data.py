import re
import time
import requests


class LiveData:
    def __init__(self):
        self.cache = {}
        self.cache_seconds = 30

        # Later, when Raymond gives us the official EXIOM RPC/API,
        # we will plug it in here.
        self.api_url = None

        # Temporary official fallback
        self.explorer_url = "https://explorer.xeqmlabs.com/"

        self.headers = {
            "User-Agent": "EXIOM-AI/1.0"
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


    def _clean_html(self, html):
        text = re.sub(
            r"<script.*?</script>",
            " ",
            html,
            flags=re.I | re.S
        )

        text = re.sub(
            r"<style.*?</style>",
            " ",
            text,
            flags=re.I | re.S
        )

        text = re.sub(
            r"<[^>]+>",
            " ",
            text
        )

        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    def _extract_number(self, text, patterns):
        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.I
            )

            if match:
                return match.group(1).strip()

        return None


    def _get_from_api(self):
        if not self.api_url:
            return None

        # We will implement this when XEQMLabs gives us
        # the official Mainnet RPC/API endpoint.
        return None


    def _get_from_explorer(self):
        response = requests.get(
            self.explorer_url,
            headers=self.headers,
            timeout=8
        )

        response.raise_for_status()

        text = self._clean_html(
            response.text
        )

        stats = {
            "status": "live",
            "source": "Official EXIOM Explorer",
            "source_url": self.explorer_url,

            "active_nodes": self._extract_number(
                text,
                [
                    r"Active Nodes?\s*[:\-]?\s*([\d,]+)",
                    r"Service Nodes?\s*[:\-]?\s*([\d,]+)"
                ]
            ),

            "awaiting_contribution": self._extract_number(
                text,
                [
                    r"Awaiting Contribution\s*[:\-]?\s*([\d,]+)"
                ]
            ),

            "total_supply": self._extract_number(
                text,
                [
                    r"Total Supply\s*[:\-]?\s*([\d,.]+)"
                ]
            ),

            "locked_supply": self._extract_number(
                text,
                [
                    r"Locked Supply\s*[:\-]?\s*([\d,.]+[KMB]?)",
                    r"(?:XEQM\s+)?Locked\s*[:\-]?\s*([\d,.]+[KMB]?)"
                ]
            ),

            "block_height": self._extract_number(
                text,
                [
                    r"(?:Block )?Height\s*[:\-]?\s*([\d,]+)"
                ]
            ),

            "service_node_reward": self._extract_number(
                text,
                [
                    r"(?:Service Node|Node) Reward\s*[:\-]?\s*([\d,.]+)"
                ]
            )
        }

        useful_values = [
            value
            for key, value in stats.items()
            if key not in {
                "status",
                "source",
                "source_url"
            }
            and value is not None
        ]

        if not useful_values:
            return {
                "status": "unavailable",
                "source": "Official EXIOM Explorer",
                "message": (
                    "The Explorer is reachable, but EXIOM AI "
                    "could not safely extract its live statistics."
                )
            }

        return stats


    def get_network_stats(self):
        cached = self._get_cached("network_stats")

        if cached:
            return cached

        try:
            api_data = self._get_from_api()

            if api_data:
                self._save_cache(
                    "network_stats",
                    api_data
                )

                return api_data

            explorer_data = self._get_from_explorer()

            self._save_cache(
                "network_stats",
                explorer_data
            )

            return explorer_data

        except requests.RequestException:
            return {
                "status": "unavailable",
                "message": (
                    "Live EXIOM network data is temporarily unavailable."
                )
            }


    def get_live_context(self):
        return {
            "network": self.get_network_stats()
        }
    def answer_live_question(self, fact):
        stats = self.get_network_stats()

        if stats.get("status") != "live":
            return None

        value = stats.get(fact)

        if value is None:
            return None

        templates = {
            "active_nodes": (
                f"{value} active service nodes are currently "
                f"online on the EXIOM network."
            ),

            "total_supply": (
                f"The current EXIOM total supply is "
                f"{value} XEQM."
            ),

            "block_height": (
                f"The current EXIOM block height is "
                f"{value}."
            ),

            "service_node_reward": (
                f"The current EXIOM service-node reward is "
                f"{value} XEQM per block."
            )
        }

        return templates.get(fact)

    