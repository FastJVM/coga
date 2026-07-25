#!/usr/bin/env python3
"""Brex missing-GL-code reminder — the second live-query + high-water-ack sweep.

Structurally identical to ``brex_missing_receipts_sweep.py`` (query + high-water
ack), differing only in the source query and its labels: it asks Brex which card
expenses still lack a general-ledger (GL) account code.

In practice this one usually self-clears — you finish assigning codes, the pile
hits zero, and it goes quiet on its own with no ack. The ack is the escape hatch
for a batch you are deferring (same mechanism as receipts, which more often
leans on it because its backlog may never clear).

That these two sweeps are the *same* shape modulo the query is the point: it is
the evidence a query-reminder helper could later live in the engine (two real
consumers). For now they stay as fixtures. Posts to the **normal** coga channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from coga import reminders

GL_SLUG = "brex-missing-gl"
SWEEP_TASK_SLUG = f"admin/{GL_SLUG}"


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


def acked_through(ticket: Path) -> date | None:
    """The high-water date the backlog is acknowledged through, or ``None``."""
    return reminders.parse_date(reminders.read_ack(ticket) or "")


def flagged(missing: list[Expense], ack_through: date | None) -> list[Expense]:
    """The subset still worth surfacing: incurred after the ack high-water.

    No ack -> the whole pile. An unparseable incurred date fails safe (surfaced).
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
    header = f"Brex missing-GL-code check — as of {today.isoformat()}"
    if not missing:
        return f"{header}\n  all card expenses have a GL code."
    lines = [header, f"  {len(missing)} expense(s) missing a GL code total."]
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
        f"🏷️ {len(flags)} Brex expense(s) missing a GL code "
        f"(oldest {oldest.incurred}, {oldest.merchant} {oldest.amount}). "
        f"Assign GL codes in Brex, or ack to acknowledge the backlog."
    )


def build_sweep(fetch=None):
    """The sweep with the Brex query injectable (see the receipts sweep)."""

    def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
        missing = (fetch or fetch_missing_gl)()
        ack_through = acked_through(tasks_dir / GL_SLUG / "ticket.md")
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
        description="Flag Brex card expenses missing a GL code (new since the last ack).",
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
