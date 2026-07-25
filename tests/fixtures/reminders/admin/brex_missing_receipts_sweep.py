#!/usr/bin/env python3
"""Brex missing-receipts reminder — live query with a high-water ack.

The **query** shape with an **acknowledge-the-backlog** ack layered on:

* The query (``fetch``) each run returns the card expenses still missing a
  receipt — the whole pile, old and new.
* Missing receipts are a *running pile*, not a per-period obligation, so a
  calendar snooze does not fit (on a monthly run it would expire exactly when the
  next run fires and never quiet anything). Instead the ack is a **high-water
  mark**: it records the date the backlog is acknowledged through, and the sweep
  flags only expenses incurred *after* it. No ack -> the whole pile (the plain
  query); ack the pile and only genuinely new gaps surface next run.
* It still self-clears: nothing missing -> nothing flagged, no ack needed.

Posts to the **normal** coga channel — a missing receipt is routine bookkeeping,
not a hard deadline. The Brex call is injected (``fetch``) so the fixture and its
tests never touch Brex; the admin repo wires it to the real query.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from coga import reminders

RECEIPTS_SLUG = "brex-missing-receipts"
SWEEP_TASK_SLUG = f"admin/{RECEIPTS_SLUG}"


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


def acked_through(ticket: Path) -> date | None:
    """The high-water date the backlog is acknowledged through, or ``None``.

    Stored as ``Acked: <YYYY-MM-DD>`` in the reminder's own blackboard — the same
    ack helper the other reminders use, carrying a date rather than a period.
    """
    return reminders.parse_date(reminders.read_ack(ticket) or "")


def flagged(missing: list[Expense], ack_through: date | None) -> list[Expense]:
    """The subset still worth surfacing: incurred after the ack high-water.

    No ack -> the whole pile. An unparseable incurred date fails safe (surfaced),
    so a receipt is never muted just because its date is odd.
    """
    if ack_through is None:
        return list(missing)
    out = []
    for e in missing:
        d = reminders.parse_date(e.incurred)
        if d is None or d > ack_through:
            out.append(e)
    return out


def format_report(
    missing: list[Expense], flags: list[Expense], ack_through: date | None, today: date
) -> str:
    header = f"Brex missing-receipts check — as of {today.isoformat()}"
    if not missing:
        return f"{header}\n  all card expenses have receipts."
    lines = [header, f"  {len(missing)} expense(s) missing a receipt total."]
    if ack_through is not None:
        lines.append(
            f"  {len(missing) - len(flags)} acknowledged through {ack_through.isoformat()}."
        )
    if not flags:
        lines.append("  nothing new since the last ack.")
        return "\n".join(lines)
    lines.append(f"  {len(flags)} to act on:")
    for e in sorted(flags, key=lambda e: (e.incurred, e.id)):
        lines.append(f"    - {e.incurred}  {e.merchant}  {e.amount}  (id {e.id})")
    return "\n".join(lines)


def alert_message(flags: list[Expense]) -> str:
    """One summary alert per run — not one per expense — to stay low-noise."""
    oldest = min(flags, key=lambda e: e.incurred)
    return (
        f"🧾 {len(flags)} Brex expense(s) missing a receipt "
        f"(oldest {oldest.incurred}, {oldest.merchant} {oldest.amount}). "
        f"Add receipts in Brex, or ack to acknowledge the backlog."
    )


def build_sweep(fetch=None):
    """The sweep with the Brex query injectable (see the module docstring)."""

    def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
        missing = (fetch or fetch_missing_receipts)()
        ack_through = acked_through(tasks_dir / RECEIPTS_SLUG / "ticket.md")
        flags = flagged(missing, ack_through)
        report = format_report(missing, flags, ack_through, today)
        alerts = [alert_message(flags)] if flags else []
        return reminders.SweepResult(report=report, alerts=alerts)

    return _sweep


def main(argv: list[str] | None = None) -> int:
    # important defaults to False -> normal coga channel.
    return reminders.run(
        build_sweep(),
        task_slug=SWEEP_TASK_SLUG,
        description="Flag Brex card expenses missing a receipt (new since the last ack).",
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
