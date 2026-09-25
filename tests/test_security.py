import re

import pytest

import app as application
import security
import usage_control

from test_ask_endpoint import (  # noqa: F401
    FakeProvider,
    provider,
    client,
    ask,
)


class Clock:

    def __init__(self, now=1_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


# ---------------------------------------------------------
# RESPONSE HEADERS
# ---------------------------------------------------------

def test_page_carries_a_nonce_csp_that_matches_its_only_script(client):
    response = client.get("/")
    html = response.get_data(as_text=True)
    csp = response.headers["Content-Security-Policy"]

    nonce = re.search(r"'nonce-([^']+)'", csp).group(1)

    scripts = re.findall(r"<script\b[^>]*>", html)

    # One inline script (the app) and the self-hosted GSAP file
    # (Task 9); every one carries this response's nonce.
    assert f'<script nonce="{nonce}">' in html
    assert len(scripts) == 2
    assert all(f'nonce="{nonce}"' in tag for tag in scripts)
    assert all("//" not in tag for tag in scripts)
    assert "'unsafe-inline'" not in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_the_nonce_is_fresh_on_every_page(client):
    first = client.get("/").headers["Content-Security-Policy"]
    second = client.get("/").headers["Content-Security-Policy"]

    assert first != second


def test_the_page_has_no_inline_event_handlers(client):
    """
    A nonce CSP blocks inline handlers, so any left behind
    would silently stop working.
    """

    html = client.get("/").get_data(as_text=True)

    assert not re.search(r"\son[a-z]+\s*=", html)


def test_every_response_is_hardened(client, provider):
    for response in (
        client.get("/"),
        client.get("/api/network-stats"),
        ask(client, "hello"),
    ):
        headers = response.headers

        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert "max-age=" in headers["Strict-Transport-Security"]
        assert headers["Cross-Origin-Opener-Policy"] == "same-origin"
        assert "camera=()" in headers["Permissions-Policy"]


def test_answers_are_never_stored_by_caches(client, provider):
    assert ask(client, "hello").headers["Cache-Control"] == "no-store"

    streamed = client.post("/ask/stream", json={"question": "hello"})

    assert "no-store" in streamed.headers["Cache-Control"]


def test_versioned_assets_keep_their_long_cache(client):
    html = client.get("/").get_data(as_text=True)
    href = re.search(r'href="(/static/style\.css\?v=[^"]+)"', html).group(1)

    assert "immutable" in client.get(href).headers["Cache-Control"]


def test_no_cross_origin_access_is_granted(client, provider):
    response = client.post(
        "/ask",
        json={"question": "hello"},
        headers={"Origin": "https://evil.example"}
    )

    assert "Access-Control-Allow-Origin" not in response.headers


# ---------------------------------------------------------
# REQUEST HARDENING
# ---------------------------------------------------------

@pytest.mark.parametrize("path", ["/ask", "/ask/stream"])
@pytest.mark.parametrize(
    "body",
    [
        b"[1, 2]",
        b'"just a string"',
        b"null",
        b"{not json",
        b"\xff\xfe\x00",
        b"[" * 50_000 + b"]" * 50_000,
        b'{"question": {"nested": true}}',
        b'{"question": 42}',
    ],
)
def test_malformed_bodies_are_refused_without_ai_work(
    client, provider, path, body
):
    response = client.post(
        path,
        data=body,
        content_type="application/json"
    )

    assert response.status_code == 400
    assert response.get_json()["error_type"] in {
        "invalid_request",
        "empty_question",
    }
    assert provider.calls == 0


def test_a_non_json_content_type_is_refused(client, provider):
    """
    A cross-site form or sendBeacon can only send "simple"
    content types; requiring JSON forces a CORS preflight
    that this service never approves.
    """

    response = client.post(
        "/ask",
        data='{"question": "what is staking"}',
        content_type="text/plain"
    )

    assert response.status_code == 400
    assert provider.calls == 0


def test_control_characters_are_removed_from_the_question(client, provider):
    ask(client, "what\x00 is\x1b staking\x7f")

    assert provider.generate_calls[0]["question"] == "what is staking"


def test_a_question_of_only_control_characters_is_empty(client, provider):
    response = ask(client, "\x00\x01\x02")

    assert response.get_json()["error_type"] == "empty_question"


def test_control_characters_are_removed_from_history(client, provider):
    ask(
        client,
        "and nodes?",
        conversation=[{"role": "user", "content": "hi\x00 there"}]
    )

    assert provider.generate_calls[0]["conversation"] == [
        {"role": "user", "content": "hi there"}
    ]


def test_an_oversized_body_is_refused_as_json(client, provider):
    response = client.post(
        "/ask",
        json={"question": "x" * (application.MAX_REQUEST_BYTES + 1)}
    )

    assert response.status_code == 413
    assert response.get_json()["error_type"] == "request_too_large"
    assert provider.calls == 0


def test_a_full_conversation_fits_the_body_limit():
    """
    The page sends at most 8 turns; even at 4 bytes per
    character they must fit comfortably.
    """

    assert application.MAX_REQUEST_BYTES >= 8 * 6000 * 4


def test_an_unexpected_error_is_json_without_details(
    client, provider, monkeypatch
):
    def explode(*args, **kwargs):
        raise RuntimeError("secret internals sk-abcdefghijklmnop")

    monkeypatch.setattr(application, "read_ask_request", explode)

    # Testing mode re-raises errors by default; production
    # does not.
    monkeypatch.setitem(
        application.app.config,
        "PROPAGATE_EXCEPTIONS",
        False
    )

    response = ask(client, "hello")

    assert response.status_code == 500
    assert response.get_json()["error_type"] == "unknown"
    assert "internals" not in response.get_data(as_text=True)


# ---------------------------------------------------------
# USAGE ENDPOINT
# ---------------------------------------------------------

STRONG_TOKEN = "t" * 32


def test_a_non_ascii_usage_token_is_refused_not_crashed(client, monkeypatch):
    monkeypatch.setattr(application, "USAGE_TOKEN", STRONG_TOKEN)

    response = client.get(
        "/api/usage",
        headers={"X-Usage-Token": "café"}
    )

    assert response.status_code == 401


def test_the_usage_token_still_works(client, monkeypatch):
    monkeypatch.setattr(application, "USAGE_TOKEN", STRONG_TOKEN)

    response = client.get(
        "/api/usage",
        headers={"X-Usage-Token": STRONG_TOKEN}
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "configured, expected",
    [
        ("", ""),
        ("short", ""),
        ("  " + STRONG_TOKEN + "  ", STRONG_TOKEN),
        (STRONG_TOKEN, STRONG_TOKEN),
    ],
)
def test_only_a_strong_usage_token_enables_the_endpoint(configured, expected):
    assert security.usage_token_from(configured) == expected


# ---------------------------------------------------------
# SECRETS
# ---------------------------------------------------------

def test_api_keys_are_redacted_from_log_text():
    text = security.redact_secrets(
        "Incorrect API key provided: sk-proj-AbC_123-xyz987654. "
        "Bearer abcdefghijklmnopqrstu"
    )

    assert "AbC_123" not in text
    assert "abcdefghijklmnopqrstu" not in text
    assert "Incorrect API key provided" in text


def test_provider_errors_are_logged_redacted(capsys):
    application.api_error_payload(
        RuntimeError("key sk-live1234567890abcdef leaked")
    )

    assert "1234567890" not in capsys.readouterr().out


# ---------------------------------------------------------
# CLIENT IDENTITY
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "address, expected",
    [
        ("203.0.113.9", "203.0.113.9"),
        (" 203.0.113.9 ", "203.0.113.9"),
        ("2001:db8:1:2:aaaa::1", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:bbbb::9", "2001:db8:1:2::/64"),
        ("::ffff:203.0.113.9", "203.0.113.9"),
        ("not-an-ip", None),
        ("", None),
        (None, None),
    ],
)
def test_client_key_groups_an_ipv6_subnet(address, expected):
    """
    One IPv6 subscriber usually holds a whole /64; counting
    each address separately would let one person rotate past
    every limit.
    """

    assert security.client_key(address) == expected


def test_a_public_peer_cannot_choose_its_identity():
    """
    Reached directly from the internet, the forwarded header
    is the client's own invention.
    """

    with application.app.test_request_context(
        "/ask",
        headers={"X-Forwarded-For": "1.2.3.4"},
        environ_base={"REMOTE_ADDR": "34.117.0.50"}
    ):
        assert application.client_identifier() == "34.117.0.50"


def test_a_public_proxy_can_be_trusted_explicitly(monkeypatch):
    monkeypatch.setattr(application, "TRUST_PUBLIC_PROXY", True)

    with application.app.test_request_context(
        "/ask",
        headers={"X-Forwarded-For": "1.2.3.4"},
        environ_base={"REMOTE_ADDR": "34.117.0.50"}
    ):
        assert application.client_identifier() == "1.2.3.4"


@pytest.mark.parametrize(
    "peer, internal",
    [
        ("10.0.0.5", True),
        ("172.16.3.1", True),
        ("192.168.1.1", True),
        ("127.0.0.1", True),
        ("::1", True),
        ("fd00::1", True),
        ("::ffff:10.0.0.5", True),
        ("34.117.0.50", False),
        ("8.8.8.8", False),
        ("2606:4700::1", False),
        ("garbage", False),
        (None, False),
    ],
)
def test_internal_peers_are_recognised(peer, internal):
    assert security.is_internal_peer(peer) is internal


def test_a_forged_forwarded_entry_falls_back_to_the_peer():
    with application.app.test_request_context(
        "/ask",
        headers={"X-Forwarded-For": "<script>"},
        environ_base={"REMOTE_ADDR": "10.0.0.7"}
    ):
        assert application.client_identifier() == "10.0.0.7"


# ---------------------------------------------------------
# FLOOD GUARD
# ---------------------------------------------------------

def test_flood_guard_allows_a_burst_then_refuses():
    clock = Clock()
    guard = security.FloodGuard(requests_per_minute=3, now=clock)

    assert [guard.allow("a")[0] for _ in range(4)] == [
        True, True, True, False
    ]

    allowed, retry_after = guard.allow("a")

    assert not allowed
    assert 1 <= retry_after <= 20

    assert guard.allow("b")[0]


def test_flood_guard_refills_over_time():
    clock = Clock()
    guard = security.FloodGuard(requests_per_minute=60, now=clock)

    for _ in range(60):
        guard.allow("a")

    assert not guard.allow("a")[0]

    clock.now += 1.0

    assert guard.allow("a")[0]
    assert not guard.allow("a")[0]


def test_flood_guard_memory_is_bounded():
    guard = security.FloodGuard(
        requests_per_minute=5,
        max_clients=100,
        now=Clock()
    )

    for index in range(1000):
        guard.allow(f"client-{index}")

    assert guard.tracked_clients() <= 100


def test_flood_guard_evicts_the_least_recently_seen():
    guard = security.FloodGuard(
        requests_per_minute=1,
        max_clients=2,
        now=Clock()
    )

    guard.allow("busy")
    guard.allow("idle")
    guard.allow("busy")
    guard.allow("new")

    # "busy" was seen more recently than "idle", so it kept
    # its (empty) bucket.
    assert not guard.allow("busy")[0]


def test_the_flood_guard_covers_free_routes(client, provider, monkeypatch):
    monkeypatch.setattr(
        application,
        "flood_guard",
        security.FloodGuard(requests_per_minute=2)
    )

    statuses = [
        client.get("/api/network-stats").status_code
        for _ in range(3)
    ]

    assert statuses == [200, 200, 429]


def test_a_flood_refusal_is_a_readable_429(client, provider, monkeypatch):
    monkeypatch.setattr(
        application,
        "flood_guard",
        security.FloodGuard(requests_per_minute=1)
    )

    ask(client, "hello")
    response = ask(client, "hello")

    assert response.status_code == 429
    assert response.get_json()["error_type"] == "too_many_requests"
    assert int(response.headers["Retry-After"]) >= 1
    assert "X-Content-Type-Options" in response.headers


def test_static_assets_are_not_flood_counted(client, monkeypatch):
    monkeypatch.setattr(
        application,
        "flood_guard",
        security.FloodGuard(requests_per_minute=1)
    )

    statuses = {
        client.get("/static/style.css").status_code
        for _ in range(5)
    }

    assert statuses == {200}


# ---------------------------------------------------------
# CONCURRENT ANSWERS
# ---------------------------------------------------------

def test_answer_slots_are_per_client():
    slots = security.AnswerSlots(per_client=2)

    assert slots.acquire("a")
    assert slots.acquire("a")
    assert not slots.acquire("a")
    assert slots.acquire("b")

    slots.release("a")

    assert slots.acquire("a")


def test_released_clients_are_forgotten():
    slots = security.AnswerSlots(per_client=1)

    slots.acquire("a")
    slots.release("a")
    slots.release("a")

    assert slots.in_use() == 0


def test_an_open_stream_holds_its_slot_until_closed(
    client, provider, monkeypatch
):
    slots = security.AnswerSlots(per_client=1)
    monkeypatch.setattr(application, "answer_slots", slots)

    stream = client.post(
        "/ask/stream",
        json={"question": "what is staking"},
        buffered=False
    )

    assert stream.status_code == 200

    blocked = ask(client, "what are nodes")

    assert blocked.status_code == 429
    assert blocked.get_json()["error_type"] == "too_many_concurrent"

    stream.get_data()
    stream.close()

    assert slots.in_use() == 0
    assert ask(client, "what are nodes").status_code == 200


def test_a_refused_stream_frees_its_slot(client, provider, monkeypatch):
    slots = security.AnswerSlots(per_client=1)
    monkeypatch.setattr(application, "answer_slots", slots)

    provider.generate_error = RuntimeError("down")

    assert client.post(
        "/ask/stream",
        json={"question": "what is staking"}
    ).status_code == 500

    assert slots.in_use() == 0


def test_a_json_answer_frees_its_slot_even_on_failure(
    client, provider, monkeypatch
):
    slots = security.AnswerSlots(per_client=1)
    monkeypatch.setattr(application, "answer_slots", slots)

    provider.generate_error = RuntimeError("down")

    ask(client, "what is staking")
    ask(client, "what is staking")

    assert slots.in_use() == 0


# ---------------------------------------------------------
# USAGE CONTROLLER MEMORY
# ---------------------------------------------------------

def test_usage_controller_memory_is_bounded():
    controller = usage_control.UsageController(
        requests_per_minute=5,
        requests_per_day=5,
        client_tokens_per_day=1000,
        global_tokens_per_day=10_000,
        max_clients=50,
        now=Clock()
    )

    for index in range(500):
        controller.check(f"client-{index}")

    assert controller.snapshot()["tracked_clients"] <= 50


def test_usage_controller_keeps_the_active_clients():
    controller = usage_control.UsageController(
        requests_per_minute=1,
        requests_per_day=100,
        client_tokens_per_day=1000,
        global_tokens_per_day=10_000,
        max_clients=2,
        now=Clock()
    )

    controller.check("busy")
    controller.check("idle")
    controller.check("busy")
    controller.check("new")

    assert controller.check("busy").reason == "client_rate"
