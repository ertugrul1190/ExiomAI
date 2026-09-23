try:  # The SDK vendors its HTTP client under a versioned name.
    import httpx2 as httpx

except ImportError:  # pragma: no cover - older SDK layout
    import httpx

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

import reliability
from reliability import Deadline, retry_delay


REQUEST = httpx.Request("POST", "https://api.openai.com/v1/responses")


def status_error(code, headers=None, body=None):
    response = httpx.Response(code, request=REQUEST, headers=headers or {})

    error_type = RateLimitError if code == 429 else APIStatusError

    return error_type("error", response=response, body=body)


def no_jitter():
    return 0.0


# ---------------------------------------------------------
# WHAT IS RETRIED
# ---------------------------------------------------------

def test_transport_failures_are_retried():
    assert retry_delay(APITimeoutError(request=REQUEST), 0, no_jitter) == 0.5
    assert retry_delay(APIConnectionError(request=REQUEST), 0, no_jitter) == 0.5


def test_the_sdk_retryable_statuses_are_retried():
    for code in (408, 409, 429, 500, 502, 503, 504):
        assert retry_delay(status_error(code), 0, no_jitter) == 0.5, code


def test_other_client_errors_are_final():
    for code in (400, 401, 403, 404, 422):
        assert retry_delay(status_error(code), 0, no_jitter) is None, code


def test_an_exhausted_quota_is_never_retried():
    """
    OpenAI reports a spent account as a 429. Waiting cannot
    fix it, so a retry only doubles the user's wait.
    """

    error = status_error(
        429,
        body={"code": "insufficient_quota", "message": "quota"}
    )

    assert retry_delay(error, 0, no_jitter) is None


def test_no_header_can_revive_an_exhausted_quota():
    error = status_error(
        429,
        headers={"x-should-retry": "true"},
        body={"code": "insufficient_quota"}
    )

    assert retry_delay(error, 0, no_jitter) is None


def test_the_server_can_forbid_or_demand_a_retry():
    assert retry_delay(
        status_error(503, {"x-should-retry": "false"}), 0, no_jitter
    ) is None

    assert retry_delay(
        status_error(400, {"x-should-retry": "true"}), 0, no_jitter
    ) == 0.5


def test_unknown_errors_are_final():
    assert retry_delay(RuntimeError("bug"), 0, no_jitter) is None


# ---------------------------------------------------------
# HOW LONG TO WAIT
# ---------------------------------------------------------

def test_backoff_doubles_and_is_capped():
    error = APITimeoutError(request=REQUEST)

    assert [
        retry_delay(error, attempt, no_jitter)
        for attempt in range(6)
    ] == [0.5, 1.0, 2.0, 4.0, 8.0, 8.0]


def test_jitter_only_ever_shortens_the_wait():
    error = APITimeoutError(request=REQUEST)

    assert retry_delay(error, 0, lambda: 1.0) == 0.375


def test_retry_after_is_honored():
    assert retry_delay(
        status_error(429, {"retry-after": "3"}), 0, no_jitter
    ) == 3.0

    assert retry_delay(
        status_error(429, {"retry-after-ms": "250"}), 0, no_jitter
    ) == 0.25


def test_a_retry_after_beyond_the_limit_is_not_waited_for():
    error = status_error(
        429,
        {"retry-after": str(reliability.MAX_RETRY_AFTER_SECONDS + 1)}
    )

    assert retry_delay(error, 0, no_jitter) is None


def test_an_overflowing_retry_after_is_not_waited_for():
    assert retry_delay(
        status_error(503, {"retry-after": "1e999"}), 0, no_jitter
    ) is None


def test_retry_after_as_an_http_date_is_honored():
    from email.utils import formatdate
    import time

    header = formatdate(time.time() + 3, usegmt=True)

    delay = retry_delay(
        status_error(503, {"retry-after": header}), 0, no_jitter
    )

    assert 1.5 < delay <= 3.0


def test_a_malformed_retry_after_falls_back_to_backoff():
    assert retry_delay(
        status_error(503, {"retry-after": "soon"}), 0, no_jitter
    ) == 0.5


# ---------------------------------------------------------
# DEADLINE
# ---------------------------------------------------------

class FakeClock:

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def test_deadline_counts_down_and_never_goes_negative():
    clock = FakeClock()
    deadline = Deadline(10, clock=clock)

    clock.now += 4
    assert deadline.remaining() == 6

    clock.now += 20
    assert deadline.remaining() == 0


def test_a_retry_is_only_allowed_when_it_can_still_finish():
    clock = FakeClock()
    deadline = Deadline(10, clock=clock)

    assert deadline.allows(1.0)

    clock.now += 8
    assert not deadline.allows(1.0)


def test_attempt_timeout_is_clamped_to_the_time_left():
    clock = FakeClock()
    deadline = Deadline(10, clock=clock)

    clock.now += 7

    timeout = deadline.attempt_timeout(connect=5, read=45)

    assert timeout.connect == 3
    assert timeout.read == 3


def test_env_float_rejects_nonsense(monkeypatch):
    monkeypatch.setenv("EXIOM_TEST_FLOAT", "abc")
    assert reliability.env_float("EXIOM_TEST_FLOAT", 2.5) == 2.5

    monkeypatch.setenv("EXIOM_TEST_FLOAT", "-1")
    assert reliability.env_float("EXIOM_TEST_FLOAT", 2.5) == 2.5

    monkeypatch.setenv("EXIOM_TEST_FLOAT", "7.5")
    assert reliability.env_float("EXIOM_TEST_FLOAT", 2.5) == 7.5


def test_env_int_rejects_nonsense(monkeypatch):
    for bad in ("abc", "0", "-3", "2.5"):
        monkeypatch.setenv("EXIOM_TEST_INT", bad)
        assert reliability.env_int("EXIOM_TEST_INT", 2) == 2

    monkeypatch.setenv("EXIOM_TEST_INT", "4")
    assert reliability.env_int("EXIOM_TEST_INT", 2) == 4
