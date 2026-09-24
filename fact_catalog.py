# ---------------------------------------------------------
# EXPLORER FACT HELPERS
# ---------------------------------------------------------
#
# Semantic interpretation is handled by the AI router.
#
# This file does not interpret user language.
# It safely selects and formats Explorer facts AFTER the
# semantic router decides which facts are required.
# ---------------------------------------------------------


def get_selected_facts(
    fact_keys,
    fact_registry=None
):
    """
    Return only Explorer facts explicitly selected by
    the semantic AI router.
    """

    if not fact_registry:
        return {}

    if not isinstance(fact_keys, list):
        return {}

    selected = {}

    for fact_key in fact_keys:

        if fact_key not in fact_registry:
            continue

        selected[fact_key] = fact_registry[fact_key]

    return selected


def get_fact(
    fact_key,
    fact_registry=None
):
    """
    Return one Explorer fact by its exact registry key.
    """

    if not fact_registry:
        return None

    return fact_registry.get(fact_key)


def format_fact_value(fact):
    """
    Format the value of one Explorer fact.
    """

    if not fact:
        return None

    value = fact.get(
        "value",
        ""
    )

    unit = fact.get(
        "unit",
        ""
    )

    if value is None or value == "":
        return None

    if unit:
        return f"{value} {unit}"

    return str(value)


def format_fact_answer(fact):
    """
    Format one Explorer fact for a direct response.
    """

    if not fact:
        return None

    label = fact.get(
        "label",
        "Explorer value"
    )

    value_text = format_fact_value(
        fact
    )

    if not value_text:
        return None

    # A breakdown (one entry per line) reads as a list.
    if "\n" in value_text:
        items = "\n".join(
            f"- {line}" for line in value_text.splitlines()
        )

        return f"**{label}:**\n\n{items}"

    return f"{label}: {value_text}."


def format_multiple_fact_answer(selected):
    """
    Format multiple Explorer facts as a compact
    live-network snapshot.
    """

    if not selected:
        return None

    lines = []

    for fact in selected.values():

        label = fact.get(
            "label",
            "Explorer value"
        )

        value_text = format_fact_value(
            fact
        )

        if not value_text:
            continue

        # A snapshot line holds one value, so a breakdown is
        # folded onto it.
        value_text = ", ".join(value_text.splitlines())

        lines.append(
            f"- **{label}:** {value_text}"
        )

    if not lines:
        return None

    return (
        "**Current EXIOM network snapshot:**\n\n"
        + "\n".join(lines)
    )


def answer_selected_direct_fact(
    fact_keys,
    fact_registry=None
):
    """
    Give a local response when the semantic router has
    selected verified Explorer facts.

    One selected fact:
    return a simple direct answer.

    Multiple selected facts:
    return a compact live-network snapshot.
    """

    selected = get_selected_facts(
        fact_keys,
        fact_registry
    )

    if not selected:
        return None

    if len(selected) == 1:

        fact = next(
            iter(selected.values())
        )

        return format_fact_answer(
            fact
        )

    return format_multiple_fact_answer(
        selected
    )