from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest

from relay.config import ConfigError, find_repo_root, load_config


def _write(path: Path, text: str) -> None:
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "ready"

        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        [assignees.marc]
        agents = {"claude1" = "claude", "claude2" = "claude"}
        slack = "U04ABCDEF"

        [slack]
        webhook = "https://hooks.slack.com/services/xxx"
        """,
    )
    _write(
        tmp_path / "relay.local.toml",
        """
        user = "marc"

        [secrets]
        stripe_key = "env:STRIPE_SECRET_KEY"
        literal = "just-a-value"
        """,
    )
    return tmp_path


def test_load_basic(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    cfg = load_config(repo)
    assert cfg.current_user == "marc"
    assert cfg.default_status == "ready"
    assert cfg.agents["claude"].cli == "claude"
    assert cfg.slack_webhook.startswith("https://")
    assert cfg.secrets["stripe_key"] == "sk_test_abc"
    assert cfg.secrets["literal"] == "just-a-value"


def test_default_status_defaults_to_ready(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
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
    assert cfg.default_status == "ready"


def test_resolve_agent_type(repo: Path) -> None:
    cfg = load_config(repo)
    agent = cfg.agent_type_for("marc", "claude1")
    assert agent.name == "claude"


def test_unknown_nickname(repo: Path) -> None:
    cfg = load_config(repo)
    with pytest.raises(ConfigError, match="no agent nickname 'goat'"):
        cfg.agent_type_for("marc", "goat")


def test_missing_user(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(tmp_path / "relay.local.toml", "")
    with pytest.raises(ConfigError, match="user` is missing"):
        load_config(tmp_path)


def test_find_repo_root(repo: Path) -> None:
    nested = repo / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == repo


def test_find_repo_root_not_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No relay.toml found"):
        find_repo_root(tmp_path)


def test_missing_env_secret_is_empty(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    cfg = load_config(repo)
    assert cfg.secrets["stripe_key"] == ""


def test_unsupported_version(tmp_path: Path) -> None:
    _write(tmp_path / "relay.toml", "version = 99\n")
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match="Unsupported relay.toml version"):
        load_config(tmp_path)
