import json

import pytest

import query_router
from query_router import build_router_prompt, parse_router_result


REGISTRY = {
    "active_nodes": {
        "label": "Active service nodes",
        "meaning": "count of active nodes",
        "value": "1,024",
        "unit": ""
    },
    "block_height": {
        "label": "Block height",
        "meaning": "latest block height",
        "value": "123,456",
        "unit": ""
    },
}


def test_catalogue_lists_every_fact_key():
    catalogue = query_router.build_fact_catalogue(REGISTRY)

    assert "active_nodes" in catalogue
    assert "block_height" in catalogue


def test_catalogue_never_leaks_changing_values():
    """
    Values would change this prompt every 30 seconds and
    destroy prompt caching, for no routing benefit.
    """

    catalogue = query_router.build_fact_catalogue(REGISTRY)

    assert "1,024" not in catalogue
    assert "123,456" not in catalogue


def test_catalogue_handles_an_unavailable_explorer():
    assert query_router.build_fact_catalogue({}) == "(none available)"
    assert query_router.build_fact_catalogue(None) == "(none available)"


def test_prompt_is_identical_while_the_same_facts_exist():
    changed_values = {
        key: {**fact, "value": "999"}
        for key, fact in REGISTRY.items()
    }

    assert query_router.build_router_prompt(REGISTRY) == \
        query_router.build_router_prompt(changed_values)


def test_prompt_does_not_embed_the_question():
    prompt = query_router.build_router_prompt(REGISTRY)

    assert "USER MESSAGE" not in prompt


def test_prompt_keeps_the_critical_routing_rules():
    prompt = query_router.build_router_prompt(REGISTRY)

    assert "direct_live_fact" in prompt
    assert '"What is staking?" does NOT request staking_requirement.' \
        in prompt
    assert "RELEVANT" in prompt
    assert "Never invent a fact key." in prompt
    assert "JSON" in prompt


def test_valid_result_is_passed_through():
    result = query_router.parse_router_result(
        json.dumps({
            "scope": "mixed",
            "intent": "explanation",
            "facts": ["active_nodes"]
        }),
        REGISTRY
    )

    assert result == {
        "scope": "mixed",
        "intent": "explanation",
        "facts": ["active_nodes"],
        "search": False
    }


def test_invalid_json_falls_back_to_a_safe_route():
    assert query_router.parse_router_result("not json", REGISTRY) == {
        "scope": "relevant",
        "intent": "general",
        "facts": [],
        "search": False
    }


def test_empty_output_falls_back_to_a_safe_route():
    assert query_router.parse_router_result("", REGISTRY)["scope"] == \
        "relevant"


def test_invented_fact_keys_are_dropped():
    result = query_router.parse_router_result(
        '{"scope":"relevant","intent":"direct_live_fact",'
        '"facts":["active_nodes","made_up"]}',
        REGISTRY
    )

    assert result["facts"] == ["active_nodes"]


def test_unknown_scope_and_intent_are_replaced():
    result = query_router.parse_router_result(
        '{"scope":"weird","intent":"weird","facts":"nope"}',
        REGISTRY
    )

    assert result == {
        "scope": "relevant",
        "intent": "general",
        "facts": [],
        "search": False
    }


# ---------------------------------------------------------
# WEB SEARCH FLAG
# ---------------------------------------------------------

def test_search_flag_is_read():
    result = parse_router_result(
        '{"scope":"relevant","intent":"general","facts":[],"search":true}',
        {}
    )

    assert result["search"] is True


@pytest.mark.parametrize("raw", [
    '{"scope":"relevant","intent":"general","facts":[]}',
    '{"scope":"relevant","intent":"general","facts":[],"search":"true"}',
    '{"scope":"relevant","intent":"general","facts":[],"search":1}',
    '{"scope":"relevant","intent":"general","facts":[],"search":null}',
    'not json',
    '[]',
])
def test_search_is_off_unless_the_router_says_true(raw):
    assert parse_router_result(raw, {})["search"] is False


def test_an_unrelated_question_never_searches():
    result = parse_router_result(
        '{"scope":"unrelated","intent":"general","facts":[],"search":true}',
        {}
    )

    assert result["search"] is False


def test_router_prompt_asks_for_the_search_flag():
    prompt = build_router_prompt({})

    assert '"search":<true|false>' in prompt
    assert "price" in prompt.lower()


# ---------------------------------------------------------
# MARKET QUESTION BACKSTOP
# ---------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Exiom Coin Price",
    "xeqm price?",
    "what's XEQM's market cap",
    "marketcap of exiom",
    "How much is XEQM worth?",
    "how much is exiom",
    "Where can I buy XEQM right now?",
    "where to trade xeqm",
    "which exchanges list XEQM",
    "is xeqm listed on mexc",
    "what's the latest XEQM release?",
    "any exiom news",
    "24h volume xeqm",
])
def test_market_questions_are_recognised(question):
    assert query_router.asks_for_current_market_info(question)


@pytest.mark.parametrize("question", [
    "what is staking?",
    "how many active nodes are there?",
    "what is the current block height?",
    "explain the RFQ platform",
    "who made you?",
    "what is the staking requirement",
])
def test_other_questions_are_not(question):
    assert not query_router.asks_for_current_market_info(question)


# Operator questions that name neither EXIOM nor XEQM (the
# router sent "What is Pulse-recovery?" off-topic).
@pytest.mark.parametrize("question", [
    "What is Pulse-recovery and when does it activate?",
    "my uptime proof is 40 minutes old",
    "why was I decommissioned",
    "how long after deregistration can I withdraw",
    "how do I generate the registration command",
    "what is the max operator fee",
    "how do I unstake",
    "the GUI wallet won't open",
    "how do I start wallet rpc",
    "what is the oracle sidecar",
    "is lokinet live",
    "how do I stake into a pool node",
])
def test_operator_terms_count_as_exiom_topics(question):
    assert query_router.names_exiom_topic(question)


@pytest.mark.parametrize("question", [
    "how many calories are in rice",
    "write me a poem about the sea",
    "what's the weather in paris",
    "best pizza in rome",
    "what port does postgres use",
    "how do I write an oracle sql join",
    "what's at stake in the election",
    "renew my car registration",
    "why do eyes blink",
    "what is the aws uptime sla",
])
def test_everyday_questions_are_not_exiom_topics(question):
    assert not query_router.names_exiom_topic(question)


# ---------------------------------------------------------
# ANSWER QUALITY (Task Docs/Answer Quality and Image Upload)
# ---------------------------------------------------------

def test_the_output_example_names_no_real_intent():
    # At minimal reasoning the router echoed the example: every
    # question came back as "explanation".
    prompt = build_router_prompt(REGISTRY)
    output = prompt.split("OUTPUT")[1]
    example = next(
        line for line in output.splitlines() if line.startswith("{")
    )

    for intent in ("direct_live_fact", "explanation", "general", "mixed"):
        assert f'"{intent}"' not in example


def test_the_prompt_works_through_price_tracker_and_can_i_questions():
    prompt = " ".join(build_router_prompt(REGISTRY).split())

    assert '"whats the coin price" → scope relevant, intent general, search true' in prompt
    assert '"what does nonkyc and coinpaprika say" → scope relevant' in prompt
    assert '"can I stake 60k?" → intent general, search false' in prompt


@pytest.mark.parametrize("question", [
    "what does market cap mean?",
    "Meaning of trading volume",
    "define market cap",
    "explain the 24h volume",
    "how is the market cap calculated",
    "what is a market cap",
    "what is market cap",
])
def test_concept_questions_are_recognised(question):
    assert query_router.asks_what_it_means(question)


@pytest.mark.parametrize("question", [
    "whats the coin price",
    "what is the market cap",
    "whats xeqm market cap",
    "what does nonkyc and coinpaprika say",
    "price?",
])
def test_value_questions_are_not_concept_questions(question):
    assert not query_router.asks_what_it_means(question)


@pytest.mark.parametrize("question", [
    "whats the coin price",
    "what does nonkyc and coinpaprika say",
    "coingecko?",
    "what does CMC show",
    "check coinmarketcap",
    "livecoinwatch",
    "what do the trackers say",
    "what do price trackers show",
    "how much is my 60k worth",
])
def test_tracker_names_ask_for_the_price(question):
    assert query_router.asks_for_price(question)


@pytest.mark.parametrize("question", [
    "is it worth running a node?",
    "is staking worth it",
])
def test_worth_it_is_not_a_price_question(question):
    assert not query_router.asks_for_price(question)
    assert not query_router.asks_for_current_market_info(question)


@pytest.mark.parametrize("question, named", [
    ("what does nonkyc and coinpaprika say", True),
    ("CoinGecko?", True),
    ("whats the coin price", True),
    ("price of the coin?", True),
    ("price of eggs", False),
    ("flip a coin", False),
    ("the cmcs of brazil", False),
    ("whats the best fitness tracker", False),
    ("is the cmc api free", False),
])
def test_xeqm_price_wording_is_recognised(question, named):
    assert query_router.names_xeqm_price(question) is named


def test_named_trackers_are_listed_in_the_order_asked():
    assert query_router.named_trackers(
        "what does coinpaprika and NonKYC say, and Coin Gecko?"
    ) == ["coinpaprika", "nonkyc", "coingecko"]
    assert query_router.named_trackers("whats the coin price") == []
    assert query_router.named_trackers("livecoinwatch price") == []


@pytest.mark.parametrize("answer", [
    "I don't have the current figures from NonKYC in this chat, but",
    "I do not have live prices right now.",
    "I can't access real-time prices.",
    "You can check the price on CoinGecko.",
    "Check it at nonkyc.io for the latest.",
    "Please visit CoinPaprika for the latest price.",
    "I can guide you to the exact pages where it is listed.",
    "Search for XEQM on their site to see it.",
])
def test_deflections_are_recognised(answer):
    assert query_router.is_deflection(answer)


@pytest.mark.parametrize("answer", [
    "XEQM is $0.0203 on NonKYC right now.",
    "Yes: as a contributor to a pool node (minimum 10,000 XEQM).",
    "Find an open node on the Explorer, then run `stake`.",
    "Check that port 9230 is open on your firewall.",
    "I don't have to stake all 200,000 myself: a pool node works.",
])
def test_real_answers_are_not_deflections(answer):
    assert not query_router.is_deflection(answer)
