from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from report_helpers import RUN_STATE_PATH_WARNING
from conftest import windows_skip, derived_operator, hold_by_agent, hold_by_owner, seed_direct_body_workflow
from coga import compose as compose_module
from coga.blackboard import append_blocker
from coga.cli import app
from coga import launch as launch_module
from coga.config import Config, load_config
from coga.create import create_task
from coga.launch_script import (
    ScriptChainResult,
    run_script_chain,
    run_script_phase,
    script_entry_point,
)
from coga.repl_supervisor import ReplOutcome
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import TaskRef, resolve_bootstrap, resolve_task
from coga.ticket import Ticket


_SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


@pytest.fixture
def script_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "repo" / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"

        [agents.codex]
        cli = "codex"
        file = "AGENTS.md"

        [notification]
        channels = []

        [git]
        enabled = false

        [aliases]
        deterministic = "launch bootstrap/deterministic"
        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    seed_direct_body_workflow(coga_os)
    monkeypatch.chdir(coga_os)
    return coga_os


def _create_script_task(
    coga_os: Path,
    script: str,
    *,
    secrets: list[dict[str, str]] | None = None,
) -> TaskRef:
    cfg = load_config(coga_os)
    created = create_task(
        cfg=cfg,
        title="Deterministic check",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        secrets=secrets,
        force_directory=True,
    )
    ref = resolve_task(cfg, created["slug"])
    assert ref.task_dir is not None
    _write(ref.task_dir / "ticket.py", script)
    return ref


def _create_two_step_script_task(
    coga_os: Path,
    script: str,
    *,
    first_assignee: str = "agent",
    second_assignee: str = "agent",
    title: str = "Deterministic two-step check",
) -> TaskRef:
    _write(
        coga_os / "workflows" / "deterministic" / "two-step.md",
        f"""
        ---
        name: deterministic/two-step
        description: Two deterministic launch phases.
        steps:
          - name: prepare
            assignee: {first_assignee}
          - name: finish
            assignee: {second_assignee}
        ---

        ## prepare

        Prepare the result.

        ## finish

        Finish the result.
        """,
    )
    cfg = load_config(coga_os)
    created = create_task(
        cfg=cfg,
        title=title,
        workflow_name="deterministic/two-step",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        force_directory=True,
    )
    ref = resolve_task(cfg, created["slug"])
    assert ref.task_dir is not None
    _write(ref.task_dir / "ticket.py", script)
    return ref


def _fail(message: str):
    def fail(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(message)

    return fail


def test_classifier_reserves_only_ticket_py_in_a_task_directory(
    script_repo: Path,
) -> None:
    cfg = load_config(script_repo)
    created = create_task(
        cfg=cfg,
        title="File form",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
    )
    file_ref = resolve_task(cfg, created["slug"])
    assert script_entry_point(file_ref) is None

    directory_ref = _create_script_task(script_repo, "print('ok')\n")
    assert directory_ref.task_dir is not None
    entry = directory_ref.task_dir / "ticket.py"
    entry.chmod(0o644)
    assert script_entry_point(directory_ref) == entry

    entry.rename(directory_ref.task_dir / "run.py")
    assert script_entry_point(directory_ref) is None


def test_script_only_launch_is_headless_and_receives_task_contract(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    observed_path = script_repo.parent / "observed.json"
    sentinel = script_repo.parent / "outer-done"
    monkeypatch.setenv("COGA_DONE_SENTINEL", str(sentinel))
    monkeypatch.setenv("COGA_SCRIPT_TASK", "/outer/script")
    monkeypatch.setenv("SCRIPT_TOKEN_SOURCE", "resolved-secret")
    monkeypatch.setenv("COGA_SUPERVISED", "outer")
    monkeypatch.setenv("COGA_EXPECTED_TASK", "/outer/task")
    monkeypatch.setenv("COGA_EXPECTED_STEP", "9 (outer)")
    ref = _create_script_task(
        script_repo,
        f"""
        import json
        import os
        import subprocess
        import sys
        from pathlib import Path

        keys = [
            "COGA_TASK_SLUG",
            "COGA_TASK_DIR",
            "COGA_TASK_TICKET",
            "COGA_TASK_BLACKBOARD",
            "COGA_TASK_STEP",
            "COGA_SCRIPT_TASK",
            "COGA_COGA_OS_ROOT",
            "COGA_REPO_ROOT",
            "SCRIPT_TOKEN",
        ]
        Path({str(observed_path)!r}).write_text(json.dumps({{
            "argv": sys.argv[1:],
            "cwd": os.getcwd(),
            "env": {{key: os.environ.get(key) for key in keys}},
            "supervised": {{
                key: os.environ.get(key)
                for key in (
                    "COGA_SUPERVISED",
                    "COGA_EXPECTED_TASK",
                    "COGA_EXPECTED_STEP",
                    "COGA_DONE_SENTINEL",
                )
            }},
        }}))
        raise SystemExit(subprocess.run([
            sys.executable,
            "-m",
            "coga.cli",
            "bump",
            os.environ["COGA_TASK_SLUG"],
        ]).returncode)
        """,
        secrets=[{"SCRIPT_TOKEN": "env:SCRIPT_TOKEN_SOURCE"}],
    )

    monkeypatch.setenv("PATH", "/agents-absent")
    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: False,
    )
    monkeypatch.setattr(launch_module, "compose_prompt", _fail("prompt composed"))
    monkeypatch.setattr(
        launch_module,
        "spawn_agent_session",
        _fail("agent spawned"),
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        _fail("agent skills refreshed"),
    )
    monkeypatch.setattr(launch_module.shutil, "which", _fail("agent CLI resolved"))
    monkeypatch.setattr(Config, "agent_type", _fail("agent type resolved"))

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert Ticket.read(ref.ticket_path).status == "done"
    observed = json.loads(observed_path.read_text(encoding="utf-8"))
    assert observed["argv"] == []
    assert observed["cwd"] == str(script_repo.parent.resolve())
    assert observed["env"] == {
        "COGA_TASK_SLUG": ref.id_slug,
        "COGA_TASK_DIR": str(ref.path.resolve()),
        "COGA_TASK_TICKET": str(ref.ticket_path.resolve()),
        "COGA_TASK_BLACKBOARD": str(ref.ticket_path.resolve()),
        "COGA_TASK_STEP": "1 (execute)",
        "COGA_SCRIPT_TASK": str(ref.path.resolve()),
        "COGA_COGA_OS_ROOT": str(script_repo.resolve()),
        "COGA_REPO_ROOT": str(script_repo.parent.resolve()),
        "SCRIPT_TOKEN": "resolved-secret",
    }
    assert observed["supervised"] == {
        "COGA_SUPERVISED": None,
        "COGA_EXPECTED_TASK": None,
        "COGA_EXPECTED_STEP": None,
        "COGA_DONE_SENTINEL": "",
    }
    task_log = (script_repo / "log.md").read_text(encoding="utf-8")
    assert task_log.count("task done") == 1
    assert "[system] task done" in task_log
    assert f"system finished *{ref.id_slug}*" in capfd.readouterr().err
    assert not sentinel.exists()


def test_ticket_py_phase_resolves_op_secret_without_1password_auth(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_path = script_repo.parent / "observed.json"
    op_auth = [
        "OP_SERVICE_ACCOUNT_TOKEN",
        "OP_CONNECT_TOKEN",
        "OP_CONNECT_HOST",
        "OP_SESSION_my",
    ]
    for key in op_auth:
        monkeypatch.setenv(key, "parent-auth")
    ref = _create_script_task(
        script_repo,
        f"""
        import json
        import os
        import subprocess
        import sys
        from pathlib import Path

        Path({str(observed_path)!r}).write_text(json.dumps({{
            "token": os.environ.get("SCRIPT_TOKEN"),
            "op_auth": sorted(
                key for key in os.environ
                if key in {op_auth!r} or key.startswith("OP_SESSION_")
            ),
        }}))
        raise SystemExit(subprocess.run([
            sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"],
        ]).returncode)
        """,
        secrets=[{"SCRIPT_TOKEN": "op://vault/script/token"}],
    )
    real_run = subprocess.run
    op_reads: list[str | None] = []

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        if list(cmd[:2]) == ["op", "read"]:
            op_reads.append(os.environ.get("OP_SERVICE_ACCOUNT_TOKEN"))
            return subprocess.CompletedProcess(cmd, 0, stdout="op-value\n", stderr="")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert op_reads and set(op_reads) == {"parent-auth"}
    observed = json.loads(observed_path.read_text(encoding="utf-8"))
    assert observed == {"token": "op-value", "op_auth": []}


def test_script_chain_attributes_each_child_bump_to_system(
    script_repo: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    ref = _create_two_step_script_task(
        script_repo,
        """
        import os
        import subprocess
        import sys

        raise SystemExit(subprocess.run([
            sys.executable, "-m", "coga.cli", "bump",
            os.environ["COGA_TASK_SLUG"], "--message", "deterministic result",
        ]).returncode)
        """,
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert Ticket.read(ref.ticket_path).status == "done"
    task_log = (script_repo / "log.md").read_text(encoding="utf-8")
    assert task_log.count("[system] advanced to step 2 (finish)") == 1
    assert task_log.count("[system] task done") == 1
    assert task_log.count("launched as a script") == 2
    output = capfd.readouterr().err
    assert output.count(f"system advanced *{ref.id_slug}*") == 1
    assert output.count(f"system finished *{ref.id_slug}*") == 1
    assert "claude advanced" not in output
    assert "claude finished" not in output


def test_script_block_returns_internal_script_stop_kind(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recurring can distinguish a script-owned block from an agent block."""
    ref = _create_script_task(
        script_repo,
        """
        import os
        import subprocess
        import sys

        raise SystemExit(subprocess.run([
            sys.executable,
            "-m",
            "coga.cli",
            "block",
            "--task",
            os.environ["COGA_TASK_SLUG"],
            "--reason",
            "A deterministic prerequisite is unavailable.",
        ]).returncode)
        """,
    )
    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: False,
    )
    monkeypatch.setattr(
        launch_module,
        "spawn_agent_session",
        _fail("agent spawned after script block"),
    )

    kind = launch_module.launch(
        ref.id_slug,
        args=[],
        agent_override=None,
        prompt_report=False,
        idle_timeout=None,
        max_session=None,
        return_timeout=True,
        script_failure_important=True,
    )

    assert kind.kind == "script"
    assert Ticket.read(ref.ticket_path).status == "blocked"


def test_nonzero_script_exit_halts_and_notifies_once(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_script_task(script_repo, "raise SystemExit(17)\n")
    notifications: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        "coga.launch_script.post",
        lambda *args, **kwargs: notifications.append((args, kwargs)),
    )
    monkeypatch.setattr(launch_module, "compose_prompt", _fail("prompt composed"))
    monkeypatch.setattr(
        launch_module,
        "spawn_agent_session",
        _fail("agent spawned"),
    )
    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: False,
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 17
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "in_progress"
    assert ticket.step == "1 (execute)"
    assert "script exited with code 17" in (script_repo / "log.md").read_text(encoding="utf-8")
    assert len(notifications) == 1
    args, kwargs = notifications[0]
    assert "💥 script failed" in str(args[1])
    assert kwargs["important"] is False
    assert kwargs["fatal"] is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal exit status")
def test_signal_killed_script_exits_128_plus_signal(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A signal reaching only the child (kill, OOM) must not leak -N to the shell.
    ref = _create_script_task(
        script_repo,
        "import os, signal\nos.kill(os.getpid(), signal.SIGTERM)\n",
    )
    notifications: list[str] = []
    monkeypatch.setattr(
        "coga.launch_script.post",
        lambda cfg, message, **kwargs: notifications.append(message),
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 143, result.output
    assert "script exited with code 143" in (script_repo / "log.md").read_text(encoding="utf-8")
    assert len(notifications) == 1
    assert "exit 143" in notifications[0]


@pytest.mark.parametrize("ticket_result", ["deleted", "malformed"])
def test_nonzero_script_exit_survives_unreadable_ticket_result(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    ticket_result: str,
) -> None:
    mutation = (
        'ticket.unlink()\n'
        if ticket_result == "deleted"
        else 'ticket.write_text("not a ticket\\n")\n'
    )
    ref = _create_script_task(
        script_repo,
        f"""
        import os
        from pathlib import Path

        ticket = Path(os.environ["COGA_TASK_TICKET"])
        {mutation}
        raise SystemExit(17)
        """,
    )
    notifications: list[str] = []
    monkeypatch.setattr(
        "coga.launch_script.post",
        lambda cfg, message, **kwargs: notifications.append(message),
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        _fail("agent skills refreshed after failed script"),
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 17, result.output
    assert "Script exited with 17" in result.output
    assert "script exited with code 17" in (script_repo / "log.md").read_text(encoding="utf-8")
    assert len(notifications) == 1
    assert "exit 17" in notifications[0]














def test_missing_script_on_chained_step_becomes_agent_handoff(
    script_repo: Path,
) -> None:
    ref = _create_two_step_script_task(
        script_repo,
        """
        import os
        import subprocess
        import sys
        from pathlib import Path

        if os.environ["COGA_TASK_STEP"].startswith("1 "):
            result = subprocess.run([
                sys.executable,
                "-m",
                "coga.cli",
                "bump",
                os.environ["COGA_TASK_SLUG"],
            ])
            Path(__file__).unlink()
            raise SystemExit(result.returncode)
        """,
    )
    ticket = Ticket.read(ref.ticket_path)

    outcome = run_script_chain(
        load_config(script_repo),
        ref,
        ticket,
        set(),
    )

    assert outcome.exit_code == 0
    assert outcome.needs_agent is True
    assert outcome.stop_reason is None
    assert outcome.ticket is not None
    assert outcome.ticket.step == "2 (finish)"
    assert script_entry_point(ref) is None




def test_human_assist_override_expires_at_agent_owned_step(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_two_step_script_task(
        script_repo,
        """
        import os
        import subprocess
        import sys

        if os.environ["COGA_TASK_STEP"].startswith("1 "):
            raise SystemExit(subprocess.run([
                sys.executable,
                "-m",
                "coga.cli",
                "bump",
                os.environ["COGA_TASK_SLUG"],
            ]).returncode)
        """,
        first_assignee="owner",
        second_assignee="agent",
        title="Human assist then agent",
    )
    spawned: list[str] = []

    def fake_spawn(cfg, target, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        spawned.append(agent.name)
        return launch_module.AgentSessionResult(0, "natural")

    monkeypatch.setattr(launch_module, "spawn_agent_session", fake_spawn)
    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: True,
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        lambda coga_os: None,
    )
    monkeypatch.setattr(
        launch_module.shutil,
        "which",
        lambda cli: f"/usr/bin/{cli}",
    )

    result = CliRunner().invoke(
        app,
        ["launch", ref.id_slug, "--agent", "codex"],
    )

    assert result.exit_code == 0, result.output
    assert spawned == ["claude"]
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.step == "2 (finish)"
    # The assist override expired at the agent step; the step's own role routes
    # it, and nothing was written to the ticket.
    assert ticket.current_step()["assignee"] == "agent"
    assert "assignee" not in ticket.frontmatter




def test_agent_handoff_uses_configuration_reloaded_after_script(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_script_task(
        script_repo,
        """
        import os
        from pathlib import Path

        task_dir = Path(os.environ["COGA_TASK_DIR"])
        config = task_dir.parents[1] / "coga.toml"
        config.write_text(
            config.read_text()
            + '\\n[agents.reviewer]\\ncli = "reviewer"\\nfile = "AGENTS.md"\\n'
        )
        ticket = Path(os.environ["COGA_TASK_TICKET"])
        ticket.write_text(
            ticket.read_text().replace("agent: claude", "agent: reviewer", 1)
        )
        """,
    )
    spawned: list[str] = []

    def fake_spawn(cfg, target, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        spawned.append(agent.name)
        return launch_module.AgentSessionResult(0, "natural")

    monkeypatch.setattr(launch_module, "spawn_agent_session", fake_spawn)
    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: True,
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        lambda coga_os: None,
    )
    monkeypatch.setattr(
        launch_module.shutil,
        "which",
        lambda cli: f"/usr/bin/{cli}",
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    # The handoff resolves the `agent` role against the *reloaded* config and
    # the *reloaded* ticket, so a main-agent change the script made takes effect.
    assert spawned == ["reviewer"]
    assert Ticket.read(ref.ticket_path).agent == "reviewer"


def test_chained_agent_env_uses_fresh_ticket_secrets(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_two_step_script_task(script_repo, "pass\n")
    (ref.task_dir / "ticket.py").unlink()
    monkeypatch.setenv("FRESH_SECRET_SOURCE", "fresh-value")
    child_envs: list[dict[str, str]] = []

    def fake_spawn(cfg, target, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        child_envs.append(dict(kwargs["env"]))
        if len(child_envs) == 1:
            current = Ticket.read(ref.ticket_path)
            current.frontmatter["secrets"] = [
                {"FRESH_SECRET": "env:FRESH_SECRET_SOURCE"}
            ]
            current.write(ref.ticket_path)
            bumped = CliRunner().invoke(app, ["bump", ref.id_slug])
            assert bumped.exit_code == 0, bumped.output
            return launch_module.AgentSessionResult(0, "done")
        return launch_module.AgentSessionResult(0, "natural")

    monkeypatch.setattr(launch_module, "spawn_agent_session", fake_spawn)
    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: True,
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        lambda coga_os: None,
    )
    monkeypatch.setattr(
        launch_module.shutil,
        "which",
        lambda cli: f"/usr/bin/{cli}",
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert len(child_envs) == 2
    assert "FRESH_SECRET" not in child_envs[0]
    assert child_envs[1]["FRESH_SECRET"] == "fresh-value"
    assert "FRESH_SECRET_SOURCE" not in child_envs[1]


def test_zero_exit_hands_blackboard_to_agent_on_the_same_step(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COGA_SCRIPT_TASK", "/outer/script")
    ref = _create_script_task(
        script_repo,
        """
        import os
        from pathlib import Path

        with Path(os.environ["COGA_TASK_BLACKBOARD"]).open("a") as handle:
            handle.write("\\nscript finding: retry ceiling is 30s\\n")
        """,
    )
    prompts: list[str] = []
    child_envs: list[dict[str, str]] = []

    def capture_prompt(cfg, target, ticket, **kwargs):  # type: ignore[no-untyped-def]
        prompt = compose_module.compose_prompt(cfg, target, ticket, **kwargs)
        prompts.append(prompt)
        return prompt

    def fake_repl(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        child_envs.append(dict(env))
        return ReplOutcome(exit_code=0, kind="natural")

    monkeypatch.setattr(launch_module, "compose_prompt", capture_prompt)
    monkeypatch.setattr(launch_module, "run_with_done_marker", fake_repl)
    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: True,
    )
    monkeypatch.setattr(
        launch_module.shutil,
        "which",
        lambda cli: f"/usr/bin/{cli}",
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        lambda coga_os: None,
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert prompts
    assert all("script finding: retry ceiling is 30s" in p for p in prompts)
    assert len(child_envs) == 1
    assert child_envs[0]["COGA_TASK_STEP"] == "1 (execute)"
    assert "COGA_SCRIPT_TASK" not in child_envs[0]
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "in_progress"
    assert ticket.step == "1 (execute)"


@pytest.mark.parametrize("blocked_resume", [False, True], ids=["active", "blocked"])
def test_script_chain_stops_when_next_step_hands_off_to_human(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    blocked_resume: bool,
) -> None:
    _write(
        script_repo / "workflows" / "deterministic" / "handoff.md",
        """
        ---
        name: deterministic/handoff
        description: Deterministic preparation followed by human review.
        steps:
          - name: prepare
            assignee: agent
          - name: approve
            assignee: owner
        ---

        ## prepare

        Run deterministic preparation.

        ## approve

        Review and approve the result.
        """,
    )
    counter = script_repo.parent / "script-runs.txt"
    cfg = load_config(script_repo)
    created = create_task(
        cfg=cfg,
        title="Prepare then approve",
        workflow_name="deterministic/handoff",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        force_directory=True,
    )
    ref = resolve_task(cfg, created["slug"])
    assert ref.task_dir is not None
    _write(
        ref.task_dir / "ticket.py",
        f"""
        import os
        import subprocess
        import sys
        from pathlib import Path

        counter = Path({str(counter)!r})
        count = int(counter.read_text()) if counter.exists() else 0
        counter.write_text(str(count + 1))
        raise SystemExit(subprocess.run([
            sys.executable,
            "-m",
            "coga.cli",
            "bump",
            os.environ["COGA_TASK_SLUG"],
        ]).returncode)
        """,
    )

    if blocked_resume:
        blocked = CliRunner().invoke(
            app,
            ["block", "--task", ref.id_slug, "--reason", "approve this result?"],
        )
        assert blocked.exit_code == 0, blocked.output

    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: blocked_resume,
    )
    monkeypatch.setattr(
        launch_module,
        "spawn_agent_session",
        _fail("agent spawned at human handoff"),
    )
    if blocked_resume:
        monkeypatch.setattr(
            launch_module,
            "_refresh_agent_skills_for_launch",
            lambda coga_os: None,
        )
        monkeypatch.setattr(
            launch_module.shutil,
            "which",
            lambda cli: f"/usr/bin/{cli}",
        )
    else:
        monkeypatch.setattr(
            launch_module,
            "compose_prompt",
            _fail("prompt composed"),
        )
        monkeypatch.setattr(
            launch_module,
            "_refresh_agent_skills_for_launch",
            _fail("agent skills refreshed"),
        )
        monkeypatch.setattr(
            launch_module.shutil,
            "which",
            _fail("agent CLI resolved"),
        )
        monkeypatch.setattr(Config, "agent_type", _fail("agent type resolved"))

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    if blocked_resume:
        assert result.exit_code == 2, result.output
        assert "coga unblock" in result.output
        assert not counter.exists()
        assert Ticket.read(ref.ticket_path).status == "blocked"
        assert "- [ ]" in read_blackboard(ref.ticket_path)
        return
    assert result.exit_code == 0, result.output
    assert counter.read_text(encoding="utf-8") == "1"
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "in_progress"
    assert ticket.step == "2 (approve)"
    assert ticket.current_step()["assignee"] == "owner"
    assert "next step hands off to marc" in result.output


@pytest.mark.parametrize("unavailable", ["tty", "cli", "human"])
def test_open_script_step_fails_loud_when_no_agent_can_continue(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    unavailable: str,
) -> None:
    ref = _create_script_task(
        script_repo,
        """
        import os
        from pathlib import Path

        with Path(os.environ["COGA_TASK_BLACKBOARD"]).open("a") as handle:
            handle.write("\\ndeterministic work retained\\n")
        """,
    )
    if unavailable == "human":
        ticket = Ticket.read(ref.ticket_path)
        hold_by_owner(ticket)
        ticket.write(ref.ticket_path)
        monkeypatch.setenv("COGA_SCRIPT_TASK", str(ref.path))

    monkeypatch.setattr(launch_module, "compose_prompt", _fail("prompt composed"))
    monkeypatch.setattr(
        launch_module,
        "spawn_agent_session",
        _fail("agent spawned"),
    )
    monkeypatch.setattr(
        launch_module,
        "interactive_stdio_has_tty",
        lambda: unavailable != "tty",
    )
    monkeypatch.setattr(
        launch_module.shutil,
        "which",
        (lambda cli: None)
        if unavailable == "cli"
        else (lambda cli: f"/usr/bin/{cli}"),
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 2
    assert ref.id_slug in result.output
    if unavailable == "human":
        assert "current step" in result.output
        assert "deterministic work retained" not in read_blackboard(ref.ticket_path)
        return
    assert "step 1 (execute)" in result.output
    assert "deterministic work retained" in read_blackboard(ref.ticket_path)
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "in_progress"
    assert ticket.step == "1 (execute)"


@pytest.mark.parametrize("value", ["machine-value", "Café → 東京"])
def test_bootstrap_script_is_stateless_and_keeps_stdout_machine_readable(
    script_repo: Path,
    value: str,
) -> None:
    bootstrap = script_repo / "bootstrap" / "deterministic"
    _write(
        bootstrap / "ticket.md",
        """
        ---
        title: Deterministic command
        ---

        ## Description

        Print one machine-readable value.
        """,
    )
    _write(
        bootstrap / "ticket.py",
        f"""
        import os
        import sys

        assert sys.argv[1:] == []
        assert os.environ["COGA_TASK_SLUG"] == "bootstrap/deterministic"
        assert "COGA_TASK_BLACKBOARD" not in os.environ
        assert "COGA_TASK_STEP" not in os.environ
        print({value!r})
        print({value!r}, file=sys.stderr)
        """,
    )
    env = os.environ.copy()
    env.pop("PYTHONIOENCODING", None)
    env.pop("PYTHONUTF8", None)
    source_path = str(_SOURCE_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        source_path if not existing else source_path + os.pathsep + existing
    )
    env["PATH"] = "/agents-absent"

    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "deterministic"],
        cwd=script_repo,
        env=env,
        check=False,
        capture_output=True,
        text=True, encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == value + "\n"
    assert value in result.stderr
    assert "Launch: task bootstrap/deterministic" in result.stderr
    assert "bootstrap/deterministic: script ran successfully" in result.stderr
    assert not (script_repo / "log.md").exists()


def _write_argv_probe(coga_os: Path, observed_path: Path) -> None:
    _write(
        coga_os / "bootstrap" / "argv-probe" / "ticket.md",
        """
        ---
        title: Argv probe
        ---

        ## Description

        Record the operands launch passed.
        """,
    )
    _write(
        coga_os / "bootstrap" / "argv-probe" / "ticket.py",
        f"""
        import json
        import sys
        from pathlib import Path

        Path({str(observed_path)!r}).write_text(json.dumps(sys.argv))
        """,
    )


def test_bootstrap_script_receives_trailing_launch_args_as_argv(
    script_repo: Path,
) -> None:
    observed_path = script_repo.parent / "argv.json"
    _write_argv_probe(script_repo, observed_path)

    result = CliRunner().invoke(
        app,
        ["launch", "bootstrap/argv-probe", "--", "two words", "--no-launch", "x"],
    )

    assert result.exit_code == 0, result.output
    argv = json.loads(observed_path.read_text(encoding="utf-8"))
    assert Path(argv[0]).as_posix().endswith("bootstrap/argv-probe/ticket.py")
    assert argv[1:] == ["two words", "--no-launch", "x"]


def test_bootstrap_script_without_launch_args_gets_only_its_path(
    script_repo: Path,
) -> None:
    observed_path = script_repo.parent / "argv.json"
    _write_argv_probe(script_repo, observed_path)

    result = CliRunner().invoke(app, ["launch", "bootstrap/argv-probe"])

    assert result.exit_code == 0, result.output
    argv = json.loads(observed_path.read_text(encoding="utf-8"))
    assert len(argv) == 1
    assert Path(argv[0]).as_posix().endswith("bootstrap/argv-probe/ticket.py")


def test_bootstrap_script_runs_without_configured_agents(
    script_repo: Path,
) -> None:
    config = script_repo / "coga.toml"
    text = config.read_text(encoding="utf-8")
    start = text.index("[agents.claude]")
    end = text.index("[notification]")
    config.write_text(text[:start] + text[end:], encoding="utf-8", newline="\n")
    observed_path = script_repo.parent / "argv.json"
    _write_argv_probe(script_repo, observed_path)

    result = CliRunner().invoke(app, ["launch", "bootstrap/argv-probe", "--", "a"])

    assert result.exit_code == 0, result.output
    assert json.loads(observed_path.read_text(encoding="utf-8"))[1:] == ["a"]




@pytest.mark.parametrize("status", ["active", "draft", "paused", "assist"])
def test_stateful_script_target_refuses_launch_args_before_any_effect(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
) -> None:
    marker = script_repo.parent / "script-ran"
    ref = _create_script_task(
        script_repo,
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
    )
    ticket = Ticket.read(ref.ticket_path)
    launch_argv = ["launch", ref.id_slug]
    if status == "assist":
        ticket.frontmatter["status"] = "in_progress"
        hold_by_owner(ticket)
        launch_argv += ["--agent", "codex"]
        monkeypatch.setattr(launch_module, "interactive_stdio_has_tty", lambda: True)
    elif status != "active":
        ticket.frontmatter["status"] = status
    ticket.write(ref.ticket_path)
    ticket_before = ref.ticket_path.read_bytes()
    log_path = script_repo / "log.md"
    log_before = log_path.read_bytes() if log_path.exists() else None
    for module in ("coga.launch", "coga.launch_script"):
        monkeypatch.setattr(
            f"{module}.build_launch_env", _fail("secrets resolved")
        )

    result = CliRunner().invoke(app, [*launch_argv, "--", "hidden-input"])

    assert result.exit_code == 2, result.output
    assert f"Cannot pass trailing arguments to {ref.id_slug}" in result.output
    assert "takes no launch arguments" in result.output
    assert not marker.exists()
    assert ref.ticket_path.read_bytes() == ticket_before
    assert (log_path.read_bytes() if log_path.exists() else None) == log_before


def test_stateful_script_phase_rejects_args_from_a_caller(script_repo: Path) -> None:
    ref = _create_script_task(script_repo, "pass\n")
    with pytest.raises(ValueError, match="takes no launch arguments"):
        run_script_phase(
            load_config(script_repo),
            ref,
            Ticket.read(ref.ticket_path),
            stateless=False,
            args=["x"],
        )








@pytest.fixture
def read_only_repo(script_repo: Path) -> Path:
    _write(
        script_repo / "coga.toml",
        '''
        version = 1
        [git]
        enabled = true
        [notification]
        channels = []
        [aliases]
        inspect = "launch --read-only bootstrap/inspect"
        ''',
    )
    (script_repo / "coga.local.toml").unlink()
    _write(script_repo / "bootstrap" / "inspect" / "ticket.md", "---\ntitle: Inspect\n---\n")
    return script_repo


@pytest.mark.parametrize("alias", [False, True])
@pytest.mark.parametrize("exit_code", [0, 7, 75])
def test_read_only_script_preserves_streams_argv_authority_and_dirty_checkout(
    read_only_repo: Path, alias: bool, exit_code: int,
) -> None:
    script = read_only_repo / "bootstrap" / "inspect" / "ticket.py"
    _write(
        script,
        f'''
        import json
        import os
        import sys
        assert os.getcwd() == {str(read_only_repo.parent)!r}
        assert os.environ["COGA_TASK_SLUG"] == "bootstrap/inspect"
        assert os.environ["COGA_SCRIPT_TASK"] == {str(script.parent.resolve())!r}
        for key in ("COGA_EXPECTED_TASK", "COGA_EXPECTED_STEP", "COGA_EXPECTED_AGENT",
                    "COGA_ASSIST_AGENT",
                    "COGA_SUPERVISED", "COGA_TASK_BLACKBOARD", "COGA_TASK_STEP"):
            assert key not in os.environ, key
        assert not os.environ.get("COGA_DONE_SENTINEL")
        assert os.environ["SCOPED_TOKEN"] == "secret-value"
        assert "TOKEN_SOURCE" not in os.environ
        sys.stdout.buffer.write(sys.stdin.buffer.read())
        print(json.dumps(sys.argv[1:]), flush=True)
        sys.stderr.buffer.write(b"reader stderr\\n")
        raise SystemExit({exit_code})
        ''',
    )
    _write(
        script.parent / "ticket.md",
        "---\ntitle: Inspect\nsecrets:\n  - SCOPED_TOKEN: env:TOKEN_SOURCE\n---\n",
    )
    root = read_only_repo.parent
    def git_command(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(root), *args])
    git_command("init", "-b", "main")
    git_command("config", "core.autocrlf", "false")
    git_command("add", ".")
    git_command("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "seed")
    # Effective local definitions and unrelated state must stay dirty and readable.
    _write(script.parent / "ticket.md", (script.parent / "ticket.md").read_text() + "Local intent.\n")
    _write(read_only_repo / "contexts" / "dirty.md", "unpublished context\n")
    _write(read_only_repo / "log.md", "unpublished audit\n")
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    status = git_command("status", "--porcelain=v1")
    head = git_command("rev-parse", "HEAD")
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(_SOURCE_ROOT / "src"), "PATH": "/agents-absent",
        "PYTHONIOENCODING": "utf-8", "TOKEN_SOURCE": "secret-value",
        "COGA_DONE_SENTINEL": str(root / "outer-done"),
        "COGA_EXPECTED_TASK": str(root / "outer-task"), "COGA_EXPECTED_STEP": "1 (outer)",
        "COGA_EXPECTED_AGENT": "codex", "COGA_SUPERVISED": "1",
        "COGA_ASSIST_AGENT": "codex",
    })
    argv = ["inspect"] if alias else ["launch", "--read-only", "bootstrap/inspect"]
    operands = ["two words", "", "--write-looking-operand", "Café → 東京"]
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", *argv, "--", *operands],
        cwd=read_only_repo, env=env, input=b"stdin bytes\n", capture_output=True, check=False,
    )
    assert result.returncode == exit_code, result.stderr
    assert result.stdout == b"stdin bytes\n" + (json.dumps(operands) + "\n").encode()
    # Launch's one run-state warning (pytest's tmp path is long) is the only
    # framing read-only dispatch may add, and only on stderr.
    stderr = b"".join(
        line for line in result.stderr.splitlines(keepends=True)
        if not line.startswith(RUN_STATE_PATH_WARNING.encode())
    )
    assert stderr.endswith(b"reader stderr\n")
    if not alias:
        assert stderr == b"reader stderr\n"
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    assert git_command("status", "--porcelain=v1") == status
    assert git_command("rev-parse", "HEAD") == head
    assert git_command("branch", "--show-current").strip() == b"main"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal exit status")
def test_read_only_signal_killed_script_exits_128_plus_signal(read_only_repo: Path) -> None:
    _write(
        read_only_repo / "bootstrap" / "inspect" / "ticket.py",
        "import os, signal\nos.kill(os.getpid(), signal.SIGTERM)\n",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_SOURCE_ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "launch", "--read-only", "bootstrap/inspect"],
        cwd=read_only_repo, env=env, capture_output=True, check=False,
    )
    assert result.returncode == 143, result.stderr


@pytest.mark.parametrize("alias", [False, True])
@pytest.mark.parametrize("failure", ["missing-script", "missing-secret", "malformed-config"])
def test_read_only_refusals_never_publish_or_prepare_agents(
    read_only_repo: Path, monkeypatch: pytest.MonkeyPatch, alias: bool, failure: str,
) -> None:
    from coga.cli import main

    bootstrap = read_only_repo / "bootstrap" / "inspect"
    if failure != "missing-script":
        _write(bootstrap / "ticket.py", "raise AssertionError('must not spawn')\n")
    if failure == "missing-secret":
        _write(bootstrap / "ticket.md", "---\ntitle: Inspect\nsecrets:\n  - TOKEN: env:READ_ONLY_MISSING\n---\n")
        monkeypatch.delenv("READ_ONLY_MISSING", raising=False)
    if failure == "malformed-config":
        _write(read_only_repo / "coga.toml", "malformed = [\n")
    before = {p: p.read_bytes() for p in read_only_repo.rglob("*") if p.is_file()}
    for name in ("spawn_agent_session", "_refresh_agent_skills_for_launch"):
        monkeypatch.setattr(launch_module, name, _fail(name))
    monkeypatch.setattr("coga.launch_script.subprocess.run", _fail("script spawn"))
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    argv = ["inspect"] if alias else ["launch", "--read-only", "bootstrap/inspect"]
    monkeypatch.setattr(sys, "argv", ["coga", *argv])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert {p: p.read_bytes() for p in read_only_repo.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("option", ["--agent", "--prompt-report", "--idle-timeout", "--max-session", "--return-timeout", "--script-failure-important"])
def test_read_only_rejects_agent_options_before_config(option: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launch_module, "load_config", _fail("config loaded"))
    values = ["codex"] if option == "--agent" else ["1"] if option in {"--idle-timeout", "--max-session"} else []
    result = CliRunner().invoke(app, ["launch", "--read-only", option, *values, "bootstrap/inspect"])
    assert result.exit_code == 2, result.output


def test_read_only_rejects_stateful_target_before_secrets(script_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref = _create_script_task(script_repo, "raise AssertionError('must not run')")
    monkeypatch.setattr("coga.launch_script.build_launch_env", _fail("secrets resolved"))
    result = CliRunner().invoke(app, ["launch", "--read-only", ref.id_slug])
    assert result.exit_code == 2
    assert "requires a bootstrap target" in result.output


def test_read_only_vanished_script_refuses_without_agent_fallback(read_only_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = read_only_repo / "bootstrap" / "inspect" / "ticket.py"
    _write(script, "pass\n")
    original = launch_module.run_script_phase
    def remove_before_phase(*args, **kwargs):
        script.unlink()
        return original(*args, **kwargs)
    monkeypatch.setattr(launch_module, "run_script_phase", remove_before_phase)
    monkeypatch.setattr(launch_module, "spawn_agent_session", _fail("agent fallback"))
    result = CliRunner().invoke(app, ["launch", "--read-only", "bootstrap/inspect"])
    assert result.exit_code == 2
    assert "entry disappeared" in result.output


def test_read_only_python_api_reuses_script_executor_without_launch_effects(
    read_only_repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace
    _write(read_only_repo / "bootstrap" / "inspect" / "ticket.py", "pass\n")
    calls = []
    def script_spawn(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=9)
    for name in ("spawn_agent_session", "_refresh_agent_skills_for_launch"):
        monkeypatch.setattr(launch_module, name, _fail(name))
    monkeypatch.setattr("coga.launch_script.subprocess.run", script_spawn)
    result = launch_module.launch("bootstrap/inspect", args=["two words", ""], read_only=True)
    assert result.exit_code == 9
    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert argv[0] == sys.executable
    assert argv[2:] == ["two words", ""]
    assert kwargs["cwd"] == read_only_repo.parent
    assert not {"capture_output", "stdin", "stdout", "stderr"} & kwargs.keys()




def test_agent_preparation_checks_order_without_repo_writes(script_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref = _create_script_task(script_repo, "pass\n")
    cfg = load_config(script_repo)
    ticket = Ticket.read(ref.ticket_path)
    calls = []
    monkeypatch.setattr(launch_module.shutil, "which", lambda cli: calls.append("cli") or "/agent")
    monkeypatch.setattr(launch_module, "compose_prompt", lambda *a, **kw: calls.append("prompt") or "validated prompt")
    monkeypatch.setattr(launch_module, "build_launch_env", lambda *a: calls.append("secrets") or {"TOKEN": "scoped"})
    monkeypatch.setattr(launch_module, "agent_command_refusal", lambda *a, **kw: calls.append("command") or None)
    before = {p: p.read_bytes() for p in script_repo.rglob("*") if p.is_file()}
    prepared = launch_module.prepare_agent_launch(cfg, ref, ticket, "claude")
    assert calls == ["cli", "prompt", "secrets", "command"]
    assert prepared.prompt == "validated prompt"
    assert prepared.env == {"TOKEN": "scoped"}
    assert prepared.agent == cfg.agent_type("claude")
    assert {p: p.read_bytes() for p in script_repo.rglob("*") if p.is_file()} == before


def test_agent_preparation_command_refusal_is_typed_without_publication(script_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref = _create_script_task(script_repo, "pass\n")
    cfg = load_config(script_repo)
    monkeypatch.setattr(launch_module.shutil, "which", lambda cli: "/agent")
    monkeypatch.setattr(launch_module, "agent_command_refusal", lambda *a, **kw: "command cannot be represented")
    with pytest.raises(launch_module.AgentPreparationError, match="cannot be represented") as exc:
        launch_module.prepare_agent_launch(cfg, ref, Ticket.read(ref.ticket_path), "claude")
    assert exc.value.command_refused


def test_ordinary_bootstrap_keeps_user_requirement(read_only_repo: Path) -> None:
    bootstrap = read_only_repo / "bootstrap" / "inspect"
    _write(bootstrap / "ticket.py", "print('writer ran')\n")
    result = CliRunner().invoke(app, ["launch", "bootstrap/inspect"])
    assert result.exit_code == 2
    assert "No `user` set" in result.output
    _write(read_only_repo / "coga.local.toml", 'user = "marc"\n')
    result = CliRunner().invoke(app, ["launch", "bootstrap/inspect"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("name,argv", [
    ("show", ["show", "missing"]),
    ("status", ["status", "--order-by", "invalid"]),
    ("usage", ["usage", "--by", "invalid"]),
    ("recurring-list", ["recurring", "list", "--invalid"]),
])
@pytest.mark.parametrize("branch", ["main", "feature"])
def test_packaged_reports_preserve_dirty_git_checkout(
    read_only_repo: Path, name: str, argv: list[str], branch: str,
) -> None:
    """Real alias/subcommand dispatch preserves files, index, HEAD and refs."""
    root = read_only_repo.parent
    def git_command(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(root), *args])
    git_command("init", "-b", "main")
    git_command("config", "core.autocrlf", "false")
    git_command("add", ".")
    git_command("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "seed")
    if branch != "main":
        git_command("checkout", "-b", branch)
    # Dirty tracked log plus untracked ticket, context and full local definition.
    _write(read_only_repo / "log.md", "unpublished audit\n")
    _write(read_only_repo / "tasks" / "sample.md",
           "---\ntitle: Sample\nstatus: draft\n---\n\n## Description\nSample\n\n<!-- coga:blackboard -->\n")
    _write(read_only_repo / "contexts" / "dirty.md", "unpublished context\n")
    source = _SOURCE_ROOT / "src/coga/resources/templates/coga/bootstrap" / name
    shutil.copytree(source, read_only_repo / "bootstrap" / name,
                    ignore=shutil.ignore_patterns("__pycache__"))
    def snapshot() -> dict[Path, bytes]:
        return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    before = snapshot()
    status = git_command("status", "--porcelain=v1")
    refs = git_command("show-ref", "--head")
    env = dict(os.environ, PYTHONPATH=str(_SOURCE_ROOT / "src"),
               PYTHONDONTWRITEBYTECODE="1", TERM="dumb")
    normal = ["show", "sample"] if name == "show" else ["recurring", "list"] if name == "recurring-list" else [name]
    for command, expected in ((normal, 0), ([*(normal[:2] if name == "recurring-list" else normal[:1]), "--help"], 0), (argv, 2)):
        result = subprocess.run([sys.executable, "-m", "coga.cli", *command],
                                cwd=read_only_repo, env=env, capture_output=True, text=True)
        assert result.returncode == expected, result.stderr
        assert "state sweep withheld" not in result.stderr
        assert snapshot() == before
        assert git_command("status", "--porcelain=v1") == status
        assert git_command("show-ref", "--head") == refs
    assert not (root / ".agent-skills").exists()


@pytest.mark.parametrize("argv", [
    ["show", "missing"], ["status"], ["usage"], ["recurring", "list"],
])
def test_report_dispatch_uses_read_executor_without_writer_effects(
    read_only_repo: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str],
) -> None:
    from coga.cli import main
    from types import SimpleNamespace
    for name in ("spawn_agent_session", "_refresh_agent_skills_for_launch"):
        monkeypatch.setattr(launch_module, name, _fail(name))
    calls = []
    def script_spawn(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr("coga.launch_script.subprocess.run", script_spawn)
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["coga", *argv])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert len(calls) == 1
    assert calls[0][0][1].endswith("ticket.py")
    assert "COGA_SUPERVISED" not in calls[0][1]["env"]


@pytest.mark.parametrize("command", ["megalaunch", "pick", "retire", "slack"])
@pytest.mark.parametrize("workspace", ["absent", "no-user", "invalid-config"])
def test_command_script_help_without_setup(tmp_path: Path, command: str, workspace: str) -> None:
    cwd = tmp_path / "help"
    cwd.mkdir()
    if workspace != "absent":
        _write(cwd / "coga.toml", 'version = 1\n[git]\nenabled = false\n' if workspace == "no-user" else 'not valid toml = [')
    before = {p.name: p.read_bytes() for p in cwd.iterdir()}
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", command, "--help"],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Usage:" in result.stdout
    assert {p.name: p.read_bytes() for p in cwd.iterdir()} == before


@pytest.mark.parametrize("argv", [["megalaunch", "--agent", "--help"], ["retire", "1", "--agent", "--help"], ["slack", "--task", "x", "--message", "--help"]])
def test_command_script_help_consumed_as_value_fails_closed(tmp_path: Path, argv: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", *argv], cwd=tmp_path,
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not list(tmp_path.iterdir())


def test_script_help_for_unknown_bootstrap_reports_without_traceback(script_repo: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "launch", "bootstrap/no-such-target", "--", "--help"],
        cwd=script_repo, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "no-such-target" in result.stdout + result.stderr


def test_script_help_has_no_launch_identity_or_git_calls(script_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from coga.task_env import TASK_ENV_KEYS

    seen = {}
    def forbidden(*args, **kwargs):
        raise AssertionError("help touched Git")
    def child(argv, *, cwd, env, **kwargs):
        seen.update(env)
        assert cwd == script_repo.parent
        assert argv[-1] == "--help"
        return 0, False
    for key in (*TASK_ENV_KEYS, "COGA_SUPERVISED", "COGA_DONE_SENTINEL", "COGA_EXPECTED_TASK", "COGA_EXPECTED_STEP", "COGA_EXPECTED_AGENT"):
        monkeypatch.setenv(key, "outer")
    monkeypatch.setattr("coga.launch_script.run_foreground_child", child)
    assert launch_module.launch("bootstrap/megalaunch", args=["--help"]).exit_code == 0
    assert seen["COGA_SCRIPT_HELP"] == "1"
    assert all(key not in seen for key in TASK_ENV_KEYS if key != "COGA_SCRIPT_HELP")
    assert "COGA_SUPERVISED" not in seen
    assert "COGA_DONE_SENTINEL" not in seen


@pytest.mark.parametrize("code", [0, 1, 2, 75, 130])
def test_queue_alias_preserves_local_script_argv_streams_and_status(script_repo: Path, code: int) -> None:
    bootstrap = script_repo / "bootstrap/megalaunch"
    _write(bootstrap / "ticket.md", '---\ntitle: Local queue\n---\n')
    _write(bootstrap / "ticket.py", f'''
        import json, os, sys
        print(json.dumps([sys.argv[1:], os.getcwd(), os.environ.get("COGA_SCRIPT_HELP")]))
        print("local stderr", file=sys.stderr)
        raise SystemExit({code})
    ''')
    nested = script_repo.parent / "nested"
    nested.mkdir()
    argv = ["word with spaces", "--agent", "option-like", "--", "--help"]
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "megalaunch", *argv], cwd=nested,
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == code, result.stdout + result.stderr
    assert json.loads(result.stdout) == [argv, str(script_repo.parent), None]
    assert "local stderr" in result.stderr
    assert "Launch:" not in result.stdout
    assert not (script_repo / "tasks").exists()


def test_classified_bootstrap_script_vanishes_without_agent_fallback(script_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_config(script_repo)
    ref = resolve_bootstrap(cfg, "retire")
    monkeypatch.setattr("coga.launch_script.script_entry_point", lambda *args, **kwargs: None)
    with pytest.raises(FileNotFoundError, match="Classified bootstrap script disappeared"):
        run_script_phase(cfg, ref, Ticket.read(ref.ticket_path), stateless=True)


@pytest.mark.parametrize("code,expected", [(-2, 130), (-15, 143), (75, 75), (130, 130)])
def test_foreground_script_wait_restores_handlers_and_forwards_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, code: int, expected: int) -> None:
    import signal
    from coga.process_relay import run_foreground_child

    before = signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)
    forwarded = []
    class Child:
        def send_signal(self, signum):
            forwarded.append(signum)
        def wait(self):
            for _ in range(2):
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            assert callable(signal.getsignal(signal.SIGINT))
            return code
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: Child())
    result, terminated = run_foreground_child(["child"], cwd=tmp_path, env={}, defer_interrupt=True)
    assert result == expected and terminated
    assert forwarded == [signal.SIGTERM]
    assert (signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)) == before


# --- `coga slack` through its default alias and real script phase -------------


def _run_slack(cwd: Path, *argv: str, env: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, "-m", "coga.cli", "slack", *argv],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
        env=env,
    )


def test_slack_alias_runs_the_edge_script_end_to_end(script_repo: Path, tmp_path: Path) -> None:
    """Notifications are off here, so the real child never reaches a webhook."""
    cfg = load_config(script_repo)
    slug = create_task(
        cfg=cfg, title="Work", workflow_name="direct/body", contexts=[],
        owner="marc", agent="claude", status="active",
    )["slug"]
    sentinel = tmp_path / "outer.done"
    env = {**os.environ, "COGA_DONE_SENTINEL": str(sentinel)}

    result = _run_slack(script_repo, "--task", slug, "--message", "hi there", env=env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1] == "posted"
    assert "no channels configured" in result.stderr
    assert "slack: hi there" in (script_repo / "log.md").read_text(encoding="utf-8")
    assert not sentinel.exists()


def test_slack_alias_on_bootstrap_target_never_completes(script_repo: Path, tmp_path: Path) -> None:
    sentinel = tmp_path / "outer.done"
    env = {**os.environ, "COGA_DONE_SENTINEL": str(sentinel)}

    result = _run_slack(
        script_repo, "--task", "bootstrap/resolve-conflicts", "--message", "1 conflict",
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "slack: 1 conflict" in (script_repo / "log.md").read_text(encoding="utf-8")
    assert not sentinel.exists()


@pytest.mark.parametrize(
    "argv", [["--task", "no-such-task", "--message", "hi"], ["--task", "x", "--message", " "]]
)
def test_slack_alias_propagates_refusal_status(script_repo: Path, argv: list[str]) -> None:
    result = _run_slack(script_repo, *argv)

    assert result.returncode == 2, result.stdout + result.stderr
    log = script_repo / "log.md"
    assert not log.exists() or "slack:" not in log.read_text(encoding="utf-8")


def test_slack_alias_works_from_inside_a_running_script_phase(script_repo: Path) -> None:
    """`coga.reminders` posts by running `coga slack` from a script ticket."""
    ref = _create_script_task(
        script_repo,
        "import os, subprocess, sys\n"
        "slug = os.environ['COGA_TASK_SLUG']\n"
        "coga = [sys.executable, '-m', 'coga.cli']\n"
        "subprocess.run([*coga, 'slack', '--task', slug, '--message', 'nested fyi'], check=True)\n"
        "subprocess.run([*coga, 'bump', slug], check=True)\n",
    )

    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "launch", ref.id_slug],
        cwd=script_repo, capture_output=True, text=True, encoding="utf-8", check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "posted" in result.stdout
    assert f"[{ref.id_slug}]" in (script_repo / "log.md").read_text(encoding="utf-8")
    assert "slack: nested fyi" in (script_repo / "log.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("entry", ["launch", "megalaunch", "recurring"])
def test_workflow_run_step_hands_off_to_owner(script_repo: Path, monkeypatch, entry) -> None:
    _write(
        script_repo / "workflows" / "deterministic" / "run-step.md",
        """
        ---
        name: deterministic/run-step
        steps:
          - name: compute
            run: fixture/compute
            assignee: agent
          - name: inspect
            assignee: owner
        ---
        ## inspect

        Inspect the result.
        """,
    )
    skill = script_repo / "skills" / "fixture" / "compute"
    _write(skill / "SKILL.md", "# Compute\n")
    _write(
        skill / "run.py",
        """
        import os
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]],
            check=True,
        )
        """,
    )
    cfg = load_config(script_repo)
    created = create_task(
        cfg=cfg,
        title="Run workflow script",
        workflow_name="deterministic/run-step",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    slug = created["slug"]
    ref = resolve_task(cfg, slug)
    assert ref.task_dir is None
    assert not (script_repo.parent / ".git").exists()

    if entry == "launch":
        result = CliRunner().invoke(app, ["launch", slug])
        assert result.exit_code == 0, result.output
    elif entry == "megalaunch":
        from coga_edge import megalaunch

        monkeypatch.setattr(megalaunch, "interactive_stdio_has_tty", lambda: True)
        run = megalaunch.run_megalaunch(cfg, selection=[slug])
        assert run.counts["completed"] == 1
    else:
        _write(
            script_repo / "recurring" / "script-check" / "ticket.md",
            """
            ---
            title: Workflow script check
            schedule: "0 0 * * *"
            workflow: deterministic/run-step
            ---
            ## Description

            Run the deterministic check.

            <!-- coga:blackboard -->
            """,
        )
        result = CliRunner().invoke(app, ["recurring", "launch", "script-check"])
        assert result.exit_code == 0, result.output
        ref = resolve_task(cfg, "recurring/script-check")
    assert Ticket.read(ref.ticket_path).step == "2 (inspect)"
    assert "[system] advanced" in (script_repo / "log.md").read_text(encoding="utf-8")


def test_cli_lifecycle_in_a_directory_without_git(tmp_path, monkeypatch):
    runner = CliRunner()

    def cli(*args):
        result = runner.invoke(app, list(args))
        assert result.exit_code == 0, result.output

    monkeypatch.chdir(tmp_path)
    cli("init", "--user", "marc")
    root = tmp_path / "coga"
    _write(
        root / "workflows" / "local.md",
        """
        ---
        name: local
        steps:
          - name: compute
            assignee: agent
            run: fixture/compute
          - name: inspect
            assignee: owner
          - name: finish
            assignee: owner
        ---
        ## inspect

        Inspect the result.

        ## finish

        Finish the result.
        """,
    )
    skill = root / "skills" / "fixture" / "compute"
    _write(skill / "SKILL.md", "# Compute\n")
    _write(
        skill / "run.py",
        """
        import os
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]],
            check=True,
        )
        """,
    )
    slug = "local-check"
    cli("create", "Local check", "--description", "Exercise the local lifecycle.", "--workflow", "local")
    cli("mark", "active", slug)
    cli("launch", slug)
    path = root / "tasks" / f"{slug}.md"
    assert Ticket.read(path).step == "2 (inspect)"
    cli("bump", slug)
    assert Ticket.read(path).step == "3 (finish)"
    cli("block", "--task", slug, "--reason", "Choose a timeout")
    assert Ticket.read(path).status == "blocked"
    cli("unblock", slug, "--answer", "Five minutes")
    assert Ticket.read(path).status == "active"
    assert not (tmp_path / ".git").exists()


@pytest.mark.parametrize("in_session,target", [(False, "active"), (True, "in_progress")])
def test_local_unblock_uses_the_launched_ticket_environment(script_repo, monkeypatch, in_session, target):
    ref = _create_script_task(script_repo, "# no-op")
    runner = CliRunner()
    blocked = runner.invoke(app, ["block", "--task", ref.id_slug, "--reason", "Choose a timeout"])
    assert blocked.exit_code == 0, blocked.output
    if in_session:
        monkeypatch.setenv("COGA_TASK_TICKET", str(ref.ticket_path))
    answered = runner.invoke(app, ["unblock", ref.id_slug, "--answer", "Five minutes"])
    assert answered.exit_code == 0, answered.output
    assert Ticket.read(ref.ticket_path).status == target
    assert "Five minutes" in read_blackboard(ref.ticket_path)


# --- run state (`coga/launch` "Run state") -----------------------------------


_RUN_STATE_SCRIPT = """
import json
import os
import sys
import tempfile
from pathlib import Path

fd, name = tempfile.mkstemp()
os.close(fd)
data = Path(os.environ["COGA_TASK_DATA_DIR"])
(data / "keep.txt").write_text("evidence")
Path({observed!r}).write_text(json.dumps({{
    "tmpdir": os.environ["TMPDIR"],
    "tmp": os.environ["TMP"],
    "temp": os.environ["TEMP"],
    "system": os.environ["COGA_SYSTEM_TMPDIR"],
    "data": os.environ["COGA_DATA_DIR"],
    "task_data": str(data),
    "mkstemp": name,
}}))
raise SystemExit({code})
"""


def _patch_agent_spawn(monkeypatch: pytest.MonkeyPatch, fake_repl) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(launch_module, "run_with_done_marker", fake_repl)
    monkeypatch.setattr(launch_module, "interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(launch_module.shutil, "which", lambda cli: f"/usr/bin/{cli}")
    monkeypatch.setattr(launch_module, "_refresh_agent_skills_for_launch", lambda coga_os: None)


def test_launch_gives_script_and_agent_one_purged_tmp_and_durable_data(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from coga.validate import emit_report, run as validate_run

    observed = script_repo.parent / "observed.json"
    ref = _create_script_task(
        script_repo, _RUN_STATE_SCRIPT.format(observed=str(observed), code=0),
    )
    system = os.environ["TMPDIR"]
    agent_seen: dict[str, object] = {}

    def fake_repl(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        tmpdir = Path(env["TMPDIR"])
        agent_seen.update(
            tmpdir=tmpdir, exists=tmpdir.is_dir(),
            task_data=env["COGA_TASK_DATA_DIR"], system=env["COGA_SYSTEM_TMPDIR"],
        )
        (tmpdir / "agent-scratch").write_text("x")
        return ReplOutcome(exit_code=0, kind="natural")

    _patch_agent_spawn(monkeypatch, fake_repl)

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    seen = json.loads(observed.read_text(encoding="utf-8"))
    tmp_root = (script_repo / ".coga" / "tmp").resolve()
    tmpdir = Path(seen["tmpdir"])
    assert tmpdir.parent == tmp_root
    assert seen["tmp"] == seen["temp"] == seen["tmpdir"]
    assert Path(seen["mkstemp"]).parent == tmpdir
    assert seen["system"] == system
    data_root = (script_repo / ".coga" / "data").resolve()
    assert seen["data"] == str(data_root)
    assert seen["task_data"] == str(data_root / "tasks" / ref.id_slug)
    # The agent session shares the launch's one scope.
    assert agent_seen == {
        "tmpdir": tmpdir, "exists": True,
        "task_data": seen["task_data"], "system": system,
    }
    # Temporaries are purged; durable data survives and is reported.
    assert not tmpdir.exists()
    assert list(tmp_root.iterdir()) == []
    keep = data_root / "tasks" / ref.id_slug / "keep.txt"
    assert keep.read_text() == "evidence"

    capsys.readouterr()
    emit_report(validate_run(load_config(script_repo)), json_output=True)
    state = json.loads(capsys.readouterr().out)["state"]
    entries = [e for e in state["entries"] if e["owner"] == ref.id_slug]
    assert entries == [{
        "owner": ref.id_slug, "path": str(keep.parent), "bytes": len("evidence"),
        "files": 1, "kind": "data",
    }]


def test_failing_script_launch_still_purges_its_tmp(
    script_repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = script_repo.parent / "observed.json"
    ref = _create_script_task(
        script_repo, _RUN_STATE_SCRIPT.format(observed=str(observed), code=3),
    )
    monkeypatch.setattr(launch_module, "spawn_agent_session", _fail("agent spawned"))

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 3, result.output
    seen = json.loads(observed.read_text(encoding="utf-8"))
    assert not Path(seen["tmpdir"]).exists()
    assert list((script_repo / ".coga" / "tmp").iterdir()) == []
    assert Path(seen["task_data"], "keep.txt").is_file()


def test_launch_raising_in_the_agent_phase_still_purges_its_tmp(
    script_repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_script_task(script_repo, "pass\n")
    created: list[Path] = []

    def exploding_repl(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        created.append(Path(env["TMPDIR"]))
        (created[0] / "partial").write_text("x")
        raise RuntimeError("agent crashed")

    _patch_agent_spawn(monkeypatch, exploding_repl)

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code != 0
    assert created and not created[0].exists()
    assert list((script_repo / ".coga" / "tmp").iterdir()) == []


def test_prompt_report_creates_no_run_state(script_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_config(script_repo)
    created = create_task(
        cfg=cfg, title="Report only", workflow_name="direct/body", contexts=[],
        owner="marc", agent="claude", status="active",
    )
    monkeypatch.setattr(launch_module, "_refresh_agent_skills_for_launch", lambda coga_os: None)
    result = CliRunner().invoke(app, ["launch", "--prompt-report", created["slug"]])
    assert result.exit_code == 0, result.output
    assert not (script_repo / ".coga").exists()


def test_read_only_dispatch_gets_tmp_but_no_data_and_never_sweeps(read_only_repo: Path) -> None:
    script = read_only_repo / "bootstrap" / "inspect" / "ticket.py"
    _write(
        script,
        '''
        import json, os, tempfile
        fd, name = tempfile.mkstemp()
        os.close(fd)
        print(json.dumps({
            "tmpdir": os.environ.get("TMPDIR"),
            "data": os.environ.get("COGA_DATA_DIR"),
            "task_data": os.environ.get("COGA_TASK_DATA_DIR"),
            "mkstemp": name,
        }))
        ''',
    )
    crashed = read_only_repo / ".coga" / "tmp" / "aaaaaaaa"
    crashed.mkdir(parents=True)
    (crashed / "left").write_text("x")
    (crashed.parent / "aaaaaaaa.lock").write_text("")
    env = os.environ.copy()
    env.update({"PYTHONPATH": str(_SOURCE_ROOT / "src"), "PATH": "/agents-absent"})
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "launch", "--read-only", "bootstrap/inspect"],
        cwd=read_only_repo, env=env, capture_output=True, check=False, text=True,
    )
    assert result.returncode == 0, result.stderr
    seen = json.loads(result.stdout)
    assert Path(seen["tmpdir"]).parent == (read_only_repo / ".coga" / "tmp").resolve()
    assert Path(seen["mkstemp"]).parent == Path(seen["tmpdir"])
    assert not Path(seen["tmpdir"]).exists()
    assert seen["data"] is None and seen["task_data"] is None
    assert not (read_only_repo / ".coga" / "data").exists()
    assert (crashed / "left").is_file()
