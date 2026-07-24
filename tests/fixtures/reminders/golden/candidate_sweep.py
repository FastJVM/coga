#!/usr/bin/env python3
"""Candidate first-office-action reminder sweep.

Reads the local patent tickets, selects the ones in the **candidate** stage (a
utility application prosecuting at the USPTO, not yet granted), and flags every
candidate whose utility filing date has just reached the 14-month mark — USPTO's
first-office-action deadline. The alert is a nudge for the human to go check
where that application stands in prosecution; this sweep never tracks office
actions, advances a stage, or mutates a ticket.

A candidate is flagged for the one month starting at filing + 14 months::

    deadline = patent_filing_date + 14 months   # USPTO first-office-action mark
    window   [deadline, patent_filing_date + 15 months)   # open inclusive

The window is exactly one month wide, so the monthly sweep lands in it once and
each candidate alerts a single time, then ages out — there is no re-fire and no
reviewed-state field to read or write.

Selector — a ticket is a *candidate* when its ``step`` is the ``candidate`` stage
of ``patent/lifecycle-v2`` and it has no ``patent_number`` (a number means the
USPTO sync already advanced it to the granted/utility stage). The stage is read
from the ``step`` field, never inferred from the slug — some ``idea``-stage
tickets carry "candidate" in their slug. A candidate with a blank
``patent_filing_date`` cannot be windowed, so it is flagged with distinct
*needs-a-filing-date* text rather than silently skipped.

Run it through coga (``coga launch repo/candidate/candidate-sweep``), or
standalone for testing::

    python candidate_sweep.py [--today YYYY-MM-DD] [--tasks-dir PATH] [--notify]

A bare run is read-only: it prints the report and posts nothing. With
``--notify`` each flagged candidate is announced to the coga-important Slack
channel via ``coga slack --important`` (needs ``COGA_IMPORTANT_WEBHOOK_URL``
configured). A run against a ``--tasks-dir`` of fake tickets only posts about
those, so it is safe for testing.

It has no third-party dependencies beyond the ``coga`` CLI on PATH, so it runs
under any Python 3.
"""

from __future__ import annotations

import argparse
import calendar
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# USPTO's first-office-action deadline is 14 months after filing; the sweep
# flags a candidate for the one month starting there, then it ages out.
OFFICE_ACTION_MONTHS = 14
WINDOW_MONTHS = 1  # -> window is [filing + 14mo, filing + 15mo)


@dataclass(frozen=True)
class CandidateRecord:
    slug: str
    title: str
    application: str
    number: str
    filing_raw: str
    filing: date | None


@dataclass(frozen=True)
class Flag:
    record: CandidateRecord
    deadline: date  # filing + 14 months (first-office-action mark)
    ages_out: date  # filing + 15 months (window closes)


def add_months(d: date, months: int) -> date:
    """``d`` plus ``months``, clamping the day to the target month's last day
    (e.g. Jan 31 + 1 month -> Feb 28/29)."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _stage_of(step_field: str) -> str:
    """The stage name from a ``step`` value like ``3 (candidate)`` -> ``candidate``.

    The workflow step number can shift, but the parenthesised stage name is
    stable, so match on the name. Returns ``""`` when there is no stage.
    """
    inside = step_field.partition("(")[2].rpartition(")")[0]
    return inside.strip().lower()


def _read_frontmatter(path: Path) -> dict[str, str]:
    """Top-level scalar frontmatter fields of a ticket, as strings.

    Deliberately dependency-free: we only need a handful of simple scalar keys
    (``step``, ``patent_application``, ``patent_filing_date``, ``patent_number``,
    ``slug``, ``title``). We read the block between the first two ``---`` fences
    and keep only column-0 ``key: value`` lines, so nested/indented keys (lists,
    the workflow block) are ignored. Returns ``{}`` when there is no frontmatter.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    if not text.startswith("---"):
        return {}
    _, _, after = text.partition("---")
    block, sep, _ = after.partition("\n---")
    if not sep:
        return {}
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        key, colon, value = line.partition(":")
        if not colon:
            continue
        fields[key.strip()] = value.strip().strip("'\"")
    return fields


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def load_candidate_records(tasks_dir: Path) -> list[CandidateRecord]:
    """Every ticket under ``tasks_dir`` whose ``step`` is the candidate stage.

    Read the stage from ``step`` (never the slug). A ``patent_number`` is kept on
    the record so ``evaluate`` can surface an already-granted ticket that has not
    yet been advanced, rather than window it.
    """
    records: list[CandidateRecord] = []
    for path in sorted(tasks_dir.rglob("*.md")):
        fm = _read_frontmatter(path)
        if _stage_of(fm.get("step", "")) != "candidate":
            continue
        filing_raw = fm.get("patent_filing_date", "").strip()
        records.append(
            CandidateRecord(
                slug=fm.get("slug", "").strip() or path.stem,
                title=fm.get("title", "").strip(),
                application=fm.get("patent_application", "").strip(),
                number=fm.get("patent_number", "").strip(),
                filing_raw=filing_raw,
                filing=_parse_date(filing_raw),
            )
        )
    return records


def evaluate(
    records: list[CandidateRecord], today: date
) -> tuple[
    list[Flag],
    list[CandidateRecord],
    list[CandidateRecord],
    list[CandidateRecord],
]:
    """Split candidate tickets into:

    - **flags** — a readable filing date whose 14-month window contains today.
    - **needs_filing** — ``patent_filing_date`` is blank: cannot be windowed, so
      it is flagged with distinct text rather than skipped.
    - **unreadable** — a filing-date field that is present but does not parse (a
      data-entry error to surface, never silently dropped).
    - **granted** — a candidate carrying a ``patent_number``: the USPTO sync
      should have advanced it to the granted stage, so it is reported as an
      anomaly rather than windowed.

    ``granted`` is checked first so a ticket that has genuinely exited the stage
    is reported as such even if its filing date is also blank/malformed.
    """
    flags: list[Flag] = []
    needs_filing: list[CandidateRecord] = []
    unreadable: list[CandidateRecord] = []
    granted: list[CandidateRecord] = []
    for r in records:
        if r.number:
            granted.append(r)
            continue
        if not r.filing_raw:
            needs_filing.append(r)
            continue
        if r.filing is None:
            unreadable.append(r)
            continue
        deadline = add_months(r.filing, OFFICE_ACTION_MONTHS)
        ages_out = add_months(r.filing, OFFICE_ACTION_MONTHS + WINDOW_MONTHS)
        if deadline <= today < ages_out:
            flags.append(Flag(record=r, deadline=deadline, ages_out=ages_out))
    return flags, needs_filing, unreadable, granted


def default_tasks_dir() -> Path:
    """The coga tasks directory: from ``$COGA_COGA_OS_ROOT`` when coga launches
    the script, else derived from this file's location for standalone runs."""
    env_root = os.environ.get("COGA_COGA_OS_ROOT")
    coga_os_root = Path(env_root) if env_root else Path(__file__).resolve().parents[4]
    return coga_os_root / "tasks"


def _app(record: CandidateRecord) -> str:
    """Application number for display, or an em dash when blank."""
    return record.application or "—"


def format_report(
    records: list[CandidateRecord],
    flags: list[Flag],
    needs_filing: list[CandidateRecord],
    unreadable: list[CandidateRecord],
    granted: list[CandidateRecord],
    today: date,
) -> str:
    lines = [
        f"Candidate first-office-action sweep — as of {today.isoformat()}",
        f"Checked {len(records)} candidate ticket(s).",
    ]
    if granted:
        slugs = ", ".join(r.slug for r in granted)
        lines.append(
            f"  ! {len(granted)} carry a patent number (already granted — the sync "
            f"should have advanced them, not swept here): {slugs}"
        )

    if needs_filing:
        lines.append(f"\nNeeds a filing date ({len(needs_filing)}):")
        for r in sorted(needs_filing, key=lambda r: r.slug):
            lines.append(
                f"  ? {r.slug}  (app {_app(r)})  "
                f"— patent_filing_date is blank; set it so this candidate can be windowed"
            )
    if unreadable:
        lines.append(f"\nUnreadable filing date ({len(unreadable)}):")
        for r in sorted(unreadable, key=lambda r: r.slug):
            lines.append(
                f"  ! {r.slug}  (app {_app(r)})  "
                f"— patent_filing_date={r.filing_raw!r} does not parse (YYYY-MM-DD expected)"
            )

    if not flags:
        lines.append("\nFlagged (0): no candidate in its 14-month window this run.")
        return "\n".join(lines)

    lines.append(f"\nFlagged ({len(flags)}):")
    for f in sorted(flags, key=lambda f: (f.deadline, f.record.slug)):
        lines.append(
            f"  * {f.record.slug}  (app {_app(f.record)})  "
            f"— filed {f.record.filing.isoformat()}; first-office-action deadline "
            f"{f.deadline.isoformat()} (filing+14mo); window closes "
            f"{f.ages_out.isoformat()} (check where the utility filing stands)"
        )
    return "\n".join(lines)


# Where notifications land: each flagged candidate is posted to the coga-important
# channel via `coga slack … --important`. `--task` needs a real ticket for the
# [project]/[owner] prefix; under a coga launch that's this script's own task
# ($COGA_TASK_SLUG), and a standalone run falls back to the sweep ticket slug.
SWEEP_TASK_SLUG = "repo/candidate/candidate-sweep"


def flag_message(flag: Flag) -> str:
    """One-line coga-important alert for a candidate at its 14-month mark."""
    return (
        f"⚠️ Candidate first-office-action check — {flag.record.slug} "
        f"(app {_app(flag.record)}): filed {flag.record.filing.isoformat()}, "
        f"first-office-action deadline {flag.deadline.isoformat()} (filing+14mo). "
        f"Check where the utility filing stands."
    )


def needs_filing_message(record: CandidateRecord) -> str:
    """One-line coga-important alert for a candidate missing its filing date."""
    return (
        f"⚠️ Candidate needs a filing date — {record.slug} (app {_app(record)}): "
        f"patent_filing_date is blank, so the first-office-action reminder can't "
        f"track this candidate. Set it."
    )


def unreadable_message(record: CandidateRecord) -> str:
    """One-line coga-important alert for a candidate with an unparseable filing date."""
    return (
        f"⚠️ Candidate has an unreadable filing date — {record.slug} "
        f"(app {_app(record)}): patent_filing_date={record.filing_raw!r} does not "
        f"parse (YYYY-MM-DD expected). Fix it so the reminder can track this candidate."
    )


def post_alerts(
    flags: list[Flag],
    needs_filing: list[CandidateRecord],
    unreadable: list[CandidateRecord],
) -> int:
    """Post one coga-important alert per flagged candidate; return the failure count.

    Shells out to `coga slack --important` (no coga import — this script stays
    standalone). coga reads COGA_IMPORTANT_WEBHOOK_URL from the environment and
    fails loud if it isn't set, so a missing webhook surfaces as a failure here.
    """
    task = os.environ.get("COGA_TASK_SLUG") or SWEEP_TASK_SLUG
    posts: list[tuple[str, str]] = []
    for flag in sorted(flags, key=lambda f: (f.deadline, f.record.slug)):
        posts.append((flag.record.slug, flag_message(flag)))
    for r in sorted(needs_filing, key=lambda r: r.slug):
        posts.append((r.slug, needs_filing_message(r)))
    for r in sorted(unreadable, key=lambda r: r.slug):
        posts.append((r.slug, unreadable_message(r)))

    failures = 0
    for slug, message in posts:
        result = subprocess.run(
            ["coga", "slack", "--task", task, "--message", message, "--important"],
        )
        if result.returncode != 0:
            failures += 1
            print(f"  ! failed to post alert for {slug}", file=sys.stderr)
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flag candidate patents reaching their 14-month first-office-action mark."
    )
    parser.add_argument(
        "--today", type=date.fromisoformat, default=None,
        help="Override today's date (YYYY-MM-DD) — for testing.",
    )
    parser.add_argument(
        "--tasks-dir", type=Path, default=None,
        help="Override the tasks directory (defaults to the coga tasks dir).",
    )
    parser.add_argument(
        "--notify", action="store_true",
        help="Post a coga-important alert per flagged candidate (bare run is print-only).",
    )
    args = parser.parse_args(argv)

    today = args.today or date.today()
    tasks_dir = args.tasks_dir or default_tasks_dir()
    if not tasks_dir.is_dir():
        print(f"tasks directory not found: {tasks_dir}", file=sys.stderr)
        return 1

    records = load_candidate_records(tasks_dir)
    flags, needs_filing, unreadable, granted = evaluate(records, today)
    print(format_report(records, flags, needs_filing, unreadable, granted, today))

    alert_count = len(flags) + len(needs_filing) + len(unreadable)
    if args.notify and alert_count:
        print(
            f"\nPosting {alert_count} alert(s) to the coga-important channel …",
            file=sys.stderr,
        )
        if post_alerts(flags, needs_filing, unreadable):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
