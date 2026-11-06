"""
The anti-hallucination monitor: numbers in an answer that
nothing supplied to the model contains. See "Task Docs/
Answer Quality and Image Upload.md", 2.7.
"""

import pytest

import grounding


@pytest.mark.parametrize("text, value", [
    ("stake 100k", "100000"),
    ("stake 100,000 XEQM", "100000"),
    ("stake 100000", "100000"),
    ("1.5M coins", "1500000"),
    ("a 30m outage", "30"),
    ("about 2.3% a year", "2.3"),
    ("$0.020293 on NonKYC", "0.020293"),
    ("down -8.2% today", "8.2"),
    ("a 14-day unlock", "14"),
    ("total is 200,000.", "200000"),
])
def test_number_forms_are_normalised(text, value):
    assert value in grounding.numbers(text)


@pytest.mark.parametrize("text", [
    "run v1.1.2 or newer",
    "step 1, then 2",
    "wait 5m",
    "no numbers here",
])
def test_versions_and_single_digits_are_not_counted(text):
    assert grounding.numbers(text) == set()


def test_supported_numbers_pass_in_any_form():
    context = "The operator stakes at least 100,000 XEQM; 10 contributors."

    assert grounding.unsupported_numbers(
        "Operators need 100k, and up to 10 contributors join.", context
    ) == []


def test_invented_numbers_are_returned_once_in_order():
    context = "Minimum contribution: 10,000 XEQM."

    assert grounding.unsupported_numbers(
        "You need 25,000 XEQM, or 50k, or 25,000 again; 10,000 is fine.",
        context
    ) == ["25000", "50000"]


def test_arithmetic_on_the_users_own_amount_is_supported():
    context = "A node needs 200,000 XEQM."

    assert grounding.unsupported_numbers(
        "Contributors bring the other 80,000.", context, "run a node with 120k"
    ) == []
    assert grounding.unsupported_numbers(
        "Contributors bring the other 80,000.", context
    ) == ["80000"]


def test_a_rounded_price_is_supported():
    context = "- Price: $0.02029 (USD)\n- 24h change: -8.2%"

    assert grounding.unsupported_numbers(
        "XEQM is about $0.0203, down 8.2%.", context
    ) == []
    assert grounding.unsupported_numbers("It is $0.0196.", context) == ["0.0196"]
