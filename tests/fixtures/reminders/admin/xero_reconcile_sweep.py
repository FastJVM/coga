#!/usr/bin/env python3
"""Monthly Xero reconciliation nudge — the reference ack-based admin sweep.

A pure nudge: it asks whether last month's books are reconciled and goes quiet
once told they are. It does no detection of its own.

* **period** — the *prior* calendar month as ``YYYY-MM``. On any day of August
  the books under reconciliation are July's, so the period is ``today``'s month
  minus one.
* **satisfied()** — the reconcile is done for a period once a human records
  ``Acked: <period>`` in the reconcile ticket's blackboard (``coga.reminders``'
  sanctioned cross-run state home). No live query — a human ack is the only
  signal.
* **quiet at rollover** — the period is recomputed every run, so a missed month
  simply stops nagging when the month turns over (the window closes and the
  period advances). That is intentional: the next month's reconcile surfaces the
  skipped month's backlog anyway, so there is nothing to keep firing about.

Relationship to the deployed script
-----------------------------------
``admin/coga/skills/xero/reconcile-reminder/remind.py`` is the reminder this
replaces. It is **not** a parity oracle, because this sweep deliberately differs
from it on two points:

* **It drops the detection step.** The deployed script shells out to a
  Playwright-driven ``xero/reconcile`` run and posts a per-account backlog table.
  That machinery is being retired; the nudge is the intended replacement, so
  there is no table to reproduce.
* **The period runs one month behind it.** The deployed script acks
  ``current_month()``; this acks the prior month. A deliberate change, not drift
  — reconciling August's books during August is not a thing you can finish, so
  the ack now names the month whose books are actually closed.

The second point means recorded ``Acked: YYYY-MM`` state written by the old
script reads one month ahead of what this expects. On a August 2026 changeover an
``Acked: 2026-08`` left by the old script will not satisfy this sweep's
``2026-07`` period, so the first run after the switch fires once. That is the
intended, visible cost of the change.

Verified behaviourally (see ``test_reminders.py``) plus a recorded live run under
``tests/fixtures/reminders/recorded/xero/``.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from coga import reminders

RECONCILE_SLUG = "xero-reconciliation"
SWEEP_TASK_SLUG = "admin/xero-reconciliation"


def period_for(today: date) -> str:
    """The month under reconciliation — ``today``'s prior month as ``YYYY-MM``.

    This is the string a human records as ``Acked: <period>`` and the one
    ``satisfied`` recomputes to compare against. The write side (this) and the
    read side (``satisfied``) agreeing on it *is* the ack shape.
    """
    prior = reminders.add_months(today.replace(day=1), -1)
    return prior.strftime("%Y-%m")


def reconcile_ticket(tasks_dir: Path) -> Path:
    """The single recurring reconcile ticket this reminder tracks."""
    return tasks_dir / RECONCILE_SLUG / "ticket.md"


def satisfied(ticket: Path, today: date) -> bool:
    """Reconciled for the current period once the ticket carries that ack."""
    return reminders.read_ack(ticket) == period_for(today)


def reconcile_message(period: str) -> str:
    """One-line alert for an unreconciled month (posts to the normal coga channel)."""
    return (
        f"⚠️ Xero reconciliation due — reconcile {period}'s books, then record "
        f"`Acked: {period}` on the {RECONCILE_SLUG} ticket."
    )


def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
    ticket = reconcile_ticket(tasks_dir)
    period = period_for(today)

    if not ticket.exists():
        return reminders.SweepResult(
            report=(
                f"Xero reconciliation reminder — as of {today.isoformat()}\n"
                f"  ! reconcile ticket not found at {RECONCILE_SLUG}/ticket.md"
            ),
            alerts=[],
        )

    # Window: a month's reconcile is live throughout the *following* month —
    # opens on its 1st, closes on the next 1st (close-exclusive). Recomputed each
    # run, so at rollover the sweep asks about the new prior month instead of
    # nagging about a missed one forever. For a monthly reminder this window is
    # always open at runtime; the ack is the operative satisfied() gate — which
    # is exactly why this sweep is the ack reference.
    opens = today.replace(day=1)
    closes = reminders.add_months(opens, 1)
    acked = reminders.read_ack(ticket)
    fires = reminders.in_window(today, opens, closes) and acked != period

    ack_note = f"last ack {acked}" if acked else "no ack recorded"
    report = (
        f"Xero reconciliation reminder — as of {today.isoformat()}\n"
        f"  reconcile {period} (prior month): "
        f"{'DUE' if fires else 'done'} ({ack_note})"
    )
    alerts = [reconcile_message(period)] if fires else []
    return reminders.SweepResult(report=report, alerts=alerts)


def main(argv: list[str] | None = None) -> int:
    return reminders.run(
        _sweep,
        task_slug=SWEEP_TASK_SLUG,
        description="Remind to reconcile last month's Xero books until acked.",
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
