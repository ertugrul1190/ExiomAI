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


# ---------------------------------------------------------
# TIMEOUTS AND RETRIES
# ---------------------------------------------------------

class FakeStreamEvent:

    def __init__(self, delta):
        self.type = "response.output_text.delta"
        self.delta = delta


class FakeStream:

    def __init__(self, deltas, error_after=None):
        self.deltas = deltas
        self.error_after = error_after

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        for index, delta in enumerate(self.deltas):
            if self.error_after == index:
                raise APITimeoutError(
                    request=httpx.Request("POST", "https://x")
                )
            yield FakeStreamEvent(delta)

    def get_final_response(self):
        return FakeResponse("".join(self.deltas))


def attach_stream(provider, outcomes):
    """
    Give the fake client a stream() that plays outcomes in
    order: an exception is raised on open, a FakeStream is
    iterated.
    """

    outcomes = list(outcomes)

    def stream(**request):
        provider.client.responses.requests.append(request)

        outcome = outcomes.pop(0)

        if isinstance(outcome, Exception):
            raise outcome

        return outcome

    provider.client.responses.stream = stream


def record_sleeps(monkeypatch):
    sleeps = []
    monkeypatch.setattr(ai_provider.time, "sleep", sleeps.append)
    return sleeps


def test_router_fails_faster_than_the_answer(monkeypatch):
    provider = build_provider(
        [FakeResponse("{}"), FakeResponse("answer")],
        monkeypatch
    )

    provider.route_question("hello", [], REGISTRY)
    provider.generate("system", [], "question")

    router, answer = provider.client.responses.requests

    assert router["timeout"].read < answer["timeout"].read
    assert router["timeout"].connect == ai_provider.CONNECT_TIMEOUT


def test_server_errors_are_retried(monkeypatch):
    provider = build_provider(
        [status_error(503, "busy"), FakeResponse("answer")],
        monkeypatch
    )

    assert provider.generate("system", [], "question")["answer"] == "answer"
    assert len(provider.client.responses.requests) == 2


def test_an_exhausted_quota_fails_immediately(monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")

    error = RateLimitError(
        "quota",
        response=httpx.Response(429, request=request),
        body={"code": "insufficient_quota"}
    )

    provider = build_provider([error], monkeypatch)

    with pytest.raises(RateLimitError):
        provider.generate("system", [], "question")

    assert len(provider.client.responses.requests) == 1


def test_retry_after_sets_the_wait(monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")

    error = RateLimitError(
        "slow down",
        response=httpx.Response(
            429,
            request=request,
            headers={"retry-after": "2"}
        ),
        body=None
    )

    provider = build_provider([error, FakeResponse("answer")], monkeypatch)
    sleeps = record_sleeps(monkeypatch)

    provider.generate("system", [], "question")

    assert sleeps == [2.0]


def test_no_retry_is_started_that_cannot_finish(monkeypatch):
    monkeypatch.setitem(
        ai_provider.CALL_LIMITS,
        "answer",
        {"read": 1.0, "deadline": 1.0}
    )

    provider = build_provider(
        [status_error(503, "busy"), FakeResponse("answer")],
        monkeypatch
    )

    with pytest.raises(APIStatusError):
        provider.generate("system", [], "question")

    assert len(provider.client.responses.requests) == 1


def test_dropping_options_does_not_use_up_retries(monkeypatch):
    provider = build_provider(
        [
            status_error(400, "Unsupported parameter: 'reasoning.effort'"),
            status_error(400, "Unsupported parameter: 'text.format'"),
            FakeResponse('{"scope":"relevant","intent":"general","facts":[]}'),
        ],
        monkeypatch
    )

    route = provider.route_question("hello", [], REGISTRY)

    assert route["scope"] == "relevant"
    assert len(provider.client.responses.requests) == 3


def test_stream_retries_before_any_text(monkeypatch):
    provider = build_provider([], monkeypatch)

    attach_stream(provider, [
        status_error(503, "busy"),
        FakeStream(["hel", "lo"]),
    ])

    chunks = list(provider.stream_generate("system", [], "question"))

    assert chunks == ["hel", "lo"]
    assert provider.last_usage["output_tokens"] == 20
    assert provider.client.responses.requests[0]["timeout"].read == \
        ai_provider.CALL_LIMITS["answer"]["read"]


def test_stream_never_retries_once_text_was_sent(monkeypatch):
    provider = build_provider([], monkeypatch)

    attach_stream(provider, [
        FakeStream(["hel", "lo"], error_after=1),
        FakeStream(["hel", "lo"]),
    ])

    chunks = []

    with pytest.raises(APITimeoutError):
        for chunk in provider.stream_generate("system", [], "question"):
            chunks.append(chunk)

    assert chunks == ["hel"]
    assert len(provider.client.responses.requests) == 1
