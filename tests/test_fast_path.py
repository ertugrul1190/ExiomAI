import pytest

import fast_path


REGISTRY = {
    "locked_supply": {"label": "Locked supply", "value": "5M", "unit": "XEQM"},
    "minimum_operator_contribution": {
        "label": "Minimum operator contribution",
        "value": "3,750",
        "unit": "XEQM"
    },
    "daily_reward_per_node": {
        "label": "Daily reward per node",
        "value": "12.5",
        "unit": "XEQM"
    },
    "block_height": {"label": "Block height", "value": "123,456", "unit": ""},
    "active_nodes": {"label": "Active service nodes", "value": "1,024", "unit": ""},
    "staking_requirement": {"label": "Staking requirement", "value": "15,000", "unit": "XEQM"},
    "current_apy": {"label": "Current service node APY", "value": "12.5", "unit": "%"},
    "total_supply": {"label": "Total supply", "value": "100M", "unit": "XEQM"},
    "mempool_transactions": {"label": "Mempool transactions", "value": "3", "unit": ""},
}


# ---------------------------------------------------------
# NORMALISATION
# ---------------------------------------------------------

def test_normalize_strips_punctuation_and_case():
    assert fast_path.normalize_question("  What's THE APY?? ") == \
        "what s the apy"


def test_normalize_handles_empty_input():
    assert fast_path.normalize_question(None) == ""


# ---------------------------------------------------------
# SOCIAL MESSAGES
# ---------------------------------------------------------

@pytest.mark.parametrize("question", [
    "hi", "Hello!", "hey there", "Good morning", "yo",
])
def test_greetings_are_answered_without_ai(question):
    result = fast_path.classify(question, REGISTRY)

    assert result["route"] == "greeting"
    assert "EXIOM" in result["answer"]


@pytest.mark.parametrize("question", [
    "thanks", "Thank you!", "thx", "appreciate it",
])
def test_thanks_is_answered_without_ai(question):
    assert fast_path.classify(question, REGISTRY)["route"] == "thanks"


def test_farewell_is_answered_without_ai():
    assert fast_path.classify("bye", REGISTRY)["route"] == "farewell"


def test_greeting_variants_are_deterministic():
    first = fast_path.classify("hello", REGISTRY)
    second = fast_path.classify("hello", REGISTRY)

    assert first["answer"] == second["answer"]


# ---------------------------------------------------------
# IDENTITY AND CREATOR
# ---------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Who made you?",
    "who built EXIOM AI",
    "Who is your developer?",
    "who is behind this assistant",
    "Are you made by XEQMLabs?",
    "who created this bot",
])
def test_creator_questions_use_the_documented_answer(question):
    result = fast_path.classify(question, REGISTRY)

    assert result["route"] == "creator"
    assert "Xrypto" in result["answer"]
    assert "youtube.com/@xrypto_cryptozone" in result["answer"]
    assert "XEQM Labs" in result["answer"]


@pytest.mark.parametrize("question", [
    "who are you",
    "What are you?",
    "what is EXIOM AI",
    "are you official?",
])
def test_identity_questions_state_independence(question):
    result = fast_path.classify(question, REGISTRY)

    assert result["route"] == "identity"
    assert "Xrypto" in result["answer"]
    assert "XEQM Labs" in result["answer"]


def test_creator_question_about_exiom_itself_is_not_claimed():
    """
    "Who developed EXIOM?" is a question about the project,
    not about this assistant, and must reach the AI.
    """

    assert fast_path.classify("who is the developer of exiom", REGISTRY) is None

    assert fast_path.classify("who created xeqm", REGISTRY) is None


# ---------------------------------------------------------
# DIRECT LIVE FACTS
# ---------------------------------------------------------

@pytest.mark.parametrize("question,expected", [
    ("How many active nodes are there?", "active_nodes"),
    ("how many active service nodes", "active_nodes"),
    ("What is the current block height?", "block_height"),
    ("latest block height please", "block_height"),
    ("What's the staking requirement?", "staking_requirement"),
    ("staking requirement", "staking_requirement"),
    ("what is the total supply right now", "total_supply"),
    ("what is the apy right now", "current_apy"),
    ("how many transactions are in the mempool", "mempool_transactions"),
])
def test_explicit_value_requests_skip_both_ai_calls(question, expected):
    result = fast_path.classify(question, REGISTRY)

    assert result == {"route": "live", "facts": [expected]}


@pytest.mark.parametrize("question", [
    "What is staking?",
    "What is a node?",
    "What does block height mean?",
    "Why does the node count matter?",
    "How does staking work?",
    "what are rewards",
    "explain the mempool",
    "is it worth running a node",
    "how do i run a node",
    "what is the difference between staking and locking",
])
def test_concept_questions_are_never_answered_with_a_number(question):
    assert fast_path.classify(question, REGISTRY) is None


def test_ambiguous_fact_names_require_a_value_cue():
    assert fast_path.classify("whats the apy", REGISTRY) is None
    assert fast_path.classify("block height", REGISTRY) is None
    assert fast_path.classify("what is the current apy", REGISTRY)["facts"] == ["current_apy"]


def test_two_facts_in_one_question_go_to_the_ai_router():
    assert fast_path.classify("what is the current block height and the total supply", REGISTRY) is None


def test_extra_meaning_in_the_question_goes_to_the_ai_router():
    assert fast_path.classify("is the current block height higher than bitcoin", REGISTRY) is None


def test_follow_up_pronouns_go_to_the_ai_router():
    assert fast_path.classify("and the active nodes for that", REGISTRY) is None


def test_long_questions_go_to_the_ai_router():
    assert fast_path.classify(
        "what is the current block height " + ("please " * 30),
        REGISTRY
    ) is None


def test_missing_fact_goes_to_the_ai_router():
    assert fast_path.match_direct_fact(
        "what is the current block height", {}
    ) is None


def test_empty_fact_value_goes_to_the_ai_router():
    registry = {"block_height": {"label": "Block height", "value": ""}}

    assert fast_path.match_direct_fact(
        "what is the current block height", registry
    ) is None


def test_unrelated_question_goes_to_the_ai_router():
    assert fast_path.classify("what is the best chicken biryani recipe", REGISTRY) is None


def test_empty_question_returns_none():
    assert fast_path.classify("", REGISTRY) is None
