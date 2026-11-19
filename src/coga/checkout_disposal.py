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

The `retires.md` backlog walk (`dispose_worklist_backlog`) lives here too:
autoclose drains every open entry with it, and the branch sweep drains the
entries its own clone owns. `CheckoutOutcome` is what that walk returns.

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

import shlex
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from coga import git
from coga.dev_links import (
    parse_branch_names,
    parse_pr_url,
    parse_worktree_path,
    read_dev_blackboard,
)
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
from coga.retire_worklist import (
    RetireFollowUp,
    RetireWorklistError,
    _recorded_relation,
    branch_owner,
    is_primary_checkout,
    owner_branch_remains,
    parse_worklist,
    worktree_owner,
)
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
    in every path. A recorded worktree that exists but is not this
    repository's own checkout skips all branch cleanup here: its branch is
    judged only in the repository that owns it. A proof that raises preserves the checkout with the failure
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
            if _foreign_checkout(root, disposal.worktree):
                # A recorded checkout that exists but is not this repository's
                # linked worktree keeps its branch in the repository that owns
                # it; a same-named branch here is never judged.
                note(
                    f"Branch cleanup: skipped — recorded worktree {disposal.worktree!r} "
                    "is not this repository's linked worktree, so branch "
                    f"{disposal.branch!r} is not judged in this clone."
                )
                return disposal
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


def _foreign_checkout(root: Path, worktree: str | None) -> bool:
    """Whether a recorded `worktree:` exists but is not this repository's own.

    Foreign linked worktrees, other repositories' primary checkouts, and
    directories `git.classify_checkout` cannot answer for all count; this
    repository's primary and linked checkouts do not. A missing directory is
    not foreign: that is the ordinary already-gone path.
    """
    relation = _recorded_relation(root, worktree)
    if relation is None:
        return bool(worktree) and resolve_worktree_path(root, worktree).is_dir()
    return relation.kind not in {"primary", "linked"}


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


def describe_checkout(branch: str | None, worktree: str | None) -> str:
    """What is still on disk for one recorded checkout, for a report line."""
    parts = []
    if worktree:
        parts.append(f"worktree `{worktree}`")
    if branch:
        parts.append(f"branch `{branch}`")
    return ", ".join(parts)


@dataclass
class CheckoutOutcome:
    """One recorded checkout the disposal phase judged, and what became of it.

    Candidates are the tickets this sweep closed (`title` set) and the open
    `retires.md` entries carried over from earlier runs (`title` None). A
    backlog entry's ticket may already be gone — retire preserved the checkout
    and then deleted the ticket — so `ticket_exists` says whether the manual
    `coga retire <slug>` still resolves.
    """

    slug: str
    title: str | None
    branch: str | None
    worktree: str | None
    ticket_exists: bool
    disposal: CheckoutDisposal
    home: git.CheckoutRelation | None = None
    """`git.classify_checkout`'s verdict, set only when the worktree proof
    refused the path as not a linked worktree of this repository."""
    worktree_path: Path | None = None
    """The recorded `worktree:` resolved against the sweep's git root."""
    branch_owner: Path | None = None
    """The other repository a backlog entry's branch lives in, set only when
    its worktree is gone and the proofs here therefore never ran."""
    owner_unreadable: bool = False
    """`branch_owner` is only the recorded path: it is gone or git cannot
    read it, so nobody knows where the branch lives now."""

    @property
    def disposed(self) -> bool:
        return self.disposal.disposed

    @property
    def checkout_state(self) -> str:
        return describe_checkout(self.branch, self.worktree)

    @property
    def not_linked(self) -> bool:
        result = self.disposal.worktree_result
        return result is not None and result.not_linked

    @property
    def manual_command(self) -> str:
        """What a human does about a preserved checkout, as one actionable remedy.

        `coga retire <slug>` only helps when its own proofs could pass from
        this repository and the task still exists here. A worktree refused as
        not a linked worktree of this repository is judged again
        (`git.classify_checkout`) so the remedy names where it can be removed:
        another repository's linked worktree from its owning checkout, and an
        independent clone or a path git cannot read by hand. A worktree
        already gone leaves only the branch to name.
        """
        retire = f"`coga retire {self.slug}`"
        branch_left = self.branch is not None and self.disposal.local_branch_remains
        if (
            self.owner_unreadable
            and self.branch_owner is not None
            and self.branch is not None
        ):
            return (
                f"the recorded owning clone `{self.branch_owner}` is gone or "
                "not a repository git can read, so where branch "
                f"`{self.branch}` lives is unknown: locate the clone that holds "
                "it and correct the entry's `owner` in `retires.md` to that "
                "clone's main working tree, or, once you have verified the "
                "branch landed and deleted it there by hand, remove the entry"
            )
        if self.branch_owner is not None and self.branch is not None:
            owner = shlex.quote(str(self.branch_owner))
            return (
                f"the branch lives in the owning clone `{self.branch_owner}`, "
                "not this repository: verify there that it landed, then delete "
                f"it by hand (`git -C {owner} branch -d {shlex.quote(self.branch)}`)"
            )
        if self.not_linked and self.worktree_path is not None:
            path = shlex.quote(str(self.worktree_path))
            home = self.home
            if home is not None and home.kind == "foreign-linked":
                owner = shlex.quote(str(home.owner))
                return (
                    f"the worktree belongs to `{home.owner}`, not this "
                    f"repository: {retire} fails the same proof from here and "
                    "the task does not exist there — inspect it first with "
                    f"`git -C {owner} worktree list --porcelain` and "
                    f"`git -C {path} status --short --untracked-files=all --ignored`; "
                    f"verify it still holds recorded branch `{self.branch}` and "
                    "preserve tracked, untracked, and ignored local data. "
                    "Before removing anything, verify no live ticket or open PR "
                    "claims it, and prove the branch landed or still equals its "
                    "recorded merged PR head in the owning repository. "
                    "Plan worktree and branch cleanup together: a squash- or "
                    "rebase-merged tip may require guarded forced branch deletion "
                    "after exact merged-head verification; ordinary branch -d "
                    "can refuse it. Keep the worktree until that plan is verified."
                )
            if home is not None and home.kind in {"primary", "foreign-primary"}:
                return (
                    f"`{self.worktree_path}` is a primary checkout — preserve it; "
                    "inspect the recorded branch in that repository "
                    "(see `coga/checkout-cleanup`, \"Primary checkouts and other clones\")"
                )
            what = "not a git worktree git can read"
            return (
                f"`{self.worktree_path}` is {what}, which no proof removes — "
                f"inspect and remove it by hand{self._branch_only(branch_left)}"
            )
        worktree_result = self.disposal.worktree_result
        if (
            branch_left
            and self.disposal.claim is None
            and worktree_result is not None
            and worktree_result.already_gone
        ):
            return "the worktree is already gone" + self._branch_only(True)
        if self.ticket_exists:
            return retire
        return "dispose of the recorded worktree and branch by hand"

    def _branch_only(self, branch_left: bool) -> str:
        if not branch_left:
            return ""
        if self.ticket_exists:
            return f"; then `coga retire {self.slug}` for branch `{self.branch}`"
        return (
            f"; then delete branch `{self.branch}` by hand "
            f"(`git branch -d {shlex.quote(self.branch or '')}`)"
        )


def dispose_worklist_backlog(
    cfg: Config,
    root: Path,
    worklists: list[Path],
    *,
    seen: set[str],
    echo: Callable[[str], Callable[[str], None]],
    include: Callable[[RetireFollowUp], bool] | None = None,
    label: str = "autoclose",
) -> list[CheckoutOutcome]:
    """Judge every open `retires.md` entry under the shared retire proofs.

    The backlog half of autoclose's disposal phase, shared with the
    clone-scoped branch sweep, which passes `include=retire_worklist.owned_here`
    to judge only the entries its own clone owns. The caller has already
    checked that `root` is on the control branch. Slugs in `seen` are skipped
    and every walked slug is added to it. Each entry goes through
    `checkout_disposal.dispose_checkout`, unless its branch lives in another
    clone (`owner_held_branch`); nothing here rewrites a worklist.
    """
    outcomes: list[CheckoutOutcome] = []
    for path in worklists:
        try:
            _, entries = parse_worklist(path.read_text(encoding="utf-8"))
        except (RetireWorklistError, OSError, UnicodeError) as exc:
            # The caller's reconcile fails the run loudly over the same file;
            # here it only means its backlog is not walked this time.
            sys.stderr.write(f"[{label}] backlog in {path} not walked: {exc}\n")
            continue
        for entry in entries:
            if entry.slug in seen or (include is not None and not include(entry)):
                continue
            seen.add(entry.slug)
            branch = entry.branch or None
            # An entry recorded before the primary-checkout rule may still
            # name it; only the branch half is debt (and the reconcile drops
            # the entry once that is gone too).
            worktree = (
                None
                if is_primary_checkout(root, entry.worktree)
                else entry.worktree or None
            )
            if branch is None and worktree is None and not entry.branches:
                continue
            ticket_exists, pr_url, owned = _entry_ticket(cfg, entry.slug)
            held = owner_held_branch(
                root,
                entry,
                branch=branch,
                worktree=worktree,
                ticket_exists=ticket_exists,
                echo=echo(entry.slug),
            )
            if held is not None:
                outcomes.append(held)
                continue
            outcomes.append(
                CheckoutOutcome(
                    slug=entry.slug,
                    title=None,
                    branch=branch,
                    worktree=worktree,
                    ticket_exists=ticket_exists,
                    disposal=dispose_checkout(
                        cfg,
                        root,
                        branch=branch,
                        worktree=worktree,
                        pr_url=pr_url,
                        echo=echo(entry.slug),
                        owned_branches=tuple(dict.fromkeys((*entry.branches, *owned))),
                    ),
                )
            )
    return outcomes


def owner_held_branch(
    root: Path,
    entry: RetireFollowUp,
    *,
    branch: str | None,
    worktree: str | None,
    ticket_exists: bool,
    echo: Callable[[str], None],
) -> CheckoutOutcome | None:
    """Judge a backlog entry whose branch lives in another clone, without proofs.

    Applies once the recorded worktree is gone or is a primary checkout,
    and the entry's recorded or inferred `owner` is
    not this repository (`retire_worklist.branch_owner`): the proofs here would
    find no local branch and call it disposed while the owning clone still
    holds it. The outcome is preserved while the owner still lists the branch
    or cannot be read (`retire_worklist.owner_branch_remains`, the verdict
    `is_discharged` gives the entry too) and names the by-hand delete in the
    owning clone — except when the recorded owner path itself is gone or
    unreadable (`retire_worklist.branch_owner` has no answer), where that
    command could not run: the outcome is marked `owner_unreadable` and asks
    for the owner to be located instead. `None` leaves the entry to the
    ordinary proofs.
    """
    if branch is None:
        return None
    if worktree is not None and resolve_worktree_path(root, worktree).is_dir():
        return None
    if not entry.owner:
        entry = replace(entry, owner=worktree_owner(root, entry.worktree))
    remains = owner_branch_remains(root, entry)
    if remains is None:
        return None
    owner = Path(entry.owner)
    unreadable = remains and branch_owner(root, entry.owner) is None
    disposal = CheckoutDisposal(branch=branch, worktree=None)
    disposal.local_branch_remains = remains
    if unreadable:
        message = (
            f"Branch cleanup: {branch!r} was recorded in the owning clone "
            f"{owner}, which is gone or cannot be read — left in place."
        )
    elif remains:
        message = (
            f"Branch cleanup: {branch!r} lives in the owning clone {owner}, "
            "not this repository (or its branches cannot be read) — left in place."
        )
    else:
        message = (
            f"Branch cleanup: {branch!r} already gone from the owning clone {owner}."
        )
    disposal.notes.append(message)
    echo(message)
    return CheckoutOutcome(
        slug=entry.slug,
        title=None,
        branch=branch,
        worktree=None,
        ticket_exists=ticket_exists,
        disposal=disposal,
        branch_owner=owner,
        owner_unreadable=unreadable,
    )


def _entry_ticket(
    cfg: Config, slug: str
) -> tuple[bool, str | None, tuple[str, ...]]:
    """Whether a worklist entry's ticket still exists, its `pr:` link, and
    every `branch:` it records.

    Exact `id_slug` match only: the CLI's unique-prefix resolution would let a
    deleted `foo` resolve to a newer `foo-followup` and borrow its `pr:`.
    """
    ref = next((t for t in list_tasks(cfg) if t.id_slug == slug), None)
    if ref is None:
        return False, None, ()
    blackboard = read_dev_blackboard(ref.ticket_path)
    if blackboard is None:
        return True, None, ()
    return True, parse_pr_url(blackboard), tuple(parse_branch_names(blackboard))


__all__ = [
    "CheckoutDisposal",
    "CheckoutOutcome",
    "describe_checkout",
    "dispose_checkout",
    "dispose_worklist_backlog",
    "live_checkout_claim",
    "owner_held_branch",
]
