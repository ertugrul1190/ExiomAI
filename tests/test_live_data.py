import threading
import time

import requests

import live_data


PAGE = """
<html><body>
<div>Block Height: 123,456</div>
<div>Active Service Nodes: 1,024</div>
</body></html>
"""


class FakeResponse:

    text = PAGE

    def raise_for_status(self):
        pass


class FakeSession:
    """
    Counts Explorer fetches; optionally slow or failing.
    """

    def __init__(self, delay=0.0, fail=False):
        self.delay = delay
        self.fail = fail
        self.calls = 0
        self.timeouts = []
        self._lock = threading.Lock()

    def get(self, url, headers=None, timeout=None):
        with self._lock:
            self.calls += 1
            self.timeouts.append(timeout)

        time.sleep(self.delay)

        if self.fail:
            raise requests.ConnectionError("explorer down")

        return FakeResponse()


def wait_for_background_refresh(data):
    # The refresh holds the fetch lock for its whole run.
    with data._fetch_lock:
        pass


def build(session, clock=None):
    data = live_data.LiveData()
    data.session = session

    if clock:
        data._now = clock

    return data


def test_a_page_is_parsed_into_facts():
    data = build(FakeSession())

    stats = data.get_network_stats()

    assert stats["status"] == "available"
    assert stats["facts"]["block_height"]["value"] == "123,456"


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
