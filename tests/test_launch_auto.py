from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from conftest import seed_direct_body_workflow
from coga.cli import app
from coga.create import create_task
from coga.config import load_config


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_script_task(repo: Path, *, slug: str, title: str) -> None:
    """Write a workflow-less ticket whose own `script: inline` makes it a
    script launch (deduced — `mode: script` is gone in v2). A script task
    composes no agent prompt, so `--autonomy` can't override it."""
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        slug: {slug}
        title: {title}
        status: active
        autonomy: interactive
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: null
        script: inline
        ---

        ## Description

        ## Script

        ```bash
        echo hi
        ```

        ## Context

        <!-- coga:blackboard -->

        # Blackboard
    """).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga-os"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    seed_direct_body_workflow(company)
    monkeypatch.chdir(company)
    return company


def test_launch_auto_mode_is_blocked(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`autonomy: auto` launches are temporarily disabled.

    Auto runs (claude -p, codex exec) buffer stdout until completion, so an
    unattended launch sits without any live console signal. The block lives
    in `coga launch` itself and fires before the ticket flips to
    `in_progress` or any agent process spawns.
    """
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Auto run", workflow_name="direct/body",
        contexts=[], autonomy="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "auto-run"])
    assert result.exit_code == 2, result.output
    assert "autonomy=auto is temporarily disabled" in result.output
    # No agent spawned, ticket still active.
    assert calls == []
    from coga.ticket import Ticket
    ticket = Ticket.read(repo / "tasks" / "auto-run.md")
    assert ticket.status == "active"


def test_launch_mode_override_auto_is_blocked(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--autonomy auto` is rejected just like an `autonomy: auto` ticket."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Interactive run", workflow_name="direct/body",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    result = CliRunner().invoke(
        app, ["launch", "interactive-run", "--autonomy", "auto"]
    )
    assert result.exit_code == 2
    assert "autonomy=auto is temporarily disabled" in result.output


def test_launch_mode_override_runs_auto_ticket_interactively(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga launch --autonomy interactive` runs an `autonomy: auto` ticket as
    an interactive session — and leaves the ticket file's `autonomy:`
    untouched."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Auto run", workflow_name="direct/body",
        contexts=[], autonomy="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")
    # Interactive mode requires a TTY; the override path is no exception.
    monkeypatch.setattr(
        "coga.commands.launch._interactive_stdio_has_tty", lambda: True
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "auto-run", "--autonomy", "interactive"])
    assert result.exit_code == 0, result.output
    assert "autonomy overridden to 'interactive'" in result.output

    # Interactive spawn: `claude <prompt>` — no `-p` auto flag.
    assert len(calls) == 1
    assert calls[0][0] == "claude"
    assert "-p" not in calls[0]

    # The override is ephemeral — the ticket file still says `autonomy: auto`.
    from coga.ticket import Ticket
    ticket = Ticket.read(repo / "tasks" / "auto-run.md")
    assert ticket.autonomy == "auto"
    assert ticket.status == "in_progress"


def test_launch_mode_override_rejects_bad_value(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--autonomy` only accepts interactive / auto."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Auto run", workflow_name="direct/body",
        contexts=[], autonomy="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    result = CliRunner().invoke(app, ["launch", "auto-run", "--autonomy", "script"])
    assert result.exit_code == 2
    assert "--autonomy must be 'interactive' or 'auto'" in result.output


def test_launch_mode_override_rejects_script_ticket(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A script ticket has no agent prompt — `--autonomy` can't override it."""
    _write_script_task(repo, slug="script-run", title="Script run")

    result = CliRunner().invoke(
        app, ["launch", "script-run", "--autonomy", "interactive"]
    )
    assert result.exit_code == 2
    assert "not supported for script tasks" in result.output
