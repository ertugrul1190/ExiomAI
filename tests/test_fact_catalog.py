import fact_catalog


def test_a_breakdown_answer_is_a_list():
    fact = {
        "label": "Service nodes by country",
        "value": "France: 323\nTurkey: 34",
        "unit": "",
    }

    assert fact_catalog.format_fact_answer(fact) == (
        "**Service nodes by country:**\n\n"
        "- France: 323\n"
        "- Turkey: 34"
    )


def test_a_single_value_answer_is_one_line():
    fact = {"label": "Active nodes", "value": "921", "unit": ""}

    assert fact_catalog.format_fact_answer(fact) == "Active nodes: 921."


def test_a_breakdown_in_a_snapshot_stays_on_its_line():
    selected = {
        "active_nodes": {"label": "Active nodes", "value": "921"},
        "nodes_by_country": {
            "label": "Service nodes by country",
            "value": "France: 323\nTurkey: 34",
        },
    }

    answer = fact_catalog.format_multiple_fact_answer(selected)

    assert "- **Service nodes by country:** France: 323, Turkey: 34" in answer
