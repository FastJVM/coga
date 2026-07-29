"""Retire a finished ticket's feature checkout and git branch.

Local and remote feature branches accumulate because nothing prunes them once
a ticket finishes. `coga retire` is the lifecycle event that disposes of the
branch alongside the task directory: at retire time the ticket still exists, so
its recorded `branch:` (and `pr:`) under `## Dev` are still readable — no cron,
no orphan-matching guesswork.

The recorded `worktree:` checkout accumulated for the same reason, and it made
the branch half worse: a branch still checked out in a linked worktree cannot be
deleted at all, so every stale worktree pinned a branch that no sweep could
prune. Retire therefore removes the recorded linked worktree *first*
(`remove_ticket_worktree`), which unpins the branch for the cleanup below.

Worktree safety model:

  - Only a checkout Git itself identifies as a **linked worktree of this same
    repository** is removed. An independent fallback clone (the sandbox
    `/tmp` path in the `dev/code` context), an unrelated repo, and the primary
    checkout are preserved and reported.
  - The target must still hold the ticket's recorded branch, and that branch
    must either have landed on the control branch or still match the exact head
    of its merged PR. A stale path or reused branch is preserved.
  - Before `git worktree remove`, an explicit status check includes ignored
    files. Git's own unforced removal silently deletes ignored files, so any
    tracked, untracked, or ignored local state preserves the checkout. A locked
    worktree likewise survives with its failure reported.
  - Retire never removes the checkout it is running from.
  - A recorded path that is already gone is reported, not pruned: clearing the
    stale registration is a repo-wide operation that belongs to branch sweep.

Branch safety model:

  - **Never** delete the control branch (`main`) or the currently checked-out
    branch.
  - **Remote** delete is gated on the linked PR actually being `MERGED` and the
    live remote ref still equaling that PR's exact head. The delete carries a
    force-with-lease for the same tip, closing the check/delete race. Ancestry
    is *not* used: a squash-merged PR (GitHub's common default) leaves the branch
    tip not an ancestor of `main` even though the work landed.
  - **Local** delete prefers `git branch -d`, which refuses an unmerged branch.
    If that refuses but the current tip is the exact head of the merged PR (the
    squash-merge case), we log the tip SHA and force-delete `-D` so the work
    stays recoverable from the reflog. An advanced/reused branch is preserved.

`gh` missing/unauthed means the merge state can't be confirmed: the gated
deletes are skipped and reported, never forced.

Subprocess usage mirrors `autoclose.py` and `git.py`: plain `subprocess.run`
with `check=False`, no third-party git binding.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from coga.autoclose import (
    GhError,
    parse_branch_name,
    parse_pr_url,
    parse_worktree_path,
    pr_head,
    pr_state,
)
from coga.config import Config


@dataclass
class BranchCleanupResult:
    """What `delete_ticket_branch` did, for reporting and tests."""

    branch: str | None = None
    local_deleted: bool = False
    remote_deleted: bool = False
    local_worktree_path: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class WorktreeCleanupResult:
    """What `remove_ticket_worktree` did, for reporting and tests."""

    worktree: str | None = None
    removed: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class _PrCleanupAuthorization:
    """Which current refs still match the recorded merged PR head."""

    local_merged: bool = False
    remote_merged: bool = False
    remote_known: bool = False
    remote_present: bool = False
    remote_expected_tip: str | None = None


def remove_ticket_worktree(
    cfg: Config,
    root: Path,
    blackboard_text: str,
    *,
    echo: Callable[[str], None] = print,
) -> WorktreeCleanupResult:
    """Remove the linked worktree recorded under `## Dev` for one retiring ticket.

    `root` is the git working-tree root retire runs from (the control checkout).
    `blackboard_text` is the ticket's blackboard region, read while the
    `worktree:` line still exists. Returns a `WorktreeCleanupResult`; every
    decision is echoed for the human watching the retire run.

    Preserves anything it cannot prove is disposable — see the module docstring's
    worktree safety model.
    """
    result = WorktreeCleanupResult()

    recorded = parse_worktree_path(blackboard_text)
    result.worktree = recorded
    if not recorded:
        # No `## Dev` worktree line — nothing to remove (e.g. a doc-only ticket).
        return result

    branch = parse_branch_name(blackboard_text)
    if not branch:
        _wnote(
            result,
            echo,
            "Worktree cleanup: no `branch:` line recorded — cannot prove which "
            "checkout the worktree belongs to; left in place.",
        )
        return result

    path = Path(recorded).expanduser()
    if not path.is_absolute():
        path = root / path
    if not path.is_dir():
        _wnote(
            result,
            echo,
            f"Worktree cleanup: recorded worktree {recorded!r} is already gone.",
        )
        return result

    if path.is_symlink():
        _wnote(
            result,
            echo,
            f"Worktree cleanup: recorded path {recorded!r} is a symlink — left "
            "in place rather than removing its target.",
        )
        return result

    if _same_path(root, path):
        _wnote(
            result,
            echo,
            f"Worktree cleanup: {recorded!r} is the checkout running retire — "
            "left in place.",
        )
        return result

    if not _is_linked_worktree_of(root, path):
        _wnote(
            result,
            echo,
            f"Worktree cleanup: {recorded!r} is not a linked worktree of this "
            "repository (independent clone, unrelated repo, or the primary "
            "checkout) — left in place.",
        )
        return result

    checked_out = _current_branch(path)
    if checked_out != branch:
        actual = checked_out or "detached HEAD"
        _wnote(
            result,
            echo,
            f"Worktree cleanup: {recorded!r} holds {actual!r}, not the recorded "
            f"branch {branch!r} — left in place.",
        )
        return result

    local_state, status_error = _worktree_local_state(path)
    if status_error is not None:
        _wnote(
            result,
            echo,
            f"Worktree cleanup: could not inspect local state in {recorded!r} "
            f"({status_error}) — left in place.",
        )
        return result
    if local_state:
        sample = ", ".join(repr(entry) for entry in local_state[:3])
        if len(local_state) > 3:
            sample += f", and {len(local_state) - 3} more"
        _wnote(
            result,
            echo,
            f"Worktree cleanup: {recorded!r} contains tracked, untracked, or "
            f"ignored local state ({sample}) — left in place.",
        )
        return result

    if not local_branch_landed(root, branch, cfg.git_control_branch):
        authorization = _pr_cleanup_authorization(
            cfg,
            root,
            blackboard_text,
            branch,
            note=lambda message: _wnote(result, echo, message),
            prefix="Worktree cleanup",
        )
        remote_safe = (
            authorization.remote_known
            and (
                not authorization.remote_present
                or authorization.remote_merged
            )
        )
        if not authorization.local_merged or not remote_safe:
            _wnote(
                result,
                echo,
                f"Worktree cleanup: branch {branch!r} has not landed on "
                f"{cfg.git_control_branch!r} and its current refs do not exactly "
                "match the recorded merged PR — left in place.",
            )
            return result

    proc = _git(root, "worktree", "remove", str(path))
    if proc.returncode == 0:
        result.removed = True
        _wnote(result, echo, f"Worktree cleanup: removed linked worktree {recorded!r}.")
        return result

    stderr = (proc.stderr + proc.stdout).strip() or "git worktree remove failed"
    _wnote(
        result,
        echo,
        f"Worktree cleanup: could not remove {recorded!r} ({stderr}) — left in "
        "place for manual inspection.",
    )
    return result


def _is_linked_worktree_of(root: Path, path: Path) -> bool:
    """True iff `path` is a linked worktree sharing `root`'s common git dir.

    A linked worktree has its own administrative git dir while sharing the
    repository's common dir; the primary checkout and an independent clone
    report the same path for both. Comparing the common dir against `root`'s
    also rejects a linked worktree belonging to some *other* repository.
    """
    git_dir = _git_path(path, "--git-dir")
    common_dir = _git_path(path, "--git-common-dir")
    root_common_dir = _git_path(root, "--git-common-dir")
    if git_dir is None or common_dir is None or root_common_dir is None:
        return False
    return git_dir != common_dir and common_dir == root_common_dir


def _git_path(cwd: Path, flag: str) -> Path | None:
    proc = _git(cwd, "rev-parse", "--path-format=absolute", flag)
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    if not out:
        return None
    try:
        return Path(out).resolve()
    except OSError:
        return None


def _same_path(left: Path, right: Path) -> bool:
    """Best-effort identity check for destructive checkout operations."""
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def _worktree_local_state(path: Path) -> tuple[list[str], str | None]:
    """Return all tracked, untracked, and ignored state in ``path``.

    ``git worktree remove`` without ``--force`` protects ordinary dirt but
    deliberately deletes ignored files. Retire's stronger no-data-loss
    contract therefore has to ask status for ignored entries explicitly.
    """
    proc = _git(
        path,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignored",
    )
    if proc.returncode != 0:
        detail = (proc.stderr + proc.stdout).strip() or "git status failed"
        return [], detail
    return [line for line in proc.stdout.splitlines() if line], None


def _wnote(
    result: WorktreeCleanupResult, echo: Callable[[str], None], message: str
) -> None:
    result.notes.append(message)
    echo(message)


def delete_ticket_branch(
    cfg: Config,
    root: Path,
    blackboard_text: str,
    *,
    echo: Callable[[str], None] = print,
) -> BranchCleanupResult:
    """Delete the branch recorded under `## Dev` for one retiring ticket.

    `root` is the git working-tree root. `blackboard_text` is the ticket's
    blackboard region (read before the task directory is removed, so the
    `branch:`/`pr:` lines are still present). Returns a `BranchCleanupResult`
    describing the actions taken; every decision is also echoed for the human
    watching the retire run.
    """
    result = BranchCleanupResult()

    branch = parse_branch_name(blackboard_text)
    result.branch = branch
    if not branch:
        # No `## Dev` branch line — nothing to prune (e.g. a doc-only ticket).
        return result

    if branch == cfg.git_control_branch:
        _note(result, echo, f"Branch cleanup: refusing to delete control branch {branch!r}.")
        return result

    if _current_branch(root) == branch:
        _note(
            result,
            echo,
            f"Branch cleanup: {branch!r} is the checked-out branch — left in place.",
        )
        return result

    authorization = _pr_cleanup_authorization(
        cfg,
        root,
        blackboard_text,
        branch,
        note=lambda message: _note(result, echo, message),
        prefix="Branch cleanup",
    )

    local_present = _local_branch_exists(root, branch)
    delete_local_branch(
        root,
        branch,
        authorization.local_merged,
        echo,
        result,
    )
    if local_present and not result.local_deleted:
        _note(
            result,
            echo,
            f"Branch cleanup: skipping remote {cfg.git_remote}/{branch} because "
            "the local branch remains.",
        )
        return result
    if authorization.remote_known and not authorization.remote_present:
        _note(
            result,
            echo,
            f"Branch cleanup: remote {cfg.git_remote}/{branch} already gone.",
        )
        return result
    delete_remote_branch(
        cfg,
        root,
        branch,
        authorization.remote_merged,
        echo,
        result,
        expected_tip=authorization.remote_expected_tip,
    )
    return result


def _pr_cleanup_authorization(
    cfg: Config,
    root: Path,
    blackboard_text: str,
    branch: str,
    *,
    note: Callable[[str], None],
    prefix: str,
) -> _PrCleanupAuthorization:
    """Authorize only refs equal to the recorded merged PR's exact head.

    The PR state alone is insufficient: a branch may be reused after merge, or
    another checkout may push a newer remote tip. Local and remote refs are
    checked independently so landed local cleanup can proceed without deleting
    a newer remote branch.
    """
    authorization = _PrCleanupAuthorization()
    url = parse_pr_url(blackboard_text)
    if not url:
        note(f"{prefix}: no `pr:` link recorded — cannot confirm merge.")
        return authorization
    try:
        state = pr_state(url)
    except GhError as exc:
        note(f"{prefix}: could not check PR state ({exc}).")
        return authorization
    if state != "MERGED":
        note(f"{prefix}: PR is {state} (not MERGED).")
        return authorization

    try:
        head_branch, head_oid = pr_head(url)
    except GhError as exc:
        note(f"{prefix}: could not check the merged PR head ({exc}).")
        return authorization
    if head_branch != branch:
        note(
            f"{prefix}: merged PR head is {head_branch!r}, not the recorded "
            f"branch {branch!r}."
        )
        return authorization

    local_tip = _rev_parse(root, f"refs/heads/{branch}")
    authorization.local_merged = bool(local_tip and local_tip == head_oid)
    if local_tip and not authorization.local_merged:
        note(
            f"{prefix}: local {branch!r} advanced past the merged PR head "
            f"{head_oid[:12]} — preserving it."
        )

    remote_known, remote_tip, remote_error = _remote_branch_tip(
        cfg, root, branch
    )
    authorization.remote_known = remote_known
    authorization.remote_present = remote_tip is not None
    if not remote_known:
        note(
            f"{prefix}: could not read current {cfg.git_remote}/{branch} "
            f"({remote_error}) — preserving it."
        )
        return authorization
    authorization.remote_merged = bool(remote_tip and remote_tip == head_oid)
    if authorization.remote_merged:
        authorization.remote_expected_tip = head_oid
    if remote_tip and not authorization.remote_merged:
        note(
            f"{prefix}: {cfg.git_remote}/{branch} advanced past the merged PR "
            f"head {head_oid[:12]} — preserving it."
        )
    return authorization


def _remote_branch_tip(
    cfg: Config, root: Path, branch: str
) -> tuple[bool, str | None, str | None]:
    """Return ``(known, tip, error)`` for the live configured remote ref."""
    ref = f"refs/heads/{branch}"
    proc = _git(root, "ls-remote", "--heads", cfg.git_remote, ref)
    if proc.returncode != 0:
        detail = (proc.stderr + proc.stdout).strip() or "git ls-remote failed"
        return False, None, detail
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return True, None, None
    try:
        tip, returned_ref = lines[0].split(None, 1)
    except ValueError:
        return False, None, f"unexpected ls-remote output: {lines[0]!r}"
    if returned_ref != ref:
        return False, None, f"unexpected ls-remote ref: {returned_ref!r}"
    return True, tip, None


def delete_remote_branch(
    cfg: Config,
    root: Path,
    branch: str,
    pr_merged: bool,
    echo: Callable[[str], None],
    result: BranchCleanupResult,
    *,
    expected_tip: str | None = None,
) -> None:
    """Delete `origin/<branch>` iff `pr_merged`.

    Shared with the branch-sweep recipe, whose merge signal is looked up by
    branch name instead of a ticket's `pr:` URL — the caller decides
    `pr_merged`; this function only does the git plumbing. Retire also passes
    the verified current tip as ``expected_tip`` so the delete is atomic with
    respect to a concurrent branch update.
    """
    remote = cfg.git_remote
    if not pr_merged:
        _note(
            result,
            echo,
            f"Branch cleanup: skipping remote {remote}/{branch} (no merged PR).",
        )
        return
    lease = (
        [f"--force-with-lease=refs/heads/{branch}:{expected_tip}"]
        if expected_tip
        else []
    )
    proc = _git(root, "push", *lease, remote, "--delete", branch)
    if proc.returncode == 0:
        result.remote_deleted = True
        _note(result, echo, f"Branch cleanup: deleted remote {remote}/{branch}.")
        return
    stderr = (proc.stderr + proc.stdout).strip()
    if _remote_ref_absent(stderr):
        _note(result, echo, f"Branch cleanup: remote {remote}/{branch} already gone.")
        return
    _note(result, echo, f"Branch cleanup: could not delete remote {remote}/{branch}: {stderr}")


def delete_local_branch(
    root: Path,
    branch: str,
    pr_merged: bool,
    echo: Callable[[str], None],
    result: BranchCleanupResult,
    *,
    landed_ref: str = "HEAD",
) -> None:
    """Delete the local `branch` iff safe.

    Shared with the branch-sweep recipe; see `delete_remote_branch`.
    `landed_ref` is the ref whose history authorizes a normal `-d` deletion.
    Retire runs on the control checkout and uses the default `HEAD`; branch
    sweep passes the configured control branch explicitly.
    """
    if not _local_branch_exists(root, branch):
        _note(result, echo, f"Branch cleanup: local {branch!r} not present.")
        return

    # Ancestry into the checked-out control branch is the positive "did the work
    # land" signal. `git branch -d` alone is too loose: it also accepts a branch
    # merged only into its *upstream* (`origin/<branch>`), so a pushed branch
    # whose PR is still open would be deleted on the strength of being pushed.
    # Confirming the tip is reachable from `landed_ref` means a real
    # merge-commit or fast-forward landing — safe to `-d`.
    if local_branch_landed(root, branch, landed_ref):
        safe = _git(root, "branch", "-d", branch)
        if safe.returncode == 0:
            result.local_deleted = True
            _note(result, echo, f"Branch cleanup: deleted local {branch!r}.")
            return
        stderr = (safe.stderr + safe.stdout).strip()
        result.local_worktree_path = _worktree_path_from_delete_error(stderr)
        _note(result, echo, f"Branch cleanup: could not delete local {branch!r}: {stderr}")
        return

    # Tip not reachable from HEAD. That is exactly the squash-merge shape (the
    # PR landed but the branch tip is not an ancestor of `main`), so the
    # merged-PR gate is what authorizes a forced delete; the tip SHA is logged
    # first so the work stays recoverable from the reflog.
    if not pr_merged:
        _note(
            result,
            echo,
            f"Branch cleanup: local {branch!r} has unmerged work and no merged "
            "PR — left in place.",
        )
        return

    tip = _rev_parse(root, branch)
    forced = _git(root, "branch", "-D", branch)
    if forced.returncode == 0:
        result.local_deleted = True
        tip_note = f" (was {tip})" if tip else ""
        _note(
            result,
            echo,
            f"Branch cleanup: force-deleted local {branch!r}{tip_note} — "
            "PR merged; recover with `git checkout -b` from the reflog SHA.",
        )
        return
    stderr = (forced.stderr + forced.stdout).strip()
    result.local_worktree_path = _worktree_path_from_delete_error(stderr)
    _note(result, echo, f"Branch cleanup: could not delete local {branch!r}: {stderr}")


def _note(
    result: BranchCleanupResult, echo: Callable[[str], None], message: str
) -> None:
    result.notes.append(message)
    echo(message)


def _local_branch_exists(root: Path, branch: str) -> bool:
    return (
        _git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode
        == 0
    )


def local_branch_landed(
    root: Path, branch: str, landed_ref: str = "HEAD"
) -> bool:
    """True iff the local branch tip is reachable from `landed_ref`."""
    return _is_ancestor(root, branch, landed_ref)


def _worktree_path_from_delete_error(output: str) -> str | None:
    """Extract Git's worktree path when branch deletion is refused.

    A worktree paused in rebase/bisect can appear detached in `git worktree
    list --porcelain` while Git still reserves its original branch. Git's
    deletion gate is authoritative for that hidden state, so callers can use
    this marker to preserve the remote ref too.
    """
    marker = next(
        (
            candidate
            for candidate in ("used by worktree at ", "checked out at ")
            if candidate in output
        ),
        None,
    )
    if marker is None:
        return None
    path = output.split(marker, 1)[1].splitlines()[0].strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in {"'", '"'}:
        path = path[1:-1]
    return path or "(unknown worktree)"


def _is_ancestor(root: Path, ref: str, maybe_descendant: str) -> bool:
    """True iff `ref` is an ancestor of `maybe_descendant` (i.e. it has landed)."""
    return (
        _git(root, "merge-base", "--is-ancestor", ref, maybe_descendant).returncode == 0
    )


def _current_branch(root: Path) -> str:
    proc = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _rev_parse(root: Path, ref: str) -> str:
    proc = _git(root, "rev-parse", ref)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _remote_ref_absent(stderr: str) -> bool:
    lowered = stderr.lower()
    return "remote ref does not exist" in lowered or "unable to delete" in lowered


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "LC_ALL": "C"},
    )


__all__ = [
    "BranchCleanupResult",
    "WorktreeCleanupResult",
    "remove_ticket_worktree",
    "delete_ticket_branch",
    "delete_remote_branch",
    "delete_local_branch",
    "local_branch_landed",
]
