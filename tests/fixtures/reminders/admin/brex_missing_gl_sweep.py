#!/usr/bin/env python3
"""Brex missing-GL-code reminder — the second live-query admin sweep.

Structurally identical to ``brex_missing_receipts_sweep.py`` (the query shape),
differing only in the source query and its labels: it asks Brex which card
expenses still lack a general-ledger (GL) account code, and fires while that set
is non-empty. No window, no ack — the source is the whole truth.

That these two sweeps are the *same* shape modulo the query is the point: it is
the evidence that a query-reminder helper could later live in the engine itself
(two real consumers). For now they stay as fixtures. Posts to the **normal**
coga channel — uncategorised expenses are routine bookkeeping, not a deadline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from coga import reminders

SWEEP_TASK_SLUG = "admin/brex-missing-gl"


@dataclass(frozen=True)
class Expense:
    id: str
    merchant: str
    amount: str  # display string, e.g. "$120.00"
    incurred: str  # ISO date the expense was incurred


def fetch_missing_gl() -> list[Expense]:
    """Card expenses still missing a GL account code, from Brex.

    Wired to the real Brex query in the admin repo. Raises here so a fixture or
    standalone run can never silently reach Brex — tests inject a fake.
    """
    raise NotImplementedError(
        "wire fetch_missing_gl to Brex in the admin repo, or inject it in tests"
    )


def format_report(missing: list[Expense], today: date) -> str:
    if not missing:
        return (
            f"Brex missing-GL-code check — as of {today.isoformat()}\n"
            f"  all card expenses have a GL code."
        )
    lines = [
        f"Brex missing-GL-code check — as of {today.isoformat()}",
        f"  {len(missing)} expense(s) missing a GL code:",
    ]
    for e in sorted(missing, key=lambda e: (e.incurred, e.id)):
        lines.append(f"    - {e.incurred}  {e.merchant}  {e.amount}  (id {e.id})")
    return "\n".join(lines)


def alert_message(missing: list[Expense]) -> str:
    """One summary alert per run — not one per expense — to stay low-noise."""
    oldest = min(missing, key=lambda e: e.incurred)
    return (
        f"🏷️ {len(missing)} Brex expense(s) missing a GL code "
        f"(oldest {oldest.incurred}, {oldest.merchant} {oldest.amount}). "
        f"Assign GL codes in Brex."
    )


def build_sweep(fetch=None):
    """The sweep with the Brex query injectable (see the receipts sweep)."""

    def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
        missing = (fetch or fetch_missing_gl)()
        report = format_report(missing, today)
        alerts = [alert_message(missing)] if missing else []
        return reminders.SweepResult(report=report, alerts=alerts)

    return _sweep


def main(argv: list[str] | None = None) -> int:
    # important defaults to False -> normal coga channel.
    return reminders.run(
        build_sweep(),
        task_slug=SWEEP_TASK_SLUG,
        description="Flag Brex card expenses still missing a GL account code.",
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
