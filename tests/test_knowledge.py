"""
The knowledge base against the official sources it was
written from (knowledge/sources.json). See "Task Docs/
Official Sources - Knowledge Refresh.md".

Retrieval is keyword scoring, so a fact the AI needs is only
useful if the question a user would really ask pulls the
section holding it. Each golden question below comes from
the official documentation, and its answer must reach the
AI exactly as the app retrieves it.
"""

import json
import re
from pathlib import Path

import pytest

import retrieval


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = ROOT / "knowledge"

DOCUMENTS = retrieval.load_knowledge_directory(KNOWLEDGE)
SECTIONS = retrieval.build_knowledge_sections(DOCUMENTS)
SOURCES = json.loads((KNOWLEDGE / "sources.json").read_text())


def retrieved(question):
    # The arguments app.py uses.
    return retrieval.retrieve_knowledge(question, SECTIONS, limit=6)


# (question, text the retrieved knowledge must contain)
GOLDEN = [
    # Service nodes: uptime, credits, penalties, deregistration
    ("How do decommission credits work?", "48 minutes"),
    ("How long can my node be offline before it gets deregistered?", "48 hours"),
    ("What happens if my service node goes offline?", "recommission"),
    ("How often are uptime proofs sent?", "21 minutes"),
    ("How long is the stake locked after deregistration?", "14 days with no rewards"),
    ("What are the quorum tests a node must pass?", "4 missed out of the last 8"),
    ("Is there a grace period after a hard fork?", "5 days"),
    ("When does my node start earning after registration?", "first 4 blocks"),

    # Operator guide: setup and troubleshooting
    ("Which ports do I need to open for a service node?", "9232"),
    ("What hardware do I need to run a node?", "4 CPU cores"),
    ("What is the docker image for the XEQM node?", "ghcr.io/xeqmlabs/xeqm-node"),
    ("How do I generate the service node registration command?", "get_service_node_registration_cmd"),
    ("How many atomic units is one XEQM?", "1,000,000,000"),
    ("My RPC says connection closed, how do I fix it?", "--rpc-admin=0.0.0.0:9231"),
    ("My last uptime proof was over 30 minutes ago", "send_uptime_proof"),
    ("How do I update my node to the latest version?", "no resync"),
    ("How do I check if my service node is active?", "get_service_nodes"),
    ("How do I stake into someone else's pool node?", "stake <service_node_pubkey>"),
    ("How long until a registration command expires?", "expires after 14 days"),

    # Tokenomics: supply, emissions, staking rewards
    ("Does XEQM have a max supply?", "uncapped"),
    ("How much XEQM is emitted per day?", "11,880"),
    ("How much does the governance treasury get?", "17,857"),
    ("How much does one service node earn per month?", "380 XEQM"),
    ("What is the staking APY?", "2.3%"),
    ("How often are staking rewards paid out?", "10,080"),
    ("What is the emission allocation breakdown?", "Service node rewards 40%"),
    ("Does XEQM burn coins?", "does not burn coins"),

    # Hard forks and releases
    ("What did HF22 change?", "219,120"),
    ("What is Pulse recovery?", "236,920"),
    ("What is the latest XEQM core version?", "v1.1.2"),
    ("What is HF23?", "30% or more of active nodes"),

    # Developer platform, oracle, samples
    ("How much does the EXIOM developer API cost?", "prepaid"),
    ("How are platform fees split?", "70% to oracle sidecar operators"),
    ("Is the EXIOM Oracle live?", "Robinhood Chain"),
    ("What API samples are there?", "kyc-gate"),
    ("Where are the EXIOM API docs?", "api.exiom.network/docs"),

    # Wallets and community nodes
    ("Where do I download the GUI wallet?", "XEQMLabs-GUI"),
    ("The mac wallet app says it is damaged", "xattr -cr"),
    ("How do I run a community public node with HTTPS?", "cpn-"),

    # Decentralization and roadmap
    ("What is the Nakamoto coefficient?", "204 operators"),
    ("What is the EXIOM roadmap?", "Phase 6"),

    # Fundamentals
    ("What was XEQM called before?", "Equilibria"),
    ("When did the legacy XEQ swap happen?", "1,806,294"),

    # Casual wording, as users type it
    ("my node got decommissioned what do i do", "recommission"),
    ("node keeps getting decomm'd", "decommission_count"),
    ("how much downtime is allowed", "48 hours"),
    ("is my stake slashed if my node goes down", "slashing"),
    ("how many xeqm do i need for a node", "200,000"),
    ("minimum to join a pool", "10,000"),
    ("whats the max operator fee", "10%"),
    ("what ports should be open", "9230"),
    ("is 9231 safe to expose", "local only"),
    ("how do i check my sn is synced", "target_height"),
    ("can I run several nodes on one server", "9242"),
    ("how do I set up a node on windows", "--rpc-admin=0.0.0.0:9231"),
    ("whats the minimum payout", "1 XEQM"),
    ("total supply of xeqm", "276,917,604"),
    ("do developers need to stake xeqm for api access", "prepaid"),
    ("is lokinet live", "NOT active"),
    ("why do i need to upgrade before block 236920", "236,920"),
    ("my gui wallet won't open on linux", "--no-sandbox"),
    ("how do i restore my wallet", "25-word"),
    ("how is the oracle secured", "8 of 12"),
    ("is xeqm an erc20", "ERC-20"),

    # Found by the spec review: two facts in one question
    ("what is the minimum contribution and how long is unbonding", "10,000"),
    ("What happens to my stake if my node is offline for 3 days?", "48 hours"),
]


@pytest.mark.parametrize("question, expected", GOLDEN)
def test_golden_question_retrieves_its_answer(question, expected):
    assert expected.lower() in retrieved(question).lower(), question


def test_no_section_is_cut_short():
    # A truncated section can lose the very fact asked for.
    oversized = [
        section["title"]
        for section in SECTIONS
        if len(section["content"]) > 2200
    ]

    assert oversized == []


SOURCE_LINE = re.compile(r"^Source[s]?: (.+)$", re.MULTILINE)
LINK = re.compile(r"\]\((https?://[^)\s]+)\)")


def registered_urls():
    return {source["url"].rstrip("/") for source in SOURCES["sources"]}


def test_every_section_names_its_official_source():
    unsourced = [
        section["title"]
        for section in SECTIONS
        if not SOURCE_LINE.search(section["content"])
    ]

    assert unsourced == []


def test_every_cited_source_is_registered():
    # The AI links what a section cites, so a section may only
    # cite a page listed in sources.json.
    cited = {
        url.rstrip("/")
        for section in SECTIONS
        for line in SOURCE_LINE.findall(section["content"])
        for url in LINK.findall(line)
    }

    assert cited and cited <= registered_urls()


CLIENT_SOURCES = [
    "https://xeqmlabs.gitbook.io/docs",
    "https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/service-nodes-sn",
    "https://xeqmlabs.gitbook.io/docs/documentation/sn-operator-guide",
    "https://xeqmlabs.gitbook.io/docs/documentation/whitepaper/tokenomics",
    "https://github.com/XEQMLabs/whitepaper",
    "https://xeqmlabs.com/ai-instructions",
    "https://xeqmlabs.com/faq",
    "https://xeqmlabs.com/blog/exiom-platform-whitepaper",
    "https://xeqmlabs.com/blog/what-is-xeqm",
    "https://xeqmlabs.com/blog/xeqmlabs-developer-platform",
    "https://xeqmlabs.com/blog/xeqmlabs-vision",
    "https://github.com/XEQMLabs",
    "https://github.com/XEQMLabs/xeqm-core",
    "https://github.com/XEQMLabs/XEQMLabs-GUI",
    "https://github.com/XEQMLabs/exiom-samples",
    "https://github.com/XEQMLabs/xeqm-community-nodes",
    "https://explorer.xeqmlabs.com",
]


def test_every_client_source_is_registered():
    assert set(CLIENT_SOURCES) <= registered_urls()


def test_sources_have_unique_ids_and_a_known_priority():
    ids = [source["id"] for source in SOURCES["sources"]]
    priorities = set(SOURCES["source_priority"])

    assert len(ids) == len(set(ids))
    assert all(
        source["type"] in priorities for source in SOURCES["sources"]
    )


def test_superseded_facts_are_never_retrieved_as_current():
    # Whitepaper v12 replaced the stake-to-unlock API tiers and
    # the 35/35/30 fee split; HF22 made forced deregistration
    # 14 days. Older pages still show them, so the knowledge
    # mentions them only as replaced.
    for question, stale in [
        ("What are the developer API tiers?", "Builder"),
        ("How are platform fees split?", "35%"),
        ("How long is the stake locked after deregistration?", "7 days"),
    ]:
        for line in retrieved(question).splitlines():
            if stale in line:
                assert re.search(
                    r"replaced|superseded|earlier|older|before HF22|was ",
                    line,
                    re.IGNORECASE
                ), line


def test_answers_may_link_the_official_source_a_section_names():
    import app

    assert "official Source link" in " ".join(app.STATIC_SYSTEM_PROMPT.split())


def test_web_search_covers_the_official_documentation_sites():
    import ai_provider

    for domain in ("xeqmlabs.gitbook.io", "exiom.network", "xeqmlabs.com", "github.com", "nonlogs.io"):
        assert domain in ai_provider.DEFAULT_WEB_SEARCH_DOMAINS


@pytest.mark.parametrize("question, concept", [
    ("Ports to open?", "ports"),
    ("why was my node deregistered", "penalties"),
    ("what's the APY", "earnings"),
])
def test_concepts_match_whole_words_and_stems(question, concept):
    assert concept in retrieval._question_index(question)["concepts"]


@pytest.mark.parametrize("question", [
    "my android app is happy with my portfolio",
    "what is the purpose of this",
    "costs exceed the proceeds",
])
def test_concepts_never_match_inside_other_words(question):
    assert retrieval._question_index(question)["concepts"] == frozenset()
