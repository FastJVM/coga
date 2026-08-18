from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from conftest import seed_direct_body_workflow
from coga import compose as compose_module
from coga.cli import app
from coga.commands import launch as launch_module
from coga.config import Config, load_config
from coga.create import create_task
from coga.launch_script import script_entry_point
from coga.repl_supervisor import ReplOutcome
from coga.taskfile import read_blackboard
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
            "COGA_TASK_LOG",
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
        "COGA_TASK_LOG": str((script_repo / "log.md").resolve()),
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
    assert kwargs["fatal"] is False


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
