"""Importable skill-update recipe.

Wraps `coga skill update --all --pr`: applies every clean imported-skill
update into one reviewable PR and reports the skills that could not be updated
cleanly (a local adaptation, a provenance conflict, a fetch failure) so they
surface as follow-up work on the task blackboard.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from coga.config import Config
from coga.task_env import blackboard_from_env, discover_coga_os_root

# Update statuses `coga skill update` emits, grouped into the three buckets
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


@dataclass
class SkillUpdateReport:
    """What one `run_skill_update_recipe` run collected, for reporting.

    The wrapper already computes every field before it returns an exit code.
    Handing them back lets a caller name the run — the recurring `ticket.py`
    shim bumping with `--message` — from the values themselves rather than by
    scraping `Result:` and `PR:` back out of the rendered `report`, which would
    rot silently the next time that layout changes.

    `command` is recorded before the update is invoked, so it names the command
    that was attempted even on the failure exit — `run_update_json` raises only
    *after* the subprocess ran (non-zero exit, or output that is not valid
    JSON), so an empty `command` would have been a misleading "never ran"
    signal. `results` still empty after a run is what says nothing was
    collected.
    """

    results: list[SkillUpdate] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    pr_url: str | None = None
    pr_requested: bool = True
    report: str = ""


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
    """Return the exact `coga skill update` command this skill runs."""
    cmd = [sys.executable, "-m", "coga.cli", "skill", "update", "--all", "--json"]
    if pr:
        cmd.extend(["--pr", "--pr-title", pr_title])
    return cmd


def run_update_json(
    *,
    cwd: Path | None,
    pr: bool,
    pr_title: str,
) -> tuple[dict[str, Any], list[str]]:
    """Run `coga skill update --all [--pr] --json` and return `(payload, cmd)`.

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


def render_result_line(results: list[SkillUpdate]) -> str:
    """The one-sentence tally the report's `Result:` line carries.

    Public so a caller summarizing a run states the counts the same way the
    blackboard report does, from the same input, instead of parsing the line
    back out of the rendered text.
    """
    if not results:
        return "no installed skills to update."
    grouped = group_results(results)
    return (
        f"{len(results)} skill(s): "
        f"{len(grouped[GROUP_UPDATED])} updated, "
        f"{len(grouped[GROUP_FOLLOWUP])} need follow-up, "
        f"{len(grouped[GROUP_SKIPPED])} skipped."
    )


def group_results(results: list[SkillUpdate]) -> dict[str, list[SkillUpdate]]:
    """Bucket `results` by `classify_status`, with every bucket present."""
    grouped: dict[str, list[SkillUpdate]] = {
        GROUP_UPDATED: [],
        GROUP_FOLLOWUP: [],
        GROUP_SKIPPED: [],
    }
    for result in results:
        grouped[classify_status(result.status)].append(result)
    return grouped


# The heading both report variants carry. Named here because it is the report's
# contract with everything that reads it back: the packaged skill-update SKILL.md
# and ticket.md, the workflow run.md, and the tests that assert on the section.
SKILL_UPDATE_HEADING = "## Skill Update"


def _report_header(
    *, generated_at: str, command: list[str], task_slug: str | None
) -> list[str]:
    """The opening lines every skill-update report shares, success or failure.

    A failure report is still a skill-update report: it is read out of the same
    blackboard section by the same readers, so the two renderers must not drift
    apart about what identifies a run.
    """
    lines = [
        SKILL_UPDATE_HEADING,
        "",
        f"Generated: {generated_at}",
        f"Command: `{shlex.join(command)}`",
    ]
    if task_slug:
        lines.append(f"Task: `{task_slug}`")
    lines.append("")
    return lines


def render_blackboard_report(
    results: list[SkillUpdate],
    *,
    generated_at: str,
    command: list[str],
    pr_url: str | None,
    pr_requested: bool,
    task_slug: str | None = None,
) -> str:
    lines = _report_header(
        generated_at=generated_at, command=command, task_slug=task_slug
    )

    if not results:
        lines.append(f"Result: {render_result_line(results)}")
        lines.append("")
        lines.append("PR: none opened — nothing to update.")
        return "\n".join(lines) + "\n"

    grouped = group_results(results)

    lines.append(f"Result: {render_result_line(results)}")

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


def render_failure_report(
    detail: str,
    *,
    generated_at: str,
    command: list[str],
    pr_requested: bool,
    task_slug: str | None = None,
) -> str:
    """Render the report for a run that failed before classifying anything.

    A hard failure has to be as legible in the run record as a follow-up one.
    The recurring sweep discards a task's stderr, so a run that only wrote its
    diagnostic there showed up as a failed task with a blank blackboard and no
    reason. `detail` is the `RuntimeError` message, which already names the
    command, its exit code, and the stderr the subprocess produced.
    """
    lines = _report_header(
        generated_at=generated_at, command=command, task_slug=task_slug
    )
    lines.append("Result: the update failed; no skills were classified.")
    if pr_requested:
        # Deliberately not "none opened": `run_update_json` raises only after
        # the child process has run, and `open_or_update_pr` pushes the branch
        # before it calls `gh`. A `gh` failure can therefore leave a real PR —
        # or a real branch update — behind. Report what was observed.
        lines.append(
            "PR: not confirmed — the update failed; check the skill-update branch."
        )
    else:
        lines.append("PR: none opened (--no-pr).")
    lines.append("")
    lines.append("### Failed")
    lines.append("")
    lines.append("```")
    lines.append(detail.strip() or "no output")
    lines.append("```")
    return "\n".join(lines).rstrip() + "\n"


def has_followups(results: list[SkillUpdate]) -> bool:
    return any(classify_status(result.status) == GROUP_FOLLOWUP for result in results)


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


def _emit_report(blackboard: Path | None, report: str) -> None:
    """Send a rendered report to the blackboard, or to stdout when there is none."""
    if blackboard:
        append_report(blackboard, report)
    else:
        sys.stdout.write(report)


def script_task_slug_from_env() -> str | None:
    return os.environ.get("COGA_TASK_SLUG")


def run_skill_update_recipe(
    cfg: Config, argv: list[str], *, result: SkillUpdateReport | None = None
) -> int:
    """Run the recurring skill-update job.

    `result` is the optional out-parameter described on `run_recipe`: the
    results, PR link and rendered report this wrapper already holds as locals
    are recorded on it as they are computed, so a caller summarizing the run
    reads them directly. The attempted `command` and `pr_requested` are
    recorded before the update runs, so the exit-2 path reports what it tried;
    the exit-1 path additionally carries everything it collected. Both non-zero
    exits leave a `## Skill Update` section on the blackboard: exit 2 writes the
    failure detail there rather than to stderr alone, which the recurring sweep
    discards.

    That exit-2 blackboard write is the first instance of a property the other
    recipes still lack — `dream_validate_drift`, `dream_cleanup_orphan_markers`,
    `branchsweep`, `autoclose`, `blocker_reminders` and `recurring_autofix` all
    exit non-zero to stderr alone. It belongs in the recipe layer rather than
    here; do not paste a seventh copy, generalize it instead.
    """
    del cfg
    report_out = result if result is not None else SkillUpdateReport()
    parser = argparse.ArgumentParser(description="Run the skill-update maintenance skill.")
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Run the update from this repo directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--pr-title",
        default="Update Coga-managed skills",
        help="Title for the skill-update PR.",
    )
    parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Collect and classify updates without opening a PR.",
    )
    args = parser.parse_args(argv)

    blackboard = blackboard_from_env(discover_coga_os_root(args.cwd))
    task_slug = script_task_slug_from_env()
    pr = not args.no_pr
    report_out.pr_requested = pr
    # Recorded up front, not from `run_update_json`'s second return value —
    # it runs exactly this command, but raises only *after* the subprocess has
    # already run, so waiting for it would leave `command` empty on exactly the
    # failed runs a caller most wants to name.
    report_out.command = build_update_command(pr=pr, pr_title=args.pr_title)

    # Scoped to the update itself. `_emit_report` is deliberately *outside* it:
    # `append_report` also raises `RuntimeError` (a missing blackboard parent),
    # and catching that here would file a successful run under "the update
    # failed; no skills were classified" while `report_out.results` still held
    # the full classification.
    try:
        payload, command = run_update_json(cwd=args.cwd, pr=pr, pr_title=args.pr_title)
    except RuntimeError as exc:
        detail = str(exc)
        sys.stderr.write(f"{detail}\n")
        failure = render_failure_report(
            detail,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            command=report_out.command,
            pr_requested=pr,
            task_slug=task_slug,
        )
        report_out.report = failure
        try:
            _emit_report(blackboard, failure)
        except (RuntimeError, OSError) as write_exc:
            # `OSError` as well as `RuntimeError`: `append_report` only converts
            # a missing parent directory into the latter, while the write itself
            # raises `PermissionError` on a read-only checkout or a full disk.
            # Either way, say so on stderr and still exit 2 rather than burying
            # the original diagnostic under a traceback.
            sys.stderr.write(f"Could not write the failure report: {write_exc}\n")
        return 2

    results = parse_results(payload)
    raw_pr_url = payload.get("pr_url")
    pr_url = raw_pr_url if isinstance(raw_pr_url, str) and raw_pr_url else None
    report = render_blackboard_report(
        results,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        command=command,
        pr_url=pr_url,
        pr_requested=pr,
        task_slug=task_slug,
    )
    report_out.results = results
    report_out.pr_url = pr_url
    report_out.report = report
    _emit_report(blackboard, report)
    if pr and pr_url is None and has_followups(results):
        sys.stderr.write(
            "Skill update needs human follow-up and no PR was opened; "
            "see the task blackboard for the conflict report.\n"
        )
        return 1

    return 0
