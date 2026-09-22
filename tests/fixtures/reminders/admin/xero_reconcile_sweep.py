#!/usr/bin/env python3
"""Monthly Xero reconciliation nudge — the **period ack** worked example.

A pure nudge: it asks whether last month's books are reconciled and goes quiet
once told they are. It does no detection of its own.

* **period** — the *prior* calendar month as ``YYYY-MM``. On any day of August
  the books under reconciliation are July's, so the period is ``today``'s month
  minus one.
* **satisfied()** — the reconcile is done for a period once a human records
  ``Acked: <period>`` in the reconcile ticket's blackboard. That is an ordinary
  ``key: value`` blackboard line, so the read is core's
  ``period_state.parse_keys`` over ``taskfile.read_blackboard``; there is no
  writer — the human edits the ticket. No live query — the ack is the only
  signal.
* **no window.** A monthly nudge is always inside its own month at runtime; the
  first attempt wrote an ``in_window(today, first_of_month, first_of_next)``
  check here that was a provable tautology, and it is gone. The period being
  recomputed every run is what makes a missed month go quiet at rollover: the
  next month's reconcile surfaces the skipped month's backlog anyway.

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
script reads one month ahead of what this expects. On an August 2026 changeover
an ``Acked: 2026-08`` left by the old script will not satisfy this sweep's
``2026-07`` period, so the first run after the switch fires once. That is the
intended, visible cost of the change.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from coga import reminders
from coga.period_state import parse_keys
from coga.taskfile import read_blackboard

RECONCILE_SLUG = "xero-reconciliation"
SWEEP_TASK_SLUG = "admin/xero-reconciliation"
ACK_KEY = "Acked"


def period_for(today: date) -> str:
    """The month under reconciliation — ``today``'s prior month as ``YYYY-MM``.

    This is the string a human records as ``Acked: <period>`` and the one
    ``satisfied`` recomputes to compare against. The write side (this) and the
    read side (``satisfied``) agreeing on it *is* the ack shape.
    """
    first = today.replace(day=1)
    if first.month == 1:
        prior = first.replace(year=first.year - 1, month=12)
    else:
        prior = first.replace(month=first.month - 1)
    return prior.strftime("%Y-%m")


def reconcile_ticket(tasks_dir: Path) -> Path:
    """The single recurring reconcile ticket this reminder tracks."""
    return tasks_dir / RECONCILE_SLUG / "ticket.md"


def read_ack(ticket: Path) -> str | None:
    """The recorded ``Acked:`` value on ``ticket``'s blackboard, or ``None``.

    A fence-less ticket (a hand-authored reminder predating the single-file
    format) reads as no ack, so the nudge fires rather than crashing.
    """
    text = read_blackboard(ticket, blackboard_required=False)
    return parse_keys(text, [ACK_KEY])[ACK_KEY] or None


def satisfied(ticket: Path, today: date) -> bool:
    """Reconciled for the current period once the ticket carries that ack."""
    return read_ack(ticket) == period_for(today)


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

    acked = read_ack(ticket)
    fires = acked != period

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
