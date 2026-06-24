"""`relay project` — interview about a project, then create ordered drafts.

The agent session is mocked; tests cover the launcher's contract: it composes
the bootstrap/project skill, threads an optional seed, requires a TTY, and
reports/validates whatever drafts the session created.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

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
        relay_os / "bootstrap" / "project" / "ticket.md",
        """
        ---
        title: Plan a project into tickets
        autonomy: interactive
        skills:
          - bootstrap/project
        assignee: claude
        ---

        ## Description

        Persistent launch shim for project planning.
        """,
    )
    _write(
        relay_os / "skills" / "bootstrap" / "project" / "SKILL.md",
        """
        ---
        name: bootstrap/project
        description: Plan a project into an ordered set of draft tickets.
        ---

        Interview, propose, create ordered drafts.
        """,
    )
    monkeypatch.chdir(relay_os)
    return relay_os


def _allow_launch(
    monkeypatch: pytest.MonkeyPatch,
    prompts: list[str],
    *,
    on_run=None,  # type: ignore[no-untyped-def]
    returncode: int = 0,
) -> None:
    class _Result:
        pass

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        prompts.append(_prompt_arg(cmd))
        if on_run is not None:
            on_run()
        r = _Result()
        r.returncode = returncode
        return r

    monkeypatch.setattr("relay.commands.project._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("relay.commands.project.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)


def _create_drafts(*titles: str):  # type: ignore[no-untyped-def]
    """Stand in for the agent calling `relay create` per step during the session."""

    def _run() -> None:
        cfg = load_config()
        for title in titles:
            create_task(
                cfg=cfg,
                title=title,
                workflow_name=None,
                contexts=[],
                autonomy="interactive",
                owner=cfg.current_user,
                assignee=None,
                watchers=[],
                status="draft",
            )

    return _run


def test_project_composes_skill_and_logs_launch(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts: list[str] = []
    _allow_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["project"])
    assert result.exit_code == 0, result.output

    assert len(prompts) == 1
    assert "Skill: bootstrap/project" in prompts[0]
    assert "project planning launched" in (repo / "log.md").read_text()
    # No drafts created → says so plainly rather than implying success.
    assert "no draft tickets were created" in result.output


def test_project_reports_created_drafts_in_order(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts: list[str] = []
    _allow_launch(
        monkeypatch,
        prompts,
        on_run=_create_drafts("Set up test account", "Build the flow"),
    )

    result = CliRunner().invoke(app, ["project"])
    assert result.exit_code == 0, result.output

    assert "2 draft ticket(s) created" in result.output
    assert "set-up-test-account" in result.output
    assert "build-the-flow" in result.output


def test_project_threads_seed_into_prompt(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts: list[str] = []
    _allow_launch(monkeypatch, prompts)

    result = CliRunner().invoke(app, ["project", "ship the killer demo video"])
    assert result.exit_code == 0, result.output

    assert "## Project seed" in prompts[0]
    assert "ship the killer demo video" in prompts[0]


def test_project_planning_does_not_inject_relay_secrets(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Secrets are now declared inline per-ticket and flow only through the
    # `relay launch` chokepoint. The project-planning shim runs no task work and
    # declares no `secrets:`, so it must never gain a scoped Relay secret alias
    # in its env — even when a source env var the operator exported is present.
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live")
    captured_env: dict[str, str] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured_env.update(env or {})
        return _Result()

    monkeypatch.setattr("relay.commands.project._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("relay.commands.project.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["project"])
    assert result.exit_code == 0, result.output
    # No ticket-scoped secret alias is injected into the planning session.
    assert "STRIPE_KEY" not in captured_env
    assert "stripe_key" not in captured_env


def test_project_requires_tty(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "relay.commands.project._interactive_stdio_has_tty", lambda: False
    )
    result = CliRunner().invoke(app, ["project"])
    assert result.exit_code == 2
    assert "requires a TTY" in result.output


def test_project_fails_loud_on_broken_draft(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def make_broken() -> None:
        cfg = load_config()
        result = create_task(
            cfg=cfg,
            title="Broken step",
            workflow_name=None,
            contexts=[],
            autonomy="interactive",
            owner=cfg.current_user,
            assignee=None,
            watchers=[],
            status="draft",
        )
        # An invalid autonomy is a hard validation error — the session left a
        # malformed ticket and the command must surface it, not pass silently.
        path = result["path"]
        t = Ticket.read(path)
        t.frontmatter["autonomy"] = "bogus"
        t.write(path)

    prompts: list[str] = []
    _allow_launch(monkeypatch, prompts, on_run=make_broken)

    result = CliRunner().invoke(app, ["project"])
    assert result.exit_code == 2
    assert "Validation failed for" in result.output


def test_project_propagates_agent_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts: list[str] = []
    _allow_launch(monkeypatch, prompts, returncode=3)

    result = CliRunner().invoke(app, ["project"])
    assert result.exit_code == 3
    assert "Agent exited with code 3" in result.output
