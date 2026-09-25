# ---------------------------------------------------------
# DETERMINISTIC FAST PATH
# ---------------------------------------------------------
#
# The semantic AI router is excellent but it is not free.
#
# A meaningful share of real traffic is trivially
# classifiable without any AI call at all:
#
# - greetings and thanks
# - questions about ExiomAI itself (a fixed, documented
#   answer that must never be improvised)
# - explicit requests for one verified Explorer value
#
# This file answers ONLY those cases, and only when it is
# certain. Anything ambiguous returns None and is handed to
# the semantic AI router exactly as before.
#
# Being wrong here is far more expensive than an AI call,
# so every rule below is deliberately conservative.
# ---------------------------------------------------------

import re


# ---------------------------------------------------------
# NORMALISATION
# ---------------------------------------------------------

def normalize_question(question):
    """
    Lowercase, drop punctuation, collapse whitespace.
    """

    if not question:
        return ""

    text = str(question).lower()

    text = text.replace("’", "'")

    # Keep letters, digits and spaces only.
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def _words(normalized):
    return normalized.split()


# ---------------------------------------------------------
# CANNED RESPONSES
# ---------------------------------------------------------

CREATOR_URL = "https://youtube.com/@xrypto_cryptozone"


IDENTITY_ANSWER = (
    "I'm ExiomAI 👋 an assistant built to explain EXIOM and "
    "its coin XEQM in plain language.\n\n"
    "I was independently developed by **Xrypto** "
    f"({CREATOR_URL}). I'm not developed, operated, or "
    "endorsed by XEQM Labs — I'm an independent "
    "community project."
)


CREATOR_ANSWER = (
    "I was independently developed by **Xrypto** 🛠️\n\n"
    f"You can find Xrypto here: {CREATOR_URL}\n\n"
    "Just to be clear: I'm not developed, operated, or "
    "endorsed by XEQM Labs. ExiomAI is an independent "
    "community project."
)


GREETING_ANSWERS = (
    "Hey! 👋 I'm ExiomAI. Ask me anything about EXIOM or XEQM.",
    "Hello! 😄 ExiomAI here — what would you like to know "
    "about EXIOM or XEQM?",
    "Hey there! 👋 I'm your EXIOM/XEQM guy. What's on your mind?",
)


THANKS_ANSWERS = (
    "Anytime! 😄",
    "Happy to help! 🙌",
    "No problem at all 👍",
)


FAREWELL_ANSWERS = (
    "See you around! 👋",
    "Take care! 😄",
)


GREETING_PHRASES = {
    "hi", "hii", "hiii", "hello", "helo", "hey", "heyy", "yo",
    "hiya", "sup", "whats up", "what s up", "wassup", "gm",
    "good morning", "good afternoon", "good evening",
    "hi there", "hello there", "hey there", "greetings",
    "hi exiom", "hello exiom", "hey exiom", "hi exiom ai", "hi exiomai", "hello exiomai", "hey exiomai",
    "hello exiom ai", "hey exiom ai", "hey ai", "hello ai",
}


THANKS_PHRASES = {
    "thanks", "thank you", "thankyou", "thanks a lot",
    "thank you so much", "thanks so much", "ty", "thx",
    "tysm", "much appreciated", "appreciate it", "nice one",
    "thanks mate", "thanks man", "thanks bro", "cheers",
    "perfect thanks", "ok thanks", "okay thanks", "great thanks",
}


FAREWELL_PHRASES = {
    "bye", "goodbye", "bye bye", "see you", "see ya", "cya",
    "good night", "goodnight", "later", "peace out",
}


# ---------------------------------------------------------
# ExiomAI IDENTITY QUESTIONS
# ---------------------------------------------------------
#
# The documented answer to these is fixed: Xrypto, with the
# channel link, and an explicit independence statement.
#
# A deterministic answer is both cheaper AND safer than a
# generated one.
# ---------------------------------------------------------

# Only explicit self-references are listed. A bare "this"
# or "it" may easily refer to EXIOM itself rather than to
# ExiomAI, and answering those deterministically would be
# wrong rather than merely cheap.
_SELF = r"(you|exiom ?ai|this ai|this bot|this assistant|this chatbot)"


CREATOR_PATTERNS = (
    r"\bwho (made|built|created|developed|designed|coded|"
    r"programmed|owns|runs|maintains|operates) " + _SELF + r"\b",

    r"\bwho (is|s) your (maker|creator|developer|owner|dev|"
    r"author|founder)\b",

    r"\bwho (is|s) behind " + _SELF + r"\b",

    r"\byour (creator|developer|maker|owner|dev)\b",

    r"\bdid (xeqm ?labs|xeqm|exiom|the exiom team|xrypto) "
    r"(make|build|create|develop) " + _SELF + r"\b",

    r"\b(are|were) you (made|built|created|developed) by\b",
)


_IDENTITY_TAIL = r"( exactly| really| anyway| then)?$"


IDENTITY_PATTERNS = (
    r"^who (are|r) (you|u)" + _IDENTITY_TAIL,
    r"^what (are|r) (you|u)" + _IDENTITY_TAIL,
    r"^(what|who) (is|s) exiom ?ai" + _IDENTITY_TAIL,
    r"\bare you (an? )?(official|independent)\b",
    r"\bare you (part of|affiliated with|owned by|related to|"
    r"run by|made by) (xeqm ?labs|xeqm|exiom|the exiom team|"
    r"xrypto)\b",
    r"\bwhat (is|s) your (name|purpose|job)\b",
)


# ---------------------------------------------------------
# EXPLANATION CUES
# ---------------------------------------------------------
#
# If any of these appear, the user wants understanding, not
# a number. The fast path must never answer those.
# ---------------------------------------------------------

EXPLANATION_CUES = (
    "what does", "what do", "mean", "meaning", "explain",
    "explanation", "how does", "how do", "how is", "how are",
    "why", "difference", "compare", "should i", "is it worth",
    "tell me about", "teach", "learn", "understand", "benefit",
    "purpose", "good idea", "safe", "risk", "define",
    "definition", "works", "work", "affect", "impact",
    "matter", "important", "vs", "versus", "guide", "tutorial",
    "how can", "how could", "can i", "do i need", "help me",
)


# Words that carry no meaning for fact selection and may be
# safely ignored when checking that a question asks for one
# specific verified value and nothing else.
FILLER_WORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "by",
    "can", "count", "current", "currently", "data", "do",
    "does", "exiom", "exioms", "for", "from", "give", "has",
    "have", "here", "how", "in", "is", "it", "its", "just",
    "know", "latest", "like", "live", "many", "me", "much",
    "network", "networks", "no", "now", "number", "of", "ok",
    "on", "please", "pls", "right", "s", "show", "stat",
    "stats", "statistic", "statistics", "status", "tell",
    "transaction", "transactions", "tx", "txs", "txns",
    "the", "there", "these", "they", "this", "to", "today",
    "total", "u", "us", "value", "was", "what", "whats",
    "which", "with", "xeqm", "xeqms", "you", "your", "chain",
    "blockchain", "explorer", "atm", "moment", "at",
}


# Pronouns that usually refer to earlier conversation.
# Their presence means the question cannot be understood in
# isolation, so the semantic AI router must handle it.
CONTEXT_PRONOUNS = {
    "it", "its", "that", "those", "them", "they", "this",
    "these", "he", "she", "him", "her", "one", "ones", "same",
    "instead", "again", "also", "too",
}


# ---------------------------------------------------------
# DIRECT FACT PHRASES
# ---------------------------------------------------------
#
# Each phrase is specific enough that it can only be a
# request for that verified Explorer value.
#
# Generic single words such as "staking", "node" or
# "rewards" are deliberately absent: those are concept
# questions and belong to the AI router.
# ---------------------------------------------------------

FACT_PHRASES = {
    "block_height": (
        "block height",
        "blockheight",
        "block number",
        "chain height",
    ),

    "active_nodes": (
        "active nodes",
        "active node",
        "active service nodes",
        "active service node",
        "nodes are active",
        "nodes active",
        "nodes are running",
        "nodes running",
        "running nodes",
        "service nodes are there",
        "service nodes are running",
    ),

    "awaiting_contribution": (
        "awaiting contribution",
        "awaiting contributions",
        "nodes waiting for contributions",
        "waiting for contributions",
    ),

    "total_supply": (
        "total supply",
    ),

    "circulating_supply": (
        "circulating supply",
        "circulation supply",
        "coins in circulation",
    ),

    "locked_supply": (
        "locked supply",
        "locked in staking",
        "amount locked",
        "how much is locked",
    ),

    "staking_requirement": (
        "staking requirement",
        "staking requirements",
        "stake requirement",
        "staking req",
        "required to run a node",
        "required to run a service node",
        "needed to run a node",
        "need to stake",
        "needed to stake",
        "to stake a node",
        "to run a node",
    ),

    "minimum_operator_contribution": (
        "minimum operator contribution",
        "min operator contribution",
        "minimum contribution",
        "min contribution",
        "operator contribution",
    ),

    "service_node_reward": (
        "sn reward",
        "reward per block",
        "rewards per block",
        "block reward",
        "service node reward per block",
    ),

    "daily_service_node_emission": (
        "daily sn emission",
        "daily service node emission",
        "sn rewards 24h",
        "rewards in 24h",
        "emission per day",
    ),

    "mempool_transactions": (
        "mempool",
        "mem pool",
        "pending transactions",
        "unconfirmed transactions",
    ),

    "network_version": (
        "mainnet version",
        "network version",
        "node version",
        "software version",
    ),

    "hard_fork": (
        "hard fork",
        "hardfork",
        "hf version",
    ),

    "current_apy": (
        "apy",
        "annual percentage yield",
    ),

    "daily_reward_per_node": (
        "daily reward per node",
        "daily rewards per node",
        "reward per day per node",
        "earn per day",
        "earnings per day",
        "per day per node",
        "daily node reward",
    ),

    "annual_reward_per_node": (
        "annual reward per node",
        "annual rewards per node",
        "yearly reward per node",
        "earn per year",
        "earnings per year",
        "per year per node",
    ),

    # "Total nodes" is deliberately absent: the Explorer's
    # dashboard uses it for the active count, its feed for
    # the registered count.
    "inactive_nodes": (
        "inactive nodes",
        "inactive service nodes",
        "decommissioned nodes",
        "decommissioned service nodes",
    ),

    "registered_nodes": (
        "registered nodes",
        "registered service nodes",
    ),

    "open_pool_nodes": (
        "open pool nodes",
        "pool nodes",
        "open nodes",
        "nodes open for staking",
    ),

    "active_swarms": (
        "swarms",
        "active swarms",
    ),

    "node_countries": (
        "countries",
        "countries have nodes",
        "countries with nodes",
    ),

    "nodes_by_country": (
        "nodes by country",
        "nodes per country",
        "nodes in each country",
    ),

    "locked_supply_percent": (
        "percentage locked",
        "percent locked",
        "locked percentage",
        "percentage of supply locked",
        "percentage of supply is locked",
        "percentage of the supply is locked",
    ),

    "unlocked_supply": (
        "unlocked supply",
        "unstaked supply",
    ),

    "max_contributors": (
        "max contributors",
        "maximum contributors",
        "max contributors per node",
        "maximum contributors per node",
    ),

    # "Block time" alone is left to the router: it may mean
    # the target or the measured average.
    "average_block_time_24h": (
        "average block time",
        "avg block time",
        "average block time today",
    ),

    "average_block_time_1h": (
        "average block time in the last hour",
        "average block time last hour",
        "average block time this hour",
    ),

    "average_block_time_7d": (
        "average block time this week",
        "average block time last week",
        "average block time in the last 7 days",
        "average block time in the last week",
    ),

    "target_block_time": (
        "target block time",
    ),

    "blocks_24h": (
        "blocks in the last 24 hours",
        "blocks in 24 hours",
        "blocks in 24h",
        "blocks per day",
        "blocks a day",
    ),

    "hashrate_24h": (
        "hashrate",
        "hash rate",
        "network hashrate",
    ),

    "total_transactions": (
        "total transactions",
        "transactions ever",
        "transactions so far",
    ),

    "mempool_size": (
        "mempool size",
        "size of the mempool",
    ),

    "database_size": (
        "database size",
        "blockchain size",
        "size of the blockchain",
    ),

    "nodes_on_current_release": (
        "nodes are upgraded",
        "nodes upgraded",
        "upgraded nodes",
        "nodes are updated",
        "nodes updated",
        "nodes on the latest version",
        "nodes on latest version",
        "nodes on the current release",
        "nodes on the latest release",
    ),

    # "Quorums" alone is left to the router: there are four
    # kinds.
    "testing_quorums": (
        "testing quorums",
    ),

    "pulse_quorums": (
        "pulse quorums",
    ),

    "checkpoint_quorums": (
        "checkpoint quorums",
    ),

    "blink_quorums": (
        "blink quorums",
    ),
}


# Sorted longest-first so that the most specific phrase wins
# when two phrases overlap.
_SORTED_FACT_PHRASES = sorted(
    (
        (phrase, fact_key)
        for fact_key, phrases in FACT_PHRASES.items()
        for phrase in phrases
    ),
    key=lambda item: len(item[0]),
    reverse=True
)


# Words showing the user wants the value itself rather than
# the concept behind it.
VALUE_CUES = (
    "current", "currently", "now", "right now", "latest",
    "today", "atm", "at the moment", "how many", "how much",
    "number of", "count", "live", "so far", "up to date",
)


# Almost every fact name doubles as a concept a beginner may
# want explained, so a value cue is required before the fast
# path will answer with a number.
#
# The exceptions are the named thresholds, whose everyday name
# IS the value being asked for. The project documentation
# gives the staking requirement as the worked example of a
# direct live fact:
#
#   "What's the staking requirement?" → direct_live_fact
#
# Everything else — supply, APY, block height, rewards — goes
# to the semantic AI router unless the user clearly asked for
# the current number.
VALUE_CUE_EXEMPT_FACT_KEYS = {
    "staking_requirement",
    "minimum_operator_contribution",
    "max_contributors",
    "target_block_time",
    # A breakdown has no concept behind it to explain:
    # "nodes by country" can only mean the list.
    "nodes_by_country",
}


MAX_FAST_PATH_LENGTH = 120


def _matches_any(normalized, patterns):
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True

    return False


def _has_explanation_cue(normalized):
    padded = f" {normalized} "

    for cue in EXPLANATION_CUES:
        if f" {cue} " in padded:
            return True

    return False


def _pick(options, question):
    """
    Choose a canned variant deterministically.

    Deterministic selection keeps responses testable while
    still avoiding the exact same wording every time.
    """

    if not options:
        return None

    index = sum(
        ord(character)
        for character in question
    ) % len(options)

    return options[index]


def match_direct_fact(question, fact_registry=None):
    """
    Return one Explorer fact key when the question is
    unambiguously a request for that single verified value.

    Returns None whenever there is any doubt.
    """

    normalized = normalize_question(question)

    if not normalized:
        return None

    if len(normalized) > MAX_FAST_PATH_LENGTH:
        return None

    if _has_explanation_cue(normalized):
        return None

    matched_key = None
    remainder = normalized

    for phrase, fact_key in _SORTED_FACT_PHRASES:

        if f" {phrase} " not in f" {remainder} ":
            continue

        # Two different facts in one question is a mixed
        # question, which the AI router must handle.
        if matched_key and matched_key != fact_key:
            return None

        matched_key = fact_key

        remainder = f" {remainder} ".replace(
            f" {phrase} ",
            " "
        ).strip()

    if not matched_key:
        return None

    if matched_key not in VALUE_CUE_EXEMPT_FACT_KEYS:

        padded = f" {normalized} "

        has_value_cue = any(
            f" {cue} " in padded
            for cue in VALUE_CUES
        )

        if not has_value_cue:
            return None

    # Everything left over must be filler. If the user added
    # any other meaningful word, the question is richer than
    # a plain value lookup.
    for word in _words(remainder):

        if word in CONTEXT_PRONOUNS:
            return None

        if word not in FILLER_WORDS:
            return None

    if fact_registry is not None:

        fact = fact_registry.get(matched_key)

        if not fact:
            return None

        value = fact.get("value")

        if value is None or str(value).strip() == "":
            return None

    return matched_key


def classify(question, fact_registry=None):
    """
    Deterministically classify a question, or return None
    when the semantic AI router is required.

    Conversation history is deliberately not consulted: a
    question that cannot stand on its own is handed to the
    semantic AI router instead, which is what CONTEXT_PRONOUNS
    enforces.

    Returns one of:

    {"route": "greeting" | "thanks" | "farewell"
              | "identity" | "creator",
     "answer": str}

    {"route": "live", "facts": [fact_key]}
    """

    normalized = normalize_question(question)

    if not normalized:
        return None

    if len(normalized) > MAX_FAST_PATH_LENGTH:
        return None

    # Social openers are safe to answer even mid-conversation.
    if normalized in GREETING_PHRASES:
        return {
            "route": "greeting",
            "answer": _pick(GREETING_ANSWERS, normalized)
        }

    if normalized in THANKS_PHRASES:
        return {
            "route": "thanks",
            "answer": _pick(THANKS_ANSWERS, normalized)
        }

    if normalized in FAREWELL_PHRASES:
        return {
            "route": "farewell",
            "answer": _pick(FAREWELL_ANSWERS, normalized)
        }

    if _matches_any(normalized, CREATOR_PATTERNS):
        return {
            "route": "creator",
            "answer": CREATOR_ANSWER
        }

    if _matches_any(normalized, IDENTITY_PATTERNS):
        return {
            "route": "identity",
            "answer": IDENTITY_ANSWER
        }

    fact_key = match_direct_fact(
        question,
        fact_registry
    )

    if fact_key:
        return {
            "route": "live",
            "facts": [fact_key]
        }

    return None
