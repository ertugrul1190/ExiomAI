import sqlite3
import threading

import usage_control
from usage_ledger import UsageLedger


DAY = 20_000 * 86400  # 2024-10-04, any fixed UTC midnight


def ledger_at(tmp_path, now=DAY + 3600):
    return UsageLedger(str(tmp_path / "usage.sqlite3"), now=lambda: now)


def test_records_add_up_per_day_and_route(tmp_path):
    ledger = ledger_at(tmp_path)

    ledger.record("answer", calls=1, input_tokens=100, output_tokens=20,
                  cost_usd=0.001)
    ledger.record("answer", calls=1, input_tokens=50, output_tokens=10,
                  web_searches=1, cost_usd=0.011)
    ledger.record("live", free_responses=1)

    [today] = ledger.daily()

    assert today["day"] == "2024-10-04"
    assert today["provider_calls"] == 2
    assert today["free_responses"] == 1
    assert today["input_tokens"] == 150
    assert today["output_tokens"] == 30
    assert today["web_searches"] == 1
    assert abs(today["estimated_cost_usd"] - 0.012) < 1e-9
    assert today["by_route"]["answer"]["provider_calls"] == 2
    assert today["by_route"]["live"]["free_responses"] == 1


def test_survives_a_restart_and_is_shared_between_instances(tmp_path):
    ledger_at(tmp_path).record("router", calls=1, cost_usd=0.5)
    ledger_at(tmp_path).record("router", calls=1, cost_usd=0.5)

    [today] = ledger_at(tmp_path).daily()

    assert today["provider_calls"] == 2
    assert today["estimated_cost_usd"] == 1.0


def test_days_are_utc_and_newest_first(tmp_path):
    ledger_at(tmp_path, now=DAY - 1).record("answer", calls=1)
    ledger_at(tmp_path, now=DAY).record("answer", calls=3)

    days = ledger_at(tmp_path).daily()

    assert [day["day"] for day in days] == ["2024-10-04", "2024-10-03"]
    assert [day["provider_calls"] for day in days] == [3, 1]


def test_daily_is_limited_to_the_requested_window(tmp_path):
    for offset in range(5):
        ledger_at(tmp_path, now=DAY + offset * 86400).record("answer", calls=1)

    ledger = ledger_at(tmp_path, now=DAY + 4 * 86400)

    assert len(ledger.daily(days=2)) == 2


def test_concurrent_writes_are_not_lost(tmp_path):
    ledger = ledger_at(tmp_path)

    def write():
        for _ in range(25):
            ledger.record("answer", calls=1)

    threads = [threading.Thread(target=write) for _ in range(4)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert ledger.daily()[0]["provider_calls"] == 100


def test_a_broken_store_never_raises(tmp_path):
    # A directory where the file should be: every open fails.
    (tmp_path / "usage.sqlite3").mkdir()

    ledger = ledger_at(tmp_path)

    ledger.record("answer", calls=1)

    assert ledger.daily() == []
    assert ledger.available is False


def test_a_disabled_ledger_does_nothing(tmp_path):
    ledger = UsageLedger("")

    ledger.record("answer", calls=1)

    assert ledger.daily() == []
    assert ledger.available is False


def test_only_counters_are_stored(tmp_path):
    ledger = ledger_at(tmp_path)
    ledger.record("answer", calls=1, input_tokens=5)

    with sqlite3.connect(tmp_path / "usage.sqlite3") as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(usage_daily)")
        }

    assert columns == {
        "day", "route", "calls", "free_responses", "input_tokens",
        "cached_input_tokens", "output_tokens", "reasoning_tokens",
        "web_searches", "cost_usd",
    }


# ---------------------------------------------------------
# COST METER → LEDGER
# ---------------------------------------------------------

def test_cost_meter_writes_every_call_to_the_ledger(tmp_path):
    ledger = ledger_at(tmp_path)
    meter = usage_control.CostMeter(ledger=ledger)

    meter.record_usage(
        "gpt-5-nano",
        {"input_tokens": 1000, "output_tokens": 100},
        "answer"
    )
    meter.record_web_searches(2, "answer")
    meter.record_free_response("live")

    [today] = ledger.daily()

    assert today["provider_calls"] == 1
    assert today["input_tokens"] == 1000
    assert today["web_searches"] == 2
    assert today["free_responses"] == 1

    expected = (
        meter.estimate_cost("gpt-5-nano", 1000, 0, 100)
        + 2 * usage_control.WEB_SEARCH_CALL_USD
    )

    assert abs(today["estimated_cost_usd"] - expected) < 1e-9


def test_cost_meter_counts_web_searches_in_memory_too():
    meter = usage_control.CostMeter()

    meter.record_web_searches(3, "answer")
    meter.record_web_searches(0, "answer")

    snapshot = meter.snapshot()

    assert snapshot["web_searches"] == 3
    assert snapshot["estimated_cost_usd"] == round(
        3 * usage_control.WEB_SEARCH_CALL_USD, 6
    )
    assert snapshot["by_route"]["answer"]["web_searches"] == 3


def test_the_window_is_calendar_days_not_active_days(tmp_path):
    ledger_at(tmp_path, now=DAY - 40 * 86400).record("answer", calls=1)
    ledger_at(tmp_path, now=DAY).record("answer", calls=1)

    days = ledger_at(tmp_path, now=DAY).daily(days=30)

    assert [day["day"] for day in days] == ["2024-10-04"]


def test_state_reports_off_available_and_unavailable(tmp_path):
    assert UsageLedger("off").state == "off"
    assert UsageLedger(" OFF ").path == ""

    ledger = ledger_at(tmp_path)
    ledger.record("answer", calls=1)

    assert ledger.state == "available"

    (tmp_path / "broken").mkdir()
    broken = UsageLedger(str(tmp_path / "broken"))
    broken.record("answer", calls=1)

    assert broken.state == "unavailable"
