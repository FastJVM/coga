"""Dependency asks whose named task can no longer finish them.

A dependency is an open blocker ask on the dependent ticket that reads
`Depends on <task-ref>: …` (`coga/lifecycle`). The megalaunch drain retries
the dependent once that task is `done`, or once it disappears during the same
run. Three things leave the ask open forever instead:

- the named task was **canceled** — cancellation does not count as completion;
- the named task is **gone** after a rename, delete, or cancel-then-delete —
  the slug no longer resolves, so nothing ever finishes it;
- the named task finished and was **retired** before the run that would have
  drained the dependent — it is satisfied, but the drain only recognizes a
  disappearance it saw happen.

This module finds those asks. It never rewrites them: whether a successor
covers what the dependent needed is a judgment for the dependent's owner.
Consumers are `coga validate` (the `dead-dependency` warning, which Dream's
weekly validate-drift already sweeps) and `coga mark canceled` (a read-only
list of the dependents the cancel just stranded).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from coga.blackboard import open_blockers
from coga.config import Config
from coga.logfile import iter_log_messages_reverse
from coga.taskfile import TaskFileError
from coga.tasks import TaskRef, read_ticket
from coga.ticket import TicketError

# Mirrors `megalaunch._reason_names_task`'s ref alphabet. A trailing `.` or `/`
# is sentence punctuation, not part of the ref.
_DEPENDS_ON_RE = re.compile(r"\bDepends on\s+`?(?P<ref>[A-Za-z0-9_./-]+)`?")
_SUPERSEDED_RE = re.compile(r"^Superseded by\s+`?(?P<ref>[A-Za-z0-9_./-]+)`?")
_CANCELED_LOG_RE = re.compile(r"^canceled \([^)]*\): (?P<reason>.*)$")

CANCELED = "canceled"
MISSING = "missing"
RETIRED = "retired"


@dataclass(frozen=True)
class DeadDependency:
    """One open `Depends on <target>` ask that cannot drain on its own."""

    dependent: str
    blocker_id: str
    target: str
    state: str  # CANCELED | MISSING | RETIRED
    cancel_reason: str | None = None
    successor: str | None = None

    def remedy(self) -> str:
        """The repair the dependent's owner should make, as one sentence."""
        if self.state == RETIRED:
            return (
                f"{self.target} finished and was retired; answer the ask with "
                f"`coga unblock {self.dependent} --answer \"...\"`"
            )
        rewrite = (
            f"answer the ask (`coga unblock {self.dependent}`) and, if work "
            f"still waits, re-block on the real dependency"
        )
        if self.successor:
            return (
                f"{self.target} was superseded by {self.successor}; {rewrite} "
                f"(`coga block --task {self.dependent} --reason "
                f"\"Depends on {self.successor}: ...\"`)"
            )
        if self.state == CANCELED:
            return f"{self.target} was canceled; {rewrite}"
        return (
            f"{self.target} names no task (renamed or deleted?); {rewrite}"
        )


def named_dependencies(reason: str) -> list[str]:
    """Task refs a blocker reason declares with `Depends on <ref>`."""
    out: list[str] = []
    for match in _DEPENDS_ON_RE.finditer(reason):
        ref = match.group("ref").rstrip("./")
        if ref and ref not in out:
            out.append(ref)
    return out


def successor_from_reason(reason: str | None) -> str | None:
    """The successor ref of a `Superseded by <ref>` cancel reason, if any."""
    if not reason:
        return None
    match = _SUPERSEDED_RE.match(reason.strip())
    return match.group("ref").rstrip("./") if match else None


def dead_dependency_asks(
    cfg: Config,
    refs: list[TaskRef],
    *,
    targets: set[str] | None = None,
) -> list[DeadDependency]:
    """Open dependency asks on live tickets that cannot drain on their own.

    `refs` is the full task listing (so a missing target really is missing).
    `targets`, when given, limits the scan to asks naming those refs — the
    cancel hint passes the one slug it just canceled.
    """
    by_slug = {ref.id_slug: ref for ref in refs}
    asks: list[tuple[str, str, str]] = []
    for ref in refs:
        try:
            ticket = read_ticket(ref)
        except (TicketError, TaskFileError):
            continue
        if ticket.status in ("done", "canceled"):
            continue
        try:
            blockers = open_blockers(ref.ticket_path)
        except (OSError, TaskFileError):
            continue
        for blocker in blockers:
            for target in named_dependencies(blocker.reason):
                if targets is not None and target not in targets:
                    continue
                asks.append((ref.id_slug, blocker.id, target))

    if not asks:
        return []

    states: dict[str, tuple[str, str | None] | None] = {}
    unresolved: set[str] = set()
    for _, _, target in asks:
        if target in states or target in unresolved:
            continue
        target_ref = by_slug.get(target)
        if target_ref is None:
            unresolved.add(target)
            continue
        try:
            status = read_ticket(target_ref).status
        except (TicketError, TaskFileError):
            states[target] = None
            continue
        states[target] = (CANCELED, None) if status == "canceled" else None
        if status == "canceled":
            unresolved.add(target)  # still need the logged reason

    _resolve_from_log(cfg, unresolved, states, present=set(by_slug))

    out: list[DeadDependency] = []
    for dependent, blocker_id, target in asks:
        verdict = states.get(target)
        if verdict is None:
            continue
        state, reason = verdict
        out.append(DeadDependency(
            dependent=dependent,
            blocker_id=blocker_id,
            target=target,
            state=state,
            cancel_reason=reason,
            successor=successor_from_reason(reason),
        ))
    return out


def _resolve_from_log(
    cfg: Config,
    pending: set[str],
    states: dict[str, tuple[str, str | None] | None],
    *,
    present: set[str],
) -> None:
    """Classify `pending` targets by their newest terminal log line.

    A target still on disk is already known `canceled`; the log only supplies
    its reason. A target gone from disk is `retired` when its newest terminal
    line is a done, `canceled` when it is a cancel, and `missing` otherwise
    (no terminal line at all: renamed, deleted, or a typo).
    """
    remaining = set(pending)
    for task_ref, message in iter_log_messages_reverse(cfg):
        if not remaining:
            break
        if task_ref not in remaining:
            continue
        canceled = _CANCELED_LOG_RE.match(message)
        if canceled:
            states[task_ref] = (CANCELED, canceled.group("reason").strip())
            remaining.discard(task_ref)
        elif task_ref not in present and (
            message.startswith("task done") or "→ done" in message
        ):
            states[task_ref] = (RETIRED, None)
            remaining.discard(task_ref)
    for target in remaining:
        if target not in present:
            states[target] = (MISSING, None)


__all__ = [
    "CANCELED",
    "MISSING",
    "RETIRED",
    "DeadDependency",
    "dead_dependency_asks",
    "named_dependencies",
    "successor_from_reason",
]
