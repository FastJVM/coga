"""Config leniency at the CLI surface — a clone without `coga.local.toml`.

A teammate's fresh clone of a coga repo has no gitignored `coga.local.toml`
yet. `coga --help`, per-command `--help`, and the read-only commands must
still run there; only commands that act *as* someone keep the hard
"No `user` set" error (raised from their own strict `load_config()`).
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.cli import app, main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


TICKET = """
---
slug: fix-retry-logic
title: X
status: draft
mode: agent
owner: marc
human: marc
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
---

## Description

<!-- coga:blackboard -->
"""


@pytest.fixture
def clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A coga repo as a teammate first sees it: shared config committed,
    no gitignored `coga.local.toml`."""
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "tasks" / "fix-retry-logic" / "ticket.md", TICKET)
    monkeypatch.chdir(company)
    # main() registers alias placeholders on the module-global `app`;
    # re-registering across tests would accumulate duplicates.
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    return company


def test_root_help_runs_without_user(
    clone: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["coga", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "Organize agent work" in capsys.readouterr().out


def test_command_help_runs_without_user(
    clone: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Even a mutating command's `--help` must work — Typer prints help before
    the command body ever loads config strictly."""
    monkeypatch.setattr("sys.argv", ["coga", "create", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "--help" in capsys.readouterr().out


def test_status_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0
    assert "fix-retry-logic" in result.output


def test_show_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["show", "fix-retry-logic"])
    assert result.exit_code == 0
    assert "fix-retry-logic" in result.output


def test_validate_runs_and_warns_without_user(clone: Path) -> None:
    """`coga validate` still runs on a fresh clone and points at the setup
    step as a warn-level finding instead of dying (or validating clean)."""
    result = CliRunner().invoke(app, ["validate", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    missing_user = [i for i in payload["issues"] if i["kind"] == "missing-user"]
    assert len(missing_user) == 1
    assert missing_user[0]["severity"] == "warn"
    assert "coga.local.toml" in missing_user[0]["message"]


def test_usage_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["usage"])
    assert result.exit_code == 0


def test_mutating_command_still_requires_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["bump", "fix-retry-logic"])
    assert result.exit_code == 2
    assert "No `user` set in coga.local.toml" in result.output


def test_validate_does_not_warn_when_user_set(clone: Path) -> None:
    _write(clone / "coga.local.toml", 'user = "marc"\n')
    result = CliRunner().invoke(app, ["validate", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert [i for i in payload["issues"] if i["kind"] == "missing-user"] == []
