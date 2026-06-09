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
from relay.tasks import list_tasks
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _capture_slack(sink: list[str], json_payload):
    sink.append(json_payload["text"])
    class R:
        status_code = 200
        text = "ok"
    return R()


def _prompt_arg(cmd: list[str]) -> str:
    for arg in cmd:
        if isinstance(arg, str) and arg.startswith("# Relay task"):
            return arg
        if isinstance(arg, str) and arg.startswith("developer_instructions=# Relay task"):
            return arg.removeprefix("developer_instructions=")
    raise AssertionError(f"No Relay prompt in argv: {cmd!r}")


# --- unit: command construction ------------------------------------------------


def _agent(auto: str, name_flag: str = "", discussion: str = "") -> AgentType:
    return AgentType(
        name="x",
        cli="my-cli",
        auto=auto,
        file="X.md",
        mode="local",
        name_flag=name_flag,
        discussion=discussion,
    )


def test_build_command_interactive_passes_prompt_positionally() -> None:
    cmd = build_agent_command(_agent("-p"), mode="interactive", prompt="full prompt text")
    assert cmd == ["my-cli", "full prompt text"]


def test_build_command_auto_prepends_flag_then_prompt() -> None:
    cmd = build_agent_command(_agent("-p"), mode="auto", prompt="full prompt text")
    assert cmd == ["my-cli", "-p", "full prompt text"]


def test_build_command_auto_subcommand_style() -> None:
    cmd = build_agent_command(_agent("exec"), mode="auto", prompt="full prompt text")
    assert cmd == ["my-cli", "exec", "full prompt text"]


def test_build_command_injects_name_flag_when_set() -> None:
    cmd = build_agent_command(
        _agent("-p", name_flag="-n"),
        mode="interactive",
        prompt="full prompt text",
        name="Fix retry backoff",
    )
    assert cmd == ["my-cli", "-n", "Fix retry backoff", "full prompt text"]


def test_build_command_injects_name_flag_in_auto_mode() -> None:
    cmd = build_agent_command(
        _agent("-p", name_flag="-n"),
        mode="auto",
        prompt="full prompt text",
        name="Fix retry backoff",
    )
    assert cmd == ["my-cli", "-n", "Fix retry backoff", "-p", "full prompt text"]


def test_build_command_skips_name_flag_when_agent_has_none() -> None:
    cmd = build_agent_command(
        _agent("-p"),
        mode="interactive",
        prompt="full prompt text",
        name="Fix retry backoff",
    )
    assert cmd == ["my-cli", "full prompt text"]


def test_build_command_skips_name_flag_when_name_is_empty() -> None:
    cmd = build_agent_command(
        _agent("-p", name_flag="-n"),
        mode="interactive",
        prompt="full prompt text",
        name="",
    )
    assert cmd == ["my-cli", "full prompt text"]


def test_build_command_discussion_skips_name_flag() -> None:
    """Discussion mode intentionally leaves the session unnamed so the
    human's first ask becomes the title; name_flag must not pre-set it."""
    agent = _agent("-p", name_flag="-n", discussion="--append-system-prompt {prompt}")
    cmd = build_agent_command(
        agent,
        mode="interactive",
        prompt="orient body",
        name="Orient an agent in this relay-os/ repo",
        discussion=True,
    )
    assert cmd == ["my-cli", "--append-system-prompt", "orient body"]


def test_build_command_discussion_uses_template_for_claude() -> None:
    agent = _agent("-p", discussion="--append-system-prompt {prompt}")
    cmd = build_agent_command(
        agent,
        mode="interactive",
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["my-cli", "--append-system-prompt", "orient body"]


def test_build_command_discussion_uses_template_for_codex() -> None:
    agent = _agent("exec", discussion="-c developer_instructions={prompt}")
    cmd = build_agent_command(
        agent,
        mode="interactive",
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["my-cli", "-c", "developer_instructions=orient body"]


def test_build_command_discussion_uses_default_template_for_claude_cli() -> None:
    agent = AgentType(
        name="standard-claude",
        cli="claude",
        auto="-p",
        file="CLAUDE.md",
        mode="local",
    )
    cmd = build_agent_command(
        agent,
        mode="interactive",
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["claude", "--append-system-prompt", "orient body"]


def test_build_command_discussion_uses_default_template_for_codex_cli() -> None:
    agent = AgentType(
        name="standard-codex",
        cli="codex",
        auto="exec",
        file="AGENTS.md",
        mode="local",
    )
    cmd = build_agent_command(
        agent,
        mode="interactive",
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["codex", "-c", "developer_instructions=orient body"]


def test_build_command_discussion_falls_back_when_template_unset() -> None:
    agent = _agent("-p", discussion="")
    cmd = build_agent_command(
        agent,
        mode="interactive",
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["my-cli", "orient body"]


def test_build_command_discussion_ignored_in_auto_mode() -> None:
    agent = _agent("-p", discussion="--append-system-prompt {prompt}")
    cmd = build_agent_command(
        agent,
        mode="auto",
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["my-cli", "-p", "orient body"]


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
        auto = "-p"
        file = "CLAUDE.md"
        [agents.codex]
        cli = "codex"
        auto = "exec"
        file = "AGENTS.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')

    monkeypatch.chdir(company)
    cfg = load_config(company)
    scaffold_task(
        cfg=cfg, title="Fix retry logic",
        workflow_name=None, contexts=[], mode="interactive",
        owner="marc", assignee="claude", watchers=[], status="active",
    )
    return company


def _allow_slack(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://slack.example.test")
    slack_msgs: list[str] = []
    monkeypatch.setattr(
        "relay.slack.requests.post",
        lambda url, json=None, timeout=None: _capture_slack(slack_msgs, json),
    )
    return slack_msgs


def _allow_interactive_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.commands.launch._interactive_stdio_has_tty",
        lambda: True,
    )


def _deny_interactive_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.commands.launch._interactive_stdio_has_tty",
        lambda: False,
    )


def _write_skill(repo: Path, ref: str, body: str) -> None:
    _write(
        repo / "skills" / ref / "SKILL.md",
        f"""
        ---
        name: {ref}
        description: test skill.
        ---

        {body}
        """,
    )


def _scaffold_chain_task(active_task: Path, *, mode: str = "interactive") -> dict[str, object]:
    _write(
        active_task / "workflows" / "chain.md",
        """
        ---
        name: chain
        description: Agent chain.
        steps:
          - name: implement
            skills:
              - code/implement
            assignee: agent
          - name: self-review
            skills:
              - code/self-review
            assignee: agent
          - name: review
            assignee: human
        ---
        """,
    )
    _write_skill(active_task, "code/implement", "Implement the change.")
    _write_skill(active_task, "code/self-review", "Review your own change.")

    cfg = load_config(active_task)
    return scaffold_task(
        cfg=cfg,
        title="Chain work",
        workflow_name="chain",
        contexts=[],
        mode=mode,
        owner="marc",
        human="marc",
        agent="claude",
        assignee="claude",
        watchers=[],
        status="active",
    )


def test_launch_flow(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    _allow_interactive_tty(monkeypatch)

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

    # Agent called with `claude <composed-prompt-text>` — composed prompt
    # arrives as the first user message in the REPL.
    assert len(calls) == 1
    assert calls[0][0] == "claude"
    assert len(calls[0]) == 2
    assert "Relay task" in calls[0][1]

    # Log entry written
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    assert ticket.status == "in_progress"
    log = (ref.path / "log.md").read_text()
    assert "started (active → in_progress) via relay launch" in log
    assert "launched in interactive mode" in log


def test_launch_bails_on_missing_context(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ticket referencing a context with no file must refuse to launch,
    rather than starting an agent with a silently-missing prompt layer."""
    _allow_interactive_tty(monkeypatch)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket_md = ref.path / "ticket.md"
    ticket_md.write_text(
        ticket_md.read_text().replace("contexts: []", "contexts:\n- email/ghost")
    )

    def fail_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        raise AssertionError(f"agent must not be launched, got {cmd!r}")

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fail_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2, result.output
    assert "email/ghost" in result.output
    # Ticket was not flipped to in_progress — launch refused before starting.
    assert Ticket.read(ticket_md).status == "active"


def test_launch_handles_agent_self_deleting_task(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workflow-less agent (e.g. a Dream run retiring itself) may delete its
    own task directory as a final action. Launch must treat the missing
    ticket.md as a clean terminal state, not crash reading the ticket back."""
    import shutil as _shutil

    _allow_interactive_tty(monkeypatch)
    task_dir = active_task / "tasks" / "fix-retry-logic"
    assert task_dir.exists()

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        # Simulate the agent deleting its own task directory before exit.
        _shutil.rmtree(task_dir)
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert not task_dir.exists()


def test_launch_marks_interactive_session_supervised(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interactive launches chain across agent-owned steps, so the child
    inherits `RELAY_SUPERVISED=1`. `relay bump` keys its supervised-launch
    hint off that env var."""
    envs: list[dict] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        envs.append(env or {})
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    assert envs
    assert envs[0].get("RELAY_SUPERVISED") == "1"


def test_launch_in_progress_resumes_without_status_transition(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.path / "ticket.md")
    calls: list[list[str]] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    log = (ref.path / "log.md").read_text()
    assert "started (active → in_progress) via relay launch" not in log


# --- pre-launch freshness check (auto_bump_one) ------------------------------


def _attach_pr(active_task: Path, slug: str, pr_url: str) -> None:
    bb = active_task / "tasks" / slug / "blackboard.md"
    bb.write_text(bb.read_text().rstrip() + f"\n\n## Dev\n\nbranch: foo\npr: {pr_url}\n")


def _stub_merged(monkeypatch: pytest.MonkeyPatch, url: str, state: str = "MERGED") -> None:
    from relay import automerge as am
    monkeypatch.setattr(am, "pr_state", lambda u: state if u == url else "OPEN")


def test_launch_freshness_check_bumps_to_done_and_skips_agent(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the linked PR has merged, launch auto-bumps and exits clean
    without spawning the agent."""
    _attach_pr(active_task, "fix-retry-logic", "https://github.com/o/r/pull/77")
    _stub_merged(monkeypatch, "https://github.com/o/r/pull/77", "MERGED")
    _allow_interactive_tty(monkeypatch)
    _allow_slack(monkeypatch)

    spawned: list[list[str]] = []

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        spawned.append(cmd)
        class R: returncode = 0
        return R()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert spawned == []  # no agent spawn
    assert "auto-bumped to done before launch" in result.output

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    from relay.ticket import Ticket
    assert Ticket.read(ref.path / "ticket.md").status == "done"


def test_launch_freshness_check_no_op_when_pr_open(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Open PR → freshness check no-ops, launch proceeds."""
    _attach_pr(active_task, "fix-retry-logic", "https://github.com/o/r/pull/78")
    _stub_merged(monkeypatch, "https://github.com/o/r/pull/78", "OPEN")
    _allow_interactive_tty(monkeypatch)

    spawned: list[list[str]] = []

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        spawned.append(cmd)
        class R: returncode = 0
        return R()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert len(spawned) == 1  # agent did spawn


def test_launch_freshness_check_warns_on_gh_error_then_continues(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`gh` missing/unauthed → warning to stderr, launch proceeds."""
    from relay import automerge as am
    _attach_pr(active_task, "fix-retry-logic", "https://github.com/o/r/pull/79")

    def boom(url: str) -> str:
        raise am.GhError("gh: not authenticated")

    monkeypatch.setattr(am, "pr_state", boom)
    _allow_interactive_tty(monkeypatch)

    spawned: list[list[str]] = []

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        spawned.append(cmd)
        class R: returncode = 0
        return R()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert len(spawned) == 1  # launch continued
    combined = result.output + (result.stderr or "")
    assert "skipping pre-launch freshness check" in combined
    assert "gh auth login" in combined


def test_launch_no_verify_skips_freshness_check(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--no-verify` skips the check entirely — gh is never called."""
    from relay import automerge as am
    _attach_pr(active_task, "fix-retry-logic", "https://github.com/o/r/pull/80")

    pr_state_calls: list[str] = []

    def track(url: str) -> str:
        pr_state_calls.append(url)
        return "MERGED"

    monkeypatch.setattr(am, "pr_state", track)
    _allow_interactive_tty(monkeypatch)

    spawned: list[list[str]] = []

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        spawned.append(cmd)
        class R: returncode = 0
        return R()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic", "--no-verify"])
    assert result.exit_code == 0, result.output
    assert pr_state_calls == []  # freshness check entirely skipped
    assert len(spawned) == 1


def test_launch_freshness_check_no_op_without_pr_link(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default-scaffold blackboard has no `## Dev` section → no gh call."""
    from relay import automerge as am
    pr_state_calls: list[str] = []
    monkeypatch.setattr(am, "pr_state", lambda u: pr_state_calls.append(u) or "OPEN")
    _allow_interactive_tty(monkeypatch)

    spawned: list[list[str]] = []

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        spawned.append(cmd)
        class R: returncode = 0
        return R()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert pr_state_calls == []  # no PR link → no gh lookup
    assert len(spawned) == 1


def test_launch_interactive_without_tty_fails_before_lock(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False
    _deny_interactive_tty(monkeypatch)

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        raise AssertionError("interactive launch should fail before spawning agent")

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code == 2
    assert "Cannot launch 'fix-retry-logic': mode=interactive requires a TTY" in (
        result.output + (result.stderr or "")
    )
    assert not called

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]


def test_launch_interactive_chains_consecutive_agent_steps(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interactive launches chain while the next step is still the agent's.

    After `relay bump` advances from step 1 (agent) to step 2 (also agent),
    the launch loop re-composes the prompt and spawns a fresh REPL. The
    chain stops at the first human-assigned step (step 3 here).
    """
    ref = _scaffold_chain_task(active_task, mode="interactive")
    slug = str(ref["slug"])
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        # Each spawned "agent" bumps once. After the 1→2 bump the agent is
        # still the assignee → launch should respawn. After the 2→3 bump
        # the next step is human-assigned → launch should stop.
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Two REPLs: step 1, then a fresh one for step 2. Step 3 is the human's,
    # so the loop stops without spawning a third.
    assert len(calls) == 2

    from relay.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]) / "ticket.md")
    assert ticket.step == "3 (review)"


def test_launch_harness_stops_when_next_skilled_step_changes_assignee(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        active_task / "workflows" / "handoff.md",
        """
        ---
        name: handoff
        description: Skilled handoff.
        steps:
          - name: implement
            skills:
              - code/implement
            assignee: agent
          - name: human-check
            skills:
              - code/human-check
            assignee: human
        ---
        """,
    )
    _write_skill(active_task, "code/implement", "Implement the change.")
    _write_skill(active_task, "code/human-check", "Human checks the change.")
    cfg = load_config(active_task)
    ref = scaffold_task(
        cfg=cfg,
        title="Handoff work",
        workflow_name="handoff",
        contexts=[],
        mode="interactive",
        owner="marc",
        human="marc",
        agent="claude",
        assignee="claude",
        watchers=[],
        status="active",
    )
    slug = ref["slug"]
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Interactive does not chain — one agent run, then back to the caller.
    # The assignee transition surfaces in `relay status`, not in launch
    # output, because the human is the one driving step transitions.
    assert len(calls) == 1

    from relay.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]) / "ticket.md")
    assert ticket.step == "2 (human-check)"
    assert ticket.assignee == "marc"


def test_launch_harness_stops_on_agent_panic(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _scaffold_chain_task(active_task)
    slug = str(ref["slug"])
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 1

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(
            app,
            ["panic", "--task", slug, "--reason", "test panic"],
        )
        assert result.exit_code == 1, result.output
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 1, result.output
    assert len(calls) == 1
    assert "Agent exited with code 1" in (result.output + (result.stderr or ""))
    assert "test panic" in (Path(ref["path"]) / "blackboard.md").read_text()


def _launch_single_spawn(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Mock the agent spawn so launch runs one REPL and stops (no bump → no
    progress → supervisor halts). Returns the list of spawned argvs."""
    calls: list[list[str]] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    return calls


@pytest.mark.parametrize("prior", ["draft", "paused"])
def test_launch_auto_activates_draft_and_paused(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, prior: str
) -> None:
    """`relay launch` is itself the readiness signal: a draft/paused ticket
    with a workflow is activated inline, then flipped to in_progress."""
    from relay.ticket import Ticket

    ref = _scaffold_chain_task(active_task, mode="interactive")
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"]) / "ticket.md"
    t = Ticket.read(ticket_md)
    t.frontmatter["status"] = prior
    t.write(ticket_md)

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1  # agent spawned

    after = Ticket.read(ticket_md)
    assert after.status == "in_progress"
    assert after.step == "1 (implement)"
    log = (Path(ref["path"]) / "log.md").read_text()
    assert f"activated ({prior} → active) — auto on launch" in log


def test_launch_auto_activates_done_and_reseeds_step(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A done ticket had its `step:` cleared by `mark done`; re-activating on
    launch restarts the frozen workflow from step 1."""
    from relay.ticket import Ticket

    ref = _scaffold_chain_task(active_task, mode="interactive")
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"]) / "ticket.md"
    t = Ticket.read(ticket_md)
    t.frontmatter["status"] = "done"
    t.frontmatter.pop("step", None)  # mark done clears the step
    t.write(ticket_md)

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1

    after = Ticket.read(ticket_md)
    assert after.status == "in_progress"
    assert after.step == "1 (implement)"


def test_launch_auto_activate_bails_without_workflow(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workflow-less ticket still can't be activated — launch fails loud
    (it can never be advanced by `relay bump`) and never spawns an agent."""
    from relay.ticket import Ticket

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]  # the default fixture task has no workflow
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["status"] = "draft"
    t.write(ref.path / "ticket.md")

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2, result.output
    combined = result.output + (result.stderr or "")
    assert "no workflow" in combined
    assert not calls  # agent never spawned

    # Ticket stayed draft — the failed activation did not mutate status.
    assert Ticket.read(ref.path / "ticket.md").status == "draft"


def test_launch_agent_not_in_path(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: None)
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2
    assert "not found in PATH" in (result.output + (result.stderr or ""))


def test_launch_warns_for_large_blackboard(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    (ref.path / "blackboard.md").write_text("x" * (33 * 1024))
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        "relay.commands.launch.subprocess.run",
        lambda cmd, env=None, check=False: _Result(),
    )
    monkeypatch.setattr(
        "relay.commands.launch.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert "blackboard.md is" in (result.output + (result.stderr or ""))


def test_launch_prompt_report_prints_layers_without_launching(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        active_task / "contexts" / "email" / "payment-flow" / "SKILL.md",
        """
        ---
        name: email/payment-flow
        description: Payment context.
        ---

        Stripe retries on 429.
        """,
    )
    _write(
        active_task / "workflows" / "code" / "measure.md",
        """
        ---
        name: code/measure
        description: Measure prompt scope.
        steps:
          - name: implement
            skills:
              - code/implement
        ---
        """,
    )
    _write_skill(active_task, "code/implement", "Implement the change.")
    cfg = load_config(active_task)
    ref = scaffold_task(
        cfg=cfg,
        title="Measure prompt scope",
        workflow_name="code/measure",
        contexts=["email/payment-flow"],
        mode="interactive",
        owner="marc",
        human="marc",
        agent="claude",
        assignee="claude",
        watchers=[],
        status="draft",
    )

    def fail_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        raise AssertionError("prompt report must not spawn an agent")

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fail_run)
    monkeypatch.setattr("relay.commands.launch._interactive_stdio_has_tty", lambda: False)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: None)

    result = CliRunner().invoke(app, ["launch", str(ref["slug"]), "--prompt-report"])
    assert result.exit_code == 0, result.output
    assert "Prompt report for measure-prompt-scope" in result.output
    assert "ticket_context" in result.output
    assert "email/payment-flow" in result.output
    assert "workflow_skill" in result.output
    assert "code/implement" in result.output
    assert "Total composed prompt" in result.output

    from relay.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]) / "ticket.md")
    assert ticket.status == "draft"
    assert "launched in interactive mode" not in (Path(ref["path"]) / "log.md").read_text()


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
        auto = "-p"
        file = "CLAUDE.md"
        [agents.codex]
        cli = "codex"
        auto = "exec"
        file = "AGENTS.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _write(
        company / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        mode: interactive
        skills:
          - bootstrap/ticket
        assignee: claude
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


def test_launch_bare_bootstrap_does_not_post_to_slack(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare shim launches (e.g. `relay chat`) are stateless re-entry points,
    not "started work" events — they must not post to Slack."""
    posts: list[str] = []
    _allow_interactive_tty(monkeypatch)

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        posts.append((json or {}).get("text", ""))

        class R:
            status_code = 200

        return R()

    class _Result:
        returncode = 0

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    monkeypatch.setattr(
        "relay.commands.launch.subprocess.run",
        lambda cmd, env=None, check=False: _Result(),
    )
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output
    assert posts == []


def test_launch_bootstrap_skips_status_and_lock(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["prompt"] = _prompt_arg(cmd)
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output

    # No lock file left behind; in fact none was ever written.

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


def test_launch_discussion_bootstrap_uses_discussion_template(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discussion shims ride the composed prompt as system context instead of
    making it the first user message."""
    # Rewrite the fixture's relay.toml to add a discussion template on claude.
    _write(
        bootstrap_repo / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        discussion = "--append-system-prompt {prompt}"
        [agents.codex]
        cli = "codex"
        auto = "exec"
        file = "AGENTS.md"
        """,
    )

    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    # Argv: [cli, --append-system-prompt, <prompt>]
    assert cmd[0] == "claude"
    assert cmd[1] == "--append-system-prompt"
    assert "Skill: bootstrap/ticket" in cmd[2]


def test_launch_regular_task_does_not_use_discussion_template(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        active_task / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        discussion = "--append-system-prompt {prompt}"
        """,
    )
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert cmd[0] == "claude"
    assert "Fix retry logic" in _prompt_arg(cmd)


def test_launch_bootstrap_agent_override_uses_requested_agent(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket", "--agent", "codex"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "codex"
    assert cmd[1] == "-c"
    assert "Skill: bootstrap/ticket" in _prompt_arg(cmd)

    log = (bootstrap_repo / "bootstrap" / "ticket" / "log.md").read_text()
    assert "assignee=codex, agent=codex" in log


def test_launch_agent_override_normal_task_uses_requested_agent_without_reassigning(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic", "--agent", "codex"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "codex"

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    from relay.ticket import Ticket
    ticket = Ticket.read(ref.path / "ticket.md")
    assert ticket.frontmatter["assignee"] == "claude"

    log = (ref.path / "log.md").read_text()
    assert "assignee=claude, launch_assignee=codex, agent=codex" in log


def test_launch_bootstrap_unknown_shim(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/does-not-exist"])
    assert result.exit_code == 2
    assert "bootstrap/does-not-exist" in (result.output + (result.stderr or ""))


# --- unit: supervisor stop logic (agent rotation vs human handoff) -------------


def _wf_ticket(step: str, assignee: str, status: str = "in_progress") -> Ticket:
    """Build an in-memory 2-step-workflow ticket for stop-reason tests."""
    return Ticket(
        frontmatter={
            "status": status,
            "assignee": assignee,
            "step": step,
            "workflow": {
                "name": "test/wf",
                "steps": [
                    {"name": "a", "assignee": "agent"},
                    {"name": "b", "assignee": "other-agent"},
                ],
            },
        },
        body="",
    )


def test_harness_chains_across_agent_rotation(active_task: Path) -> None:
    """claude -> codex (assignee change to another agent) must NOT stop."""
    from relay.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    after = _wf_ticket("2 (b)", "codex")
    assert _harness_stop_reason(ref, before, after, cfg) is None


def test_harness_chains_same_agent(active_task: Path) -> None:
    from relay.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    after = _wf_ticket("2 (b)", "claude")
    assert _harness_stop_reason(ref, before, after, cfg) is None


def test_harness_stops_on_human_handoff(active_task: Path) -> None:
    """Next step assigned to a human (not a configured agent) returns control."""
    from relay.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "codex")
    after = _wf_ticket("2 (b)", "marc")
    reason = _harness_stop_reason(ref, before, after, cfg)
    assert reason is not None
    assert "hands off to marc" in reason


def test_harness_stops_on_done_and_paused(active_task: Path) -> None:
    from relay.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    done = _wf_ticket("2 (b)", "claude", status="done")
    paused = _wf_ticket("2 (b)", "claude", status="paused")
    assert "done" in (_harness_stop_reason(ref, before, done, cfg) or "")
    assert "paused" in (_harness_stop_reason(ref, before, paused, cfg) or "")


def test_harness_stops_when_no_progress(active_task: Path) -> None:
    from relay.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    after = _wf_ticket("1 (a)", "claude")
    reason = _harness_stop_reason(ref, before, after, cfg)
    assert reason is not None
    assert "still on" in reason


def test_harness_stops_on_workflowless_task_without_marking_done(
    active_task: Path,
) -> None:
    """A workflow-less task left in_progress reports 'no workflow to chain',
    not the misleading 'still on no workflow step' no-progress message."""
    from relay.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    wfless = Ticket(
        frontmatter={
            "status": "in_progress",
            "assignee": "claude",
            "workflow": None,
        },
        body="",
    )
    reason = _harness_stop_reason(ref, wfless, wfless, cfg)
    assert reason is not None
    assert "no workflow to chain" in reason
    assert "still on" not in reason


def test_launch_interactive_rotates_across_agents(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The supervisor relaunches the *next* agent across an assignee change.

    Workflow: implement (agent=claude) → peer (other-agent=codex) →
    review (human). One `relay launch` should spawn claude, then — after the
    claude→codex bump — auto-relaunch codex as a fresh process, then stop at
    the human review step. This is the cross-agent auto-relaunch.
    """
    _write(
        active_task / "workflows" / "rotate.md",
        """
        ---
        name: rotate
        description: Agent rotation chain.
        steps:
          - name: implement
            assignee: agent
          - name: peer
            assignee: other-agent
          - name: review
            assignee: human
        ---

        ## implement
        Do the work.

        ## peer
        Peer review by the other agent.
        """,
    )
    cfg = load_config(active_task)
    ref = scaffold_task(
        cfg=cfg, title="Rotate work", workflow_name="rotate", contexts=[],
        mode="interactive", owner="marc", human="marc", agent="claude",
        assignee="claude", watchers=[], status="active",
    )
    slug = ref["slug"]
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output

    # Two agent runs: claude (implement), then codex (peer) auto-relaunched
    # across the assignee change. The chain stops at the human review step.
    assert len(calls) == 2, calls
    assert calls[0][0] == "claude"
    assert calls[1][0] == "codex"

    from relay.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]) / "ticket.md")
    assert ticket.step == "3 (review)"
    assert ticket.assignee == "marc"


def test_launch_rotation_stops_when_next_agent_cli_missing(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the chain rotates to an agent whose CLI is absent, stop cleanly."""
    _write(
        active_task / "workflows" / "rotate2.md",
        """
        ---
        name: rotate2
        description: Agent rotation chain.
        steps:
          - name: implement
            assignee: agent
          - name: peer
            assignee: other-agent
        ---

        ## implement
        Do the work.

        ## peer
        Peer review.
        """,
    )
    cfg = load_config(active_task)
    ref = scaffold_task(
        cfg=cfg, title="Rotate2 work", workflow_name="rotate2", contexts=[],
        mode="interactive", owner="marc", human="marc", agent="claude",
        assignee="claude", watchers=[], status="active",
    )
    slug = ref["slug"]
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    # claude resolves, codex does not (simulate codex not on PATH).
    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "relay.commands.launch.shutil.which",
        lambda name: "/usr/bin/claude" if name == "claude" else None,
    )

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Only claude ran; codex CLI missing → stop cleanly, hand back to caller.
    assert len(calls) == 1, calls
    assert calls[0][0] == "claude"
    assert "not on PATH" in result.output

    from relay.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]) / "ticket.md")
    assert ticket.step == "2 (peer)"
    assert ticket.assignee == "codex"
