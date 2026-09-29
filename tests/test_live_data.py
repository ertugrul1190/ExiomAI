import json
import logging
import re
import threading
import time
from pathlib import Path

import requests

import live_data


PAGE = """
<html><body>
<div class="offline-banner is-hidden" id="offline-banner" hidden>
Disconnected. Explorer is not connected to a daemon.
</div>
<div>Block Height: 123,456</div>
<div>Active Service Nodes: 1,024</div>
<div>APY (current) 2.36%</div>
</body></html>
"""


FEEDS = {
    "api/live_slow": {
        "status": "OK",
        "height": 123457,
        "active_sns": 1025,
        "total_sns": 1030,
        "circulating_supply_atomic": 280_528_963_924_700_000,
        "total_locked_atomic": 184_400_000_000_000_000,
        "avg_24h": 60.016,
    },
    "api/networkinfo": {
        "status": "OK",
        "data": {"height": 123457, "tx_pool_size": 3},
    },
    "api/node_map": {
        "status": "OK",
        "data": {
            "summary": {"countries": 2},
            "nodes": [
                {"country": "France", "country_code": "FR", "count": 5},
                {"country": "Germany", "country_code": "DE", "count": 7},
                {"country": "France", "country_code": "FR", "count": 4},
            ],
        },
    },
}


class FakeResponse:

    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return json.loads(self.text)


class FakeSession:
    """
    Serves the Explorer's feeds and page; counts page
    fetches; optionally slow or failing.

    Tests change ``routes`` to break individual sources.
    """

    def __init__(self, delay=0.0, fail=False):
        self.delay = delay
        self.fail = fail
        self.calls = 0
        self.requests = 0
        self.paths = []
        self.timeouts = []
        self._lock = threading.Lock()

        self.routes = {"": FakeResponse(PAGE)}

        for path, payload in FEEDS.items():
            self.routes[path] = FakeResponse(json.dumps(payload))

    def get(self, url, headers=None, timeout=None):
        path = url.removeprefix(live_data.LiveData().explorer_url)

        with self._lock:
            self.requests += 1
            self.paths.append(path)
            self.timeouts.append(timeout)

            # Every reading asks for the dashboard exactly
            # once, whether or not the Explorer answers.
            if path == "":
                self.calls += 1

        time.sleep(self.delay)

        if self.fail:
            raise requests.ConnectionError("explorer down")

        return self.routes.get(path, FakeResponse("", 404))

    def close(self):
        pass


def wait_for_background_refresh(data):
    # The refresh holds the fetch lock for its whole run.
    with data._fetch_lock:
        pass


def build(session, clock=None):
    data = live_data.LiveData()
    data.session_factory = lambda: session

    if clock:
        data._now = clock

    return data


def test_a_page_is_parsed_into_facts():
    data = build(FakeSession())

    stats = data.get_network_stats()

    assert stats["status"] == "available"
    assert stats["facts"]["block_height"]["value"] == "123,457"
    assert stats["facts"]["current_apy"]["value"] == "2.36"


def test_the_explorer_call_is_time_bounded():
    session = FakeSession()

    build(session).get_network_stats()

    connect, read = session.timeouts[0]

    assert connect <= 5 and read <= 8


def test_concurrent_misses_fetch_the_explorer_once():
    """
    When the cache expires under load, every waiting request
    must share one fetch instead of stampeding the Explorer.
    """

    session = FakeSession(delay=0.2)
    data = build(session)

    results = []
    start = threading.Barrier(20)

    def call():
        start.wait()
        results.append(data.get_network_stats()["status"])

    threads = [threading.Thread(target=call) for _ in range(20)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert session.calls == 1
    assert results == ["available"] * 20


def test_a_failure_is_remembered_briefly():
    """
    A down Explorer must not add a full network timeout to
    every single question.
    """

    now = [1000.0]
    session = FakeSession(fail=True)
    data = build(session, clock=lambda: now[0])

    assert data.get_network_stats()["status"] == "unavailable"
    assert data.get_network_stats()["status"] == "unavailable"
    assert session.calls == 1

    now[0] += data.failure_cache_seconds + 1
    session.fail = False

    assert data.get_network_stats()["status"] == "available"
    assert session.calls == 2


def test_success_is_cached_for_its_window_only():
    now = [1000.0]
    session = FakeSession()
    data = build(session, clock=lambda: now[0])

    data.get_network_stats()
    data.get_fact_registry()
    assert session.calls == 1

    now[0] += data.cache_seconds + 1

    data.get_network_stats()
    assert session.calls == 2


def test_stale_values_are_never_served_after_a_failure():
    """
    Explorer values are presented as current, so an old
    reading must not outlive its window just because the
    Explorer went down.
    """

    now = [1000.0]
    session = FakeSession()
    data = build(session, clock=lambda: now[0])

    data.get_network_stats()

    now[0] += data.cache_seconds + 1
    session.fail = True

    stats = data.get_network_stats()

    assert stats["status"] == "unavailable"
    assert stats["facts"] == {}


def test_a_nearly_expired_reading_is_refreshed_in_the_background():
    """
    Under steady traffic nobody should wait for the Explorer:
    shortly before the window closes, one background fetch
    renews it while callers keep the still-valid reading.
    """

    now = [1000.0]
    session = FakeSession()
    data = build(session, clock=lambda: now[0])

    data.get_network_stats()

    now[0] += data.cache_seconds - data.refresh_ahead_seconds + 1

    session.delay = 0.2

    started = time.perf_counter()
    stats = data.get_network_stats()
    waited = time.perf_counter() - started

    assert stats["status"] == "available"
    assert waited < 0.1

    # Only one background refresh, however many callers.
    for _ in range(10):
        data.get_network_stats()

    wait_for_background_refresh(data)

    assert session.calls == 2
    assert data.cache["network_stats"]["time"] == now[0]


def test_a_failure_is_never_refreshed_ahead():
    now = [1000.0]
    session = FakeSession(fail=True)
    data = build(session, clock=lambda: now[0])

    data.get_network_stats()

    now[0] += data.failure_cache_seconds - 1

    data.get_network_stats()

    assert session.calls == 1


def test_a_failed_early_refresh_keeps_the_valid_reading():
    """
    A refresh-ahead runs while the current reading still has
    time left. Its failure must not throw that reading away.
    """

    now = [1000.0]
    session = FakeSession()
    data = build(session, clock=lambda: now[0])

    data.get_network_stats()

    now[0] += data.cache_seconds - data.refresh_ahead_seconds + 1
    session.fail = True

    data.get_network_stats()
    wait_for_background_refresh(data)

    assert session.calls == 2
    assert data.get_network_stats()["status"] == "available"

    # ...and once that reading expires, the failure shows.
    now[0] += data.refresh_ahead_seconds

    assert data.get_network_stats()["status"] == "unavailable"


def test_feeds_are_read_before_the_page():
    stats = build(FakeSession()).get_network_stats()
    facts = stats["facts"]

    assert facts["block_height"]["via"] == "api"
    assert facts["active_nodes"]["value"] == "1,025"
    assert facts["locked_supply"]["value"] == "184,400,000"
    assert facts["unlocked_supply"]["value"] == "96,128,964"
    assert facts["locked_supply_percent"]["value"] == "65.7"
    assert facts["average_block_time_24h"]["value"] == "1m 00s"
    assert facts["mempool_transactions"]["value"] == "3"

    # Facts the page alone shows still come from the page.
    assert facts["current_apy"]["via"] == "page"


def test_nodes_by_country_adds_up_regions():
    facts = build(FakeSession()).get_network_stats()["facts"]

    assert facts["nodes_by_country"]["value"] == "France: 9\nGermany: 7"
    assert facts["node_countries"]["value"] == "2"


def test_nodes_by_country_merges_spellings_of_one_country():
    # The live feed lists Turkey under both names, with the
    # same country code.
    session = FakeSession()
    session.routes["api/node_map"] = FakeResponse(json.dumps({
        "status": "OK",
        "data": {
            "summary": {"countries": 2},
            "nodes": [
                {"country": "Turkey", "country_code": "TR", "count": 30},
                {"country": "Germany", "country_code": "DE", "count": 20},
                {"country": "Türkiye", "country_code": "TR", "count": 4},
            ],
        },
    }))

    facts = build(session).get_network_stats()["facts"]

    assert facts["nodes_by_country"]["value"] == "Turkey: 34\nGermany: 20"


def test_a_removed_feed_falls_back_to_the_page():
    session = FakeSession()
    del session.routes["api/live_slow"]
    del session.routes["api/networkinfo"]

    stats = build(session).get_network_stats()
    block_height = stats["facts"]["block_height"]

    assert stats["status"] == "available"
    assert block_height["value"] == "123,456"
    assert block_height["via"] == "page"

    # A fact only a feed carries is gone, not guessed.
    assert "registered_nodes" not in stats["facts"]


def test_a_feed_that_is_no_longer_json_falls_back():
    session = FakeSession()
    session.routes["api/live_slow"] = FakeResponse("<html>moved</html>")

    facts = build(session).get_network_stats()["facts"]

    assert facts["active_nodes"]["value"] == "1,024"
    assert facts["active_nodes"]["via"] == "page"


def test_a_feed_reporting_a_bad_status_is_not_trusted():
    session = FakeSession()
    session.routes["api/live_slow"] = FakeResponse(
        json.dumps({**FEEDS["api/live_slow"], "status": "BUSY"})
    )

    facts = build(session).get_network_stats()["facts"]

    assert facts["active_nodes"]["via"] == "page"


def test_a_renamed_field_moves_only_that_fact():
    session = FakeSession()
    renamed = dict(FEEDS["api/live_slow"])
    renamed["active_service_nodes"] = renamed.pop("active_sns")
    session.routes["api/live_slow"] = FakeResponse(json.dumps(renamed))

    facts = build(session).get_network_stats()["facts"]

    assert facts["active_nodes"]["via"] == "page"
    assert facts["active_nodes"]["value"] == "1,024"
    assert facts["registered_nodes"]["via"] == "api"


def test_a_field_of_the_wrong_type_falls_back():
    session = FakeSession()
    changed = dict(FEEDS["api/live_slow"])
    changed["active_sns"] = "1025"
    session.routes["api/live_slow"] = FakeResponse(json.dumps(changed))

    facts = build(session).get_network_stats()["facts"]

    assert facts["active_nodes"]["via"] == "page"


def test_feeds_alone_are_enough_when_the_page_breaks():
    session = FakeSession()
    session.routes[""] = FakeResponse("", 500)

    stats = build(session).get_network_stats()

    assert stats["status"] == "available"
    assert stats["connection_state"] == "connected"
    assert stats["facts"]["block_height"]["value"] == "123,457"
    assert "current_apy" not in stats["facts"]


def test_an_unrecognisable_explorer_is_unavailable():
    """
    Every source answered, but nothing in them is a fact:
    nothing can be presented as current.
    """

    session = FakeSession()
    session.routes = {"": FakeResponse("<html>redesigned</html>")}

    assert build(session).get_network_stats()["status"] == (
        "unavailable"
    )


def test_an_unreachable_explorer_costs_one_round_of_requests():
    """
    The sources are asked at once, so a down Explorer costs
    one timeout, and no background page fetch is started.
    """

    session = FakeSession(fail=True)
    data = build(session)

    data.get_network_stats()
    data.wait_for_page_refreshes()

    assert "quorums" not in session.paths
    assert session.requests == len(data.feeds) + 2


def test_the_hidden_offline_banner_means_connected():
    """
    The page always carries its "Disconnected" banner and
    hides it while the daemon is up.
    """

    session = FakeSession()
    del session.routes["api/live_slow"]
    del session.routes["api/networkinfo"]
    del session.routes["api/node_map"]

    stats = build(session).get_network_stats()

    assert stats["connection_state"] == "connected"


def test_a_visible_offline_banner_means_disconnected():
    session = FakeSession()
    session.routes[""] = FakeResponse(
        PAGE.replace(' hidden>', '>').replace("is-hidden", "")
    )

    stats = build(session).get_network_stats()

    assert stats["connection_state"] == "disconnected"


def test_a_broken_source_is_logged_once(caplog):
    now = [1000.0]
    session = FakeSession()
    del session.routes["api/node_map"]
    data = build(session, clock=lambda: now[0])

    with caplog.at_level(logging.WARNING, logger="live_data"):
        data.get_network_stats()
        now[0] += data.cache_seconds + 1
        data.get_network_stats()

    warnings = [
        record for record in caplog.records
        if "node_map" in record.getMessage()
    ]

    assert len(warnings) == 1


# ---------------------------------------------------------
# FACTS FROM THE OTHER EXPLORER PAGES
# ---------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures" / "explorer"


def explorer_page(name):
    return FakeResponse((FIXTURES / name).read_text())


def session_with_pages():
    session = FakeSession()
    session.routes[""] = explorer_page("dashboard.html")
    session.routes["txpool"] = explorer_page("txpool.html")
    session.routes["quorums"] = explorer_page("quorums.html")
    session.routes["service_nodes"] = explorer_page("service_nodes.html")

    return session


def settled(data):
    """
    A reading taken once the background pages have arrived.
    """

    data.get_network_stats()
    data.wait_for_page_refreshes()
    data.cache.clear()

    return data.get_network_stats()


def test_quorum_counts_come_from_the_quorums_page():
    facts = settled(build(session_with_pages()))["facts"]

    assert facts["testing_quorums"]["value"] == "55"
    assert facts["pulse_quorums"]["value"] == "56"
    assert facts["checkpoint_quorums"]["value"] == "14"
    assert facts["blink_quorums"]["value"] == "11"


def test_mempool_size_comes_from_the_mempool_page():
    facts = build(session_with_pages()).get_network_stats()["facts"]

    assert facts["mempool_size"]["value"] == "0B"


def test_current_release_adoption_comes_from_the_node_list():
    facts = settled(build(session_with_pages()))["facts"]

    assert facts["nodes_on_current_release"]["value"] == "490/916"


def test_swarms_fall_back_to_the_node_list():
    session = session_with_pages()
    del session.routes["api/live_slow"]

    facts = settled(build(session))["facts"]

    assert facts["active_swarms"]["value"] == "134"
    assert facts["active_swarms"]["via"] == "page"


def test_the_real_dashboard_is_read_as_connected():
    stats = build(session_with_pages()).get_network_stats()

    assert stats["connection_state"] == "connected"


def test_slow_pages_never_hold_up_a_reading():
    session = session_with_pages()
    session.delay = 0.3
    data = build(session)

    started = time.perf_counter()

    # Every request takes 0.3 s and the sources are fetched
    # in parallel, so a reading costs one request's time.
    data.get_network_stats()
    waited = time.perf_counter() - started

    data.wait_for_page_refreshes()

    assert waited < 0.6


def test_slow_pages_are_fetched_at_their_own_interval():
    """
    The quorum and node-list pages are large and change
    slowly; they are not refetched on every 30 s reading.
    """

    now = [1000.0]
    session = session_with_pages()
    data = build(session, clock=lambda: now[0])

    def quorum_fetches():
        return session.paths.count("quorums")

    settled(data)

    now[0] += data.cache_seconds + 1
    data.get_network_stats()
    data.wait_for_page_refreshes()

    assert quorum_fetches() == 1

    # Renewal starts halfway through a copy's life.
    now[0] = 1000.0 + data.pages["quorums"]["max_age"] / 2
    data.cache.clear()
    facts = data.get_network_stats()["facts"]
    data.wait_for_page_refreshes()

    assert facts["pulse_quorums"]["value"] == "56"
    assert quorum_fetches() == 2


def test_an_expired_slow_page_is_not_used():
    now = [1000.0]
    session = session_with_pages()
    data = build(session, clock=lambda: now[0])

    settled(data)

    session.routes["quorums"] = FakeResponse("", 500)
    now[0] += data.pages["quorums"]["max_age"] + 1
    data.cache.clear()

    facts = data.get_network_stats()["facts"]

    assert "pulse_quorums" not in facts
    assert "block_height" in facts


def test_a_failed_slow_page_is_dropped_not_reused():
    now = [1000.0]
    session = session_with_pages()
    data = build(session, clock=lambda: now[0])

    settled(data)

    session.routes["quorums"] = FakeResponse("", 500)
    now[0] += data.pages["quorums"]["max_age"] / 2
    data.cache.clear()
    data.get_network_stats()
    data.wait_for_page_refreshes()
    data.cache.clear()

    assert "pulse_quorums" not in data.get_network_stats()["facts"]


def test_a_background_page_not_yet_fetched_is_not_logged(caplog):
    session = session_with_pages()
    session.delay = 0.05

    with caplog.at_level(logging.WARNING, logger="live_data"):
        data = build(session)
        data.get_network_stats()
        data.wait_for_page_refreshes()

    assert not [
        r for r in caplog.records if "quorums" in r.getMessage()
    ]


def test_a_sub_minute_block_time_reads_like_the_page():
    session = FakeSession()
    fast = dict(FEEDS["api/live_slow"], avg_24h=59.4)
    session.routes["api/live_slow"] = FakeResponse(json.dumps(fast))

    facts = build(session).get_network_stats()["facts"]

    assert facts["average_block_time_24h"]["value"] == "59s"


def test_a_sub_minute_block_time_falls_back_to_the_page():
    session = FakeSession()
    del session.routes["api/live_slow"]
    session.routes[""] = FakeResponse(
        PAGE + "<div>Avg Block (1h) 59s Avg Block (12h) 1m 00s</div>"
    )

    facts = build(session).get_network_stats()["facts"]

    assert facts["average_block_time_1h"]["value"] == "59s"


def test_a_banner_marked_not_hidden_means_disconnected():
    session = FakeSession()
    session.routes[""] = FakeResponse(
        PAGE.replace(
            'class="offline-banner is-hidden" id="offline-banner" hidden',
            'class="offline-banner" id="offline-banner" aria-hidden="false"'
        )
    )

    assert build(session).get_network_stats()["connection_state"] == (
        "disconnected"
    )


# ---------------------------------------------------------
# RECENT CHANGES AND THE NEXT UPGRADE
# ---------------------------------------------------------

def session_with_recent_pages():
    session = session_with_pages()
    session.routes[""] = explorer_page("dashboard_hf22.html")
    session.routes["service_nodes"] = explorer_page(
        "service_nodes_recent.html"
    )

    return session


def test_nodes_registered_in_the_last_day_come_from_the_node_list():
    facts = settled(build(session_with_recent_pages()))["facts"]

    # 43 active rows and 2 awaiting rows registered after block
    # 210,253 - 1,440 (the page's own "Lifespan" agrees).
    assert facts["nodes_registered_24h"]["value"] == (
        "45 (2 still awaiting contributions)"
    )


def test_a_full_first_page_of_new_nodes_is_a_lower_bound():
    session = session_with_recent_pages()
    page = (FIXTURES / "service_nodes_recent.html").read_text()

    # Every row on the first page registered a block ago.
    session.routes["service_nodes"] = FakeResponse(
        re.sub(r"#2\d{5}\b", "#210252", page)
    )

    value = settled(build(session))["facts"]["nodes_registered_24h"]["value"]

    assert value.startswith("at least ")


def test_no_node_list_means_no_new_node_count():
    session = session_with_recent_pages()
    del session.routes["service_nodes"]

    facts = settled(build(session))["facts"]

    assert "nodes_registered_24h" not in facts


def test_the_next_hard_fork_comes_from_the_dashboard():
    facts = settled(build(session_with_recent_pages()))["facts"]

    assert facts["next_hard_fork"]["value"] == (
        "HF v22 (SN Policy) at block 219,120: 8,867 blocks to go, "
        "estimated 2026-10-05 19:00 UTC"
    )


def test_no_upcoming_fork_on_the_page_means_no_fact():
    facts = settled(build(session_with_pages()))["facts"]

    assert "next_hard_fork" not in facts


def test_short_window_block_figures_come_from_the_feed():
    session = FakeSession()
    feed = dict(FEEDS["api/live_slow"], blocks_1h=60, blocks_12h=720, avg_12h=60.2)
    session.routes["api/live_slow"] = FakeResponse(json.dumps(feed))

    facts = build(session).get_network_stats()["facts"]

    assert facts["blocks_1h"]["value"] == "60"
    assert facts["blocks_12h"]["value"] == "720"
    assert facts["average_block_time_12h"]["value"] == "1m 00s"


def test_the_twelve_hour_block_time_falls_back_to_the_page():
    facts = settled(build(session_with_recent_pages()))["facts"]

    assert facts["average_block_time_12h"]["value"] == "1m 00s"


def test_the_node_count_change_appears_a_day_later():
    now = [1_000_000.0]
    session = FakeSession()
    data = build(session, clock=lambda: now[0])

    data.get_network_stats()

    feed = dict(FEEDS["api/live_slow"], total_sns=1040)
    session.routes["api/live_slow"] = FakeResponse(json.dumps(feed))
    now[0] += 24 * 60 * 60

    facts = data.get_network_stats()["facts"]

    assert facts["node_count_change_24h"]["value"] == (
        "+10 (from 1,030 to 1,040)"
    )


def test_nodes_by_region_group_under_their_country():
    session = FakeSession()
    feed = json.loads(json.dumps(FEEDS["api/node_map"]))
    feed["data"]["nodes"] = [
        {"country": "United States", "country_code": "US", "count": 25, "region": "Virginia"},
        {"country": "Canada", "country_code": "CA", "count": 45, "region": "Quebec"},
        {"country": "United States", "country_code": "US", "count": 48, "region": "New York"},
        {"country": "Canada", "country_code": "CA", "count": 4, "region": "British Columbia"},
        {"country": "United States", "country_code": "US", "count": 2, "region": "Virginia"},
    ]
    session.routes["api/node_map"] = FakeResponse(json.dumps(feed))

    facts = build(session).get_network_stats()["facts"]

    assert facts["nodes_by_region"]["value"] == (
        "United States: New York 48, Virginia 27\n"
        "Canada: Quebec 45, British Columbia 4"
    )


def test_a_map_without_regions_gives_no_region_fact():
    facts = build(FakeSession()).get_network_stats()["facts"]

    assert "nodes_by_region" not in facts
