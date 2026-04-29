"""Focused tests for `relay status` — table render is covered in test_smoke."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.slack import FAILURES_LOG


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
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
    _write(company / "relay.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


def test_status_no_footer_when_log_absent(repo: Path) -> None:
    r = CliRunner().invoke(app, ["status"])
    assert r.exit_code == 0
    assert "Slack post failures" not in r.output


def test_status_no_footer_when_log_empty(repo: Path) -> None:
    (repo / FAILURES_LOG).write_text("")
    r = CliRunner().invoke(app, ["status"])
    assert r.exit_code == 0
    assert "Slack post failures" not in r.output


def test_status_footer_counts_failure_lines(repo: Path) -> None:
    (repo / FAILURES_LOG).write_text(
        "2026-04-28T10:00:00+00:00\tConnectionError\tmsg one\n"
        "2026-04-28T10:00:01+00:00\tTimeout\tmsg two\n"
        "\n"  # blank line — must not be counted
        "2026-04-28T10:00:02+00:00\tConnectionError\tmsg three\n"
    )
    r = CliRunner().invoke(app, ["status"])
    assert r.exit_code == 0
    assert "3 Slack post failures" in r.output
    assert ".slack-failures.log" in r.output
