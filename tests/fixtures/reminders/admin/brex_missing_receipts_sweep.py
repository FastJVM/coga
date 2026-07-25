#!/usr/bin/env python3
"""Brex missing-receipts reminder — a reference live-query admin sweep.

The **query** shape: `satisfied()` is a *live source query*, not a ticket field
and not an ack. Each run asks Brex which card expenses still lack a receipt; the
reminder fires while that set is non-empty and goes quiet the moment it clears.

Two things fall away versus the patents/ack sweeps:

* **No date window.** `in_window` is vacuous for a pure-query reminder — the
  source is the whole truth — so `fire` is simply "the query returned work".
* **No ack.** There is nothing to record; adding the receipt in Brex *is* the
  satisfying action, and the next run sees it.

Posts to the **normal** coga channel (`important=False`) — a missing receipt is
routine bookkeeping, not a hard deadline. The Brex call is injected (`fetch`) so
the fixture and its tests never touch Brex; the admin repo wires `fetch` to the
real query.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from coga import reminders

SWEEP_TASK_SLUG = "admin/brex-missing-receipts"


@dataclass(frozen=True)
class Expense:
    id: str
    merchant: str
    amount: str  # display string, e.g. "$120.00"
    incurred: str  # ISO date the expense was incurred


def fetch_missing_receipts() -> list[Expense]:
    """Card expenses still missing a receipt, from Brex.

    Wired to the real Brex query in the admin repo. Raises here so a fixture or
    standalone run can never silently reach Brex — tests inject a fake.
    """
    raise NotImplementedError(
        "wire fetch_missing_receipts to Brex in the admin repo, or inject it in tests"
    )


def format_report(missing: list[Expense], today: date) -> str:
    if not missing:
        return (
            f"Brex missing-receipts check — as of {today.isoformat()}\n"
            f"  all card expenses have receipts."
        )
    lines = [
        f"Brex missing-receipts check — as of {today.isoformat()}",
        f"  {len(missing)} expense(s) missing a receipt:",
    ]
    for e in sorted(missing, key=lambda e: (e.incurred, e.id)):
        lines.append(f"    - {e.incurred}  {e.merchant}  {e.amount}  (id {e.id})")
    return "\n".join(lines)


def alert_message(missing: list[Expense]) -> str:
    """One summary alert per run — not one per expense — to stay low-noise."""
    oldest = min(missing, key=lambda e: e.incurred)
    return (
        f"🧾 {len(missing)} Brex expense(s) missing a receipt "
        f"(oldest {oldest.incurred}, {oldest.merchant} {oldest.amount}). "
        f"Add receipts in Brex."
    )


def build_sweep(fetch=None):
    """The sweep with the Brex query injectable.

    Passing ``fetch`` overrides the source directly (tests); leaving it ``None``
    resolves the module-level ``fetch_missing_receipts`` at call time, so it can
    also be monkeypatched.
    """

    def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
        missing = (fetch or fetch_missing_receipts)()
        report = format_report(missing, today)
        # Pure query: fire = the source still reports work to do.
        alerts = [alert_message(missing)] if missing else []
        return reminders.SweepResult(report=report, alerts=alerts)

    return _sweep


def main(argv: list[str] | None = None) -> int:
    # important defaults to False -> normal coga channel.
    return reminders.run(
        build_sweep(),
        task_slug=SWEEP_TASK_SLUG,
        description="Flag Brex card expenses still missing a receipt.",
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
