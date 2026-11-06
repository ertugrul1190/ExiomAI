import json
import re


# ---------------------------------------------------------
# MARKET QUESTION BACKSTOP
# ---------------------------------------------------------
#
# The router flags these for a web search, but at minimal
# reasoning it sometimes forgets (1 in 4 identical calls in
# the Task 15 live test). The plainest wording is caught here
# too, at no cost. It only ever adds a search to a relevant,
# non-explanation question (see app.py).
# ---------------------------------------------------------

# "How much is it worth", never "is it worth running a node".
WORTH = r"worth(?! it\b| \w+ing\b)"

# The price trackers and the exchange XEQM trades on. Naming
# one asks what it says the price is.
TRACKERS = (
    r"nonkyc|coin ?paprika|coin ?gecko|coin ?market ?cap|cmc"
    r"|live ?coin ?watch|(the|price) trackers"
)

MARKET_PATTERN = re.compile(
    r"\b("
    r"prices?|priced"
    r"|market\s?caps?|marketcap"
    r"|(trading|24h|24 hour|daily)\s+volume"
    r"|" + WORTH +
    r"|how much is (xeqm|exiom|it|one)"
    r"|where (can|do|should|to) (i |we |you )?(buy|trade|purchase)"
    r"|where (can|do|should|to) (i |we |you )?get (xeqm|exiom|coins?|tokens?|some)\b"
    r"|exchanges?|listed|listings?"
    r"|(latest|newest|current) ((xeqm|exiom) )?(core |software )?releases?"
    r"|news|announcements?"
    r")\b",
    re.IGNORECASE
)


def asks_for_current_market_info(question):
    return bool(MARKET_PATTERN.search(question or ""))


# The part of a market question the price trackers' APIs
# answer live (market_data.py). Movement words count: "is
# XEQM up today?" wants the 24h change.
PRICE_PATTERN = re.compile(
    r"\b("
    r"prices?|priced|value|" + WORTH + "|" + TRACKERS +
    r"|how much is (xeqm|exiom|it|one)"
    r"|market\s?caps?|marketcap"
    r"|(trading|24h|24 hour|daily)\s+volume"
    r"|(going|gone|trending) (up|down)|pumping|dumping"
    r"|(is|are) (xeqm|exiom|it) (up|down)"
    r"|(24h|24 hour|daily) change"
    r")\b",
    re.IGNORECASE
)

# The part only a web search answers: where it trades,
# releases, news.
BEYOND_PRICE_PATTERN = re.compile(
    r"\b("
    r"where (can|do|should|to) (i |we |you )?(buy|trade|purchase)"
    r"|where (can|do|should|to) (i |we |you )?get (xeqm|exiom|coins?|tokens?|some)\b"
    r"|exchanges?|listed|listings?"
    r"|releases?|news|announcements?"
    r"|all[- ]time|ath|history|historical|predictions?|forecasts?"
    r")\b",
    re.IGNORECASE
)


def asks_for_price(question):
    return bool(PRICE_PATTERN.search(question or ""))


# A price prediction or target. Never searched: the answer
# may not repeat one anyway (WEB_SEARCH_RULES 6), and a
# search for one only ever finds an exchange's forecast tool
# (it quoted MEXC's "2027 target" in the 6 Nov review).
PREDICTION_PATTERN = re.compile(
    r"\b(predictions?|predict|forecasts?|price targets?"
    r"|(will|could|can) (xeqm|exiom|it|the (coin|price)) "
    r"(go up|go down|rise|fall|moon|pump|reach|hit))\b",
    re.IGNORECASE
)


def asks_for_prediction(question):
    return bool(PREDICTION_PATTERN.search(question or ""))


def asks_beyond_price(question):
    return bool(BEYOND_PRICE_PATTERN.search(question or ""))


# A question about what a market term means, not its current
# value: "what does market cap mean?" needs no price. Decided
# here rather than by the router's intent, which once labelled
# every price question "explanation".
CONCEPT_PATTERN = re.compile(
    r"\b(mean|means|meaning|define|definition|explain\w*)\b"
    r"|\bhow (is|are) (the )?[\w\s]{0,40}?\b(calculated|computed|worked out)\b"
    r"|\bwhat(['’]s| is| are)( an?)? (market\s?caps?|marketcap|trading volume)\b",
    re.IGNORECASE
)


def asks_what_it_means(question):
    return bool(CONCEPT_PATTERN.search(question or ""))


# The trackers market_data.py reads, by the names users type.
TRACKER_NAMES = {
    "nonkyc": re.compile(r"\bnonkyc", re.IGNORECASE),
    "coinpaprika": re.compile(r"\bcoin ?paprika", re.IGNORECASE),
    "coingecko": re.compile(r"\bcoin ?gecko", re.IGNORECASE),
}


def named_trackers(question):
    """
    The trackers we read that the question names, in the
    order it names them.
    """

    found = [
        (match.start(), name)
        for name, pattern in TRACKER_NAMES.items()
        if (match := pattern.search(question or ""))
    ]

    return [name for _, name in sorted(found)]


# ---------------------------------------------------------
# DEFLECTIONS
# ---------------------------------------------------------
#
# "I don't have the current figures in this chat, check
# CoinGecko": the model sending the user off for something
# the backend could have given it. app.py treats one like
# [[LOOKUP]] at a step that can still look further. Only the
# answer's opening is checked (see app.DEFLECTION_WINDOW).
# ---------------------------------------------------------

DEFLECTION_PATTERN = re.compile(
    r"\bI (don['’]t|do not|can['’]t|cannot|am unable to|['’]m unable to)"
    r" (have|access|see|fetch|pull|get|check)\b[^.!?\n]{0,80}?"
    r"\b(in this chat|right now|at the moment|currently|real[- ]time|live)\b"
    r"|\bcheck (it|them|the (latest |current |live )?(price|prices|figures?|numbers?|rates?))"
    r" (on|at|via)\b"
    r"|\bvisit\b[^.!?\n]{0,60}\bfor (the )?(latest|current|live|up[- ]to[- ]date)\b"
    r"|\bI can guide you to\b"
    r"|\bsearch (for )?[^.!?\n]{0,40}\bon (their|its|the official) (site|website|page)",
    re.IGNORECASE
)


def is_deflection(answer):
    return bool(DEFLECTION_PATTERN.search(answer or ""))


EXIOM_NAME = re.compile(r"\b(exiom|xeqm|xeqmlabs|xeqm ?labs)", re.IGNORECASE)


def names_exiom(question):
    return bool(EXIOM_NAME.search(question or ""))


# A price tracker, or "the coin's" price: in a chat about
# XEQM, both mean XEQM. The router sent "what does nonkyc and
# coinpaprika say" and "whats the coin price" off-topic.
# Never bare "cmc" here: "is the cmc api free" is unrelated.
XEQM_PRICE_WORDING = re.compile(
    r"\b(" + TRACKERS.replace("|cmc", "") + r")\b"
    r"|\bcoin(['’]?s)? (price|value|worth|market\s?cap)"
    r"|\b(price|value|worth) of (the|this|your|ur) coin\b",
    re.IGNORECASE
)


def names_xeqm_price(question):
    return bool(XEQM_PRICE_WORDING.search(question or ""))


# Network terms that, in a chat about EXIOM, mean EXIOM. The
# operator, wallet and platform words come from the official
# docs (knowledge/sources.json). Only unambiguous ones: "port",
# "oracle", "stake" or "blink" alone are everyday words too,
# and the router prompt covers "which ports do I open?".
EXIOM_TOPIC = re.compile(
    r"\b(service nodes?|nodes|staking|stakers?|quorums?|block height"
    r"|hard ?forks?|hf ?\d+|explorer|mempool|circulating supply"
    r"|pulse[- ]recovery|uptime proofs?"
    r"|decommission\w*|deregist\w*|recommission\w*"
    r"|registration command|operator (fee|cut)"
    r"|unstake|unstaking|unbond\w*|pool nodes?"
    r"|(gui|cli) wallet|wallet rpc|oracle sidecar|lokinet|llarp"
    r"|pecunia|appimage|(the|my) daemon)\b",
    re.IGNORECASE
)


def names_exiom_topic(question):
    return bool(EXIOM_TOPIC.search(question or ""))


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
You are the semantic router for ExiomAI.

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

- EXIOM, XEQM, or ExiomAI itself
- cryptocurrency/blockchain concepts reasonably useful for
  understanding EXIOM
- running, staking on or fixing a node, wallet, oracle or
  the API, even unnamed: "Which ports do I open?",
  "What is Pulse-recovery?", "Why was I decommissioned?",
  "What sample apps are there for the API?"
- a follow-up to an EXIOM conversation

ANY question about THIS assistant is RELEVANT, including its
creator, maker, developer, owner, name, identity, purpose,
public creator information, and whether it is official or
independent. Different wording, slang, or indirect phrasing
does not change this.

Examples: "Who made you?", "Who is behind this?",
"Are you made by XEQMLabs?", "What are you?" → relevant

XEQM price, market and exchange questions are RELEVANT:
"Exiom coin price", "Where can I buy XEQM?" → relevant

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
"How many nodes are in Canada?" → direct_live_fact
"How many nodes joined or left in the last 24 hours?"
→ direct_live_fact
"When is the next hard fork?" → direct_live_fact

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
above. Questions about ExiomAI itself — its creator,
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
"How many nodes are in Germany?" DOES request
nodes_by_country.

A question about ANY current EXIOM number, count, status,
date or recent change selects the closest facts, even when
none matches exactly.


============================================================
WEB SEARCH
============================================================

"search" is true ONLY when a relevant message needs CURRENT
EXIOM/XEQM information that no Explorer fact above supplies
and that changes over time:

- XEQM market price, market cap, trading volume
- where XEQM is traded or listed right now
- the latest XEQM software release
- recent EXIOM/XEQMLabs announcements or news

Otherwise "search" is false: concepts, explanations, how
EXIOM works, ExiomAI itself, anything an Explorer fact
answers, and every unrelated message.

"Exiom coin price" → search true
"How much is XEQM worth?" → search true
"Where can I buy XEQM right now?" → search true
"What's the latest XEQM release?" → search true
"How many active nodes are there?" → search false
"What is staking?" → search false
"Will XEQM go up?" → search false


============================================================
WORKED EXAMPLES
============================================================

"whats the coin price" → scope relevant, intent general,
search true ("the coin" is XEQM)
"what does nonkyc and coinpaprika say" → scope relevant,
intent general, search true (XEQM's price trackers)
"and now?" after a price answer → intent general, search true
"can I stake 60k?" → intent general, search false (what the
user can do with that amount)
"i have 50000 xeqm what can i do" → intent general, search
false
"what does market cap mean?" → intent explanation, search
false
"I get GLIBC_2.x not found when starting the daemon",
"the Linux AppImage gives a sandbox error", "how much does
Pecunia charge?" → scope relevant (node, wallet and hosting
troubleshooting the docs cover)


============================================================
OUTPUT
============================================================

Return ONLY valid JSON, exactly this structure:

{{"scope":"<scope>","intent":"<intent>","facts":[<keys>],"search":<true|false>}}

Replace every <...> with your decision for this message.

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
        result = None

    # Valid JSON that is not an object ("[]", "true") is as
    # unusable as invalid JSON.
    if not isinstance(result, dict):
        return {
            "scope": "relevant",
            "intent": "general",
            "facts": [],
            "search": False
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

    # Only a literal true searches: a search is paid work.
    search = result.get("search") is True and scope != "unrelated"

    return {
        "scope": scope,
        "intent": intent,
        "facts": facts,
        "search": search
    }