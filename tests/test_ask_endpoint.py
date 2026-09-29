import json

import pytest

import ai_provider
import app as application
import usage_control


FACT_REGISTRY = {
    "block_height": {
        "key": "block_height",
        "label": "Block height",
        "meaning": "latest block height",
        "value": "123,456",
        "unit": "",
        "dynamic": True,
        "source": "Official EXIOM Explorer",
    },
    "active_nodes": {
        "key": "active_nodes",
        "label": "Active service nodes",
        "meaning": "count of active nodes",
        "value": "1,024",
        "unit": "",
        "dynamic": True,
        "source": "Official EXIOM Explorer",
    },
}


class FakeLiveData:

    def get_fact_registry(self):
        return dict(FACT_REGISTRY)

    def get_network_stats(self):
        return {
            "status": "available",
            "connection_state": "connected",
            "source": "Official EXIOM Explorer",
            "facts": dict(FACT_REGISTRY),
        }


NODE_KEY = "99efd7f74cc325ae6d2b62a08be9e932d960dfb53243f3f2d67595cb378747ba"


class FakeMarketData:
    """
    No tracker answers unless a test sets a quote.
    """

    def __init__(self):
        self.quote = None
        self.calls = 0

    def get_quote(self):
        self.calls += 1
        return self.quote


LIVE_QUOTE = {
    "source": "NonKYC",
    "page": "https://nonkyc.io/market/XEQM_USDT",
    "price_usd": 0.02215,
    "change_24h_percent": -8.21,
    "volume_24h_usd": 15252.5,
    "market_cap_usd": None,
    "updated_at": None,
}


class FakeLookups:
    """
    Stands in for Explorer lookups and records what was asked.
    """

    def __init__(self):
        self.calls = []
        self.value = "status active; registered at block 5,948"

    def lookup(self, ids):
        self.calls.append(list(ids))

        return {
            f"lookup_{kind}_{value}": {
                "key": f"lookup_{kind}_{value}",
                "label": f"Service node {value}",
                "value": self.value,
                "unit": "",
                "source": "Official EXIOM Explorer",
                "via": "api",
            }
            for kind, value in ids
        }


class FakeProvider:
    """
    Stands in for the AI provider and counts what it costs.
    """

    def __init__(self):
        self.route_calls = []
        self.generate_calls = []
        self.off_topic_calls = []

        self.route_result = {
            "scope": "relevant",
            "intent": "explanation",
            "facts": []
        }

        self.route_error = None
        self.generate_error = None

        # Raised part-way through a stream, after some text
        # has already reached the caller.
        self.stream_error_after = None

        self.last_usage = {"input_tokens": 100, "output_tokens": 20}

        # None answers "answer to <question>"; any string,
        # empty included, is the answer instead.
        self.answer_text = None

        # Answers for successive calls, used before answer_text.
        # A list entry is streamed as those chunks.
        self.answers = []

        # Pages the last call cited.
        self.last_sources = []

        self.web_search_enabled = True

    @property
    def calls(self):
        return (
            len(self.route_calls)
            + len(self.generate_calls)
            + len(self.off_topic_calls)
        )

    def route_question(self, question, conversation, fact_registry):
        self.route_calls.append(question)

        if self.route_error:
            raise self.route_error

        return dict(self.route_result)

    def generate(self, system_prompt, conversation, question,
                 web_search=False):
        self.generate_calls.append(
            {
                "system_prompt": system_prompt,
                "conversation": conversation,
                "question": question,
                "web_search": web_search,
            }
        )

        if self.generate_error:
            raise self.generate_error

        if self.answers:
            return {"answer": "".join(self.answers.pop(0))}

        if self.answer_text is not None:
            return {"answer": self.answer_text}

        return {"answer": f"answer to {question}"}

    def generate_off_topic(self, conversation, question):
        self.off_topic_calls.append(question)

        return {"answer": "banter"}

    def stream_generate(self, system_prompt, conversation, question,
                        web_search=False):
        self.generate_calls.append(
            {
                "system_prompt": system_prompt,
                "conversation": conversation,
                "question": question,
                "web_search": web_search,
            }
        )

        if self.generate_error:
            raise self.generate_error

        if self.answers:
            planned = self.answers.pop(0)
            chunks = [planned] if isinstance(planned, str) else planned

        else:
            chunks = (
                ["answer ", "to ", question]
                if self.answer_text is None
                else [self.answer_text] if self.answer_text else []
            )

        for index, chunk in enumerate(chunks):
            if self.stream_error_after == index:
                raise RuntimeError("stream broke")

            yield chunk

    def stream_generate_off_topic(self, conversation, question):
        self.off_topic_calls.append(question)

        for chunk in ["ban", "ter"]:
            yield chunk


@pytest.fixture
def provider(monkeypatch):
    fake = FakeProvider()

    monkeypatch.setattr(application, "ai_provider", fake)
    monkeypatch.setattr(application, "live_data", FakeLiveData())
    monkeypatch.setattr(application, "explorer_lookups", FakeLookups())
    monkeypatch.setattr(application, "market_data", FakeMarketData())
    monkeypatch.setattr(application, "cost_meter", usage_control.CostMeter())
    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController()
    )

    application.router_cache.clear()
    application.answer_cache.clear()

    return fake


@pytest.fixture
def client():
    application.app.config["TESTING"] = True

    return application.app.test_client()


def ask(client, question, conversation=None):
    return client.post(
        "/ask",
        json={
            "question": question,
            "conversation": conversation or []
        }
    )


def ask_stream(client, question, conversation=None):
    response = client.post(
        "/ask/stream",
        json={
            "question": question,
            "conversation": conversation or []
        }
    )

    # A real client reads the stream to the end. Metering and
    # answer reuse both happen after the last chunk, so an
    # unread body would skip them.
    response.get_data()

    return response


def frames(response):
    """
    Decode an SSE body into the objects it carried.
    """

    return [
        json.loads(line[len("data: "):])
        for line in response.get_data(as_text=True).splitlines()
        if line.startswith("data: ")
    ]


def streamed_answer(response):
    return "".join(
        frame["text"]
        for frame in frames(response)
        if frame["type"] == "delta"
    )


# ---------------------------------------------------------
# REQUEST VALIDATION
# ---------------------------------------------------------

def test_empty_question_is_rejected_before_any_cost(client, provider):
    response = ask(client, "   ")

    assert response.status_code == 400
    assert provider.calls == 0


def test_oversized_question_is_rejected_before_any_cost(client, provider):
    response = ask(client, "x" * 1001)

    assert response.status_code == 400
    assert provider.calls == 0


def test_unreadable_body_is_rejected(client, provider):
    response = client.post("/ask", data="not json")

    assert response.status_code == 400
    assert provider.calls == 0


# ---------------------------------------------------------
# FREE DETERMINISTIC RESPONSES
# ---------------------------------------------------------

def test_greeting_costs_nothing(client, provider):
    response = ask(client, "hello")

    assert response.status_code == 200
    assert response.json["route"] == "greeting"
    assert provider.calls == 0


def test_creator_question_costs_nothing_and_credits_xrypto(client, provider):
    response = ask(client, "who made you?")

    assert "Xrypto" in response.json["answer"]
    assert provider.calls == 0


def test_direct_fact_question_skips_both_ai_calls(client, provider):
    response = ask(client, "what is the current block height?")

    assert response.json["route"] == "live"
    assert "123,456" in response.json["answer"]
    assert provider.calls == 0


def test_concept_question_still_reaches_the_ai(client, provider):
    response = ask(client, "what is staking?")

    assert response.status_code == 200
    assert len(provider.route_calls) == 1
    assert len(provider.generate_calls) == 1


def test_free_responses_are_counted_as_free(client, provider):
    ask(client, "hello")

    snapshot = application.cost_meter.snapshot()

    assert snapshot["free_responses"] == 1
    assert snapshot["provider_calls"] == 0


# ---------------------------------------------------------
# PROMPT SHAPE
# ---------------------------------------------------------

def test_static_prompt_comes_first_so_it_can_be_cached(client, provider):
    ask(client, "what is staking?")

    system_prompt = provider.generate_calls[0]["system_prompt"]

    assert system_prompt.startswith(application.STATIC_SYSTEM_PROMPT)
    assert "THIS REQUEST" in system_prompt


def test_request_section_carries_the_routing_decision(client, provider):
    provider.route_result = {
        "scope": "relevant",
        "intent": "mixed",
        "facts": ["active_nodes"]
    }

    ask(client, "why does the active node count matter right now")

    system_prompt = provider.generate_calls[0]["system_prompt"]

    assert "SCOPE: relevant" in system_prompt
    assert "INTENT: mixed" in system_prompt
    assert "1,024" in system_prompt


def test_explorer_facts_are_slimmed_before_sending(client, provider):
    provider.route_result = {
        "scope": "relevant",
        "intent": "mixed",
        "facts": ["active_nodes"]
    }

    ask(client, "why does the active node count matter right now")

    system_prompt = provider.generate_calls[0]["system_prompt"]

    assert "meaning" not in system_prompt.split("THIS REQUEST")[1]
    assert "dynamic" not in system_prompt.split("THIS REQUEST")[1]


def test_conversation_is_trimmed_before_sending(client, provider):
    conversation = [
        {"role": "user", "content": "x" * 4000},
        {"role": "assistant", "content": "y" * 4000},
        {"role": "user", "content": "z" * 4000},
    ]

    ask(client, "what is staking?", conversation)

    sent = provider.generate_calls[0]["conversation"]

    assert sum(len(message["content"]) for message in sent) <= \
        application.MAX_CONVERSATION_CHARS + 10


# ---------------------------------------------------------
# SAFE REUSE
# ---------------------------------------------------------

def test_identical_stateless_question_is_answered_once(client, provider):
    first = ask(client, "what is staking?")
    second = ask(client, "what is staking?")

    assert first.json["answer"] == second.json["answer"]
    assert len(provider.route_calls) == 1
    assert len(provider.generate_calls) == 1


def test_reuse_is_reported_as_a_free_response(client, provider):
    ask(client, "what is staking?")
    ask(client, "what is staking?")

    assert application.cost_meter.snapshot()["free_responses"] == 1


def test_questions_inside_a_conversation_are_never_reused(client, provider):
    conversation = [{"role": "user", "content": "we were discussing nodes"}]

    ask(client, "what is staking?", conversation)
    ask(client, "what is staking?", conversation)

    assert len(provider.generate_calls) == 2
    assert len(provider.route_calls) == 2


def test_a_changed_explorer_value_is_never_served_from_cache(
    client,
    provider,
    monkeypatch
):
    provider.route_result = {
        "scope": "relevant",
        "intent": "mixed",
        "facts": ["block_height"]
    }

    ask(client, "why is the current block height interesting")

    class MovedOn(FakeLiveData):

        def get_fact_registry(self):
            registry = super().get_fact_registry()
            registry["block_height"] = {
                **registry["block_height"],
                "value": "999,999"
            }
            return registry

    monkeypatch.setattr(application, "live_data", MovedOn())

    ask(client, "why is the current block height interesting")

    assert len(provider.generate_calls) == 2


def test_off_topic_banter_is_never_reused(client, provider):
    provider.route_result = {
        "scope": "unrelated",
        "intent": "general",
        "facts": []
    }

    first = ask(client, "best chicken biryani recipe?")
    second = ask(client, "best chicken biryani recipe?")

    assert first.json["route"] == "off_topic"
    assert second.json["route"] == "off_topic"
    assert len(provider.off_topic_calls) == 2


def test_router_decision_is_reused_for_an_identical_question(
    client,
    provider
):
    provider.route_result = {
        "scope": "relevant",
        "intent": "direct_live_fact",
        "facts": ["active_nodes"]
    }

    ask(client, "give me the node number the explorer shows")
    ask(client, "give me the node number the explorer shows")

    assert len(provider.route_calls) == 1
    assert len(provider.generate_calls) == 1


# ---------------------------------------------------------
# USAGE CONTROL
# ---------------------------------------------------------

def test_paid_requests_are_paced(client, provider, monkeypatch):
    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(requests_per_minute=2)
    )

    for index in range(2):
        assert ask(client, f"what is staking {index}?").status_code == 200

    response = ask(client, "what is staking again?")

    assert response.status_code == 429
    assert response.json["error_type"] == "usage_limit"
    assert int(response.headers["Retry-After"]) > 0


def test_free_responses_never_consume_the_budget(
    client,
    provider,
    monkeypatch
):
    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(requests_per_minute=1)
    )

    for _ in range(5):
        assert ask(client, "hello").status_code == 200

    assert ask(client, "what is staking?").status_code == 200


def test_spent_tokens_are_charged_to_the_caller(client, provider):
    ask(client, "what is staking?")

    # Both the routing call and the answering call are charged.
    assert application.usage_controller.snapshot()[
        "global_tokens_today"
    ] == 240


# ---------------------------------------------------------
# FAILURE HANDLING
# ---------------------------------------------------------

def test_router_failure_still_produces_an_answer(client, provider):
    provider.route_error = RuntimeError("router exploded")

    response = ask(client, "what is staking?")

    assert response.status_code == 200
    assert len(provider.generate_calls) == 1


def test_a_failed_route_is_never_cached(client, provider):
    provider.route_error = RuntimeError("router exploded")

    ask(client, "what is staking?")

    provider.route_error = None

    ask(client, "what is staking?")

    assert len(provider.route_calls) == 2


def test_provider_failure_returns_a_friendly_error(client, provider):
    provider.generate_error = RuntimeError("boom")

    response = ask(client, "what is staking?")

    assert response.status_code == 500
    assert response.json["error_type"] == "unknown"


def test_a_failed_answer_is_never_cached(client, provider):
    provider.generate_error = RuntimeError("boom")

    ask(client, "what is staking?")

    provider.generate_error = None

    response = ask(client, "what is staking?")

    assert response.status_code == 200
    assert response.json["answer"] == "answer to what is staking?"


# ---------------------------------------------------------
# OBSERVABILITY
# ---------------------------------------------------------

def test_usage_endpoint_is_off_without_a_token(client, provider):
    assert client.get("/api/usage").status_code == 404


def test_usage_endpoint_rejects_a_wrong_token(client, provider, monkeypatch):
    monkeypatch.setattr(application, "USAGE_TOKEN", "secret")

    assert client.get("/api/usage").status_code == 401
    assert client.get(
        "/api/usage",
        headers={"X-Usage-Token": "guess"}
    ).status_code == 401


def test_usage_endpoint_reports_cost_and_caches(client, provider, monkeypatch):
    monkeypatch.setattr(application, "USAGE_TOKEN", "secret")

    ask(client, "hello")
    ask(client, "what is staking?")

    payload = client.get(
        "/api/usage",
        headers={"X-Usage-Token": "secret"}
    ).json

    assert payload["cost"]["free_responses"] == 1
    assert payload["cost"]["provider_calls"] == 0
    assert "router" in payload["caches"]
    assert payload["usage_control"]["limits"]["requests_per_minute"] > 0


# ---------------------------------------------------------
# CLIENT IDENTITY
# ---------------------------------------------------------

def test_a_forged_forwarded_header_cannot_dodge_the_limit(
    client,
    provider,
    monkeypatch
):
    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(requests_per_minute=1)
    )

    # With one proxy in front, the caller controls everything
    # except the last entry, which the proxy appends itself.
    assert client.post(
        "/ask",
        json={"question": "what is staking?"},
        headers={"X-Forwarded-For": "1.1.1.1, 9.9.9.9"}
    ).status_code == 200

    # A different forged prefix must not buy a fresh budget.
    assert client.post(
        "/ask",
        json={"question": "what is staking twice?"},
        headers={"X-Forwarded-For": "2.2.2.2, 9.9.9.9"}
    ).status_code == 429


def test_separate_clients_behind_the_proxy_are_independent(
    client,
    provider,
    monkeypatch
):
    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(requests_per_minute=1)
    )

    assert client.post(
        "/ask",
        json={"question": "what is staking?"},
        headers={"X-Forwarded-For": "9.9.9.9"}
    ).status_code == 200

    assert client.post(
        "/ask",
        json={"question": "what is staking too?"},
        headers={"X-Forwarded-For": "8.8.8.8"}
    ).status_code == 200


# ---------------------------------------------------------
# STREAMING TRANSPORT
# ---------------------------------------------------------

def test_streamed_answer_arrives_as_deltas(client, provider):
    response = ask_stream(client, "what is staking?")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    assert streamed_answer(response) == "answer to what is staking?"

    assert [frame["type"] for frame in frames(response)] == [
        "delta",
        "delta",
        "delta",
        "done",
    ]


def test_streamed_answer_matches_the_json_answer(client, provider):
    streamed = ask_stream(client, "what is staking?")

    application.router_cache.clear()
    application.answer_cache.clear()

    plain = ask(client, "what is staking?")

    assert streamed_answer(streamed) == plain.json["answer"]


def test_done_frame_carries_the_routing_decision(client, provider):
    response = ask_stream(client, "what is staking?")

    done = frames(response)[-1]

    assert done["route"] == "explanation"
    assert done["scope"] == "relevant"


def test_a_free_answer_is_sent_whole_rather_than_chunked(client, provider):
    response = ask_stream(client, "hello")

    assert response.status_code == 200
    assert provider.calls == 0

    assert [frame["type"] for frame in frames(response)] == ["message"]


def test_a_cached_answer_is_sent_whole_rather_than_chunked(client, provider):
    ask_stream(client, "what is staking?")

    response = ask_stream(client, "what is staking?")

    assert [frame["type"] for frame in frames(response)] == ["message"]
    assert frames(response)[0]["answer"] == "answer to what is staking?"

    # The second question never reached the provider.
    assert len(provider.generate_calls) == 1


def test_off_topic_banter_streams(client, provider):
    provider.route_result = {
        "scope": "unrelated",
        "intent": "general",
        "facts": []
    }

    response = ask_stream(client, "tell me a joke")

    assert streamed_answer(response) == "banter"


# ---------------------------------------------------------
# STREAMING COST AND REUSE
# ---------------------------------------------------------

def test_a_streamed_answer_is_cached_once_it_completes(client, provider):
    ask_stream(client, "what is staking?")

    cached = ask(client, "what is staking?")

    assert cached.json["answer"] == "answer to what is staking?"
    assert len(provider.generate_calls) == 1


def test_a_broken_stream_is_never_cached(client, provider):
    provider.stream_error_after = 1

    ask_stream(client, "what is staking?")

    provider.stream_error_after = None

    response = ask_stream(client, "what is staking?")

    assert streamed_answer(response) == "answer to what is staking?"


def test_streamed_tokens_are_charged_to_the_caller(client, provider):
    ask_stream(client, "what is staking?")

    # Both the routing call and the answering call are charged.
    assert application.usage_controller.snapshot()[
        "global_tokens_today"
    ] == 240


# ---------------------------------------------------------
# STREAMING FAILURE HANDLING
# ---------------------------------------------------------

def test_validation_is_refused_as_json_not_as_a_stream(client, provider):
    response = ask_stream(client, "")

    assert response.status_code == 400
    assert response.mimetype == "application/json"
    assert response.json["error_type"] == "empty_question"


def test_usage_limit_is_refused_before_the_stream_opens(
    client,
    provider,
    monkeypatch
):
    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(requests_per_minute=1)
    )

    assert ask_stream(client, "what is staking?").status_code == 200

    response = ask_stream(client, "what is proof of stake?")

    assert response.status_code == 429
    assert response.mimetype == "application/json"
    assert response.json["error_type"] == "usage_limit"
    assert int(response.headers["Retry-After"]) > 0


def test_a_failure_before_the_first_token_keeps_its_status_code(
    client,
    provider
):
    provider.generate_error = RuntimeError("boom")

    response = ask_stream(client, "what is staking?")

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    assert response.json["error_type"] == "unknown"


def test_a_failure_after_the_first_token_arrives_in_band(client, provider):
    provider.stream_error_after = 1

    response = ask_stream(client, "what is staking?")

    # The 200 was already committed when the break happened.
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    sent = frames(response)

    assert streamed_answer(response) == "answer "
    assert sent[-1]["type"] == "error"
    assert sent[-1]["answer"]


# ---------------------------------------------------------
# EXPLORER LOOKUPS
# ---------------------------------------------------------

def test_a_named_node_is_looked_up_and_given_to_the_model(
    client, provider
):
    ask(client, f"is node {NODE_KEY} healthy?")

    assert application.explorer_lookups.calls == [[("hex", NODE_KEY)]]

    request_section = (
        provider.generate_calls[0]["system_prompt"]
        .split("THIS REQUEST")[1]
    )

    assert "registered at block 5,948" in request_section
    assert "via" not in request_section


def test_a_question_naming_a_block_skips_the_fast_path(client, provider):
    """
    "block height" would otherwise be answered with the
    current chain height, not the named block.
    """

    response = ask(client, "what is the block height of block 203140")

    assert application.explorer_lookups.calls == [[("height", "203140")]]
    assert len(provider.generate_calls) == 1
    assert response.json["route"] != "live"


def test_a_direct_fact_route_still_answers_the_named_id(client, provider):
    provider.route_result = {
        "scope": "relevant",
        "intent": "direct_live_fact",
        "facts": ["block_height"]
    }

    ask(client, "block 203140?")

    assert len(provider.generate_calls) == 1


def test_a_named_id_is_never_off_topic(client, provider):
    provider.route_result = {
        "scope": "unrelated",
        "intent": "general",
        "facts": []
    }

    ask(client, f"{NODE_KEY}")

    assert provider.off_topic_calls == []
    assert len(provider.generate_calls) == 1


def test_lookups_are_paid_work(client, provider, monkeypatch):
    """
    A refused caller must not be able to make the server
    fetch Explorer pages for free.
    """

    class Refused:
        def check(self, client_id):
            return usage_control.UsageDecision(
                False, "client_daily_tokens", retry_after=60
            )

    monkeypatch.setattr(application, "usage_controller", Refused())

    ask(client, f"is node {NODE_KEY} healthy?")

    assert application.explorer_lookups.calls == []


def test_a_changed_lookup_value_is_never_served_from_cache(
    client, provider
):
    question = f"is node {NODE_KEY} healthy?"

    ask(client, question)
    application.explorer_lookups.value = "status decommissioned"
    ask(client, question)

    assert len(provider.generate_calls) == 2


def test_questions_without_ids_do_no_lookup(client, provider):
    ask(client, "what is staking?")

    assert application.explorer_lookups.calls == []


def test_a_broken_lookup_still_answers(client, provider):
    class Broken(FakeLookups):
        def lookup(self, ids):
            raise RuntimeError("parser bug")

    application.explorer_lookups = Broken()

    response = ask(client, f"is node {NODE_KEY} healthy?")

    assert response.status_code == 200
    assert len(provider.generate_calls) == 1



# ---------------------------------------------------------
# WEB SEARCH
# ---------------------------------------------------------

SEARCH_ROUTE = {
    "scope": "relevant",
    "intent": "general",
    "facts": [],
    "search": True
}


@pytest.mark.parametrize("send", [ask, ask_stream])
def test_a_flagged_question_is_answered_with_a_search(client, provider, send):
    provider.route_result = dict(SEARCH_ROUTE)

    assert send(client, "exiom coin price").status_code == 200

    [call] = provider.generate_calls

    assert call["web_search"] is True
    assert "WEB SEARCH: ON" in call["system_prompt"]


@pytest.mark.parametrize("send", [ask, ask_stream])
def test_an_unflagged_question_never_searches(client, provider, send):
    send(client, "what is staking?")

    [call] = provider.generate_calls

    assert call["web_search"] is False
    assert "WEB SEARCH" not in call["system_prompt"].split("THIS REQUEST")[1]


def test_searched_answers_are_never_reused(client, provider):
    provider.route_result = dict(SEARCH_ROUTE)

    ask(client, "exiom coin price")
    ask(client, "exiom coin price")

    assert len(provider.generate_calls) == 2


def test_past_the_search_allowance_the_answer_says_it_cannot_check(
    client,
    provider,
    monkeypatch
):
    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(client_web_searches_per_day=0)
    )
    provider.route_result = dict(SEARCH_ROUTE)

    assert ask(client, "exiom coin price").status_code == 200

    [call] = provider.generate_calls

    assert call["web_search"] is False
    assert "WEB SEARCH: UNAVAILABLE" in call["system_prompt"]


def test_search_off_in_the_provider_is_not_claimed(client, provider, monkeypatch):
    provider.web_search_enabled = False
    provider.route_result = dict(SEARCH_ROUTE)

    ask(client, "exiom coin price")

    [call] = provider.generate_calls

    assert call["web_search"] is False
    assert "WEB SEARCH: UNAVAILABLE" in call["system_prompt"]
    assert application.usage_controller.snapshot()[
        "global_web_searches_today"
    ] == 0


# ---------------------------------------------------------
# EMPTY ANSWERS
# ---------------------------------------------------------

def test_an_empty_answer_is_never_sent_blank(client, provider):
    provider.answer_text = "   "

    response = ask(client, "what is staking?")

    assert response.status_code == 200
    assert response.json["answer"] == application.EMPTY_ANSWER


def test_an_empty_stream_is_never_left_blank(client, provider):
    provider.answer_text = ""

    response = ask_stream(client, "what is staking?")

    assert streamed_answer(response) == application.EMPTY_ANSWER
    assert frames(response)[-1]["type"] == "done"


def test_an_empty_answer_is_not_reused(client, provider):
    provider.answer_text = ""

    ask(client, "what is staking?")
    ask(client, "what is staking?")

    assert len(provider.generate_calls) == 2


# ---------------------------------------------------------
# USAGE PAGE
# ---------------------------------------------------------

def test_usage_endpoint_reports_the_daily_ledger(
    client,
    provider,
    monkeypatch,
    tmp_path
):
    from usage_ledger import UsageLedger

    ledger = UsageLedger(str(tmp_path / "usage.sqlite3"))
    ledger.record("answer", calls=2, web_searches=1, cost_usd=0.02)

    monkeypatch.setattr(application, "usage_ledger", ledger)
    monkeypatch.setattr(application, "USAGE_TOKEN", "secret")

    payload = client.get(
        "/api/usage",
        headers={"X-Usage-Token": "secret"}
    ).json

    assert payload["ledger"] == "available"
    assert payload["web_search"] == "on"
    assert payload["daily"][0]["provider_calls"] == 2
    assert payload["daily"][0]["web_searches"] == 1
    assert "web_searches" in payload["cost"]


def test_usage_page_is_an_empty_shell(client, provider, monkeypatch):
    monkeypatch.setattr(application, "USAGE_TOKEN", "secret")

    response = client.get("/usage")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "X-Usage-Token" in page
    assert "secret" not in page
    assert response.headers["Cache-Control"] == "no-store"
    assert "noindex" in response.headers.get("X-Robots-Tag", "")


def test_usage_page_is_off_without_a_token(client, provider):
    assert client.get("/usage").status_code == 404


@pytest.mark.parametrize("send", [ask, ask_stream])
def test_a_price_question_searches_even_if_the_router_forgets(
    client,
    provider,
    send
):
    provider.route_result = {
        "scope": "relevant", "intent": "mixed", "facts": [], "search": False
    }

    send(client, "Exiom Coin Price")

    assert provider.generate_calls[0]["web_search"] is True


def test_a_concept_question_about_price_does_not_search(client, provider):
    provider.route_result = {
        "scope": "relevant", "intent": "explanation", "facts": [],
        "search": False
    }

    ask(client, "what does market cap mean?")

    assert provider.generate_calls[0]["web_search"] is False


def test_an_unrelated_price_question_does_not_search(client, provider):
    provider.route_result = {
        "scope": "unrelated", "intent": "general", "facts": [],
        "search": False
    }

    ask(client, "price of eggs")

    assert provider.generate_calls == []


# ---------------------------------------------------------
# LIVE DATA FIRST, THEN A SEARCH, THEN A GENTLE "NOT FOUND"
# ---------------------------------------------------------

EXPLORER_ROUTE = {
    "scope": "relevant",
    "intent": "mixed",
    "facts": ["active_nodes"],
    "search": False
}

CONCEPT_ROUTE = {
    "scope": "relevant",
    "intent": "explanation",
    "facts": [],
    "search": False
}


def request_section(call):
    return call["system_prompt"].split("THIS REQUEST")[1]


def test_a_router_picked_fact_is_worded_by_the_model(client, provider):
    """
    The router's pick once became a canned reply, and a wrong
    pick ("blocks in the last hour" -> the 24-hour count)
    went straight to the user.
    """

    provider.route_result = {
        "scope": "relevant",
        "intent": "direct_live_fact",
        "facts": ["active_nodes"]
    }

    response = ask(client, "how many nodes r running rn")

    assert len(provider.generate_calls) == 1
    assert response.json["answer"] == "answer to how many nodes r running rn"


def test_an_explorer_question_sees_every_explorer_value(client, provider):
    provider.route_result = dict(EXPLORER_ROUTE)

    ask(client, "how many nodes are in canada")

    section = request_section(provider.generate_calls[0])

    # Not only the fact the router picked.
    assert "Active service nodes: 1,024" in section
    assert "Block height: 123,456" in section


def test_a_concept_question_gets_no_explorer_values(client, provider):
    provider.route_result = dict(CONCEPT_ROUTE)

    ask(client, "what is staking?")

    section = request_section(provider.generate_calls[0])

    assert "123,456" not in section
    assert application.LOOKUP_SIGNAL in section


@pytest.mark.parametrize("send, reply", [
    (ask, lambda r: r.json["answer"]),
    (ask_stream, streamed_answer),
])
def test_a_lookup_signal_brings_in_the_explorer_values(
    client, provider, send, reply
):
    provider.route_result = dict(CONCEPT_ROUTE)
    provider.answers = [["[[LOO", "KUP]]"], "There are 49 nodes in Canada."]

    response = send(client, "nodes joining lately?")

    first, second = provider.generate_calls

    assert "123,456" not in request_section(first)
    assert "Block height: 123,456" in request_section(second)
    assert second["web_search"] is False
    assert reply(response) == "There are 49 nodes in Canada."


@pytest.mark.parametrize("send", [ask, ask_stream])
def test_a_lookup_signal_with_the_explorer_values_brings_a_web_search(
    client, provider, send
):
    provider.route_result = dict(EXPLORER_ROUTE)
    provider.answers = ["[[LOOKUP]]", "Found it."]

    send(client, "who is the ceo of xeqmlabs")

    first, second = provider.generate_calls

    assert first["web_search"] is False
    assert second["web_search"] == ai_provider.OPEN_WEB
    assert "WEB SEARCH: ON" in second["system_prompt"]
    assert "Block height: 123,456" in request_section(second)


def test_a_concept_route_can_climb_all_the_way_to_a_search(client, provider):
    provider.route_result = dict(CONCEPT_ROUTE)
    provider.answers = ["[[LOOKUP]]", "[[LOOKUP]]", "Found it."]

    response = ask(client, "who founded xeqmlabs")

    assert [c["web_search"] for c in provider.generate_calls] == [
        False, False, ai_provider.OPEN_WEB
    ]
    assert response.json["answer"] == "Found it."


def test_a_market_question_searches_the_listed_sites_first_time(
    client, provider
):
    provider.route_result = dict(SEARCH_ROUTE)

    ask(client, "exiom coin price")

    [call] = provider.generate_calls

    assert call["web_search"] is True
    assert application.LOOKUP_SIGNAL not in request_section(call)


@pytest.mark.parametrize("send, reply", [
    (ask, lambda r: r.json["answer"]),
    (ask_stream, streamed_answer),
])
def test_a_signal_on_the_last_step_becomes_a_gentle_not_found(
    client, provider, send, reply
):
    provider.route_result = dict(SEARCH_ROUTE)
    provider.answers = ["[[LOOKUP]]"]

    response = send(client, "how many wallets hold xeqm")

    assert len(provider.generate_calls) == 1
    assert reply(response) == application.NOT_FOUND_ANSWER
    assert "explorer.xeqmlabs.com" in application.NOT_FOUND_ANSWER


def test_without_a_search_allowance_a_backup_ends_free_and_gently(
    client, provider, monkeypatch
):
    monkeypatch.setattr(
        application,
        "usage_controller",
        usage_control.UsageController(client_web_searches_per_day=0)
    )
    provider.route_result = dict(EXPLORER_ROUTE)
    provider.answers = ["[[LOOKUP]]"]

    response = ask(client, "who is the ceo of xeqmlabs")

    assert len(provider.generate_calls) == 1
    assert response.json["answer"] == application.NOT_FOUND_ANSWER


def test_with_search_off_the_explorer_step_is_the_last(client, provider):
    provider.web_search_enabled = False
    provider.route_result = dict(EXPLORER_ROUTE)

    ask(client, "how many nodes in canada")

    [call] = provider.generate_calls

    assert application.LOOKUP_SIGNAL not in request_section(call)


def test_answers_that_needed_a_second_step_are_not_reused(client, provider):
    provider.route_result = dict(CONCEPT_ROUTE)
    provider.answers = ["[[LOOKUP]]", "49", "[[LOOKUP]]", "50"]

    ask(client, "nodes of canada")
    response = ask(client, "nodes of canada")

    assert len(provider.generate_calls) == 4
    assert response.json["answer"] == "50"


def test_an_answer_that_merely_starts_with_brackets_is_kept(client, provider):
    provider.route_result = dict(CONCEPT_ROUTE)
    provider.answers = [["[", "[not a signal] staking locks XEQM"]]

    response = ask_stream(client, "what is staking?")

    assert len(provider.generate_calls) == 1
    assert streamed_answer(response) == "[[not a signal] staking locks XEQM"


# ---------------------------------------------------------
# SOURCES ARE ALWAYS LINKS
# ---------------------------------------------------------

def test_an_unlinked_explorer_mention_gets_the_linked_source(client, provider):
    provider.route_result = dict(EXPLORER_ROUTE)
    provider.answer_text = "1,024 nodes. Source: Official EXIOM Explorer."

    response = ask(client, "how many nodes are running right now or so")

    assert response.json["source"] == "Official EXIOM Explorer"


def test_a_streamed_unlinked_explorer_mention_gets_the_linked_source(
    client, provider
):
    provider.route_result = dict(EXPLORER_ROUTE)
    provider.answer_text = "1,024 nodes. Source: Official EXIOM Explorer."

    response = ask_stream(client, "how many nodes are running right now or so")

    [done] = [f for f in frames(response) if f["type"] == "done"]

    assert done["source"] == "Official EXIOM Explorer"


def test_a_linked_explorer_mention_gets_no_second_source(client, provider):
    provider.route_result = dict(EXPLORER_ROUTE)
    provider.answer_text = (
        "1,024 nodes. Source: "
        "[Official EXIOM Explorer](https://explorer.xeqmlabs.com/)"
    )

    response = ask(client, "how many nodes are running right now or so")

    assert "source" not in response.json


@pytest.mark.parametrize("send, reply", [
    (ask, lambda r: r.json["answer"]),
    (ask_stream, streamed_answer),
])
def test_a_searched_answer_without_links_gets_its_sources(
    client, provider, send, reply
):
    provider.route_result = dict(SEARCH_ROUTE)
    provider.answer_text = "XEQM is about $0.02."
    provider.last_sources = [
        "https://www.coingecko.com/en/coins/xeqm-labs?utm_source=openai",
        "https://nonkyc.io/market/XEQM_USDT",
    ]

    text = reply(send(client, "exiom coin price"))

    assert text.startswith("XEQM is about $0.02.")
    assert (
        "[coingecko.com](https://www.coingecko.com/en/coins/xeqm-labs"
        "?utm_source=openai)" in text
    )
    assert "[nonkyc.io](https://nonkyc.io/market/XEQM_USDT)" in text


def test_a_searched_answer_with_links_is_left_alone(client, provider):
    provider.route_result = dict(SEARCH_ROUTE)
    provider.answer_text = "About $0.02 ([coingecko.com](https://coingecko.com/x))."
    provider.last_sources = ["https://coingecko.com/x"]

    response = ask(client, "exiom coin price")

    # No sources line; only the searched price's warning.
    assert response.json["answer"] == (
        provider.answer_text + application.STALE_PRICE_NOTE
    )


# ---------------------------------------------------------
# PROMPT RULES THE CLIENT ASKED FOR
# ---------------------------------------------------------

def test_the_prompt_asks_for_plain_words_and_linked_sources(client, provider):
    prompt = application.STATIC_SYSTEM_PROMPT

    assert "[Official EXIOM Explorer](https://explorer.xeqmlabs.com/)" in prompt
    assert "PLAIN" in prompt


def test_a_question_naming_xeqm_is_never_off_topic(client, provider):
    provider.route_result = {
        "scope": "unrelated", "intent": "general", "facts": [],
        "search": False
    }

    ask(client, "What is the all-time high price of XEQM?")

    assert provider.off_topic_calls == []
    [call] = provider.generate_calls
    assert call["web_search"] is True


def test_a_value_question_starts_with_the_explorer_values(client, provider):
    """
    The router called "weather in paris and how many nodes are
    there" general, and the node count was never looked at.
    """

    provider.route_result = {
        "scope": "relevant", "intent": "general", "facts": [],
        "search": False
    }

    ask(client, "what's the weather in paris and how many nodes are there")

    [call] = provider.generate_calls
    assert "Active service nodes: 1,024" in request_section(call)


def test_an_off_topic_route_naming_nodes_is_treated_as_mixed(client, provider):
    provider.route_result = {
        "scope": "unrelated", "intent": "general", "facts": [],
        "search": False
    }

    ask(client, "what's the weather in paris and how many nodes are there")

    assert provider.off_topic_calls == []
    [call] = provider.generate_calls
    assert "SCOPE: mixed" in call["system_prompt"]


def test_a_truly_off_topic_question_stays_off_topic(client, provider):
    provider.route_result = {
        "scope": "unrelated", "intent": "general", "facts": [],
        "search": False
    }

    ask(client, "how many calories are in rice")

    assert provider.generate_calls == []
    assert len(provider.off_topic_calls) == 1


@pytest.mark.parametrize("send, reply", [
    (ask, lambda r: r.json["answer"]),
    (ask_stream, streamed_answer),
])
def test_a_closing_offer_is_dropped(client, provider, send, reply):
    provider.route_result = dict(EXPLORER_ROUTE)
    provider.answer_text = (
        "1,024 nodes.\n\nIf you'd like, I can pull the block list."
    )

    assert reply(send(client, "how many nodes, and why")) == "1,024 nodes."


def test_explorer_figures_without_naming_it_still_get_the_source(
    client, provider
):
    provider.route_result = dict(EXPLORER_ROUTE)
    provider.answer_text = "Canada has 49 nodes."

    response = ask(client, "nodes of canada")

    assert response.json["source"] == "Official EXIOM Explorer"


def test_an_explorer_link_does_not_hide_the_web_sources(client, provider):
    provider.route_result = dict(SEARCH_ROUTE)
    provider.answer_text = (
        "About $0.02. Source: "
        "[Official EXIOM Explorer](https://explorer.xeqmlabs.com/)"
    )
    provider.last_sources = ["https://coingecko.com/x"]

    response = ask(client, "exiom coin price")

    assert "[coingecko.com](https://coingecko.com/x)" in response.json["answer"]


def test_a_backticked_signal_still_looks_further(client, provider):
    provider.route_result = dict(CONCEPT_ROUTE)
    provider.answers = [["`[[LOO", "KUP]]`"], "Found."]

    response = ask_stream(client, "nodes joining lately?")

    assert len(provider.generate_calls) == 2
    assert streamed_answer(response) == "Found."


def test_a_stray_signal_mid_answer_is_removed(client, provider):
    provider.route_result = dict(EXPLORER_ROUTE)
    provider.answer_text = "Canada has 49 nodes. [[LOOKUP]]"

    response = ask(client, "nodes of canada")

    assert "[[LOOKUP]]" not in response.json["answer"]


def test_an_answer_written_without_search_is_not_reused_once_it_returns(
    client, provider
):
    provider.web_search_enabled = False
    provider.route_result = dict(EXPLORER_ROUTE)

    ask(client, "nodes of canada please")

    provider.web_search_enabled = True
    ask(client, "nodes of canada please")

    assert len(provider.generate_calls) == 2


# ---------------------------------------------------------
# LIVE MARKET DATA
# ---------------------------------------------------------
#
# A search reads the index's copy of a tracker's page, which
# gave everyone the same stale price and 24h change. The
# price is read from the tracker's API instead.
# ---------------------------------------------------------

@pytest.mark.parametrize("send", [ask, ask_stream])
def test_a_price_question_is_answered_from_live_market_data(
    client, provider, send
):
    provider.route_result = dict(SEARCH_ROUTE)
    application.market_data.quote = dict(LIVE_QUOTE)

    assert send(client, "What is the price of xeqm").status_code == 200

    [call] = provider.generate_calls
    prompt = call["system_prompt"]

    assert call["web_search"] is False
    assert "MARKET DATA (live" in prompt
    assert "- Price: $0.02215 (USD)" in prompt
    assert "- 24h change: -8.2% (down over the last 24 hours)" in prompt
    assert "WEB SEARCH: NOT NEEDED" in prompt


def test_a_live_price_spends_no_search_allowance(client, provider):
    provider.route_result = dict(SEARCH_ROUTE)
    application.market_data.quote = dict(LIVE_QUOTE)
    application.usage_controller = usage_control.UsageController(
        client_web_searches_per_day=0
    )

    ask(client, "What is the price of xeqm")

    [call] = provider.generate_calls

    assert "WEB SEARCH: UNAVAILABLE" not in call["system_prompt"]
    assert "MARKET DATA (live" in call["system_prompt"]


def test_a_price_question_is_never_answered_from_the_answer_cache(
    client, provider
):
    provider.route_result = dict(SEARCH_ROUTE)
    application.market_data.quote = dict(LIVE_QUOTE)

    ask(client, "What is the price of xeqm")
    application.market_data.quote = {**LIVE_QUOTE, "price_usd": 0.019}
    ask(client, "What is the price of xeqm")

    assert len(provider.generate_calls) == 2
    assert "- Price: $0.01900 (USD)" in provider.generate_calls[1]["system_prompt"]


def test_price_with_listings_still_searches_and_carries_the_live_price(
    client, provider
):
    provider.route_result = dict(SEARCH_ROUTE)
    application.market_data.quote = dict(LIVE_QUOTE)

    ask(client, "What is the xeqm price and where can I buy it?")

    [call] = provider.generate_calls

    assert call["web_search"] is True
    assert "MARKET DATA (live" in call["system_prompt"]
    assert "WEB SEARCH: ON" in call["system_prompt"]


def test_without_live_market_data_a_price_question_searches(client, provider):
    provider.route_result = dict(SEARCH_ROUTE)

    ask(client, "What is the price of xeqm")

    [call] = provider.generate_calls

    assert call["web_search"] is True
    assert "MARKET DATA" not in call["system_prompt"]


def test_a_movement_question_gets_the_live_price(client, provider):
    provider.route_result = {
        "scope": "relevant", "intent": "general", "facts": [], "search": False
    }
    application.market_data.quote = dict(LIVE_QUOTE)

    ask(client, "is xeqm up today?")

    [call] = provider.generate_calls

    assert call["web_search"] is False
    assert "- 24h change: -8.2%" in call["system_prompt"]


def test_questions_that_never_search_never_read_the_market(client, provider):
    ask(client, "what is staking?")

    assert application.market_data.calls == 0


# The last resort and the search: the answer says the price
# may be out of date, added by the code, not the model.

SENDERS = [
    (ask, lambda response: response.json["answer"]),
    (ask_stream, streamed_answer),
]


@pytest.mark.parametrize("send, reply", SENDERS)
def test_a_live_price_carries_no_warning(client, provider, send, reply):
    provider.route_result = dict(SEARCH_ROUTE)
    application.market_data.quote = dict(LIVE_QUOTE)

    text = reply(send(client, "What is the price of xeqm"))

    assert "may be out of date" not in text


@pytest.mark.parametrize("send, reply", SENDERS)
def test_a_coingecko_price_says_it_may_be_out_of_date(client, provider, send, reply):
    provider.route_result = dict(SEARCH_ROUTE)
    application.market_data.quote = {
        **LIVE_QUOTE,
        "source": "CoinGecko",
        "page": "https://www.coingecko.com/en/coins/xeqm-labs",
        "last_resort": True,
    }

    text = reply(send(client, "What is the price of xeqm"))

    assert text.endswith(application.STALE_PRICE_NOTE)
    assert provider.generate_calls[0]["web_search"] is False
    assert "Backup source" in provider.generate_calls[0]["system_prompt"]


@pytest.mark.parametrize("send, reply", SENDERS)
def test_a_searched_price_says_it_may_be_out_of_date(client, provider, send, reply):
    provider.route_result = dict(SEARCH_ROUTE)

    text = reply(send(client, "What is the price of xeqm"))

    assert provider.generate_calls[0]["web_search"] is True
    assert text.endswith(application.STALE_PRICE_NOTE)


def test_a_searched_non_price_answer_has_no_price_warning(client, provider):
    provider.route_result = dict(SEARCH_ROUTE)

    text = ask(client, "What is the latest xeqm release?").json["answer"]

    assert "may be out of date" not in text
