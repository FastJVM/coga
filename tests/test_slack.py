from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import requests

from relay.config import load_config
from relay.slack import FAILURES_LOG, post


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make retry backoff instant for all slack tests."""
    monkeypatch.setattr("relay.slack.time.sleep", lambda _: None)


@pytest.fixture
def cfg(tmp_path: Path):
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        [assignees.pierre]
        agents = {"claude1" = "claude"}
        [slack]
        webhook = "https://hooks.slack.com/services/test"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    return load_config(tmp_path)


def test_post_calls_webhook(cfg, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        calls.append({"url": url, "json": json})

        class R:
            pass

        return R()

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg, "task done")
    assert len(calls) == 1
    assert calls[0]["url"] == "https://hooks.slack.com/services/test"
    assert calls[0]["json"] == {"text": "task done"}


def test_no_webhook_writes_to_stderr(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    post(cfg, "hello")
    captured = capsys.readouterr()
    assert "[slack] hello" in captured.err


def test_env_var_fallback_when_no_toml_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/from-env")
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook == "https://hooks.slack.com/services/from-env"

    calls: list[str] = []

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        calls.append(url)

        class R:
            pass

        return R()

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg, "via env")
    assert calls == ["https://hooks.slack.com/services/from-env"]


def test_toml_overrides_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        [slack]
        webhook = "https://hooks.slack.com/services/from-toml"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/from-env")
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook == "https://hooks.slack.com/services/from-toml"


def test_retry_then_success(cfg, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"n": 0}

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise requests.ConnectionError("transient")

        class R:
            pass

        return R()

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg, "eventually lands")
    assert attempts["n"] == 3
    # No failure log written on eventual success.
    assert not (cfg.repo_root / FAILURES_LOG).exists()


def test_retry_exhaustion_writes_failure_log(
    cfg, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg, "still logged")  # must not raise

    err = capsys.readouterr().err
    assert "post failed" in err
    assert "still logged" in err

    log_path = cfg.repo_root / FAILURES_LOG
    assert log_path.is_file()
    line = log_path.read_text().strip()
    parts = line.split("\t")
    assert len(parts) == 3
    assert parts[1] == "ConnectionError"
    assert parts[2] == "still logged"


def test_failure_log_truncates_long_messages(
    cfg, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    long_msg = "x" * 500
    post(cfg, long_msg)

    line = (cfg.repo_root / FAILURES_LOG).read_text().strip()
    preview = line.split("\t")[2]
    assert len(preview) == 120
    assert preview == "x" * 120
