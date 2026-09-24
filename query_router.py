import json


def build_fact_catalogue(fact_registry):
    """
    Describe the Explorer facts the router may choose from.

    Deliberately excludes each fact's current VALUE.

    The router selects fact KEYS; it never needs the numbers
    to do that. Leaving the values out keeps this prompt
    identical between requests, which both removes tokens
    and lets the provider reuse the cached prompt prefix.
    """

    if not fact_registry:
        return "(none available)"

    lines = []

    for key in sorted(fact_registry.keys()):

        fact = fact_registry[key] or {}

        label = fact.get("label", "")
        meaning = fact.get("meaning", "")

        lines.append(
            f"{key}: {label} — {meaning}"
        )

    return "\n".join(lines)


def build_router_prompt(fact_registry):
    """
    Build the semantic router instructions.

    The user's message is NOT embedded here. It is sent as
    the user turn instead, so this prompt stays constant and
    cacheable across requests.
    """

    return f"""
You are the semantic router for EXIOM AI.

Your ONLY job is to decide how the user's latest message
should be handled.

Do not answer the user's question.


AVAILABLE LIVE EXPLORER FACTS:

{build_fact_catalogue(fact_registry)}


============================================================
SCOPE
============================================================

relevant | unrelated | mixed

RELEVANT means the message concerns:

- EXIOM, XEQM, or EXIOM AI itself
- cryptocurrency/blockchain concepts reasonably useful for
  understanding EXIOM
- a follow-up to an EXIOM conversation

ANY question about THIS assistant is RELEVANT, including its
creator, maker, developer, owner, name, identity, purpose,
public creator information, and whether it is official or
independent. Different wording, slang, or indirect phrasing
does not change this.

Examples: "Who made you?", "Who is behind this?",
"Are you made by XEQMLabs?", "What are you?" → relevant

UNRELATED means it has nothing reasonably to do with those.

MIXED means it contains both.


============================================================
INTENT
============================================================

direct_live_fact | explanation | general | mixed

DIRECT_LIVE_FACT:
ONLY when the user requests a specific current value, number,
count, amount, version or statistic that one of the supplied
Explorer facts directly answers.

"How many active nodes are there?" → direct_live_fact
"What is the current block height?" → direct_live_fact
"What's the staking requirement?" → direct_live_fact
"Nodes by country" → direct_live_fact

A message that is only a fact's name, with no question
around it, asks for that fact's current value.

EXPLANATION:
The user wants to understand a concept, meaning, reason,
relationship, process, implication or interpretation.

"What is staking?" → explanation
"What is a node?" → explanation
"What does block height mean?" → explanation
"Why does the node count matter?" → explanation

GENERAL:
A relevant EXIOM/XEQM question that fits neither category
above. Questions about EXIOM AI itself — its creator,
identity, ownership, purpose, or relationship to
XEQM/XEQMLabs — normally use GENERAL.

MIXED:
The question needs BOTH one or more live Explorer facts AND
an explanation.


============================================================
FACT SELECTION
============================================================

Return Explorer fact keys ONLY when those facts are actually
useful for answering the question.

Do NOT select a fact merely because its name contains a word
from the user's question. This distinction is CRITICAL:

"What is staking?" does NOT request staking_requirement.
"What is a node?" does NOT request active_nodes.
"What are rewards?" does NOT request service_node_reward.
"What is block height?" does NOT request block_height.

But:

"What is the staking requirement?" DOES request
staking_requirement.
"How many nodes are active?" DOES request active_nodes.
"What is the current block height?" DOES request
block_height.
"Nodes by country" DOES request nodes_by_country.
"Where are the nodes located?" DOES request
nodes_by_country.


============================================================
OUTPUT
============================================================

Return ONLY valid JSON, exactly this structure:

{{"scope":"relevant","intent":"explanation","facts":[]}}

"facts" must contain zero or more exact keys from AVAILABLE
LIVE EXPLORER FACTS. Never invent a fact key.
"""


def parse_router_result(raw_result, fact_registry):
    """
    Safely validate the AI router's JSON.
    """

    try:
        result = json.loads(raw_result)

    except (json.JSONDecodeError, TypeError):
        return {
            "scope": "relevant",
            "intent": "general",
            "facts": []
        }

    valid_scopes = {
        "relevant",
        "unrelated",
        "mixed"
    }

    valid_intents = {
        "direct_live_fact",
        "explanation",
        "general",
        "mixed"
    }

    scope = result.get("scope", "relevant")
    intent = result.get("intent", "general")
    facts = result.get("facts", [])

    if scope not in valid_scopes:
        scope = "relevant"

    if intent not in valid_intents:
        intent = "general"

    if not isinstance(facts, list):
        facts = []

    available_keys = set(
        (fact_registry or {}).keys()
    )

    facts = [
        fact
        for fact in facts
        if fact in available_keys
    ]

    return {
        "scope": scope,
        "intent": intent,
        "facts": facts
    }