# ---------------------------------------------------------
# USAGE LEDGER
# ---------------------------------------------------------
#
# Daily usage totals that outlive the process.
#
# CostMeter and UsageController are in memory and per worker
# (Task 10), so their numbers split across gunicorn workers
# and reset on every restart. That is fine for enforcing
# limits and useless for showing someone what the service
# costs. This ledger is the one place those totals add up:
# one SQLite file, shared by every worker, kept across
# restarts.
#
# Counters only, keyed by UTC day and route. No question,
# answer or client identity is ever written (Task 13).
#
# Accounting must never break an answer: every failure is
# logged once and swallowed.
# ---------------------------------------------------------

import sqlite3
import threading
import time


COUNTERS = (
    "calls",
    "free_responses",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "web_searches",
    "cost_usd",
)

# The names /api/usage already uses for the same counters.
PUBLIC_NAMES = {
    "calls": "provider_calls",
    "free_responses": "free_responses",
    "input_tokens": "input_tokens",
    "cached_input_tokens": "cached_input_tokens",
    "output_tokens": "output_tokens",
    "reasoning_tokens": "reasoning_tokens",
    "web_searches": "web_searches",
    "cost_usd": "estimated_cost_usd",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_daily (
    day TEXT NOT NULL,
    route TEXT NOT NULL,
    {counters},
    PRIMARY KEY (day, route)
)
""".format(
    counters=",\n    ".join(
        f"{name} {'REAL' if name == 'cost_usd' else 'INTEGER'} "
        "NOT NULL DEFAULT 0"
        for name in COUNTERS
    )
)

UPSERT = """
INSERT INTO usage_daily (day, route, {columns})
VALUES (?, ?, {placeholders})
ON CONFLICT (day, route) DO UPDATE SET {updates}
""".format(
    columns=", ".join(COUNTERS),
    placeholders=", ".join("?" for _ in COUNTERS),
    updates=", ".join(
        f"{name} = {name} + excluded.{name}"
        for name in COUNTERS
    ),
)

# A write waits at most this long for another worker's lock,
# so a busy file costs an answer a moment, never a hang.
LOCK_TIMEOUT_SECONDS = 1.0


def utc_day(timestamp):
    return time.strftime("%Y-%m-%d", time.gmtime(timestamp))


def zero_counters():
    return {name: 0 for name in COUNTERS}


def public_counters(counters):
    return {
        PUBLIC_NAMES[name]: value
        for name, value in counters.items()
    }


class UsageLedger:
    """
    Daily counters per route in one SQLite file.

    Stores counters only. No question text is ever kept.
    """

    def __init__(self, path, now=None):
        """
        path: the SQLite file. Empty or "off" disables it.
        """

        path = (path or "").strip()

        self.path = "" if path.lower() == "off" else path
        self._now = now or time.time
        self._ready = False
        self._failed = False
        self._lock = threading.Lock()


    @property
    def available(self):
        return bool(self.path) and self._ready and not self._failed


    @property
    def state(self):
        """
        "off", "available" or "unavailable", for /api/usage.
        """

        if not self.path:
            return "off"

        return "available" if self.available else "unavailable"


    def _connect(self):

        connection = sqlite3.connect(
            self.path,
            timeout=LOCK_TIMEOUT_SECONDS
        )

        if self._ready:
            return connection

        try:

            with self._lock:

                if not self._ready:

                    # WAL lets the page read while a worker
                    # writes. The mode is stored in the file.
                    connection.execute("PRAGMA journal_mode=WAL")
                    connection.execute(SCHEMA)
                    connection.commit()
                    self._ready = True

        except BaseException:
            connection.close()
            raise

        return connection


    def _set_failed(self, failed, error=None):
        """
        Log once per change of state, not per call.
        """

        with self._lock:

            changed = failed != self._failed
            self._failed = failed

        if changed and failed:
            print(
                "EXIOM usage ledger unavailable:",
                type(error).__name__,
                error
            )

        elif changed:
            print("EXIOM usage ledger recovered.")


    def record(
        self,
        route,
        calls=0,
        free_responses=0,
        input_tokens=0,
        cached_input_tokens=0,
        output_tokens=0,
        reasoning_tokens=0,
        web_searches=0,
        cost_usd=0.0
    ):

        if not self.path:
            return

        values = (
            calls,
            free_responses,
            input_tokens,
            cached_input_tokens,
            output_tokens,
            reasoning_tokens,
            web_searches,
            cost_usd,
        )

        try:

            connection = self._connect()

            try:
                with connection:
                    connection.execute(
                        UPSERT,
                        (utc_day(self._now()), str(route), *values)
                    )

            finally:
                connection.close()

        except (sqlite3.Error, OSError) as error:
            self._set_failed(True, error)
            return

        self._set_failed(False)


    def daily(self, days=30):
        """
        Totals per UTC day, newest first, for the `days`
        calendar days ending today. Days without use are left
        out.
        """

        if not self.path:
            return []

        try:

            connection = self._connect()

            try:
                rows = connection.execute(
                    f"""
                    SELECT day, route, {", ".join(COUNTERS)}
                    FROM usage_daily
                    WHERE day >= ?
                    ORDER BY day DESC, route
                    """,
                    (
                        utc_day(
                            self._now() - (max(1, int(days)) - 1) * 86400
                        ),
                    )
                ).fetchall()

            finally:
                connection.close()

        except (sqlite3.Error, OSError) as error:
            self._set_failed(True, error)
            return []

        result = []

        for day, route, *counters in rows:

            totals = dict(zip(COUNTERS, counters))

            if not result or result[-1]["day"] != day:
                result.append({
                    "day": day,
                    **public_counters(zero_counters()),
                    "by_route": {}
                })

            entry = result[-1]

            for name, value in totals.items():
                entry[PUBLIC_NAMES[name]] += value

            entry["by_route"][route] = public_counters(totals)

        for entry in result:
            entry["estimated_cost_usd"] = round(
                entry["estimated_cost_usd"],
                6
            )

            for totals in entry["by_route"].values():
                totals["estimated_cost_usd"] = round(
                    totals["estimated_cost_usd"],
                    6
                )

        return result

