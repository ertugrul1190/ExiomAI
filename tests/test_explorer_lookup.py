import json
import re
import threading
from pathlib import Path

import requests

import explorer_lookup


FIXTURES = Path(__file__).parent / "fixtures" / "explorer"

NODE = "99efd7f74cc325ae6d2b62a08be9e932d960dfb53243f3f2d67595cb378747ba"
BLOCK_HASH = (
    "a35feb521bf533427a1293a53521ea02ef6e4f1559041af6d8d589112e67c814"
)
TX = "8a3840a780e22f46503dfc3a52431f52aa5f4b7aaf9fe8ce76eab25f8f8189ee"
UNKNOWN = "ab" * 32


def fixture(name):
    return (FIXTURES / name).read_text()


class FakeResponse:

    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeSession:
    """
    Serves Explorer pages by path, the way the real Explorer
    answers: an unknown ID is a 200 page saying so.
    """

    def __init__(self, routes=None, fail=False):
        self.routes = routes if routes is not None else {
            f"sn/{NODE}/1": FakeResponse(fixture("node.html")),
            f"sn/{UNKNOWN}/1": FakeResponse(fixture("node_unknown.html")),
            f"block/{BLOCK_HASH}/1": FakeResponse(fixture("block.html")),
            "block/203140/1": FakeResponse(fixture("block.html")),
            f"block/{UNKNOWN}/1": FakeResponse(
                fixture("block_not_found.html")
            ),
            "block/999999999/1": FakeResponse(
                fixture("block_not_found.html")
            ),
            f"tx/{TX}": FakeResponse(fixture("tx.html")),
            f"tx/{UNKNOWN}": FakeResponse(fixture("tx_not_found.html")),
            # A node key is tried as a node first; a tx hash
            # or block hash is not a node.
            f"sn/{TX}/1": FakeResponse(fixture("node_unknown.html")),
            f"sn/{BLOCK_HASH}/1": FakeResponse(
                fixture("node_unknown.html")
            ),
            f"tx/{BLOCK_HASH}": FakeResponse(
                fixture("tx_not_found.html")
            ),
        }
        self.fail = fail
        self.paths = []
        self.kwargs = []
        self._lock = threading.Lock()

    def get(self, url, **kwargs):
        path = url.removeprefix(explorer_lookup.EXPLORER_URL)

        with self._lock:
            self.paths.append(path)
            self.kwargs.append(kwargs)

        if self.fail:
            raise requests.ConnectionError("explorer down")

        return self.routes.get(path, FakeResponse("", 404))

    def close(self):
        pass


def build(session, clock=None):
    lookups = explorer_lookup.ExplorerLookup()
    lookups.session_factory = lambda: session

    if clock:
        lookups._now = clock

    return lookups


def only_fact(facts):
    assert len(facts) == 1

    return next(iter(facts.values()))


def without_markup(page):
    """
    The same page with its embedded raw JSON removed, as if
    the Explorer stopped embedding it.
    """

    return re.sub(
        r'id="more_details".*?</pre>',
        'id="more_details">',
        page,
        flags=re.S
    )


# ---------------------------------------------------------
# FINDING IDS IN A QUESTION
# ---------------------------------------------------------

def test_a_64_hex_id_is_found():
    ids = explorer_lookup.find_ids(f"is node {NODE.upper()} ok?")

    assert ids == [("hex", NODE)]


def test_block_heights_are_found():
    assert explorer_lookup.find_ids("what's in block 203140?") == [
        ("height", "203140")
    ]
    assert explorer_lookup.find_ids("block #5") == [("height", "5")]
    assert explorer_lookup.find_ids("show me #203140") == [
        ("height", "203140")
    ]


def test_a_block_count_or_time_is_not_a_height():
    for question in [
        "what was the block height 2 days ago",
        "block time 60 seconds?",
        "is XEQM the #1 coin",
        "what is the block height",
        "blocks 5 minutes apart",
    ]:
        assert explorer_lookup.find_ids(question) == [], question


def test_longer_hex_is_not_an_id():
    assert explorer_lookup.find_ids("a" * 65) == []


def test_ids_are_deduplicated_and_capped():
    question = " ".join(
        [NODE, NODE.upper()]
        + [f"{n:064x}" for n in range(1, 6)]
    )

    ids = explorer_lookup.find_ids(question)

    assert ids[0] == ("hex", NODE)
    assert len(ids) == explorer_lookup.MAX_IDS_PER_QUESTION


# ---------------------------------------------------------
# SERVICE NODES
# ---------------------------------------------------------

def test_a_node_is_read_from_its_raw_json():
    fact = only_fact(build(FakeSession()).lookup([("hex", NODE)]))

    assert fact["via"] == "api"
    assert NODE in fact["label"]

    value = fact["value"]

    assert "status active" in value
    assert "registered at block 5,948 (HF v19)" in value
    assert "200,000 of 200,000 XEQM staked" in value
    assert "1 contributor" in value
    assert "operator fee 0%" in value
    assert "version 1.0.7" in value
    assert "last reward at block 203,149" in value
    assert "allowed downtime 2,176 blocks" in value
    assert "swarm 0x47ffffffffffffff" in value
    assert "next uptime test at block 203,173" in value


def test_a_node_never_exposes_its_network_address():
    """
    The raw payload carries the node's IP and ports; the
    Explorer's own UI promises not to expose them.
    """

    value = only_fact(
        build(FakeSession()).lookup([("hex", NODE)])
    )["value"]

    assert "203.0.113.7" not in value
    assert "9232" not in value
    assert "key_image" not in value


def test_a_node_falls_back_to_the_page_without_raw_json():
    session = FakeSession()
    session.routes[f"sn/{NODE}/1"] = FakeResponse(
        without_markup(fixture("node.html"))
    )

    fact = only_fact(build(session).lookup([("hex", NODE)]))

    assert fact["via"] == "page"
    assert "status active" in fact["value"]
    assert "registered at block 5,948 (HF v19)" in fact["value"]
    assert "operator address XEQMKPoL34" in fact["value"]
    assert "203.0.113.7" not in fact["value"]


def test_raw_json_for_another_node_is_not_trusted():
    page = fixture("node.html").replace(NODE[:40], "0" * 40)
    session = FakeSession()
    session.routes[f"sn/{NODE}/1"] = FakeResponse(page)

    fact = only_fact(build(session).lookup([("hex", NODE)]))

    assert fact["via"] != "api"


def test_a_raw_field_of_the_wrong_type_falls_back_to_the_page():
    page = fixture("node.html").replace(
        '<span class="mi">5948</span>',
        '<span class="s2">&quot;5948&quot;</span>'
    )
    assert page != fixture("node.html")

    session = FakeSession()
    session.routes[f"sn/{NODE}/1"] = FakeResponse(page)

    fact = only_fact(build(session).lookup([("hex", NODE)]))

    assert fact["via"] == "page"


# ---------------------------------------------------------
# BLOCKS
# ---------------------------------------------------------

def test_a_block_is_read_by_height_from_its_raw_json():
    fact = only_fact(
        build(FakeSession()).lookup([("height", "203140")])
    )

    assert fact["via"] == "api"
    assert fact["label"] == "Block 203,140"

    value = fact["value"]

    assert f"hash {BLOCK_HASH}" in value
    assert "Pulse block" in value
    assert "3 transactions" in value
    assert "size 2,310 bytes" in value
    assert "reward 8.25 XEQM" in value
    assert "service node winner 336c2295" in value
    assert "2026-09-24 16:34 UTC" in value
    assert TX in value


def test_a_block_is_found_by_hash_after_node_and_tx_miss():
    session = FakeSession()

    fact = only_fact(build(session).lookup([("hex", BLOCK_HASH)]))

    assert fact["label"] == "Block 203,140"
    assert session.paths == [
        f"sn/{BLOCK_HASH}/1",
        f"tx/{BLOCK_HASH}",
        f"block/{BLOCK_HASH}/1",
    ]


def test_a_block_falls_back_to_the_page_without_raw_json():
    session = FakeSession()
    session.routes["block/203140/1"] = FakeResponse(
        without_markup(fixture("block.html"))
    )

    fact = only_fact(build(session).lookup([("height", "203140")]))

    assert fact["via"] == "page"
    assert "Pulse block" in fact["value"]
    assert "3 transactions" in fact["value"]
    assert "reward 8.25 XEQM" in fact["value"]
    assert f"hash {BLOCK_HASH}" in fact["value"]


def test_a_missing_block_is_reported_as_not_found():
    fact = only_fact(
        build(FakeSession()).lookup([("height", "999999999")])
    )

    assert "not found" in fact["value"].lower()


# ---------------------------------------------------------
# TRANSACTIONS
# ---------------------------------------------------------

def test_a_transaction_is_read_from_its_page():
    session = FakeSession()

    fact = only_fact(build(session).lookup([("hex", TX)]))

    assert fact["via"] == "page"
    assert fact["label"] == f"Transaction {TX}"

    value = fact["value"]

    assert "in block 203,140" in value
    assert "type recommission" in value
    assert "size 473B" in value
    assert "confirmations 33" in value
    assert "service node 2852052c" in value

    # Found as a transaction: no block request needed.
    assert session.paths == [f"sn/{TX}/1", f"tx/{TX}"]


# ---------------------------------------------------------
# UNKNOWN IDS AND FAILURES
# ---------------------------------------------------------

def test_an_unknown_id_is_reported_as_not_found():
    fact = only_fact(build(FakeSession()).lookup([("hex", UNKNOWN)]))

    assert "no service node, transaction or block" in (
        fact["value"].lower()
    )


def test_an_unreachable_explorer_is_reported_not_guessed():
    session = FakeSession(fail=True)

    fact = only_fact(build(session).lookup([("hex", NODE)]))

    assert fact["via"] is None
    assert "could not be reached" in fact["value"]

    # One failed connection is enough; the rest share a host.
    assert len(session.paths) == 1


def test_a_changed_page_is_never_read_as_not_found():
    """
    A page the lookup no longer recognises is "could not be
    read", never a confident "does not exist".
    """

    session = FakeSession(routes={
        f"sn/{NODE}/1": FakeResponse("<html>redesigned</html>"),
        f"tx/{NODE}": FakeResponse("<html>redesigned</html>"),
        f"block/{NODE}/1": FakeResponse("<html>redesigned</html>"),
    })

    fact = only_fact(build(session).lookup([("hex", NODE)]))

    assert "not found" not in fact["value"].lower()
    assert "could not be read" in fact["value"]


def test_a_redirect_is_not_followed():
    session = FakeSession()

    build(session).lookup([("hex", NODE)])

    assert session.kwargs[0]["allow_redirects"] is False


def test_every_request_is_time_bounded():
    session = FakeSession()

    build(session).lookup([("hex", UNKNOWN)])

    for kwargs in session.kwargs:
        connect, read = kwargs["timeout"]
        assert connect <= 5 and read <= 8


def test_results_are_cached_briefly():
    now = [1000.0]
    session = FakeSession()
    lookups = build(session, clock=lambda: now[0])

    lookups.lookup([("hex", NODE)])
    lookups.lookup([("hex", NODE)])

    assert len(session.paths) == 1

    now[0] += lookups.cache_seconds + 1
    lookups.lookup([("hex", NODE)])

    assert len(session.paths) == 2


def test_failures_are_cached_more_briefly():
    now = [1000.0]
    session = FakeSession(fail=True)
    lookups = build(session, clock=lambda: now[0])

    lookups.lookup([("hex", NODE)])
    now[0] += lookups.failure_cache_seconds + 1
    session.fail = False

    fact = only_fact(lookups.lookup([("hex", NODE)]))

    assert fact["via"] == "api"


def test_the_cache_is_bounded():
    lookups = build(FakeSession(routes={}))
    lookups.max_cache_entries = 3

    lookups.lookup([("height", str(n)) for n in range(3)])
    lookups.lookup([("height", str(n)) for n in range(3, 6)])

    assert len(lookups._cache) <= 3


def test_nothing_outside_a_validated_id_reaches_a_url():
    session = FakeSession()

    build(session).lookup([
        ("hex", "../../admin"),
        ("height", "1/../../x"),
        ("other", NODE),
    ])

    assert session.paths == []


def test_block_fact_values_are_plain_text():
    """
    Values go into the model's prompt; they must be the
    parsed fields, never raw page markup.
    """

    for ids in ([("height", "203140")], [("hex", TX)], [("hex", NODE)]):
        value = only_fact(build(FakeSession()).lookup(ids))["value"]

        assert "<" not in value and "{" not in value
        json.dumps(value)


def test_a_missing_block_label_is_not_read_as_unconfirmed():
    session = FakeSession()
    session.routes[f"tx/{TX}"] = FakeResponse(
        fixture("tx.html").replace("In block:", "Included in:")
    )

    value = only_fact(build(session).lookup([("hex", TX)]))["value"]

    assert "not yet" not in value
    assert "in block" not in value


def test_an_absurd_timestamp_falls_back_to_the_page():
    page = fixture("node.html").replace(
        '<span class="mi">1790269350</span>',
        '<span class="mi">99999999999999999999</span>'
    )
    assert page != fixture("node.html")

    session = FakeSession()
    session.routes[f"sn/{NODE}/1"] = FakeResponse(page)

    fact = only_fact(build(session).lookup([("hex", NODE)]))

    assert fact["via"] == "page"


def test_a_request_never_outlasts_the_budget():
    session = FakeSession()
    lookups = build(session)
    lookups.fetch_budget_seconds = 1

    lookups.lookup([("hex", NODE)])

    connect, read = session.kwargs[0]["timeout"]

    assert connect <= 1 and read <= 1


def test_ids_sharing_a_prefix_keep_separate_facts():
    first = NODE
    second = NODE[:60] + "0000"

    facts = build(FakeSession()).lookup([("hex", first), ("hex", second)])

    assert len(facts) == 2
