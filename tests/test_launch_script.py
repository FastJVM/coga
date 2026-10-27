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

from conftest import derived_operator, hold_by_agent, hold_by_owner, seed_direct_body_workflow
from coga import compose as compose_module, git
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


@pytest.fixture(autouse=True)
def _supported_mock_agent_platform(monkeypatch):
    """Agent orchestration uses stubs; platform-boundary cases override this."""
    monkeypatch.setattr(launch_module, "agent_sessions_supported", lambda: True)


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


@pytest.mark.parametrize("native_windows", [False, True])
def test_script_only_launch_is_headless_and_receives_task_contract(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    native_windows: bool,
) -> None:
    monkeypatch.setattr(launch_module, "agent_sessions_supported", lambda: not native_windows)
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
        "_interactive_stdio_has_tty",
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
    monkeypatch.setattr(
        launch_module,
        "_preflight_push_auth",
        _fail("agent push auth checked"),
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
        "_interactive_stdio_has_tty",
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
        "_interactive_stdio_has_tty",
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


def test_script_classification_is_rechecked_after_moving_sync(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = script_repo.parent / "stale-script-ran"
    ref = _create_script_task(
        script_repo,
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
    )
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    assert ref.task_dir is not None
    entry = ref.task_dir / "ticket.py"

    def remove_entry_during_sync(*args, **kwargs):  # type: ignore[no-untyped-def]
        entry.unlink()
        return True

    monkeypatch.setattr(
        "coga.launch_script.git.sync_log",
        remove_entry_during_sync,
    )

    outcome = run_script_chain(
        load_config(script_repo),
        ref,
        ticket,
        set(),
    )

    assert outcome.exit_code == 0
    assert outcome.needs_agent is True
    assert marker.exists() is False
    assert outcome.ticket is not None
    assert outcome.ticket.status == "in_progress"


def test_script_target_deleted_during_sync_stops_cleanly(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = script_repo.parent / "deleted-target-script-ran"
    ref = _create_script_task(
        script_repo,
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
    )
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    assert ref.task_dir is not None

    def delete_target_during_sync(*args, **kwargs):  # type: ignore[no-untyped-def]
        shutil.rmtree(ref.task_dir)
        return True

    monkeypatch.setattr(
        "coga.launch_script.git.sync_log",
        delete_target_during_sync,
    )

    outcome = run_script_chain(
        load_config(script_repo),
        ref,
        ticket,
        set(),
    )

    assert outcome.exit_code == 0
    assert outcome.needs_agent is False
    assert outcome.ticket is None
    assert outcome.stop_reason is not None
    assert "task directory removed" in outcome.stop_reason
    assert marker.exists() is False


@pytest.mark.parametrize(
    ("fresh_state", "expected_status", "expected_role", "reason"),
    [
        ("done", "done", "agent", "task is done"),
        ("human", "in_progress", "owner", "hands off to marc"),
    ],
)
def test_script_does_not_run_after_sync_changes_lifecycle_or_owner(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh_state: str,
    expected_status: str,
    expected_role: str,
    reason: str,
) -> None:
    marker = script_repo.parent / f"stale-{fresh_state}-script-ran"
    ref = _create_script_task(
        script_repo,
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
    )
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)

    def move_state_during_sync(*args, **kwargs):  # type: ignore[no-untyped-def]
        fresh = Ticket.read(ref.ticket_path)
        if fresh_state == "done":
            fresh.frontmatter["status"] = "done"
        else:
            hold_by_owner(fresh)
        fresh.write(ref.ticket_path)
        return True

    monkeypatch.setattr("coga.launch_script.git.sync_log", move_state_during_sync)

    outcome = run_script_chain(
        load_config(script_repo),
        ref,
        ticket,
        set(),
    )

    assert outcome.exit_code == 0
    assert outcome.needs_agent is False
    assert outcome.stop_reason is not None
    assert reason in outcome.stop_reason
    assert marker.exists() is False
    assert outcome.ticket is not None
    assert outcome.ticket.status == expected_status
    assert (outcome.ticket.current_step() or {}).get("assignee") == expected_role


def test_recorded_assist_script_receives_capability_and_publishes_result(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_path = script_repo.parent / "assist-env.json"
    ref = _create_script_task(
        script_repo,
        f"""
        import json
        import os
        from pathlib import Path

        Path({str(observed_path)!r}).write_text(json.dumps({{
            key: os.environ.get(key)
            for key in (
                "COGA_SUPERVISED",
                "COGA_EXPECTED_TASK",
                "COGA_EXPECTED_STEP",
                "COGA_ASSIST_AGENT",
                "COGA_ASSIST_BRANCH",
                "COGA_ASSIST_PR",
            )
        }}))
        """,
    )
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "in_progress"
    hold_by_owner(ticket)
    ticket.write(ref.ticket_path)

    sync_log_calls: list[dict[str, object]] = []
    sync_state_calls: list[dict[str, object]] = []

    def sync_log(*args, **kwargs):  # type: ignore[no-untyped-def]
        sync_log_calls.append(dict(kwargs))
        return True

    def sync_state(*args, **kwargs):  # type: ignore[no-untyped-def]
        sync_state_calls.append(dict(kwargs))

    monkeypatch.setattr("coga.launch_script.git.sync_log", sync_log)
    monkeypatch.setattr("coga.launch_script.git.sync_task_state", sync_state)

    result = run_script_phase(
        load_config(script_repo),
        ref,
        ticket,
        stateless=False,
        assist_branch="feature/review",
        assist_agent="claude",
        assist_pr_url="https://github.com/example/repo/pull/1",
    )

    assert result.exit_code == 0
    observed = json.loads(observed_path.read_text(encoding="utf-8"))
    assert observed == {
        "COGA_SUPERVISED": None,
        "COGA_EXPECTED_TASK": str(ref.path.resolve()),
        "COGA_EXPECTED_STEP": "1 (execute)",
        "COGA_ASSIST_AGENT": "claude",
        "COGA_ASSIST_BRANCH": "feature/review",
        "COGA_ASSIST_PR": "https://github.com/example/repo/pull/1",
    }
    assert sync_log_calls == [{"message": f"Log: {ref.id_slug}"}]
    # The assist's script result is published to control right after exit.
    assert sync_state_calls == [{"message": f"Ticket: {ref.id_slug} — script result"}]


@pytest.mark.parametrize("script_exit", [0, 17], ids=["success", "failure"])
def test_recorded_assist_aligns_before_running_ticket_script(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    script_exit: int,
) -> None:
    ref = _create_script_task(script_repo, "raise AssertionError('not run')\n")
    ticket = Ticket.read(ref.ticket_path)
    hold_by_owner(ticket)
    ticket.write(ref.ticket_path)
    replace_blackboard(
        ref.ticket_path,
        dedent(
            """
            ## Dev
            branch: feature/review
            worktree: /tmp/recorded-review
            pr: https://github.com/example/repo/pull/1
            """
        ),
    )

    events: list[str] = []
    alignment_calls = 0

    def fake_align(cfg, alignment_ticket):  # type: ignore[no-untyped-def]
        nonlocal alignment_calls
        alignment_calls += 1
        events.append(f"align-{alignment_calls}")
        if alignment_calls == 1:
            fresh = Ticket.read(ref.ticket_path)
            fresh.frontmatter["title"] = "Fresh recorded ticket"
            fresh.write(ref.ticket_path)
            return True, "remote-oid"
        return False, "remote-oid"

    def fake_start(cfg, target, current, *, launch_agent):  # type: ignore[no-untyped-def]
        events.append("publish")
        assert launch_agent == "claude"
        current.frontmatter["status"] = "in_progress"
        current.write(target.ticket_path)

    def fake_script_chain(  # type: ignore[no-untyped-def]
        cfg, target, current, ran_steps, **kwargs
    ):
        events.append("script")
        assert current.title == "Fresh recorded ticket"
        assert current.status == "in_progress"
        assert kwargs["assist_branch"] == "feature/review"
        assert kwargs["assist_agent"] == "claude"
        return ScriptChainResult(script_exit, current, False, "script complete")

    monkeypatch.setattr(
        launch_module,
        "_recorded_single_checkout_assist_branch",
        lambda cfg, current: "feature/review",
    )
    monkeypatch.setattr(
        launch_module,
        "_verify_recorded_assist_pr_head",
        lambda *args, **kwargs: "remote-oid",
    )
    monkeypatch.setattr(
        launch_module,
        "_align_recorded_assist_checkout",
        fake_align,
    )
    monkeypatch.setattr(launch_module, "_start_session", fake_start)
    monkeypatch.setattr(
        launch_module,
        "_preflight_push_auth",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(launch_module, "run_script_chain", fake_script_chain)
    monkeypatch.setattr(
        launch_module,
        "_interactive_stdio_has_tty",
        lambda: True,
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_launch_checkout",
        lambda *args, **kwargs: True,
    )

    def launch() -> None:
        launch_module.launch(
            ref.id_slug,
            args=[],
            agent_override="claude",
            prompt_report=False,
            idle_timeout=None,
            max_session=None,
            return_timeout=False,
        )

    if script_exit:
        with pytest.raises(launch_module.LaunchBail) as exc_info:
            launch()
        assert exc_info.value.code == script_exit
    else:
        launch()

    assert events == ["align-1", "align-2", "publish", "script"]


@pytest.mark.parametrize(
    ("script", "expected_exit"),
    [
        ("raise SystemExit(17)\n", 17),
        (
            """
            import os
            from pathlib import Path

            Path(os.environ["COGA_TASK_TICKET"]).write_text(
                "malformed ticket without a blackboard fence\\n"
            )
            raise SystemExit(17)
            """,
            17,
        ),
        (
            """
            import os
            import subprocess
            import sys

            raise SystemExit(subprocess.run([
                sys.executable,
                "-m",
                "coga.cli",
                "mark",
                "done",
                os.environ["COGA_TASK_SLUG"],
            ]).returncode)
            """,
            0,
        ),
        (
            """
            import os
            import subprocess
            import sys

            raise SystemExit(subprocess.run([
                sys.executable,
                "-m",
                "coga.cli",
                "mark",
                "paused",
                os.environ["COGA_TASK_SLUG"],
            ]).returncode)
            """,
            0,
        ),
    ],
    ids=["nonzero", "malformed-nonzero", "done", "paused"],
)
def test_blocked_script_termination_reblocks_unresolved_ask(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    script: str,
    expected_exit: int,
) -> None:
    ref = _create_script_task(script_repo, script)
    blocked = CliRunner().invoke(
        app,
        ["block", "--task", ref.id_slug, "--reason", "which retry ceiling?"],
    )
    assert blocked.exit_code == 0, blocked.output

    monkeypatch.setattr(
        launch_module,
        "_interactive_stdio_has_tty",
        lambda: True,
    )
    monkeypatch.setattr(
        launch_module.shutil, "which", _fail("agent CLI resolved before script")
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        _fail("agent skills refreshed before script"),
    )
    monkeypatch.setattr(
        launch_module,
        "compose_prompt",
        _fail("prompt composed before script"),
    )
    monkeypatch.setattr(
        launch_module,
        "_preflight_push_auth",
        _fail("agent push auth checked before script"),
    )
    monkeypatch.setattr(
        Config,
        "agent_type",
        _fail("agent type resolved before script"),
    )
    monkeypatch.setattr(
        launch_module,
        "spawn_agent_session",
        _fail("agent spawned after script termination"),
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == expected_exit, result.output
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "blocked"
    assert ticket.step == "1 (execute)"
    assert "- [ ]" in read_blackboard(ref.ticket_path)


def test_blocked_script_agent_preflight_failure_reblocks_unresolved_ask(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-step script handoff remains owned until agent setup succeeds."""
    monkeypatch.setattr(launch_module.shutil, "which", lambda cli: f"/stub/{cli}")
    ref = _create_script_task(script_repo, "pass\n")
    blocked = CliRunner().invoke(
        app,
        ["block", "--task", ref.id_slug, "--reason", "which retry ceiling?"],
    )
    assert blocked.exit_code == 0, blocked.output

    monkeypatch.setattr(
        launch_module,
        "_interactive_stdio_has_tty",
        lambda: True,
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        lambda coga_os: (_ for _ in ()).throw(
            RuntimeError("skill preflight failed")
        ),
    )
    monkeypatch.setattr(
        launch_module,
        "spawn_agent_session",
        _fail("agent spawned after failed composition"),
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 1, result.output
    assert "skill preflight failed" in str(result.exception)
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "blocked"
    assert ticket.step == "1 (execute)"
    assert "- [ ]" in read_blackboard(ref.ticket_path)


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


def test_resolved_blocker_does_not_stop_advanced_agent_step(
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
            answer = subprocess.run([
                sys.executable,
                "-m",
                "coga.cli",
                "unblock",
                os.environ["COGA_TASK_SLUG"],
                "--answer",
                "use five retries",
            ])
            if answer.returncode:
                raise SystemExit(answer.returncode)
            raise SystemExit(subprocess.run([
                sys.executable,
                "-m",
                "coga.cli",
                "bump",
                os.environ["COGA_TASK_SLUG"],
            ]).returncode)
        """,
    )
    blocked = CliRunner().invoke(
        app,
        ["block", "--task", ref.id_slug, "--reason", "which retry ceiling?"],
    )
    assert blocked.exit_code == 0, blocked.output

    spawned: list[str] = []

    def fake_spawn(cfg, target, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        spawned.append(agent.name)
        return launch_module.AgentSessionResult(0, "natural")

    monkeypatch.setattr(launch_module, "spawn_agent_session", fake_spawn)
    monkeypatch.setattr(
        launch_module,
        "_interactive_stdio_has_tty",
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
    assert spawned == ["claude"]
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "in_progress"
    assert ticket.step == "2 (finish)"
    assert "- [x]" in read_blackboard(ref.ticket_path)


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
        "_interactive_stdio_has_tty",
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


def test_reblock_restores_the_original_position_not_an_assignment(
    script_repo: Path,
) -> None:
    """Restoring an unanswered resume restores the *routing inputs*.

    A terminal deterministic transition can clear `step:`. Putting the original
    position back is enough: the operator is derived from the frozen role at that
    position, so an unresolved ask can no longer be attributed to whichever agent
    a later step would have used.
    """
    ref = _create_script_task(script_repo, "pass\n")
    append_blocker(ref.ticket_path, "agent:claude", "which retry ceiling?")
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter["step"] = None
    ticket.write(ref.ticket_path)

    reblocked = launch_module._reblock_unresolved_resume(
        load_config(script_repo),
        ref,
        "claude",
        resume_step="1 (execute)",
    )

    assert reblocked is True
    restored = Ticket.read(ref.ticket_path)
    assert restored.status == "blocked"
    assert restored.step == "1 (execute)"
    assert "assignee" not in restored.frontmatter
    assert derived_operator(script_repo, ref.id_slug) == "claude"


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
        "_interactive_stdio_has_tty",
        lambda: True,
    )
    monkeypatch.setattr(
        launch_module,
        "_refresh_agent_skills_for_launch",
        lambda coga_os: None,
    )
    monkeypatch.setattr(
        launch_module,
        "_preflight_push_auth",
        lambda *args, **kwargs: None,
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
        "_interactive_stdio_has_tty",
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
        "_interactive_stdio_has_tty",
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
        "_interactive_stdio_has_tty",
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
            launch_module,
            "_preflight_push_auth",
            _fail("agent push auth checked"),
        )
        monkeypatch.setattr(
            launch_module.shutil,
            "which",
            _fail("agent CLI resolved"),
        )
        monkeypatch.setattr(Config, "agent_type", _fail("agent type resolved"))

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert counter.read_text(encoding="utf-8") == "1"
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == ("blocked" if blocked_resume else "in_progress")
    assert ticket.step == "2 (approve)"
    assert ticket.current_step()["assignee"] == "owner"
    assert "next step hands off to marc" in result.output
    if blocked_resume:
        assert "- [ ]" in read_blackboard(ref.ticket_path)


@pytest.mark.parametrize("unavailable", ["tty", "cli", "human", "windows"])
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
    monkeypatch.setattr(launch_module, "agent_sessions_supported", lambda: unavailable != "windows")
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
        "_interactive_stdio_has_tty",
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
    assert "step 1 (execute)" in result.output
    assert "deterministic work retained" in read_blackboard(ref.ticket_path)
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "in_progress"
    assert ticket.step == "1 (execute)"
    if unavailable == "windows":
        assert launch_module.WINDOWS_AGENT_SESSION_MESSAGE in result.output


def test_windows_prompt_report_allows_an_agent_ticket(script_repo, monkeypatch):
    ref = _create_script_task(script_repo, "raise AssertionError('not a script launch')\n")
    (ref.task_dir / "ticket.py").unlink()
    before = ref.ticket_path.read_bytes()
    monkeypatch.setattr(launch_module, "agent_sessions_supported", lambda: False)
    monkeypatch.setattr(launch_module, "spawn_agent_session", _fail("agent spawned"))

    result = CliRunner().invoke(app, ["launch", ref.id_slug, "--prompt-report"])

    assert result.exit_code == 0, result.output
    assert launch_module.WINDOWS_AGENT_SESSION_MESSAGE not in result.output
    assert ref.ticket_path.read_bytes() == before


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


def test_bootstrap_script_retained_state_exit_skips_refresh_and_sweep(
    script_repo: Path,
) -> None:
    bootstrap = script_repo / "bootstrap" / "retains"
    _write(bootstrap / "ticket.md", "---\ntitle: Retains state\n---\n")
    _write(bootstrap / "ticket.py", "raise SystemExit(75)\n")
    env = os.environ.copy()
    source_path = str(_SOURCE_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        source_path if not existing else source_path + os.pathsep + existing
    )

    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "launch", "bootstrap/retains"],
        cwd=script_repo,
        env=env,
        check=False,
        capture_output=True,
        text=True, encoding="utf-8",
    )

    assert result.returncode == git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.stderr
    assert "Script exited with 75." in result.stderr
    # `cli.main` skips the end-of-command sweep for this exit code itself.
    assert "script ran successfully" not in result.stderr


@pytest.mark.parametrize("switch_to_older_branch", [False, True])
def test_task_script_retained_state_exit_names_its_unpublished_log_line(
    git_repo, monkeypatch: pytest.MonkeyPatch,
    switch_to_older_branch: bool,
) -> None:
    """Without a remote no checkout boundary settles the phase, so the exit
    line was left dirty with no report; the CLI boundary now names it."""
    monkeypatch.chdir(git_repo.coga_os)
    script = "raise SystemExit(75)\n"
    if switch_to_older_branch:
        script = (
            "import subprocess\n"
            "subprocess.run(['git', 'switch', 'older'], check=True)\n"
            + script
        )
    ref = _create_script_task(git_repo.coga_os, script)
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed retaining script task")
    if switch_to_older_branch:
        from coga.logfile import append_log

        git_repo.git("branch", "older")
        cfg = load_config(git_repo.coga_os)
        for index in range(20):
            append_log(cfg, "peer", "system", f"Later control event {index}")
        git_repo.git("add", "coga/log.md")
        git_repo.git("commit", "-m", "advance control log beyond the older branch")
    git_repo.git("remote", "remove", "origin")
    env = os.environ.copy()
    source_path = str(_SOURCE_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        source_path if not existing else source_path + os.pathsep + existing
    )

    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "launch", ref.id_slug],
        cwd=git_repo.coga_os,
        env=env,
        check=False,
        capture_output=True,
        text=True, encoding="utf-8",
    )

    assert result.returncode == git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.stderr
    assert "1 log line(s) are not on control" in result.stderr
    assert (
        f"[{ref.id_slug}] [system] script exited with code 75" in result.stderr
    )
    # The lines launch published itself are on control and are not named.
    assert "launched as a script" not in result.stderr
    assert git_repo.git("status", "--porcelain") == " M coga/log.md\n"


def test_bootstrap_script_retained_state_exit_does_not_refresh_the_checkout(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = script_repo / "bootstrap" / "retains"
    _write(bootstrap / "ticket.md", "---\ntitle: Retains state\n---\n")
    _write(bootstrap / "ticket.py", "raise SystemExit(75)\n")
    refreshes: list[object] = []
    monkeypatch.setattr(
        launch_module, "_refresh_launch_checkout", lambda cfg: refreshes.append(cfg)
    )

    result = CliRunner().invoke(app, ["launch", "bootstrap/retains"])

    assert result.exit_code == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    assert refreshes == []


def test_bootstrap_script_retained_state_exit_skips_between_phase_settlement(
    script_repo: Path,
) -> None:
    bootstrap = script_repo / "bootstrap" / "retains"
    _write(bootstrap / "ticket.md", "---\ntitle: Retains state\n---\n")
    _write(bootstrap / "ticket.py", "raise SystemExit(75)\n")
    cfg = load_config(script_repo)
    ref = resolve_bootstrap(cfg, "retains")
    settled: list[object] = []

    def between_phases(phase_cfg, phase_ref):
        settled.append(phase_ref)
        return phase_cfg, phase_ref

    outcome = run_script_chain(
        cfg, ref, Ticket.read(ref.ticket_path), set(), between_phases=between_phases,
    )

    assert outcome.exit_code == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    assert settled == []


def test_bootstrap_script_ordinary_failure_still_refreshes_the_checkout(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = script_repo / "bootstrap" / "fails"
    _write(bootstrap / "ticket.md", "---\ntitle: Fails\n---\n")
    _write(bootstrap / "ticket.py", "raise SystemExit(3)\n")
    refreshes: list[object] = []
    monkeypatch.setattr(
        launch_module, "_refresh_launch_checkout", lambda cfg: refreshes.append(cfg)
    )

    result = CliRunner().invoke(app, ["launch", "bootstrap/fails"])

    assert result.exit_code == 3
    assert len(refreshes) == 1


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
        monkeypatch.setattr(launch_module, "_interactive_stdio_has_tty", lambda: True)
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


@pytest.mark.parametrize("admission", ["enter", "admit"])
def test_script_chain_preserves_the_pre_phase_contexts_root(git_repo, monkeypatch, admission):
    monkeypatch.chdir(git_repo.coga_os)
    (git_repo.coga_os / "coga.local.toml").write_text(
        'user = "marc"\n[notification.slack]\nenabled = false\n',
        encoding="utf-8", newline="\n",
    )
    seed_direct_body_workflow(git_repo.coga_os)
    ref = _create_script_task(
        git_repo.coga_os,
        """
        from pathlib import Path
        config = Path('coga/coga.toml')
        config.write_text(config.read_text().replace('docs/contexts', 'docs/topics'))
        Path('docs/contexts').rename('docs/topics')
        """,
    )
    old_root = git_repo.root / "docs" / "contexts"
    _write(old_root / "team" / "SKILL.md", "---\nname: team\ndescription: Team.\n---\nKnowledge.\n")
    config = git_repo.coga_os / "coga.toml"
    config.write_text(config.read_text(encoding="utf-8") + '\n[layout]\ncontexts = "docs/contexts"\n', encoding="utf-8", newline="\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed script relocation")
    git_repo.git("push", "origin", "main")
    cfg = load_config(git_repo.coga_os)
    boundary = launch_module._CheckoutBoundary()
    if admission == "enter":
        cfg = boundary.enter(cfg, ref.id_slug)
    else:
        boundary.admit(cfg)
    destination = git_repo.root / "docs" / "topics"

    def between_phases(phase_cfg, phase_ref):
        # Exercise the real script runner's early configuration reload.
        assert phase_cfg.contexts_root == destination
        assert boundary.settle(phase_cfg, subject="script relocation")
        return boundary.reload(phase_cfg, phase_ref)

    outcome = run_script_chain(
        cfg, ref, Ticket.read(ref.ticket_path), set(), between_phases=between_phases,
    )

    assert outcome.exit_code == 0
    assert not boundary.stopped
    assert not git_repo.origin_tracks("docs/contexts/team/SKILL.md")
    assert git_repo.origin_tracks("docs/topics/team/SKILL.md")
    assert git_repo.git("status", "--porcelain").strip() == ""
    assert load_config(git_repo.coga_os).contexts_root == destination
    assert boundary._contexts_root == destination


def test_script_chain_returns_the_checkout_between_real_git_phases(
    git_repo, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    """Each chained ticket.py phase starts from a clean, fresh control checkout."""
    monkeypatch.chdir(git_repo.coga_os)
    (git_repo.coga_os / "coga.local.toml").write_text(
        'user = "marc"\n[notification.slack]\nenabled = false\n',
        encoding="utf-8", newline="\n",
    )
    ref = _create_two_step_script_task(
        git_repo.coga_os,
        """
        import os
        import subprocess
        import sys

        def git(*args):
            return subprocess.run(
                ["git", *args], capture_output=True, text=True, check=True
            ).stdout.strip()

        step = os.environ["COGA_TASK_STEP"]
        sys.stderr.write(f"PHASE {step} ON {git('rev-parse', '--abbrev-ref', 'HEAD')}\\n")
        if step.startswith("1"):
            git("switch", "-c", "feature/script")
        raise SystemExit(subprocess.run([
            sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"],
        ]).returncode)
        """,
    )
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "Seed two-step script task")
    git_repo.git("push", "origin", "main")

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    phases = [line for line in capfd.readouterr().err.splitlines() if line.startswith("PHASE")]
    assert phases == ["PHASE 1 (prepare) ON main", "PHASE 2 (finish) ON main"]
    assert Ticket.read(ref.ticket_path).status == "done"
    assert git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
    assert git_repo.git("status", "--porcelain", "--untracked-files=all") == ""
    assert git_repo.git("rev-parse", "HEAD").strip() == git_repo.git(
        "rev-parse", "main", cwd=git_repo.origin
    ).strip()


@pytest.mark.parametrize("crash", [False, True])
def test_stateful_audit_mutation_survives_child_exit_and_next_command(git_repo, crash):
    """Real script/CLI boundaries cannot sweep an interrupted deletion."""
    from coga import log_transaction
    from coga.logfile import append_log
    cfg = load_config(git_repo.coga_os)
    append_log(cfg, "retired", "system", "archived before mutation")
    script = '''
from coga import git, log_transaction
from coga.config import load_config
from coga.logfile import LogMutation, replace_log
from coga.paths import log_path
cfg=load_config()
root=git.toplevel(cfg.repo_root)
path=log_path(cfg)
git.publish(cfg,[path],"Log: archive before test mutation",require_paths=[path])
raw=path.read_bytes()
base=git.known_control_revision(cfg,root)
mutation=LogMutation(raw,(0,))
log_transaction.begin(cfg,base,mutation,{},"Log: recurring/trim-log — crash fixture")
replace_log(cfg,mutation)
'''
    script += "import os\nos._exit(1)\n" if crash else "raise SystemExit(75)\n"
    ref = _create_script_task(git_repo.coga_os, script)
    git_repo.git("add", "--all")
    git_repo.git("commit", "-m", "seed audit mutation script")
    git_repo.git("push", "origin", "main")
    env = {**os.environ, "PYTHONPATH": str(_SOURCE_ROOT / "src")}
    result = subprocess.run([sys.executable, "-m", "coga.cli", "launch", ref.id_slug],
                            cwd=git_repo.coga_os, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0, result.stdout + result.stderr
    assert log_transaction.pending(cfg)
    assert b"archived before mutation" in git.tree_bytes(git_repo.root, "origin/main", "coga/log.md")
    after = subprocess.run([sys.executable, "-m", "coga.cli", "run", "publish-state"],
                           cwd=git_repo.coga_os, env=env, capture_output=True, text=True, timeout=30)
    assert after.returncode != 0
    assert "pending audit mutation" in after.stdout + after.stderr
    assert b"archived before mutation" in git.tree_bytes(git_repo.root, "origin/main", "coga/log.md")
    assert log_transaction.recover(cfg) == "restored"
    assert b"archived before mutation" in (cfg.repo_root / "log.md").read_bytes()


def test_stateful_pending_audit_exit_75_skips_between_phase_settlement(script_repo, monkeypatch):
    from coga import log_transaction
    ref = _create_script_task(script_repo, "raise SystemExit(75)\n")
    cfg = load_config(script_repo)
    monkeypatch.setattr(log_transaction, "pending", lambda cfg: True)
    outcome = run_script_chain(cfg, ref, Ticket.read(ref.ticket_path), set(),
                               between_phases=lambda *args: pytest.fail("settled pending deletion"))
    assert outcome.exit_code == 75
