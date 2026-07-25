#!/usr/bin/env python3
"""Brex missing-receipts reminder — live query with a high-water ack.

Retrofit of ``admin/coga/skills/brex/api/missing_receipts.py`` onto
``coga.reminders``. The original owns the query contract; this keeps it and
delegates the periodic-sweep machinery to the engine.

The **query** shape with an **acknowledge-the-backlog** ack layered on:

* The query (``fetch``) returns ``/v3/accounting/records?source_type=CARD``
  records. A record needs a receipt when it is a posted purchase
  (``type == "CARD_EXPENSE_POST"`` — refunds and adjustments are not purchases),
  is over the $40 Manycore threshold, and carries an empty ``receipts`` array.
* Missing receipts are a *running pile*, not a per-period obligation, so a
  calendar snooze does not fit. The ack is a **high-water mark**: it records the
  date the backlog is acknowledged through, and the sweep flags only records
  posted *after* it. No ack -> the whole pile.
* It still self-clears: nothing missing -> nothing flagged, no ack needed.

**The high-water date is ``posted_at``, the settlement timestamp.** A v3
accounting record carries no purchase date — its only dates are ``posted_at``,
``updated_at``, ``due_at`` and ``erp_posting_date`` (see
``tests/fixtures/reminders/recorded/brex/record-shape.json``). A charge made in
the last day or two of a month therefore settles into the next month, exactly as
the original script documents.

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

# Manycore policy: expenses at or below $40 do not require a receipt.
THRESHOLD_USD = 40.0

# Only a posted purchase needs a receipt. Refunds and adjustments arrive as
# other record types.
PURCHASE_TYPE = "CARD_EXPENSE_POST"


@dataclass(frozen=True)
class Expense:
    """The fields of a Brex accounting record this sweep reports on."""

    id: str
    merchant: str
    cardholder: str
    amount: float
    currency: str
    posted: str  # ISO date the record settled, from posted_at

    @property
    def amount_str(self) -> str:
        return f"{self.currency} {self.amount:,.2f}"


def cardholder_name(record: dict) -> str:
    """The cardholder's display name.

    Brex stores trailing whitespace in some name fields; collapse it (the
    original script does the same).
    """
    user = record.get("user") or {}
    raw = " ".join(p for p in [user.get("first_name"), user.get("last_name")] if p)
    return " ".join(raw.split()) or user.get("email") or user.get("id") or "unknown"


def record_amount(record: dict) -> tuple[float | None, str]:
    money = record.get("amount") or {}
    value = money.get("amount")
    if not isinstance(value, (int, float)):
        return None, "USD"
    return float(value), money.get("currency", "USD")


def is_missing_receipt(record: dict) -> bool:
    """Whether ``record`` is a posted purchase with no receipt attached.

    v3 always includes the ``receipts`` array — empty when nothing is attached,
    populated with objects carrying ``download_uris`` when something is.
    """
    return not record.get("receipts")


def to_expense(record: dict) -> Expense | None:
    """``record`` as an :class:`Expense`, or ``None`` when it needs no receipt."""
    if record.get("type") != PURCHASE_TYPE:
        return None
    amount, currency = record_amount(record)
    if amount is None or amount <= THRESHOLD_USD:
        return None
    if not is_missing_receipt(record):
        return None
    return Expense(
        id=record.get("source_id") or record.get("id") or "?",
        merchant=(record.get("vendor") or {}).get("name") or "unknown",
        cardholder=cardholder_name(record),
        amount=amount,
        currency=currency,
        posted=(record.get("posted_at") or "")[:10],
    )


def missing_receipts(records: list[dict]) -> list[Expense]:
    """Every record in ``records`` that still owes a receipt."""
    return [e for e in (to_expense(r) for r in records) if e is not None]


def fetch_card_records() -> list[dict]:
    """Card accounting records from Brex.

    Wired in the admin repo to ``GET /v3/accounting/records`` with
    ``source_type=CARD``, ``limit=100``, and an explicit wide
    ``updated_at[gt]`` bound — Brex's default ``updated_at`` window is narrower
    than any reasonable historical bound and silently returns zero records —
    paging on ``next_cursor`` while ``has_next_page``. Raises here so a fixture
    or standalone run can never silently reach Brex; tests inject a fake.
    """
    raise NotImplementedError(
        "wire fetch_card_records to Brex in the admin repo, or inject it in tests"
    )


def acked_through(ticket: Path) -> date | None:
    """The high-water date the backlog is acknowledged through, or ``None``.

    Stored as ``Acked: <YYYY-MM-DD>`` in the reminder's own blackboard — the same
    ack helper the other reminders use, carrying a date rather than a period.
    """
    return reminders.parse_date(reminders.read_ack(ticket) or "")


def flagged(missing: list[Expense], ack_through: date | None) -> list[Expense]:
    """The subset still worth surfacing: posted after the ack high-water.

    No ack -> the whole pile. An unparseable ``posted`` date fails safe
    (surfaced), so a receipt is never muted just because its date is odd.
    """
    if ack_through is None:
        return list(missing)
    out = []
    for e in missing:
        d = reminders.parse_date(e.posted)
        if d is None or d > ack_through:
            out.append(e)
    return out


def format_report(
    missing: list[Expense], flags: list[Expense], ack_through: date | None, today: date
) -> str:
    header = f"Brex missing-receipts check — as of {today.isoformat()}"
    if not missing:
        return f"{header}\n  all card expenses over ${THRESHOLD_USD:,.0f} have receipts."
    lines = [header, f"  {len(missing)} expense(s) missing a receipt total."]
    if ack_through is not None:
        lines.append(
            f"  {len(missing) - len(flags)} acknowledged through {ack_through.isoformat()}."
        )
    if not flags:
        lines.append("  nothing new since the last ack.")
        return "\n".join(lines)
    lines.append(f"  {len(flags)} to act on:")
    for e in sorted(flags, key=lambda e: (e.posted, e.id)):
        lines.append(
            f"    - {e.posted}  {e.merchant}  {e.amount_str}  ({e.cardholder})"
        )
    return "\n".join(lines)


def alert_message(flags: list[Expense]) -> str:
    """One summary alert per run — not one per expense — to stay low-noise."""
    oldest = min(flags, key=lambda e: e.posted)
    return (
        f"🧾 {len(flags)} Brex expense(s) missing a receipt "
        f"(oldest {oldest.posted}, {oldest.merchant} {oldest.amount_str}). "
        f"Add receipts in Brex, or ack to acknowledge the backlog."
    )


def build_sweep(fetch=None):
    """The sweep with the Brex query injectable (see the module docstring)."""

    def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
        records = (fetch or fetch_card_records)()
        missing = missing_receipts(records)
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
