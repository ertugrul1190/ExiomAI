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
    "who built ExiomAI",
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
    "what is ExiomAI",
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


# ---------------------------------------------------------
# DIRECT LIVE FACTS ADDED WITH THE EXPLORER FEEDS
# ---------------------------------------------------------

NEW_FACT_KEYS = [
    "inactive_nodes", "registered_nodes", "open_pool_nodes",
    "active_swarms", "node_countries", "nodes_by_country",
    "locked_supply_percent", "unlocked_supply", "max_contributors",
    "average_block_time_1h", "average_block_time_24h",
    "average_block_time_7d", "target_block_time", "blocks_24h",
    "hashrate_24h", "total_transactions", "mempool_size",
    "database_size", "nodes_on_current_release", "testing_quorums",
    "pulse_quorums", "checkpoint_quorums", "blink_quorums",
]

FULL_REGISTRY = dict(
    REGISTRY,
    **{key: {"label": key, "value": "1", "unit": ""} for key in NEW_FACT_KEYS}
)


@pytest.mark.parametrize("question,expected", [
    ("how many inactive nodes are there", "inactive_nodes"),
    ("how many decommissioned nodes right now", "inactive_nodes"),
    ("how many registered service nodes", "registered_nodes"),
    ("how many open pool nodes", "open_pool_nodes"),
    ("how many swarms are there", "active_swarms"),
    ("how many countries have nodes", "node_countries"),
    ("current nodes by country", "nodes_by_country"),
    ("what percentage of supply is locked right now", "locked_supply_percent"),
    ("what is the unlocked supply now", "unlocked_supply"),
    ("what's the max contributors", "max_contributors"),
    ("current average block time", "average_block_time_24h"),
    ("average block time in the last hour right now", "average_block_time_1h"),
    ("current average block time this week", "average_block_time_7d"),
    ("what is the target block time", "target_block_time"),
    ("how many blocks in the last 24 hours", "blocks_24h"),
    ("what is the current hashrate", "hashrate_24h"),
    ("how many total transactions", "total_transactions"),
    ("current mempool size", "mempool_size"),
    ("what is the current database size", "database_size"),
    ("how many nodes are upgraded now", "nodes_on_current_release"),
    ("how many nodes on the latest version", "nodes_on_current_release"),
    ("how many testing quorums", "testing_quorums"),
    ("how many pulse quorums are there", "pulse_quorums"),
    ("current checkpoint quorums", "checkpoint_quorums"),
    ("how many blink quorums", "blink_quorums"),
])
def test_new_explorer_values_skip_both_ai_calls(question, expected):
    result = fast_path.classify(question, FULL_REGISTRY)

    assert result == {"route": "live", "facts": [expected]}


@pytest.mark.parametrize("question", [
    "what is a pulse quorum",
    "explain blink quorums",
    "how many quorums",
    "what is the block time",
    "how many total nodes",
    "which countries have the most nodes",
    "why is the hashrate so low",
    "what is the hashrate",
    "how many pulse quorums and blink quorums",
])
def test_ambiguous_or_conceptual_new_questions_go_to_the_ai(question):
    assert fast_path.classify(question, FULL_REGISTRY) is None


@pytest.mark.parametrize("question", [
    "Nodes by country",
    "nodes per country",
])
def test_the_country_breakdown_needs_no_value_cue(question):
    assert fast_path.classify(question, FULL_REGISTRY) == {
        "route": "live", "facts": ["nodes_by_country"]
    }


def test_the_mempool_count_still_wins_over_its_size():
    assert fast_path.classify(
        "how many transactions are in the mempool", FULL_REGISTRY
    ) == {"route": "live", "facts": ["mempool_transactions"]}


def test_every_explorer_fact_has_a_fast_path_phrase():
    """
    A new registry fact without a phrase silently costs an AI
    call for its plainest question.
    """

    import live_data

    missing = set(live_data.LiveData().fact_definitions) - set(
        fast_path.FACT_PHRASES
    )

    assert missing == set()
