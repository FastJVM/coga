"""Which checkout a shipped workflow step starts in (`dev/checkouts`).

A closed compatibility table, not a name heuristic. A row applies only to the
qualified workflow name, the frozen current step's name, and one of its known
instruction shapes; the instructions that step actually consumes (resolved
step-skill bytes, or the live inline section) must also equal the packaged
contract. Anything else — a custom workflow, a locally changed step skill or
section, extra or replaced step skills — selects `manual` with its reason.
Ticket-wide `skills:` never select entry behavior, and completion gates
(`requires:`) are not read. Pure: no Git, no writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from coga.config import Config
from coga.paths import (
    bootstrap_skill_path,
    bootstrap_workflow_path,
    resolve_skill_path,
    resolve_workflow_path,
)
from coga.ticket import Ticket
from coga.workflow import Workflow, WorkflowError

CheckoutPolicyKind = Literal["control", "create-or-reuse", "reuse-required", "manual"]


@dataclass(frozen=True)
class CheckoutPolicy:
    """The selected entry behavior and why."""

    kind: CheckoutPolicyKind
    reason: str


_CODE = ("code/design-then-implement", "code/with-review", "code/with-self-review")
_ALL = (*_CODE, "docs/with-review")
_INLINE: tuple[str, ...] = ()

# (workflow, step) -> (accepted step-skill shapes, entry policy). An empty
# shape means the step consumes its live inline section.
_ROWS: dict[tuple[str, str], tuple[tuple[tuple[str, ...], ...], CheckoutPolicyKind]] = {
    ("code/design-then-implement", "design"): ((("code/design",),), "control"),
    ("code/design-then-implement", "evaluate-design"): (
        (("code/review-design",),), "control"
    ),
    ("code/design-then-implement", "review-design"): ((_INLINE,), "control"),
    **{(wf, "implement"): ((("code/implement",),), "create-or-reuse") for wf in _CODE},
    ("docs/with-review", "implement"): ((_INLINE,), "create-or-reuse"),
    ("code/with-review", "peer-review"): ((_INLINE,), "reuse-required"),
    ("docs/with-review", "peer-review"): ((_INLINE,), "reuse-required"),
    ("code/with-self-review", "self-qa"): ((("code/self-qa",),), "reuse-required"),
    ("code/design-then-implement", "open-pr"): ((("code/open-pr",),), "control"),
    ("code/with-review", "open-pr"): ((("code/open-pr",),), "control"),
    ("docs/with-review", "open-pr"): ((_INLINE,), "control"),
    ("code/with-self-review", "pr"): ((("code/open-pr",),), "control"),
    # Owner-held PR review, reached only through an explicit assist. Older
    # frozen snapshots carry empty skills and consume the live `## review`.
    **{
        (wf, "review"): ((("code/address-pr-comments",), _INLINE), "reuse-required")
        for wf in _ALL
    },
}


def select_checkout_policy(cfg: Config, ticket: Ticket) -> CheckoutPolicy:
    """Select from the frozen workflow and current step; see the module doc."""
    workflow = ticket.workflow if isinstance(ticket.workflow, dict) else None
    step = ticket.current_step()
    if workflow is None or not isinstance(step, dict):
        return CheckoutPolicy("manual", "the ticket has no current workflow step")
    wf_name = workflow.get("name")
    step_name = step.get("name")
    row = _ROWS.get((wf_name, step_name)) if isinstance(wf_name, str) else None
    label = f"step {step_name!r} of workflow {wf_name!r}"
    if row is None:
        return CheckoutPolicy(
            "manual", f"{label} is not a shipped step with a known checkout"
        )
    shapes, kind = row
    skills = tuple(step.get("skills") or ())
    if skills not in shapes:
        return CheckoutPolicy(
            "manual", f"{label} declares step skills {list(skills)!r}, not the shipped ones"
        )
    changed = (
        _changed_skill(cfg, skills) if skills else _changed_section(cfg, wf_name, step_name)
    )
    if changed is not None:
        return CheckoutPolicy("manual", f"{label}: {changed}")
    return CheckoutPolicy(kind, f"{label} uses the shipped instructions")


def _changed_skill(cfg: Config, refs: tuple[str, ...]) -> str | None:
    for ref in refs:
        try:
            resolved = resolve_skill_path(cfg, ref)
            if resolved is None:
                return f"step skill {ref!r} does not resolve"
            if resolved.read_bytes() != bootstrap_skill_path(cfg, ref).read_bytes():
                return f"step skill {ref!r} differs from the shipped copy at {resolved}"
        except OSError as exc:
            return f"step skill {ref!r} could not be compared: {exc}"
    return None


def _changed_section(cfg: Config, wf_name: str, step_name: str) -> str | None:
    try:
        live = Workflow.load(resolve_workflow_path(cfg, wf_name))
        shipped = Workflow.load(bootstrap_workflow_path(cfg, wf_name))
    except (WorkflowError, OSError) as exc:
        return f"its workflow definition could not be compared: {exc}"
    section = live.inline_instructions.get(step_name)
    if not section:
        return f"the live workflow has no `## {step_name}` instructions"
    if section != shipped.inline_instructions.get(step_name):
        return f"its `## {step_name}` section differs from the shipped copy"
    return None


__all__ = ["CheckoutPolicy", "CheckoutPolicyKind", "select_checkout_policy"]
