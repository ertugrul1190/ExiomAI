import json
import sqlite3

import pytest

import usage_hub
from live_data import LiveData
from remote_usage import RemoteUsage, TaskLocal, share_live_readings


DAY = 20_000 * 86400  # 2024-10-04, any fixed UTC midnight


class Clock:
    def __init__(self, now=DAY + 3600):
        self.now = now

    def __call__(self):
        return self.now


def storage():
    """The Durable Object's SQL storage, as usage_hub sees it."""
    connection = sqlite3.connect(":memory:", isolation_level=None)
    return lambda query, params: connection.execute(query, params).fetchall()


def json_transport(hub):
    """Every call crosses a JSON boundary, as over RPC."""
    def call(op, args):
        return json.loads(hub.call(json.dumps({"op": op, "args": args})))
    return call


def failing_transport(op, args):
    raise RuntimeError("Durable Object unreachable")


@pytest.fixture
def hub(monkeypatch):
    monkeypatch.setenv("EXIOM_REQUESTS_PER_MINUTE", "2")
    monkeypatch.setenv("EXIOM_GLOBAL_TOKENS_PER_DAY", "1000")
    monkeypatch.setenv("EXIOM_MAX_CONCURRENT_ANSWERS", "1")
    monkeypatch.setenv("EXIOM_FLOOD_REQUESTS_PER_MINUTE", "3")
    return usage_hub.UsageHub(storage(), now=Clock())


def test_limits_are_shared_by_every_copy(hub):
    first = RemoteUsage(json_transport(hub))
    second = RemoteUsage(json_transport(hub))

    assert first.usage_controller.check("a").allowed
    assert second.usage_controller.check("a").allowed

    refused = first.usage_controller.check("a")
    assert not refused.allowed
    assert refused.reason == "client_rate"

    assert first.answer_slots.acquire("a")
    assert not second.answer_slots.acquire("a")
    second.answer_slots.release("a")
    assert first.answer_slots.acquire("a")

    assert [first.flood_guard.allow("b")[0] for _ in range(2)] == [True, True]
    assert second.flood_guard.allow("b")[0]
    allowed, retry_after = second.flood_guard.allow("b")
    assert not allowed and retry_after >= 1


def test_global_ceiling_survives_a_restarted_object(monkeypatch):
    monkeypatch.setenv("EXIOM_GLOBAL_TOKENS_PER_DAY", "1000")
    sql = storage()
    clock = Clock()

    remote = RemoteUsage(json_transport(usage_hub.UsageHub(sql, now=clock)))
    remote.cost_meter.record_usage(
        "gpt-5-nano",
        {"input_tokens": 900, "output_tokens": 200},
        "answer"
    )

    # Evicted and recreated: in-memory counters are gone, the
    # ledger in SQL storage is not.
    restarted = RemoteUsage(json_transport(usage_hub.UsageHub(sql, now=clock)))

    decision = restarted.usage_controller.check("new-client")
    assert not decision.allowed
    assert decision.reason == "global_daily_tokens"

    [today] = restarted.usage_ledger.daily()
    assert today["provider_calls"] == 1
    assert restarted.usage_ledger.state == "available"

    # A new UTC day starts from zero.
    clock.now += 86400
    assert restarted.usage_controller.check("new-client").allowed


def test_cost_meter_returns_the_charge_and_records_it(hub):
    remote = RemoteUsage(json_transport(hub))

    charged = remote.cost_meter.record_usage(
        "gpt-5-nano",
        {
            "input_tokens": 100,
            "output_tokens": 10,
            "input_tokens_details": {"cached_tokens": 40},
        },
        "answer"
    )
    remote.cost_meter.record_web_searches(2, "answer")
    remote.cost_meter.record_free_response("live")

    assert charged["input_tokens"] == 100
    assert charged["cached_input_tokens"] == 40

    snapshot = remote.cost_meter.snapshot()
    assert snapshot["provider_calls"] == 1
    assert snapshot["web_searches"] == 2
    assert snapshot["free_responses"] == 1
    assert remote.usage_controller.snapshot()["limits"]["requests_per_minute"] == 2


def test_an_unreachable_object_fails_towards_spending_less():
    remote = RemoteUsage(failing_transport)

    decision = remote.usage_controller.check("a")
    assert not decision.allowed
    assert decision.reason.startswith("global")

    assert remote.usage_controller.claim_web_search("a") is False

    # Free routes and bookkeeping never break a response.
    assert remote.flood_guard.allow("a") == (True, 0)
    assert remote.answer_slots.acquire("a") is True
    remote.answer_slots.release("a")
    remote.usage_controller.record_tokens("a", 10)
    remote.cost_meter.record_free_response("live")
    assert remote.cost_meter.record_usage(
        "gpt-5-nano", {"input_tokens": 5, "output_tokens": 1}, "answer"
    )["input_tokens"] == 5
    assert remote.usage_ledger.daily() == []
    assert remote.usage_ledger.state == "unavailable"


def test_unknown_operations_are_refused(hub):
    with pytest.raises(ValueError):
        hub.call(json.dumps({"op": "_prune", "args": {}}))


def reading(status, time, ttl=30):
    return {"time": time, "ttl": ttl, "data": {"status": status, "facts": {}}}


def test_a_failed_refresh_keeps_a_still_valid_reading(hub):
    remote = json_transport(hub)

    remote("put_reading", {"item": reading("available", DAY + 3590)})
    remote("put_reading", {"item": reading("unavailable", DAY + 3600, 10)})
    assert remote("get_reading", {})["data"]["status"] == "available"

    remote("put_reading", {"item": reading("unavailable", DAY + 3625, 10)})
    assert remote("get_reading", {})["data"]["status"] == "unavailable"


def live_data_at(clock):
    live = LiveData()
    live._now = clock
    live.fetches = 0

    def fetch_directly():
        live.fetches += 1
        return {"status": "available", "facts": {}, "fetched": True}

    live._refresh_locked = fetch_directly
    return live


def test_requests_read_the_shared_reading_instead_of_the_explorer(hub):
    clock = Clock()
    live = live_data_at(clock)
    call = json_transport(hub)
    share_live_readings(live, call)

    call("put_reading", {"item": reading("available", clock.now - 5)})

    assert live.get_network_stats()["status"] == "available"
    assert live.fetches == 0

    # A stale shared reading is never served; the copy fetches.
    clock.now += 60
    assert live.get_network_stats()["fetched"]
    assert live.fetches == 1


def test_an_unreachable_object_falls_back_to_fetching():
    live = live_data_at(Clock())
    share_live_readings(live, failing_transport)

    assert live.get_network_stats()["fetched"]


def test_the_global_ceiling_counts_provider_usage_once(hub):
    remote = RemoteUsage(json_transport(hub))

    remote.cost_meter.record_usage(
        "gpt-5-nano", {"input_tokens": 600, "output_tokens": 0}, "answer"
    )
    remote.usage_controller.record_tokens("a", 600)

    assert remote.usage_controller.snapshot()["global_tokens_today"] == 600
    assert remote.usage_controller.check("b").allowed

    remote.cost_meter.record_usage(
        "gpt-5-nano", {"input_tokens": 400, "output_tokens": 0}, "answer"
    )
    assert remote.usage_controller.check("b").reason == "global_daily_tokens"


def test_task_local_keeps_interleaved_requests_apart():
    import asyncio

    state = TaskLocal()
    seen = {}

    async def request(name, delay):
        state.usage = name
        await asyncio.sleep(delay)
        seen[name] = state.usage

    async def both():
        await asyncio.gather(request("first", 0.02), request("second", 0.01))

    asyncio.run(both())

    assert seen == {"first": "first", "second": "second"}
    assert getattr(state, "usage", None) is None


def test_an_answer_slot_never_released_expires(monkeypatch):
    monkeypatch.setenv("EXIOM_MAX_CONCURRENT_ANSWERS", "1")
    clock = Clock()
    remote = RemoteUsage(json_transport(usage_hub.UsageHub(storage(), now=clock)))

    # A copy killed mid-stream never sends the release.
    assert remote.answer_slots.acquire("a")
    assert not remote.answer_slots.acquire("a")

    clock.now += usage_hub.ANSWER_LEASE_SECONDS
    assert remote.answer_slots.acquire("a")


def test_paid_work_waits_until_today_is_restored(monkeypatch):
    broken = {"on": True}
    healthy = storage()

    def flaky(query, params):
        if broken["on"]:
            raise RuntimeError("storage unavailable")
        return healthy(query, params)

    remote = RemoteUsage(json_transport(usage_hub.UsageHub(flaky, now=Clock())))

    decision = remote.usage_controller.check("a")
    assert not decision.allowed
    assert decision.reason == "global_usage_unavailable"

    broken["on"] = False
    assert remote.usage_controller.check("a").allowed
