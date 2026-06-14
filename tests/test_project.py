"""Project planning — `plan_project` runs the bootstrap/project skill.

There is no standalone `relay project` command; this is the reusable core that
`relay setup` calls on an already-onboarded repo. The agent session is mocked;
tests cover the helper's contract: it composes the bootstrap/project skill,
threads an optional seed, requires a TTY, and reports/validates whatever drafts
the session created.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import typer

from relay.commands.project import plan_project
from relay.config import load_config
from relay.scaffold import scaffold_task
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
        mode: interactive
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

        Interview, propose, scaffold ordered drafts.
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
    monkeypatch.setattr("relay.commands.project.subprocess.run", fake_run)


def _scaffold_drafts(*titles: str):  # type: ignore[no-untyped-def]
    """Stand in for the agent calling `relay draft` per step during the session."""

    def _run() -> None:
        cfg = load_config()
        for title in titles:
            scaffold_task(
                cfg=cfg,
                title=title,
                workflow_name=None,
                contexts=[],
                mode="interactive",
                owner=cfg.current_user,
                assignee=None,
                watchers=[],
                status="draft",
            )

    return _run


def test_plan_project_composes_skill_and_logs_launch(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prompts: list[str] = []
    _allow_launch(monkeypatch, prompts)

    plan_project(load_config())
    out = capsys.readouterr().out

    assert len(prompts) == 1
    assert "Skill: bootstrap/project" in prompts[0]
    assert "project planning launched" in (
        repo / "bootstrap" / "project" / "log.md"
    ).read_text()
    # No drafts created → says so plainly rather than implying success.
    assert "no draft tickets were created" in out


def test_plan_project_reports_created_drafts_in_order(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prompts: list[str] = []
    _allow_launch(
        monkeypatch,
        prompts,
        on_run=_scaffold_drafts("Set up test account", "Build the flow"),
    )

    plan_project(load_config())
    out = capsys.readouterr().out

    assert "2 draft ticket(s) created" in out
    assert "set-up-test-account" in out
    assert "build-the-flow" in out


def test_plan_project_threads_seed_into_prompt(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts: list[str] = []
    _allow_launch(monkeypatch, prompts)

    plan_project(load_config(), seed="ship the killer demo video")

    assert "## Project seed" in prompts[0]
    assert "ship the killer demo video" in prompts[0]


def test_plan_project_requires_tty(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "relay.commands.project._interactive_stdio_has_tty", lambda: False
    )
    with pytest.raises(typer.Exit) as exc:
        plan_project(load_config())
    assert exc.value.exit_code == 2
    assert "requires a TTY" in capsys.readouterr().err


def test_plan_project_fails_loud_on_broken_draft(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def make_broken() -> None:
        cfg = load_config()
        result = scaffold_task(
            cfg=cfg,
            title="Broken step",
            workflow_name=None,
            contexts=[],
            mode="interactive",
            owner=cfg.current_user,
            assignee=None,
            watchers=[],
            status="draft",
        )
        # An invalid mode is a hard validation error — the session left a
        # malformed ticket and the helper must surface it, not pass silently.
        path = result["path"] / "ticket.md"
        t = Ticket.read(path)
        t.frontmatter["mode"] = "bogus"
        t.write(path)

    prompts: list[str] = []
    _allow_launch(monkeypatch, prompts, on_run=make_broken)

    with pytest.raises(SystemExit) as exc:
        plan_project(load_config())
    assert exc.value.code == 2
    assert "Validation failed for" in capsys.readouterr().err


def test_plan_project_propagates_agent_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prompts: list[str] = []
    _allow_launch(monkeypatch, prompts, returncode=3)

    with pytest.raises(SystemExit) as exc:
        plan_project(load_config())
    assert exc.value.code == 3
    assert "Agent exited with code 3" in capsys.readouterr().err
