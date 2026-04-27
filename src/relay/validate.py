"""Deterministic repo validation — the engine behind the dream/drift skill.

Run as a module:

    python -m relay.validate [--json] [--max-lock-hours N]

Checks:
- Task dirs have ticket.md, blackboard.md, log.md.
- Lock files aren't stale (default threshold: 24h).
- Tasks stuck in `active` with no recent log activity.
- Workflow step skill refs point to files that exist.
- Ticket context refs point to files that exist.
- Assignees referenced in tickets exist in relay.toml.
- Status values are from the valid set.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from relay.config import Config, ConfigError, load_config
from relay.lock import TaskLock
from relay.paths import context_path, skill_path
from relay.tasks import list_tasks
from relay.ticket import Ticket, TicketError

VALID_STATUSES = {"draft", "active", "paused", "done"}


@dataclass
class Issue:
    kind: str            # "stale-lock", "missing-file", "broken-ref", ...
    task: str            # "id-slug"
    message: str
    severity: str = "warn"  # "warn" | "error"


@dataclass
class Report:
    generated_at: str
    issues: list[Issue] = field(default_factory=list)
    ok_count: int = 0


# --- engine -------------------------------------------------------------------


def run(cfg: Config, max_lock_hours: float = 24.0, idle_hours: float = 72.0) -> Report:
    report = Report(generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    refs = list_tasks(cfg)

    assignee_names = set(cfg.assignees)
    # Also accept agent nicknames from any assignee — any of them is a valid assignee string.
    valid_assignees = set(assignee_names)
    for a in cfg.assignees.values():
        valid_assignees.update(a.agents.keys())

    now = datetime.now(timezone.utc)

    for ref in refs:
        task_label = ref.id_slug

        # Required files
        for fname in ("ticket.md", "blackboard.md", "log.md"):
            if not (ref.path / fname).is_file():
                report.issues.append(Issue(
                    kind="missing-file",
                    task=task_label,
                    message=f"missing {fname}",
                    severity="error",
                ))

        # Lock staleness
        lock = TaskLock(ref.path)
        info = lock.read()
        if info and lock.is_stale(max_age_hours=max_lock_hours):
            age = now - info.acquired
            report.issues.append(Issue(
                kind="stale-lock",
                task=task_label,
                message=f"lock held by {info.holder!r} for {age.total_seconds() / 3600:.1f}h",
                severity="warn",
            ))

        # Parse ticket — only continue with ticket-level checks if valid
        try:
            ticket = Ticket.read(ref.path / "ticket.md")
        except (TicketError, FileNotFoundError):
            continue

        if ticket.status and ticket.status not in VALID_STATUSES:
            report.issues.append(Issue(
                kind="invalid-status",
                task=task_label,
                message=f"status {ticket.status!r} not in {sorted(VALID_STATUSES)}",
                severity="error",
            ))

        if ticket.assignee and ticket.assignee not in valid_assignees:
            report.issues.append(Issue(
                kind="unknown-assignee",
                task=task_label,
                message=f"assignee {ticket.assignee!r} is not a known human or agent nickname",
                severity="warn",
            ))

        # Broken context refs
        for ref_name in ticket.contexts:
            if not context_path(cfg, ref_name).is_file():
                report.issues.append(Issue(
                    kind="broken-context",
                    task=task_label,
                    message=f"context {ref_name!r} does not exist",
                    severity="error",
                ))

        # Broken skill refs in workflow
        wf = ticket.workflow or {}
        for step in wf.get("steps", []):
            skill_ref = step.get("skill")
            if skill_ref and not skill_path(cfg, skill_ref).is_file():
                report.issues.append(Issue(
                    kind="broken-skill",
                    task=task_label,
                    message=f"step {step.get('name', '?')!r} skill {skill_ref!r} does not exist",
                    severity="error",
                ))

        # Stuck-active: status=active but log.md hasn't been touched in `idle_hours`.
        if ticket.status == "active":
            log_path = ref.path / "log.md"
            if log_path.is_file():
                mtime = datetime.fromtimestamp(log_path.stat().st_mtime, tz=timezone.utc)
                idle = now - mtime
                if idle > timedelta(hours=idle_hours):
                    report.issues.append(Issue(
                        kind="stuck-active",
                        task=task_label,
                        message=f"active but idle for {idle.total_seconds() / 3600:.1f}h",
                        severity="warn",
                    ))

    report.ok_count = len(refs) - len({i.task for i in report.issues if i.severity == "error"})
    return report


# --- CLI entry ----------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Relay repo validator")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--max-lock-hours", type=float, default=24.0)
    parser.add_argument("--idle-hours", type=float, default=72.0)
    args = parser.parse_args(argv)

    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    report = run(cfg, max_lock_hours=args.max_lock_hours, idle_hours=args.idle_hours)

    if args.json:
        payload: dict[str, Any] = {
            "generated_at": report.generated_at,
            "ok_count": report.ok_count,
            "issues": [asdict(i) for i in report.issues],
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not report.issues:
            print(f"All good ({report.ok_count} tasks checked).")
        else:
            for issue in report.issues:
                sev = issue.severity.upper()
                print(f"[{sev}] {issue.task}: {issue.kind} — {issue.message}")

    # Exit code: 0 if no errors, 1 if errors, 2 on tool failure.
    return 1 if any(i.severity == "error" for i in report.issues) else 0


if __name__ == "__main__":
    sys.exit(_main())
