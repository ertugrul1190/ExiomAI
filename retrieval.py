import math
import re
from collections import Counter
from pathlib import Path


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but",
    "by", "can", "do", "does", "for", "from", "had", "has",
    "have", "how", "i", "if", "in", "into", "is", "it", "its",
    "me", "my", "of", "on", "or", "our", "so", "that", "the",
    "their", "them", "there", "they", "this", "to", "was", "we",
    "what", "when", "where", "which", "who", "why", "will", "with",
    "would", "you", "your"
}


def stem(word):
    """
    Drop a common English suffix, then a final "e", so "earn"
    meets "earnings", "deregistered" meets "deregister" and
    stake, stakes, staked and staking all become "stak".
    Applied to the question and the knowledge alike; a stem
    shorter than three letters keeps the word whole.
    """

    for suffix in ("ings", "ing", "ed", "s"):
        if (
            word.endswith(suffix)
            and not word.endswith("ss")
            and len(word) - len(suffix) >= 3
        ):
            word = word[:-len(suffix)]
            break

    if word.endswith("e") and len(word) > 3:
        return word[:-1]

    return word


# Everyday words for the coin. Without this, a rare word like
# "coins" outweighs everything else and pulls in the coin-burn
# sections for "can i stake 60k coins".
SYNONYMS = {
    "coin": "xeqm",
    "token": "xeqm",
}


def _words(text):
    for word in re.findall(r"[a-zA-Z0-9]+", text.lower()):
        if word not in STOP_WORDS and len(word) > 1:
            word = stem(word)
            yield SYNONYMS.get(word, word)


def normalize_words(text):
    return set(_words(text))


def load_markdown_file(file_path):
    path = Path(file_path)

    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8")


def load_knowledge_directory(directory="knowledge"):
    """
    Loads factual Markdown knowledge.

    instructions.md is deliberately excluded because instructions
    belong permanently in the system prompt rather than retrieval.
    """

    directory_path = Path(directory)

    excluded_files = {
        "instructions.md",
        "changelog.md"
    }

    documents = []

    for path in sorted(directory_path.glob("*.md")):
        if path.name in excluded_files:
            continue

        text = path.read_text(encoding="utf-8")

        if text.strip():
            documents.append({
                "source_file": path.name,
                "text": text
            })

    return documents


def split_markdown_document(text, source_file):
    """
    Splits Markdown into useful sections using # headings.

    This is much better for our new knowledge files than splitting
    only on blank lines.
    """

    sections = []

    current_heading = "General"
    current_parent = ""
    current_lines = []

    def save_section():
        nonlocal current_lines

        content = "\n".join(current_lines).strip()

        if content:
            sections.append({
                "source_file": source_file,
                "parent": current_parent,
                "title": current_heading,
                "content": content
            })

        current_lines = []

    for line in text.splitlines():

        heading_match = re.match(
            r"^(#{1,6})\s+(.+?)\s*$",
            line
        )

        if heading_match:
            save_section()

            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()

            if level == 1:
                current_parent = heading
                current_heading = heading
            else:
                current_heading = heading

            continue

        current_lines.append(line)

    save_section()

    return sections


def build_knowledge_sections(documents):
    sections = []

    for document in documents:
        sections.extend(
            split_markdown_document(
                document["text"],
                document["source_file"]
            )
        )

    for section in sections:
        section["_index"] = _section_index(section)

    return sections


# Important XEQM concepts. A section that shares one with the
# question earns extra weight in _score().
#
# A term matches whole words (plural "s" allowed): "pos"
# never matches "purpose", nor "apy" "happy". A trailing "*"
# makes it a stem: "deregist*" matches deregister,
# deregistered and deregistration.
CONCEPT_GROUPS = {
    "service node": [
        "service node",
        "shared node",
        "node operator"
    ],
    "staking": [
        "stake",
        "staking",
        "staked",
        "contribut*",
        "collateral",
        "how many xeqm",
        "how much xeqm",
        "operator fee",
        "operator cut"
    ],
    "unbonding": [
        "unbond*",
        "withdraw*"
    ],
    "supply": [
        "supply",
        "emission",
        "mint*",
        "inflation"
    ],
    "rewards": [
        "reward",
        "earn*",
        "yield"
    ],
    "privacy": [
        "privacy",
        "private",
        "cryptonote",
        "ring signature",
        "stealth address"
    ],
    "developer api": [
        "api",
        "developer",
        "development tier"
    ],
    "oracle": [
        "oracle",
        "attestation",
        "prover",
        "verifier"
    ],
    "rfq": [
        "rfq",
        "trading platform",
        "otc"
    ],
    "lokinet": [
        "lokinet",
        "llarp",
        "onion routing"
    ],
    "governance": [
        "governance",
        "treasury",
        "voting"
    ],
    "hard fork": [
        "hard fork",
        "hf20",
        "hf21",
        "hf22",
        "hf23"
    ],
    "consensus": [
        "consensus",
        "proof of stake",
        "pos",
        "quorum",
        "pulse"
    ],

    # Operator topics from the official GitBook and core
    # README.
    "penalties": [
        "offline",
        "downtime",
        "decomm*",
        "deregist*",
        "slash*",
        "penalt*",
        "credits",
        "grace period"
    ],
    "uptime": [
        "uptime"
    ],
    "earnings": [
        "apy",
        "per month",
        "monthly",
        "income",
        "profit",
        "roi"
    ],
    "payout": [
        "payout",
        "paid out",
        "pay out",
        "batch"
    ],
    "registration": [
        "register*",
        "registration"
    ],
    "setup": [
        "set up",
        "setup",
        "install*",
        "docker",
        "hardware",
        "vps"
    ],
    "ports": [
        "port",
        "firewall"
    ],
    "upgrade": [
        "update*",
        "upgrade*",
        "latest version",
        "new version"
    ],
    "wallet": [
        "wallet",
        "seed"
    ],

    # The staking amounts a section names. A question names
    # one in its own words instead ("60k", "150k xeqm"), see
    # STAKE_AMOUNT.
    "stake amount": [
        "200,000 xeqm",
        "100,000 xeqm",
        "10,000 xeqm"
    ]
}


# An amount of XEQM in a question: "60k", "60,000", "150k
# xeqm", "50000 coins". Never a bare number: "is 9231 safe to
# expose" is a port, "block 236920" a height.
STAKE_AMOUNT = re.compile(
    r"\b\d+(?:\.\d+)?\s?k\b"
    r"|\b\d{1,3}(?:,\d{3})+\b"
    r"|\b\d+(?:\.\d+)?\s?(?:xeqm|coins?|tokens?)\b"
)


def _terms_pattern(terms):
    return re.compile(
        r"\b(?:" + "|".join(
            re.escape(term[:-1]) if term.endswith("*")
            else re.escape(term) + r"s?\b"
            for term in terms
        ) + ")"
    )


# canonical -> (name or variants, variants only)
CONCEPT_PATTERNS = {
    canonical: (
        _terms_pattern((canonical, *variants)),
        _terms_pattern(variants),
    )
    for canonical, variants in CONCEPT_GROUPS.items()
}


def _mentioned_concepts(*texts):
    """
    Canonical concepts that any of the lowercased texts
    mention, by name or by one of their variants.
    """

    return frozenset(
        canonical
        for canonical, (any_term, _) in CONCEPT_PATTERNS.items()
        if any(any_term.search(text) for text in texts)
    )


def _section_index(section):
    """
    Everything scoring needs from a section.

    Knowledge is fixed for the life of the process, so
    build_knowledge_sections() computes this once at startup
    instead of on every question. A section built any other
    way is indexed on the fly, with identical results.
    """

    index = section.get("_index")

    if index is not None:
        return index

    title = section["title"] + " " + section["parent"]
    content_words = list(_words(section["content"]))

    return {
        "title_words": normalize_words(title),
        "content_counts": Counter(content_words),
        "length": len(content_words),
        "concepts": _mentioned_concepts(
            section["title"].lower(),
            section["content"].lower()
        ),
        "title_concepts": _mentioned_concepts(title.lower()),
    }


def _question_index(question):
    """
    The question side of scoring.

    Unlike a section, a question is matched on the variants
    only, never on the canonical name: that asymmetry is the
    original scoring rule and is kept exactly.
    """

    question_lower = question.lower()

    concepts = {
        canonical
        for canonical, (_, variant) in CONCEPT_PATTERNS.items()
        if variant.search(question_lower)
    }

    if STAKE_AMOUNT.search(question_lower):
        concepts.add("stake amount")

    return {
        "words": normalize_words(question),
        "concepts": frozenset(concepts),
    }


# ---------------------------------------------------------
# RARITY-WEIGHTED SCORING (BM25)
# ---------------------------------------------------------
#
# The standard keyword-search ranking. A word or concept
# counts more the fewer sections contain it: "contributor"
# outweighs "node", which 35 of 78 sections share. A long
# section does not win by length alone, a title match counts
# triple, and a concept counts as two words (it stands for
# several wordings). Before this, every match counted the
# same, and in 74 of 92 eval questions the last places sent
# were decided by file order. See "Task Docs/Answer Quality
# and Image Upload.md".
# ---------------------------------------------------------

BM25_K1 = 1.2
BM25_B = 0.75
TITLE_WEIGHT = 3
CONCEPT_WEIGHT = 2


def _idf(containing, total):
    return math.log(1 + (total - containing + 0.5) / (containing + 0.5))


def _saturate(frequency, length_ratio):
    return frequency * (BM25_K1 + 1) / (
        frequency + BM25_K1 * (1 - BM25_B + BM25_B * length_ratio)
    )


def _rank(query, indexes):
    """
    (score, title words matched) per section, in order.
    """

    total = len(indexes)
    average_length = sum(index["length"] for index in indexes) / total or 1

    word_idf = {
        word: _idf(
            sum(
                word in index["title_words"] or word in index["content_counts"]
                for index in indexes
            ),
            total
        )
        for word in query["words"]
    }

    concept_idf = {
        concept: _idf(
            sum(concept in index["concepts"] for index in indexes),
            total
        )
        for concept in query["concepts"]
    }

    ranked = []

    for index in indexes:

        length_ratio = index["length"] / average_length
        score = 0.0

        for word, idf in word_idf.items():
            frequency = (
                index["content_counts"].get(word, 0)
                + TITLE_WEIGHT * (word in index["title_words"])
            )

            if frequency:
                score += idf * _saturate(frequency, length_ratio)

        for concept, idf in concept_idf.items():
            if concept in index["concepts"]:
                frequency = 1 + TITLE_WEIGHT * (concept in index["title_concepts"])
                score += CONCEPT_WEIGHT * idf * _saturate(frequency, length_ratio)

        ranked.append((
            round(score, 9),
            len(query["words"] & index["title_words"])
        ))

    return ranked


# Between the sections retrieve_knowledge() returns.
SECTION_SEPARATOR = "\n\n---\n\n"


def _truncate_section(content, max_chars):
    """
    Shorten one section at a paragraph or line boundary.

    Knowledge is supplied to the AI as evidence, so a clean
    cut matters more than squeezing in a few extra words.
    """

    if len(content) <= max_chars:
        return content

    cut = content[:max_chars]

    boundary = max(
        cut.rfind("\n\n"),
        cut.rfind("\n")
    )

    if boundary > max_chars * 0.5:
        cut = cut[:boundary]

    return cut.rstrip() + "\n\n[section truncated]"


def retrieve_knowledge(
    question,
    sections,
    limit=6,
    char_budget=7000,
    max_section_chars=2200,
    min_score_ratio=0.6
):
    """
    Select the verified knowledge worth paying to send.

    Three limits apply, strongest first:

    1. relevance   — a section far weaker than the best match
                     adds tokens without adding evidence (below
                     0.6 of the best score; tests/test_knowledge.py
                     keeps every golden answer at that cut)
    2. section size — one enormous section cannot consume the
                     whole budget
    3. total size  — the combined context stays predictable
    """

    query = _question_index(question)

    ranks = _rank(
        query,
        [_section_index(section) for section in sections]
    ) if sections else []

    # On an equal score, the section whose title matches more
    # of the question wins; file order only after that.
    scored = sorted(
        (
            (score, title_matches, section)
            for (score, title_matches), section in zip(ranks, sections)
            if score > 0
        ),
        key=lambda item: (item[0], item[1]),
        reverse=True
    )[:limit]

    if scored:

        best_score = scored[0][0]

        threshold = best_score * min_score_ratio

        selected = [
            section
            for score, _, section in scored
            if score >= threshold
        ]

    else:
        # No keyword overlap at all. The ranking cannot help
        # here, so a small general slice is used: enough to
        # ground an answer, without paying for a large random
        # slice of the knowledge base.
        selected = sections[:3]

    formatted_sections = []
    used = 0

    for section in selected:

        remaining = char_budget - used

        if remaining <= 400:
            break

        content = _truncate_section(
            section["content"],
            min(max_section_chars, remaining)
        )

        used += len(content)

        # No file name: the model once cited "core.md" and
        # made up a URL for it.
        formatted_sections.append(
            f"""
SECTION: {section['title']}

{content}
""".strip()
        )

    return SECTION_SEPARATOR.join(formatted_sections)
