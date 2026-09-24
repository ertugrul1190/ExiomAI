# ---------------------------------------------------------
# EXPLORER LOOKUPS
# ---------------------------------------------------------
#
# Reads one service node, block or transaction that a
# question names by ID.
#
# The Explorer has no JSON feed for these. Its node and
# block pages embed the daemon's raw JSON (the "raw details"
# view, /<page>/1), which is read first; the page's own
# labels are the fallback. The transaction page embeds no
# JSON, so transactions are read from their labels only.
#
# Only an explicit allowlist of fields ever leaves this file.
# The raw node payload carries the node's IP address and
# ports, which the Explorer's own UI promises not to expose.
#
# IDs are parsed, never interpreted: which facts a question
# needs is still the semantic router's job.
# ---------------------------------------------------------

import html
import json
import re
import threading
import time
from datetime import datetime, timezone

import requests

from live_data import (
    ATOMIC_PER_XEQM,
    as_number,
    format_count,
    format_decimal,
    format_xeqm,
)


EXPLORER_URL = "https://explorer.xeqmlabs.com/"

SOURCE = "Official EXIOM Explorer"

MAX_IDS_PER_QUESTION = 3

# Target block time: 1,440 blocks a day.
BLOCKS_PER_DAY = 1440


# ---------------------------------------------------------
# FINDING IDS
# ---------------------------------------------------------

_HEX_ID = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")

# A number right after "block" is a height unless a unit
# follows it: "block height 2 days ago" is not block 2.
_NOT_A_HEIGHT = (
    r"(?!\s*(?:s|secs?|seconds?|mins?|minutes?|h|hrs?|hours?|"
    r"days?|weeks?|months?|years?|blocks?|%|x)\b)"
)

_BLOCK_HEIGHT = re.compile(
    r"\bblocks?\s*(?:height|number|no\.?|num)?\s*[#:]?\s*"
    r"(\d{1,9})(?![\d,.]*\d)" + _NOT_A_HEIGHT,
    re.I
)

# "#203140", as the Explorer writes heights. Three digits at
# least, so "#1 coin" is not block 1.
_HASH_HEIGHT = re.compile(r"(?<![\w&])#(\d{3,9})\b" + _NOT_A_HEIGHT)


def find_ids(question):
    """
    Return up to MAX_IDS_PER_QUESTION (kind, id) pairs, in
    the order they appear: ("hex", 64 lowercase hex) or
    ("height", digits).
    """

    text = str(question or "")

    found = []

    for match in _HEX_ID.finditer(text):
        found.append((match.start(), "hex", match.group(0).lower()))

    for pattern in (_BLOCK_HEIGHT, _HASH_HEIGHT):
        for match in pattern.finditer(text):
            found.append((match.start(), "height", match.group(1)))

    ids = []

    for _, kind, value in sorted(found):

        if (kind, value) not in ids:
            ids.append((kind, value))

    return ids[:MAX_IDS_PER_QUESTION]


def _valid(kind, value):
    if kind == "hex":
        return re.fullmatch(r"[0-9a-f]{64}", value) is not None

    if kind == "height":
        return re.fullmatch(r"\d{1,9}", value) is not None

    return False


# ---------------------------------------------------------
# PAGE HELPERS
# ---------------------------------------------------------

def _page_text(raw_html):
    text = re.sub(
        r"<(script|style)\b.*?</\1>",
        " ",
        raw_html,
        flags=re.I | re.S
    )

    text = re.sub(r"<[^>]+>", " ", text)

    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _raw_json(raw_html):
    """
    The daemon payload embedded in a "raw details" view, or
    None.
    """

    match = re.search(
        r"id=[\"']more_details[\"'].*?<pre[^>]*>(.*?)</pre>",
        raw_html,
        flags=re.S | re.I
    )

    if not match:
        return None

    body = html.unescape(re.sub(r"<[^>]+>", "", match.group(1)))

    try:
        payload = json.loads(body)

    except ValueError:
        return None

    return payload if isinstance(payload, dict) else None


def _find(pattern, text):
    match = re.search(pattern, text, flags=re.I)

    return match.group(1).strip() if match else None


def _grouped(digits):
    return f"{int(digits.replace(',', '')):,}"


def _hex(value, length=64):
    if not isinstance(value, str) or not re.fullmatch(
        rf"[0-9a-f]{{{length}}}", value
    ):
        raise ValueError(f"not a hash: {value!r}")

    return value


def _flag(value):
    if not isinstance(value, bool):
        raise ValueError(f"not a flag: {value!r}")

    return value


def _age(seconds):
    seconds = max(0, int(seconds))

    if seconds < 90:
        return f"{seconds} s ago"

    if seconds < 90 * 60:
        return f"{round(seconds / 60)} min ago"

    if seconds < 36 * 3600:
        return f"{round(seconds / 3600)} h ago"

    return f"{round(seconds / 86400)} days ago"


def _utc(timestamp, now):
    try:
        moment = datetime.fromtimestamp(
            int(as_number(timestamp)),
            tz=timezone.utc
        )

    # An absurd timestamp: not the shape this file expects.
    except (OverflowError, OSError) as error:
        raise ValueError(f"bad timestamp: {timestamp!r}") from error

    return (
        f"{moment:%Y-%m-%d %H:%M} UTC "
        f"({_age(now - moment.timestamp())})"
    )


# ---------------------------------------------------------
# SERVICE NODES
# ---------------------------------------------------------

def _node_from_json(raw, pubkey, now):
    if raw.get("service_node_pubkey") != pubkey:
        raise ValueError("payload is for another node")

    active = _flag(raw["active"])
    funded = _flag(raw["funded"])

    status = (
        "active" if active
        else "decommissioned" if funded
        else "awaiting contributions"
    )

    contributors = raw["contributors"]

    if not isinstance(contributors, list):
        raise ValueError("contributors is not a list")

    version = raw["service_node_version"]

    if not isinstance(version, list) or not version:
        raise ValueError("version is not a list")

    downtime = int(as_number(raw["earned_downtime_blocks"]))

    operator = raw["operator_address"]

    if not isinstance(operator, str) or not re.fullmatch(
        r"XEQM[0-9A-Za-z]{20,200}", operator
    ):
        raise ValueError("operator address has an unexpected shape")

    parts = [
        f"status {status}",
        "registered at block "
        f"{format_count(raw['registration_height'])} "
        f"(HF v{format_count(raw['registration_hf_version'])})",
        f"{format_xeqm(raw['total_contributed'])} of "
        f"{format_xeqm(raw['staking_requirement'])} XEQM staked",
        f"{len(contributors)} contributor"
        + ("" if len(contributors) == 1 else "s"),
        f"{format_count(raw['num_open_spots'])} open contributor spots",
        # operator_fee is in millionths: 100000 is 10%.
        f"operator fee {format_decimal(as_number(raw['operator_fee']) / 10000)}%",
        f"operator address {operator}",
        "version " + ".".join(format_count(part) for part in version),
        f"last uptime proof {_utc(raw['last_uptime_proof'], now)}",
        "last reward at block "
        f"{format_count(raw['last_reward_block_height'])}",
        f"allowed downtime {downtime:,} blocks "
        f"(~{downtime / BLOCKS_PER_DAY:.1f} days)",
        f"decommissioned {format_count(raw['decommission_count'])} "
        "times so far",
        f"swarm 0x{_hex(raw['swarm'], 16)}",
    ]

    unlock = int(as_number(raw["requested_unlock_height"]))

    if unlock:
        parts.append(f"stake unlock requested, unlocks at block {unlock:,}")

    votes = raw.get("pulse_votes")

    if isinstance(votes, dict):
        parts.append(
            "recent Pulse votes "
            f"{len(votes.get('voted') or [])} voted, "
            f"{len(votes.get('missed') or [])} missed"
        )

    return parts


def _node_from_page(text, pubkey):
    if pubkey not in text:
        return None

    registered = re.search(
        r"Registered\s+Block\s+([\d,]+)\s+HF\s+v(\d+)",
        text,
        flags=re.I
    )

    operator = _find(r"Operator Address\s+(XEQM[0-9A-Za-z]{20,200})", text)

    # Without these two the page is not a node page this file
    # understands.
    if not registered or not operator:
        return None

    status = _find(
        r"\b(Active|Decommissioned|Awaiting contributions?)\b"
        r"(?= on the network| )",
        text
    )

    parts = []

    if status:
        parts.append(f"status {status.lower()}")

    parts.append(
        f"registered at block {_grouped(registered.group(1))} "
        f"(HF v{registered.group(2)})"
    )

    stake = _find(r"\bStake\s+([\d,]+(?:\.\d+)?)", text)

    if stake:
        parts.append(
            f"{_grouped(stake.split('.')[0])} XEQM staked"
        )

    fee = _find(r"Operator fee:\s*([\d.]+%)", text)

    if fee:
        parts.append(f"operator fee {fee}")

    elif re.search(r"\bSolo operator\b", text, flags=re.I):
        parts.append("solo operator, operator fee 0%")

    parts.append(f"operator address {operator}")

    proof = re.search(
        r"Last Uptime Proof\s+([\d:]+)\s+v([\d.]+)",
        text,
        flags=re.I
    )

    if proof:
        parts.append(f"last uptime proof {proof.group(1)} ago")
        parts.append(f"version {proof.group(2)}")

    downtime = _find(r"Allowed Downtime\s+([\d,]+)\s+blocks", text)

    if downtime:
        parts.append(f"allowed downtime {_grouped(downtime)} blocks")

    swarm = _find(r"Swarm ID\s+(0x[0-9a-f]{1,16})\b", text)

    if swarm:
        parts.append(f"swarm {swarm}")

    return parts


def _node_extras(text):
    """
    Page-only details, added to either source.
    """

    extras = []

    next_test = _find(r"Next SN Test\s+Block\s+([\d,]+)", text)

    if next_test:
        extras.append(
            f"next uptime test at block {_grouped(next_test)}"
        )

    return extras


def _node_is_unknown(text):
    return re.search(
        r"service node is not currently registered",
        text,
        flags=re.I
    ) is not None


# ---------------------------------------------------------
# BLOCKS
# ---------------------------------------------------------

def _block_from_json(raw, kind, value, now):
    header = raw["block_header"]

    height = int(as_number(header["height"]))
    block_hash = _hex(header["hash"])

    if (kind == "height" and height != int(value)) or (
        kind == "hex" and block_hash != value
    ):
        raise ValueError("payload is for another block")

    tx_hashes = raw.get("tx_hashes") or []

    if not isinstance(tx_hashes, list):
        raise ValueError("tx_hashes is not a list")

    parts = [
        f"hash {block_hash}",
        "Pulse block" if isinstance(header.get("pulse"), dict)
        else "mined block",
        f"timestamp {_utc(header['timestamp'], now)}",
        f"{format_count(header['num_txes'])} transactions",
        f"size {format_count(header['block_size'])} bytes",
        f"reward {format_decimal(as_number(header['reward']) / ATOMIC_PER_XEQM)} XEQM",
        f"{format_count(header['depth'])} blocks deep",
        f"hard fork v{format_count(header['major_version'])}",
    ]

    winner = header.get("service_node_winner")

    if winner:
        parts.append(f"service node winner {_hex(winner)}")

    if tx_hashes:
        shown = [_hex(tx) for tx in tx_hashes[:10]]

        parts.append("transaction hashes " + ", ".join(shown))

    return height, parts


def _block_from_page(text, kind, value):
    height = _find(r"\bBlock (\d+) Chain Height\b", text)

    if not height:
        return None

    block_hash = _find(
        r"‹?\s*Block \d+\s+([0-9a-f]{64})\s+Block \d+",
        text
    ) or _find(r"\b([0-9a-f]{64})\s+Block \d+ (?:›|Latest)", text)

    if kind == "height" and int(height) != int(value):
        return None

    if kind == "hex" and block_hash != value:
        return None

    parts = []

    if block_hash:
        parts.append(f"hash {block_hash}")

    block_type = _find(r"Block Type\s+(\w+)", text)

    if block_type:
        parts.append(f"{block_type} block")

    timestamp = _find(r"\bTimestamp\s+(.{6,40}? UTC)", text)

    if timestamp:
        parts.append(f"timestamp {timestamp}")

    transactions = _find(r"\bTransactions\s+(\d+)\s+Type\b", text)

    if transactions:
        parts.append(f"{transactions} transactions")

    size = _find(r"Block Size\s+([\d.]+\s*[kMG]?B)\b", text)

    if size:
        parts.append(f"size {size}")

    reward = _find(r"Block Reward\s+([\d,.]+)\s*XEQM", text)

    if reward:
        parts.append(f"reward {reward} XEQM")

    depth = _find(r"Depth\s+([\d,]+)\s+blocks", text)

    if depth:
        parts.append(f"{depth} blocks deep")

    winner = _find(r"Service Node Winner\s+([0-9a-f]{64})", text)

    if winner:
        parts.append(f"service node winner {winner}")

    return int(height), parts


# ---------------------------------------------------------
# TRANSACTIONS
# ---------------------------------------------------------

def _tx_from_page(text, tx_hash):
    if _find(r"TX Hash:\s*([0-9a-f]{64})", text) != tx_hash:
        return None

    parts = []

    # A missing label says nothing about confirmation; it is
    # left out rather than read as "unconfirmed".
    block = _find(r"In block:\s*([\d,]+)", text)

    if block:
        parts.append(f"in block {_grouped(block)}")

    tx_type = _find(
        r"TX Version/Type:\s*\d+/\s*(?:[^\w\s]+\s*)?"
        r"([A-Za-z][A-Za-z _-]{0,40}?)\s+Timestamp:",
        text
    )

    if tx_type:
        parts.append(f"type {tx_type.lower()}")

    for label, pattern in (
        ("timestamp", r"Timestamp:\s*(.{6,40}? UTC)"),
        ("fee per kB", r"Fee \(Per kB\):\s*(N/A|[\d.,]+(?: XEQM)?)"),
        ("size", r"TX Size:\s*([\d.]+\s*[kMG]?B)\b"),
        ("confirmations", r"No\. Confirmations:\s*([\d,]+)"),
        ("service node", r"Service Node Public Key:\s*([0-9a-f]{64})"),
    ):
        found = _find(pattern, text)

        if found:
            parts.append(f"{label} {found}")

    return parts


def _is_not_found(text):
    return re.search(r"\bNot Found\b", text) is not None


# ---------------------------------------------------------
# LOOKUP
# ---------------------------------------------------------

class _Unreachable(Exception):
    pass


class ExplorerLookup:

    def __init__(self):
        # Same bounds as LiveData: this sits on the request
        # path of a question.
        self.timeout = (3.05, 6)

        # All requests for one question share this budget.
        self.fetch_budget_seconds = 8

        self.cache_seconds = 30
        self.failure_cache_seconds = 10
        self.max_cache_entries = 256

        self.headers = {
            "User-Agent": "EXIOM-AI/1.0"
        }

        # A fresh Session per question: lookups run on many
        # request threads at once, and nothing is shared
        # between them but the cache below.
        self.session_factory = requests.Session

        self._now = time.time

        # (kind, id) -> (stored_at, ttl, fact)
        self._cache = {}
        self._cache_lock = threading.Lock()


    def _cached(self, key):
        with self._cache_lock:
            item = self._cache.get(key)

            if item and self._now() - item[0] <= item[1]:
                return item[2]

        return None


    def _store(self, key, fact, ttl):
        with self._cache_lock:
            now = self._now()

            for stale in [
                k for k, item in self._cache.items()
                if now - item[0] > item[1]
            ]:
                del self._cache[stale]

            while len(self._cache) >= self.max_cache_entries:
                del self._cache[next(iter(self._cache))]

            self._cache[key] = (now, ttl, fact)


    def _get(self, session, path, deadline):
        """
        Raw HTML of a page, or None when it gave no usable
        answer. Raises _Unreachable when the host cannot be
        reached or the budget is spent.
        """

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            raise _Unreachable()

        connect, read = self.timeout

        try:
            response = session.get(
                EXPLORER_URL + path,
                headers=self.headers,
                # Never past the question's budget.
                timeout=(min(connect, remaining), min(read, remaining)),
                # The Explorer redirects an ID it cannot show
                # to its dashboard; that is not an answer.
                allow_redirects=False
            )

            response.raise_for_status()

        except (requests.ConnectionError, requests.Timeout):
            raise _Unreachable() from None

        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None

        return response.text


    def _node(self, session, pubkey, deadline):
        raw_html = self._get(session, f"sn/{pubkey}/1", deadline)

        if raw_html is None:
            return "unreadable", None

        text = _page_text(raw_html)

        if _node_is_unknown(text):
            return "absent", None

        via = "api"

        try:
            raw = _raw_json(raw_html)

            if raw is None:
                raise ValueError("no raw payload")

            parts = _node_from_json(raw, pubkey, self._now())

        except (KeyError, IndexError, TypeError, ValueError, OverflowError):
            via = "page"
            parts = _node_from_page(text, pubkey)

        if not parts:
            return "unreadable", None

        return "found", {
            "label": f"Service node {pubkey}",
            "value": "; ".join(parts + _node_extras(text)),
            "via": via,
        }


    def _block(self, session, kind, value, deadline):
        raw_html = self._get(session, f"block/{value}/1", deadline)

        if raw_html is None:
            return "unreadable", None

        text = _page_text(raw_html)

        via = "api"

        try:
            raw = _raw_json(raw_html)

            if raw is None:
                raise ValueError("no raw payload")

            height, parts = _block_from_json(
                raw, kind, value, self._now()
            )

        except (KeyError, IndexError, TypeError, ValueError, OverflowError):
            via = "page"
            found = _block_from_page(text, kind, value)

            if found is None:
                if _is_not_found(text):
                    return "absent", None

                return "unreadable", None

            height, parts = found

        return "found", {
            "label": f"Block {height:,}",
            "value": "; ".join(parts),
            "via": via,
        }


    def _tx(self, session, tx_hash, deadline):
        raw_html = self._get(session, f"tx/{tx_hash}", deadline)

        if raw_html is None:
            return "unreadable", None

        text = _page_text(raw_html)

        parts = _tx_from_page(text, tx_hash)

        if parts is None:
            return (
                ("absent", None) if _is_not_found(text)
                else ("unreadable", None)
            )

        return "found", {
            "label": f"Transaction {tx_hash}",
            "value": "; ".join(parts),
            "via": "page",
        }


    def _resolve(self, session, kind, value, deadline):
        """
        Returns (fact, ttl).
        """

        if kind == "height":
            attempts = [lambda: self._block(session, kind, value, deadline)]
            what = f"block {int(value):,}"

        else:
            # A 64-hex ID may be a node key, a transaction or a
            # block hash; nothing in it says which.
            attempts = [
                lambda: self._node(session, value, deadline),
                lambda: self._tx(session, value, deadline),
                lambda: self._block(session, kind, value, deadline),
            ]
            what = f"service node, transaction or block {value}"

        unreadable = False

        try:
            for attempt in attempts:
                outcome, found = attempt()

                if outcome == "found":
                    return found, self.cache_seconds

                unreadable = unreadable or outcome == "unreadable"

        except _Unreachable:
            return {
                "label": f"Explorer lookup of {what}",
                "value": (
                    "The Official EXIOM Explorer could not be "
                    "reached to look this up."
                ),
                "via": None,
            }, self.failure_cache_seconds

        if unreadable:
            return {
                "label": f"Explorer lookup of {what}",
                "value": (
                    "The Official EXIOM Explorer's page for this "
                    "could not be read."
                ),
                "via": None,
            }, self.failure_cache_seconds

        return {
            "label": f"Explorer lookup of {what}",
            "value": (
                f"Not found: no {what} is shown on the Official "
                "EXIOM Explorer."
            ),
            "via": "page",
        }, self.cache_seconds


    def lookup(self, ids):
        """
        Facts for the given (kind, id) pairs, keyed like the
        Explorer fact registry.
        """

        facts = {}

        valid = [
            (kind, value) for kind, value in ids[:MAX_IDS_PER_QUESTION]
            if _valid(kind, value)
        ]

        if not valid:
            return facts

        deadline = time.monotonic() + self.fetch_budget_seconds

        session = None

        try:
            for kind, value in valid:

                fact = self._cached((kind, value))

                if fact is None:

                    if session is None:
                        session = self.session_factory()

                    fact, ttl = self._resolve(
                        session, kind, value, deadline
                    )

                    self._store((kind, value), fact, ttl)

                key = f"lookup_{kind}_{value}"

                facts[key] = {
                    "key": key,
                    "label": fact["label"],
                    "value": fact["value"],
                    "unit": "",
                    "source": SOURCE,
                    "via": fact["via"],
                }

        finally:
            if session is not None:
                session.close()

        return facts
