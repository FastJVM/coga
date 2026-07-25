#!/usr/bin/env python3
"""Candidate first-office-action reminder sweep — engine-backed retrofit.

Behaviourally identical stdout to the standalone ``golden/candidate_sweep.py``
for the same ``--today`` / ``--tasks-dir``: the shared machinery now comes from
``coga.reminders``. Only the unique 20% stays here — the candidate-stage
selector, the single ``[filing+14mo, filing+15mo)`` window, the four evaluate
buckets, and the report/message formats.

This is the second worked parity example for the reminder-engine battery — the
time-window path, complementing the maintenance sweep's auto-detect path. The
live patents migration is a downstream follow-up.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from coga import reminders

# USPTO's first-office-action deadline is 14 months after filing; the sweep flags
# a candidate for the one month starting there, then it ages out.
OFFICE_ACTION_MONTHS = 14
WINDOW_MONTHS = 1  # -> window is [filing + 14mo, filing + 15mo)

SWEEP_TASK_SLUG = "repo/candidate/candidate-sweep"


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


def _stage_of(step_field: str) -> str:
    """The stage name from a ``step`` value like ``3 (candidate)`` -> ``candidate``.

    The workflow step number can shift, but the parenthesised stage name is
    stable, so match on the name. Returns ``""`` when there is no stage.
    """
    inside = step_field.partition("(")[2].rpartition(")")[0]
    return inside.strip().lower()


def load_candidate_records(tasks_dir: Path) -> list[CandidateRecord]:
    """Every ticket under ``tasks_dir`` whose ``step`` is the candidate stage.

    Read the stage from ``step`` (never the slug). A ``patent_number`` is kept on
    the record so ``evaluate`` can surface an already-granted ticket that has not
    yet been advanced, rather than window it.
    """
    records: list[CandidateRecord] = []
    for path in sorted(tasks_dir.rglob("*.md")):
        fm = reminders.read_frontmatter(path)
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
                filing=reminders.parse_date(filing_raw),
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
    """Split candidate tickets into flags / needs_filing / unreadable / granted.

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
        deadline = reminders.add_months(r.filing, OFFICE_ACTION_MONTHS)
        ages_out = reminders.add_months(r.filing, OFFICE_ACTION_MONTHS + WINDOW_MONTHS)
        if reminders.in_window(today, deadline, ages_out):
            flags.append(Flag(record=r, deadline=deadline, ages_out=ages_out))
    return flags, needs_filing, unreadable, granted


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


def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
    records = load_candidate_records(tasks_dir)
    flags, needs_filing, unreadable, granted = evaluate(records, today)
    report = format_report(records, flags, needs_filing, unreadable, granted, today)
    # Alert order mirrors the original post_alerts: flags (by deadline, slug),
    # then needs_filing (by slug), then unreadable (by slug).
    alerts: list[str] = []
    for flag in sorted(flags, key=lambda f: (f.deadline, f.record.slug)):
        alerts.append(flag_message(flag))
    for r in sorted(needs_filing, key=lambda r: r.slug):
        alerts.append(needs_filing_message(r))
    for r in sorted(unreadable, key=lambda r: r.slug):
        alerts.append(unreadable_message(r))
    return reminders.SweepResult(report=report, alerts=alerts)


def main(argv: list[str] | None = None) -> int:
    return reminders.run(
        _sweep,
        task_slug=SWEEP_TASK_SLUG,
        description="Flag candidate patents reaching their 14-month first-office-action mark.",
        important=True,  # a first-office-action deadline is time-critical for patents
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
