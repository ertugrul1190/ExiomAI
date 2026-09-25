# ---------------------------------------------------------
# SECURITY HARDENING
# ---------------------------------------------------------
#
# The small, framework-free pieces behind Task 12 (see "Task
# Docs/Task 12 - Security Hardening.md"):
#
# * response headers, including a per-request nonce CSP
# * client identity that one IPv6 subscriber cannot rotate
# * a flood guard for EVERY route, free ones included
# * a per-client cap on answers in flight
# * scrubbing of control characters and logged secrets
#
# Like usage_control.py, all state is in-memory and per
# process. Client tables are bounded by eviction; answer
# slots by the server's own thread count.
# ---------------------------------------------------------

import ipaddress
import math
import re
import secrets
import threading
import time


# ---------------------------------------------------------
# RESPONSE HEADERS
# ---------------------------------------------------------
#
# Every script on the page carries the nonce: the one inline
# script and the self-hosted GSAP file (Task 9). Nothing else
# may execute: no inline handlers, no third-party origins, no
# framing. Fonts are self-hosted for the same reason.
# ---------------------------------------------------------

def new_nonce():
    return secrets.token_urlsafe(16)


def content_security_policy(nonce):

    return "; ".join([
        "default-src 'self'",
        f"script-src 'nonce-{nonce}'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ])


# HSTS is ignored by browsers on plain HTTP (RFC 6797 8.1),
# so it is safe to send everywhere. No includeSubDomains:
# other hosts on the domain are not ours to commit.
STATIC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=(), interest-cohort=()"
    ),
}


def apply_security_headers(headers, nonce):

    for name, value in STATIC_HEADERS.items():
        headers[name] = value

    headers["Content-Security-Policy"] = (
        content_security_policy(nonce)
    )


# ---------------------------------------------------------
# INPUT SCRUBBING
# ---------------------------------------------------------
#
# C0/C1 control characters (tab and newlines kept) and the
# Unicode bidi controls behind "Trojan Source" text: none
# belong in a question, and all of them reach the model and
# the logs verbatim.
# ---------------------------------------------------------

_CONTROL_CHARACTERS = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f"
    "\u202a-\u202e\u2066-\u2069]"
)


def strip_control_characters(text):
    return _CONTROL_CHARACTERS.sub("", text)


# ---------------------------------------------------------
# SECRETS
# ---------------------------------------------------------

_SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "sk-***"),
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]{8,}"), "Bearer ***"),
]


def redact_secrets(text):
    """
    Mask anything shaped like a provider key before it is
    logged. OpenAI echoes part of a rejected key in its error
    message.
    """

    text = str(text)

    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)

    return text


MIN_USAGE_TOKEN_LENGTH = 32


def usage_token_from(configured):
    """
    The usage token, or "" (endpoint off) when it is missing
    or too short to resist guessing.
    """

    token = (configured or "").strip()

    if token and len(token) < MIN_USAGE_TOKEN_LENGTH:

        print(
            "EXIOM usage endpoint disabled: EXIOM_USAGE_TOKEN "
            f"must be at least {MIN_USAGE_TOKEN_LENGTH} characters."
        )

        return ""

    return token


# ---------------------------------------------------------
# CLIENT IDENTITY
# ---------------------------------------------------------

def client_key(address):
    """
    A stable limit key for an address, or None if it is not
    an IP address at all.

    IPv6 is grouped by /64: that is one subscriber's normal
    allocation, so per-address counting would hand one person
    2^64 fresh budgets.
    """

    try:
        ip = ipaddress.ip_address(str(address or "").strip())

    except ValueError:
        return None

    if ip.version == 6:

        if ip.ipv4_mapped:
            return str(ip.ipv4_mapped)

        return str(
            ipaddress.ip_network(f"{ip}/64", strict=False)
        )

    return str(ip)


def is_internal_peer(address):
    """
    True for a private, loopback or link-local peer: the
    places a platform load balancer connects from.
    """

    try:
        ip = ipaddress.ip_address(str(address or "").strip())

    except ValueError:
        return False

    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    return ip.is_private or ip.is_loopback or ip.is_link_local


# ---------------------------------------------------------
# FLOOD GUARD
# ---------------------------------------------------------

class FloodGuard:
    """
    A per-client token bucket in front of every route.

    UsageController only meters paid AI work; this stops a
    script hammering the free routes (fast path, Explorer
    stats, the page) as well. A full bucket allows a burst of
    `requests_per_minute`, refilled continuously.

    Least-recently-seen clients are evicted past
    `max_clients`; losing a bucket only ever hands back a
    full allowance, never a smaller one.
    """

    def __init__(
        self,
        requests_per_minute=120,
        max_clients=50_000,
        now=None
    ):

        self.capacity = float(requests_per_minute)
        self.refill_per_second = self.capacity / 60.0
        self.max_clients = max(1, max_clients)

        self._now = now or time.monotonic
        self._lock = threading.Lock()

        # client -> (tokens, last_seen); insertion order is
        # recency order.
        self._buckets = {}


    def allow(self, client_id):
        """
        Returns (allowed, retry_after_seconds).
        """

        now = self._now()

        with self._lock:

            tokens, seen = self._buckets.pop(
                client_id,
                (self.capacity, now)
            )

            tokens = min(
                self.capacity,
                tokens + (now - seen) * self.refill_per_second
            )

            allowed = tokens >= 1.0

            if allowed:
                tokens -= 1.0

            self._buckets[client_id] = (tokens, now)

            while len(self._buckets) > self.max_clients:
                self._buckets.pop(next(iter(self._buckets)))

        if allowed:
            return True, 0

        return False, max(
            1,
            math.ceil((1.0 - tokens) / self.refill_per_second)
        )


    def tracked_clients(self):

        with self._lock:
            return len(self._buckets)


# ---------------------------------------------------------
# ANSWERS IN FLIGHT
# ---------------------------------------------------------

class AnswerSlots:
    """
    Caps how many answers one client may have running at once.

    A stream holds a server thread for its whole life, and
    the whole service has only workers x threads of them.
    Without this, one client could open a few slow streams and
    starve everyone else, well inside any per-minute limit.
    """

    def __init__(self, per_client=4):

        self.per_client = max(1, per_client)

        self._lock = threading.Lock()
        self._active = {}


    def acquire(self, client_id):

        with self._lock:

            active = self._active.get(client_id, 0)

            if active >= self.per_client:
                return False

            self._active[client_id] = active + 1

            return True


    def release(self, client_id):

        with self._lock:

            active = self._active.get(client_id, 0) - 1

            if active > 0:
                self._active[client_id] = active

            else:
                self._active.pop(client_id, None)


    def in_use(self):

        with self._lock:
            return sum(self._active.values())
