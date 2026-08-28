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

from conftest import seed_direct_body_workflow
from coga import compose as compose_module, git
from coga.blackboard import append_blocker
from coga.cli import app
from coga.commands import launch as launch_module
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
from coga.tasks import TaskRef, resolve_task
from coga.ticket import Ticket


_SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


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
        assignee="claude",
        watchers=[],
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
        human="marc",
        agent="claude",
        assignee="claude",
        watchers=[],
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
        assignee="claude",
        watchers=[],
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
) -> None:
    observed_path = script_repo.parent / "observed.json"
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
    observed = json.loads(observed_path.read_text())
    assert observed["argv"] == []
    assert observed["cwd"] == str(script_repo.parent.resolve())
    assert observed["env"] == {
        "COGA_TASK_SLUG": ref.id_slug,
        "COGA_TASK_DIR": str(ref.path.resolve()),
        "COGA_TASK_TICKET": str(ref.ticket_path.resolve()),
        "COGA_TASK_BLACKBOARD": str(ref.ticket_path.resolve()),
        "COGA_TASK_STEP": "1 (execute)",
        "COGA_COGA_OS_ROOT": str(script_repo.resolve()),
        "COGA_REPO_ROOT": str(script_repo.parent.resolve()),
        "SCRIPT_TOKEN": "resolved-secret",
    }
    assert observed["supervised"] == {
        "COGA_SUPERVISED": None,
        "COGA_EXPECTED_TASK": None,
        "COGA_EXPECTED_STEP": None,
    }
    task_log = (script_repo / "log.md").read_text()
    assert task_log.count("task done") == 1


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

    assert kind == "script"
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
    assert "script exited with code 17" in (script_repo / "log.md").read_text()
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
    assert "script exited with code 17" in (script_repo / "log.md").read_text()
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
    ("fresh_state", "expected_status", "expected_assignee", "reason"),
    [
        ("done", "done", "claude", "task is done"),
        ("human", "in_progress", "marc", "hands off to marc"),
    ],
)
def test_script_does_not_run_after_sync_changes_lifecycle_or_owner(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh_state: str,
    expected_status: str,
    expected_assignee: str,
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
            fresh.frontmatter["assignee"] = "marc"
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
    assert outcome.ticket.assignee == expected_assignee


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
    ticket.frontmatter["assignee"] = "marc"
    ticket.write(ref.ticket_path)

    sync_log_calls: list[dict[str, object]] = []
    sync_state_calls: list[dict[str, object]] = []
    guard_oids: list[str] = []

    def sync_log(*args, **kwargs):  # type: ignore[no-untyped-def]
        sync_log_calls.append(dict(kwargs))
        return True

    def sync_state(*args, **kwargs):  # type: ignore[no-untyped-def]
        sync_state_calls.append(dict(kwargs))

    monkeypatch.setattr("coga.launch_script.git.sync_log", sync_log)
    monkeypatch.setattr("coga.launch_script.git.sync_task_state", sync_state)
    monkeypatch.setattr(
        "coga.launch_script.git.feature_publication_lease",
        lambda *args, **kwargs: git.FeaturePublicationLease(
            branch="feature/review",
            local_oid="published-oid",
            remote_oid="published-oid",
        ),
    )

    result = run_script_phase(
        load_config(script_repo),
        ref,
        ticket,
        stateless=False,
        publish_aligned_branch="feature/review",
        assist_agent="claude",
        assist_pr_url="https://github.com/example/repo/pull/1",
        feature_publication_guard=guard_oids.append,
    )

    assert result.exit_code == 0
    observed = json.loads(observed_path.read_text())
    assert observed == {
        "COGA_SUPERVISED": None,
        "COGA_EXPECTED_TASK": str(ref.path.resolve()),
        "COGA_EXPECTED_STEP": "1 (execute)",
        "COGA_ASSIST_AGENT": "claude",
        "COGA_ASSIST_BRANCH": "feature/review",
        "COGA_ASSIST_PR": "https://github.com/example/repo/pull/1",
    }
    assert sync_log_calls == [
        {
            "message": f"Log: {ref.id_slug}",
            "publish_if_remote_aligned": True,
            "expected_feature_branch": "feature/review",
            "allow_feature_fast_forward": False,
            "feature_publication_guard": guard_oids.append,
        }
    ]
    assert guard_oids == ["published-oid", "published-oid"]
    assert len(sync_state_calls) == 1
    publication = sync_state_calls[0]["feature_publication"]
    assert isinstance(publication, git.FeaturePublicationLease)
    assert publication.remote_oid == "published-oid"
    generated = sync_state_calls[0]["generated_paths"]
    assert isinstance(generated, dict)
    assert ref.ticket_path in generated
    assert ref.task_dir / "ticket.py" in generated
    assert script_repo / "log.md" in generated


@pytest.mark.parametrize("script_exit", [0, 17], ids=["success", "failure"])
def test_recorded_assist_aligns_before_running_ticket_script(
    script_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    script_exit: int,
) -> None:
    ref = _create_script_task(script_repo, "raise AssertionError('not run')\n")
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["assignee"] = "marc"
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

    def fake_publish(cfg, target, **kwargs):  # type: ignore[no-untyped-def]
        events.append("publish")
        current = Ticket.read(target.ticket_path)
        current.frontmatter["status"] = "in_progress"
        current.write(target.ticket_path)

    def fake_script_chain(  # type: ignore[no-untyped-def]
        cfg, target, current, ran_steps, **kwargs
    ):
        events.append("script")
        assert current.title == "Fresh recorded ticket"
        assert current.status == "in_progress"
        assert kwargs["publish_aligned_branch"] == "feature/review"
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
    monkeypatch.setattr(
        launch_module,
        "_publish_assist_lifecycle_before_spawn",
        fake_publish,
    )
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
        with pytest.raises(SystemExit) as exc_info:
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
    assert ticket.assignee == "claude"


def test_reblock_restores_original_assignee_with_terminal_step(
    script_repo: Path,
) -> None:
    ref = _create_script_task(script_repo, "pass\n")
    append_blocker(ref.ticket_path, "agent:claude", "which retry ceiling?")
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter["step"] = None
    ticket.frontmatter["assignee"] = "codex"
    ticket.write(ref.ticket_path)

    reblocked = launch_module._reblock_unresolved_resume(
        load_config(script_repo),
        ref,
        "claude",
        resume_step="1 (execute)",
        resume_assignee="claude",
    )

    assert reblocked is True
    restored = Ticket.read(ref.ticket_path)
    assert restored.status == "blocked"
    assert restored.step == "1 (execute)"
    assert restored.assignee == "claude"


def test_reblock_refuses_to_misroute_an_originally_unassigned_step(
    script_repo: Path,
) -> None:
    ref = _create_script_task(script_repo, "pass\n")
    append_blocker(ref.ticket_path, "agent:claude", "which retry ceiling?")
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter["step"] = None
    ticket.frontmatter["assignee"] = "codex"
    ticket.write(ref.ticket_path)

    with pytest.raises(
        launch_module._AssistPublicationRefused,
        match="original resumed step had no valid assignee",
    ):
        launch_module._reblock_unresolved_resume(
            load_config(script_repo),
            ref,
            "claude",
            resume_step="1 (execute)",
            resume_assignee=None,
        )

    retained = Ticket.read(ref.ticket_path)
    assert retained.status == "done"
    assert retained.assignee == "codex"


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
            ticket.read_text().replace(
                "assignee: claude",
                "assignee: reviewer",
                1,
            )
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
    assert spawned == ["reviewer"]
    assert Ticket.read(ref.ticket_path).assignee == "reviewer"


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
        assignee="claude",
        watchers=[],
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
    assert counter.read_text() == "1"
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == ("blocked" if blocked_resume else "in_progress")
    assert ticket.step == "2 (approve)"
    assert ticket.assignee == "marc"
    assert "next step hands off to marc" in result.output
    if blocked_resume:
        assert "- [ ]" in read_blackboard(ref.ticket_path)


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
        ticket.frontmatter["assignee"] = "marc"
        ticket.write(ref.ticket_path)

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


def test_bootstrap_script_is_stateless_and_keeps_stdout_machine_readable(
    script_repo: Path,
) -> None:
    bootstrap = script_repo / "bootstrap" / "deterministic"
    _write(
        bootstrap / "ticket.md",
        """
        ---
        title: Deterministic command
        assignee: claude
        skills: []
        secrets: null
        ---

        ## Description

        Print one machine-readable value.
        """,
    )
    _write(
        bootstrap / "ticket.py",
        """
        import os
        import sys

        assert sys.argv[1:] == []
        assert os.environ["COGA_TASK_SLUG"] == "bootstrap/deterministic"
        assert "COGA_TASK_BLACKBOARD" not in os.environ
        assert "COGA_TASK_STEP" not in os.environ
        print("machine-value")
        """,
    )
    env = os.environ.copy()
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
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "machine-value\n"
    assert "Launch: task bootstrap/deterministic" in result.stderr
    assert "bootstrap/deterministic: script ran successfully" in result.stderr
    assert not (script_repo / "log.md").exists()
