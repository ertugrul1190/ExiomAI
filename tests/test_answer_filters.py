import pytest

from answer_filters import drop_closing_offer, stream_without_closing_offer


SOURCE = "Source: [Official EXIOM Explorer](https://explorer.xeqmlabs.com/)"


@pytest.mark.parametrize("text, expected", [
    # A closing offer goes.
    (
        "953 nodes are running.\n\nIf you'd like, I can pull more detail.",
        "953 nodes are running.",
    ),
    # Before the source line too; the source stays.
    (
        f"953 nodes.\n\nIf you want, I can check again later.\n\n{SOURCE}",
        f"953 nodes.\n\n{SOURCE}",
    ),
    (
        "Answer.\n\nWould you like a quick example?",
        "Answer.",
    ),
    (
        "Answer.\n\nWant me to walk you through it?",
        "Answer.",
    ),
    # Content that merely starts like an offer stays.
    (
        "Yes.\n\nIf you want to join:\n- You need 10,000 XEQM.\n\n" + SOURCE,
        "Yes.\n\nIf you want to join:\n- You need 10,000 XEQM.\n\n" + SOURCE,
    ),
    # An offer followed by more content is not a closing one.
    (
        "A.\n\nIf you'd like, I can explain.\n\nB is next.",
        "A.\n\nIf you'd like, I can explain.\n\nB is next.",
    ),
    # Saying what it can't do is not an offer.
    (
        "No 24-hour total.\n\nIf you want live figures, I can't fetch them.",
        "No 24-hour total.\n\nIf you want live figures, I can't fetch them.",
    ),
    # Nothing to drop.
    ("Just an answer.", "Just an answer."),
    ("", ""),
    # An answer that is only an offer is left alone rather
    # than emptied.
    ("If you'd like, I can help?", "If you'd like, I can help?"),
])
def test_closing_offers_are_dropped(text, expected):
    assert drop_closing_offer(text) == expected


STREAMED = [
    "953 nodes are running.\n\nIf you'd like, I can pull more detail.",
    f"953 nodes.\n\nIf you want, I can check again later.\n\n{SOURCE}",
    "Yes.\n\nIf you want to join:\n- You need 10,000 XEQM.\n\n" + SOURCE,
    "A.\n\nIf you'd like, I can explain.\n\nB is next.",
    "Plain answer with no offer at all, streamed.",
    "Answer.\n\nIf",
    "If you'd like, I can help?",
]


@pytest.mark.parametrize("text", STREAMED)
def test_a_stream_gives_the_same_text_however_it_is_split(text):
    expected = drop_closing_offer(text)

    for cut in range(len(text) + 1):
        chunks = [text[:cut], text[cut:]]

        assert "".join(stream_without_closing_offer(chunks)) == expected

    one_char_chunks = list(text)

    assert "".join(stream_without_closing_offer(one_char_chunks)) == expected


def test_ordinary_text_is_not_held_back():
    chunks = ["953 nodes ", "are running ", "right now."]

    passed = []

    for piece in stream_without_closing_offer(iter(chunks)):
        passed.append(piece)

    # Each chunk goes out as it arrives.
    assert passed == chunks
