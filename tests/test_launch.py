from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
from types import SimpleNamespace
from typer.testing import CliRunner

from conftest import seed_direct_body_workflow
from coga.cli import app
from coga.create import create_task
from coga.commands.launch import (
    _preflight_push_auth,
    _skip_permissions_argv_for_launch,
    build_agent_command,
    spawn_agent_session,
)
from coga.config import AgentType, ConfigError, load_config
from coga.github_preflight import CheckResult
from coga.repl_supervisor import _TIMEOUT_EXIT_CODE, ReplOutcome
from coga.taskfile import read_blackboard, replace_blackboard, upsert_blackboard
from coga.tasks import BootstrapRef, TaskRef, list_tasks
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _read_log(repo: Path) -> str:
    """The repo-global audit log (`coga/log.md`)."""
    return (repo / "log.md").read_text()


def _capture_slack(sink: list[str], json_payload):
    sink.append(json_payload["text"])
    class R:
        status_code = 200
        text = "ok"
    return R()


def _prompt_arg(cmd: list[str]) -> str:
    for arg in cmd:
        if isinstance(arg, str) and arg.startswith("# Coga task"):
            return arg
        if isinstance(arg, str) and arg.startswith("developer_instructions=# Coga task"):
            return arg.removeprefix("developer_instructions=")
    raise AssertionError(f"No Coga prompt in argv: {cmd!r}")


# --- unit: command construction ------------------------------------------------


def _agent(
    auto: str,
    name_flag: str = "",
    session_id_flag: str = "",
    discussion: str = "",
    skip_permissions: str = "",
    skip_permissions_argv: tuple[str, ...] = (),
) -> AgentType:
    return AgentType(
        name="x",
        cli="my-cli",
        auto=auto,
        file="X.md",
        mode="local",
        name_flag=name_flag,
        session_id_flag=session_id_flag,
        discussion=discussion,
        skip_permissions=skip_permissions,
        skip_permissions_argv=skip_permissions_argv,
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


def test_build_command_injects_session_id_after_name_flag() -> None:
    cmd = build_agent_command(
        _agent("-p", name_flag="-n", session_id_flag="--session-id"),
        mode="interactive",
        prompt="full prompt text",
        name="Fix retry backoff",
        session_id="session-123",
    )
    assert cmd == [
        "my-cli",
        "-n",
        "Fix retry backoff",
        "--session-id",
        "session-123",
        "full prompt text",
    ]


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
        name="Orient an agent in this coga/ repo",
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


# --- unit: shared single-shot spawn -------------------------------------------


def _ticket() -> Ticket:
    return Ticket(
        frontmatter={
            "title": "Spawn test",
            "mode": "interactive",
            "status": "active",
            "assignee": "claude",
        },
        body="",
    )


def test_spawn_agent_session_appends_kickoff_for_claude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = TaskRef(slug="draft-ticket", path=tmp_path / "draft-ticket")
    ref.path.mkdir()
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(
        "coga.commands.launch.compose_prompt",
        lambda cfg, ref, ticket, autonomy_override=None: "# Coga task\nbody",
    )
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

    result = spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(
            name="claude",
            cli="claude",
            auto="-p",
            file="CLAUDE.md",
            mode="local",
            discussion="--append-system-prompt {prompt}",
        ),
        "interactive",
        env={},
        actor="human:marc",
        log_message="launched",
        discussion=True,
        kickoff="Begin",
    )

    assert result.exit_code == 0
    assert calls == [["claude", "--append-system-prompt", "# Coga task\nbody", "Begin"]]
    assert "launched" in (tmp_path / "log.md").read_text()


def test_spawn_agent_session_appends_kickoff_for_codex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = TaskRef(slug="draft-ticket", path=tmp_path / "draft-ticket")
    ref.path.mkdir()
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(
        "coga.commands.launch.compose_prompt",
        lambda cfg, ref, ticket, autonomy_override=None: "# Coga task\nbody",
    )
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

    spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(
            name="codex",
            cli="codex",
            auto="exec",
            file="AGENTS.md",
            mode="local",
            discussion="-c developer_instructions={prompt}",
        ),
        "interactive",
        env={},
        actor="human:marc",
        log_message="launched",
        discussion=True,
        kickoff="Begin",
    )

    assert calls == [["codex", "-c", "developer_instructions=# Coga task\nbody", "Begin"]]


def test_spawn_commits_log_append_when_commit_log_set(git_repo, monkeypatch):
    """A bootstrap launch (commit_log=True) commits its `log.md` append at once.

    Without it the append lingers uncommitted and blocks the next `git pull` at
    the checkout gate (merge=union only saves committed content). The launch
    command passes `commit_log=is_bootstrap`, so this is the bootstrap path.
    """
    cfg = load_config(git_repo.coga_os)
    ref = BootstrapRef(name="orient", path=git_repo.coga_os / "bootstrap" / "orient")
    ref.path.mkdir(parents=True)

    # Fake only the agent spawn (the PTY watcher) — leave real `subprocess.run`
    # for git so `sync_log` actually commits.
    monkeypatch.setattr(
        "coga.commands.launch.compose_prompt",
        lambda cfg, ref, ticket, autonomy_override=None: "# Coga task\nbody",
    )
    monkeypatch.setattr(
        "coga.commands.launch.run_with_done_marker",
        lambda *a, **k: ReplOutcome(exit_code=0, kind="exit"),
    )

    spawn_agent_session(
        cfg,
        ref,
        _ticket(),
        AgentType(
            name="claude", cli="claude", auto="-p", file="CLAUDE.md",
            mode="local", discussion="--append-system-prompt {prompt}",
        ),
        "interactive",
        env={},
        actor="human:marc",
        log_message="launched in interactive mode",
        discussion=True,
        kickoff="Begin",
        commit_log=True,
    )

    # The append is committed (clean tree) and pushed to the control branch.
    assert "log.md" not in git_repo.git("status", "--porcelain")
    assert git_repo.origin_tracks("coga/log.md")
    assert "Log: bootstrap/orient" in git_repo.origin_subjects()


def test_spawn_leaves_log_dirty_when_commit_log_unset(git_repo, monkeypatch):
    """Default (commit_log=False) preserves today's behavior: the append stays
    uncommitted so a later sync (`coga ticket`'s `sync_paths`) carries it."""
    cfg = load_config(git_repo.coga_os)
    ref = BootstrapRef(name="orient", path=git_repo.coga_os / "bootstrap" / "orient")
    ref.path.mkdir(parents=True)

    monkeypatch.setattr(
        "coga.commands.launch.compose_prompt",
        lambda cfg, ref, ticket, autonomy_override=None: "# Coga task\nbody",
    )
    monkeypatch.setattr(
        "coga.commands.launch.run_with_done_marker",
        lambda *a, **k: ReplOutcome(exit_code=0, kind="exit"),
    )

    spawn_agent_session(
        cfg, ref, _ticket(),
        AgentType(
            name="claude", cli="claude", auto="-p", file="CLAUDE.md",
            mode="local", discussion="--append-system-prompt {prompt}",
        ),
        "interactive", env={}, actor="human:marc",
        log_message="launched", discussion=True, kickoff="Begin",
    )

    assert "log.md" in git_repo.git("status", "--porcelain")


def test_spawn_sweeps_usage_record_at_teardown(git_repo, monkeypatch):
    """The teardown commits the `## Usage` record `capture_session` appends past
    the agent's final `bump`/`mark` sync — the structural root cause of the
    permanently-dirty tree — while product code outside `coga/` is left alone."""
    cfg = load_config(git_repo.coga_os)
    task = git_repo.coga_os / "tasks" / "demo"
    task.mkdir(parents=True)
    (task / "ticket.md").write_text("---\ntitle: demo\nstatus: active\n---\n\nbody\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed demo task")
    git_repo.git("push", "origin", "main")
    ref = TaskRef(slug="demo", path=task)

    # A tracked code file outside coga/, dirtied — must survive the sweep.
    outside = git_repo.root / "outside.txt"
    outside.write_text("original\n")
    git_repo.git("add", "outside.txt")
    git_repo.git("commit", "-m", "seed outside")
    git_repo.git("push", "origin", "main")
    outside.write_text("locally modified\n")

    monkeypatch.setattr(
        "coga.commands.launch.compose_prompt",
        lambda cfg, ref, ticket, autonomy_override=None: "# Coga task\nbody",
    )
    monkeypatch.setattr(
        "coga.commands.launch.run_with_done_marker",
        lambda *a, **k: ReplOutcome(exit_code=0, kind="exit"),
    )

    def fake_capture(*, blackboard, **kwargs):  # type: ignore[no-untyped-def]
        # Mirror the real append: a `## Usage` line written into the ticket
        # blackboard, *past* the agent's last sync.
        blackboard.write_text(blackboard.read_text() + '\n## Usage\n{"tokens": 1}\n')

    monkeypatch.setattr(
        "coga.commands.launch.usage_tracking.capture_session", fake_capture
    )

    spawn_agent_session(
        cfg, ref, _ticket(),
        AgentType(
            name="claude", cli="claude", auto="-p", file="CLAUDE.md",
            mode="local", discussion="--append-system-prompt {prompt}",
        ),
        "interactive", env={}, actor="human:marc",
        log_message="launched", discussion=True, kickoff="Begin",
        capture_usage=True,
    )

    # The usage record is committed (clean coga/ tree) and pushed to the control
    # branch — no dangling line left behind.
    assert "coga/" not in git_repo.git("status", "--porcelain")
    assert "## Usage" in git_repo.git(
        "show", "origin/main:coga/tasks/demo/ticket.md"
    )
    # Product code outside coga/ stays dirty and unpushed.
    assert "outside.txt" in git_repo.git("status", "--porcelain")


def test_spawn_agent_session_without_kickoff_stays_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = BootstrapRef(name="orient", path=tmp_path / "bootstrap" / "orient")
    ref.path.mkdir(parents=True)
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(
        "coga.commands.launch.compose_prompt",
        lambda cfg, ref, ticket, autonomy_override=None: "# Coga task\nbody",
    )
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)

    spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(
            name="claude",
            cli="claude",
            auto="-p",
            file="CLAUDE.md",
            mode="local",
            discussion="--append-system-prompt {prompt}",
        ),
        "interactive",
        env={},
        actor="human:marc",
        log_message="launched",
        discussion=True,
    )

    assert calls == [["claude", "--append-system-prompt", "# Coga task\nbody"]]


# --- unit: permission-skip argv -------------------------------------------------


def _task_ref(slug: str = "fix-retry-logic") -> TaskRef:
    return TaskRef(slug=slug, path=Path("/tmp") / slug)


def test_build_command_skip_argv_after_name_flag_before_auto_flag() -> None:
    cmd = build_agent_command(
        _agent("-p", name_flag="-n"),
        mode="auto",
        prompt="full prompt text",
        name="Fix retry backoff",
        skip_permissions_argv=("--dangerously-skip-permissions",),
    )
    assert cmd == [
        "my-cli",
        "-n",
        "Fix retry backoff",
        "--dangerously-skip-permissions",
        "-p",
        "full prompt text",
    ]


def test_build_command_skip_argv_before_auto_subcommand() -> None:
    cmd = build_agent_command(
        _agent("exec"),
        mode="auto",
        prompt="full prompt text",
        skip_permissions_argv=("--dangerously-bypass-approvals-and-sandbox",),
    )
    assert cmd == [
        "my-cli",
        "--dangerously-bypass-approvals-and-sandbox",
        "exec",
        "full prompt text",
    ]


def test_build_command_defaults_to_no_skip_argv() -> None:
    cmd = build_agent_command(_agent("-p"), mode="auto", prompt="full prompt text")
    assert cmd == ["my-cli", "-p", "full prompt text"]


def test_skip_policy_applies_to_auto_task_launch() -> None:
    agent = _agent(
        "-p",
        skip_permissions="auto",
        skip_permissions_argv=("--dangerously-skip-permissions",),
    )
    argv = _skip_permissions_argv_for_launch(agent, "auto", _task_ref())
    assert argv == ("--dangerously-skip-permissions",)


def test_skip_policy_noop_in_interactive_mode() -> None:
    agent = _agent(
        "-p",
        skip_permissions="auto",
        skip_permissions_argv=("--dangerously-skip-permissions",),
    )
    assert _skip_permissions_argv_for_launch(agent, "interactive", _task_ref()) == ()


def test_skip_policy_noop_without_agent_policy() -> None:
    """An auto task whose effective agent has no local skip policy keeps
    today's behavior — even with argv configured but the policy unset."""
    assert _skip_permissions_argv_for_launch(_agent("-p"), "auto", _task_ref()) == ()
    inert = _agent("-p", skip_permissions_argv=("--dangerously-skip-permissions",))
    assert _skip_permissions_argv_for_launch(inert, "auto", _task_ref()) == ()


def test_skip_policy_noop_for_bootstrap_ticket() -> None:
    """`coga chat` / `coga ticket` launch targets never skip permissions, regardless
    of the selected agent's local policy."""
    agent = _agent(
        "-p",
        skip_permissions="auto",
        skip_permissions_argv=("--dangerously-skip-permissions",),
    )
    ref = BootstrapRef(name="orient", path=Path("/tmp/bootstrap/orient"))
    assert _skip_permissions_argv_for_launch(agent, "auto", ref) == ()


def test_skip_policy_per_step_agent_rotation() -> None:
    """Supervised chains re-resolve the policy per step from that step's
    agent — a rotation from a skip-configured claude to an unconfigured
    codex (or back) flips the argv accordingly."""
    claude = _agent(
        "-p",
        skip_permissions="auto",
        skip_permissions_argv=("--dangerously-skip-permissions",),
    )
    codex = _agent("exec")
    ref = _task_ref()
    assert _skip_permissions_argv_for_launch(claude, "auto", ref) != ()
    assert _skip_permissions_argv_for_launch(codex, "auto", ref) == ()


def test_skip_policy_fails_loud_without_argv() -> None:
    agent = _agent("-p", skip_permissions="auto")
    with pytest.raises(ConfigError, match="skip_permissions_argv"):
        _skip_permissions_argv_for_launch(agent, "auto", _task_ref())


# --- integration: end-to-end via CliRunner with mocked subprocess --------------


@pytest.fixture
def active_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
        [agents.codex]
        cli = "codex"
        auto = "exec"
        file = "AGENTS.md"
        [launch]
        worktree = false
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')

    seed_direct_body_workflow(company)
    monkeypatch.chdir(company)
    cfg = load_config(company)
    create_task(
        cfg=cfg, title="Fix retry logic",
        workflow_name="direct/body", contexts=[], autonomy="interactive",
        owner="marc", assignee="claude", watchers=[], status="active",
    )
    return company


def _allow_slack(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://slack.example.test")
    slack_msgs: list[str] = []
    monkeypatch.setattr(
        "coga.notification.slack.requests.post",
        lambda url, json=None, timeout=None: _capture_slack(slack_msgs, json),
    )
    return slack_msgs


def _allow_interactive_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "coga.commands.launch._interactive_stdio_has_tty",
        lambda: True,
    )


def _deny_interactive_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "coga.commands.launch._interactive_stdio_has_tty",
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


def _create_chain_task(active_task: Path, *, mode: str = "interactive") -> dict[str, object]:
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
    return create_task(
        cfg=cfg,
        title="Chain work",
        workflow_name="chain",
        contexts=[],
        autonomy=mode,
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

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    # Agent called with `claude <composed-prompt-text>` — composed prompt
    # arrives as the first user message in the REPL.
    assert len(calls) == 1
    assert calls[0][0] == "claude"
    assert len(calls[0]) == 2
    assert "Coga task" in calls[0][1]

    # Log entry written
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "in_progress"
    log = _read_log(active_task)
    assert "started (active → in_progress) via coga launch" in log
    assert "launched in interactive mode" in log


# --- push-auth gate -----------------------------------------------------------
#
# Coga drives the whole session through git/gh, so launch refuses to spawn an
# agent when push access to the configured remote is broken — fail loud at the
# door, not after a long run that can't ship.


def _ok_remote(_remote):
    return CheckResult("git-remote", True, "remote 'origin' -> url", "url")


def test_preflight_skips_for_bootstrap_and_when_git_disabled(active_task):
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    boot = BootstrapRef(name="orient", path=ref.path)

    # Bootstrap tickets never push — skip regardless of auth.
    _preflight_push_auth(cfg, boot, is_bootstrap=True)

    # git disabled → no sync, nothing to gate.
    disabled = load_config(active_task)
    object.__setattr__(disabled, "git_enabled", False)
    _preflight_push_auth(disabled, ref, is_bootstrap=False)


def test_preflight_skips_when_remote_unresolved(active_task, monkeypatch):
    """Not a git repo / no remote → soft no-op; the auth probe never runs."""
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]

    monkeypatch.setattr(
        "coga.commands.launch.check_git_remote",
        lambda remote: CheckResult("git-remote", False, "not a git repo"),
    )

    def _boom(_remote):
        raise AssertionError("check_git_auth must not run when remote unresolved")

    monkeypatch.setattr("coga.commands.launch.check_git_auth", _boom)
    _preflight_push_auth(cfg, ref, is_bootstrap=False)  # must not raise


def test_preflight_passes_when_push_authenticated(active_task, monkeypatch):
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    monkeypatch.setattr("coga.commands.launch.check_git_remote", _ok_remote)
    monkeypatch.setattr(
        "coga.commands.launch.check_git_auth",
        lambda remote: CheckResult("git-auth", True, "push access authenticated"),
    )
    _preflight_push_auth(cfg, ref, is_bootstrap=False)  # must not raise


def test_preflight_bails_when_push_auth_broken(active_task, monkeypatch):
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    monkeypatch.setattr("coga.commands.launch.check_git_remote", _ok_remote)
    monkeypatch.setattr(
        "coga.commands.launch.check_git_auth",
        lambda remote: CheckResult("git-auth", False, "could not authenticate push access"),
    )
    with pytest.raises(SystemExit):
        _preflight_push_auth(cfg, ref, is_bootstrap=False)


def test_launch_refuses_and_stays_active_when_push_auth_broken(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: a broken remote refuses the launch before flipping status
    or spawning — the ticket stays `active`, no agent process is started."""
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr("coga.commands.launch.check_git_remote", _ok_remote)
    monkeypatch.setattr(
        "coga.commands.launch.check_git_auth",
        lambda remote: CheckResult("git-auth", False, "could not authenticate push access"),
    )

    spawned: list[list[str]] = []

    def fake_run(cmd, *a, **k):  # pragma: no cover - must never run
        spawned.append(cmd)

        class _R:
            returncode = 0

        return _R()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code != 0
    assert "git push access" in result.output
    assert spawned == []  # no agent spawned

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    assert Ticket.read(ref.ticket_path).status == "active"


def test_launch_captures_usage_with_session_id(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = (active_task / "coga.toml").read_text()
    (active_task / "coga.toml").write_text(
        text.replace(
            'file = "CLAUDE.md"',
            'file = "CLAUDE.md"\nsession_id_flag = "--session-id"',
            1,
        )
    )
    calls: list[list[str]] = []
    captures: list[dict] = []
    _allow_interactive_tty(monkeypatch)

    def fake_supervisor(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return ReplOutcome(0, "natural")

    def fake_capture(**kwargs):  # type: ignore[no-untyped-def]
        captures.append(kwargs)

    monkeypatch.setattr(
        "coga.commands.launch.run_with_done_marker", fake_supervisor
    )
    monkeypatch.setattr(
        "coga.commands.launch.usage_tracking.capture_session", fake_capture
    )
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "--session-id" in calls[0]
    session_id = calls[0][calls[0].index("--session-id") + 1]
    assert len(captures) == 1
    assert captures[0]["session_id"] == session_id
    assert captures[0]["slug"] == "fix-retry-logic"
    assert captures[0]["step"] == "execute"
    assert captures[0]["agent"] == "claude"
    assert captures[0]["cli"] == "claude"


def test_launch_fails_loud_on_unset_declared_secret(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    # Inline per-ticket secret pointing at an env var that is not exported.
    t.frontmatter["secrets"] = [{"stripe_key": "env:STRIPE_SECRET_KEY"}]
    t.write(ref.ticket_path)

    calls: list[list[str]] = []
    monkeypatch.setattr(
        "coga.commands.launch.subprocess.run",
        lambda cmd, env=None, check=False, cwd=None: calls.append(cmd),
    )
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "stripe_key" in combined and "STRIPE_SECRET_KEY" in combined
    # Fail-loud: no agent process was ever spawned.
    assert calls == []
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "active"
    log = _read_log(active_task)
    assert "started (active" not in log


def test_launch_injects_only_declared_secret(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live")
    monkeypatch.setenv("OTHER_SECRET", "nope")
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    # Only `stripe_key` is declared inline; `OTHER_SECRET` is set in the env but
    # the ticket never references it, so it must not leak to the child.
    t.frontmatter["secrets"] = [{"stripe_key": "env:STRIPE_SECRET_KEY"}]
    t.write(ref.ticket_path)

    captured: dict[str, str] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured.update(env or {})
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    # Only the declared secret was injected, under its scoped NAME.
    assert captured.get("stripe_key") == "sk_live"
    assert "other" not in captured
    # The raw source env var the `env:` ref points at is scrubbed from the
    # child; an undeclared env var that was never referenced is left untouched.
    assert "STRIPE_SECRET_KEY" not in captured
    assert captured.get("OTHER_SECRET") == "nope"


def test_launch_fails_loud_on_op_read_error(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A declared `op://` secret that can't be resolved fails loud before any
    # agent is spawned, naming the key and reference (never a value).
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["secrets"] = [{"stripe_key": "op://vault/stripe/key"}]
    t.write(ref.ticket_path)

    # `coga.config` and `coga.commands.launch` import the same `subprocess`
    # module, so patching `coga.config.subprocess.run` covers both the `op read`
    # resolution and the agent spawn. The op read is mocked non-zero → SecretError
    # before any spawn, so `calls` stays empty.
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["op", "read"]:
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="[ERROR] not signed in"
            )
        calls.append(cmd)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "stripe_key" in combined and "op://vault/stripe/key" in combined
    # Fail-loud: no agent process was ever spawned, ticket stays active.
    assert calls == []
    assert Ticket.read(ref.ticket_path).status == "active"


def test_launch_injects_op_secret(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["secrets"] = [{"stripe_key": "op://vault/stripe/key"}]
    t.write(ref.ticket_path)

    # One dispatching mock for both modules' shared `subprocess`: `op read`
    # returns the secret; the agent spawn records its injected env.
    captured: dict[str, str] = {}

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["op", "read"]:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="sk_op_secret\n", stderr=""
            )
        captured.update(kwargs.get("env") or {})
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert captured.get("stripe_key") == "sk_op_secret"


def test_direct_launch_timeout_exits_non_zero(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A public `coga launch --idle-timeout` timeout must fail loud.

    Recurring gets an internal return-value path so it can record the watchdog
    timeout and continue its sweep, but the visible CLI should still propagate
    the supervisor's non-zero timeout code to scripts and shells.
    """
    _allow_interactive_tty(monkeypatch)

    def fake_supervisor(*args, **kwargs):  # type: ignore[no-untyped-def]
        return ReplOutcome(_TIMEOUT_EXIT_CODE, "timeout")

    monkeypatch.setattr(
        "coga.commands.launch.run_with_done_marker", fake_supervisor
    )
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(
        app, ["launch", "fix-retry-logic", "--idle-timeout", "1"]
    )

    assert result.exit_code == _TIMEOUT_EXIT_CODE, result.output
    assert "Agent timed out" in result.output


def test_launch_interactive_ignores_local_skip_policy(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `mode: interactive` launch never applies the agent's local
    permission-skip policy — the argv must not reach the spawned CLI."""
    _write(
        active_task / "coga.local.toml",
        """
        user = "marc"

        [agents.claude]
        skip_permissions = "auto"
        skip_permissions_argv = "--dangerously-skip-permissions"
        """,
    )
    calls: list[list[str]] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "--dangerously-skip-permissions" not in calls[0]


def test_launch_bails_on_missing_context(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ticket referencing a context with no file must refuse to launch,
    rather than starting an agent with a silently-missing prompt layer."""
    _allow_interactive_tty(monkeypatch)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket_md = ref.ticket_path
    ticket_md.write_text(
        ticket_md.read_text().replace("contexts: []", "contexts:\n- email/ghost")
    )

    def fail_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError(f"agent must not be launched, got {cmd!r}")

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fail_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

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
    _allow_interactive_tty(monkeypatch)
    # File-form task: the whole ticket lives in `tasks/<slug>.md`.
    ticket_md = active_task / "tasks" / "fix-retry-logic.md"
    assert ticket_md.exists()

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        # Simulate the agent deleting its own task before exit.
        ticket_md.unlink()
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert not ticket_md.exists()


def test_launch_marks_interactive_session_supervised(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interactive launches chain across agent-owned steps, so the child
    inherits `COGA_SUPERVISED=1`. `coga bump` keys its supervised-launch
    hint off that env var."""
    envs: list[dict] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        envs.append(env or {})
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    assert envs
    assert envs[0].get("COGA_SUPERVISED") == "1"


def test_launch_in_progress_resumes_without_status_transition(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    calls: list[list[str]] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    log = _read_log(active_task)
    assert "started (active → in_progress) via coga launch" not in log


def test_launch_interactive_without_tty_fails_before_lock(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False
    _deny_interactive_tty(monkeypatch)

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        raise AssertionError("interactive launch should fail before spawning agent")

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code == 2
    assert "Cannot launch 'fix-retry-logic': autonomy=interactive requires a TTY" in (
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

    After `coga bump` advances from step 1 (agent) to step 2 (also agent),
    the launch loop re-composes the prompt and spawns a fresh REPL. The
    chain stops at the first human-assigned step (step 3 here).
    """
    ref = _create_chain_task(active_task, mode="interactive")
    slug = str(ref["slug"])
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        # Each spawned "agent" bumps once. After the 1→2 bump the agent is
        # still the assignee → launch should respawn. After the 2→3 bump
        # the next step is human-assigned → launch should stop.
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Two REPLs: step 1, then a fresh one for step 2. Step 3 is the human's,
    # so the loop stops without spawning a third.
    assert len(calls) == 2

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.step == "3 (review)"


def test_launch_chains_when_ticket_has_ticket_level_skills(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ticket-level `skills:` list must not stop the supervised chain.

    Regression: the loop used to break on `is_bootstrap or ticket.skills`,
    a rename artifact of the old singular skill-shim field. That silently
    stopped any normal workflow ticket carrying ticket-level skills from
    chaining to its next agent step. Only bootstrap tickets should stop here.
    """
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
    ref = create_task(
        cfg=cfg,
        title="Chain work",
        workflow_name="chain",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        human="marc",
        agent="claude",
        assignee="claude",
        watchers=[],
        status="active",
        skills=["code/implement"],  # ticket-level skills — must not block chaining
    )
    slug = str(ref["slug"])

    from coga.ticket import Ticket
    assert Ticket.read(Path(ref["path"])).skills == ["code/implement"]

    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Step 1 (agent) chains to step 2 (agent); stops at step 3 (human).
    assert len(calls) == 2
    assert Ticket.read(Path(ref["path"])).step == "3 (review)"


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
    ref = create_task(
        cfg=cfg,
        title="Handoff work",
        workflow_name="handoff",
        contexts=[],
        autonomy="interactive",
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

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Interactive does not chain — one agent run, then back to the caller.
    # The assignee transition surfaces in `coga status`, not in launch
    # output, because the human is the one driving step transitions.
    assert len(calls) == 1

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.step == "2 (human-check)"
    assert ticket.assignee == "marc"


def test_launch_harness_stops_on_agent_block(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(
            app,
            ["block", "--task", slug, "--reason", "test block"],
        )
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "task status is 'blocked'" in result.output
    assert "test block" in read_blackboard(Path(ref["path"]))


def _launch_single_spawn(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Mock the agent spawn so launch runs one REPL and stops (no bump → no
    progress → supervisor halts). Returns the list of spawned argvs."""
    calls: list[list[str]] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    return calls


@pytest.mark.parametrize("prior", ["draft", "paused"])
def test_launch_auto_activates_draft_and_paused(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, prior: str
) -> None:
    """`coga launch` is itself the readiness signal: a draft/paused ticket
    with a workflow is activated inline, then flipped to in_progress."""
    from coga.ticket import Ticket

    ref = _create_chain_task(active_task, mode="interactive")
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"])
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
    log = _read_log(active_task)
    assert f"activated ({prior} → active) — auto on launch" in log


def test_launch_refuses_unsynthesized_draft_blackboard(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = _create_chain_task(active_task, mode="interactive")
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"])
    t = Ticket.read(ticket_md)
    t.frontmatter["status"] = "draft"
    t.write(ticket_md)
    before_blackboard = "\n## Ticket authoring notes\n\nNeeds body synthesis.\n"
    replace_blackboard(ticket_md, before_blackboard)
    before = ticket_md.read_text()

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug])

    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "pre-launch notes" in combined
    assert (
        "Merge the important parts into `## Description` / `## Context`"
        in combined
    )
    assert calls == []
    assert ticket_md.read_text() == before
    assert "activated (draft" not in _read_log(active_task)


def test_launch_refuses_done_ticket(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Launching a `done` ticket must not restart its frozen workflow:
    re-activating would re-seed `step: 1` without re-resolving `assignee` and
    wedge the ticket. Launch refuses loud and leaves the ticket untouched."""
    from coga.ticket import Ticket

    ref = _create_chain_task(active_task, mode="interactive")
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"])
    t = Ticket.read(ticket_md)
    t.frontmatter["status"] = "done"
    t.frontmatter.pop("step", None)  # mark done clears the step
    t.write(ticket_md)
    before = ticket_md.read_text()

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 2, result.output
    combined = result.output + (result.stderr or "")
    assert "is done" in combined
    assert "Reopen it deliberately" in combined
    assert calls == []  # no agent spawned

    after = Ticket.read(ticket_md)
    assert after.status == "done"
    assert after.step is None
    assert ticket_md.read_text() == before  # ticket file untouched


def test_launch_auto_activate_bails_without_workflow(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workflow-less ticket still can't be activated — launch fails loud
    (it can never be advanced by `coga bump`) and never spawns an agent."""
    from coga.ticket import Ticket

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    # Strip the workflow and drop to draft so launch's auto-activate hits the
    # workflow-less path (a workflow-less non-draft can't be created now).
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["status"] = "draft"
    t.frontmatter["workflow"] = None
    t.write(ref.ticket_path)

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2, result.output
    combined = result.output + (result.stderr or "")
    assert "no workflow" in combined
    assert not calls  # agent never spawned

    # Ticket stayed draft — the failed activation did not mutate status.
    assert Ticket.read(ref.ticket_path).status == "draft"


def test_launch_agent_not_in_path(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: None)
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
    upsert_blackboard(ref.ticket_path, "\n\n" + "x" * (33 * 1024) + "\n")
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        "coga.commands.launch.subprocess.run",
        lambda cmd, env=None, check=False, cwd=None: _Result(),
    )
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert "blackboard region is" in (result.output + (result.stderr or ""))


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
    ref = create_task(
        cfg=cfg,
        title="Measure prompt scope",
        workflow_name="code/measure",
        contexts=["email/payment-flow"],
        autonomy="interactive",
        owner="marc",
        human="marc",
        agent="claude",
        assignee="claude",
        watchers=[],
        status="draft",
    )

    def fail_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError("prompt report must not spawn an agent")

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fail_run)
    monkeypatch.setattr("coga.commands.launch._interactive_stdio_has_tty", lambda: False)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: None)

    result = CliRunner().invoke(app, ["launch", str(ref["slug"]), "--prompt-report"])
    assert result.exit_code == 0, result.output
    assert "Prompt report for measure-prompt-scope" in result.output
    assert "ticket_context" in result.output
    assert "email/payment-flow" in result.output
    assert "workflow_skill" in result.output
    assert "code/implement" in result.output
    assert "Total composed prompt" in result.output

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.status == "draft"
    assert "launched in interactive mode" not in _read_log(active_task)


# --- bootstrap tickets ---------------------------------------------------------


@pytest.fixture
def bootstrap_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A coga/ with a bootstrap/ticket launch target and a stub skill, no tasks."""
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
        [agents.codex]
        cli = "codex"
        auto = "exec"
        file = "AGENTS.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        autonomy: interactive
        skills:
          - bootstrap/ticket
        assignee: claude
        ---

        ## Description

        Persistent launch target for the bootstrap/ticket skill.
        """,
    )
    _write(
        company / "skills" / "bootstrap" / "ticket" / "SKILL.md",
        """
        ---
        name: bootstrap/ticket
        description: Author a Coga task.
        ---

        Interview, create, fill in the ticket. Stop.
        """,
    )
    monkeypatch.chdir(company)
    return company


def test_launch_bare_bootstrap_does_not_post_to_slack(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare bootstrap-ticket launches (e.g. `coga chat`) are stateless re-entry points,
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

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
    monkeypatch.setattr(
        "coga.commands.launch.subprocess.run",
        lambda cmd, env=None, check=False, cwd=None: _Result(),
    )
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

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

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["prompt"] = _prompt_arg(cmd)
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output

    # No lock file left behind; in fact none was ever written.

    # Skill body composed into the prompt.
    prompt = captured["prompt"]
    assert isinstance(prompt, str)
    assert "Skill: bootstrap/ticket" in prompt
    assert "Interview, create, fill in the ticket." in prompt
    # Header still uses the bootstrap/<name> id_slug.
    assert "bootstrap/ticket" in prompt

    # The repo-global log recorded the launch.
    log = _read_log(bootstrap_repo)
    assert "launched in interactive mode" in log


def test_launch_discussion_bootstrap_uses_discussion_template(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discussion tickets ride the composed prompt as system context instead of
    making it the first user message."""
    # Rewrite the fixture's coga.toml to add a discussion template on claude.
    _write(
        bootstrap_repo / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
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

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    # Argv: [cli, --append-system-prompt, <prompt>]
    assert cmd[0] == "claude"
    assert cmd[1] == "--append-system-prompt"
    assert "Skill: bootstrap/ticket" in cmd[2]
    assert cmd[3] == "Begin"


def test_launch_orient_bootstrap_stays_silent(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        bootstrap_repo / "bootstrap" / "orient" / "ticket.md",
        """
        ---
        title: Chat
        mode: interactive
        assignee: claude
        ---

        ## Description

        Persistent launch target for a discussion session.
        """,
    )
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/orient"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[-1] != "Begin"


def test_launch_regular_task_does_not_use_discussion_template(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        active_task / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        discussion = "--append-system-prompt {prompt}"
        [launch]
        worktree = false
        """,
    )
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

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

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket", "--agent", "codex"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "codex"
    assert cmd[1] == "-c"
    assert "Skill: bootstrap/ticket" in _prompt_arg(cmd)
    assert cmd[-1] == "Begin"

    log = _read_log(bootstrap_repo)
    assert "assignee=codex, agent=codex" in log


def test_launch_agent_override_normal_task_uses_requested_agent_without_reassigning(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic", "--agent", "codex"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "codex"

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    from coga.ticket import Ticket
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.frontmatter["assignee"] == "claude"

    log = _read_log(active_task)
    assert "assignee=claude, launch_assignee=codex, agent=codex" in log


def test_launch_bootstrap_unknown_ticket(
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
    from coga.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    after = _wf_ticket("2 (b)", "codex")
    assert _harness_stop_reason(ref, before, after, cfg) is None


def test_harness_chains_same_agent(active_task: Path) -> None:
    from coga.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    after = _wf_ticket("2 (b)", "claude")
    assert _harness_stop_reason(ref, before, after, cfg) is None


def test_harness_stops_on_human_handoff(active_task: Path) -> None:
    """Next step assigned to a human (not a configured agent) returns control."""
    from coga.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "codex")
    after = _wf_ticket("2 (b)", "marc")
    reason = _harness_stop_reason(ref, before, after, cfg)
    assert reason is not None
    assert "hands off to marc" in reason


def test_harness_stops_on_done_and_paused(active_task: Path) -> None:
    from coga.commands.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    done = _wf_ticket("2 (b)", "claude", status="done")
    paused = _wf_ticket("2 (b)", "claude", status="paused")
    assert "done" in (_harness_stop_reason(ref, before, done, cfg) or "")
    assert "paused" in (_harness_stop_reason(ref, before, paused, cfg) or "")


def test_harness_stops_when_no_progress(active_task: Path) -> None:
    from coga.commands.launch import _harness_stop_reason

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
    from coga.commands.launch import _harness_stop_reason

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
    review (human). One `coga launch` should spawn claude, then — after the
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
    ref = create_task(
        cfg=cfg, title="Rotate work", workflow_name="rotate", contexts=[],
        autonomy="interactive", owner="marc", human="marc", agent="claude",
        assignee="claude", watchers=[], status="active",
    )
    slug = ref["slug"]
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output

    # Two agent runs: claude (implement), then codex (peer) auto-relaunched
    # across the assignee change. The chain stops at the human review step.
    assert len(calls) == 2, calls
    assert calls[0][0] == "claude"
    assert calls[1][0] == "codex"

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
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
    ref = create_task(
        cfg=cfg, title="Rotate2 work", workflow_name="rotate2", contexts=[],
        autonomy="interactive", owner="marc", human="marc", agent="claude",
        assignee="claude", watchers=[], status="active",
    )
    slug = ref["slug"]
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    # claude resolves, codex does not (simulate codex not on PATH).
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which",
        lambda name: "/usr/bin/claude" if name == "claude" else None,
    )

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Only claude ran; codex CLI missing → stop cleanly, hand back to caller.
    assert len(calls) == 1, calls
    assert calls[0][0] == "claude"
    assert "not on PATH" in result.output

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.step == "2 (peer)"
    assert ticket.assignee == "codex"
