"""Validate-drift Dream worker.

The worker keeps `relay validate --json` as the deterministic source of truth
and adds Dream-specific classification/reporting around that JSON.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
class ClassifiedIssue:
    issue: ValidationIssue
    action: str
    remediation: str


def build_validate_command(
    *,
    max_lock_hours: float | None = None,
    idle_hours: float | None = None,
    max_blackboard_kb: float | None = None,
) -> list[str]:
    """Return the exact deterministic validation command this worker runs."""
    cmd = [sys.executable, "-m", "relay.validate", "--json"]
    if max_lock_hours is not None:
        cmd.extend(["--max-lock-hours", str(max_lock_hours)])
    if idle_hours is not None:
        cmd.extend(["--idle-hours", str(idle_hours)])
    if max_blackboard_kb is not None:
        cmd.extend(["--max-blackboard-kb", str(max_blackboard_kb)])
    return cmd


def run_validate_json(
    *,
    cwd: Path | None = None,
    max_lock_hours: float | None = None,
    idle_hours: float | None = None,
    max_blackboard_kb: float | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Run `relay validate --json` and return `(payload, command)`.

    `relay validate` exits 1 when validation errors exist, so 0 and 1 are both
    successful worker inputs. Exit 2 means the validator itself failed.
    """
    cmd = build_validate_command(
        max_lock_hours=max_lock_hours,
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
                    "Create a minimal `blackboard.md` for the task in a small Dream PR. "
                    "This restores the recovery surface without changing task state."
                ),
            )
        if "log.md" in message:
            return ClassifiedIssue(
                issue=issue,
                action=ACTION_DIRECT_FIX,
                remediation=(
                    "Create an empty `log.md` in a small Dream PR. Do not synthesize "
                    "history; future Relay commands will append real log entries."
                ),
            )
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "`ticket.md` is the source of truth. Do not recreate it from inference; "
                "ask the owner whether to restore from git history or delete the task dir."
            ),
        )

    if kind in {"broken-context", "broken-skill"}:
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_PR_PROPOSAL,
            remediation=(
                "Open a small PR after reading the task: either fix the typo in the "
                "reference or add the missing context/skill with reviewable content."
            ),
        )

    if kind == "large-blackboard":
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_PR_PROPOSAL,
            remediation=(
                "Propose a reviewed blackboard condensation that preserves current "
                "decisions and blockers before removing detail."
            ),
        )

    if kind == "stale-lock":
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "Conservative stale-lock rule: do not delete from age alone. A human "
                "must verify there is no live worker/terminal for this task, then remove "
                "`task.lock` or relaunch with `--force`."
            ),
        )

    if kind == "stuck-active":
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "Ask the owner whether the task should be relaunched, panicked, paused, "
                "or bumped. The worker should not change lifecycle state silently."
            ),
        )

    if kind in {"invalid-status", "unknown-assignee", "unfrozen-workflow"}:
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "Needs an owner decision because the correction changes task routing, "
                "workflow state, or who is expected to act next."
            ),
        )

    if kind.startswith("slack-"):
        return ClassifiedIssue(
            issue=issue,
            action=ACTION_HUMAN_NEEDED,
            remediation=(
                "Slack configuration or network state needs a human with environment "
                "access; do not edit secrets or machine-local config from Dream."
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
    generated_at: str,
    command: list[str],
) -> str:
    counts = {
        action: sum(1 for item in classified if item.action == action)
        for action in ACTION_LABELS
    }
    total = len(classified)

    lines = [
        "## Dream Worker: validate-drift",
        "",
        f"Generated: {generated_at}",
        f"Command: `{shlex.join(command)}`",
        "",
    ]
    if total == 0:
        lines.append("Result: no validation drift found.")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the validate-drift Dream worker.")
    parser.add_argument(
        "--blackboard",
        type=Path,
        help="Append the concise worker result to this Dream run blackboard.",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Run validation from this repo directory. Defaults to the current directory.",
    )
    parser.add_argument("--max-lock-hours", type=float)
    parser.add_argument("--idle-hours", type=float)
    parser.add_argument("--max-blackboard-kb", type=float)
    args = parser.parse_args(argv)

    try:
        payload, command = run_validate_json(
            cwd=args.cwd,
            max_lock_hours=args.max_lock_hours,
            idle_hours=args.idle_hours,
            max_blackboard_kb=args.max_blackboard_kb,
        )
        classified = classify_issues(parse_issues(payload))
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        report = render_blackboard_report(
            classified,
            generated_at=generated_at,
            command=command,
        )
        if args.blackboard:
            append_report(args.blackboard, report)
        else:
            sys.stdout.write(report)
    except RuntimeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
