"""Dispose of a finished ticket's feature checkout: the shared orchestration.

`branchcleanup` owns the individual proofs — same-repo linked worktree, exact
recorded branch, locally pristine, no open PR, landed or at the merged PR's
exact head, then local `-d`/`-D` and a leased remote delete. This module owns
the proof that sits above them, **no other live ticket claims the checkout**,
and the order the whole set runs in: claim scan, then the worktree (which
unpins the branch), then the local branch, then its `origin` counterpart.

Three callers share it, which is what earns it a home in core:

- `coga retire`, the lifecycle event that disposes of a ticket's checkout by
  hand;
- the daily autoclose sweep, which disposes of every checkout it closes and
  drains the `retires.md` backlog — including entries whose ticket retire
  already deleted, so the proofs take the branch and worktree directly rather
  than `## Dev` text;
- the weekly branch sweep, which reuses the claim scan before GC'ing a
  worktree no ticket recorded.

A finished ticket may own more than one branch (every `## Dev` `branch:`
line), and its PR may have been closed rather than merged. After the
merged-PR proofs here, every owned branch still present locally or on the
remote goes through `branchsweep.sweep_branches` restricted to those names:
the sweep's terminal-owner authority, post-head commit inspection, and
`retired/<branch>` archive decide them, and its notes join this disposal's.

Every refusal is a note, never an exception: a sweep walking many checkouts
must report the one it could not prove and go on to the next. The notes are
the run record; `CheckoutDisposal.reason` picks the one line a human acts on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from coga.autoclose import parse_branch_names, parse_worktree_path
from coga.branchcleanup import (
    BranchCleanupResult,
    WorktreeCleanupResult,
    _remote_branch_tip,
    delete_branch,
    local_branch_exists,
    remove_worktree,
    resolve_worktree_path,
)
from coga.config import Config, ConfigError, load_config
from coga.lifecycle import TERMINAL_STATUSES
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import list_tasks, read_ticket
from coga.ticket import TicketError
from coga.workspace_discovery import discover_coga_repos


@dataclass
class CheckoutDisposal:
    """What `dispose_checkout` did to one recorded checkout, for reporting and tests."""

    branch: str | None
    worktree: str | None
    notes: list[str] = field(default_factory=list)
    # Why the proofs never ran: another live ticket's claim, or a claim scan
    # that could not complete (an incomplete proof preserves the checkout).
    claim: str | None = None
    worktree_result: WorktreeCleanupResult | None = None
    branch_result: BranchCleanupResult | None = None
    local_branch_remains: bool = False
    # Owned branches (the recorded `branch:` included) whose local ref
    # survived the owned-branch sweep. Like `local_branch_remains`, a remote
    # leftover is reported in the notes and retried by the daily sweep.
    branches_remaining: list[str] = field(default_factory=list)

    @property
    def worktree_gone(self) -> bool:
        if not self.worktree:
            return True
        result = self.worktree_result
        return result is not None and (result.removed or result.already_gone)

    @property
    def disposed(self) -> bool:
        """Nothing left to dispose of: worktree directory and local branch gone.

        The same rule `retire_worklist.is_discharged` applies to a worklist
        entry; the remote ref is best effort and the weekly sweep's to catch.
        """
        return (
            self.claim is None
            and self.worktree_gone
            and not self.local_branch_remains
            and not self.branches_remaining
        )

    @property
    def reason(self) -> str:
        """The one refusal a human acts on, for a summary line."""
        if self.claim:
            return self.claim
        if not self.worktree_gone and self.worktree_result is not None:
            return _strip_prefix(self.worktree_result.notes[-1])
        if self.local_branch_remains and self.branch_result is not None:
            # The trailing "skipping remote ... because the local branch
            # remains" line only restates the refusal before it.
            informative = [
                note
                for note in self.branch_result.notes
                if not note.startswith("Branch cleanup: skipping remote")
            ]
            if informative:
                return _strip_prefix(informative[-1])
        if self.branches_remaining:
            return (
                "owned branch(es) "
                + ", ".join(repr(name) for name in self.branches_remaining)
                + " left in place; see the branch sweep notes"
            )
        if self.notes:
            return _strip_prefix(self.notes[-1])
        return "disposed"


def _strip_prefix(note: str) -> str:
    for prefix in (
        "Worktree cleanup: ", "Branch cleanup: ", "Checkout cleanup: ", "Branch sweep: ",
    ):
        if note.startswith(prefix):
            return note[len(prefix):]
    return note


def dispose_checkout(
    cfg: Config,
    root: Path,
    *,
    branch: str | None,
    worktree: str | None,
    pr_url: str | None,
    echo: Callable[[str], None] = print,
    owned_branches: list[str] | tuple[str, ...] = (),
) -> CheckoutDisposal:
    """Remove `worktree`, then delete `branch` locally and on the remote, iff safe.

    `root` is the git working-tree root the caller runs from, on the control
    branch. `branch` / `worktree` / `pr_url` are the ticket's `## Dev` values
    (or a worklist entry's, whose ticket may be gone — `pr_url` is then None
    and the merge signal is looked up by head branch name). `owned_branches`
    are the ticket's other recorded `branch:` names. The claim scan runs first
    in every path. A proof that raises preserves the checkout with the failure
    noted; this never aborts the caller.
    """
    disposal = CheckoutDisposal(branch=branch or None, worktree=worktree or None)
    owned = [
        name for name in dict.fromkeys([disposal.branch, *owned_branches]) if name
    ]
    if not owned and disposal.worktree is None:
        return disposal

    def note(message: str) -> None:
        disposal.notes.append(message)
        echo(message)

    try:
        claim = live_checkout_claim(
            cfg, root, branch=disposal.branch, worktree=disposal.worktree
        )
    except Exception as exc:  # noqa: BLE001 — incomplete proof preserves checkout
        disposal.claim = f"could not verify other live ticket claims: {exc}"
        note(f"Checkout cleanup: skipped ({disposal.claim}).")
        return disposal
    if claim is not None:
        disposal.claim = claim
        note(f"Checkout cleanup: skipped ({claim}).")
        return disposal

    if disposal.worktree is not None:
        if disposal.branch is None:
            note(
                "Worktree cleanup: no `branch:` recorded — cannot prove which "
                f"checkout {disposal.worktree!r} belongs to; left in place."
            )
        else:
            try:
                disposal.worktree_result = remove_worktree(
                    cfg,
                    root,
                    disposal.worktree,
                    disposal.branch,
                    pr_url=pr_url,
                    echo=echo,
                )
            except Exception as exc:  # noqa: BLE001 — never let one checkout abort a sweep
                disposal.worktree_result = WorktreeCleanupResult(
                    worktree=disposal.worktree
                )
                _record(
                    disposal.worktree_result.notes,
                    note,
                    f"Worktree cleanup: failed ({exc}) — left in place.",
                )
            else:
                disposal.notes.extend(disposal.worktree_result.notes)

    if disposal.branch is not None:
        try:
            disposal.branch_result = delete_branch(
                cfg, root, disposal.branch, pr_url=pr_url, echo=echo
            )
        except Exception as exc:  # noqa: BLE001 — same
            disposal.branch_result = BranchCleanupResult(branch=disposal.branch)
            _record(
                disposal.branch_result.notes,
                note,
                f"Branch cleanup: failed ({exc}) — left in place.",
            )
        else:
            disposal.notes.extend(disposal.branch_result.notes)
        disposal.local_branch_remains = local_branch_exists(root, disposal.branch)
    if disposal.worktree_gone:
        _sweep_owned_branches(cfg, root, disposal, owned, note=note, echo=echo)
    return disposal


def _sweep_owned_branches(
    cfg: Config,
    root: Path,
    disposal: CheckoutDisposal,
    owned: list[str],
    *,
    note: Callable[[str], None],
    echo: Callable[[str], None],
) -> None:
    """Send every owned branch still present through the restricted branch sweep.

    Skipped while the recorded worktree survives: the sweep would only report
    the branch pinned. A clean merged-PR disposal leaves nothing present, so
    the common path costs one remote read per owned branch and no PR lookups.
    """
    # Imported lazily: `branchsweep` imports this module for the claim scan.
    from coga.branchsweep import BranchSweepResult, sweep_branches

    try:
        present = [name for name in owned if _branch_present(cfg, root, name)]
    except RuntimeError as exc:
        disposal.branches_remaining = [
            name for name in owned if local_branch_exists(root, name)
        ]
        note(f"Branch sweep: could not read owned branches ({exc}) — left in place.")
        return
    if not present:
        return
    unclaimed: set[str] = set()
    for name in present:
        try:
            claim = live_checkout_claim(cfg, root, branch=name, worktree=None)
        except Exception as exc:  # noqa: BLE001 — incomplete proof preserves branch
            claim = f"could not verify other live ticket claims: {exc}"
        if claim is not None:
            note(f"Branch sweep: {name!r} kept ({claim}).")
        else:
            unclaimed.add(name)
    result = BranchSweepResult(notes=disposal.notes)
    try:
        if unclaimed:
            removed = (
                resolve_worktree_path(root, disposal.worktree)
                if disposal.worktree
                and disposal.worktree_result is not None
                and disposal.worktree_result.removed
                else None
            )
            sweep_branches(
                cfg, root, echo=echo, result=result, only=unclaimed,
                removed_worktree=removed,
            )
    except Exception as exc:  # noqa: BLE001 — never let one checkout abort a sweep
        note(f"Branch sweep: failed ({exc}) — owned branches left in place.")
    disposal.branches_remaining = [
        name for name in present if local_branch_exists(root, name)
    ]
    if disposal.branch is not None:
        disposal.local_branch_remains = local_branch_exists(root, disposal.branch)


def _branch_present(cfg: Config, root: Path, branch: str) -> bool:
    """Whether `branch` exists locally or on the remote; raises when unknown."""
    if local_branch_exists(root, branch):
        return True
    known, tip, error = _remote_branch_tip(cfg, root, branch)
    if not known:
        raise RuntimeError(f"{cfg.git_remote}/{branch}: {error}")
    return tip is not None


def _record(notes: list[str], note: Callable[[str], None], message: str) -> None:
    notes.append(message)
    note(message)


def live_checkout_claim(
    cfg: Config,
    root: Path,
    *,
    branch: str | None,
    worktree: str | None,
) -> str | None:
    """Describe a non-terminal ticket claiming `branch` or `worktree`, if any.

    Branches and linked worktrees belong to the whole Git repository, so the
    claim scan covers every supported Coga workspace in a monorepo rather than
    only the workspace that owns the finished ticket. The finished ticket
    itself is terminal and so never counts as a claim; a worklist entry whose
    ticket was reopened is claimed by that ticket, which is the right answer.

    Raises when the scan cannot be completed — an unreadable workspace or
    ticket — because an incomplete proof must preserve the checkout.
    """
    source_worktree = (
        _normalized_worktree(root, worktree) if worktree is not None else None
    )
    if branch is None and source_worktree is None:
        return None

    workspaces = discover_coga_repos(
        root, strict=True, allow_control_worktree_root=True
    )
    current_workspace = cfg.repo_root.resolve()
    if current_workspace not in {workspace.resolve() for workspace in workspaces}:
        raise RuntimeError(
            f"current Coga workspace {current_workspace} was not found under "
            f"Git root {root}"
        )

    for workspace in workspaces:
        workspace_path = workspace.resolve()
        try:
            workspace_cfg = (
                cfg
                if workspace_path == current_workspace
                else load_config(workspace_path, require_user=False)
            )
        except ConfigError as exc:
            raise RuntimeError(
                f"cannot inspect Coga workspace {workspace_path}: {exc}"
            ) from exc

        for other_ref in list_tasks(workspace_cfg):
            try:
                other_ticket = read_ticket(other_ref)
            except (OSError, TicketError) as exc:
                raise RuntimeError(
                    f"cannot read {other_ref.ticket_path}: {exc}"
                ) from exc
            if other_ticket.status in TERMINAL_STATUSES:
                continue
            try:
                other_blackboard = read_blackboard(
                    other_ref.ticket_path, blackboard_required=False
                )
            except (OSError, TaskFileError) as exc:
                raise RuntimeError(
                    f"cannot read {other_ref.ticket_path}'s blackboard: {exc}"
                ) from exc

            ticket_label = (
                other_ref.id_slug
                if workspace_path == current_workspace
                else f"{workspace_path}:{other_ref.id_slug}"
            )
            other_branches = parse_branch_names(other_blackboard)
            if branch is not None and branch in other_branches:
                return (
                    f"live ticket {ticket_label!r} also records branch "
                    f"{branch!r}"
                )
            other_worktree = _normalized_worktree(
                root, parse_worktree_path(other_blackboard)
            )
            if source_worktree is not None and other_worktree == source_worktree:
                return (
                    f"live ticket {ticket_label!r} also records worktree "
                    f"{str(source_worktree)!r}"
                )
    return None


def _normalized_worktree(root: Path, recorded: str | None) -> Path | None:
    if recorded is None:
        return None
    path = resolve_worktree_path(root, recorded)
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


__all__ = [
    "CheckoutDisposal",
    "dispose_checkout",
    "live_checkout_claim",
]
