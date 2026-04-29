"""Tests for the [aliases] dispatch mechanism in cli.main()."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import _BUILTIN_COMMANDS, _validate_aliases, app, main
from relay.config import ConfigError


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    company = tmp_path / "relay-os"
    company.mkdir()
    _write(
        company / "relay.toml",
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
    _write(company / "relay.local.toml", 'user = "marc"\n')
    return company


def test_validate_rejects_collision_with_builtin() -> None:
    with pytest.raises(ConfigError, match="collides with built-in"):
        _validate_aliases({"launch": "status"})


def test_validate_rejects_unknown_target() -> None:
    with pytest.raises(ConfigError, match="unknown command 'totally-bogus'"):
        _validate_aliases({"chat": "totally-bogus arg"})


def test_validate_accepts_well_formed() -> None:
    _validate_aliases({"chat": "launch bootstrap/orient"})


def test_main_rewrites_argv_for_alias(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay chat foo` should rewrite to `relay launch bootstrap/orient foo`."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[aliases]\nchat = "launch bootstrap/orient"\n'
    )
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["relay", "chat", "extra-arg"])
    monkeypatch.setattr("relay.cli._register_alias_placeholder", lambda *_: None)

    captured: dict[str, list[str]] = {}

    def fake_app() -> None:
        import sys
        captured["argv"] = list(sys.argv)

    monkeypatch.setattr("relay.cli.app", fake_app)

    main()
    assert captured["argv"] == ["relay", "launch", "bootstrap/orient", "extra-arg"]


def test_main_passes_through_non_alias_argv(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Built-in commands should not be rewritten."""
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["relay", "status"])
    monkeypatch.setattr("relay.cli._register_alias_placeholder", lambda *_: None)

    captured: dict[str, list[str]] = {}

    def fake_app() -> None:
        import sys
        captured["argv"] = list(sys.argv)

    monkeypatch.setattr("relay.cli.app", fake_app)
    main()
    assert captured["argv"] == ["relay", "status"]


def test_main_collision_exits_nonzero(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[aliases]\nlaunch = "status"\n'
    )
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["relay", "launch"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_builtin_set_matches_registered_commands() -> None:
    """The hardcoded set in cli.py must match what's actually registered."""
    registered = {info.name for info in app.registered_commands}
    registered |= {grp.name for grp in app.registered_groups}
    assert _BUILTIN_COMMANDS == registered
