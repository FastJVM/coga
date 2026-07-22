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
    """A completion gate: a predicate, fix hint, and transition policy.

    `check` returns a truthy value when the required artifact is present. The
    `remediation` string may reference `{slug}`; it is appended to the fail-loud
    message so the operator knows exactly how to satisfy the gate.
    `publish_current_branch` is reserved for artifacts such as a PR whose
    branch must receive the transition commit after the gate passes. Keeping
    that policy on the token means `bump` stays independent of workflow/skill
    names.
    """

    check: Callable[[str], object]
    remediation: str
    publish_current_branch: bool = False


def _has_pr(blackboard_text: str) -> object:
    # Imported lazily: `coga.autoclose` pulls in `coga.mark` (and thus
    # `coga.validate`) at module load, so a top-level import here would form a
    # `validate -> step_gate -> autoclose -> mark -> validate` cycle. step_gate
    # is imported by validate at module level, so it must stay import-light.
    from coga.autoclose import parse_pr_url

    return parse_pr_url(blackboard_text)


STEP_GATES: dict[str, StepGate] = {
    "pr": StepGate(
        check=_has_pr,
        remediation=(
            "Run `coga open-pr {slug}` from the open-pr step to push the recorded "
            "branch and open the PR (it writes `pr:` under `## Dev`), then bump."
        ),
        publish_current_branch=True,
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


def gate_publishes_current_branch(token: object) -> bool:
    """Whether a satisfied gate's transition commit must update its branch."""
    if not isinstance(token, str):
        return False
    gate = STEP_GATES.get(token)
    return bool(gate and gate.publish_current_branch)


__all__ = [
    "StepGate",
    "STEP_GATES",
    "known_gate_tokens",
    "gate_unmet_reason",
    "gate_publishes_current_branch",
]
