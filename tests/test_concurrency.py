"""
Concurrency tests against a REAL threaded HTTP server.

The Flask test client runs one request at a time, so it can
never expose shared-state bugs. These tests start an actual
server in-process and drive it with loadtest.py -- the same
tool used against production -- while the provider is faked
with realistic latency.
"""

import threading
import time

import pytest

from werkzeug.serving import make_server

import app as application
import loadtest
import usage_control

from test_ask_endpoint import FakeProvider, provider  # noqa: F401


PROVIDER_DELAY = 0.05


class SlowProvider(FakeProvider):
    """
    FakeProvider with network-like latency on every call.
    """

    def route_question(self, *args, **kwargs):
        time.sleep(PROVIDER_DELAY)
        return super().route_question(*args, **kwargs)

    def generate(self, *args, **kwargs):
        time.sleep(PROVIDER_DELAY)
        return super().generate(*args, **kwargs)

    def stream_generate(self, *args, **kwargs):
        for chunk in super().stream_generate(*args, **kwargs):
            time.sleep(PROVIDER_DELAY)
            yield chunk


@pytest.fixture
def server(provider, monkeypatch):  # noqa: F811

    monkeypatch.setattr(application, "ai_provider", SlowProvider())

    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(
            requests_per_minute=10_000,
            requests_per_day=10_000
        )
    )

    # Keep the output readable; the server logs every request.
    httpd = make_server("127.0.0.1", 0, application.app, threaded=True)
    httpd.log_request = lambda *args, **kwargs: None

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{httpd.server_port}"

    httpd.shutdown()
    thread.join(timeout=5)


def unique_questions(count, stem):
    return [f"{stem} number {index}" for index in range(count)]


def test_concurrent_answers_never_cross(server):
    """
    Forty different questions at once: every caller must get
    the answer to its OWN question.
    """

    questions = unique_questions(40, "explain staking")

    results, elapsed = loadtest.run_load(
        server, questions, concurrency=20, total=40
    )

    assert [r["status"] for r in results] == [200] * 40

    for result in results:
        assert result["answer"] == f"answer to {result['question']}"

    # Serially this is 40 x (router + answer) = 4 seconds.
    assert elapsed < 40 * 2 * PROVIDER_DELAY / 2


def test_concurrent_streams_arrive_progressively(server):

    questions = unique_questions(20, "how do rewards work")

    results, _ = loadtest.run_load(
        server, questions, concurrency=20, total=20, stream=True
    )

    for result in results:

        assert result["status"] == 200
        assert result["answer"] == f"answer to {result['question']}"

        # Text starts well before the answer is finished.
        assert result["ttfb_ms"] < result["latency_ms"] - PROVIDER_DELAY * 1000


def test_identical_questions_under_load_stay_correct(server):
    """
    Many callers asking the same thing at once exercise the
    router and answer caches from many threads.
    """

    results, _ = loadtest.run_load(
        server, ["what is staking"], concurrency=20, total=60
    )

    assert {r["status"] for r in results} == {200}
    assert {r["answer"] for r in results} == {"answer to what is staking"}


def test_the_rate_limit_holds_under_a_burst(server, monkeypatch):
    """
    A burst from one client must be admitted exactly up to
    its allowance: no lost updates between threads.
    """

    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(
            requests_per_minute=15,
            requests_per_day=10_000
        )
    )

    results, _ = loadtest.run_load(
        server,
        unique_questions(30, "explain nodes"),
        concurrency=30,
        total=30
    )

    statuses = sorted(r["status"] for r in results)

    assert statuses.count(200) == 15
    assert statuses.count(429) == 15


def test_fast_path_throughput(server):
    results, elapsed = loadtest.run_load(
        server, ["hello"], concurrency=10, total=200
    )

    report = loadtest.summarize(results, elapsed)

    assert report["statuses"] == {200: 200}
    assert report["failures"] == 0
    assert report["latency_ms"]["p95"] < 250, report


# ---------------------------------------------------------
# THE TOOL ITSELF
# ---------------------------------------------------------

def test_percentile_is_nearest_rank():
    samples = list(range(1, 101))

    assert loadtest.percentile(samples, 0.50) == 50
    assert loadtest.percentile(samples, 0.95) == 95
    assert loadtest.percentile(samples, 1.00) == 100
    assert loadtest.percentile([], 0.5) == 0.0


def test_transport_failures_fail_the_run():
    # Nothing listens on port 9 (discard) on a test machine.
    exit_code = loadtest.main([
        "--url", "http://127.0.0.1:9",
        "--requests", "2",
        "--concurrency", "2",
        "--timeout", "2",
    ])

    assert exit_code == 1


def test_a_stream_that_breaks_counts_as_a_failure(server, monkeypatch):
    """
    A broken stream still arrived with HTTP 200; only its
    error frame says it failed. The run must not pass.
    """

    application.ai_provider.stream_error_after = 1

    results, elapsed = loadtest.run_load(
        server, ["how do rewards work"], concurrency=2, total=2, stream=True
    )

    report = loadtest.summarize(results, elapsed)

    assert report["statuses"] == {200: 2}
    assert report["failures"] == 2


def test_a_malformed_frame_is_a_failure_not_a_crash():

    class Response:
        def iter_lines(self, decode_unicode=True):
            yield 'data: {"type":"delta","text":"hi"}'
            yield "data: {not json"

    answer, first_frame, error = loadtest.read_stream(Response())

    assert answer == "hi"
    assert first_frame is not None
    assert "malformed" in error
