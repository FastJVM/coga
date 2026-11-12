"""Which checkout a workflow step starts in (`coga/checkouts`).

The frozen step declares it: `checkout:` is one of `CHECKOUT_POLICIES`, and an
explicit valid value is authoritative regardless of workflow name, step name,
skills, instruction bytes, role or `requires:`. No file is resolved on that
path. A malformed value raises `CheckoutPolicyError` before any checkout
effect; `invalid_checkout_declarations` checks every frozen step up front.

Snapshots frozen before the field existed carry no `checkout` key. For those
only, a closed legacy table applies: a row matches the qualified workflow
name, the frozen current step's name, and one of its known instruction
shapes; the instructions that step actually consumes (resolved step-skill
bytes, or the live inline section) must also equal the packaged contract.
Anything else selects `manual` with its reason. The table may be retired only
under the rule in `coga/checkouts` ("Legacy snapshots"). Pure: no Git, no
writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from coga.config import Config
from coga.paths import (
    bootstrap_skill_path,
    bootstrap_workflow_path,
    resolve_skill_path,
    resolve_workflow_path,
)
from coga.ticket import Ticket
from coga.workflow import CHECKOUT_POLICIES, Workflow, WorkflowError

CheckoutPolicyKind = Literal["control", "create-or-reuse", "reuse-required", "manual"]


@dataclass(frozen=True)
class CheckoutPolicy:
    """The selected entry behavior, why, and the frozen step it was read from."""

    kind: CheckoutPolicyKind
    reason: str
    step: str | None = None


class CheckoutPolicyError(ValueError):
    """A frozen step declares a `checkout:` value outside the vocabulary."""


def _invalid(label: str, value: object) -> str:
    return (
        f"{label} declares checkout {value!r}, which must be one of "
        f"{list(CHECKOUT_POLICIES)}"
    )


def invalid_checkout_declarations(ticket: Ticket) -> list[str]:
    """Reasons for every frozen step whose present `checkout:` is malformed.

    Checks the whole snapshot, not only the current step, so a launch can
    refuse before creating a branch for a ticket a later step would break.
    """
    workflow = ticket.workflow if isinstance(ticket.workflow, dict) else None
    steps = workflow.get("steps") if workflow is not None else None
    if not isinstance(steps, list):
        return []
    wf_name = workflow.get("name")
    out = []
    for step in steps:
        if isinstance(step, dict) and "checkout" in step:
            value = step["checkout"]
            if not isinstance(value, str) or value not in CHECKOUT_POLICIES:
                label = f"step {step.get('name')!r} of workflow {wf_name!r}"
                out.append(_invalid(label, value))
    return out


_CODE = (
    "code/agent-merge",
    "code/design-then-implement",
    "code/with-review",
    "code/with-self-review",
)
# Workflows whose final step is the owner-held PR `review`.
_OWNER_REVIEWED = (
    "code/design-then-implement",
    "code/with-review",
    "code/with-self-review",
    "docs/with-review",
)
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
    **{
        (wf, "peer-review"): ((("code/peer-review",),), "reuse-required")
        for wf in ("code/agent-merge", "code/design-then-implement")
    },
    # Older `code/with-review` snapshots carry empty skills and consume the
    # live inline `## peer-review`, which points at the same skill.
    ("code/with-review", "peer-review"): (
        (("code/peer-review",), _INLINE), "reuse-required"
    ),
    ("docs/with-review", "peer-review"): ((_INLINE,), "reuse-required"),
    ("code/with-self-review", "self-qa"): ((("code/self-qa",),), "reuse-required"),
    **{
        (wf, "open-pr"): ((("code/open-pr",),), "control")
        for wf in ("code/agent-merge", "code/design-then-implement", "code/with-review")
    },
    ("docs/with-review", "open-pr"): ((_INLINE,), "control"),
    ("code/with-self-review", "pr"): ((("code/open-pr",),), "control"),
    # The agent merge re-runs verification at the reviewed head before merging.
    ("code/agent-merge", "merge"): ((("code/merge-pr",),), "reuse-required"),
    # Owner-held PR review, reached only through an explicit assist. Older
    # frozen snapshots carry empty skills and consume the live `## review`.
    **{
        (wf, "review"): ((("code/address-pr-comments",), _INLINE), "reuse-required")
        for wf in _OWNER_REVIEWED
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
    named = step_name if isinstance(step_name, str) else None
    label = f"step {step_name!r} of workflow {wf_name!r}"
    if "checkout" in step:
        declared = step["checkout"]
        if not isinstance(declared, str) or declared not in CHECKOUT_POLICIES:
            raise CheckoutPolicyError(_invalid(label, declared))
        kind = cast(CheckoutPolicyKind, declared)
        return CheckoutPolicy(kind, f"{label} declares checkout: {kind}", named)
    # Legacy snapshot: frozen before `checkout:` existed.
    label = f"{label} has no frozen checkout: (legacy snapshot);"
    row = _ROWS.get((wf_name, step_name)) if isinstance(wf_name, str) else None
    if row is None:
        return CheckoutPolicy(
            "manual", f"{label} it is not a shipped step with a known checkout", named
        )
    shapes, kind = row
    skills = tuple(step.get("skills") or ())
    if skills not in shapes:
        return CheckoutPolicy(
            "manual",
            f"{label} it declares step skills {list(skills)!r}, not the shipped ones",
            named,
        )
    changed = (
        _changed_skill(cfg, skills) if skills else _changed_section(cfg, wf_name, step_name)
    )
    if changed is not None:
        return CheckoutPolicy("manual", f"{label} {changed}", named)
    return CheckoutPolicy(kind, f"{label} it uses the shipped instructions", named)


def _changed_skill(cfg: Config, refs: tuple[str, ...]) -> str | None:
    for ref in refs:
        try:
            resolved = resolve_skill_path(cfg, ref)
            if resolved is None:
                return f"step skill {ref!r} does not resolve"
            # A Windows clone with core.autocrlf checks a local copy out as
            # CRLF while the wheel ships LF; line endings are not a change.
            if _lf(resolved.read_bytes()) != _lf(bootstrap_skill_path(cfg, ref).read_bytes()):
                return f"step skill {ref!r} differs from the shipped copy at {resolved}"
        except (OSError, ValueError) as exc:
            return f"step skill {ref!r} could not be compared: {exc}"
    return None


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


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
    if (wf_name, step_name) == ("code/with-review", "peer-review"):
        # Legacy snapshots consume an inline pointer to this live skill;
        # both instruction sources must still match the shipped contract.
        return _changed_skill(cfg, ("code/peer-review",))
    return None


__all__ = [
    "CheckoutPolicy",
    "CheckoutPolicyError",
    "CheckoutPolicyKind",
    "invalid_checkout_declarations",
    "select_checkout_policy",
]
