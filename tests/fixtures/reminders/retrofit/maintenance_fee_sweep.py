#!/usr/bin/env python3
"""Utility maintenance-fee window sweep — engine-backed retrofit.

Behaviourally identical stdout to the standalone ``golden/maintenance_fee_sweep.py``
for the same ``--today`` / ``--tasks-dir``: the shared machinery (frontmatter
reading, date-window math, the in-window check, the notify plumbing, and the CLI
harness) now comes from ``coga.reminders``. Only the unique 20% stays here — the
record dataclass + selector, the three maintenance windows, the
``patent_maintenance_paid == N`` satisfied rule, and the report/message formats.

This is the worked parity example for the reminder-engine battery. The live
patents migration is a downstream follow-up (this PR only vendors it as a
fixture; it does not edit the patents repo).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from coga import reminders

# (window number, grant offset in years). Each window spans
# [grant + offset, grant + offset + 1) — i.e. the full 12 months.
WINDOWS: list[tuple[int, int]] = [(1, 3), (2, 7), (3, 11)]

# `coga slack --task` needs a real ticket for the [project]/[owner] prefix; under
# a coga launch that's this script's own task ($COGA_TASK_SLUG), and a standalone
# run falls back to this sweep ticket slug.
SWEEP_TASK_SLUG = "repo/utility/maintenance-fee-sweep"


@dataclass(frozen=True)
class PatentRecord:
    slug: str
    title: str
    number: str
    granted: date | None
    paid: int | None


@dataclass(frozen=True)
class Flag:
    record: PatentRecord
    window: int
    opens: date
    closes: date


def _parse_paid(raw: str) -> int | None:
    """``patent_maintenance_paid`` as an int; blank/garbage -> None (unpaid)."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def load_patent_records(tasks_dir: Path) -> list[PatentRecord]:
    """Every ticket under ``tasks_dir`` that carries a non-empty ``patent_number``."""
    records: list[PatentRecord] = []
    for path in sorted(tasks_dir.rglob("*.md")):
        fm = reminders.read_frontmatter(path)
        number = fm.get("patent_number", "").strip()
        if not number:
            continue
        records.append(
            PatentRecord(
                slug=fm.get("slug", "").strip() or path.stem,
                title=fm.get("title", "").strip(),
                number=number,
                granted=reminders.parse_date(fm.get("patent_granted", "")),
                paid=_parse_paid(fm.get("patent_maintenance_paid", "")),
            )
        )
    return records


def evaluate(
    records: list[PatentRecord], today: date
) -> tuple[list[Flag], list[tuple[PatentRecord, int]]]:
    """Split granted patents into flagged (in a window, fee not recorded) and
    suppressed (in a window but ``patent_maintenance_paid == N``)."""
    flags: list[Flag] = []
    suppressed: list[tuple[PatentRecord, int]] = []
    for r in records:
        if r.granted is None:
            continue
        for window, offset in WINDOWS:
            opens = reminders.add_years(r.granted, offset)
            closes = reminders.add_years(r.granted, offset + 1)
            if reminders.in_window(today, opens, closes):
                # satisfied() for this reminder is auto-detect: the recorded fee
                # matches this window number.
                if r.paid == window:
                    suppressed.append((r, window))
                else:
                    flags.append(Flag(record=r, window=window, opens=opens, closes=closes))
    return flags, suppressed


def format_report(
    records: list[PatentRecord],
    flags: list[Flag],
    suppressed: list[tuple[PatentRecord, int]],
    missing_grant: list[PatentRecord],
    today: date,
) -> str:
    granted = [r for r in records if r.granted is not None]
    lines = [
        f"Maintenance-fee window sweep — as of {today.isoformat()}",
        f"Checked {len(granted)} granted patents ({len(records)} with a patent number).",
    ]
    if missing_grant:
        slugs = ", ".join(r.slug for r in missing_grant)
        lines.append(f"  ! {len(missing_grant)} have a patent number but no grant date (skipped): {slugs}")
    if suppressed:
        lines.append(f"  - {len(suppressed)} in a window but already recorded paid (not flagged).")

    if not flags:
        lines.append("\nFlagged (0): nothing in an unpaid window this run.")
        return "\n".join(lines)

    lines.append(f"\nFlagged ({len(flags)}):")
    for f in sorted(flags, key=lambda f: (f.opens, f.record.slug)):
        offset = WINDOWS[f.window - 1][1]
        paid = "blank" if f.record.paid is None else f.record.paid
        lines.append(
            f"  * {f.record.slug}  #{f.record.number}  "
            f"— Window {f.window} (grant+{offset}yr): open {f.opens.isoformat()} "
            f"-> {f.closes.isoformat()}; fee {f.window} not recorded "
            f"(patent_maintenance_paid={paid})"
        )
    return "\n".join(lines)


def flag_message(flag: Flag) -> str:
    """One-line coga-important alert for a flagged patent."""
    offset = WINDOWS[flag.window - 1][1]
    paid = "blank" if flag.record.paid is None else flag.record.paid
    return (
        f"⚠️ Maintenance fee window open — {flag.record.slug} #{flag.record.number}: "
        f"Window {flag.window} (grant+{offset}yr), open {flag.opens.isoformat()} → "
        f"{flag.closes.isoformat()}; fee {flag.window} not recorded "
        f"(patent_maintenance_paid={paid})."
    )


def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
    records = load_patent_records(tasks_dir)
    missing_grant = [r for r in records if r.granted is None]
    flags, suppressed = evaluate(records, today)
    report = format_report(records, flags, suppressed, missing_grant, today)
    alerts = [
        flag_message(f) for f in sorted(flags, key=lambda f: (f.opens, f.record.slug))
    ]
    return reminders.SweepResult(report=report, alerts=alerts)


def main(argv: list[str] | None = None) -> int:
    return reminders.run(
        _sweep,
        task_slug=SWEEP_TASK_SLUG,
        description="Flag utility patents inside an unpaid maintenance-fee window.",
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
