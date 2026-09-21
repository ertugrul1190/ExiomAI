import pytest

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

        self.last_usage = {"input_tokens": 100, "output_tokens": 20}

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

    def generate(self, system_prompt, conversation, question):
        self.generate_calls.append(
            {
                "system_prompt": system_prompt,
                "conversation": conversation,
                "question": question,
            }
        )

        if self.generate_error:
            raise self.generate_error

        return {"answer": f"answer to {question}"}

    def generate_off_topic(self, conversation, question):
        self.off_topic_calls.append(question)

        return {"answer": "banter"}


@pytest.fixture
def provider(monkeypatch):
    fake = FakeProvider()

    monkeypatch.setattr(application, "ai_provider", fake)
    monkeypatch.setattr(application, "live_data", FakeLiveData())
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
    assert len(provider.generate_calls) == 0


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
