from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import typer
from typer.testing import CliRunner

from relay.cli import app
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    relay_os = tmp_path / "relay-os"
    relay_os.mkdir()
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        [assignees.marc]
        agents = {"claude" = "claude"}
        """,
    )
    _write(
        relay_os / "relay.local.toml",
        """
        user = "marc"
        [slack]
        enabled = false
        """,
    )
    return relay_os


def test_dream_no_launch_scaffolds_ad_hoc_task_without_time_bucket(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)

    runner = CliRunner()
    first = runner.invoke(app, ["dream", "--no-launch"])
    second = runner.invoke(app, ["dream", "--no-launch"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert "Dream: repo root" in first.output
    assert "Dream: using assignee claude (agent type claude, mode interactive)" in first.output
    assert "Dream: scaffolding task 'Dream'" in first.output
    assert "Dream: created task dream at" in first.output
    assert "Dream: launch skipped (--no-launch)" in first.output
    assert "relay mark active dream" in first.output
    assert "Created dream" in first.output
    assert "Created dream-2" in second.output
    assert (repo / "tasks" / "dream").is_dir()
    assert (repo / "tasks" / "dream-2").is_dir()
    assert not (repo / "tasks" / "dream-2026-W19").exists()

    ticket = Ticket.read(repo / "tasks" / "dream" / "ticket.md")
    assert ticket.title == "Dream"
    assert ticket.status == "draft"
    assert ticket.mode == "interactive"
    assert ticket.assignee == "claude"
    assert ticket.workflow is None
    assert "Run the Dream cleanup pass for this Relay repo." in ticket.body


def test_dream_refuses_auto_mode(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`relay dream --mode auto` is refused with a pointer to interactive."""
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(app, ["dream", "--mode", "auto", "--no-launch"])
    assert result.exit_code == 2, result.output
    assert "mode=auto is temporarily disabled" in result.output
    # Ticket must not be scaffolded.
    assert not (repo / "tasks" / "dream").exists()


def test_dream_logs_before_launching(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(repo)
    calls: list[dict[str, object]] = []

    def fake_launch(
        task: str,
        agent_override: str | None,
        prompt_report: bool,
        no_verify: bool,
    ) -> None:
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        assert ticket.status == "active"
        calls.append(
            {
                "task": task,
                "agent_override": agent_override,
                "prompt_report": prompt_report,
                "no_verify": no_verify,
            }
        )
        typer.echo("fake launch called")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["dream", "--mode", "interactive"])

    assert result.exit_code == 0, result.output
    assert "Dream: repo root" in result.output
    assert "Dream: using assignee claude (agent type claude, mode interactive)" in result.output
    assert "Dream: scaffolding task 'Dream'" in result.output
    assert "Dream: created task dream at" in result.output
    assert "Dream: activating dream" in result.output
    assert "Dream: launching dream" in result.output
    assert "fake launch called" in result.output
    log = (repo / "tasks" / "dream" / "log.md").read_text()
    assert "activated (draft → active) via relay dream" in log
    assert calls == [
        {
            "task": "dream",
            "agent_override": None,
            "prompt_report": False,
            "no_verify": False,
        }
    ]
