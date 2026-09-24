# ---------------------------------------------------------
# WALLET-SECRET GUARD
# ---------------------------------------------------------
#
# Task 13 (see "Task Docs/Task 13 - Privacy Review.md").
#
# Users of a crypto assistant paste recovery phrases and
# private keys, usually while asking whether they are safe.
# Anything in a question is forwarded to the AI provider, so
# a secret must be stopped here, before any route, cache or
# log can see it.
#
# This protects users from an accidental paste. It is not a
# filter against someone deliberately disguising their own
# secret, which would only harm themselves.
#
# Recognised:
#
# * a recovery phrase: 12+ consecutive words from the BIP-39
#   or Monero (CryptoNote, which XEQM uses) English lists.
#   Common words ("the", "is", "my", "how"...) are in neither
#   list, so ordinary sentences break the run long before 12.
# * a BIP-32 extended private key (xprv/yprv/zprv/tprv...)
# * a WIF private key
# * 64 hex characters named as a spend, view, private or
#   secret key. Unnamed, the same shape is usually a
#   transaction or block hash, which is fine to ask about.
# ---------------------------------------------------------

import re

from pathlib import Path

from security import strip_control_characters


WORDLISTS = Path(__file__).parent / "wordlists"


def _load_words(*names):

    words = set()

    for name in names:
        words.update((WORDLISTS / name).read_text().split())

    return frozenset(words)


# bip39-english.txt: bitcoin/bips, SHA-256 2f5eed53...24dbda
# as published in BIP-39. monero-english.txt: Monero's
# src/mnemonics/english.h, 1626 words.
SEED_WORDS = _load_words("bip39-english.txt", "monero-english.txt")

MIN_SEED_WORDS = 12

_WORD = re.compile(r"[^\W\d_]+")

_BASE58 = "1-9A-HJ-NP-Za-km-z"

_KEY_PATTERNS = [

    # BIP-32 extended private keys: xprv (BIP-32), yprv/zprv
    # (BIP-49/84) and their testnet and multisig variants
    # (tprv, uprv, vprv, Yprv, Zprv, Uprv, Vprv). 111 chars.
    re.compile(rf"\b[xyztuvYZUV]prv[{_BASE58}]{{100,}}"),

    # WIF: 51 characters (uncompressed, leading 5; testnet 9)
    # or 52 (compressed, leading K/L; testnet c). Longer
    # base58, such as a CryptoNote address, never matches.
    re.compile(
        rf"(?<![{_BASE58}])[5KLc9][{_BASE58}]{{50,51}}(?![{_BASE58}])"
    ),

    # A named key followed directly by its value ("view key:
    # …", "spend key is …"). Anything more in between is a
    # question about a key, e.g. "use my view key to check
    # transaction <hash>". A bare 0x-prefixed 64-hex value is
    # not flagged: it is far more often a transaction hash.
    re.compile(
        r"\b(?:spend|view|private|priv|secret)[\s_-]*key\b"
        r"\W{0,20}(?:(?:is|was|=)\W{0,5})?"
        r"(?:0x)?[0-9a-fA-F]{64}\b",
        re.IGNORECASE
    ),
]


def _has_seed_phrase(text):

    run = 0

    for word in _WORD.findall(text.lower()):

        run = run + 1 if word in SEED_WORDS else 0

        if run >= MIN_SEED_WORDS:
            return True

    return False


def contains_wallet_secret(text):

    text = strip_control_characters(str(text or ""))

    return _has_seed_phrase(text) or any(
        pattern.search(text) for pattern in _KEY_PATTERNS
    )


def without_wallet_secrets(conversation):
    """
    Drop every history turn that carries a wallet secret.

    Runs before trimming: clipping could cut a phrase short
    enough to slip past the detector. Anything that is not a
    list of turns is returned as-is for trimming to reject.
    """

    if not isinstance(conversation, list):
        return conversation

    return [
        message
        for message in conversation
        if not (
            isinstance(message, dict)
            and isinstance(message.get("content"), str)
            and contains_wallet_secret(message["content"])
        )
    ]
