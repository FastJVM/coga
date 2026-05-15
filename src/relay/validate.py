"""Deterministic repo validation — the engine behind the dream/drift skill.

Exposed as `relay validate` (see `relay.commands.validate`); also runnable
directly as a module:

    relay validate [--json] [--fix] [--max-blackboard-kb N] [--check-slack]
    python -m relay.validate [--json] [--fix] [--max-blackboard-kb N] [--check-slack]

Checks:
- Task dirs have ticket.md, blackboard.md, log.md.
- Blackboard files are not large enough to bloat composed prompts.
- Tasks stuck in `active` with no recent log activity.
- Workflow step skill refs point to files that exist.
- Ticket context refs point to files that exist.
- Assignees referenced in tickets exist in relay.toml.
- Status values are from the valid set.
- (Opt-in) Slack webhook reachability via an empty-text probe.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from relay.blackboard import BLACKBOARD_WARN_BYTES, blackboard_size_warning, render_blackboard
from relay.config import Config, ConfigError, load_config
from relay.paths import context_path, skill_path
from relay.tasks import list_tasks
from relay.ticket import Ticket, TicketError

VALID_STATUSES = {"draft", "active", "in_progress", "paused", "done"}


@dataclass
class Issue:
    kind: str            # "missing-file", "broken-ref", ...
    task: str            # "id-slug"
    message: str
    severity: str = "warn"  # "warn" | "error"


@dataclass
class Fix:
    kind: str
    task: str
    message: str
    path: str


@dataclass
class Report:
    generated_at: str
    issues: list[Issue] = field(default_factory=list)
    fixes: list[Fix] = field(default_factory=list)
    ok_count: int = 0


# --- engine -------------------------------------------------------------------


def run(
    cfg: Config,
    idle_hours: float = 72.0,
    max_blackboard_bytes: int = BLACKBOARD_WARN_BYTES,
    check_slack: bool = False,
    fix: bool = False,
) -> Report:
    report = Report(generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    if fix:
        report.fixes.extend(apply_safe_fixes(cfg))

    if check_slack:
        if not cfg.slack_enabled:
            # Honor the opt-out — don't pretend to validate something that's off.
            pass
        elif not cfg.slack_webhook:
            report.issues.append(Issue(
                kind="slack-misconfigured",
                task="(slack)",
                message="$SLACK_WEBHOOK_URL is not set (relay requires it unless [slack].enabled = false)",
                severity="error",
            ))
        else:
            status, detail = probe_slack(cfg.slack_webhook)
            if status == "live":
                pass  # ok — leave it implicit so JSON output stays clean
            elif status == "revoked":
                report.issues.append(Issue(
                    kind="slack-revoked",
                    task="(slack)",
                    message=f"webhook URL not recognized by Slack: {detail}",
                    severity="error",
                ))
            else:  # unreachable
                report.issues.append(Issue(
                    kind="slack-unreachable",
                    task="(slack)",
                    message=f"could not reach Slack: {detail}",
                    severity="error",
                ))
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

        warning = blackboard_size_warning(
            ref.path / "blackboard.md",
            max_bytes=max_blackboard_bytes,
        )
        if warning:
            report.issues.append(Issue(
                kind="large-blackboard",
                task=task_label,
                message=warning,
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

        # Broken skill refs in workflow. `ticket.workflow` is a frozen dict
        # post-launch but can be a bare string (workflow ref) or absent on
        # hand-authored / pre-freeze tickets — don't crash on those shapes.
        wf = ticket.workflow
        if isinstance(wf, dict):
            for step in wf.get("steps", []):
                skill_ref = step.get("skill")
                if skill_ref and not skill_path(cfg, skill_ref).is_file():
                    report.issues.append(Issue(
                        kind="broken-skill",
                        task=task_label,
                        message=f"step {step.get('name', '?')!r} skill {skill_ref!r} does not exist",
                        severity="error",
                    ))
        elif wf is not None:
            report.issues.append(Issue(
                kind="unfrozen-workflow",
                task=task_label,
                message=f"workflow {wf!r} is not a frozen dict — likely a hand-authored ticket awaiting first launch",
                severity="warn",
            ))

        # Stuck in progress: work started but log.md has not moved in `idle_hours`.
        if ticket.status == "in_progress":
            log_path = ref.path / "log.md"
            if log_path.is_file():
                mtime = datetime.fromtimestamp(log_path.stat().st_mtime, tz=timezone.utc)
                idle = now - mtime
                if idle > timedelta(hours=idle_hours):
                    report.issues.append(Issue(
                        kind="stuck-in-progress",
                        task=task_label,
                        message=f"in_progress but idle for {idle.total_seconds() / 3600:.1f}h",
                        severity="warn",
                    ))

    report.ok_count = len(refs) - len({i.task for i in report.issues if i.severity == "error" and i.task != "(slack)"})
    return report


def apply_safe_fixes(cfg: Config) -> list[Fix]:
    """Apply deterministic repairs that do not change task state.

    Current safe set:
      - create missing `blackboard.md` from the default template
      - create missing `log.md` as an empty append-only file

    Existing files are never rewritten, and `ticket.md` is never
    reconstructed from inference.
    """
    fixes: list[Fix] = []
    for ref in list_tasks(cfg):
        blackboard_path = ref.path / "blackboard.md"
        if not blackboard_path.is_file():
            title = ref.slug
            try:
                title = Ticket.read(ref.path / "ticket.md").title or ref.slug
            except (TicketError, FileNotFoundError):
                pass
            blackboard_path.write_text(render_blackboard(title))
            fixes.append(
                Fix(
                    kind="missing-file",
                    task=ref.id_slug,
                    message="created blackboard.md",
                    path=str(blackboard_path),
                )
            )

        log_path = ref.path / "log.md"
        if not log_path.is_file():
            log_path.write_text("")
            fixes.append(
                Fix(
                    kind="missing-file",
                    task=ref.id_slug,
                    message="created log.md",
                    path=str(log_path),
                )
            )

    return fixes


# --- slack probe -------------------------------------------------------------


def probe_slack(webhook_url: str) -> tuple[str, str]:
    """POST an empty-text payload to a Slack webhook and classify the response.

    Returns (status, detail) where status is one of:
      "live"        — Slack received the request (any 2xx/4xx that isn't a 404
                      or a `no_service` body)
      "revoked"     — webhook URL not recognized (HTTP 404 or `no_service`)
      "unreachable" — network-level failure or 5xx

    Slack's incoming-webhook wire format isn't pinned by contract; the
    implementation matches by `in` rather than equality so minor body changes
    don't break things.
    """
    try:
        resp = requests.post(webhook_url, json={"text": ""}, timeout=5)
    except requests.RequestException as exc:
        return "unreachable", f"{type(exc).__name__}: {exc}"

    body = resp.text.strip()[:200]
    if resp.status_code == 404 or "no_service" in body:
        return "revoked", f"HTTP {resp.status_code}: {body!r}"
    if 200 <= resp.status_code < 500:
        return "live", f"HTTP {resp.status_code}: {body!r}"
    return "unreachable", f"HTTP {resp.status_code}: {body!r}"


# --- CLI entry ----------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Relay repo validator")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply conservative safe repairs before reporting.",
    )
    parser.add_argument("--idle-hours", type=float, default=72.0)
    parser.add_argument(
        "--max-blackboard-kb",
        type=float,
        default=BLACKBOARD_WARN_BYTES / 1024,
        help="Blackboard size above which to warn about prompt bloat.",
    )
    parser.add_argument(
        "--check-slack",
        action="store_true",
        help="Also probe the Slack webhook with an empty-text payload (network call).",
    )
    args = parser.parse_args(argv)

    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    report = run(
        cfg,
        idle_hours=args.idle_hours,
        max_blackboard_bytes=int(args.max_blackboard_kb * 1024),
        check_slack=args.check_slack,
        fix=args.fix,
    )

    if args.json:
        payload: dict[str, Any] = {
            "generated_at": report.generated_at,
            "ok_count": report.ok_count,
            "fixes": [asdict(f) for f in report.fixes],
            "issues": [asdict(i) for i in report.issues],
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not report.issues:
            for fix_item in report.fixes:
                print(f"[FIX] {fix_item.task}: {fix_item.kind} — {fix_item.message}")
            print(f"All good ({report.ok_count} tasks checked).")
        else:
            for fix_item in report.fixes:
                print(f"[FIX] {fix_item.task}: {fix_item.kind} — {fix_item.message}")
            for issue in report.issues:
                sev = issue.severity.upper()
                print(f"[{sev}] {issue.task}: {issue.kind} — {issue.message}")

    # Exit code: 0 if no errors, 1 if errors, 2 on tool failure.
    return 1 if any(i.severity == "error" for i in report.issues) else 0


if __name__ == "__main__":
    sys.exit(_main())
