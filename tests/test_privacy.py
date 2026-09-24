import hashlib

import pytest

import app as application
import privacy

from test_ask_endpoint import (  # noqa: F401
    FakeProvider,
    provider,
    client,
    ask,
    ask_stream,
)

from test_ai_provider import (
    FakeResponse,
    FakeStream,
    attach_stream,
    build_provider,
)


# Fixtures only: the BIP-39 reference test vector, and a
# 25-word phrase in Monero's format. Never fund either.
BIP39_SEED = (
    "legal winner thank year wave sausage "
    "worth useful legal winner thank yellow"
)

MONERO_SEED = (
    "sequence atlas unveil summon pebbles tuesday beer rudely "
    "snake rockets different fuselage woven tagged bested dented "
    "vegan hover rapid fawns obvious muppet randomly seasons randomly"
)

SPEND_KEY = "7" * 64
TX_HASH = "a1" * 32


# ---------------------------------------------------------
# WALLET-SECRET DETECTION
# ---------------------------------------------------------

def test_wordlists_are_the_published_ones():
    bip39 = (privacy.WORDLISTS / "bip39-english.txt").read_bytes()
    monero = (privacy.WORDLISTS / "monero-english.txt").read_text().split()

    # The checksum published in the BIP-39 wordlist README.
    assert hashlib.sha256(bip39).hexdigest() == (
        "2f5eed53a4727b4bf8880d8f3f199efc"
        "90e58503646d9ff8eff3a2ed3b24dbda"
    )
    assert len(bip39.split()) == 2048
    assert len(monero) == len(set(monero)) == 1626
    assert privacy.SEED_WORDS == set(bip39.decode().split()) | set(monero)


@pytest.mark.parametrize("text", [
    BIP39_SEED,
    MONERO_SEED,
    BIP39_SEED.upper(),
    ", ".join(BIP39_SEED.split()),
    " ".join(
        f"{index}. {word}"
        for index, word in enumerate(BIP39_SEED.split(), 1)
    ),
    f"is my wallet safe? my phrase is {BIP39_SEED} thanks",
    "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi",
    "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ",
    f"my private spend key is {SPEND_KEY}",
    f"view key: {SPEND_KEY}",
    f"Secret key {SPEND_KEY.upper()}",
])
def test_wallet_secrets_are_recognised(text):
    assert privacy.contains_wallet_secret(text)


@pytest.mark.parametrize("text", [
    "",
    "What is staking and how do service nodes earn rewards?",
    "can you also tell me about all the rewards you earn "
    "when you run a node for a whole year in total",
    # Eleven list words in a row: one short of any seed.
    " ".join(BIP39_SEED.split()[:11]),
    f"what happened to transaction {TX_HASH}?",
    f"is {TX_HASH} a block hash or a key image?",
    "how do I back up my seed phrase and private keys safely?",
    f"how do I use my view key to check transaction {TX_HASH}?",
])
def test_ordinary_questions_are_not_mistaken_for_secrets(text):
    assert not privacy.contains_wallet_secret(text)


def test_control_characters_cannot_hide_a_seed():
    assert privacy.contains_wallet_secret(
        BIP39_SEED.replace(" ", " \x00")
    )


def test_turns_carrying_secrets_are_dropped_from_history():
    history = [
        {"role": "user", "content": BIP39_SEED},
        {"role": "assistant", "content": "Please never share that."},
        {"role": "user", "content": "what is staking?"},
    ]

    assert privacy.without_wallet_secrets(history) == history[1:]


@pytest.mark.parametrize("history", [None, "text", 5, {"a": 1}])
def test_unusable_history_is_left_for_trimming_to_reject(history):
    assert privacy.without_wallet_secrets(history) == history


def test_malformed_turns_pass_through_untouched():
    history = ["text", {"role": "user"}, {"content": 5}]

    assert privacy.without_wallet_secrets(history) == history


# ---------------------------------------------------------
# THE CHAT NEVER FORWARDS A WALLET SECRET
# ---------------------------------------------------------

@pytest.mark.parametrize("send", [ask, ask_stream])
def test_a_pasted_seed_is_refused_before_anything_sees_it(
    client, provider, capsys, send
):
    response = send(client, f"is this ok? {BIP39_SEED}")

    assert response.status_code == 400
    assert response.get_json()["error_type"] == "sensitive_content"
    assert "recovery phrase" in response.get_json()["answer"]
    assert provider.calls == 0
    assert application.answer_cache.stats()["entries"] == 0
    assert "legal winner" not in capsys.readouterr().out


def test_a_secret_is_refused_even_in_an_oversized_question(client, provider):
    response = ask(client, BIP39_SEED + " x" * 1000)

    assert response.get_json()["error_type"] == "sensitive_content"


def test_a_secret_in_history_is_never_forwarded(client, provider):
    ask(client, "what is staking?", [
        {"role": "user", "content": MONERO_SEED},
        {"role": "assistant", "content": "Please never share that."},
    ])

    sent = provider.generate_calls[0]["conversation"]

    assert sent == [
        {"role": "assistant", "content": "Please never share that."}
    ]


def test_a_secret_cut_by_trimming_is_still_dropped(client, provider):
    """
    Trimming clips long turns. A seed at the clip boundary
    would lose words and slip under the detector, so secrets
    are removed before anything is clipped.
    """

    padding = "staking question " * 70

    ask(client, "what is staking?", [
        {"role": "user", "content": padding + BIP39_SEED},
    ])

    assert provider.generate_calls[0]["conversation"] == []


# ---------------------------------------------------------
# NOTHING A USER TYPES IS LOGGED OR TRACKED
# ---------------------------------------------------------

def test_questions_never_reach_the_logs(client, provider, capsys):
    question = "unique-question-marker what is staking?"

    provider.route_error = RuntimeError("router down")
    provider.generate_error = RuntimeError("provider down")

    ask(client, question)
    ask_stream(client, question)

    assert "unique-question-marker" not in capsys.readouterr().out


def test_no_route_sets_a_cookie(client, provider):
    for response in (
        client.get("/"),
        client.get("/api/network-stats"),
        client.get("/api/usage"),
        ask(client, "hello"),
        ask(client, "what is staking?"),
        ask_stream(client, "what is staking?"),
    ):
        assert "Set-Cookie" not in response.headers


def test_the_page_tells_users_how_their_questions_are_handled(client):
    html = client.get("/").get_data(as_text=True)

    assert "recovery phrase" in html
    assert "AI service" in html


# ---------------------------------------------------------
# THE AI PROVIDER KEEPS NOTHING
# ---------------------------------------------------------

def test_answers_are_not_stored_by_the_provider(monkeypatch):
    provider = build_provider(
        [FakeResponse('{"scope":"relevant","intent":"general","facts":[]}'),
         FakeResponse("answer"),
         FakeResponse("banter")],
        monkeypatch
    )

    provider.route_question("hello", [], {})
    provider.generate("system", [], "question")
    provider.generate_off_topic([], "question")

    attach_stream(provider, [FakeStream(["a"]), FakeStream(["b"])])
    list(provider.stream_generate("system", [], "question"))
    list(provider.stream_generate_off_topic([], "question"))

    requests = provider.client.responses.requests

    assert len(requests) == 5
    assert all(request["store"] is False for request in requests)


def test_storage_opt_out_survives_dropped_cost_controls(monkeypatch):
    provider = build_provider([FakeResponse("answer")], monkeypatch)
    provider.supports_reasoning_effort = False
    provider.supports_text_options = False

    provider.generate("system", [], "question")

    request = provider.client.responses.requests[0]

    assert "reasoning" not in request
    assert request["store"] is False
