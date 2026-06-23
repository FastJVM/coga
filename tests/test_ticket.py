from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from conftest import seed_direct_body_workflow
from relay.cli import app
from relay.config import load_config
from relay.create import create_task
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _prompt_arg(cmd: list[str]) -> str:
    for arg in cmd:
        if isinstance(arg, str) and arg.startswith("# Relay task"):
            return arg
        if isinstance(arg, str) and arg.startswith("developer_instructions=# Relay task"):
            return arg.removeprefix("developer_instructions=")
    raise AssertionError(f"No Relay prompt in argv: {cmd!r}")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    relay_os = tmp_path / "relay-os"
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

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
    seed_direct_body_workflow(relay_os)
    monkeypatch.chdir(relay_os)
    return relay_os


def _allow_ticket_launch(
    monkeypatch: pytest.MonkeyPatch,
    prompts: list[str],
    *,
    on_run=None,  # type: ignore[no-untyped-def]
) -> None:
    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        prompts.append(_prompt_arg(cmd))
        if on_run is not None:
            on_run()
        return _Result()

    monkeypatch.setattr("relay.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("relay.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)


def test_ticket_title_creates_draft_and_launches_authoring(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    task_dir = repo / "tasks" / "investigate-retries"

    def author_workflow() -> None:
        # Simulate the bootstrap/ticket skill picking a workflow: guided
        # authoring of a draft must land on a workflow or `relay ticket`
        # hard-refuses the result.
        t = Ticket.read(task_dir / "ticket.md")
        t.frontmatter["workflow"] = "code/with-review"
        t.write(task_dir / "ticket.md")

    _allow_ticket_launch(monkeypatch, prompts, on_run=author_workflow)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 0, result.output

    ticket = Ticket.read(task_dir / "ticket.md")
    assert ticket.status == "draft"
    assert ticket.title == "Investigate retries"
    assert ticket.skills == []
    assert "ticket authoring launched" in (task_dir / "log.md").read_text()

    assert len(prompts) == 1
    assert "Relay task — investigate-retries" in prompts[0]
    assert "Status: draft" in prompts[0]
    assert "Skill: bootstrap/ticket" in prompts[0]


def test_ticket_authoring_does_not_inject_relay_secrets(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [secrets]
        stripe_key = "env:STRIPE_SECRET_KEY"
        """,
    )
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live")
    task_dir = repo / "tasks" / "investigate-retries"
    captured_env: dict[str, str] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured_env.update(env or {})
        t = Ticket.read(task_dir / "ticket.md")
        t.frontmatter["workflow"] = "code/with-review"
        t.write(task_dir / "ticket.md")
        return _Result()

    monkeypatch.setattr("relay.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("relay.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 0, result.output
    assert "stripe_key" not in captured_env


def test_ticket_uses_discussion_template_when_agent_configures_one(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        repo / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"
        discussion = "--append-system-prompt {prompt}"

        """,
    )
    task_dir = repo / "tasks" / "investigate-retries"
    captured: dict[str, object] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        t = Ticket.read(task_dir / "ticket.md")
        t.frontmatter["workflow"] = "code/with-review"
        t.write(task_dir / "ticket.md")
        return _Result()

    monkeypatch.setattr("relay.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("relay.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert cmd[0] == "claude"
    assert cmd[1] == "--append-system-prompt"
    assert "Relay task — investigate-retries" in cmd[2]
    assert "Skill: bootstrap/ticket" in cmd[2]
    assert cmd[3] == "Begin"


def test_ticket_agent_override_codex_gets_kickoff(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        repo / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"
        [agents.codex]
        cli = "codex"
        auto = "exec"
        file = "AGENTS.md"
        mode = "local"

        """,
    )
    task_dir = repo / "tasks" / "investigate-retries"
    captured: dict[str, object] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        t = Ticket.read(task_dir / "ticket.md")
        t.frontmatter["workflow"] = "code/with-review"
        t.write(task_dir / "ticket.md")
        return _Result()

    monkeypatch.setattr("relay.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("relay.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(
        app, ["ticket", "Investigate retries", "--agent", "codex"]
    )
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert cmd[0] == "codex"
    assert cmd[1] == "-c"
    assert "Skill: bootstrap/ticket" in _prompt_arg(cmd)
    assert cmd[-1] == "Begin"


def test_ticket_refuses_draft_left_without_workflow(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If guided authoring hands back a draft with no workflow, `relay ticket`
    hard-refuses — a workflow-less draft can't be activated."""
    prompts: list[str] = []
    # No `on_run`: the fake agent session leaves the draft workflow-less.
    _allow_ticket_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 2, result.output
    assert "no workflow" in result.output

    ticket = Ticket.read(repo / "tasks" / "investigate-retries" / "ticket.md")
    assert ticket.workflow is None


def test_ticket_existing_active_task_is_editable_without_status_change(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Queued work",
        workflow_name="direct/body",
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


def test_ticket_reports_compose_error_for_broken_editable_task(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Broken context",
        workflow_name="direct/body",
        contexts=[],
        mode="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    ticket_path = Path(ref["path"]) / "ticket.md"
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["contexts"] = ["email/ghost"]
    ticket.write(ticket_path)

    called = False

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True

    monkeypatch.setattr("relay.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("relay.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["ticket", "broken-context"])
    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "email/ghost" in combined
    assert "broken-context" in combined
    assert "email/ghost/SKILL.md" in combined
    assert not called


def test_ticket_edits_in_progress_task(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Running work",
        workflow_name="direct/body",
        contexts=[],
        mode="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="in_progress",
    )
    prompts: list[str] = []
    _allow_ticket_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["ticket", "running-work"])
    assert result.exit_code == 0, result.output
    # in_progress no longer refused — the editing session launches, with a
    # heads-up that the ticket is in flight.
    assert "in_progress" in (result.output + (result.stderr or ""))
    assert len(prompts) == 1


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
