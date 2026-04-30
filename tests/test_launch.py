from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.scaffold import scaffold_task
from relay.commands.launch import build_agent_command
from relay.config import AgentType, load_config
from relay.lock import TaskLock
from relay.tasks import list_tasks


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _capture_slack(sink: list[str], json_payload):
    sink.append(json_payload["text"])
    class R:
        status_code = 200
        text = "ok"
    return R()


# --- unit: command construction ------------------------------------------------


def _agent(interactive: str, auto: str) -> AgentType:
    return AgentType(name="x", cli="my-cli", interactive=interactive, auto=auto, file="X.md", mode="local")


def test_build_command_claude_interactive(tmp_path: Path) -> None:
    prompt_file = tmp_path / "p.md"
    prompt_file.write_text("hi")
    cmd = build_agent_command(
        _agent("--append-system-prompt-file", "-p"),
        mode="interactive",
        prompt="IGNORED-TEXT",
        prompt_file=prompt_file,
    )
    assert cmd == ["my-cli", "--append-system-prompt-file", str(prompt_file), "Make it so."]


def test_build_command_claude_auto_passes_text(tmp_path: Path) -> None:
    prompt_file = tmp_path / "p.md"
    prompt_file.write_text("hi")
    cmd = build_agent_command(
        _agent("--append-system-prompt-file", "-p"),
        mode="auto",
        prompt="full prompt text",
        prompt_file=prompt_file,
    )
    assert cmd == ["my-cli", "-p", "full prompt text"]


def test_build_command_codex_like_subcommand(tmp_path: Path) -> None:
    prompt_file = tmp_path / "p.md"
    prompt_file.write_text("hi")
    cmd = build_agent_command(
        _agent("exec", "exec"),
        mode="interactive",
        prompt="full prompt text",
        prompt_file=prompt_file,
    )
    assert cmd == ["my-cli", "exec", "full prompt text"]


# --- integration: end-to-end via CliRunner with mocked subprocess --------------


@pytest.fixture
def active_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')

    monkeypatch.chdir(company)
    cfg = load_config(company)
    scaffold_task(
        cfg=cfg, title="Fix retry logic",
        workflow_name=None, contexts=[], mode="interactive",
        owner="marc", assignee="claude1", watchers=[], status="active",
    )
    return company


def test_launch_flow(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    # Agent called with --append-system-prompt-file <path> "Make it so."
    assert len(calls) == 1
    assert calls[0][0] == "claude"
    assert calls[0][1] == "--append-system-prompt-file"
    assert calls[0][2].endswith(".md")
    assert calls[0][3] == "Make it so."

    # Log entry written
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    log = (ref.path / "log.md").read_text()
    assert "launched in interactive mode" in log

    # Lock released after run
    assert not TaskLock(ref.path).path.exists()

    # Prompt temp file cleaned up
    assert not Path(calls[0][2]).exists()


def test_launch_flips_draft_to_active(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    from relay.ticket import Ticket
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["status"] = "draft"
    t.write(ref.path / "ticket.md")

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        "relay.commands.launch.subprocess.run",
        lambda cmd, env=None, check=False: _Result(),
    )
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    slack_msgs: list[str] = []
    monkeypatch.setattr(
        "relay.slack.requests.post",
        lambda url, json=None, timeout=None: _capture_slack(slack_msgs, json),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    t = Ticket.read(ref.path / "ticket.md")
    assert t.frontmatter["status"] == "active"

    log = (ref.path / "log.md").read_text()
    assert "activated (draft → active)" in log
    assert "launched in interactive mode" in log

    # The activation transition broadcasts; the session start does not.
    assert any("activated" in m and "draft → active" in m for m in slack_msgs)
    assert not any("started work" in m for m in slack_msgs)


def test_launch_active_stays_active(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-launching an already-active task does not re-log activation or post."""
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        "relay.commands.launch.subprocess.run",
        lambda cmd, env=None, check=False: _Result(),
    )
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    slack_msgs: list[str] = []
    monkeypatch.setattr(
        "relay.slack.requests.post",
        lambda url, json=None, timeout=None: _capture_slack(slack_msgs, json),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    log = (ref.path / "log.md").read_text()
    assert "activated" not in log

    # No state change happened — Slack stays quiet.
    assert slack_msgs == []


def test_launch_rejects_non_launchable_status(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Flip status to paused — only draft/active are launchable.
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    from relay.ticket import Ticket
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["status"] = "paused"
    t.write(ref.path / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2
    assert "'paused'" in result.output or "'paused'" in (result.stderr or "")


def test_launch_agent_not_in_path(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: None)
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2
    assert "not found in PATH" in (result.output + (result.stderr or ""))


# --- bootstrap shims -----------------------------------------------------------


@pytest.fixture
def bootstrap_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A relay-os/ with a bootstrap/ticket shim and a stub skill, no tasks."""
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _write(
        company / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        mode: interactive
        skill: bootstrap/ticket
        assignee: claude1
        ---

        ## Description

        Persistent launch shim for the bootstrap/ticket skill.
        """,
    )
    _write(
        company / "skills" / "bootstrap" / "ticket" / "SKILL.md",
        """
        ---
        name: bootstrap/ticket
        description: Author a Relay task.
        ---

        Interview, scaffold, fill in the ticket. Stop.
        """,
    )
    monkeypatch.chdir(company)
    return company


def test_launch_bootstrap_skips_status_and_lock(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["prompt"] = Path(cmd[2]).read_text()
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output

    # No lock file left behind; in fact none was ever written.
    assert not (bootstrap_repo / "bootstrap" / "ticket" / "task.lock").exists()

    # Skill body composed into the prompt.
    prompt = captured["prompt"]
    assert isinstance(prompt, str)
    assert "Skill: bootstrap/ticket" in prompt
    assert "Interview, scaffold, fill in the ticket." in prompt
    # Header still uses the bootstrap/<name> id_slug.
    assert "bootstrap/ticket" in prompt

    # log.md was created and recorded the launch.
    log = (bootstrap_repo / "bootstrap" / "ticket" / "log.md").read_text()
    assert "launched in interactive mode" in log


def test_launch_bootstrap_unknown_shim(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/does-not-exist"])
    assert result.exit_code == 2
    assert "bootstrap/does-not-exist" in (result.output + (result.stderr or ""))


def test_launch_bootstrap_factory_scaffolds_and_launches(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay launch bootstrap/ticket "title"` scaffolds a draft task
    seeded from the shim, then launches the agent against the new task."""
    captured: dict[str, object] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["prompt"] = Path(cmd[2]).read_text()
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    slack_msgs: list[str] = []
    monkeypatch.setattr(
        "relay.slack.requests.post",
        lambda url, json=None, timeout=None: _capture_slack(slack_msgs, json),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket", "Investigate flaky tests"])
    assert result.exit_code == 0, result.output

    # Factory mode broadcasts the new draft. No draft → active flip
    # because the bootstrap-skill ticket stays draft.
    assert len(slack_msgs) == 1
    assert "created investigate-flaky-tests" in slack_msgs[0]
    assert "status=draft" in slack_msgs[0]

    # A new task dir got scaffolded under tasks/.
    cfg = load_config(bootstrap_repo)
    refs = list_tasks(cfg)
    assert len(refs) == 1
    new_ref = refs[0]
    assert new_ref.slug == "investigate-flaky-tests"

    # Frontmatter inherited from the shim, status=draft, title set.
    from relay.ticket import Ticket
    t = Ticket.read(new_ref.path / "ticket.md")
    assert t.frontmatter["title"] == "Investigate flaky tests"
    assert t.frontmatter["status"] == "draft"
    assert t.frontmatter["mode"] == "interactive"
    assert t.frontmatter["assignee"] == "claude1"
    assert t.frontmatter["skill"] == "bootstrap/ticket"

    # Skill body composed into the prompt for the new task.
    prompt = captured["prompt"]
    assert isinstance(prompt, str)
    assert "Skill: bootstrap/ticket" in prompt
    assert "Interview, scaffold, fill in the ticket." in prompt

    # Launch went against the new task, not the shim.
    log = (new_ref.path / "log.md").read_text()
    assert "launched in interactive mode" in log
    # Lock for the new task was acquired and released.
    assert not TaskLock(new_ref.path).path.exists()


def test_launch_title_arg_rejected_for_regular_tasks(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic", "Some title"])
    assert result.exit_code == 2
    assert "bootstrap" in (result.output + (result.stderr or ""))
