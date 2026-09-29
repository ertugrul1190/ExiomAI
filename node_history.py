import re
import threading


# ---------------------------------------------------------
# REGISTERED NODES OVER THE LAST DAY
# ---------------------------------------------------------
#
# The Explorer shows how many nodes are registered now, and
# (on its node list) when each one registered. It keeps no
# record of nodes that left. So the count is sampled here,
# and a day later two facts can be worked out:
#
#   change    = registered now - registered a day ago
#   nodes left = new in the last 24 hours - change
#
# Until a day of samples exists, both facts say so in words:
# left out, the model filled the gap ("Removed: 0 nodes").
# ---------------------------------------------------------

DAY_SECONDS = 24 * 60 * 60

# One sample per this many seconds is plenty for a daily
# comparison.
SAMPLE_EVERY = 10 * 60

# A sample this far either side of "a day ago" still counts.
MATCH_WINDOW = 30 * 60

KEEP_SECONDS = DAY_SECONDS + 2 * MATCH_WINDOW

SOURCE = "Official EXIOM Explorer"

NOT_KNOWN_YET = (
    "not known yet (the Explorer keeps no history of this, and "
    "EXIOM AI started counting less than 24 hours ago)"
)

# A day of counts exists, but the new-node count is missing,
# a lower bound ("at least 100"), or disagrees with them.
NOT_KNOWN = (
    "not known right now (the Explorer keeps no history of this, "
    "and today's figures can't be matched up)"
)

CHANGE_FACT = (
    "node_count_change_24h",
    "Change in registered service nodes (last 24 hours)",
    "net change in the number of registered EXIOM service "
    "nodes compared with 24 hours ago",
)

LEFT_FACT = (
    "nodes_left_24h",
    "Service nodes that left (last 24 hours)",
    "EXIOM service nodes that were registered 24 hours ago and "
    "no longer are (unlocked or deregistered)",
)


def _count(fact):
    match = re.match(r"\s*([\d,]+)", str((fact or {}).get("value", "")))

    return int(match.group(1).replace(",", "")) if match else None


class NodeHistory:
    """
    Registered-node counts over the last day.

    `store` (optional) keeps samples across restarts: an
    object with load() -> [(time, count)], add(time, count)
    and drop_before(time). Without one they live in memory.
    """

    def __init__(self, store=None):
        self._store = store
        self._lock = threading.Lock()
        self.samples = sorted(store.load()) if store else []

    def _record(self, count, now):
        if self.samples and now - self.samples[-1][0] < SAMPLE_EVERY:
            return

        self.samples.append((now, count))

        cutoff = now - KEEP_SECONDS
        self.samples = [s for s in self.samples if s[0] >= cutoff]

        if self._store:
            self._store.add(now, count)
            self._store.drop_before(cutoff)

    def _count_a_day_ago(self, now):
        target = now - DAY_SECONDS

        nearest = min(
            self.samples,
            key=lambda sample: abs(sample[0] - target),
            default=None
        )

        if nearest and abs(nearest[0] - target) <= MATCH_WINDOW:
            return nearest[1]

        return None

    def add_facts(self, facts, now):
        """
        Record the current count, then set (or remove) the
        two change facts in `facts`, a registry dict.
        """

        facts.pop(CHANGE_FACT[0], None)
        facts.pop(LEFT_FACT[0], None)

        registered = _count(facts.get("registered_nodes"))

        if registered is None:
            return

        with self._lock:
            before = self._count_a_day_ago(now)
            self._record(registered, now)

        change = None if before is None else registered - before
        joined = _count(facts.get("nodes_registered_24h"))

        facts[CHANGE_FACT[0]] = _fact(
            *CHANGE_FACT,
            NOT_KNOWN_YET if change is None
            else f"{change:+,} (from {before:,} to {registered:,})",
        )

        left = (
            joined - change
            if change is not None and joined is not None
            else None
        )

        facts[LEFT_FACT[0]] = _fact(
            *LEFT_FACT,
            f"{left:,}" if left is not None and left >= 0
            else NOT_KNOWN_YET if change is None
            else NOT_KNOWN,
        )


def _fact(key, label, meaning, value):
    return {
        "key": key,
        "value": value,
        "label": label,
        "meaning": meaning,
        "unit": "",
        "dynamic": True,
        "source": SOURCE,
        "via": "history",
    }
