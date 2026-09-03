from fact_catalog import find_requested_fact, needs_explanation


def classify_question(question):
    requested_fact = find_requested_fact(question)

    if requested_fact is None:
        return {
            "route": "ai",
            "fact": None
        }

    if needs_explanation(question):
        return {
            "route": "ai_with_live",
            "fact": requested_fact
        }

    return {
        "route": "direct_fact",
        "fact": requested_fact
    }