# ---------------------------------------------------------
# SAFE CACHING
# ---------------------------------------------------------
#
# Repeating an identical AI call for an identical situation
# is pure waste.
#
# Caching an answer is only safe when EVERYTHING that shaped
# that answer is part of the key. For EXIOM AI that means:
#
# - the exact question (normalised)
# - the routing decision
# - the verified Explorer values used
# - the verified knowledge supplied
#
# Conversation-dependent answers are never cached, because
# the same words can mean different things after different
# context. Off-topic banter is never cached either, because
# it is required to stay varied.
# ---------------------------------------------------------

import hashlib
import threading
import time


class TTLCache:
    """
    Small thread-safe cache with expiry and a hard size cap.

    Least-recently-used entries are evicted first so that the
    process memory stays bounded.
    """

    def __init__(self, ttl_seconds=300, max_entries=256):

        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries

        self._entries = {}
        self._lock = threading.Lock()

        self.hits = 0
        self.misses = 0


    def _expired(self, entry, now):
        return now - entry["stored_at"] > self.ttl_seconds


    def get(self, key):

        if not key:
            return None

        now = time.time()

        with self._lock:

            entry = self._entries.get(key)

            if not entry:
                self.misses += 1
                return None

            if self._expired(entry, now):
                self._entries.pop(key, None)
                self.misses += 1
                return None

            entry["used_at"] = now
            self.hits += 1

            return entry["value"]


    def set(self, key, value):

        if not key:
            return

        now = time.time()

        with self._lock:

            self._entries[key] = {
                "value": value,
                "stored_at": now,
                "used_at": now
            }

            if len(self._entries) <= self.max_entries:
                return

            # Drop expired entries first, then the oldest.
            for existing_key in list(self._entries.keys()):

                if self._expired(self._entries[existing_key], now):
                    self._entries.pop(existing_key, None)

            while len(self._entries) > self.max_entries:

                oldest_key = min(
                    self._entries,
                    key=lambda item: self._entries[item]["used_at"]
                )

                self._entries.pop(oldest_key, None)


    def clear(self):

        with self._lock:
            self._entries.clear()
            self.hits = 0
            self.misses = 0


    def stats(self):

        with self._lock:

            total = self.hits + self.misses

            return {
                "entries": len(self._entries),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(self.hits / total, 4) if total else 0.0
            }


def fingerprint(*parts):
    """
    Build a short, stable digest of everything supplied.
    """

    digest = hashlib.sha256()

    for part in parts:

        digest.update(str(part).encode("utf-8"))
        digest.update(b"\x1f")

    return digest.hexdigest()[:32]


def router_cache_key(normalized_question, registry_keys):
    """
    Router decisions depend on the question and on which
    facts exist — not on the values those facts hold.
    """

    if not normalized_question:
        return None

    return fingerprint(
        "router",
        normalized_question,
        ",".join(sorted(registry_keys or []))
    )


def answer_cache_key(
    normalized_question,
    scope,
    intent,
    fact_values,
    knowledge,
    explorer_state=""
):
    """
    Answer reuse requires every input to be identical.

    explorer_state carries the Explorer's availability and
    connection state. Those reach the prompt even when no
    fact is selected, and an answer written while the
    Explorer was down must never be replayed once it is back.
    """

    if not normalized_question:
        return None

    facts_part = ";".join(
        f"{key}={value}"
        for key, value in sorted((fact_values or {}).items())
    )

    return fingerprint(
        "answer",
        normalized_question,
        scope,
        intent,
        facts_part,
        explorer_state,
        knowledge
    )
