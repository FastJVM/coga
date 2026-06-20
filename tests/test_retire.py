from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import typer
from typer.testing import CliRunner

from relay.cli import app
from relay.ticket import Ticket

from conftest import seed_direct_body_workflow


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
    # Retire creates its task with the `direct/body` workflow; the minimal
    # test repo needs that shipped workflow + skill present (real repos get it
    # from `relay init`) or `create_task` fails to load the workflow.
    seed_direct_body_workflow(relay_os)
    return relay_os


def _seed_done_task(repo: Path, slug: str = "fix-retry-logic") -> Path:
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        f"""
        ---
        title: Fix retry logic
        status: done
        mode: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Done.
        """,
    )
    (task_dir / "blackboard.md").write_text("# Fix retry logic\n")
    (task_dir / "log.md").write_text("")
    return task_dir


def test_retire_no_launch_creates_task_with_target_slug(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "fix-retry-logic")

    result = CliRunner().invoke(app, ["retire", "fix-retry-logic", "--no-launch"])

    assert result.exit_code == 0, result.output
    assert "Retire: target task fix-retry-logic" in result.output
    assert "Retire: using assignee claude (agent type claude, mode interactive)" in result.output
    assert "Retire: creating task 'Retire fix-retry-logic'" in result.output
    assert "Retire: created task retire-fix-retry-logic" in result.output
    assert "Retire: launch skipped (--no-launch)" in result.output
    assert "relay launch retire-fix-retry-logic" in result.output

    new_task = repo / "tasks" / "retire-fix-retry-logic"
    assert new_task.is_dir()
    ticket = Ticket.read(new_task / "ticket.md")
    assert ticket.title == "Retire fix-retry-logic"
    # Retire tasks create straight to `active`, carrying the `direct/body`
    # workflow so they run their body directly while still being a
    # workflow-carrying, bumpable, valid active task.
    assert ticket.status == "active"
    assert ticket.mode == "interactive"
    assert ticket.assignee == "claude"
    assert ticket.workflow["name"] == "direct/body"
    assert "Retire the done ticket `fix-retry-logic`" in ticket.body
    assert "retro/done-ticket" in ticket.body
    # Source task untouched until the agent runs the retro skill.
    assert (repo / "tasks" / "fix-retry-logic" / "ticket.md").is_file()


def test_retire_refuses_non_done_target(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    task_dir = repo / "tasks" / "in-flight"
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        """
        ---
        title: Still going
        status: active
        mode: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Active.
        """,
    )
    (task_dir / "blackboard.md").write_text("")
    (task_dir / "log.md").write_text("")

    result = CliRunner().invoke(app, ["retire", "in-flight", "--no-launch"])

    assert result.exit_code == 2
    assert "Retire only operates on done tickets" in result.output
    assert "is 'active'" in result.output
    # Refused — no retire create task created.
    assert not (repo / "tasks" / "retire-in-flight").exists()


def test_retire_refuses_unknown_slug(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "real-task")

    result = CliRunner().invoke(app, ["retire", "no-such-task", "--no-launch"])

    assert result.exit_code == 2
    assert "no-such-task" in result.output


def test_retire_refuses_auto_mode(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay retire <slug> --mode auto` is rejected while auto is disabled."""
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "fix-retry-logic")

    result = CliRunner().invoke(
        app, ["retire", "fix-retry-logic", "--mode", "auto", "--no-launch"]
    )

    assert result.exit_code == 2
    assert "mode=auto is temporarily disabled" in result.output
    assert not (repo / "tasks" / "retire-fix-retry-logic").exists()


def test_retire_launches_after_create(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "fix-retry-logic")
    calls: list[dict[str, object]] = []

    def fake_launch(
        task: str,
        agent_override: str | None,
        prompt_report: bool,
        mode_override: str | None = None,
    ) -> None:
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        assert ticket.status == "active"
        calls.append(
            {
                "task": task,
                "agent_override": agent_override,
                "prompt_report": prompt_report,
                "mode_override": mode_override,
            }
        )
        typer.echo("fake launch called")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(
        app, ["retire", "fix-retry-logic", "--mode", "interactive"]
    )

    assert result.exit_code == 0, result.output
    assert "Retire: created task retire-fix-retry-logic" in result.output
    assert "(active)" in result.output
    assert "Retire: launching retire-fix-retry-logic" in result.output
    assert "fake launch called" in result.output
    log = (repo / "tasks" / "retire-fix-retry-logic" / "log.md").read_text()
    assert "created (mode=interactive, status=active)" in log
    assert calls == [
        {
            "task": "retire-fix-retry-logic",
            "agent_override": None,
            "prompt_report": False,
            "mode_override": None,
        }
    ]


def test_retire_resolves_unique_prefix(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "fix-retry-logic")

    result = CliRunner().invoke(app, ["retire", "fix-retr", "--no-launch"])

    assert result.exit_code == 0, result.output
    assert "Retire: target task fix-retry-logic" in result.output
    assert (repo / "tasks" / "retire-fix-retry-logic").is_dir()
