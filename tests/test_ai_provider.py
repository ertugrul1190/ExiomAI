import pytest

try:  # The SDK vendors its HTTP client under a versioned name.
    import httpx2 as httpx

except ImportError:  # pragma: no cover - older SDK layout
    import httpx

from openai import APIStatusError, APITimeoutError, RateLimitError

import ai_provider


REGISTRY = {
    "active_nodes": {
        "label": "Active service nodes",
        "meaning": "count of active nodes"
    }
}


class FakeResponse:

    def __init__(self, text="ok", usage=None):
        self.output_text = text
        self.usage = usage or {
            "input_tokens": 100,
            "output_tokens": 20,
            "input_tokens_details": {"cached_tokens": 80},
        }


class FakeResponses:

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def create(self, **request):
        self.requests.append(request)

        outcome = self.outcomes.pop(0)

        if isinstance(outcome, Exception):
            raise outcome

        return outcome


class FakeClient:

    def __init__(self, outcomes):
        self.responses = FakeResponses(outcomes)


def build_provider(outcomes, monkeypatch):
    monkeypatch.setattr(ai_provider.time, "sleep", lambda _: None)

    provider = ai_provider.AIProvider()
    provider.client = FakeClient(outcomes)

    return provider


def status_error(code, message):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(code, request=request)

    error_type = RateLimitError if code == 429 else APIStatusError

    return error_type(message, response=response, body=None)


# ---------------------------------------------------------
# COST CONTROLS
# ---------------------------------------------------------

def test_router_call_uses_the_cheapest_settings(monkeypatch):
    provider = build_provider(
        [FakeResponse('{"scope":"relevant","intent":"general","facts":[]}')],
        monkeypatch
    )

    provider.route_question("hello", [], REGISTRY)

    request = provider.client.responses.requests[0]

    assert request["reasoning"] == {"effort": "minimal"}
    assert request["max_output_tokens"] == ai_provider.ROUTER_MAX_OUTPUT_TOKENS
    assert request["text"] == {"format": {"type": "json_object"}}


def test_router_never_sends_the_question_twice(monkeypatch):
    provider = build_provider([FakeResponse("{}")], monkeypatch)

    provider.route_question("how many active nodes", [], REGISTRY)

    messages = provider.client.responses.requests[0]["input"]

    assert messages[0]["role"] == "system"
    assert "how many active nodes" not in messages[0]["content"]
    assert messages[-1]["content"] == "how many active nodes"


def test_router_history_is_tightly_trimmed(monkeypatch):
    provider = build_provider([FakeResponse("{}")], monkeypatch)

    conversation = [
        {"role": "user", "content": "x" * 5000},
        {"role": "assistant", "content": "y" * 5000},
        {"role": "user", "content": "z" * 5000},
    ]

    provider.route_question("and now?", conversation, REGISTRY)

    messages = provider.client.responses.requests[0]["input"]
    history = messages[1:-1]

    assert len(history) <= ai_provider.ROUTER_HISTORY_MESSAGES

    for message in history:
        assert len(message["content"]) <= ai_provider.ROUTER_HISTORY_CHARS + 1


def test_answer_call_keeps_more_room_than_the_router(monkeypatch):
    provider = build_provider([FakeResponse("answer")], monkeypatch)

    provider.generate("system", [], "question")

    request = provider.client.responses.requests[0]

    assert request["max_output_tokens"] == ai_provider.MAIN_MAX_OUTPUT_TOKENS
    assert "text" not in request


def test_off_topic_call_is_capped_short(monkeypatch):
    provider = build_provider([FakeResponse("banter")], monkeypatch)

    provider.generate_off_topic([], "chicken biryani recipe")

    request = provider.client.responses.requests[0]

    assert request["max_output_tokens"] == \
        ai_provider.OFF_TOPIC_MAX_OUTPUT_TOKENS


def test_router_prompt_is_reused_until_the_facts_change(monkeypatch):
    provider = build_provider([], monkeypatch)

    first = provider.get_router_prompt(REGISTRY)
    second = provider.get_router_prompt(dict(REGISTRY))

    assert first is second

    third = provider.get_router_prompt(
        {**REGISTRY, "block_height": {"label": "Block height"}}
    )

    assert third is not first


# ---------------------------------------------------------
# GRACEFUL DEGRADATION
# ---------------------------------------------------------

def test_rejected_reasoning_option_is_dropped_and_retried(monkeypatch):
    provider = build_provider(
        [
            status_error(400, "Unsupported parameter: 'reasoning.effort'"),
            FakeResponse("answer"),
        ],
        monkeypatch
    )

    result = provider.generate("system", [], "question")

    assert result["answer"] == "answer"
    assert provider.supports_reasoning_effort is False
    assert "reasoning" not in provider.client.responses.requests[1]


def test_rejected_text_option_is_dropped_and_retried(monkeypatch):
    provider = build_provider(
        [
            status_error(400, "Unsupported parameter: 'text.format'"),
            FakeResponse("{}"),
        ],
        monkeypatch
    )

    provider.route_question("hello", [], REGISTRY)

    assert provider.supports_text_options is False
    assert "text" not in provider.client.responses.requests[1]


def test_a_context_length_error_never_disables_json_mode(monkeypatch):
    """
    "text" is a substring of "context". A cost control may
    only be dropped when the provider rejected it by name.
    """

    provider = build_provider(
        [status_error(400, "maximum context length exceeded")],
        monkeypatch
    )

    with pytest.raises(APIStatusError):
        provider.route_question("hello", [], REGISTRY)

    assert provider.supports_text_options is True
    assert len(provider.client.responses.requests) == 1


def test_other_client_errors_are_not_retried(monkeypatch):
    provider = build_provider(
        [status_error(400, "invalid api key")],
        monkeypatch
    )

    with pytest.raises(APIStatusError):
        provider.generate("system", [], "question")

    assert len(provider.client.responses.requests) == 1


def test_temporary_failures_are_retried_once(monkeypatch):
    provider = build_provider(
        [status_error(429, "slow down"), FakeResponse("answer")],
        monkeypatch
    )

    assert provider.generate("system", [], "question")["answer"] == "answer"


def test_repeated_failure_raises_the_last_error(monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")

    provider = build_provider(
        [
            APITimeoutError(request=request),
            APITimeoutError(request=request),
        ],
        monkeypatch
    )

    with pytest.raises(APITimeoutError):
        provider.generate("system", [], "question")


# ---------------------------------------------------------
# METERING
# ---------------------------------------------------------

def test_every_call_is_metered(monkeypatch):
    provider = build_provider([FakeResponse("answer")], monkeypatch)

    provider.generate("system", [], "question")

    snapshot = provider.cost_meter.snapshot()

    assert snapshot["provider_calls"] == 1
    assert snapshot["input_tokens"] == 100
    assert snapshot["cached_input_tokens"] == 80
    assert provider.last_usage["output_tokens"] == 20


def test_usage_is_not_shared_between_threads(monkeypatch):
    """
    One process serves many callers at once. Usage must never
    be charged to whoever asks for it last.
    """

    import threading

    provider = build_provider(
        [
            FakeResponse("answer", {"input_tokens": 10, "output_tokens": 1}),
            FakeResponse("answer", {"input_tokens": 20, "output_tokens": 2}),
        ],
        monkeypatch
    )

    seen = {}
    started = threading.Barrier(2)

    def call(name):
        started.wait()
        provider.generate("system", [], name)
        seen[name] = provider.last_usage

    threads = [
        threading.Thread(target=call, args=(name,))
        for name in ("a", "b")
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert seen["a"] is not seen["b"]
    assert {usage["input_tokens"] for usage in seen.values()} == {10, 20}


def test_usage_is_cleared_before_each_call(monkeypatch):
    provider = build_provider(
        [FakeResponse("answer"), status_error(400, "invalid request")],
        monkeypatch
    )

    provider.generate("system", [], "question")

    assert provider.last_usage is not None

    with pytest.raises(APIStatusError):
        provider.generate("system", [], "question")

    assert provider.last_usage is None


def test_failed_calls_are_not_metered(monkeypatch):
    provider = build_provider(
        [status_error(400, "invalid request")],
        monkeypatch
    )

    with pytest.raises(APIStatusError):
        provider.generate("system", [], "question")

    assert provider.cost_meter.snapshot()["provider_calls"] == 0
