"""Shared branch preparation for ticket launch and ad-hoc chat (`coga/checkouts`).

Two consumers call one implementation of the Git mechanics: ordinary
`coga launch`, for a shipped step whose policy (`checkout_policy`) names a
feature branch, and the `coga run prepare-checkout` recipe an agent inside a
direct chat invokes before its first edit. Both start from a clean control
checkout proven by `git.prepare_control_checkout`, create or reuse exactly one
branch without resetting its commits, check occupancy and ignored-file
collisions, and switch normally. Neither commits code, pushes a feature
branch, rebases, rolls back, transitions a workflow, or deletes a branch.

The ticket path splits into `plan_ticket_checkout` (on control: reserve,
create, write and strictly publish `branch:` linkage, then re-prove control)
and `enter_ticket_checkout` (switch, project the current ticket unstaged from
the final control snapshot, and record that blob as strict publication
provenance), so launch composes its prompt from control state in between.
Failures raise `CheckoutPreparationError` naming the stage, where the checkout
stands, and what was retained. Receipts in this worktree's private Git
directory (`git rev-parse --git-path coga/checkout-receipts`), where no state
sweep can ever reach them, make an interrupted reservation retry the same
name; they are retry evidence, never task state, and removing one never
deletes a branch.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import secrets
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from coga import git
from coga.atomicio import atomic_write_text
from coga.autoclose import (
    dev_heading_line,
    parse_branch_names,
    parse_worktree_path,
)
from coga.blackboard import update_blackboard_under_barrier
from coga.checkout_policy import CheckoutPolicy, select_checkout_policy
from coga.compose import CheckoutNotice
from coga.oscompat import lock_dir, lock_fd, unlock_fd, process_is_running
from coga.config import Config
from coga.tasks import TaskRef
from coga.taskfile import TaskFileError, split_body
from coga.ticket import Ticket, TicketError
from coga.open_pr import same_git_checkout

PREPARE_RECIPE = "prepare-checkout"
_RECEIPT_DIR = "coga/checkout-receipts"
# Receipt stages written only after `branch:` reached control.
_LANDED_STAGES = frozenset({"published", "switching", "admitted"})
_BRANCH_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")


class CheckoutPreparationError(RuntimeError):
    """Preparation stopped; the message names stage, position and what remains.

    `switched` is True once HEAD left control, so teardown must not return or
    sweep blindly over what the session never started.
    """

    def __init__(self, stage: str, message: str, *, switched: bool = False) -> None:
        self.stage = stage
        self.switched = switched
        super().__init__(f"checkout preparation stopped at {stage}: {message}")


TicketCheckoutAction = Literal["stay", "switch", "external"]


@dataclass(frozen=True)
class TicketCheckoutPlan:
    """What `plan_ticket_checkout` proved and decided, on control."""

    policy: CheckoutPolicy
    root: Path
    rel: str
    control_oid: str
    ticket_bytes: bytes
    action: TicketCheckoutAction
    branch: str | None = None
    branch_oid: str | None = None
    outcome: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)
    worktree: str | None = None


# --- ticket preparation -------------------------------------------------------


def plan_ticket_checkout(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    policy: CheckoutPolicy,
) -> TicketCheckoutPlan:
    """Prove control, then select, create, link and publish the step's branch.

    `ticket` is the authoritative copy launch routed and preflighted. Runs
    only from an armed launch boundary on control. A linkage publication
    that lands advances control, so the ticket's lifecycle, frozen workflow
    and resolved checkout policy are re-checked after each control refresh;
    a changed contract refuses rather than spawning a stale step. Never switches.
    """
    root, control_oid = _prove_control(cfg, "entry")
    rel = git.relative_to_root(root, ref.ticket_path)
    current = _authoritative_ticket(
        cfg, root, ref, rel, control_oid, ticket, policy, "entry"
    )
    _, blackboard = _split(current, ref)
    branches = parse_branch_names(blackboard)
    worktree = parse_worktree_path(blackboard)
    base = TicketCheckoutPlan(
        policy=policy, root=root, rel=rel, control_oid=control_oid,
        ticket_bytes=current, action="stay",
    )
    if policy.kind in {"control", "manual"}:
        return base
    branch = branches[0] if branches else None
    if branch is not None:
        _require_valid_branch(cfg, root, branch, "linkage")
    if worktree is not None:
        if branch is None:
            raise CheckoutPreparationError(
                "linkage",
                f"`## Dev` records worktree: {worktree} without a branch:; "
                "record the clone's branch or remove the stale worktree line. "
                f"This checkout stayed on {cfg.git_control_branch!r}.",
            )
        return replace(
            base, action="external", branch=branch, worktree=worktree,
            outcome="recorded clone", notes=(_verify_recorded_clone(cfg, branch, worktree),),
        )
    if branch is None:
        if policy.kind == "reuse-required":
            if _already_satisfied(blackboard):
                return replace(base, notes=(
                    "No branch is recorded, but `## Already satisfied` evidence "
                    "exists: verify it from control instead of editing.",
                ))
            raise CheckoutPreparationError(
                "linkage",
                f"{ref.id_slug}'s current step reuses its implementation branch, "
                "but `## Dev` records no branch:. Record the branch that holds "
                "the work (or the `## Already satisfied` evidence) on control. "
                f"This checkout stayed on {cfg.git_control_branch!r}.",
            )
        branch, oid = _reserve_and_create(cfg, root, ref, rel, control_oid)
        current = _publish_linkage(cfg, root, ref, rel, current, branch)
        root, control_oid = _prove_control(cfg, "linkage publication")
        current = _authoritative_ticket(
            cfg, root, ref, rel, control_oid, ticket, policy, "linkage publication"
        )
        _, blackboard = _split(current, ref)
        if (parse_branch_names(blackboard) or [None])[0] != branch:
            raise CheckoutPreparationError(
                "linkage publication",
                f"control's ticket no longer records branch: {branch} first; "
                "retry the launch",
            )
        _update_receipt(cfg, root, rel, stage="published")
        _check_switch_target(cfg, root, branch, control_oid)
        return replace(
            base, control_oid=control_oid, ticket_bytes=current, action="switch",
            branch=branch, branch_oid=oid, outcome="created",
        )
    oid, notes = _reuse_recorded_branch(cfg, root, branch)
    _discard_receipt(cfg, root, rel)
    # Refuse what the switch would refuse while still before the launch audit;
    # `enter_ticket_checkout` re-observes both under the state lock.
    _check_switch_target(cfg, root, branch, control_oid)
    _guard_stranded_ticket(cfg, root, branch, control_oid, rel)
    return replace(
        base, action="switch", branch=branch, branch_oid=oid, outcome="reused",
        notes=notes,
    )


def confirm_ticket_checkout(
    cfg: Config, ref: TaskRef, ticket: Ticket, plan: TicketCheckoutPlan
) -> TicketCheckoutPlan:
    """Re-prove control after launch published its audit line; keep the plan.

    Launch records its `launched` line only once planning succeeded, and
    publishing it advances control. A switch plan is re-anchored to that
    final control revision, with the ticket's contract, policy and recorded
    branch re-checked, so the projection still comes from control as the
    agent will see it. A plan that stays on control needs no anchor.
    """
    if plan.action != "switch":
        return plan
    stage = "launch audit"
    root, control_oid = _prove_control(cfg, stage)
    if control_oid == plan.control_oid:
        return plan
    current = _authoritative_ticket(
        cfg, root, ref, plan.rel, control_oid, ticket, plan.policy, stage
    )
    _, blackboard = _split(current, ref)
    if (parse_branch_names(blackboard) or [None])[0] != plan.branch:
        raise CheckoutPreparationError(
            stage,
            f"control's ticket no longer records branch: {plan.branch} first; "
            "retry the launch",
        )
    return replace(plan, root=root, control_oid=control_oid, ticket_bytes=current)


def enter_ticket_checkout(cfg: Config, ref: TaskRef, plan: TicketCheckoutPlan) -> None:
    """Switch, project the ticket from `plan.control_oid`, record provenance.

    Every precondition is re-observed under the state lock first: HEAD is
    control at the planned revision, the tree is clean, and the ticket's
    bytes are still the planned ones. After the ordinary `git switch`, only
    this ticket is written (unstaged) and its control blob recorded in
    `git.PUBLISHED_REF`; the read-back is verified before returning.
    """
    if plan.action != "switch":
        return
    assert plan.branch is not None
    root, rel = plan.root, plan.rel
    with git.state_lock(cfg):
        if _head(root) != plan.control_oid or git.symbolic_head(root) != cfg.git_control_branch:
            raise CheckoutPreparationError(
                "switch",
                f"HEAD moved off {cfg.git_control_branch!r} at {plan.control_oid} "
                "after preparation; retry the launch",
            )
        dirt = _status(root)
        if dirt:
            raise CheckoutPreparationError(
                "switch", "the control checkout changed after preparation:\n" + dirt
            )
        if ref.ticket_path.read_bytes() != plan.ticket_bytes:
            raise CheckoutPreparationError(
                "switch", f"{rel} changed after preparation; retry the launch"
            )
        _check_switch_target(cfg, root, plan.branch, plan.control_oid)
        _guard_stranded_ticket(cfg, root, plan.branch, plan.control_oid, rel)
        _update_receipt(cfg, root, rel, stage="switching", missing_ok=True)
        _switch(root, plan.branch, "switch")
        try:
            _project_after_switch(cfg, ref, plan)
        except CheckoutPreparationError as exc:
            exc.switched = True
            raise
        except (git.GitError, OSError) as exc:
            # Whatever failed after the switch, HEAD already left control:
            # say so, so launch neither returns nor sweeps over it blindly.
            raise CheckoutPreparationError(
                "verification",
                f"switched to {plan.branch!r}, then could not finish preparing "
                f"it: {exc}. No agent was started; the branch and control's "
                f"{rel} are intact",
                switched=True,
            ) from exc


def _project_after_switch(cfg: Config, ref: TaskRef, plan: TicketCheckoutPlan) -> None:
    """Project, record provenance and verify; runs only after the switch."""
    assert plan.branch is not None
    root, rel = plan.root, plan.rel
    try:
        ref.ticket_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(ref.ticket_path, plan.ticket_bytes.decode("utf-8"))
    except OSError as exc:
        raise CheckoutPreparationError(
            "projection",
            f"switched to {plan.branch!r} but could not write control's {rel}: "
            f"{exc}. The branch and control's ticket are intact; retry the "
            "launch, which returns this checkout first",
        ) from exc
    oid = git._blob_oid(root, plan.control_oid, rel)
    if oid is None:
        raise CheckoutPreparationError(
            "provenance", f"{rel} is not on control at {plan.control_oid}"
        )
    try:
        git.record_projected_baseline(cfg, root, rel, oid)
    except (git.GitError, OSError) as exc:
        raise CheckoutPreparationError(
            "provenance",
            f"switched to {plan.branch!r} and projected {rel}, but could not "
            f"record its publication baseline: {exc}. No agent was started; "
            "the projected ticket equals control's copy, so returning this "
            "checkout loses nothing",
        ) from exc
    # Control records the branch: the reservation has done its job.
    _discard_receipt(cfg, root, rel)
    if git.symbolic_head(root) != plan.branch or _head(root) != plan.branch_oid:
        raise CheckoutPreparationError(
            "verification", f"HEAD is not {plan.branch!r} at {plan.branch_oid}"
        )
    if ref.ticket_path.read_bytes() != plan.ticket_bytes:
        raise CheckoutPreparationError(
            "verification", f"{rel} does not hold control's bytes"
        )


def ticket_notice(cfg: Config, plan: TicketCheckoutPlan) -> CheckoutNotice:
    """The runtime notice for a planned launch, verified by `enter_ticket_checkout`."""
    control = cfg.git_control_branch
    # Only a step with a branch has anything to push; a control step, a
    # manual one, or an `## Already satisfied` stay hands off with the bump.
    last = (
        "Push your branch and run `coga bump` last."
        if plan.branch is not None
        else "Run `coga bump` last."
    )
    returns = (
        f"After the session `coga launch` publishes Coga state and returns this "
        f"checkout to a clean {control!r}; do not switch back yourself. {last}"
    )
    notes = list(plan.notes)
    if plan.action == "switch":
        verb = "created" if plan.outcome == "created" else "reused"
        summary = (
            f"Launch {verb} and switched to branch `{plan.branch}` in {plan.root} "
            f"for step {_step_label(plan)}; its `## Dev` linkage is on "
            f"{cfg.git_remote}/{control}. Commit code there."
        )
        return CheckoutNotice(
            summary=" ".join([summary, *notes]),
            return_owner=returns,
            projected=plan.rel,
        )
    if plan.action == "external":
        summary = (
            f"This primary checkout ({plan.root}) stays on {control!r} with the "
            f"authoritative ticket. The code for branch `{plan.branch}` lives in "
            f"the recorded clone `{plan.worktree}`: change code only there, and "
            "write the ticket handoff here. " + " ".join(notes)
        )
        return CheckoutNotice(summary=summary.strip(), return_owner=returns)
    if plan.policy.kind == "manual":
        summary = (
            f"Launch prepared {plan.root} on a clean {control!r} but did not set up "
            f"a branch: {plan.policy.reason}. Before any edit, follow the complete "
            "procedure in `coga/checkouts` yourself."
        )
        return CheckoutNotice(summary=summary, return_owner=returns)
    summary = (
        f"Launch prepared {plan.root} on a clean {control!r} at "
        f"{cfg.git_remote}/{control} for step {_step_label(plan)}, which runs "
        "from control. " + " ".join(notes)
    )
    return CheckoutNotice(summary=summary.strip(), return_owner=returns)


def _step_label(plan: TicketCheckoutPlan) -> str:
    step = plan.policy.step
    return f"`{step}`" if step else "this step"


def _prove_control(cfg: Config, stage: str) -> tuple[Path, str]:
    outcome = git.prepare_control_checkout(cfg, require_remote_control=True)
    if outcome.kind != "prepared" or outcome.commit is None:
        blocking = "".join(f"\n  - {item}" for item in outcome.blocking)
        raise CheckoutPreparationError(
            stage,
            f"could not confirm a clean {cfg.git_control_branch!r} at "
            f"{cfg.git_remote}/{cfg.git_control_branch}: {outcome.reason}{blocking}",
        )
    root = git.toplevel(cfg.repo_root)
    assert root is not None
    return root, outcome.commit


def _authoritative_ticket(
    cfg: Config,
    root: Path,
    ref: TaskRef,
    rel: str,
    control_oid: str,
    expected: Ticket,
    expected_policy: CheckoutPolicy,
    stage: str,
) -> bytes:
    control = git.tree_bytes(root, control_oid, rel)
    if control is None:
        raise CheckoutPreparationError(stage, f"{rel} is not on control")
    if ref.ticket_path.read_bytes() != control:
        raise CheckoutPreparationError(
            stage, f"{rel} differs from control's copy; publish or reconcile it first"
        )
    try:
        observed = Ticket.parse(control.decode("utf-8"))
    except (UnicodeDecodeError, TicketError) as exc:
        raise CheckoutPreparationError(stage, f"cannot parse {rel}: {exc}") from exc
    if (observed.status, observed.step) != (expected.status, expected.step):
        raise CheckoutPreparationError(
            stage,
            f"control's ticket moved to status={observed.status!r} "
            f"step={observed.step!r} during preparation; retry the launch",
        )
    if observed.workflow != expected.workflow:
        raise CheckoutPreparationError(
            stage,
            "control's frozen workflow changed during preparation; retry the launch "
            "so routing and preflights use the new step contract",
        )
    # Control can also change the instructions without changing the ticket.
    # Re-select from the refreshed files before any branch mutation or spawn.
    observed_policy = select_checkout_policy(cfg, observed)
    if observed_policy != expected_policy:
        raise CheckoutPreparationError(
            stage,
            f"control's checkout policy changed during preparation: "
            f"{observed_policy.reason}; retry the launch",
        )
    return control


def _split(data: bytes, ref: TaskRef) -> tuple[str, str]:
    try:
        ticket = Ticket.parse(data.decode("utf-8"))
        above, blackboard = split_body(ticket.body)
    except (UnicodeDecodeError, TicketError, TaskFileError) as exc:
        raise CheckoutPreparationError("linkage", f"cannot read {ref.id_slug}: {exc}") from exc
    return above, blackboard or ""


def _already_satisfied(blackboard: str) -> bool:
    return re.search(r"^##\s+Already satisfied\s*$", blackboard, re.MULTILINE) is not None


def _verify_recorded_clone(cfg: Config, branch: str, worktree: str) -> str:
    path = Path(worktree).expanduser()
    try:
        clone = git.toplevel(path) if path.is_dir() else None
        head = git.symbolic_head(clone) if clone is not None else None
    except git.GitError:
        clone, head = None, None
    if clone is None:
        raise CheckoutPreparationError(
            "recorded clone",
            f"the recorded worktree {worktree} is not a Git checkout. Recover or "
            "re-record it under coga/checkouts/sandbox-clone; launch does not "
            "replace it. This checkout stayed on control.",
        )
    if same_git_checkout(cfg.repo_root, str(clone)):
        raise CheckoutPreparationError(
            "recorded clone",
            f"the recorded worktree {worktree} is this checkout but HEAD is not "
            f"{branch!r}; switch it there yourself or correct `## Dev`",
        )
    if head != branch:
        raise CheckoutPreparationError(
            "recorded clone",
            f"the recorded clone {clone} is on {head!r}, not {branch!r}; reconcile "
            "it under coga/checkouts/sandbox-clone before relaunching",
        )
    return f"The clone is on `{branch}`."


def _require_valid_branch(cfg: Config, root: Path, branch: str, stage: str) -> None:
    if branch == cfg.git_control_branch:
        raise CheckoutPreparationError(
            stage, f"`## Dev` records the control branch {branch!r} as its branch"
        )
    result = git._run(["git", "-C", str(root), "check-ref-format", "--branch", branch])
    if result.returncode != 0:
        raise CheckoutPreparationError(stage, f"{branch!r} is not a valid branch name")


def _reserve_and_create(
    cfg: Config, root: Path, ref: TaskRef, rel: str, control_oid: str
) -> tuple[str, str]:
    receipt = _read_receipt(cfg, root, rel)
    if receipt is not None and receipt.get("stage") in _LANDED_STAGES:
        # Its linkage already reached control, which no longer records it:
        # a later authority removed that branch, so never resurrect its name
        # or its old base. The branch itself is left alone.
        _discard_receipt(cfg, root, rel)
        receipt = None
    if receipt is None:
        name = _fresh_branch_name(cfg, root, f"coga/{_slug(ref.id_slug)}")
        receipt = {
            "task": rel, "root": str(root), "branch": name, "oid": control_oid,
            "stage": "reserved",
        }
        _write_receipt(cfg, root, rel, receipt)
    name, oid = receipt["branch"], receipt["oid"]
    _require_valid_branch(cfg, root, name, "reservation")
    _create_reserved_branch(
        cfg, root, name, oid,
        evidence=f"the receipt {_receipt_path(root, rel)}",
    )
    _update_receipt(cfg, root, rel, stage="created")
    return name, oid


def _create_reserved_branch(
    cfg: Config, root: Path, name: str, oid: str, *, evidence: str
) -> None:
    """Create `name` at its reserved `oid`, or verify it already stands there.

    The one create-and-verify core both consumers share. A ref absent locally
    but present on the remote, or present at any other commit, was not made
    by this reservation: refuse, adopting nothing. `evidence` names the
    retained reservation the operator inspects.
    """
    existing = _ref_oid(root, f"refs/heads/{name}")
    if existing is None:
        if git._ref_present(root, f"refs/remotes/{cfg.git_remote}/{name}"):
            raise CheckoutPreparationError(
                "reservation",
                f"reserved branch {name!r} already exists on {cfg.git_remote}; "
                f"inspect it and {evidence} before retrying",
            )
        try:
            git.run_git(root, "branch", "--no-track", name, oid)
        except git.GitError as exc:
            raise CheckoutPreparationError(
                "branch creation",
                f"could not create {name!r} at {oid}: {exc}; {evidence} is "
                "retained, so retry the same command",
            ) from exc
        existing = _ref_oid(root, f"refs/heads/{name}")
    if existing != oid:
        raise CheckoutPreparationError(
            "reservation",
            f"reserved branch {name!r} is at {existing}, not its reserved {oid}; "
            f"it was not created by this reservation. Inspect it and {evidence}; "
            "nothing was adopted",
        )


def _publish_linkage(
    cfg: Config, root: Path, ref: TaskRef, rel: str, control_bytes: bytes, branch: str
) -> bytes:
    def add_branch(region: str) -> str | None:
        return insert_branch_line(region, branch)

    try:
        written = update_blackboard_under_barrier(
            cfg, ref.ticket_path, add_branch, expected_bytes=control_bytes
        )
    except (TaskFileError, OSError, git.GitError) as exc:
        raise CheckoutPreparationError(
            "linkage", f"could not write branch: {branch} into {rel}: {exc}"
        ) from exc
    assert written is not None
    _update_receipt(cfg, root, rel, stage="linked")
    try:
        git.sync_task_state(
            cfg, ref.path, message=f"Ticket: {ref.id_slug} — branch {branch}",
            expect={ref.ticket_path: control_bytes}, strict=True,
        )
    except git.GitError as exc:
        raise CheckoutPreparationError(
            "linkage publication",
            f"branch {branch!r} exists and {rel} records it, but publication "
            f"failed: {exc}. This checkout stayed on {cfg.git_control_branch!r} "
            "with the edit retained; the next launch retries the same reservation",
        ) from exc
    published = git.tree_bytes(root, git.fetch_control(cfg, root), rel)
    if published != written:
        raise CheckoutPreparationError(
            "linkage publication",
            f"control does not carry {rel} with branch: {branch}; it stays retained "
            "locally and the next launch retries the same reservation",
        )
    return written


def insert_branch_line(region: str, branch: str) -> str:
    """Add `branch: <name>` to the live `## Dev` section, creating it if absent."""
    newline = "\r\n" if "\r\n" in region else "\n"
    line = f"branch: {branch}{newline}"
    lines = region.splitlines(keepends=True)
    heading = dev_heading_line(region)
    if heading is None:
        lead = "" if region.startswith(("\n", "\r\n")) or not region else newline
        return f"{newline}## Dev{newline}{newline}{line}{lead}{region}"
    at = heading + 1
    if at < len(lines) and not lines[at].strip():
        at += 1
    if heading < len(lines) and not lines[heading].endswith(("\n", "\r")):
        lines[heading] += newline
    lines.insert(at, line)
    if at + 1 < len(lines) and lines[at + 1].strip().startswith("#"):
        lines.insert(at + 1, newline)
    return "".join(lines)


def _reuse_recorded_branch(
    cfg: Config, root: Path, branch: str
) -> tuple[str, tuple[str, ...]]:
    remote = cfg.git_remote
    remote_ref = f"refs/remotes/{remote}/{branch}"
    try:
        # Ask the remote whether the branch exists (exit status and ref
        # listing, not localized fetch stderr), then fetch only one that does.
        remote_oid = git.remote_branch_oid(root, remote, branch)
        if remote_oid is not None:
            git.run_git(
                root, "fetch", "--quiet", remote, f"+refs/heads/{branch}:{remote_ref}"
            )
            remote_oid = _ref_oid(root, remote_ref)
    except git.GitError as exc:
        raise CheckoutPreparationError(
            "branch reuse", f"could not fetch {remote}/{branch}: {exc}"
        ) from exc
    local = _ref_oid(root, f"refs/heads/{branch}")
    if local is None and remote_oid is None:
        raise CheckoutPreparationError(
            "branch reuse",
            f"the recorded branch {branch!r} exists neither locally nor on "
            f"{remote}; recover it (or correct `## Dev`) rather than relaunching "
            "into an empty replacement",
        )
    if local is None:
        assert remote_oid is not None
        git.run_git(root, "branch", "--no-track", branch, remote_oid)
        return remote_oid, ()
    if remote_oid is None or remote_oid == local:
        return local, ()
    if git._is_ancestor(root, local, remote_oid):
        if git.worktree_holding_branch(root, branch) is None:
            git.run_git(root, "update-ref", f"refs/heads/{branch}", remote_oid, local)
            return remote_oid, ()
        return local, ()
    relation = "ahead of" if git._is_ancestor(root, remote_oid, local) else "diverged from"
    note = (
        f"Local `{branch}` is {relation} {remote}/{branch}; its commits were kept. "
        "Reconcile per coga/checkouts/reconciliation before pushing."
    )
    return local, (note,)


def _check_switch_target(cfg: Config, root: Path, branch: str, control_oid: str) -> None:
    holder = git.worktree_holding_branch(root, branch)
    if holder is not None:
        raise CheckoutPreparationError(
            "switch", f"{branch!r} is checked out in another worktree ({holder})"
        )
    target = _ref_oid(root, f"refs/heads/{branch}")
    if target is None:
        raise CheckoutPreparationError("switch", f"{branch!r} no longer exists")
    collisions = git._ignored_collisions(root, [control_oid, target])
    if collisions:
        raise CheckoutPreparationError(
            "switch",
            "switching would overwrite ignored files: " + ", ".join(collisions),
        )


def _guard_stranded_ticket(
    cfg: Config, root: Path, branch: str, control_oid: str, rel: str
) -> None:
    """Refuse a branch whose committed ticket holds intent control lacks."""
    target = _ref_oid(root, f"refs/heads/{branch}")
    assert target is not None
    base = git.run_git(root, "merge-base", control_oid, target).strip() or None
    on_branch = git._blob_oid(root, target, rel)
    at_base = git._blob_oid(root, base, rel) if base else None
    on_control = git._blob_oid(root, control_oid, rel)
    if on_branch in {at_base, on_control}:
        return
    raise CheckoutPreparationError(
        "stranded ticket",
        f"{branch!r} commits its own {rel} that control does not carry; "
        "preserve what it holds in the control ticket and restore the merge "
        "base's copy on the branch (coga/checkouts, \"Stranded ticket writes\") "
        "before relaunching",
    )


def _switch(root: Path, branch: str, stage: str) -> None:
    try:
        git.run_git(root, "switch", "--quiet", branch)
    except git.GitError as exc:
        raise CheckoutPreparationError(stage, f"`git switch {branch}` failed: {exc}") from exc


def _head(root: Path) -> str:
    return git.run_git(root, "rev-parse", "HEAD").strip()


def _ref_oid(root: Path, ref: str) -> str | None:
    result = git._run(
        ["git", "-C", str(root), "rev-parse", "-q", "--verify", f"{ref}^{{commit}}"]
    )
    return result.stdout.decode().strip() or None if result.returncode == 0 else None


def _status(root: Path) -> str:
    return git.run_git(
        root, "status", "--porcelain", "--untracked-files=all"
    ).strip()


def _slug(id_slug: str) -> str:
    return _BRANCH_SLUG_RE.sub("-", id_slug).strip("-.")[:48] or "task"


def _fresh_branch_name(cfg: Config, root: Path, prefix: str) -> str:
    for _ in range(8):
        name = f"{prefix}-{secrets.token_hex(3)}"
        if (
            _ref_oid(root, f"refs/heads/{name}") is None
            and not git._ref_present(root, f"refs/remotes/{cfg.git_remote}/{name}")
        ):
            return name
    raise CheckoutPreparationError("reservation", f"no free branch name under {prefix}")


# --- receipts -----------------------------------------------------------------


def _receipt_path(root: Path, rel: str) -> Path:
    digest = hashlib.sha256(rel.encode()).hexdigest()[:16]
    receipts = Path(git.run_git(root, "rev-parse", "--git-path", _RECEIPT_DIR).strip())
    if not receipts.is_absolute():
        receipts = root / receipts
    return receipts / f"ticket-{digest}.json"


def _read_receipt(cfg: Config, root: Path, rel: str) -> dict | None:
    path = _receipt_path(root, rel)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise CheckoutPreparationError(
            "reservation", f"cannot read receipt {path}: {exc}; inspect or remove it"
        ) from exc
    if (
        not isinstance(data, dict)
        or data.get("task") != rel
        or data.get("root") != str(root)
        or not isinstance(data.get("branch"), str)
        or not isinstance(data.get("oid"), str)
    ):
        raise CheckoutPreparationError(
            "reservation",
            f"receipt {path} belongs to another task or checkout; it was kept "
            "for diagnosis — remove it once its branch is accounted for",
        )
    return data


def _write_receipt(cfg: Config, root: Path, rel: str, data: dict) -> None:
    path = _receipt_path(root, rel)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        raise CheckoutPreparationError(
            "reservation", f"cannot write receipt {path}: {exc}"
        ) from exc


def _update_receipt(
    cfg: Config, root: Path, rel: str, *, stage: str, missing_ok: bool = False
) -> None:
    data = _read_receipt(cfg, root, rel)
    if data is None:
        if missing_ok:
            return
        raise CheckoutPreparationError("reservation", f"receipt for {rel} disappeared")
    data["stage"] = stage
    _write_receipt(cfg, root, rel, data)


def _discard_receipt(cfg: Config, root: Path, rel: str) -> None:
    """Control's recorded branch supersedes any reservation for this task.

    Called once control's ticket records a branch (reuse, or a completed
    entry): whatever stage the receipt reached (a `linked` one whose
    publication later landed, or an abandoned reservation of another name),
    it must not resurrect its name or base if that line is later removed.
    Unlinking never deletes a branch; an unreadable receipt is kept for
    diagnosis.
    """
    path = _receipt_path(root, rel)
    try:
        data = _read_receipt(cfg, root, rel)
    except CheckoutPreparationError:
        return
    if data is not None:
        try:
            path.unlink()
        except OSError:
            pass


# --- direct chat --------------------------------------------------------------


@dataclass(frozen=True)
class ChatSession:
    """The live direct chat holding a checkout's orientation guard."""

    session: str
    root: Path
    pid: int
    branch: str
    receipt: Path


def orientation_lock_paths(root: Path) -> tuple[Path, Path]:
    """The orientation guard's lock file and its companion chat receipt."""
    checkout = hashlib.sha256(os.fsencode(root.resolve())).hexdigest()
    lock_root = lock_dir("coga-orientation")
    return lock_root / f"{checkout}.lock", lock_root / f"{checkout}.json"


def install_chat_session(cfg: Config, root: Path) -> ChatSession:
    """Record the guard holder's identity; replaces any earlier chat's receipt.

    Called with the orientation guard already held, under the state lock, so
    a newly admitted guard never exposes a previous session's receipt.
    Reserving the name creates no branch.
    """
    _, receipt = orientation_lock_paths(root)
    token = secrets.token_hex(6)
    session = ChatSession(token, root.resolve(), os.getpid(), f"coga/chat-{token}", receipt)
    with git.state_lock(cfg):
        _write_chat_receipt(session, created=None)
    return session


def clear_chat_session(cfg: Config, session: ChatSession) -> None:
    """Remove this session's receipt (never its branch) at guard release."""
    try:
        with git.state_lock(cfg):
            data = _load_json(session.receipt)
            if isinstance(data, dict) and data.get("session") == session.session:
                session.receipt.unlink()
    except (OSError, git.GitError):
        pass


def chat_prepare_command(session: ChatSession) -> str:
    return f"coga run {PREPARE_RECIPE} --session {session.session}"


def chat_notice(cfg: Config, session: ChatSession | None, *, armed: bool, reason: str = "") -> CheckoutNotice:
    control = cfg.git_control_branch
    if armed:
        summary = (
            f"This chat starts on a clean {control!r} at "
            f"{cfg.git_remote}/{control} in {session.root if session else cfg.repo_root}."
        )
        returns = (
            "When the chat ends, `coga launch` publishes Coga state and returns "
            f"this checkout to a clean {control!r}; it refuses, preserving them, "
            "over uncommitted source changes. Conversation turns do not return it."
        )
    else:
        summary = f"Launch did not prepare this checkout: {reason or 'Git preparation is unavailable'}."
        returns = "Nothing returns this checkout automatically."
    return CheckoutNotice(
        summary=summary,
        return_owner=returns,
        prepare_command=chat_prepare_command(session) if session else None,
    )


def _write_chat_receipt(
    session: ChatSession, *, created: str | None, reserved: str | None = None
) -> None:
    session.receipt.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write_text(session.receipt, json.dumps({
        "session": session.session,
        "root": str(session.root),
        "pid": session.pid,
        "branch": session.branch,
        "reserved_oid": reserved,
        "created_oid": created,
    }, sort_keys=True) + "\n")


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except ValueError:
        return {}


@contextmanager
def _guard_is_held(lock: Path) -> Iterator[bool]:
    try:
        fd = os.open(lock, os.O_RDWR)
    except FileNotFoundError:
        yield False
        return
    try:
        try:
            lock_fd(fd, blocking=False)
        except BlockingIOError:
            yield True
            return
        except OSError as exc:
            if exc.errno in {errno.EAGAIN, errno.EACCES}:
                yield True
                return
            raise
        unlock_fd(fd)
        yield False
    finally:
        os.close(fd)


def _pid_alive(pid: int) -> bool:
    return process_is_running(pid)


@dataclass(frozen=True)
class ChatPreparation:
    kind: Literal["prepared", "reused", "exempt"]
    root: Path
    branch: str | None
    detail: str = ""


def prepare_chat_checkout(cfg: Config, session_id: str) -> ChatPreparation:
    """Create or reuse the live chat's one branch through the shared mechanics.

    The session must match the current root and the still-held orientation
    guard; a stale receipt or a bare identifier proves nothing. On the
    session's own branch the call is a verified no-op, even over that
    session's dirty work, and publishes nothing. From a clean control it
    switches back to the branch this chat created when the branch still
    descends from its creation commit (keeping the chat's commits). The
    create-and-verify core is `_create_reserved_branch`, shared with ticket
    preparation; the receipt stays separate because it is bound to the live
    occupancy guard, not to a task.
    """
    if not cfg.git_enabled:
        raise CheckoutPreparationError("session", "Git is disabled; there is no chat guard")
    root = git.toplevel(cfg.repo_root)
    if root is None:
        raise CheckoutPreparationError("session", "not a Git checkout; there is no chat guard")
    lock, receipt = orientation_lock_paths(root)
    with git.state_lock(cfg), _guard_is_held(lock) as held:
        data = _load_json(receipt)
        if not held or not isinstance(data, dict):
            raise CheckoutPreparationError(
                "session", f"no live direct chat holds {root}; nothing was changed"
            )
        if (
            data.get("session") != session_id
            or data.get("root") != str(root.resolve())
            or not isinstance(data.get("pid"), int)
            or not _pid_alive(data["pid"])
        ):
            raise CheckoutPreparationError(
                "session",
                f"session {session_id!r} is not the live chat in {root}; a new chat "
                "does not adopt an earlier chat's branch — recover it under "
                "coga/checkouts/launch-boundary",
            )
        session = ChatSession(
            session_id, root.resolve(), data["pid"], str(data["branch"]), receipt
        )
        created = data.get("created_oid")
        head = git.symbolic_head(root)
        if head == session.branch:
            if not created:
                raise CheckoutPreparationError(
                    "session", f"HEAD is {head!r} but this session never created it"
                )
            return ChatPreparation("reused", root, session.branch)
        if head != cfg.git_control_branch:
            raise CheckoutPreparationError(
                "occupied",
                f"HEAD is {head or 'detached'!r}, neither {cfg.git_control_branch!r} "
                f"nor this chat's {session.branch!r}; nothing was adopted",
            )
        if not git.remote_configured(root, cfg.git_remote):
            return ChatPreparation(
                "exempt", root, None,
                f"no {cfg.git_remote!r} remote: no branch was prepared; follow "
                "coga/checkouts manually",
            )
    _, control_oid = _prove_control(cfg, "entry")
    with git.state_lock(cfg):
        data = _load_json(receipt)
        if not isinstance(data, dict) or data.get("session") != session_id:
            raise CheckoutPreparationError("session", "the chat ended during preparation")
        reserved = data.get("reserved_oid")
        created = data.get("created_oid")
        if created:
            # Rerun after the chat committed on its branch and went back to
            # control: reuse it when it still descends from where this chat
            # created it; a moved-away or foreign tip is never adopted.
            existing = _ref_oid(root, f"refs/heads/{session.branch}")
            if existing is None:
                raise CheckoutPreparationError(
                    "branch creation",
                    f"{session.branch!r} was created by this chat but no longer exists",
                )
            if not git._is_ancestor(root, created, existing):
                raise CheckoutPreparationError(
                    "reservation",
                    f"{session.branch!r} is at {existing}, which does not descend "
                    f"from {created} where this chat created it; nothing was adopted",
                )
        else:
            if reserved is None:
                if _ref_oid(root, f"refs/heads/{session.branch}") is not None:
                    raise CheckoutPreparationError(
                        "reservation",
                        f"{session.branch!r} already exists, but this chat never "
                        "reserved it; nothing was adopted",
                    )
                reserved = control_oid
                _write_chat_receipt(session, reserved=reserved, created=None)
            _create_reserved_branch(
                cfg, root, session.branch, reserved,
                evidence=f"the reservation in {receipt}",
            )
            existing = reserved
            # A branch command may have succeeded before its caller failed or
            # the receipt write was interrupted. Only its reserved tip qualifies.
            try:
                _write_chat_receipt(session, reserved=reserved, created=existing)
            except OSError as exc:
                raise CheckoutPreparationError(
                    "branch creation",
                    f"created {session.branch!r} at {existing}, but could not record "
                    f"it: {exc}. The branch and reservation in {receipt} are retained; "
                    "retry the same command",
                ) from exc
        if _status(root):
            raise CheckoutPreparationError("switch", "the control checkout became dirty")
        _check_switch_target(cfg, root, session.branch, _head(root))
        _switch(root, session.branch, "switch")
        if git.symbolic_head(root) != session.branch:
            raise CheckoutPreparationError("verification", "HEAD is not the chat branch", switched=True)
    return ChatPreparation("reused" if created else "prepared", root, session.branch)


def run_prepare_checkout_recipe(cfg: Config, argv: list[str]) -> int:
    """`coga run prepare-checkout --session <id>`: 0 ready, 2 usage, 75 refused."""
    if len(argv) == 2 and argv[0] == "--session" and argv[1]:
        session_id = argv[1]
    elif len(argv) == 1 and argv[0].startswith("--session=") and argv[0][10:]:
        session_id = argv[0][10:]
    else:
        sys.stderr.write(f"usage: coga run {PREPARE_RECIPE} --session <id>\n")
        return 2
    try:
        result = prepare_chat_checkout(cfg, session_id)
    except (CheckoutPreparationError, git.GitError, OSError) as exc:
        sys.stderr.write(f"{PREPARE_RECIPE}: {exc}\n")
        return git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    if result.kind == "exempt":
        print(f"exempt: {result.root}: {result.detail}")
    else:
        print(f"{result.kind}: branch {result.branch} in {result.root}")
    return 0


__all__ = [
    "ChatPreparation",
    "ChatSession",
    "CheckoutPreparationError",
    "PREPARE_RECIPE",
    "TicketCheckoutPlan",
    "chat_notice",
    "chat_prepare_command",
    "clear_chat_session",
    "confirm_ticket_checkout",
    "enter_ticket_checkout",
    "insert_branch_line",
    "install_chat_session",
    "orientation_lock_paths",
    "plan_ticket_checkout",
    "prepare_chat_checkout",
    "run_prepare_checkout_recipe",
    "ticket_notice",
]
