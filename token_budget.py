# ---------------------------------------------------------
# TOKEN BUDGET HELPERS
# ---------------------------------------------------------
#
# Every token sent to the AI provider costs money.
#
# This file contains the small, pure helpers used to keep
# prompt payloads inside a predictable size, without
# silently destroying the meaning of what is sent.
#
# Nothing here performs semantic interpretation.
# ---------------------------------------------------------

import json


# Rough provider-agnostic approximation.
# Used only for budgeting and reporting, never for billing.
CHARS_PER_TOKEN = 4


def estimate_tokens(text):
    """
    Approximate the number of tokens in a piece of text.
    """

    if not text:
        return 0

    return max(
        1,
        len(str(text)) // CHARS_PER_TOKEN
    )


def clip_text(text, max_chars):
    """
    Shorten text to max_chars, preferring a word boundary.
    """

    if not text:
        return ""

    text = str(text)

    if max_chars <= 0:
        return ""

    if len(text) <= max_chars:
        return text

    cut = text[:max_chars]

    boundary = cut.rfind(" ")

    # Only respect the word boundary when it keeps most of
    # the allowed text. Otherwise a long unbroken string
    # would collapse to almost nothing.
    if boundary > max_chars * 0.6:
        cut = cut[:boundary]

    return cut.rstrip() + "…"


def trim_conversation(
    conversation,
    max_messages=8,
    max_chars_per_message=1200,
    total_char_budget=6000
):
    """
    Keep the most recent usable conversation turns inside a
    predictable character budget.

    Newest turns are the most useful ones, so they are kept
    first and older turns are dropped.
    """

    if not isinstance(conversation, list):
        return []

    kept = []
    used = 0

    for message in reversed(conversation):

        if len(kept) >= max_messages:
            break

        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content")

        if role not in {"user", "assistant"}:
            continue

        if not isinstance(content, str) or not content.strip():
            continue

        content = clip_text(
            content.strip(),
            max_chars_per_message
        )

        remaining = total_char_budget - used

        if remaining <= 0:
            break

        if len(content) > remaining:

            # The newest turn is always worth keeping, even
            # when it has to be shortened further.
            if kept:
                break

            content = clip_text(
                content,
                remaining
            )

        used += len(content)

        kept.append({
            "role": role,
            "content": content
        })

    kept.reverse()

    return kept


def compact_json(value):
    """
    Serialise JSON without decorative whitespace.

    Indented JSON is easier for humans to read but costs
    noticeably more tokens for identical meaning.
    """

    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True
    )
