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

    return sections


def score_section(question, section):
    question_words = normalize_words(question)

    title_words = normalize_words(
        section["title"] + " " + section["parent"]
    )

    content_words = normalize_words(section["content"])

    title_matches = question_words.intersection(title_words)
    content_matches = question_words.intersection(content_words)

    score = 0

    # Heading matches matter more than ordinary body matches.
    score += len(title_matches) * 6
    score += len(content_matches) * 2

    question_lower = question.lower()
    content_lower = section["content"].lower()
    title_lower = section["title"].lower()

    # Give additional weight to important XEQM concepts.
    concept_groups = {
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

    for canonical_concept, variants in concept_groups.items():

        question_mentions_concept = any(
            variant in question_lower
            for variant in variants
        )

        if not question_mentions_concept:
            continue

        section_mentions_concept = (
            canonical_concept in title_lower
            or canonical_concept in content_lower
            or any(
                variant in title_lower or variant in content_lower
                for variant in variants
            )
        )

        if section_mentions_concept:
            score += 12

    return score


def retrieve_knowledge(question, sections, limit=8):
    scored = []

    for section in sections:
        score = score_section(question, section)

        if score > 0:
            scored.append((score, section))

    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    selected = [
        section
        for score, section in scored[:limit]
    ]

    if not selected:
        selected = sections[:4]

    formatted_sections = []

    for section in selected:
        formatted_sections.append(
            f"""
SOURCE FILE: {section['source_file']}
SECTION: {section['title']}

{section['content']}
""".strip()
        )

    return "\n\n---\n\n".join(formatted_sections)