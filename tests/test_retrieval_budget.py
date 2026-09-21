import retrieval


def make_sections(count=12, size=4000):
    return [
        {
            "source_file": "core.md",
            "parent": "EXIOM",
            "title": f"Staking topic {index}",
            "content": ("staking rewards line\n" * (size // 20))
        }
        for index in range(count)
    ]


def test_retrieval_stays_inside_the_character_budget():
    knowledge = retrieval.retrieve_knowledge(
        "what is staking",
        make_sections(),
        limit=6,
        char_budget=3000
    )

    assert 0 < len(knowledge) < 4000


def test_oversized_sections_are_truncated_and_marked():
    knowledge = retrieval.retrieve_knowledge(
        "what is staking",
        make_sections(count=1),
        max_section_chars=500
    )

    assert "[section truncated]" in knowledge


def test_weak_matches_are_dropped():
    sections = [
        {
            "source_file": "core.md",
            "parent": "",
            "title": "Staking",
            "content": "staking staking staking rewards"
        },
        {
            "source_file": "core.md",
            "parent": "",
            "title": "Unrelated",
            "content": "lokinet routing details"
        },
    ]

    knowledge = retrieval.retrieve_knowledge(
        "what is staking",
        sections
    )

    assert "Staking" in knowledge
    assert "lokinet routing" not in knowledge


def test_unmatched_question_falls_back_to_a_small_slice():
    sections = make_sections(count=12, size=800)

    knowledge = retrieval.retrieve_knowledge(
        "zzzz qqqq",
        sections
    )

    assert knowledge.count("SOURCE FILE:") <= 3


def test_no_sections_returns_empty_context():
    assert retrieval.retrieve_knowledge("anything", []) == ""


def test_real_knowledge_base_stays_affordable():
    documents = retrieval.load_knowledge_directory("knowledge")
    sections = retrieval.build_knowledge_sections(documents)

    for question in [
        "what is staking",
        "how does the oracle work",
        "tell me about governance and the treasury",
    ]:
        knowledge = retrieval.retrieve_knowledge(question, sections)

        assert len(knowledge) <= 7000
