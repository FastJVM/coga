from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

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


def test_post_failure_swallowed(cfg, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import requests

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg, "still logged")  # must not raise
    err = capsys.readouterr().err
    assert "post failed" in err
    assert "still logged" in err
