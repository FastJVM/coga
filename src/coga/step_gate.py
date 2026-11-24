"""Completion gates for workflow steps (`requires:`).

A frozen workflow step may declare `requires: <token>`. Before `coga bump`
advances *off* that step, it runs the token's predicate against the task
blackboard; a falsy result blocks the bump with a fail-loud message. This makes
step completion a **data check** — the required artifact must be recorded on the
blackboard — rather than trusting an agent (or an exit code) to have produced
it. It is what lets `code/open-pr` be an ordinary agent step again: a rogue
agent that skips `coga open-pr` and bumps is rejected because there is no `pr:`.

The registry is deliberately tiny and generic — `bump` never hardcodes a
`code/*` skill name — so any future step can gate on a recorded artifact by
declaring `requires: <token>` for a token registered here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class StepGate:
    """A completion gate: a predicate and a fix hint.

    `check` returns a truthy value when the required artifact is present. The
    `remediation` string may reference `{slug}`; it is appended to the fail-loud
    message so the operator knows exactly how to satisfy the gate.
    """

    check: Callable[[str], object]
    remediation: str


def _has_pr(blackboard_text: str) -> object:
    from coga.blackboard import read_dev_fields

    return read_dev_fields(blackboard_text).get("pr")


def _has_branch_linkage(blackboard_text: str) -> object:
    from coga.blackboard import read_dev_fields

    return read_dev_fields(blackboard_text).get("branch")


STEP_GATES: dict[str, StepGate] = {
    "branch": StepGate(
        check=_has_branch_linkage,
        remediation=(
            "Record this attempt's branch as `branch:` under `## Dev` "
            "in the ticket, then bump."
        ),
    ),
    "pr": StepGate(
        check=_has_pr,
        remediation=(
            "Run the `git/push-and-open-pr` workflow script to record `pr:` "
            "under `## Dev` and bump."
        ),
    ),
}


def known_gate_tokens() -> frozenset[str]:
    """Registered `requires:` tokens (used by workflow parsing and validate)."""
    return frozenset(STEP_GATES)


def gate_unmet_reason(token: object, blackboard_text: str, *, slug: str) -> str | None:
    """Return a fail-loud reason if the gate is unmet, else None.

    An unknown token also returns a reason — a mis-frozen `requires:` should fail
    loud rather than silently wave the bump through.
    """
    if not isinstance(token, str):
        valid = ", ".join(sorted(STEP_GATES)) or "(none)"
        return (
            f"Step declares malformed `requires: {token!r}`; completion gate "
            f"tokens must be strings (valid: {valid}). Fix the workflow definition."
        )
    gate = STEP_GATES.get(token)
    if gate is None:
        valid = ", ".join(sorted(STEP_GATES)) or "(none)"
        return (
            f"Step declares `requires: {token}`, which is not a known completion "
            f"gate (valid: {valid}). Fix the workflow definition."
        )
    if gate.check(blackboard_text):
        return None
    return (
        f"Cannot advance: this step requires a recorded `{token}` artifact on the "
        f"blackboard, but none is present. " + gate.remediation.format(slug=slug)
    )


__all__ = [
    "StepGate",
    "STEP_GATES",
    "known_gate_tokens",
    "gate_unmet_reason",
]
