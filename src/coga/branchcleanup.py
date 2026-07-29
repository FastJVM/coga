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
  - `git worktree remove` runs **without** `--force`, so a dirty or locked
    worktree survives with its failure reported. Uncommitted work is never
    discarded on the strength of a lifecycle transition.
  - A recorded path that is already gone is reported, not pruned: clearing the
    stale registration is a repo-wide operation that belongs to branch sweep.

Branch safety model:

  - **Never** delete the control branch (`main`) or the currently checked-out
    branch.
  - **Remote** delete is gated on the linked PR actually being `MERGED`
    (reusing `autoclose.pr_state`'s `gh pr view` check). Ancestry is *not* used:
    a squash-merged PR (GitHub's common default) leaves the branch tip not an
    ancestor of `main` even though the work landed, which a `git merge-base`
    gate would wrongly skip. Deleting `origin/<branch>` is not protected by the
    local reflog, so the merged-PR gate is the only authorization.
  - **Local** delete prefers `git branch -d`, which refuses an unmerged branch.
    If that refuses but the PR did merge (the squash-merge case), we log the tip
    SHA and force-delete `-D` so the work stays recoverable from the reflog. If
    the branch is unmerged and has no merged PR, we skip it and report rather
    than force-deleting silently.

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


def remove_ticket_worktree(
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

    path = Path(recorded).expanduser()
    if not path.is_dir():
        _wnote(
            result,
            echo,
            f"Worktree cleanup: recorded worktree {recorded!r} is already gone.",
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

    pr_merged = _pr_merged(blackboard_text, echo, result)

    delete_remote_branch(cfg, root, branch, pr_merged, echo, result)
    delete_local_branch(root, branch, pr_merged, echo, result)
    return result


def _pr_merged(
    blackboard_text: str,
    echo: Callable[[str], None],
    result: BranchCleanupResult,
) -> bool:
    """Return True iff the `## Dev` `pr:` link is MERGED on GitHub.

    A missing `pr:` line, or any `gh` failure, returns False (the gated deletes
    then skip). `gh` trouble is reported but never fatal — retire still runs.
    """
    url = parse_pr_url(blackboard_text)
    if not url:
        _note(result, echo, "Branch cleanup: no `pr:` link recorded — cannot confirm merge.")
        return False
    try:
        state = pr_state(url)
    except GhError as exc:
        _note(result, echo, f"Branch cleanup: could not check PR state ({exc}).")
        return False
    if state != "MERGED":
        _note(result, echo, f"Branch cleanup: PR is {state} (not MERGED).")
        return False
    return True


def delete_remote_branch(
    cfg: Config,
    root: Path,
    branch: str,
    pr_merged: bool,
    echo: Callable[[str], None],
    result: BranchCleanupResult,
) -> None:
    """Delete `origin/<branch>` iff `pr_merged`.

    Shared with the branch-sweep recipe, whose merge signal is looked up by
    branch name instead of a ticket's `pr:` URL — the caller decides
    `pr_merged`; this function only does the git plumbing.
    """
    remote = cfg.git_remote
    if not pr_merged:
        _note(
            result,
            echo,
            f"Branch cleanup: skipping remote {remote}/{branch} (no merged PR).",
        )
        return
    proc = _git(root, "push", remote, "--delete", branch)
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
