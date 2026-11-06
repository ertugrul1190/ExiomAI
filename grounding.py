import re
from decimal import Decimal, InvalidOperation


# ---------------------------------------------------------
# GROUNDING CHECK
# ---------------------------------------------------------
#
# Every number in an answer (amounts, percentages, days,
# prices) that appears nowhere in what the model was given:
# knowledge, Explorer values, market data, the question. A
# monitor, not a filter: live_eval.py counts them per answer
# and app.py logs the count. See "Task Docs/Answer Quality
# and Image Upload.md", 2.7.
#
# Forms are normalised (100k = 1.5M = 100,000 = 100000; a
# lowercase "30m" is minutes, not millions) and signs dropped
# (-8.2% = 8.2). Single-digit integers ("step 1",
# "1-2 sentences") and versions ("v1.1.2") are not counted:
# they are everywhere and almost never a claim.
# ---------------------------------------------------------

NUMBER = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\d.]*\d)"
    r"(?:(k|(?-i:M))\b|\s?(thousand|million|billion)\b)?",
    re.IGNORECASE
)

MULTIPLIERS = {
    "k": 1000, "thousand": 1000,
    "m": 1000000, "million": 1000000,
    "billion": 1000000000,
}


def _values(text):
    """
    (value, decimal places as written) for each number.
    """

    for match in NUMBER.finditer(text or ""):

        whole, fraction, short, word = match.groups()

        try:
            value = Decimal(whole.replace(",", "") + (fraction or ""))

        except InvalidOperation:
            continue

        suffix = (short or word or "").lower()

        if suffix:
            value *= MULTIPLIERS[suffix]

        places = 0 if suffix else len(fraction or ".") - 1

        if places == 0 and value < 10:
            continue

        yield value, places


def _text(value):
    return format(value.normalize(), "f")


def numbers(text):
    """
    The normalised numbers in a text, as strings.
    """

    return {_text(value) for value, _ in _values(text)}


def unsupported_numbers(answer, context, question=""):
    """
    The answer's numbers that the context lacks, once each,
    in order. A rounded figure is supported: "$0.0203" for
    a supplied "$0.02029". So is the sum or difference of an
    amount in the question and a supplied figure: "the other
    80,000" for "120k" and a 200,000 stake.
    """

    supplied = {value for value, _ in _values(context)}
    asked = {value for value, _ in _values(question)}

    known = supplied | asked | {
        result
        for mine in asked
        for other in supplied
        for result in (mine + other, abs(mine - other))
    }
    found = []

    for value, places in _values(answer):

        supported = value in known or (
            places > 0 and any(
                round(other, places) == value
                for other in known
                if other.as_tuple().exponent < -places
            )
        )

        if not supported and _text(value) not in found:
            found.append(_text(value))

    return found
