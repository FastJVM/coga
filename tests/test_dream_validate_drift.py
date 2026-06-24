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
ACTION_HUMAN_NEEDED = validate_drift.ACTION_HUMAN_NEEDED
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
        auto = "-p"
        file = "CLAUDE.md"

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
        assignee: claude
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


def test_classifies_blackboard_fence_as_direct_fix() -> None:
    # v2 single-file: the auto-fixable issue is a missing blackboard fence,
    # which `relay validate --fix` appends to ticket.md. (There is no per-task
    # log.md / blackboard.md to recreate anymore.)
    classified = classify_issue(
        ValidationIssue(
            kind="blackboard-fence",
            task="broken-task",
            message="ticket.md must contain exactly one blackboard fence",
            severity="error",
        )
    )

    assert classified.action == ACTION_DIRECT_FIX
    assert "relay validate --fix" in classified.remediation


def test_classifies_missing_ticket_as_human_needed() -> None:
    # The only required per-task file is ticket.md — never recreated from
    # inference, so a missing one is human-needed.
    classified = classify_issue(
        ValidationIssue(
            kind="missing-file",
            task="broken-task",
            message="missing ticket.md",
            severity="error",
        )
    )

    assert classified.action == validate_drift.ACTION_HUMAN_NEEDED
    assert "`ticket.md` is the source of truth" in classified.remediation


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


def test_classifies_recurring_state_stuck_as_human_needed() -> None:
    classified = classify_issue(
        ValidationIssue(
            kind="recurring-state-stuck",
            task="dev-update-2026-06-07",
            message="finished without advancing declared state key(s) last_commit",
            severity="warn",
        )
    )

    assert classified.action == ACTION_HUMAN_NEEDED
    assert "parent recurring blackboard" in classified.remediation


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
    from relay.taskfile import fence_count

    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "broken-context"
    # Single-file format: the deterministic drift `--fix` repairs is a ticket.md
    # missing its blackboard fence (there is no separate blackboard.md/log.md to
    # recreate). `_seed_repo` writes the body with no fence, so the fix adds one.
    assert fence_count((task / "ticket.md").read_text()) == 0
    report = task / "report.md"
    env = os.environ.copy()
    env.update(
        {
            "RELAY_TASK_SLUG": "validate-drift-child",
            "RELAY_TASK_DIR": str(task.resolve()),
            "RELAY_TASK_BLACKBOARD": str(report.resolve()),
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
    # The fix landed in the repo: ticket.md now carries exactly one fence.
    assert fence_count((task / "ticket.md").read_text()) == 1
    text = report.read_text()
    assert "Applied fixes: 1." in text
    assert "added blackboard fence + region" in text
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


def test_commit_and_push_uses_configured_remote_without_upstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = tmp_path / "relay-os" / "tasks" / "x" / "log.md"
    fixed.parent.mkdir(parents=True)
    fixed.write_text("")
    commands: list[list[str]] = []

    def fake_run_git(args, *, cwd):
        command = ["git", *args]
        commands.append(command)
        if args == ["rev-parse", "--show-toplevel"]:
            return f"{tmp_path}\n"
        if args == ["branch", "--show-current"]:
            return "repair-branch\n"
        return ""

    def fake_run(args, **kwargs):
        command = list(args)
        commands.append(command)
        if command == ["git", "diff", "--cached", "--quiet"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command == [
            "git",
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{u}",
        ]:
            return subprocess.CompletedProcess(
                command, 128, stdout="", stderr="no upstream"
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_drift, "_run_git", fake_run_git)
    monkeypatch.setattr(validate_drift.subprocess, "run", fake_run)

    result = commit_and_push_fixes(
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
        remote="upstream",
    )

    assert result == "committed and pushed `repair-branch`"
    assert ["git", "push", "-u", "upstream", "HEAD"] in commands
    assert not any(
        command[:1] == ["git"] and "origin" in command for command in commands
    )


def test_commit_and_push_main_passes_configured_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    class Cfg:
        git_remote = "upstream"

    def fake_run_validate_json(**kwargs):
        return (
            {
                "fixes": [
                    {
                        "kind": "missing-file",
                        "task": "x",
                        "message": "created log.md",
                        "path": "relay-os/tasks/x/log.md",
                    }
                ],
                "issues": [],
            },
            ["relay", "validate", "--json", "--fix"],
        )

    def fake_commit_and_push_fixes(**kwargs):
        captured.update(kwargs)
        return "committed and pushed `repair-branch`"

    monkeypatch.setattr(validate_drift, "run_validate_json", fake_run_validate_json)
    monkeypatch.setattr(validate_drift, "load_worker_config", lambda cwd: Cfg())
    monkeypatch.setattr(
        validate_drift, "commit_and_push_fixes", fake_commit_and_push_fixes
    )

    result = validate_drift.main(["--cwd", str(tmp_path), "--commit-and-push"])

    assert result == 0
    assert captured["remote"] == "upstream"
