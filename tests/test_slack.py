from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import requests

from relay.config import load_config
from relay.slack import post


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


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


def test_failure_writes_to_stderr(cfg, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg, "lost message")  # must not raise

    err = capsys.readouterr().err
    assert "post failed" in err
    assert "lost message" in err


def test_failure_with_task_path_appends_to_log(
    cfg, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_path = tmp_path / "tasks" / "001-x"
    task_path.mkdir(parents=True)
    (task_path / "log.md").write_text("")

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg, "daemon message", task_path=task_path)

    log_text = (task_path / "log.md").read_text()
    assert "[slack]" in log_text
    assert "post failed" in log_text
    assert "ConnectionError" in log_text
