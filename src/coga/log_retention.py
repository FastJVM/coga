"""Pure event selection shared by maintenance and publication reconciliation.

Callers supply the pinned inventory/cursor snapshot and a local calendar
cutoff. This module performs no repository discovery or Git operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from coga.logfile import LogEvent, LogMutation, parse_events
from coga.movement_cursor import fingerprint
from coga.recurring import _LedgerAccumulator


class RetentionError(ValueError):
    """Input needs repair before history can safely be removed."""


@dataclass(frozen=True)
class RetentionSnapshot:
    existing_refs: frozenset[str]
    unread_movements: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Selection:
    events: tuple[LogEvent, ...]
    reasons: tuple[frozenset[str], ...]
    mutation: LogMutation

    @property
    def summary(self) -> dict[str, tuple[int, int]]:
        names = {reason for reasons in self.reasons for reason in reasons}
        return {name: (sum(name in r for r in self.reasons),
                       sum(len(e.raw) for e, r in zip(self.events, self.reasons) if name in r))
                for name in sorted(names)}


def cutoff_at(today: date, days: int) -> datetime:
    """Local calendar arithmetic, saturating before datetime.min, even huge ints."""
    return datetime.combine(date.fromordinal(max(1, today.toordinal() - days)), datetime.min.time())


def select(raw: bytes, snapshot: RetentionSnapshot, cutoff: datetime) -> Selection:
    events = parse_events(raw)
    ledger = _LedgerAccumulator()
    per_event: dict[int, tuple[str, str]] = {}
    pauses: dict[str, tuple[datetime, int]] = {}
    for i, event in enumerate(events):
        if event.ref is None:
            continue
        # Include parseable incomplete entries in validation too: deleting an
        # older bad record must not make a bounded reader appear healthy.
        one = _LedgerAccumulator()
        one.add(event.ref, event.message or "")
        ledger.add(event.ref, event.message or "")
        if event.ref in one.periods:
            per_event[i] = (event.ref, one.periods[event.ref])
        if (event.ref.startswith("recurring/") and event.timestamp is not None
                and (event.message or "").startswith(("created ", "paused "))):
            pauses[event.ref] = max(pauses.get(event.ref, (datetime.min, -1)), (event.timestamp, i))
    # The ordinary readers can recognize a malformed-date header even though
    # retention regards it as opaque. Validate that same envelope grammar.
    from coga.logfile import _ENTRY_RE, decode_log_message, log_lines
    for line in log_lines(raw.decode("utf-8", errors="replace").replace("\r\n", "\n")):
        match = _ENTRY_RE.match(line)
        if match:
            ledger.add(match["ref"], decode_log_message(match["message"]) if match["version"] else match["message"])
    if ledger.errors:
        raise RetentionError("; ".join(ledger.errors[k] for k in sorted(ledger.errors)))
    reasons: list[set[str]] = [set() for _ in events]
    for i, event in enumerate(events):
        if event.timestamp is None or not event.complete:
            reasons[i].add("opaque")
            # Existing task_log_lines attaches unmatched lines to the prior
            # header even after v1. Preserve that boundary, not just its bytes.
            if i:
                reasons[i - 1].add("opaque-boundary")
        elif event.timestamp >= cutoff:
            reasons[i].add("recent")
        if event.ref in snapshot.existing_refs:
            reasons[i].add("existing-task")
        if i in per_event:
            ref, period = per_event[i]
            if ledger.periods[ref] == period:
                reasons[i].add("ledger")
        if event.ref in pauses and pauses[event.ref][1] == i:
            reasons[i].add("pause")
        if fingerprint(event) in snapshot.unread_movements:
            reasons[i].add("unread-movement")
    return Selection(events, tuple(frozenset(r) for r in reasons),
                     LogMutation(raw, tuple(i for i, r in enumerate(reasons) if not r)))
