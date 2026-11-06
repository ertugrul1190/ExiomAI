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


# ---------------------------------------------------------
# PLAIN-TEXT SOURCES
# ---------------------------------------------------------
#
# "Sources: EXIOM Tokenomics Whitepaper; XEQM Core Releases"
# names official pages without linking them. In a source line,
# each known title becomes its link. Titles anywhere else, and
# titles already linked, are left alone.
#
# The streamed version gives exactly the same text. It holds
# back only a line that opens like a source line, until the
# line ends.
# ---------------------------------------------------------

_SOURCE_LINE = re.compile(r"\W{0,6}sources?\b", re.IGNORECASE)
_LINE_OPENING = re.compile(r"\W{0,6}")
_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")


def _is_source_line(line):
    return bool(_SOURCE_LINE.match(line))


def _could_be_source_line(line):
    rest = line[_LINE_OPENING.match(line).end():].lower()

    if not rest:
        return len(line) <= 6

    return "sources".startswith(rest) or rest.startswith("source")


def _title_pattern(titles):
    if not titles:
        return None

    return re.compile(
        r"(?<![\w\[])(" + "|".join(
            re.escape(title)
            for title in sorted(titles, key=len, reverse=True)
        ) + r")(?![\w\]])",
        re.IGNORECASE
    )


def _link_titles(line, titles, pattern):
    if pattern is None:
        return line

    def link(match):
        return f"[{match.group(1)}]({titles[match.group(1).lower()]})"

    # Only the text between existing links.
    parts = []
    last = 0

    for existing in _MARKDOWN_LINK.finditer(line):
        parts.append(pattern.sub(link, line[last:existing.start()]))
        parts.append(existing.group(0))
        last = existing.end()

    parts.append(pattern.sub(link, line[last:]))

    return "".join(parts)


def _link_line(line, titles, pattern):
    if _is_source_line(line):
        return _link_titles(line, titles, pattern)

    return line


def link_source_lines(text, titles):
    """
    The text with each known title in a source line linked.

    titles: lowercased title -> URL.
    """

    pattern = _title_pattern(titles)

    return "\n".join(
        _link_line(line, titles, pattern) for line in text.split("\n")
    )


def stream_linking_source_lines(chunks, titles):
    """
    Pass a stream through, giving in total exactly
    link_source_lines(the whole text, titles).
    """

    pattern = _title_pattern(titles)

    def finish(line):
        return _link_line(line, titles, pattern)

    text = ""
    sent = 0
    line_start = 0

    for chunk in chunks:
        text += chunk

        while True:
            end = text.find("\n", line_start)

            if end == -1:
                line = text[line_start:]

                # Undecided lines wait; others flow.
                if sent > line_start or not _could_be_source_line(line):
                    if len(text) > sent:
                        yield text[sent:]
                        sent = len(text)

                break

            if sent > line_start:
                yield text[sent:end + 1]

            else:
                yield finish(text[line_start:end]) + "\n"

            sent = line_start = end + 1

    if sent > line_start:
        if len(text) > sent:
            yield text[sent:]

    elif len(text) > line_start:
        yield finish(text[line_start:])
