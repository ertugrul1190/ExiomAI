import node_history
from node_history import NodeHistory


DAY = 24 * 60 * 60


def registry(registered, new_24h=None):
    facts = {
        "registered_nodes": {"key": "registered_nodes", "value": registered},
    }

    if new_24h is not None:
        facts["nodes_registered_24h"] = {
            "key": "nodes_registered_24h",
            "value": new_24h,
        }

    return facts


def test_before_a_day_has_been_seen_the_change_is_said_to_be_unknown():
    """
    Left out, the model filled the gap: "Removed: 0 nodes".
    """

    history = NodeHistory()
    facts = registry("954", "45")

    history.add_facts(facts, now=1000)

    for key in ("node_count_change_24h", "nodes_left_24h"):
        assert facts[key]["value"] == node_history.NOT_KNOWN_YET


def test_the_change_compares_with_the_count_a_day_ago():
    history = NodeHistory()
    history.add_facts(registry("951", "10"), now=1000)

    facts = registry("954", "45")
    history.add_facts(facts, now=1000 + DAY)

    assert facts["node_count_change_24h"]["value"] == "+3 (from 951 to 954)"
    assert facts["node_count_change_24h"]["source"] == "Official EXIOM Explorer"


def test_nodes_that_left_are_the_new_ones_minus_the_growth():
    history = NodeHistory()
    history.add_facts(registry("951"), now=1000)

    facts = registry("954", "45 (2 still awaiting contributions)")
    history.add_facts(facts, now=1000 + DAY)

    # 45 joined, the total grew by 3: 42 left.
    assert facts["nodes_left_24h"]["value"] == "42"


def test_a_shrinking_network_reads_as_a_negative_change():
    history = NodeHistory()
    history.add_facts(registry("1,000"), now=0)

    facts = registry("990", "0")
    history.add_facts(facts, now=DAY)

    assert facts["node_count_change_24h"]["value"] == "-10 (from 1,000 to 990)"
    assert facts["nodes_left_24h"]["value"] == "10"


def test_an_impossible_departure_count_is_said_to_be_unknown():
    history = NodeHistory()
    history.add_facts(registry("900"), now=0)

    # More growth than new nodes: the readings disagree.
    facts = registry("954", "5")
    history.add_facts(facts, now=DAY)

    assert facts["nodes_left_24h"]["value"] == node_history.NOT_KNOWN
    assert facts["node_count_change_24h"]["value"].startswith("+54")


def test_a_lower_bound_of_new_nodes_gives_no_departure_count():
    history = NodeHistory()
    history.add_facts(registry("900"), now=0)

    facts = registry("954", "at least 100")
    history.add_facts(facts, now=DAY)

    assert facts["nodes_left_24h"]["value"] == node_history.NOT_KNOWN


def test_a_sample_far_from_a_day_ago_is_not_used():
    history = NodeHistory()
    history.add_facts(registry("900"), now=0)

    # Two days later, with nothing recorded in between.
    facts = registry("954", "5")
    history.add_facts(facts, now=2 * DAY)

    assert facts["node_count_change_24h"]["value"] == node_history.NOT_KNOWN_YET


def test_samples_are_thinned_and_old_ones_dropped():
    history = NodeHistory()

    for minute in range(0, 3 * 24 * 60, 1):
        history.add_facts(registry("954"), now=minute * 60)

    times = [time for time, _ in history.samples]

    assert len(times) <= 26 * 60 * 60 // node_history.SAMPLE_EVERY + 2
    assert times[-1] - times[0] <= node_history.KEEP_SECONDS


def test_a_missing_registered_count_changes_nothing():
    history = NodeHistory()
    facts = {"active_nodes": {"value": "953"}}

    history.add_facts(facts, now=0)

    assert history.samples == []
    assert list(facts) == ["active_nodes"]


def test_samples_go_to_the_store_and_come_back():
    class Store:
        def __init__(self):
            self.rows = []

        def load(self):
            return list(self.rows)

        def add(self, time, count):
            self.rows.append((time, count))

        def drop_before(self, time):
            self.rows = [row for row in self.rows if row[0] >= time]

    store = Store()
    NodeHistory(store=store).add_facts(registry("951"), now=0)

    # A new object (an evicted Durable Object) reads them back.
    facts = registry("954", "3")
    NodeHistory(store=store).add_facts(facts, now=DAY)

    assert facts["node_count_change_24h"]["value"] == "+3 (from 951 to 954)"


def test_a_stale_change_fact_is_replaced_when_it_cannot_be_worked_out():
    history = NodeHistory()
    facts = registry("954", "3")
    facts["node_count_change_24h"] = {"value": "+99 (from 855 to 954)"}
    facts["nodes_left_24h"] = {"value": "0"}

    history.add_facts(facts, now=0)

    assert facts["node_count_change_24h"]["value"] == node_history.NOT_KNOWN_YET
    assert facts["nodes_left_24h"]["value"] == node_history.NOT_KNOWN_YET


def test_a_stale_change_fact_is_removed_without_a_registered_count():
    facts = {"nodes_left_24h": {"value": "0"}}

    NodeHistory().add_facts(facts, now=0)

    assert facts == {}
