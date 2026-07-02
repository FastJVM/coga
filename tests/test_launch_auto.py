from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from conftest import seed_direct_body_workflow
from coga.cli import app
from coga.create import create_task
from coga.config import load_config
from coga.repl_supervisor import ReplOutcome
from coga.ticket import Ticket


def _fake_headless(calls: list[dict], *, exit_code: int = 0, kind: str = "natural",
                   on_run=None):
    """A stand-in for `run_headless` that records its invocation.

    `on_run` lets a test simulate the agent's own state transition (e.g.
    flipping the ticket to done, as a real run's `coga mark done` would)
    before the launch supervisor re-reads the ticket.
    """
    def fake(cmd, env, *, capture_path, idle_timeout=None, max_session=None,
             cwd=None, output_fd=None):
        calls.append({
            "cmd": cmd,
            "capture_path": capture_path,
            "idle_timeout": idle_timeout,
            "max_session": max_session,
        })
        capture_path.parent.mkdir(parents=True, exist_ok=True)
        capture_path.write_text("captured agent output\n")
        if on_run is not None:
            on_run()
        return ReplOutcome(exit_code, kind)
    return fake


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
    company = tmp_path / "coga"
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
        [launch]
        worktree = false
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    seed_direct_body_workflow(company)
    monkeypatch.chdir(company)
    return company


def test_launch_auto_mode_runs_headless(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An `autonomy: auto` ticket launches headless: the CLI's auto argv is
    used, output is captured next to the task, and the exit is recorded in
    the repo-global log. No TTY is required."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Auto run", workflow_name="direct/body",
        contexts=[], autonomy="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[dict] = []

    def agent_marks_done() -> None:
        ticket = Ticket.read(repo / "tasks" / "auto-run.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(repo / "tasks" / "auto-run.md")

    monkeypatch.setattr(
        "coga.commands.launch.run_headless",
        _fake_headless(calls, on_run=agent_marks_done),
    )
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "auto-run"])
    assert result.exit_code == 0, result.output

    # Headless spawn: `claude -p <prompt>` — the auto flag, not a REPL.
    assert len(calls) == 1
    assert calls[0]["cmd"][0] == "claude"
    assert "-p" in calls[0]["cmd"]
    # Capture sits beside the file-form ticket, not inside tasks listing.
    assert calls[0]["capture_path"] == repo / "tasks" / "auto-run.auto-run.log"
    assert calls[0]["capture_path"].read_text() == "captured agent output\n"
    # The exit is durably recorded in the repo-global log.
    log_text = (repo / "log.md").read_text()
    assert "auto run exited 0 (natural)" in log_text
    assert "auto-run.auto-run.log" in log_text


def test_launch_mode_override_auto_runs_headless(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--autonomy auto` runs an interactive ticket headless for this launch,
    leaving the ticket file's `autonomy:` untouched."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Interactive run", workflow_name="direct/body",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[dict] = []

    def agent_marks_done() -> None:
        ticket = Ticket.read(repo / "tasks" / "interactive-run.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(repo / "tasks" / "interactive-run.md")

    monkeypatch.setattr(
        "coga.commands.launch.run_headless",
        _fake_headless(calls, on_run=agent_marks_done),
    )
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")

    result = CliRunner().invoke(
        app, ["launch", "interactive-run", "--autonomy", "auto"]
    )
    assert result.exit_code == 0, result.output
    assert "autonomy overridden to 'auto'" in result.output
    assert len(calls) == 1
    assert "-p" in calls[0]["cmd"]
    ticket = Ticket.read(repo / "tasks" / "interactive-run.md")
    assert ticket.autonomy == "interactive"


def test_launch_auto_failure_posts_alert_and_propagates_exit(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-zero headless exit posts the 💥 live alert (there is no human at
    a console to see it fail) and propagates the exit code."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Auto run", workflow_name="direct/body",
        contexts=[], autonomy="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[dict] = []
    posts: list[str] = []
    monkeypatch.setattr(
        "coga.commands.launch.run_headless", _fake_headless(calls, exit_code=3)
    )
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")
    monkeypatch.setattr(
        "coga.commands.launch.post",
        lambda cfg, text, **kwargs: posts.append(text),
    )

    result = CliRunner().invoke(app, ["launch", "auto-run"])
    assert result.exit_code == 3, result.output
    assert len(posts) == 1
    assert "💥 auto run failed" in posts[0]
    assert "exit 3" in posts[0]


def test_launch_auto_timeout_posts_alert(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A liveness teardown outside the recurring sweep posts its own ⏱️ alert
    (the sweep path returns 'timeout' instead and posts its own pause)."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Auto run", workflow_name="direct/body",
        contexts=[], autonomy="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[dict] = []
    posts: list[str] = []
    monkeypatch.setattr(
        "coga.commands.launch.run_headless",
        _fake_headless(calls, exit_code=124, kind="timeout"),
    )
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")
    monkeypatch.setattr(
        "coga.commands.launch.post",
        lambda cfg, text, **kwargs: posts.append(text),
    )

    result = CliRunner().invoke(app, ["launch", "auto-run"])
    assert result.exit_code == 124, result.output
    assert len(posts) == 1
    assert "⏱️ auto run" in posts[0]
    assert "timed out" in posts[0]


def test_launch_auto_silent_noop_posts_warning(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An auto run that exits 0 without bump/done/block must not end
    invisibly: the launch posts a ⚠️ no-advance alert and stops."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Auto run", workflow_name="direct/body",
        contexts=[], autonomy="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[dict] = []
    posts: list[str] = []
    # exit 0 with no state transition — the silent no-op.
    monkeypatch.setattr(
        "coga.commands.launch.run_headless", _fake_headless(calls)
    )
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")
    monkeypatch.setattr(
        "coga.commands.launch.post",
        lambda cfg, text, **kwargs: posts.append(text),
    )

    result = CliRunner().invoke(app, ["launch", "auto-run"])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1  # ran once, did not chain or relaunch
    assert len(posts) == 1
    assert "⚠️ auto run" in posts[0]
    assert "without advancing" in posts[0]
    ticket = Ticket.read(repo / "tasks" / "auto-run.md")
    assert ticket.status == "in_progress"


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

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
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
