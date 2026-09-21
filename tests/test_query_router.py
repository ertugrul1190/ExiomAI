import json

import query_router


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
        "facts": ["active_nodes"]
    }


def test_invalid_json_falls_back_to_a_safe_route():
    assert query_router.parse_router_result("not json", REGISTRY) == {
        "scope": "relevant",
        "intent": "general",
        "facts": []
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
        "facts": []
    }
