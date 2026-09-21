# ---------------------------------------------------------
# USAGE CONTROL AND COST ACCOUNTING
# ---------------------------------------------------------
#
# Two separate jobs live here.
#
# 1. UsageController decides whether a request is allowed to
#    reach the AI provider at all. It is the last line of
#    defence against a single client (or a script) burning
#    the whole budget.
#
# 2. CostMeter records what was actually spent, so the cost
#    of the service is observable instead of guessed.
#
# Both are in-memory and per-process, which is the right fit
# for this single-service deployment. Nothing here blocks a
# request that costs nothing.
# ---------------------------------------------------------

import os
import threading
import time


# USD per 1,000,000 tokens.
# Cached input tokens are billed at a large discount, which
# is why the prompts are ordered static-content-first.
MODEL_RATES = {
    "gpt-5-nano": {
        "input": 0.05,
        "cached_input": 0.005,
        "output": 0.40,
    },
}


DEFAULT_RATES = MODEL_RATES["gpt-5-nano"]


def empty_route_totals():
    return {
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0
    }


def _env_int(name, fallback):

    try:
        value = int(os.getenv(name, ""))

    except (TypeError, ValueError):
        return fallback

    return value if value > 0 else fallback


# ---------------------------------------------------------
# COST METER
# ---------------------------------------------------------

class CostMeter:
    """
    Aggregate token usage and estimated spend.

    Stores counters only. No question text is ever kept.
    """

    def __init__(self):

        self._lock = threading.Lock()
        self.reset()


    def reset(self):

        with self._lock:

            self.started_at = time.time()

            self.calls = 0
            self.input_tokens = 0
            self.cached_input_tokens = 0
            self.output_tokens = 0
            self.reasoning_tokens = 0
            self.estimated_cost_usd = 0.0

            self.by_route = {}
            self.free_responses = 0


    def _rates(self, model):
        return MODEL_RATES.get(model, DEFAULT_RATES)


    def estimate_cost(
        self,
        model,
        input_tokens,
        cached_input_tokens,
        output_tokens
    ):

        rates = self._rates(model)

        billed_input = max(
            0,
            input_tokens - cached_input_tokens
        )

        return (
            billed_input * rates["input"]
            + cached_input_tokens * rates["cached_input"]
            + output_tokens * rates["output"]
        ) / 1_000_000


    def record_usage(self, model, usage, route="unknown"):
        """
        Record one provider call.

        Accepts either the provider usage object or a plain
        dictionary. Missing fields count as zero rather than
        raising: accounting must never break a response.
        """

        input_tokens = _usage_value(usage, "input_tokens")
        output_tokens = _usage_value(usage, "output_tokens")

        cached_input_tokens = _usage_detail(
            usage,
            "input_tokens_details",
            "cached_tokens"
        )

        reasoning_tokens = _usage_detail(
            usage,
            "output_tokens_details",
            "reasoning_tokens"
        )

        cost = self.estimate_cost(
            model,
            input_tokens,
            cached_input_tokens,
            output_tokens
        )

        with self._lock:

            self.calls += 1
            self.input_tokens += input_tokens
            self.cached_input_tokens += cached_input_tokens
            self.output_tokens += output_tokens
            self.reasoning_tokens += reasoning_tokens
            self.estimated_cost_usd += cost

            route_totals = self.by_route.setdefault(
                route,
                empty_route_totals()
            )

            route_totals["calls"] += 1
            route_totals["input_tokens"] += input_tokens
            route_totals["output_tokens"] += output_tokens
            route_totals["estimated_cost_usd"] += cost

        return {
            "input_tokens": input_tokens,
            "cached_input_tokens": cached_input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": reasoning_tokens,
            "estimated_cost_usd": cost
        }


    def record_free_response(self, route="deterministic"):
        """
        Record an answer that required no AI call at all.
        """

        with self._lock:

            self.free_responses += 1

            route_totals = self.by_route.setdefault(
                route,
                empty_route_totals()
            )

            route_totals["calls"] += 1


    def snapshot(self):

        with self._lock:

            total_responses = self.free_responses + self.calls

            return {
                "uptime_seconds": int(time.time() - self.started_at),
                "provider_calls": self.calls,
                "free_responses": self.free_responses,
                "free_response_rate": (
                    round(self.free_responses / total_responses, 4)
                    if total_responses else 0.0
                ),
                "input_tokens": self.input_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "cached_input_rate": (
                    round(
                        self.cached_input_tokens / self.input_tokens,
                        4
                    )
                    if self.input_tokens else 0.0
                ),
                "output_tokens": self.output_tokens,
                "reasoning_tokens": self.reasoning_tokens,
                "estimated_cost_usd": round(
                    self.estimated_cost_usd,
                    6
                ),
                "by_route": {
                    route: {
                        **totals,
                        "estimated_cost_usd": round(
                            totals["estimated_cost_usd"],
                            6
                        )
                    }
                    for route, totals in self.by_route.items()
                }
            }


def _usage_value(usage, field):

    if usage is None:
        return 0

    if isinstance(usage, dict):
        value = usage.get(field)

    else:
        value = getattr(usage, field, None)

    try:
        return max(0, int(value))

    except (TypeError, ValueError):
        return 0


def _usage_detail(usage, container_field, field):

    if usage is None:
        return 0

    if isinstance(usage, dict):
        container = usage.get(container_field)

    else:
        container = getattr(usage, container_field, None)

    return _usage_value(container, field)


# ---------------------------------------------------------
# USAGE CONTROLLER
# ---------------------------------------------------------

class UsageDecision:

    def __init__(self, allowed, reason="", retry_after=0):

        self.allowed = allowed
        self.reason = reason
        self.retry_after = retry_after


    def __repr__(self):
        return (
            f"UsageDecision(allowed={self.allowed}, "
            f"reason={self.reason!r})"
        )


class UsageController:
    """
    Per-client request pacing plus daily token ceilings.

    Limits are intentionally generous for a human asking
    questions and restrictive for an automated loop.
    """

    def __init__(
        self,
        requests_per_minute=None,
        requests_per_day=None,
        client_tokens_per_day=None,
        global_tokens_per_day=None,
        now=None
    ):

        self.requests_per_minute = (
            requests_per_minute
            if requests_per_minute is not None
            else _env_int("EXIOM_REQUESTS_PER_MINUTE", 15)
        )

        self.requests_per_day = (
            requests_per_day
            if requests_per_day is not None
            else _env_int("EXIOM_REQUESTS_PER_DAY", 300)
        )

        self.client_tokens_per_day = (
            client_tokens_per_day
            if client_tokens_per_day is not None
            else _env_int("EXIOM_CLIENT_TOKENS_PER_DAY", 400_000)
        )

        self.global_tokens_per_day = (
            global_tokens_per_day
            if global_tokens_per_day is not None
            else _env_int("EXIOM_GLOBAL_TOKENS_PER_DAY", 20_000_000)
        )

        self._now = now or time.time
        self._lock = threading.Lock()

        self._clients = {}

        self._global_tokens = 0
        self._global_day = None


    def _client_state(self, client_id, now):

        state = self._clients.get(client_id)

        day = int(now // 86400)

        if not state or state["day"] != day:

            state = {
                "day": day,
                "recent_requests": [],
                "requests_today": 0,
                "tokens_today": 0
            }

            self._clients[client_id] = state

        return state


    def _roll_global_day(self, now):

        day = int(now // 86400)

        if self._global_day != day:
            self._global_day = day
            self._global_tokens = 0


    def _prune(self, now):
        """
        Forget clients that have been idle for a full day.
        """

        if len(self._clients) < 5000:
            return

        day = int(now // 86400)

        for client_id in list(self._clients.keys()):

            if self._clients[client_id]["day"] != day:
                self._clients.pop(client_id, None)


    def check(self, client_id):
        """
        Decide whether this client may trigger AI work now.
        """

        client_id = client_id or "unknown"

        now = self._now()

        with self._lock:

            self._roll_global_day(now)
            self._prune(now)

            state = self._client_state(client_id, now)

            state["recent_requests"] = [
                stamp
                for stamp in state["recent_requests"]
                if now - stamp < 60
            ]

            if self._global_tokens >= self.global_tokens_per_day:
                return UsageDecision(
                    False,
                    "global_daily_tokens",
                    retry_after=3600
                )

            if state["tokens_today"] >= self.client_tokens_per_day:
                return UsageDecision(
                    False,
                    "client_daily_tokens",
                    retry_after=3600
                )

            if state["requests_today"] >= self.requests_per_day:
                return UsageDecision(
                    False,
                    "client_daily_requests",
                    retry_after=3600
                )

            if len(state["recent_requests"]) >= self.requests_per_minute:

                oldest = min(state["recent_requests"])

                return UsageDecision(
                    False,
                    "client_rate",
                    retry_after=max(1, int(60 - (now - oldest)))
                )

            state["recent_requests"].append(now)
            state["requests_today"] += 1

            return UsageDecision(True)


    def record_tokens(self, client_id, tokens):
        """
        Charge tokens against the client and global budgets.
        """

        client_id = client_id or "unknown"

        try:
            tokens = max(0, int(tokens))

        except (TypeError, ValueError):
            return

        now = self._now()

        with self._lock:

            self._roll_global_day(now)

            state = self._client_state(client_id, now)

            state["tokens_today"] += tokens
            self._global_tokens += tokens


    def snapshot(self):

        with self._lock:

            return {
                "tracked_clients": len(self._clients),
                "global_tokens_today": self._global_tokens,
                "limits": {
                    "requests_per_minute": self.requests_per_minute,
                    "requests_per_day": self.requests_per_day,
                    "client_tokens_per_day": self.client_tokens_per_day,
                    "global_tokens_per_day": self.global_tokens_per_day
                }
            }
