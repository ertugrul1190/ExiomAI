import re


FACT_CATALOG = {
    "active_nodes": {
        "concepts": [
            "active node",
            "active nodes",
            "service node",
            "service nodes",
            "node count",
            "nodes online",
            "online nodes"
        ],
        "question_signals": [
            "how many",
            "number",
            "count",
            "current",
            "currently",
            "right now",
            "now"
        ]
    },

    "total_supply": {
        "concepts": [
            "total supply",
            "xeqm supply",
            "supply of xeqm"
        ],
        "question_signals": [
            "what",
            "how much",
            "current",
            "currently",
            "right now",
            "now"
        ]
    },

    "block_height": {
        "concepts": [
            "block height",
            "current block",
            "latest block",
            "block number"
        ],
        "question_signals": [
            "what",
            "which",
            "current",
            "latest",
            "right now",
            "now"
        ]
    },

    "service_node_reward": {
        "concepts": [
            "service node reward",
            "node reward",
            "block reward",
            "reward per block",
            "reward for a block"
        ],
        "question_signals": [
            "what",
            "how much",
            "current",
            "currently",
            "right now",
            "now"
        ]
    }
}


EXPLANATION_SIGNALS = [
    "why",
    "explain",
    "what does that mean",
    "what does this mean",
    "how does",
    "reason",
    "significance",
    "important",
    "is that good",
    "is that bad",
    "compare",
    "difference"
]


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def needs_explanation(question):
    text = normalize(question)

    return any(
        signal in text
        for signal in EXPLANATION_SIGNALS
    )


def find_requested_fact(question):
    text = normalize(question)

    best_fact = None
    best_score = 0

    for fact_name, config in FACT_CATALOG.items():
        score = 0

        for concept in config["concepts"]:
            if concept in text:
                score += 5

        for signal in config["question_signals"]:
            if signal in text:
                score += 1

        if score > best_score:
            best_score = score
            best_fact = fact_name

    if best_score < 5:
        return None

    return best_fact