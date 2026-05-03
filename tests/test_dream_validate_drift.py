from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from relay.dream_validate_drift import (
    ACTION_DIRECT_FIX,
    ACTION_HUMAN_NEEDED,
    ACTION_PR_PROPOSAL,
    ValidationFix,
    ValidationIssue,
    build_validate_command,
    classify_issue,
    commit_and_push_fixes,
)


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
    cmd = build_validate_command(fix=True, max_lock_hours=12, idle_hours=48)
    assert cmd[:4] == [sys.executable, "-m", "relay.validate", "--json"]
    assert "--fix" in cmd
    assert "--check-slack" not in cmd
    assert "--max-lock-hours" in cmd
    assert "--idle-hours" in cmd


def test_classifies_stale_lock_as_human_needed() -> None:
    classified = classify_issue(
        ValidationIssue(
            kind="stale-lock",
            task="slow-task",
            message="lock held by 'claude1' for 25.0h",
            severity="warn",
        )
    )

    assert classified.action == ACTION_HUMAN_NEEDED
    assert "do not delete from age alone" in classified.remediation


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

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_validate_drift",
            "--cwd",
            str(tmp_path),
            "--blackboard",
            str(blackboard),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    text = blackboard.read_text()
    assert "## Dream Worker: validate-drift" in text
    assert "`broken-context`: `broken-context` (error)" in text
    assert "PR Proposal" in text
    assert "Command: `" in text


def test_worker_fix_repairs_missing_files_and_posts_summary(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "broken-context"
    (task / "blackboard.md").unlink()
    (task / "log.md").unlink()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_validate_drift",
            "--cwd",
            str(tmp_path),
            "--fix",
            "--blackboard",
            str(task / "blackboard.md"),
            "--slack-task",
            "broken-context",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (task / "blackboard.md").is_file()
    assert (task / "log.md").is_file()
    assert "[slack] disabled" in result.stderr
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
