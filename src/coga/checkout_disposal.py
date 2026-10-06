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

Every refusal is a note, never an exception: a sweep walking many checkouts
must report the one it could not prove and go on to the next. The notes are
the run record; `CheckoutDisposal.reason` picks the one line a human acts on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from coga.tasks import TaskRef

from coga.autoclose import parse_branch_name, parse_branch_names, parse_worktree_path
from coga.branchcleanup import (
    BranchCleanupResult,
    WorktreeCleanupResult,
    delete_branch,
    local_branch_exists,
    inspect_worktree_for_removal,
    remove_worktree,
    resolve_worktree_path,
)
from coga.config import Config, load_config, local_config_path
from coga.lifecycle import TERMINAL_STATUSES
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import list_tasks, read_ticket
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
        return self.claim is None and self.worktree_gone and not self.local_branch_remains

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
        if self.notes:
            return _strip_prefix(self.notes[-1])
        return "disposed"


def _strip_prefix(note: str) -> str:
    for prefix in ("Worktree cleanup: ", "Branch cleanup: ", "Checkout cleanup: "):
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
) -> CheckoutDisposal:
    """Remove `worktree`, then delete `branch` locally and on the remote, iff safe.

    `root` is the git working-tree root the caller runs from, on the control
    branch. `branch` / `worktree` / `pr_url` are the ticket's `## Dev` values
    (or a worklist entry's, whose ticket may be gone — `pr_url` is then None
    and the merge signal is looked up by head branch name). The claim scan
    runs first in every path. A proof that raises preserves the checkout with
    the failure noted; this never aborts the caller.
    """
    disposal = CheckoutDisposal(branch=branch or None, worktree=worktree or None)
    if disposal.branch is None and disposal.worktree is None:
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

    # A surviving terminal ticket supplies the authority for closed PRs. Use
    # the sweep's archive and history proofs; legacy owner-less worklist debt
    # retains its existing merged-only disposal path below.
    try:
        terminal_owned = any(
            status in TERMINAL_STATUSES and branch in branches
            for _, status, branches, _ in checkout_records(cfg, root)
        )
    except Exception as exc:
        disposal.claim = f"could not verify ownership: {exc}"
        note(f"Checkout cleanup: skipped ({disposal.claim}).")
        return disposal
    if terminal_owned and branch:
        from coga.branchsweep import sweep_branches

        from coga import git
        relation = git.classify_checkout(root, resolve_worktree_path(root, worktree)) if worktree else None
        if worktree and (relation is None or relation.kind != "primary"):
            checked = WorktreeCleanupResult(worktree=worktree)
            state = inspect_worktree_for_removal(
                root, resolve_worktree_path(root, worktree), branch,
                result=checked, echo=echo, local_config=local_config_path(cfg.repo_root),
            )
            if state is None and not checked.already_gone:
                disposal.worktree_result = checked
                disposal.notes.extend(checked.notes)
                disposal.local_branch_remains = local_branch_exists(root, branch)
                return disposal

        swept = sweep_branches(
            cfg, root, branches={branch},
            recorded_worktrees={branch: worktree} if worktree else {}, echo=echo,
        )
        disposal.notes.extend(swept.notes)
        disposal.branch_result = BranchCleanupResult(
            branch=branch, local_deleted=branch in swept.local_deleted,
            remote_deleted=branch in swept.remote_deleted, notes=swept.notes,
        )
        disposal.local_branch_remains = local_branch_exists(root, branch)
        if worktree:
            disposal.worktree_result = WorktreeCleanupResult(
                worktree=worktree, removed=worktree in swept.worktree_removed,
                already_gone=not resolve_worktree_path(root, worktree).exists(),
                notes=swept.notes or ["Checkout cleanup: recorded checkout preserved."],
            )
        if swept.failure:
            disposal.claim = swept.failure
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
    return disposal


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

    for label, status, branches, recorded in checkout_records(cfg, root):
        if status in TERMINAL_STATUSES:
            continue
        if branch is not None and branch in branches:
            return f"live ticket {label!r} also records branch {branch!r}"
        if source_worktree is not None and _normalized_worktree(root, recorded) == source_worktree:
            return f"live ticket {label!r} also records worktree {str(source_worktree)!r}"
    return None


def checkout_records(
    cfg: Config, root: Path,
) -> list[tuple[str, str | None, list[str], str | None]]:
    """Read explicit ownership across every workspace; incomplete scans raise.

    A record is (ticket label, status, branches, recorded checkout). Prose and
    attachments never grant ownership. The checkout applies to the first branch.
    """
    workspaces = discover_coga_repos(root, strict=True, allow_control_worktree_root=True)
    current = cfg.repo_root.resolve()
    if current not in {workspace.resolve() for workspace in workspaces}:
        raise RuntimeError(f"current Coga workspace {current} was not found under Git root {root}")
    records = []
    for workspace in workspaces:
        workspace = workspace.resolve()
        other_cfg = cfg if workspace == current else load_config(workspace, require_user=False)
        for ref in list_tasks(other_cfg):
            ticket = read_ticket(ref)
            board = read_blackboard(ref.ticket_path, blackboard_required=False)
            label = ref.id_slug if workspace == current else f"{workspace}:{ref.id_slug}"
            records.append((label, ticket.status, parse_branch_names(board), parse_worktree_path(board)))
    return records


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


def cleanup_terminal_ticket(cfg: Config, ref: "TaskRef", *, defer: bool = False) -> None:
    """Best-effort scoped cleanup, with a durable reason and existing sweep retry.

    Never remove checkouts from a terminal writer. Its caller may still be
    running in one; the scheduled sweep performs the ordinary checkout proofs.
    """
    from coga import git
    from coga.blackboard import append_blackboard_report
    from coga.branchsweep import sweep_branches

    if not cfg.git_enabled:
        return
    try:
        board = read_blackboard(ref.ticket_path, blackboard_required=False)
        branches = set(parse_branch_names(board))
        if not branches:
            return
        root = git.toplevel(cfg.repo_root)
        if root is None:
            return
        if defer or git.current_branch(root) != cfg.git_control_branch:
            notes = ["Cleanup deferred until the session has returned to control; retry with `coga run branch-sweep`."]
        else:
            result = sweep_branches(cfg, root, branches=branches, remove_worktrees=False)
            notes = result.notes
        report = "## Branch cleanup\n\n" + "\n".join(f"- {note}" for note in notes) + "\n"
        append_blackboard_report(cfg, ref.ticket_path, report)
        git.sync_task_state(cfg, ref.path, message=f"Ticket: {ref.id_slug} — branch cleanup")
    except Exception as exc:
        # Cleanup is never a rollback of a published terminal verdict.
        import sys
        sys.stderr.write(f"[cleanup] {ref.id_slug}: {exc}; retry `coga run branch-sweep`.\n")
