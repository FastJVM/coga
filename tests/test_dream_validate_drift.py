from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

VALIDATE_DRIFT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "bootstrap"
    / "skills"
    / "bootstrap"
    / "dream"
    / "tasks"
    / "validate-drift"
)


def _load_validate_drift_module():
    spec = importlib.util.spec_from_file_location(
        "validate_drift_skill", VALIDATE_DRIFT / "run.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validate_drift = _load_validate_drift_module()

ACTION_DIRECT_FIX = validate_drift.ACTION_DIRECT_FIX
ACTION_PR_PROPOSAL = validate_drift.ACTION_PR_PROPOSAL
ValidationFix = validate_drift.ValidationFix
ValidationIssue = validate_drift.ValidationIssue
build_validate_command = validate_drift.build_validate_command
classify_issue = validate_drift.classify_issue
commit_and_push_fixes = validate_drift.commit_and_push_fixes


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _seed_repo(root: Path) -> Path:
    relay_os = root / "relay-os"
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"

        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(relay_os / "relay.local.toml", 'user = "marc"\n')
    task = relay_os / "tasks" / "broken-context"
    _write(
        task / "ticket.md",
        """
        ---
        title: Broken Context
        status: active
        mode: interactive
        owner: marc
        assignee: claude1
        contexts:
          - missing/context
        ---

        ## Description

        Exercise validate-drift.
        """,
    )
    _write(task / "blackboard.md", "Initial blackboard.\n")
    _write(task / "log.md", "")
    return relay_os


def test_build_validate_command_uses_deterministic_json_surface() -> None:
    cmd = build_validate_command(fix=True, idle_hours=48)
    assert cmd[:4] == [sys.executable, "-m", "relay.validate", "--json"]
    assert "--fix" in cmd
    assert "--check-slack" not in cmd
    assert "--idle-hours" in cmd


def test_classifies_missing_log_as_direct_fix() -> None:
    classified = classify_issue(
        ValidationIssue(
            kind="missing-file",
            task="broken-task",
            message="missing log.md",
            severity="error",
        )
    )

    assert classified.action == ACTION_DIRECT_FIX
    assert "empty `log.md`" in classified.remediation


def test_classifies_broken_refs_as_pr_proposal() -> None:
    classified = classify_issue(
        ValidationIssue(
            kind="broken-context",
            task="broken-task",
            message="context 'missing/context' does not exist",
            severity="error",
        )
    )

    assert classified.action == ACTION_PR_PROPOSAL
    assert "Open a small PR" in classified.remediation


def test_worker_appends_validate_result_to_blackboard(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    blackboard = relay_os / "tasks" / "broken-context" / "blackboard.md"
    env = os.environ.copy()
    env.update(
        {
            "RELAY_TASK_SLUG": "validate-drift-child",
            "RELAY_TASK_DIR": str((relay_os / "tasks" / "broken-context").resolve()),
            "RELAY_TASK_BLACKBOARD": str(blackboard.resolve()),
            "RELAY_RELAY_OS_ROOT": str(relay_os.resolve()),
            "RELAY_REPO_ROOT": str(tmp_path.resolve()),
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATE_DRIFT / "run.py"),
            "--cwd",
            str(tmp_path),
            "--no-fix",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    text = blackboard.read_text()
    assert "## Dream Skill: validate-drift" in text
    assert "Task: `validate-drift-child`" in text
    assert "`broken-context`: `broken-context` (error)" in text
    assert "PR Proposal" in text
    assert "Command: `" in text


def test_worker_fix_repairs_missing_files_and_posts_summary(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "broken-context"
    (task / "blackboard.md").unlink()
    (task / "log.md").unlink()
    env = os.environ.copy()
    env.update(
        {
            "RELAY_TASK_SLUG": "validate-drift-child",
            "RELAY_TASK_DIR": str(task.resolve()),
            "RELAY_TASK_BLACKBOARD": str((task / "blackboard.md").resolve()),
            "RELAY_RELAY_OS_ROOT": str(relay_os.resolve()),
            "RELAY_REPO_ROOT": str(tmp_path.resolve()),
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATE_DRIFT / "run.py"),
            "--cwd",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (task / "blackboard.md").is_file()
    assert (task / "log.md").is_file()
    text = (task / "blackboard.md").read_text()
    assert "Applied fixes: 2." in text
    assert "created blackboard.md" in text
    assert "created log.md" in text
    assert "PR Proposal" in text


def test_commit_and_push_refuses_main_branch(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    fixed = tmp_path / "relay-os" / "tasks" / "x" / "log.md"
    fixed.parent.mkdir(parents=True)
    fixed.write_text("")

    with pytest.raises(RuntimeError, match="refusing to push validation fixes directly"):
        commit_and_push_fixes(
            cwd=tmp_path,
            fixes=[
                ValidationFix(
                    kind="missing-file",
                    task="x",
                    message="created log.md",
                    path=str(fixed),
                )
            ],
            message="Dream: repair validation drift",
        )
