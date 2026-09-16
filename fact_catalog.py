# ---------------------------------------------------------
# EXPLORER FACT HELPERS
# ---------------------------------------------------------
#
# Semantic interpretation is now handled by the AI router.
#
# This file no longer tries to understand English using
# keywords, synonyms, scoring, or explanation detection.
#
# Its job is only to safely select Explorer facts AFTER the
# semantic router has decided which facts are needed.
# ---------------------------------------------------------


def get_selected_facts(
    fact_keys,
    fact_registry=None
):
    """
    Return only the Explorer facts explicitly selected by
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


def format_fact_answer(fact):
    """
    Format one simple Explorer fact for a direct response.
    """

    if not fact:
        return None

    label = fact.get(
        "label",
        "Explorer value"
    )

    value = fact.get(
        "value",
        ""
    )

    unit = fact.get(
        "unit",
        ""
    )

    if not value:
        return None

    if unit:
        value_text = f"{value} {unit}"
    else:
        value_text = str(value)

    return f"{label}: {value_text}."


def answer_selected_direct_fact(
    fact_keys,
    fact_registry=None
):
    """
    Give a $0 local response ONLY when the AI semantic router
    explicitly decided that the question is a direct live
    fact request and selected exactly one Explorer fact.

    If multiple facts are needed, app.py should let EXIOM AI
    compose the answer naturally.
    """

    selected = get_selected_facts(
        fact_keys,
        fact_registry
    )

    if len(selected) != 1:
        return None

    fact = next(
        iter(selected.values())
    )

    return format_fact_answer(
        fact
    )