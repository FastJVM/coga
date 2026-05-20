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


# --- unit: command construction ------------------------------------------------


def _agent(auto: str) -> AgentType:
    return AgentType(name="x", cli="my-cli", auto=auto, file="X.md", mode="local")


def test_build_command_interactive_passes_prompt_positionally() -> None:
    cmd = build_agent_command(_agent("-p"), mode="interactive", prompt="full prompt text")
    assert cmd == ["my-cli", "full prompt text"]


def test_build_command_auto_prepends_flag_then_prompt() -> None:
    cmd = build_agent_command(_agent("-p"), mode="auto", prompt="full prompt text")
    assert cmd == ["my-cli", "-p", "full prompt text"]


def test_build_command_auto_subcommand_style() -> None:
    cmd = build_agent_command(_agent("exec"), mode="auto", prompt="full prompt text")
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


def test_launch_marks_interactive_session_supervised(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    # The agent's env carries the supervised marker so `relay bump`, run
    # from inside the session, can tell the human to exit and chain.
    assert envs and envs[0].get("RELAY_SUPERVISED") == "1"


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


@pytest.mark.parametrize("mode", ["interactive"])
def test_launch_harness_continues_through_consecutive_agent_steps(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    ref = _scaffold_chain_task(active_task, mode=mode)
    slug = str(ref["slug"])
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
    assert len(calls) == 2
    assert "next step has no skill" in result.output

    from relay.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]) / "ticket.md")
    assert ticket.step == "3 (review)"
    assert ticket.assignee == "marc"


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
    assert len(calls) == 1
    assert "next step assignee changed: claude → marc" in result.output

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


def test_launch_rejects_draft_with_mark_active_hint(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Launch no longer flips draft → active. It errors with a hint."""
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    _allow_interactive_tty(monkeypatch)
    from relay.ticket import Ticket
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["status"] = "draft"
    t.write(ref.path / "ticket.md")

    called = False

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        class R: returncode = 0
        return R()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2, result.output
    assert "draft" in (result.output + (result.stderr or ""))
    assert "relay mark active fix-retry-logic" in (result.output + (result.stderr or ""))
    assert not called  # agent never spawned

    # Ticket stayed draft — launch did not mutate status.
    t = Ticket.read(ref.path / "ticket.md")
    assert t.status == "draft"


def test_launch_rejects_paused(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    combined = result.output + (result.stderr or "")
    assert "'paused'" in combined
    assert "relay mark active fix-retry-logic" in combined


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
        captured["prompt"] = cmd[1]
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
    assert "Skill: bootstrap/ticket" in cmd[1]

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
