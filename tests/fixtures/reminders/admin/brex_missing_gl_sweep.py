#!/usr/bin/env python3
"""Brex missing-GL-code reminder — the **live query, no window** worked example.

Retrofit of ``admin/coga/skills/brex/missing-gl/missing_gl.py`` onto the
``coga.reminders`` harness. ``fire`` is simply "the query returned work": no
date window, no period, and the pile self-clears at zero. Structurally the
same as ``brex_missing_receipts_sweep.py`` (query, with the same high-water ack
available as an escape hatch), differing in three ways that come straight from
the original:

* **The probe.** Per the v3 schema the Debit GL is the only settable GL on a CARD
  record — the Credit line is implicitly the Brex card-liability account and
  carries no accounting fields. So the sweep walks ``line_items`` -> the
  ``DEBIT`` line -> ``accounting_field_values`` -> the ``GL_ACCOUNT`` entry, and
  calls it missing when ``brex_field_value_id`` is unset. This matches the
  dashboard's ``accountingFlag:MISSING_GL_ACCOUNT``.
* **A fiscal-year horizon.** Only charges from the currently-open fiscal year are
  surfaced. Missing GL on a closed-year charge is not actionable — it would mean
  re-opening the books. The cutoff is January 1 in ``America/Los_Angeles`` so it
  is the company's January 1, not UTC's.
* **No amount threshold.** Every charge needs a GL code, however small.

Unlike receipts this one usually self-clears — you finish assigning codes, the
pile hits zero, and it goes quiet with no ack. The ack is the escape hatch for a
batch you are deferring.

The two Brex sweeps share the record shaping and the high-water ack almost
line for line. That duplication is real, but it is *between two admin-repo
scripts*, so factoring a sibling helper out is the admin repo's call — not a
reason to widen the harness. Posts to the **normal** coga channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from coga import reminders
from coga.period_state import parse_keys
from coga.taskfile import read_blackboard

GL_SLUG = "brex-missing-gl"
SWEEP_TASK_SLUG = f"admin/{GL_SLUG}"
ACK_KEY = "Acked"

# The company's fiscal calendar, so "January 1" is its January 1, not UTC's.
FISCAL_TZ = ZoneInfo("America/Los_Angeles")

GL_FIELD = "GL_ACCOUNT"
DEBIT = "DEBIT"


@dataclass(frozen=True)
class Expense:
    """The fields of a Brex accounting record this sweep reports on."""

    id: str
    merchant: str
    cardholder: str
    amount: float | None  # None when Brex sent no numeric amount
    currency: str
    posted: str  # ISO date the record settled, from posted_at

    @property
    def amount_str(self) -> str:
        if self.amount is None:
            return f"{self.currency} ?"
        return f"{self.currency} {self.amount:,.2f}"


def fiscal_year_cutoff(today: date) -> str:
    """``today``'s fiscal year start as a UTC RFC-3339 stamp.

    Derived from ``today`` rather than import-time wall-clock so a ``--today``
    run is reproducible — the original computes it at module import.
    """
    local_start = datetime(today.year, 1, 1, tzinfo=FISCAL_TZ)
    return local_start.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def in_scope(record: dict, cutoff: str) -> bool:
    """Whether ``record`` settled inside the currently-open fiscal year."""
    return (record.get("posted_at") or "") >= cutoff


def is_missing_gl(record: dict) -> bool:
    """Whether ``record``'s Debit line has no GL account set.

    Fails safe: a record with no Debit line, no accounting fields, or no
    ``GL_ACCOUNT`` entry is surfaced rather than silently dropped, so a malformed
    record gets a human's attention.
    """
    debit = next(
        (li for li in record.get("line_items") or [] if li.get("type") == DEBIT),
        None,
    )
    if not debit:
        return True
    values = debit.get("accounting_field_values") or []
    if not values:
        return True
    gl = next((f for f in values if f.get("remote_field_id") == GL_FIELD), None)
    if not gl:
        return True
    return gl.get("brex_field_value_id") is None


def cardholder_name(record: dict) -> str:
    """The cardholder's display name, with Brex's trailing whitespace collapsed."""
    user = record.get("user") or {}
    raw = " ".join(p for p in [user.get("first_name"), user.get("last_name")] if p)
    return " ".join(raw.split()) or user.get("email") or user.get("id") or "unknown"


def record_amount(record: dict) -> tuple[float | None, str]:
    """The record's ``(amount, currency)``; ``None`` when Brex sent no number.

    Same rule as the receipts sweep. There is no threshold here, so ``None``
    only changes how the amount is displayed (``?``), never whether the record
    is surfaced.
    """
    money = record.get("amount") or {}
    value = money.get("amount")
    amount = float(value) if isinstance(value, (int, float)) else None
    return amount, money.get("currency", "USD")


def to_expense(record: dict) -> Expense:
    amount, currency = record_amount(record)
    return Expense(
        id=record.get("source_id") or record.get("id") or "?",
        merchant=(record.get("vendor") or {}).get("name") or "unknown",
        cardholder=cardholder_name(record),
        amount=amount,
        currency=currency,
        posted=(record.get("posted_at") or "")[:10],
    )


def missing_gl(records: list[dict], today: date) -> list[Expense]:
    """Every in-scope record in ``records`` whose Debit GL is unset."""
    cutoff = fiscal_year_cutoff(today)
    return [
        to_expense(r)
        for r in records
        if in_scope(r, cutoff) and is_missing_gl(r)
    ]


def fetch_card_records() -> list[dict]:
    """Card accounting records from Brex.

    Wired in the admin repo to the same paged ``GET /v3/accounting/records``
    query the receipts sweep uses (``source_type=CARD``, explicit wide
    ``updated_at[gt]`` bound). Read-only — the sweep never writes to Brex, and
    Brex's API can detect a missing GL but cannot assign one. Raises here so a
    fixture or standalone run can never silently reach Brex.
    """
    raise NotImplementedError(
        "wire fetch_card_records to Brex in the admin repo, or inject it in tests"
    )


def acked_through(ticket: Path) -> date | None:
    """The high-water date the backlog is acknowledged through, or ``None``.

    Stored as ``Acked: <YYYY-MM-DD>`` on the reminder's own blackboard — an
    ordinary ``key: value`` line, read with core's ``period_state.parse_keys``
    over ``taskfile.read_blackboard`` and written by the human who acknowledges
    it. A missing or fence-less ticket, and an unparseable value, all read as no
    ack: the whole pile surfaces rather than being muted by accident.
    """
    if not ticket.is_file():
        return None
    text = read_blackboard(ticket, blackboard_required=False)
    raw = (parse_keys(text, [ACK_KEY])[ACK_KEY] or "").strip()
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def flagged(missing: list[Expense], ack_through: date | None) -> list[Expense]:
    """The subset still worth surfacing: posted after the ack high-water.

    No ack -> the whole pile. An unparseable ``posted`` date fails safe.
    """
    if ack_through is None:
        return list(missing)
    out = []
    for e in missing:
        try:
            d = date.fromisoformat(e.posted)
        except ValueError:
            d = None
        if d is None or d > ack_through:
            out.append(e)
    return out


def format_report(
    missing: list[Expense], flags: list[Expense], ack_through: date | None, today: date
) -> str:
    header = f"Brex missing-GL-code check — as of {today.isoformat()}"
    if not missing:
        return f"{header}\n  all {today.year} card expenses have a GL code."
    lines = [header, f"  {len(missing)} expense(s) missing a GL code total."]
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
        f"🏷️ {len(flags)} Brex expense(s) missing a GL code "
        f"(oldest {oldest.posted}, {oldest.merchant} {oldest.amount_str}). "
        f"Set the Debit GL in Brex, or ack to acknowledge the backlog."
    )


def build_sweep(fetch=None):
    """The sweep with the Brex query injectable (see the receipts sweep)."""

    def _sweep(today: date, tasks_dir: Path) -> reminders.SweepResult:
        records = (fetch or fetch_card_records)()
        missing = missing_gl(records, today)
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
