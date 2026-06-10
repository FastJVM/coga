#!/usr/bin/env python3
"""Run the skill-update Dream skill.

Wraps `relay skill update --all --pr`: applies every clean imported-skill
update into one reviewable PR and reports the skills that could not be updated
cleanly (a local adaptation, a provenance conflict, a fetch failure) so they
surface as follow-up work on the child task blackboard.
"""

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

# Update statuses `relay skill update` emits, grouped into the three buckets
# this skill reports. The buckets only drive the headline summary and the
# section a skill is listed under; skills are always listed by their *raw*
# status, so a new status (e.g. the `conflict` status a sibling ticket adds)
# stays distinct from `skipped-local-adaptation` instead of being merged with
# it. Any status not named here is treated as follow-up so it is never silently
# swallowed.
GROUP_UPDATED = "updated"
GROUP_FOLLOWUP = "followup"
GROUP_SKIPPED = "skipped"

UPDATED_STATUSES = {"updated", "installed", "delegated"}
FOLLOWUP_STATUSES = {"conflict", "skipped-local-adaptation", "failed", "fetch-failed"}
SKIPPED_STATUSES = {
    "unchanged",
    "skipped-bundled",
    "package-backed",
    "local-override",
    "up-to-date",
    "not-checked",
}

GROUP_HEADINGS = {
    GROUP_UPDATED: "Updated",
    GROUP_FOLLOWUP: "Needs follow-up",
    GROUP_SKIPPED: "Skipped",
}


@dataclass(frozen=True)
class SkillUpdate:
    name: str
    source_type: str
    status: str
    message: str
    changed: bool


def classify_status(status: str) -> str:
    """Map a raw update status to one of the three report buckets.

    Unknown statuses fall through to `followup` so a newly-introduced status is
    surfaced loudly for a human rather than hidden under a benign heading.
    """
    if status in UPDATED_STATUSES:
        return GROUP_UPDATED
    if status in SKIPPED_STATUSES:
        return GROUP_SKIPPED
    return GROUP_FOLLOWUP


def build_update_command(*, pr: bool, pr_title: str) -> list[str]:
    """Return the exact `relay skill update` command this skill runs."""
    cmd = [sys.executable, "-m", "relay.cli", "skill", "update", "--all", "--json"]
    if pr:
        cmd.extend(["--pr", "--pr-title", pr_title])
    return cmd


def run_update_json(
    *,
    cwd: Path | None,
    pr: bool,
    pr_title: str,
) -> tuple[dict[str, Any], list[str]]:
    """Run `relay skill update --all [--pr] --json` and return `(payload, cmd)`.

    The command exits non-zero only when the update itself failed; a clean run
    that leaves some skills needing follow-up still exits 0.
    """
    cmd = build_update_command(pr=pr, pr_title=pr_title)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(
            f"`{shlex.join(cmd)}` failed with exit {result.returncode}: {detail}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"`{shlex.join(cmd)}` did not emit valid JSON: {exc}") from exc
    return payload, cmd


def parse_results(payload: dict[str, Any]) -> list[SkillUpdate]:
    results: list[SkillUpdate] = []
    for raw in payload.get("results", []):
        if not isinstance(raw, dict):
            continue
        results.append(
            SkillUpdate(
                name=str(raw.get("name", "(unknown)")),
                source_type=str(raw.get("source_type", "unknown")),
                status=str(raw.get("status", "unknown")),
                message=str(raw.get("message", "")),
                changed=bool(raw.get("changed", False)),
            )
        )
    return results


def render_blackboard_report(
    results: list[SkillUpdate],
    *,
    generated_at: str,
    command: list[str],
    pr_url: str | None,
    pr_requested: bool,
    task_slug: str | None = None,
) -> str:
    lines = [
        "## Dream Skill: skill-update",
        "",
        f"Generated: {generated_at}",
        f"Command: `{shlex.join(command)}`",
    ]
    if task_slug:
        lines.append(f"Task: `{task_slug}`")
    lines.append("")

    if not results:
        lines.append("Result: no installed skills to update.")
        lines.append("")
        lines.append("PR: none opened — nothing to update.")
        return "\n".join(lines) + "\n"

    grouped: dict[str, list[SkillUpdate]] = {
        GROUP_UPDATED: [],
        GROUP_FOLLOWUP: [],
        GROUP_SKIPPED: [],
    }
    for result in results:
        grouped[classify_status(result.status)].append(result)

    lines.append(
        f"Result: {len(results)} skill(s): "
        f"{len(grouped[GROUP_UPDATED])} updated, "
        f"{len(grouped[GROUP_FOLLOWUP])} need follow-up, "
        f"{len(grouped[GROUP_SKIPPED])} skipped."
    )

    if pr_url:
        lines.append(f"PR: {pr_url}")
    elif not pr_requested:
        lines.append("PR: none opened (--no-pr).")
    else:
        lines.append("PR: none opened — no clean skill updates to commit.")
    lines.append("")

    for group in (GROUP_UPDATED, GROUP_FOLLOWUP, GROUP_SKIPPED):
        bucket = grouped[group]
        if not bucket:
            continue
        lines.append(f"### {GROUP_HEADINGS[group]}")
        lines.append("")
        for result in sorted(bucket, key=lambda item: (item.status, item.name)):
            lines.append(
                f"- `{result.name}`: `{result.status}` ({result.source_type}) - {result.message}"
            )
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


def script_blackboard_from_env() -> Path | None:
    value = os.environ.get("RELAY_TASK_BLACKBOARD")
    return Path(value) if value else None


def script_task_slug_from_env() -> str | None:
    return os.environ.get("RELAY_TASK_SLUG")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the skill-update Dream skill.")
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Run the update from this repo directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--pr-title",
        default="Update Relay-managed skills",
        help="Title for the skill-update PR.",
    )
    parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Collect and classify updates without opening a PR.",
    )
    args = parser.parse_args(argv)

    blackboard = script_blackboard_from_env()
    task_slug = script_task_slug_from_env()
    pr = not args.no_pr

    try:
        payload, command = run_update_json(cwd=args.cwd, pr=pr, pr_title=args.pr_title)
        results = parse_results(payload)
        pr_url = payload.get("pr_url")
        report = render_blackboard_report(
            results,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            command=command,
            pr_url=pr_url if isinstance(pr_url, str) and pr_url else None,
            pr_requested=pr,
            task_slug=task_slug,
        )
        if blackboard:
            append_report(blackboard, report)
        else:
            sys.stdout.write(report)
    except RuntimeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
