# ---------------------------------------------------------
# USAGE HUB (Cloudflare Workers)
# ---------------------------------------------------------
#
# On Workers, Cloudflare runs as many copies of the app as
# traffic needs and recycles them freely, so the in-memory
# limits of Tasks 10-12 would multiply with the copies and
# reset with them. This hub holds them once for everyone: it
# runs inside one Durable Object (cloudflare/worker.py), the
# way the single gunicorn process holds them on Railway.
#
# It is plain Python and reuses the same classes, so the
# limits behave exactly as they do under gunicorn. Copies
# reach it through remote_usage.py.
#
# The ledger lives in the object's SQL storage and survives
# the object being evicted. On start, today's global token
# and web-search totals are read back from it, so the daily
# spend ceilings survive too. Per-client counters restart,
# which only ever hands a client a fresh allowance (as
# UsageController's own eviction does).
#
# It also keeps the Cron Trigger's latest Explorer reading
# (share_live_readings in remote_usage.py).
# ---------------------------------------------------------

import json
import sqlite3

import security
from usage_control import CostMeter, UsageController, _env_int
from usage_ledger import SCHEMA, UsageLedger, utc_day


class _Rows:
    """
    A query's result rows, as sqlite3's cursor hands them out.
    """

    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Connection:
    """
    The slice of sqlite3.Connection UsageLedger uses, over
    the Durable Object's storage. Storage errors surface as
    sqlite3.Error so the ledger handles them as it always has.
    """

    def __init__(self, sql):
        self._sql = sql

    def execute(self, query, params=()):
        try:
            return _Rows(self._sql(query, tuple(params)))

        except Exception as error:
            raise sqlite3.Error(str(error)) from error

    def commit(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class DurableLedger(UsageLedger):
    """
    UsageLedger over storage that is already transactional
    and single-writer: no file, no WAL, no lock timeout.
    """

    def __init__(self, sql, now=None):
        super().__init__("durable-object", now=now)
        self._sql = sql

    def _connect(self):
        connection = _Connection(self._sql)

        if not self._ready:
            connection.execute(SCHEMA)
            self._ready = True

        return connection


# An answer runs for well under a minute. A slot still held
# after this was never released: its copy was recycled or
# killed mid-stream, which gunicorn's WSGI close() guarantee
# does not cover on Workers.
ANSWER_LEASE_SECONDS = 300


class LeasedAnswerSlots:
    """
    security.AnswerSlots, but each slot expires after
    ANSWER_LEASE_SECONDS, so a lost release can never lock a
    client out.
    """

    def __init__(self, per_client, now):

        self.per_client = max(1, per_client)
        self._now = now

        # client -> acquisition times, oldest first
        self._leases = {}


    def acquire(self, client_id):

        now = self._now()

        leases = [
            started
            for started in self._leases.get(client_id, [])
            if now - started < ANSWER_LEASE_SECONDS
        ]

        if len(leases) >= self.per_client:
            self._leases[client_id] = leases
            return False

        self._leases[client_id] = leases + [now]

        return True


    def release(self, client_id):

        leases = self._leases.get(client_id, [])[1:]

        if leases:
            self._leases[client_id] = leases

        else:
            self._leases.pop(client_id, None)


class UsageHub:
    """
    Every copy's limits, counters and Explorer reading, in the
    one Durable Object. Requests arrive as JSON through call().
    """

    # What a copy may ask for. Anything else is refused.
    OPERATIONS = {
        "flood_allow",
        "slot_acquire",
        "slot_release",
        "check",
        "record_tokens",
        "claim_web_search",
        "control_snapshot",
        "record_usage",
        "record_free_response",
        "record_web_searches",
        "cost_snapshot",
        "ledger_daily",
        "put_reading",
        "get_reading",
    }

    def __init__(self, sql, now=None):

        self._sql = sql
        self.ledger = DurableLedger(sql, now=now)
        self.cost_meter = CostMeter(ledger=self.ledger)
        self.usage_controller = UsageController(now=now)

        # Same settings as app.py.
        self.flood_guard = security.FloodGuard(
            requests_per_minute=_env_int(
                "EXIOM_FLOOD_REQUESTS_PER_MINUTE",
                120
            ),
            max_clients=_env_int("EXIOM_MAX_TRACKED_CLIENTS", 50_000)
        )

        self.answer_slots = LeasedAnswerSlots(
            per_client=_env_int("EXIOM_MAX_CONCURRENT_ANSWERS", 4),
            now=self.usage_controller._now
        )

        self.reading = None

        self._restored = False
        self._restore_today()


    def _restore_today(self):
        """
        Carry today's global totals over an eviction. Until
        the ledger has been read, check() refuses paid work:
        starting the daily ceilings from zero would not be safe.
        """

        try:
            self._sql(SCHEMA, ())

            [(tokens, web_searches)] = self._sql(
                """
                SELECT COALESCE(SUM(input_tokens + output_tokens), 0),
                       COALESCE(SUM(web_searches), 0)
                FROM usage_daily
                WHERE day = ?
                """,
                (utc_day(self.ledger._now()),)
            )

        except Exception as error:
            print("EXIOM usage hub could not restore today:", error)
            return

        self.usage_controller.restore_today(tokens, web_searches)
        self._restored = True


    def call(self, message):
        """
        One JSON request {"op", "args"} in, one JSON result out.
        """

        request = json.loads(message)
        op = request.get("op")

        if op not in self.OPERATIONS:
            raise ValueError(f"Unknown usage operation: {op!r}")

        if not self._restored:
            self._restore_today()

        return json.dumps(getattr(self, op)(**request.get("args", {})))


    def flood_allow(self, client):
        return list(self.flood_guard.allow(client))

    def slot_acquire(self, client):
        return self.answer_slots.acquire(client)

    def slot_release(self, client):
        self.answer_slots.release(client)

    def check(self, client):
        if not self._restored:
            return {
                "allowed": False,
                "reason": "global_usage_unavailable",
                "retry_after": 60,
            }

        decision = self.usage_controller.check(client)
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "retry_after": decision.retry_after,
        }

    def record_tokens(self, client, tokens):
        # The global total is counted in record_usage, from the
        # provider's own numbers: a copy interleaves requests
        # and could charge a call to the wrong client, but the
        # global ceiling stays exact.
        self.usage_controller.record_tokens(client, tokens, count_global=False)

    def claim_web_search(self, client):
        return self.usage_controller.claim_web_search(client)

    def control_snapshot(self):
        return self.usage_controller.snapshot()

    def record_usage(self, model, usage, route):
        charged = self.cost_meter.record_usage(model, usage, route)

        self.usage_controller.record_global_tokens(
            charged["input_tokens"] + charged["output_tokens"]
        )

        return charged

    def record_free_response(self, route):
        self.cost_meter.record_free_response(route)

    def record_web_searches(self, count, route):
        self.cost_meter.record_web_searches(count, route)

    def cost_snapshot(self):
        return self.cost_meter.snapshot()

    def ledger_daily(self, days):
        return {
            "daily": self.ledger.daily(days=days),
            "state": self.ledger.state,
        }


    def put_reading(self, item):
        """
        Keep the newest Explorer reading, except that a failed
        fetch never replaces a good reading still in its window
        (the rule LiveData._refresh_locked follows in-process).
        """

        current = self.reading

        if (
            current is not None
            and item["data"].get("status") != "available"
            and current["data"].get("status") == "available"
            and item["time"] - current["time"] <= current["ttl"]
        ):
            return

        self.reading = item

    def get_reading(self):
        return self.reading
