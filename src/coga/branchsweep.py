"""Sweep stale git branches as a scheduled safety net behind retire-time deletion.

`coga retire` deletes a ticket's branch as soon as the ticket finishes (see
`branchcleanup.py`), but that cleanup is best-effort: `git`/`gh` failures are
swallowed there, and a branch also leaks when its ticket is deleted without
going through retire, or a session dies before retire runs. `sweep_branches`
is the net behind that — it walks every local and `origin` branch directly
(no ticket lookup) and deletes the ones GitHub confirms have already landed.

The merge signal differs from retire's: retire trusts a single ticket's
recorded `pr:` link (`autoclose.pr_state`, URL-keyed). A swept branch has no
ticket to point at a PR, so the check here is by **head branch name** and
current tip SHA (`gh pr list --head <branch> --json headRefOid`), and it
requires a merged PR for that exact tip **and no open PR** for that head — a
branch that once merged a PR and was later reused must survive unless the
current ref itself is the one GitHub says landed.

Live tickets are consulted defensively before any gh lookup: a non-terminal
ticket's `## Dev` `branch:` line is skipped outright, so a ticket still
mid-workflow never loses its branch even if its PR already merged.

Before enumerating branches, the sweep prunes registrations for worktrees whose
directories are gone. A merged branch that remains checked out in a live
worktree is preserved deliberately and reported as worktree-pinned instead of
falling through to a failed `git branch -d`/`-D`.

Reuses `branchcleanup.py`'s `delete_remote_branch` / `delete_local_branch`
for the actual git plumbing (ancestry check, `-d` then logged `-D` fallback,
never force without a merged PR) — only the merge-signal lookup differs, so
those two functions were exported (dropped their leading underscore) rather
than duplicated.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from coga.autoclose import GhError, parse_branch_name, prs_for_head
from coga.branchcleanup import (
    BranchCleanupResult,
    delete_local_branch,
    delete_remote_branch,
    local_branch_landed,
)
from coga.config import Config
from coga import git
from coga.lifecycle import TERMINAL_STATUSES
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import list_tasks, read_ticket
from coga.ticket import TicketError


@dataclass
class BranchSweepResult:
    """What one `sweep_branches` run did, for reporting and tests."""

    local_deleted: list[str] = field(default_factory=list)
    remote_deleted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    worktree_pinned: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    gh_unavailable: str | None = None
    remote_unavailable: str | None = None
    worktree_unavailable: str | None = None


def sweep_branches(
    cfg: Config, root: Path, *, echo: Callable[[str], None] = print
) -> BranchSweepResult:
    """Delete local/`origin` branches whose PR has merged, skipping live ones.

    `root` is the git working-tree root. Prunes registrations for missing
    worktrees first. Never touches `cfg.git_control_branch`, the currently
    checked-out branch, a branch recorded on a non-terminal ticket, or a merged
    branch still checked out in a live worktree. If worktree state or `gh` is
    unavailable, the rest of the sweep is skipped and reported rather than
    deleting with incomplete safety information.
    """
    result = BranchSweepResult()
    worktree_branches = _worktree_branches(root, result, echo)
    if result.worktree_unavailable is not None:
        return result

    current = _current_branch(root)
    live_branches = _live_ticket_branches(cfg)
    local = _local_branches(root)
    remote = _remote_branches(cfg, root, result, echo)
    merged_by_tip: dict[tuple[str, str], bool] = {}

    for branch in sorted(local | remote):
        if branch == cfg.git_control_branch:
            continue
        if branch == current:
            _note(result, echo, f"Branch sweep: {branch!r} is the checked-out branch — left in place.")
            continue
        if branch in live_branches:
            _note(result, echo, f"Branch sweep: {branch!r} is recorded on a live ticket — left in place.")
            continue

        if result.gh_unavailable is not None:
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: {branch!r} left in place (gh unavailable).")
            continue

        local_tip = local.get(branch)
        remote_tip = remote.get(branch)

        try:
            remote_merged = (
                _merged_for_tip(branch, remote_tip, merged_by_tip)
                if remote_tip is not None
                else False
            )
            local_merged = (
                _merged_for_tip(branch, local_tip, merged_by_tip)
                if local_tip is not None
                else False
            )
        except GhError as exc:
            result.gh_unavailable = str(exc)
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: gh unavailable ({exc}) — no gated deletes this run.")
            continue

        local_landed = (
            local_tip is not None
            and local_branch_landed(root, branch, cfg.git_control_branch)
        )
        if branch in worktree_branches and (
            remote_merged
            or local_merged
            or local_landed
        ):
            result.worktree_pinned.append(branch)
            _note(
                result,
                echo,
                f"Branch sweep: {branch!r} has a landed ref but is checked out "
                f"in worktree {worktree_branches[branch]!r} — left in place.",
            )
            continue

        cleanup = BranchCleanupResult(branch=branch)
        if branch in local:
            delete_local_branch(
                root,
                branch,
                local_merged,
                echo,
                cleanup,
                landed_ref=cfg.git_control_branch,
                expected_tip=local_tip,
            )

        # During rebase/bisect Git can report a worktree as detached while
        # still reserving its original branch. Let Git's own deletion gate
        # catch that hidden state before touching the remote ref.
        if cleanup.local_worktree_path is not None:
            result.worktree_pinned.append(branch)
            _note(
                result,
                echo,
                f"Branch sweep: {branch!r} has a landed ref but is held by "
                f"worktree {cleanup.local_worktree_path!r} — both refs left in place.",
            )
            continue

        # Do not delete the remote half of a branch whose local half could not
        # be removed. Besides making partial cleanup conservative, this is the
        # fallback safety gate for worktree operation states Git does not expose
        # as a branch in porcelain output.
        if branch in remote and (branch not in local or cleanup.local_deleted):
            delete_remote_branch(cfg, root, branch, remote_merged, echo, cleanup)

        if cleanup.local_deleted:
            result.local_deleted.append(branch)
        if cleanup.remote_deleted:
            result.remote_deleted.append(branch)
        if not cleanup.local_deleted and not cleanup.remote_deleted:
            result.skipped.append(branch)

    return result


def branch_merged_without_open_pr(branch: str, current_tip: str) -> bool:
    """True iff `branch`'s current tip has merged and no PR is open.

    Raises `GhError` if `gh` is missing, unauthed, or errors.
    """
    merged = any(
        item.get("headRefOid") == current_tip
        for item in prs_for_head(branch, "merged")
    )
    return merged and not prs_for_head(branch, "open")


def run_branch_sweep_recipe(cfg: Config, argv: list[str]) -> int:
    """Run the recurring branch-sweep job."""
    if argv:
        sys.stderr.write(
            f"branch-sweep: unexpected arguments: {' '.join(repr(arg) for arg in argv)}\n"
        )
        return 2
    root = git._toplevel(cfg.repo_root)
    if root is None:
        sys.stderr.write(f"[branch-sweep] {cfg.repo_root} is not inside a git repo\n")
        return 2
    result = sweep_branches(cfg, root, echo=print)
    if result.remote_unavailable:
        sys.stderr.write(f"[branch-sweep] {result.remote_unavailable}\n")
        return 2
    if result.worktree_unavailable:
        sys.stderr.write(f"[branch-sweep] {result.worktree_unavailable}\n")
        return 2
    if result.gh_unavailable:
        sys.stderr.write(f"[branch-sweep] {result.gh_unavailable}\n")
        return 2
    if result.worktree_pinned:
        sys.stdout.write(
            "[branch-sweep] skipped-worktree-pinned: "
            f"{', '.join(result.worktree_pinned)}\n"
        )
    if not result.local_deleted and not result.remote_deleted:
        sys.stdout.write("[branch-sweep] no branches deleted.\n")
    return 0


def _merged_for_tip(
    branch: str, tip: str, cache: dict[tuple[str, str], bool]
) -> bool:
    key = (branch, tip)
    if key not in cache:
        cache[key] = branch_merged_without_open_pr(branch, tip)
    return cache[key]


def _live_ticket_branches(cfg: Config) -> set[str]:
    """Branch names recorded under `## Dev` on any non-terminal ticket."""
    branches: set[str] = set()
    for ref in list_tasks(cfg):
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.status in TERMINAL_STATUSES:
            continue
        try:
            blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
        except (OSError, TaskFileError):
            continue
        name = parse_branch_name(blackboard)
        if name:
            branches.add(name)
    return branches


def _note(result: BranchSweepResult, echo: Callable[[str], None], message: str) -> None:
    result.notes.append(message)
    echo(message)


def _worktree_branches(
    root: Path,
    result: BranchSweepResult,
    echo: Callable[[str], None],
) -> dict[str, str]:
    """Prune missing worktrees and return live local branch-to-path mappings."""
    pruned = _git(root, "worktree", "prune")
    if pruned.returncode != 0:
        detail = (pruned.stderr + pruned.stdout).strip() or "git worktree prune failed"
        result.worktree_unavailable = detail
        _note(
            result,
            echo,
            f"Branch sweep: could not prune stale worktrees — sweep skipped: {detail}",
        )
        return {}

    listed = _git(root, "worktree", "list", "--porcelain")
    if listed.returncode != 0:
        detail = (
            (listed.stderr + listed.stdout).strip()
            or "git worktree list --porcelain failed"
        )
        result.worktree_unavailable = detail
        _note(
            result,
            echo,
            f"Branch sweep: could not list live worktrees — sweep skipped: {detail}",
        )
        return {}

    worktrees: dict[str, str] = {}
    path = ""
    branch_prefix = "branch refs/heads/"
    for line in listed.stdout.splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif path and line.startswith(branch_prefix):
            worktrees[line.removeprefix(branch_prefix)] = path
    return worktrees


def _local_branches(root: Path) -> dict[str, str]:
    proc = _git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    branches: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        tip = _rev_parse(root, line)
        if tip:
            branches[line] = tip
    return branches


def _remote_branches(
    cfg: Config,
    root: Path,
    result: BranchSweepResult,
    echo: Callable[[str], None],
) -> dict[str, str]:
    proc = _git(root, "ls-remote", "--heads", cfg.git_remote)
    if proc.returncode != 0:
        detail = (proc.stderr + proc.stdout).strip()
        result.remote_unavailable = detail or f"could not list {cfg.git_remote}"
        _note(
            result,
            echo,
            f"Branch sweep: could not list {cfg.git_remote} branches — remote sweep skipped: "
            f"{result.remote_unavailable}",
        )
        return {}
    branches: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        try:
            tip, ref = line.split(None, 1)
        except ValueError:
            continue
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            branches[ref[len(prefix):]] = tip
    return branches


def _current_branch(root: Path) -> str:
    proc = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _rev_parse(root: Path, ref: str) -> str:
    proc = _git(root, "rev-parse", ref)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


__all__ = [
    "BranchSweepResult",
    "branch_merged_without_open_pr",
    "run_branch_sweep_recipe",
    "sweep_branches",
]
