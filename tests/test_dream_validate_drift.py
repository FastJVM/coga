from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from relay.dream_validate_drift import (
    ACTION_DIRECT_FIX,
    ACTION_HUMAN_NEEDED,
    ACTION_PR_PROPOSAL,
    ValidationIssue,
    build_validate_command,
    classify_issue,
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
    cmd = build_validate_command(max_lock_hours=12, idle_hours=48)
    assert cmd[:4] == [sys.executable, "-m", "relay.validate", "--json"]
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
