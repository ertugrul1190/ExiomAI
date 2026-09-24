from pathlib import Path

import usage_link


TOKEN = "a" * 40


def test_the_token_goes_after_the_hash():
    assert usage_link.usage_link("https://site.com/", TOKEN) == \
        f"https://site.com/usage#{TOKEN}"


def test_odd_token_characters_are_escaped():
    assert usage_link.usage_link("https://site.com", "a b/#c") == \
        "https://site.com/usage#a%20b%2F%23c"


def test_prints_the_link(monkeypatch, capsys):
    monkeypatch.setenv("EXIOM_USAGE_TOKEN", TOKEN)

    assert usage_link.main(["usage_link.py", "https://site.com"]) == 0
    assert capsys.readouterr().out.strip() == \
        f"https://site.com/usage#{TOKEN}"


def test_refuses_without_a_strong_token(monkeypatch, capsys):
    monkeypatch.setenv("EXIOM_USAGE_TOKEN", "short")

    assert usage_link.main(["usage_link.py", "https://site.com"]) == 1
    assert "32" in capsys.readouterr().out


def test_asks_for_the_site(capsys):
    assert usage_link.main(["usage_link.py"]) == 2


def test_the_page_reads_the_token_from_the_link():
    page = (
        Path(__file__).parent.parent / "templates" / "usage.html"
    ).read_text()

    assert "location.hash" in page
