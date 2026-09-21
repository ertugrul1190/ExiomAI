import token_budget as tb


def test_clip_text_keeps_short_text_untouched():
    assert tb.clip_text("hello", 10) == "hello"


def test_clip_text_cuts_on_word_boundary():
    clipped = tb.clip_text("alpha beta gamma delta", 16)

    assert clipped.endswith("…")
    assert "gamma" not in clipped or clipped.startswith("alpha beta")


def test_clip_text_handles_unbreakable_text():
    clipped = tb.clip_text("x" * 100, 10)

    assert len(clipped) == 11


def test_clip_text_handles_empty_and_zero():
    assert tb.clip_text("", 10) == ""
    assert tb.clip_text("hello", 0) == ""


def test_trim_conversation_keeps_newest_messages():
    conversation = [
        {"role": "user", "content": f"message {index}"}
        for index in range(20)
    ]

    trimmed = tb.trim_conversation(
        conversation,
        max_messages=3,
        max_chars_per_message=100,
        total_char_budget=1000
    )

    assert len(trimmed) == 3
    assert trimmed[-1]["content"] == "message 19"
    assert trimmed[0]["content"] == "message 17"


def test_trim_conversation_respects_total_budget():
    conversation = [
        {"role": "user", "content": "a" * 100},
        {"role": "assistant", "content": "b" * 100},
    ]

    trimmed = tb.trim_conversation(
        conversation,
        max_messages=8,
        max_chars_per_message=100,
        total_char_budget=120
    )

    assert len(trimmed) == 1
    assert trimmed[0]["role"] == "assistant"


def test_trim_conversation_always_keeps_newest_turn():
    conversation = [
        {"role": "user", "content": "a" * 500},
    ]

    trimmed = tb.trim_conversation(
        conversation,
        max_messages=8,
        max_chars_per_message=500,
        total_char_budget=50
    )

    assert len(trimmed) == 1
    assert len(trimmed[0]["content"]) <= 51


def test_trim_conversation_rejects_malformed_entries():
    conversation = [
        "not a dict",
        {"role": "system", "content": "ignore me"},
        {"role": "user", "content": "   "},
        {"role": "user", "content": 42},
        {"role": "user", "content": "real question"},
    ]

    trimmed = tb.trim_conversation(conversation)

    assert trimmed == [
        {"role": "user", "content": "real question"}
    ]


def test_trim_conversation_rejects_non_list():
    assert tb.trim_conversation(None) == []
    assert tb.trim_conversation("nope") == []


def test_compact_json_has_no_decorative_whitespace():
    assert tb.compact_json({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'


def test_estimate_tokens_scales_with_length():
    assert tb.estimate_tokens("") == 0
    assert tb.estimate_tokens("a" * 400) == 100
