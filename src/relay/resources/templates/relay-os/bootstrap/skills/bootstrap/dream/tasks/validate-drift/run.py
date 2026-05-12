#!/usr/bin/env python3
"""Run the validate-drift Dream skill."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from relay.config import Config, ConfigError, find_repo_root, load_config
from relay.slack import post
from relay.tasks import TaskNotFoundError, read_ticket, resolve_task


ACTION_DIRECT_FIX = "direct-fix"
ACTION_PR_PROPOSAL = "pr-proposal"
ACTION_HUMAN_NEEDED = "human-needed"

ACTION_LABELS = {
    ACTION_DIRECT_FIX: "Direct Fix",
    ACTION_PR_PROPOSAL: "PR Proposal",
    ACTION_HUMAN_NEEDED: "Human Needed",
}


@dataclass(frozen=True)
class ValidationIssue:
    kind: str
    task: str
    message: str
    severity: str


@dataclass(frozen=True)
class ValidationFix:
    kind: str
    task: str
    message: str
    path: str


@dataclass(frozen=True)
class ClassifiedIssue:
    issue: ValidationIssue
    action: str
    remediation: str


def build_validate_command(
    *,
    fix: bool = True,
    idle_hours: float | None = None,
    max_blackboard_kb: float | None = None,
) -> list[str]:
    """Return the exact deterministic validation command this skill runs."""
    cmd = [sys.executable, "-m", "relay.validate", "--json"]
    if fix:
        cmd.append("--fix")
    if idle_hours is not None:
        cmd.extend(["--idle-hours", str(idle_hours)])
    if max_blackboard_kb is not None:
        cmd.extend(["--max-blackboard-kb", str(max_blackboard_kb)])
    return cmd


def run_validate_json(
    *,
    cwd: Path | None = None,
    fix: bool = True,
    idle_hours: float | None = None,
    max_blackboard_kb: float | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Run `relay validate --json` and return `(payload, command)`.

    `relay validate` exits 1 when validation errors exist, so 0 and 1 are both
    successful skill inputs. Exit 2 means the validator itself failed.
    """
    cmd = build_validate_command(
        fix=fix,
        idle_hours=idle_hours,
        max_blackboard_kb=max_blackboard_kb,
    )
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(
            f"`{shlex.join(cmd)}` failed with exit {result.returncode}: {detail}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"`{shlex.join(cmd)}` did not emit valid JSON: {exc}"
        ) from exc
    return payload, cmd


def parse_fixes(payload: dict[str, Any]) -> list[ValidationFix]:
    fixes: list[ValidationFix] = []
    for raw in payload.get("fixes", []):
        if not isinstance(raw, dict):
            continue
        fixes.append(
            ValidationFix(
                kind=str(raw.get("kind", "unknown")),
                task=str(raw.get("task", "(unknown)")),
                message=str(raw.get("message", "")),
                path=str(raw.get("path", "")),
            )
        )
    return fixes


def parse_issues(payload: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for raw in payload.get("issues", []):
        if not isinstance(raw, dict):
            continue
        issues.append(
            ValidationIssue(
                kind=str(raw.get("kind", "unknown")),
                task=str(raw.get("task", "(unknown)")),
                message=str(raw.get("message", "")),
                severity=str(raw.get("severity", "warn")),
            )
        )
    return issues


def classify_issue(issue: ValidationIssue) -> ClassifiedIssue:
    """Classify one validator issue into Dream's remediation buckets."""
    kind = issue.kind
    message = issue.message

    if kind == "missing-file":
        if "blackboard.md" in message:
            return ClassifiedIssue(
                issue=issue,
                action=ACTION_DIRECT_FIX,
                remediation=(
                    "Create a minimal `blackboard.md` for the task in a small "
                    "Dream PR. This restores the recovery surface without "
                    "changing task state."
                ),
            )
        if "log.md" in message:
            return ClassifiedIssue(
                issue=issue,
                action=ACTION_DIRECT_FIX,
                remediation=(
                    "Create an empty `log.md` in a small Dream PR. Do not "
                    "synthesize history; future Relay commands will append "
                    "real log entries."
                ),
            )
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "`ticket.md` is the source of truth. Do not recreate it from "
                "inference; ask the owner whether to restore from git history "
                "or delete the task dir."
            ),
        )

    if kind in {"broken-context", "broken-skill"}:
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_PR_PROPOSAL,
            remediation=(
                "Open a small PR after reading the task: either fix the typo in "
                "the reference or add the missing context/skill with reviewable "
                "content."
            ),
        )

    if kind == "large-blackboard":
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_PR_PROPOSAL,
            remediation=(
                "Propose a reviewed blackboard condensation that preserves "
                "current decisions and blockers before removing detail."
            ),
        )

    if kind == "stuck-active":
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "Ask the owner whether the task should be relaunched, panicked, "
                "paused, or bumped. The skill should not change lifecycle state "
                "silently."
            ),
        )

    if kind in {"invalid-status", "unknown-assignee", "unfrozen-workflow"}:
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "Needs an owner decision because the correction changes task "
                "routing, workflow state, or who is expected to act next."
            ),
        )

    if kind.startswith("slack-"):
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "Slack configuration or network state needs a human with "
                "environment access; do not edit secrets or machine-local config "
                "from Dream."
            ),
        )

    return ClassifiedIssue(
        issue=issue,
        action=ACTION_HUMAN_NEEDED,
        remediation="Unknown validator issue kind. Ask a human before changing repo state.",
    )


def classify_issues(issues: list[ValidationIssue]) -> list[ClassifiedIssue]:
    return [classify_issue(issue) for issue in issues]


def render_blackboard_report(
    classified: list[ClassifiedIssue],
    *,
    fixes: list[ValidationFix] | None = None,
    generated_at: str,
    command: list[str],
    task_slug: str | None = None,
    git_result: str | None = None,
) -> str:
    fixes = fixes or []
    counts = {
        action: sum(1 for item in classified if item.action == action)
        for action in ACTION_LABELS
    }
    total = len(classified)

    lines = [
        "## Dream Skill: validate-drift",
        "",
        f"Generated: {generated_at}",
        f"Command: `{shlex.join(command)}`",
    ]
    if task_slug:
        lines.append(f"Task: `{task_slug}`")
    lines.append("")

    if fixes:
        lines.append(f"Applied fixes: {len(fixes)}.")
        lines.append("")
        for fix_item in fixes:
            lines.append(
                f"- `{fix_item.task}`: `{fix_item.kind}` - {fix_item.message} "
                f"(`{fix_item.path}`)"
            )
        lines.append("")
    if git_result:
        lines.append(f"Git: {git_result}")
        lines.append("")
    if total == 0:
        lines.append("Result: no remaining validation drift found.")
        return "\n".join(lines) + "\n"

    lines.append(
        "Result: "
        f"{total} issue(s): "
        f"{counts[ACTION_DIRECT_FIX]} direct fix, "
        f"{counts[ACTION_PR_PROPOSAL]} PR proposal, "
        f"{counts[ACTION_HUMAN_NEEDED]} human-needed."
    )
    lines.append("")

    for action, label in ACTION_LABELS.items():
        bucket = [item for item in classified if item.action == action]
        if not bucket:
            continue
        lines.append(f"### {label}")
        lines.append("")
        for item in bucket:
            issue = item.issue
            lines.append(
                f"- `{issue.task}`: `{issue.kind}` ({issue.severity}) - {issue.message}"
            )
            lines.append(f"  Remediation: {item.remediation}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def append_report(blackboard: Path, report: str) -> None:
    if not blackboard.parent.is_dir():
        raise RuntimeError(f"Blackboard parent does not exist: {blackboard.parent}")
    existing = blackboard.read_text() if blackboard.is_file() else ""
    if not existing or existing.endswith("\n\n"):
        separator = ""
    elif existing.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    blackboard.write_text(existing + separator + report)


def build_slack_summary(
    fixes: list[ValidationFix],
    classified: list[ClassifiedIssue],
    *,
    git_result: str | None = None,
) -> str:
    direct = sum(1 for item in classified if item.action == ACTION_DIRECT_FIX)
    proposals = sum(1 for item in classified if item.action == ACTION_PR_PROPOSAL)
    human = sum(1 for item in classified if item.action == ACTION_HUMAN_NEEDED)
    parts: list[str] = []
    if fixes:
        parts.append(f"fixed {len(fixes)}")
    if classified:
        parts.append(
            f"{len(classified)} remaining "
            f"({direct} direct, {proposals} proposal, {human} human-needed)"
        )
    else:
        parts.append("no remaining validation drift")
    if git_result:
        parts.append(git_result)
    return "Dream validate-drift: " + "; ".join(parts)


def post_slack_summary(cfg: Config, task_slug: str, summary: str) -> None:
    try:
        ref = resolve_task(cfg, task_slug)
    except TaskNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc
    ticket = read_ticket(ref)
    post(cfg, f"Dream: {summary}", task_path=ref.path, owner=ticket.owner or cfg.current_user)


def infer_task_slug_from_blackboard(cfg: Config, blackboard: Path | None) -> str | None:
    if blackboard is None:
        return None
    try:
        rel = blackboard.resolve().relative_to((cfg.repo_root / "tasks").resolve())
    except ValueError:
        return None
    if len(rel.parts) == 2 and rel.parts[1] == "blackboard.md":
        return rel.parts[0]
    return None


def load_worker_config(cwd: Path | None) -> Config:
    if cwd is None:
        return load_config()
    return load_config(find_repo_root(cwd))


def commit_and_push_fixes(
    *,
    cwd: Path,
    fixes: list[ValidationFix],
    message: str,
    allow_main_push: bool = False,
) -> str | None:
    if not fixes:
        return None

    git_root = Path(_run_git(["rev-parse", "--show-toplevel"], cwd=cwd).strip())
    branch = _run_git(["branch", "--show-current"], cwd=git_root).strip()
    if not branch:
        raise RuntimeError("refusing to commit validation fixes from detached HEAD")
    if branch in {"main", "master"} and not allow_main_push:
        raise RuntimeError(
            "refusing to push validation fixes directly from main; "
            "create a Dream repair branch or pass --allow-main-push"
        )

    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=git_root)
    if staged.returncode not in (0, 1):
        raise RuntimeError("could not inspect staged git changes")
    if staged.returncode == 1:
        raise RuntimeError("refusing to commit with pre-existing staged changes")

    rel_paths: list[str] = []
    for fix_item in fixes:
        path = Path(fix_item.path)
        if not path.is_absolute():
            path = cwd / path
        try:
            rel_paths.append(str(path.resolve().relative_to(git_root.resolve())))
        except ValueError as exc:
            raise RuntimeError(f"fix path is outside git root: {path}") from exc

    _run_git(["add", *rel_paths], cwd=git_root)
    _run_git(["commit", "-m", message], cwd=git_root)

    upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=git_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if upstream.returncode == 0:
        _run_git(["push"], cwd=git_root)
    else:
        _run_git(["push", "-u", "origin", "HEAD"], cwd=git_root)
    return f"committed and pushed `{branch}`"


def _run_git(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"`git {shlex.join(args)}` failed: {detail}")
    return result.stdout


def script_blackboard_from_env() -> Path | None:
    value = os.environ.get("RELAY_TASK_BLACKBOARD")
    return Path(value) if value else None


def script_task_slug_from_env() -> str | None:
    return os.environ.get("RELAY_TASK_SLUG")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the validate-drift Dream skill.")
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Run validation from this repo directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--no-fix",
        action="store_true",
        help="Disable the default conservative `relay validate --fix` repair pass.",
    )
    parser.add_argument(
        "--post-slack",
        action="store_true",
        help="Post the skill summary to Slack against RELAY_TASK_SLUG.",
    )
    parser.add_argument(
        "--commit-and-push",
        action="store_true",
        help="Commit repaired files and push the current non-main branch.",
    )
    parser.add_argument(
        "--allow-main-push",
        action="store_true",
        help="Allow --commit-and-push while on main/master.",
    )
    parser.add_argument(
        "--commit-message",
        default="Dream: repair validation drift",
        help="Commit subject used with --commit-and-push.",
    )
    parser.add_argument("--idle-hours", type=float)
    parser.add_argument("--max-blackboard-kb", type=float)
    args = parser.parse_args(argv)

    blackboard = script_blackboard_from_env()
    task_slug = script_task_slug_from_env()
    fix = not args.no_fix

    try:
        payload, command = run_validate_json(
            cwd=args.cwd,
            fix=fix,
            idle_hours=args.idle_hours,
            max_blackboard_kb=args.max_blackboard_kb,
        )
        fixes = parse_fixes(payload)
        classified = classify_issues(parse_issues(payload))
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        git_result = None
        if args.commit_and_push:
            if not fix:
                raise RuntimeError("--commit-and-push requires the fix pass")
            git_result = commit_and_push_fixes(
                cwd=args.cwd or Path.cwd(),
                fixes=fixes,
                message=args.commit_message,
                allow_main_push=args.allow_main_push,
            )
        report = render_blackboard_report(
            classified,
            fixes=fixes,
            generated_at=generated_at,
            command=command,
            task_slug=task_slug,
            git_result=git_result,
        )
        if blackboard:
            append_report(blackboard, report)
        else:
            sys.stdout.write(report)
        if args.post_slack:
            cfg = load_worker_config(args.cwd)
            slack_task = task_slug or infer_task_slug_from_blackboard(cfg, blackboard)
            if slack_task:
                post_slack_summary(
                    cfg,
                    slack_task,
                    build_slack_summary(fixes, classified, git_result=git_result),
                )
    except (ConfigError, RuntimeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
