"""
Response-time budgets for the application's OWN work.

The provider and the Explorer are faked with zero latency, so
these numbers measure only routing, retrieval, prompt
building, caching and serialisation. The budgets are wide on
purpose: they exist to catch an accidental blocking call or
an O(n^2) slip, not to benchmark the machine running CI.

Real end-to-end latency is measured with loadtest.py.
"""

import re
import statistics
import time

import pytest

import app as application
import usage_control

# The endpoint tests' fakes and fixtures, reused as-is.
from test_ask_endpoint import (  # noqa: F401
    ask,
    ask_stream,
    client,
    provider,
)


RUNS = 40


@pytest.fixture
def unlimited(provider, monkeypatch):
    """
    The real limiter would rightly refuse a timing loop.
    """

    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(
            requests_per_minute=10_000,
            requests_per_day=10_000
        )
    )

    return provider


def timings(call):
    samples = []

    for _ in range(RUNS):
        started = time.perf_counter()
        response = call()
        samples.append((time.perf_counter() - started) * 1000)

        assert response.status_code == 200

    samples.sort()

    return {
        "p50": statistics.median(samples),
        "p95": samples[int(RUNS * 0.95) - 1],
    }


def test_fast_path_answers_are_near_instant(client, provider):
    result = timings(lambda: ask(client, "hello"))

    assert result["p95"] < 25, result


def test_cached_answers_are_near_instant(client, unlimited):
    ask(client, "what is staking")

    result = timings(lambda: ask(client, "what is staking"))

    assert unlimited.calls == 2  # router + answer, once
    assert result["p95"] < 25, result


def test_full_pipeline_overhead_is_small(client, unlimited):
    """
    Every run is a new question, so nothing is cached: the
    whole routing + retrieval + prompt path runs each time.
    """

    counter = iter(range(10_000))

    result = timings(
        lambda: ask(client, f"explain service node staking {next(counter)}")
    )

    assert result["p95"] < 50, result


def test_streaming_overhead_is_small(client, unlimited):
    counter = iter(range(10_000))

    result = timings(
        lambda: ask_stream(client, f"how do rewards work {next(counter)}")
    )

    assert result["p95"] < 50, result


# ---------------------------------------------------------
# OBSERVABILITY
# ---------------------------------------------------------

def test_every_response_reports_its_server_time(client, provider):
    for response in (
        ask(client, "hello"),
        ask_stream(client, "what is staking"),
        client.get("/api/network-stats"),
    ):
        header = response.headers.get("Server-Timing", "")

        assert re.fullmatch(r"app;dur=\d+(\.\d+)?", header), header


def test_slow_requests_are_logged(client, provider, monkeypatch, capsys):
    monkeypatch.setattr(application, "SLOW_REQUEST_MS", 0.0)

    ask(client, "hello")

    assert "EXIOM slow request: POST /ask" in capsys.readouterr().out


# ---------------------------------------------------------
# STATIC ASSETS
# ---------------------------------------------------------

def test_the_stylesheet_is_versioned_by_its_content(client):
    page = client.get("/").get_data(as_text=True)

    match = re.search(r'href="(/static/style\.css\?v=([0-9a-f]{12}))"', page)

    assert match, "stylesheet link is not versioned"

    response = client.get(match.group(1))

    assert response.status_code == 200
    assert "max-age=31536000" in response.headers["Cache-Control"]
    assert "immutable" in response.headers["Cache-Control"]


def test_an_unversioned_asset_is_not_cached_for_a_year(client):
    response = client.get("/static/style.css")

    assert "max-age=31536000" not in response.headers.get(
        "Cache-Control", ""
    )


def test_the_version_follows_the_file(tmp_path, monkeypatch):
    asset = tmp_path / "style.css"
    asset.write_text("a")

    monkeypatch.setattr(application.app, "static_folder", str(tmp_path))

    first = application.asset_version("style.css")

    # A different size alone must invalidate the memo, even
    # where the clock is too coarse to move the mtime.
    asset.write_text("bb")

    assert application.asset_version("style.css") != first


def test_a_missing_asset_does_not_break_the_page(monkeypatch, tmp_path):
    monkeypatch.setattr(application.app, "static_folder", str(tmp_path))

    assert application.asset_version("missing.css") == ""


@pytest.fixture(autouse=True)
def _fresh_version_memo():
    application._asset_versions.clear()
    yield
    application._asset_versions.clear()
