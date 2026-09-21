import time

import cache


def test_ttl_cache_returns_stored_value():
    store = cache.TTLCache(ttl_seconds=60)
    store.set("key", "value")

    assert store.get("key") == "value"


def test_ttl_cache_expires_entries():
    store = cache.TTLCache(ttl_seconds=0.01)
    store.set("key", "value")

    time.sleep(0.02)

    assert store.get("key") is None


def test_ttl_cache_evicts_least_recently_used():
    store = cache.TTLCache(ttl_seconds=60, max_entries=2)

    store.set("a", 1)
    store.set("b", 2)
    store.get("a")
    store.set("c", 3)

    assert store.get("a") == 1
    assert store.get("c") == 3
    assert store.get("b") is None


def test_ttl_cache_ignores_empty_keys():
    store = cache.TTLCache()

    store.set(None, "value")

    assert store.get(None) is None


def test_ttl_cache_reports_hit_rate():
    store = cache.TTLCache()

    store.set("a", 1)
    store.get("a")
    store.get("missing")

    stats = store.stats()

    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5


def test_router_key_ignores_fact_key_order():
    assert cache.router_cache_key("hi", ["b", "a"]) == \
        cache.router_cache_key("hi", ["a", "b"])


def test_router_key_changes_with_available_facts():
    assert cache.router_cache_key("hi", ["a"]) != \
        cache.router_cache_key("hi", ["a", "b"])


def test_router_key_requires_a_question():
    assert cache.router_cache_key("", ["a"]) is None


def test_answer_key_changes_when_a_fact_value_changes():
    first = cache.answer_cache_key(
        "how many nodes", "relevant", "mixed",
        {"active_nodes": "100"}, "knowledge"
    )

    second = cache.answer_cache_key(
        "how many nodes", "relevant", "mixed",
        {"active_nodes": "101"}, "knowledge"
    )

    assert first != second


def test_answer_key_changes_when_knowledge_changes():
    first = cache.answer_cache_key(
        "what is staking", "relevant", "explanation", {}, "old"
    )

    second = cache.answer_cache_key(
        "what is staking", "relevant", "explanation", {}, "new"
    )

    assert first != second


def test_answer_key_changes_when_the_explorer_goes_down():
    """
    Explorer health reaches the prompt even when no fact is
    selected, so it has to reach the key too.
    """

    available = cache.answer_cache_key(
        "what is staking", "relevant", "explanation", {}, "knowledge",
        explorer_state="available/connected"
    )

    unavailable = cache.answer_cache_key(
        "what is staking", "relevant", "explanation", {}, "knowledge",
        explorer_state="unavailable/unknown"
    )

    assert available != unavailable


def test_answer_key_is_stable_for_identical_inputs():
    arguments = (
        "what is staking", "relevant", "explanation",
        {"a": "1"}, "knowledge"
    )

    assert cache.answer_cache_key(*arguments) == \
        cache.answer_cache_key(*arguments)
