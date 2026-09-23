# ---------------------------------------------------------
# PROVIDER RELIABILITY
# ---------------------------------------------------------
#
# The SDK's own retries are switched off (max_retries=0) so
# that every retry decision is made here, where it can be
# tested and bounded.
#
# The policy deliberately mirrors the OpenAI Python SDK's
# built-in one, so behaviour matches OpenAI's documentation:
#
# - retry timeouts, connection failures, 408, 409, 429, 5xx
# - obey the server's x-should-retry header
# - honour Retry-After / Retry-After-Ms (seconds, ms or an
#   HTTP date); an overflowing value means "do not retry"
# - otherwise back off 0.5s, 1s, 2s ... capped at 8s, with up
#   to 25% jitter so callers do not retry in lockstep
#
# Deliberate differences from the SDK:
#
# 1. A 429 for an exhausted quota is final, whatever any
#    header says. Waiting cannot refill an account.
# 2. A server asking for more than 10s is not waited for
#    (the SDK waits up to two minutes): a person is watching a
#    spinner, and a clear error beats a minute of silence.
# 3. Every call has a deadline. A new attempt only starts if
#    it can still finish in time. It bounds retries, not a
#    stream that is actively delivering text: that is bounded
#    by its output-token ceiling and the per-event read
#    timeout, and cutting it would lose an answer mid-way.
# ---------------------------------------------------------

import email.utils
import math
import os
import random
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    Timeout,
)


INITIAL_RETRY_DELAY = 0.5
MAX_RETRY_DELAY = 8.0

# A server asking for a longer pause than this is overloaded
# for longer than anyone will wait for an answer.
MAX_RETRY_AFTER_SECONDS = 10.0

# A retry with less time than this left cannot realistically
# complete, so it would only delay the inevitable error.
MIN_ATTEMPT_SECONDS = 2.0

RETRYABLE_STATUS_CODES = {408, 409, 429}

FINAL_ERROR_CODES = {"insufficient_quota"}


def env_float(name, fallback):
    """
    A positive float from the environment, or the fallback.
    """

    try:
        value = float(os.getenv(name, ""))

    except ValueError:
        return fallback

    if not math.isfinite(value) or value <= 0:
        return fallback

    return value


def env_int(name, fallback):
    """
    A positive integer from the environment, or the fallback.
    """

    try:
        value = int(os.getenv(name, ""))

    except ValueError:
        return fallback

    return value if value > 0 else fallback


def _retry_after_seconds(headers):
    """
    The server's requested wait, or None when it gave none.
    An unrepresentably large value comes back as math.inf.
    """

    for header, divisor in (
        ("retry-after-ms", 1000),
        ("retry-after", 1)
    ):

        value = headers.get(header)

        if value is None:
            continue

        try:
            seconds = float(value) / divisor

        except ValueError:
            continue

        if math.isnan(seconds):
            continue

        return max(0.0, seconds)

    value = headers.get("retry-after")

    if value:

        try:
            when = email.utils.parsedate_to_datetime(value)

        except (TypeError, ValueError, IndexError):
            return None

        if when is not None and when.tzinfo is not None:
            return max(0.0, when.timestamp() - time.time())

    return None


def _backoff(attempt, jitter):

    delay = min(
        INITIAL_RETRY_DELAY * (2.0 ** min(attempt, 32)),
        MAX_RETRY_DELAY
    )

    return delay * (1 - 0.25 * jitter())


def retry_delay(error, attempt, jitter=random.random):
    """
    Seconds to wait before retrying after `error`, or None
    when the error is final.

    `attempt` counts from 0 for the attempt that just failed.
    """

    # APITimeoutError is a subclass of APIConnectionError.
    if isinstance(error, APIConnectionError):
        return _backoff(attempt, jitter)

    if not isinstance(error, APIStatusError):
        return None

    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None) or {}

    retry_after = _retry_after_seconds(headers)

    if (
        retry_after is not None
        and retry_after > MAX_RETRY_AFTER_SECONDS
    ):
        return None

    if getattr(error, "code", None) in FINAL_ERROR_CODES:
        return None

    should_retry = headers.get("x-should-retry")

    if should_retry == "false":
        return None

    if should_retry != "true":

        status = error.status_code

        if (
            status not in RETRYABLE_STATUS_CODES
            and status < 500
        ):
            return None

    if retry_after is not None and retry_after > 0:
        return retry_after

    return _backoff(attempt, jitter)


class Deadline:
    """
    The time budget for starting attempts of one provider
    call, retries included.
    """

    def __init__(self, seconds, clock=time.monotonic):

        self._clock = clock
        self._ends_at = clock() + seconds


    def remaining(self):

        return max(0.0, self._ends_at - self._clock())


    def allows(self, delay):
        """
        Whether waiting `delay` still leaves room for one
        realistic attempt.
        """

        return self.remaining() > delay + MIN_ATTEMPT_SECONDS


    def attempt_timeout(self, connect, read):
        """
        Per-attempt timeouts, never longer than the time left.
        """

        left = max(0.1, self.remaining())

        return Timeout(
            connect=min(connect, left),
            read=min(read, left),
            write=min(read, left),
            pool=min(connect, left)
        )
