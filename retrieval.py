import re
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


def normalize_words(text):
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {
        word for word in words
        if word not in STOP_WORDS and len(word) > 1
    }


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
        "contribution",
        "contributor"
    ],
    "unbonding": [
        "unbond",
        "unbonding",
        "withdraw",
        "withdrawal"
    ],
    "supply": [
        "supply",
        "emission",
        "mint",
        "inflation"
    ],
    "rewards": [
        "reward",
        "rewards",
        "earn",
        "earning",
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
    ]
}


def _mentioned_concepts(*texts):
    """
    Canonical concepts that any of the lowercased texts
    mention, by name or by one of their variants.
    """

    return frozenset(
        canonical
        for canonical, variants in CONCEPT_GROUPS.items()
        if any(
            term in text
            for text in texts
            for term in (canonical, *variants)
        )
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

    return {
        "title_words": normalize_words(
            section["title"] + " " + section["parent"]
        ),
        "content_words": normalize_words(section["content"]),
        "concepts": _mentioned_concepts(
            section["title"].lower(),
            section["content"].lower()
        ),
    }


def _question_index(question):
    """
    The question side of scoring.

    Unlike a section, a question is matched on the variants
    only, never on the canonical name: that asymmetry is the
    original scoring rule and is kept exactly.
    """

    question_lower = question.lower()

    return {
        "words": normalize_words(question),
        "concepts": frozenset(
            canonical
            for canonical, variants in CONCEPT_GROUPS.items()
            if any(
                variant in question_lower
                for variant in variants
            )
        ),
    }


def _score(query, index):

    score = 0

    # Heading matches matter more than ordinary body matches.
    score += len(query["words"] & index["title_words"]) * 6
    score += len(query["words"] & index["content_words"]) * 2

    score += len(query["concepts"] & index["concepts"]) * 12

    return score


def score_section(question, section):

    return _score(
        _question_index(question),
        _section_index(section)
    )


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
    min_score_ratio=0.2
):
    """
    Select the verified knowledge worth paying to send.

    Three limits apply, strongest first:

    1. relevance   — a section far weaker than the best match
                     adds tokens without adding evidence
    2. section size — one enormous section cannot consume the
                     whole budget
    3. total size  — the combined context stays predictable
    """

    scored = []

    query = _question_index(question)

    for section in sections:
        score = _score(query, _section_index(section))

        if score > 0:
            scored.append((score, section))

    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    scored = scored[:limit]

    if scored:

        best_score = scored[0][0]

        threshold = best_score * min_score_ratio

        selected = [
            section
            for score, section in scored
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

        formatted_sections.append(
            f"""
SOURCE FILE: {section['source_file']}
SECTION: {section['title']}

{content}
""".strip()
        )

    return "\n\n---\n\n".join(formatted_sections)
