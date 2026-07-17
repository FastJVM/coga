from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from conftest import seed_direct_body_workflow
from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.logfile import task_log_lines
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _prompt_arg(cmd: list[str]) -> str:
    for arg in cmd:
        if isinstance(arg, str) and arg.startswith("# Coga task"):
            return arg
        if isinstance(arg, str) and arg.startswith("developer_instructions=# Coga task"):
            return arg.removeprefix("developer_instructions=")
    raise AssertionError(f"No Coga prompt in argv: {cmd!r}")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        mode = "local"

        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    _write(
        coga_os / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        skills:
          - bootstrap/ticket
        assignee: claude
        ---

        ## Description

        Persistent launch target.
        """,
    )
    _write(
        coga_os / "skills" / "bootstrap" / "ticket" / "SKILL.md",
        """
        ---
        name: bootstrap/ticket
        description: Author a Coga task.
        ---

        Interview and fill the ticket.
        """,
    )
    seed_direct_body_workflow(coga_os)
    monkeypatch.chdir(coga_os)
    return coga_os


def _allow_ticket_launch(
    monkeypatch: pytest.MonkeyPatch,
    prompts: list[str],
    *,
    on_run=None,  # type: ignore[no-untyped-def]
) -> None:
    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        prompts.append(_prompt_arg(cmd))
        if on_run is not None:
            on_run()
        return _Result()

    monkeypatch.setattr("coga.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)


def test_ticket_title_creates_draft_and_launches_authoring(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    ticket_path = repo / "tasks" / "investigate-retries.md"

    def author_workflow() -> None:
        # Simulate the bootstrap/ticket skill picking a workflow: guided
        # authoring of a draft must land on a workflow or `coga ticket`
        # hard-refuses the result.
        t = Ticket.read(ticket_path)
        t.frontmatter["workflow"] = "code/with-review"
        t.write(ticket_path)

    _allow_ticket_launch(monkeypatch, prompts, on_run=author_workflow)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 0, result.output

    ticket = Ticket.read(ticket_path)
    assert ticket.status == "draft"
    assert ticket.title == "Investigate retries"
    assert ticket.skills == []
    log = "\n".join(task_log_lines(load_config(repo), "investigate-retries"))
    assert "ticket authoring launched" in log

    assert len(prompts) == 1
    assert "Coga task — investigate-retries" in prompts[0]
    assert "Status: draft" in prompts[0]
    assert "Skill: bootstrap/ticket" in prompts[0]


def test_ticket_path_title_drafts_in_subdirectory(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`coga ticket "v2/<title>"` drafts under tasks/v2/, same path syntax as create."""
    prompts: list[str] = []
    ticket_path = repo / "tasks" / "v2" / "build-the-flow.md"

    def author_workflow() -> None:
        t = Ticket.read(ticket_path)
        t.frontmatter["workflow"] = "code/with-review"
        t.write(ticket_path)

    _allow_ticket_launch(monkeypatch, prompts, on_run=author_workflow)

    result = CliRunner().invoke(app, ["ticket", "v2/Build the flow"])
    assert result.exit_code == 0, result.output

    assert ticket_path.is_file()
    ticket = Ticket.read(ticket_path)
    assert ticket.status == "draft"
    assert ticket.title == "Build the flow"
    assert ticket.frontmatter["slug"] == "v2/build-the-flow"
    assert "Coga task — v2/build-the-flow" in prompts[0]


def test_ticket_authoring_does_not_inject_coga_secrets(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Secrets are now declared inline per-ticket and flow only through the
    # `coga launch` chokepoint. The authoring ticket runs no task work and
    # declares no `secrets:`, so it must never gain a scoped Coga secret alias
    # in its env — even when a source env var the operator exported is present.
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live")
    ticket_path = repo / "tasks" / "investigate-retries.md"
    captured_env: dict[str, str] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured_env.update(env or {})
        t = Ticket.read(ticket_path)
        t.frontmatter["workflow"] = "code/with-review"
        t.write(ticket_path)
        return _Result()

    monkeypatch.setattr("coga.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 0, result.output
    # No ticket-scoped secret alias is injected into the authoring session.
    assert "STRIPE_KEY" not in captured_env
    assert "stripe_key" not in captured_env


def test_ticket_uses_discussion_template_when_agent_configures_one(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        repo / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        mode = "local"
        discussion = "--append-system-prompt {prompt}"

        """,
    )
    ticket_path = repo / "tasks" / "investigate-retries.md"
    captured: dict[str, object] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        t = Ticket.read(ticket_path)
        t.frontmatter["workflow"] = "code/with-review"
        t.write(ticket_path)
        return _Result()

    monkeypatch.setattr("coga.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert cmd[0] == "claude"
    assert cmd[1] == "--append-system-prompt"
    assert "Coga task — investigate-retries" in cmd[2]
    assert "Skill: bootstrap/ticket" in cmd[2]
    # New-title launch → the create kickoff token, which the skill greets off of.
    assert cmd[3] == "Begin (new ticket)"


def test_ticket_agent_override_codex_gets_kickoff(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        repo / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        mode = "local"
        [agents.codex]
        cli = "codex"
        file = "AGENTS.md"
        mode = "local"

        """,
    )
    ticket_path = repo / "tasks" / "investigate-retries.md"
    captured: dict[str, object] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        t = Ticket.read(ticket_path)
        t.frontmatter["workflow"] = "code/with-review"
        t.write(ticket_path)
        return _Result()

    monkeypatch.setattr("coga.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(
        app, ["ticket", "Investigate retries", "--agent", "codex"]
    )
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert cmd[0] == "codex"
    assert cmd[1] == "-c"
    assert "Skill: bootstrap/ticket" in _prompt_arg(cmd)
    # New-title launch → the create kickoff token (appended last, after the
    # discussion-template prompt).
    assert cmd[-1] == "Begin (new ticket)"


def test_ticket_refuses_draft_left_without_workflow(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If guided authoring hands back a draft with no workflow, `coga ticket`
    hard-refuses — a workflow-less draft can't be activated."""
    prompts: list[str] = []
    # No `on_run`: the fake agent session leaves the draft workflow-less.
    _allow_ticket_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 2, result.output
    assert "no workflow" in result.output

    ticket = Ticket.read(repo / "tasks" / "investigate-retries.md")
    assert ticket.workflow is None


def test_ticket_reports_post_exit_validation_errors(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Schema breakage authored by the interview fails before returning."""
    prompts: list[str] = []
    ticket_path = repo / "tasks" / "investigate-retries.md"

    def author_broken_ticket() -> None:
        t = Ticket.read(ticket_path)
        t.frontmatter["workflow"] = "direct/body"
        t.frontmatter["contexts"] = ["email/ghost"]
        t.write(ticket_path)

    _allow_ticket_launch(monkeypatch, prompts, on_run=author_broken_ticket)

    result = CliRunner().invoke(app, ["ticket", "Investigate retries"])
    assert result.exit_code == 2, result.output
    combined = result.output + (result.stderr or "")
    assert "task validation failed after ticket authoring" in combined
    assert "email/ghost" in combined


def test_ticket_requires_tty_before_spawning(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True

    monkeypatch.setattr("coga.commands.ticket._interactive_stdio_has_tty", lambda: False)
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["ticket"])
    assert result.exit_code == 2
    assert "requires a TTY" in (result.output + (result.stderr or ""))
    assert called is False


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
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    prompts: list[str] = []
    _allow_ticket_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["ticket", "queued-work"])
    assert result.exit_code == 0, result.output

    ticket = Ticket.read(Path(ref["path"]))
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
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    ticket_path = Path(ref["path"])
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["contexts"] = ["email/ghost"]
    ticket.write(ticket_path)

    called = False

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True

    monkeypatch.setattr("coga.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

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


def _capture_ticket_launch(
    monkeypatch: pytest.MonkeyPatch,
    captured: dict[str, object],
    *,
    on_run=None,  # type: ignore[no-untyped-def]
) -> None:
    """Like `_allow_ticket_launch`, but captures the spawned argv (`cmd`) so a
    test can assert the kickoff token — the last argv element — directly."""

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        if on_run is not None:
            on_run()
        return _Result()

    monkeypatch.setattr("coga.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)


def test_ticket_without_target_launches_bootstrap_interview(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    _capture_ticket_launch(monkeypatch, captured)

    result = CliRunner().invoke(app, ["ticket"])
    assert result.exit_code == 0, result.output

    prompt = _prompt_arg(captured["cmd"])
    assert "Coga task — bootstrap/ticket" in prompt
    assert "Skill: bootstrap/ticket" in prompt
    # No-target empty interview keeps the bare kickoff — the skill detects this
    # shape structurally (bootstrap/ticket header, no Status line).
    assert captured["cmd"][-1] == "Begin"


def test_ticket_existing_draft_greets_as_edit_not_create(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: an existing draft opened for authoring greets as an *edit*,
    keyed off the CLI's resolve outcome — not misclassified as a new ticket
    because its body is empty (the `coga create` batch state). The kickoff token
    the CLI appends carries the create-vs-edit decision to the skill."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Batch draft",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
    )
    captured: dict[str, object] = {}
    _capture_ticket_launch(monkeypatch, captured)

    result = CliRunner().invoke(app, ["ticket", "batch-draft"])
    assert result.exit_code == 0, result.output
    assert captured["cmd"][-1] == "Begin (editing existing ticket)"


def test_ticket_nested_bare_leaf_edits_existing_not_duplicate(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`coga ticket <bare-leaf>` for a nested ticket edits the existing ticket
    rather than silently scaffolding a duplicate top-level draft — `resolve_task`
    only matches a nested task by its full `<dir>/<slug>`, so `coga ticket`
    falls back to a bare-leaf scan."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Relaunch",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
        directory="marketing",
    )
    captured: dict[str, object] = {}
    _capture_ticket_launch(monkeypatch, captured)

    result = CliRunner().invoke(app, ["ticket", "relaunch"])
    assert result.exit_code == 0, result.output

    # Greeted as an edit of the existing nested ticket...
    assert captured["cmd"][-1] == "Begin (editing existing ticket)"
    assert "Coga task — marketing/relaunch" in _prompt_arg(captured["cmd"])
    # ...and did NOT scaffold a duplicate top-level draft.
    assert not (repo / "tasks" / "relaunch.md").exists()
    assert (repo / "tasks" / "marketing" / "relaunch.md").is_file()


def test_ticket_ambiguous_bare_leaf_bails_without_launching(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two nested tickets share a leaf: a bare-leaf `coga ticket` can't tell
    which is meant, so it bails listing both qualified slugs rather than guessing
    or scaffolding a duplicate."""
    cfg = load_config(repo)
    for directory in ("marketing", "growth"):
        create_task(
            cfg=cfg,
            title="Relaunch",
            workflow_name="direct/body",
            contexts=[],
            owner="marc",
            assignee="claude",
            watchers=[],
            status="draft",
            directory=directory,
        )
    called = False

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True

    monkeypatch.setattr("coga.commands.ticket._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["ticket", "relaunch"])
    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "growth/relaunch" in combined
    assert "marketing/relaunch" in combined
    assert not called
    # No duplicate top-level draft was scaffolded.
    assert not (repo / "tasks" / "relaunch.md").exists()
