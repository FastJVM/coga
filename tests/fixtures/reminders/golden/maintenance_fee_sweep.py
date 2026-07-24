#!/usr/bin/env python3
"""Utility maintenance-fee window sweep.

Reads the local patent tickets, selects the granted ones (any ticket carrying a
non-empty ``patent_number``), and flags every patent that is currently inside a
maintenance-fee window whose fee is not yet recorded as paid — so no fee lapses.

Maintenance-fee windows open at grant + 3 / 7 / 11 years and each stays open for
12 months::

    Window 1  [grant + 3yr,  grant + 4yr)
    Window 2  [grant + 7yr,  grant + 8yr)
    Window 3  [grant + 11yr, grant + 12yr)

A patent inside Window N is flagged **unless** ``patent_maintenance_paid == N``
(a blank/missing value counts as unpaid, so a patent is never skipped on missing
state — over-alert beats miss). This sweep only *reads* ``patent_maintenance_paid``;
it never decides whether a fee was actually paid (a separate USPTO sweep does that)
and it never mutates a ticket.

Run it through coga (``coga launch repo/utility/maintenance-fee-sweep``), or
standalone for testing::

    python maintenance_fee_sweep.py [--today YYYY-MM-DD] [--tasks-dir PATH]

Each flagged patent is announced to the coga-important Slack channel via
``coga slack --important`` (needs ``COGA_IMPORTANT_WEBHOOK_URL`` configured). A
run against a ``--tasks-dir`` of fake tickets only posts about those, so it is
safe for testing.

It has no third-party dependencies beyond the ``coga`` CLI on PATH, so it runs
under any Python 3.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# (window number, grant offset in years). Each window spans
# [grant + offset, grant + offset + 1) — i.e. the full 12 months.
WINDOWS: list[tuple[int, int]] = [(1, 3), (2, 7), (3, 11)]


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


def add_years(d: date, years: int) -> date:
    """``d`` plus ``years``, clamping Feb 29 to Feb 28 in a non-leap target year."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29 -> a year with no Feb 29
        return d.replace(year=d.year + years, day=28)


def _read_frontmatter(path: Path) -> dict[str, str]:
    """Top-level scalar frontmatter fields of a ticket, as strings.

    Deliberately dependency-free: we only need a handful of simple scalar keys
    (``patent_number``, ``patent_granted``, ``patent_maintenance_paid``, ``slug``,
    ``title``). We read the block between the first two ``---`` fences and keep
    only column-0 ``key: value`` lines, so nested/indented keys (lists, the
    workflow block) are ignored. Returns ``{}`` when there is no frontmatter.
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


def _parse_paid(raw: str) -> int | None:
    """``patent_maintenance_paid`` as an int; blank/garbage -> None (unpaid)."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_granted(raw: str) -> date | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def load_patent_records(tasks_dir: Path) -> list[PatentRecord]:
    """Every ticket under ``tasks_dir`` that carries a non-empty ``patent_number``."""
    records: list[PatentRecord] = []
    for path in sorted(tasks_dir.rglob("*.md")):
        fm = _read_frontmatter(path)
        number = fm.get("patent_number", "").strip()
        if not number:
            continue
        records.append(
            PatentRecord(
                slug=fm.get("slug", "").strip() or path.stem,
                title=fm.get("title", "").strip(),
                number=number,
                granted=_parse_granted(fm.get("patent_granted", "")),
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
            opens = add_years(r.granted, offset)
            closes = add_years(r.granted, offset + 1)
            if opens <= today < closes:
                if r.paid == window:
                    suppressed.append((r, window))
                else:
                    flags.append(Flag(record=r, window=window, opens=opens, closes=closes))
    return flags, suppressed


def default_tasks_dir() -> Path:
    """The coga tasks directory: from ``$COGA_COGA_OS_ROOT`` when coga launches
    the script, else derived from this file's location for standalone runs."""
    env_root = os.environ.get("COGA_COGA_OS_ROOT")
    coga_os_root = Path(env_root) if env_root else Path(__file__).resolve().parents[4]
    return coga_os_root / "tasks"


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


# Where notifications land: each flagged patent is posted to the coga-important
# channel via `coga slack … --important`. `--task` needs a real ticket for the
# [project]/[owner] prefix; under a coga launch that's this script's own task
# ($COGA_TASK_SLUG), and a standalone run falls back to the sweep ticket slug.
SWEEP_TASK_SLUG = "repo/utility/maintenance-fee-sweep"


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


def post_flags(flags: list[Flag]) -> int:
    """Post each flag to the coga-important channel; return the failure count.

    Shells out to `coga slack --important` (no coga import — this script stays
    standalone). coga reads COGA_IMPORTANT_WEBHOOK_URL from the environment and
    fails loud if it isn't set, so a missing webhook surfaces as a failure here.
    """
    task = os.environ.get("COGA_TASK_SLUG") or SWEEP_TASK_SLUG
    failures = 0
    for flag in sorted(flags, key=lambda f: (f.opens, f.record.slug)):
        result = subprocess.run(
            ["coga", "slack", "--task", task,
             "--message", flag_message(flag), "--important"],
        )
        if result.returncode != 0:
            failures += 1
            print(f"  ! failed to post alert for {flag.record.slug}", file=sys.stderr)
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flag utility patents inside an unpaid maintenance-fee window."
    )
    parser.add_argument(
        "--today", type=date.fromisoformat, default=None,
        help="Override today's date (YYYY-MM-DD) — for testing.",
    )
    parser.add_argument(
        "--tasks-dir", type=Path, default=None,
        help="Override the tasks directory (defaults to the coga tasks dir).",
    )
    args = parser.parse_args(argv)

    today = args.today or date.today()
    tasks_dir = args.tasks_dir or default_tasks_dir()
    if not tasks_dir.is_dir():
        print(f"tasks directory not found: {tasks_dir}", file=sys.stderr)
        return 1

    records = load_patent_records(tasks_dir)
    missing_grant = [r for r in records if r.granted is None]
    flags, suppressed = evaluate(records, today)
    print(format_report(records, flags, suppressed, missing_grant, today))
    if flags:
        print(
            f"\nPosting {len(flags)} alert(s) to the coga-important channel …",
            file=sys.stderr,
        )
        if post_flags(flags):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
