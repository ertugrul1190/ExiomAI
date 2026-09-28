# ---------------------------------------------------------
# REMOTE USAGE (Cloudflare Workers)
# ---------------------------------------------------------
#
# Stand-ins for app.py's flood_guard, answer_slots,
# usage_controller, cost_meter and usage_ledger, with the
# same methods, that ask the one UsageHub (usage_hub.py)
# instead of keeping per-copy counters. cloudflare/worker.py
# installs them after importing app.
#
# `call(op, args)` sends one request to the hub and returns
# its JSON result. When it fails, each method errs towards
# spending less: paid work is refused, free routes and
# bookkeeping carry on (accounting must never break a
# response).
# ---------------------------------------------------------

from contextvars import ContextVar

from security import redact_secrets
from usage_control import CostMeter, UsageDecision


def _log_failure(op, error):
    print(
        "EXIOM usage hub unreachable:",
        op,
        type(error).__name__,
        redact_secrets(str(error))
    )


class _Remote:
    """
    One hub operation per method; `fallback` when the hub
    cannot answer.
    """

    def __init__(self, call):
        self._call = call

    def _ask(self, fallback, op, **args):
        try:
            return self._call(op, args)

        except Exception as error:
            _log_failure(op, error)
            return fallback


class RemoteFloodGuard(_Remote):

    def allow(self, client_id):
        allowed, retry_after = self._ask([True, 0], "flood_allow", client=client_id)
        return bool(allowed), int(retry_after)


class RemoteAnswerSlots(_Remote):

    def acquire(self, client_id):
        return bool(self._ask(True, "slot_acquire", client=client_id))

    def release(self, client_id):
        self._ask(None, "slot_release", client=client_id)


class RemoteUsageController(_Remote):

    # Without the hub no limit can be checked, so no paid
    # work starts. "global" selects the capacity message.
    UNAVAILABLE = {
        "allowed": False,
        "reason": "global_usage_unavailable",
        "retry_after": 60,
    }

    def check(self, client_id):
        decision = self._ask(self.UNAVAILABLE, "check", client=client_id)
        return UsageDecision(
            decision["allowed"],
            decision["reason"],
            decision["retry_after"]
        )

    def record_tokens(self, client_id, tokens):
        self._ask(None, "record_tokens", client=client_id, tokens=tokens)

    def claim_web_search(self, client_id):
        return bool(self._ask(False, "claim_web_search", client=client_id))

    def snapshot(self):
        return self._ask({}, "control_snapshot")


class RemoteCostMeter(_Remote):
    """
    Charges are worked out here, where the provider's usage
    object is, and sent to the hub as plain numbers.
    """

    def __init__(self, call):
        super().__init__(call)
        self._local = CostMeter()

    def record_usage(self, model, usage, route="unknown"):
        charged = self._local.record_usage(model, usage, route)

        self._ask(
            None,
            "record_usage",
            model=model,
            usage={
                "input_tokens": charged["input_tokens"],
                "output_tokens": charged["output_tokens"],
                "input_tokens_details": {
                    "cached_tokens": charged["cached_input_tokens"]
                },
                "output_tokens_details": {
                    "reasoning_tokens": charged["reasoning_tokens"]
                },
            },
            route=route
        )

        return charged

    def record_free_response(self, route="deterministic"):
        self._ask(None, "record_free_response", route=route)

    def record_web_searches(self, count, route="unknown"):
        # Most calls run no search: no round trip for nothing.
        if not count:
            return

        self._ask(None, "record_web_searches", count=count, route=route)

    def snapshot(self):
        return self._ask({}, "cost_snapshot")


class RemoteLedger(_Remote):
    """
    Read side of the ledger for /api/usage; writes go through
    RemoteCostMeter. app.py reads `daily` then `state`, so the
    state of the last read is kept for the second.
    """

    def __init__(self, call):
        super().__init__(call)
        self._state = "unavailable"

    def daily(self, days=30):
        result = self._ask(None, "ledger_daily", days=days)

        if result is None:
            self._state = "unavailable"
            return []

        self._state = result["state"]
        return result["daily"]

    @property
    def state(self):
        return self._state


class TaskLocal:
    """
    threading.local for one copy that interleaves requests on
    one thread: each asyncio task (a request, or one step of a
    streamed answer) sees only its own attributes. Values are
    copied on write so no task shares another's dict.
    """

    def __init__(self):
        object.__setattr__(self, "_var", ContextVar("exiom_task_local"))

    def __getattr__(self, name):
        try:
            return self._var.get({})[name]

        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name, value):
        self._var.set({**self._var.get({}), name: value})


class OpenLock:
    """
    Stands in for a lock held across a network wait. On one
    thread, a second request reaching a held threading.Lock
    would block the whole copy for good; here it goes ahead
    (LiveData's lock only saves a duplicate Explorer fetch).
    """

    def acquire(self, blocking=True, timeout=-1):
        return True

    def release(self):
        pass

    def __enter__(self):
        return True

    def __exit__(self, *exc_info):
        return False


class RemoteUsage:

    def __init__(self, call):
        self.flood_guard = RemoteFloodGuard(call)
        self.answer_slots = RemoteAnswerSlots(call)
        self.usage_controller = RemoteUsageController(call)
        self.cost_meter = RemoteCostMeter(call)
        self.usage_ledger = RemoteLedger(call)


def install(app_module, call):
    """
    Point app.py (and its provider) at the hub.
    """

    remote = RemoteUsage(call)

    app_module.flood_guard = remote.flood_guard
    app_module.answer_slots = remote.answer_slots
    app_module.usage_controller = remote.usage_controller
    app_module.cost_meter = remote.cost_meter
    app_module.usage_ledger = remote.usage_ledger
    app_module.ai_provider.cost_meter = remote.cost_meter
    app_module.ai_provider._thread_state = TaskLocal()

    app_module.live_data._fetch_lock = OpenLock()
    share_live_readings(app_module.live_data, call)

    return remote


def share_live_readings(live_data, call):
    """
    Serve the Cron Trigger's Explorer reading from the hub.

    A copy's own reading is used while valid. After that the
    hub's is taken if it is still inside its window; only when
    it is not (the cron failed or has not run yet) does the
    copy fetch the Explorer itself, as it would anywhere else.
    No reading older than its window is ever served.
    """

    fetch_directly = live_data.get_network_stats

    def get_network_stats():
        cached = live_data._get_cached("network_stats")

        if cached:
            return cached

        try:
            item = call("get_reading", {})

        except Exception as error:
            _log_failure("get_reading", error)
            item = None

        if item and live_data._now() - item["time"] <= item["ttl"]:
            live_data.cache["network_stats"] = item
            return item["data"]

        return fetch_directly()

    live_data.get_network_stats = get_network_stats
