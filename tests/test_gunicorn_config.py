import runpy
from pathlib import Path


CONFIG = Path(__file__).parent.parent / "gunicorn.conf.py"


def load(monkeypatch, **env):
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    return runpy.run_path(str(CONFIG))


def test_workers_are_threaded_for_streaming(monkeypatch):
    config = load(monkeypatch)

    assert config["worker_class"] == "gthread"
    assert config["workers"] * config["threads"] >= 8


def test_workers_are_never_recycled(monkeypatch):
    """
    Usage limits live in worker memory; a recycled worker
    would reset every client's budget.
    """

    assert load(monkeypatch)["max_requests"] == 0


def test_the_platform_port_is_used(monkeypatch):
    assert load(monkeypatch, PORT="5123")["bind"] == "0.0.0.0:5123"


def test_bad_environment_values_fall_back(monkeypatch):
    config = load(monkeypatch, WEB_CONCURRENCY="lots", GUNICORN_THREADS="0")

    assert config["workers"] == 2
    assert config["threads"] == 1


def test_request_heads_are_bounded(monkeypatch):
    config = load(monkeypatch)

    assert 0 < config["limit_request_line"] <= 8190
    assert 0 < config["limit_request_fields"] <= 100
    assert 0 < config["limit_request_field_size"] <= 8190


def test_access_log_records_no_personal_data(monkeypatch):
    log_format = load(monkeypatch)["access_log_format"]

    # h: client address, a: User-Agent, f: Referer,
    # r/q: query string, {...}i: any request header.
    for atom in ("%(h)s", "%(a)s", "%(f)s", "%(r)s", "%(q)s", "}i"):
        assert atom not in log_format

    assert "%(U)s" in log_format
    assert "%(s)s" in log_format
