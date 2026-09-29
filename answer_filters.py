import re


# ---------------------------------------------------------
# CLOSING OFFERS
# ---------------------------------------------------------
#
# A small model often ends with an offer ("If you'd like, I
# can pull the block list...") that promises things EXIOM AI
# cannot do, whatever the prompt says. A closing paragraph
# like that is dropped; source lines after it stay.
#
# The streamed version gives exactly the same text. It holds
# back only a paragraph that opens like an offer, and only
# until it is known not to close the answer.
# ---------------------------------------------------------

_OFFER_OPENINGS = (
    "if you'd like",
    "if you’d like",
    "if you would like",
    "if you want",
    "if you prefer",
    "want me to",
    "would you like",
    "let me know if",
    "i can also",
    "happy to",
)

# An offer promises something, or asks.
_OFFER_PROMISE = re.compile(
    r"\b(i can(?!['’]t|not)|i could|i'll|i’ll|i will|me to)\b"
    r"|\?\s*\S{0,3}\s*$",
    re.IGNORECASE
)

_PARAGRAPH_BREAK = "\n\n"


def _opening(paragraph):
    return paragraph.strip().lower()


def _is_offer(paragraph):
    opening = _opening(paragraph)

    return (
        opening.startswith(_OFFER_OPENINGS)
        and bool(_OFFER_PROMISE.search(paragraph))
    )


def _could_become_offer(opening):
    return any(
        prefix.startswith(opening) or opening.startswith(prefix)
        for prefix in _OFFER_OPENINGS
    )


def _is_source(paragraph):
    return _opening(paragraph).startswith(("source", "(source"))


def drop_closing_offer(text):
    """
    The text without a closing offer paragraph.
    """

    paragraphs = text.split(_PARAGRAPH_BREAK)

    # Walk back over trailing source lines to the last real
    # paragraph.
    index = len(paragraphs) - 1

    while index > 0 and (
        _is_source(paragraphs[index]) or not paragraphs[index].strip()
    ):
        index -= 1

    # Never empty an answer that is only an offer.
    if index > 0 and _is_offer(paragraphs[index]):
        del paragraphs[index]

    return _PARAGRAPH_BREAK.join(paragraphs)


def _held_from(text):
    """
    Where the text that may still be dropped starts, or None.
    """

    paragraphs = text.split(_PARAGRAPH_BREAK)
    start = 0

    for index, paragraph in enumerate(paragraphs):

        last = index == len(paragraphs) - 1

        candidate = index > 0 and (
            _could_become_offer(_opening(paragraph))
            if last else _is_offer(paragraph)
        )

        if candidate:
            rest = paragraphs[index + 1:]

            # It closes the answer unless real content follows.
            if all(_is_source(p) or not p.strip() for p in rest[:-1]) and (
                not rest
                or _is_source(rest[-1])
                or _could_become_source(rest[-1])
            ):
                # With the break before it, which goes too.
                return start - len(_PARAGRAPH_BREAK)

        start += len(paragraph) + len(_PARAGRAPH_BREAK)

    return None


def _could_become_source(paragraph):
    opening = _opening(paragraph)

    return not opening or any(
        prefix.startswith(opening) or opening.startswith(prefix)
        for prefix in ("source", "(source")
    )


def stream_without_closing_offer(chunks):
    """
    Pass a stream through, giving in total exactly
    drop_closing_offer(the whole text).
    """

    text = ""
    sent = 0

    for chunk in chunks:
        text += chunk

        held = _held_from(text)
        safe = len(text) if held is None else held

        # A paragraph break may still be completing: keep a
        # trailing newline until the next character decides.
        if held is None and text.endswith("\n"):
            safe = len(text.rstrip("\n"))

        if safe > sent:
            yield text[sent:safe]
            sent = safe

    final = drop_closing_offer(text)

    if len(final) > sent:
        yield final[sent:]
