from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.scaffold import scaffold_task
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    relay_os = tmp_path / "relay-os"
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
    _write(relay_os / "relay.local.toml", 'user = "marc"\n')
    _write(
        relay_os / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        mode: interactive
        skills:
          - bootstrap/ticket
        assignee: claude
        ---

        ## Description

        Persistent launch shim.
        """,
    )
    _write(
        relay_os / "skills" / "bootstrap" / "ticket" / "SKILL.md",
        """
        ---
        name: bootstrap/ticket
        description: Author a Relay task.
        ---

        Interview and fill the ticket.
        """,
    )
    monkeypatch.chdir(relay_os)
    return relay_os


def _allow_ticket_launch(monkeypatch: pytest.MonkeyPatch, prompts: list[str]) -> None:
    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        prompts.append(cmd[1])
        return _Result()

    monkeypatch.setattr("relay.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("relay.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("relay.commands.ticket.subprocess.run", fake_run)


def test_ticket_title_creates_draft_and_launches_authoring(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    _allow_ticket_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 0, result.output

    task_dir = repo / "tasks" / "investigate-retries"
    ticket = Ticket.read(task_dir / "ticket.md")
    assert ticket.status == "draft"
    assert ticket.title == "Investigate retries"
    assert ticket.skills == []
    assert "ticket authoring launched" in (task_dir / "log.md").read_text()

    assert len(prompts) == 1
    assert "Relay task — investigate-retries" in prompts[0]
    assert "Status: draft" in prompts[0]
    assert "Skill: bootstrap/ticket" in prompts[0]


def test_ticket_existing_active_task_is_editable_without_status_change(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="Queued work",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    prompts: list[str] = []
    _allow_ticket_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["ticket", "queued-work"])
    assert result.exit_code == 0, result.output

    ticket = Ticket.read(Path(ref["path"]) / "ticket.md")
    assert ticket.status == "active"
    assert ticket.skills == []
    assert "Status: active" in prompts[0]
    assert "Skill: bootstrap/ticket" in prompts[0]


def test_ticket_refuses_in_progress_task(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="Running work",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="in_progress",
    )
    called = False

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True

    monkeypatch.setattr("relay.commands.ticket.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["ticket", "running-work"])
    assert result.exit_code == 2
    assert "in_progress" in (result.output + (result.stderr or ""))
    assert not called


def test_ticket_without_target_launches_bootstrap_interview(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    _allow_ticket_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["ticket"])
    assert result.exit_code == 0, result.output

    assert len(prompts) == 1
    assert "Relay task — bootstrap/ticket" in prompts[0]
    assert "Skill: bootstrap/ticket" in prompts[0]
