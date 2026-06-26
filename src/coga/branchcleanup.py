"""Delete a finished ticket's git branch as part of `coga retire`.

Local and remote feature branches accumulate because nothing prunes them once
a ticket finishes. `coga retire` is the lifecycle event that disposes of the
branch alongside the task directory: at retire time the ticket still exists, so
its recorded `branch:` (and `pr:`) under `## Dev` are still readable — no cron,
no orphan-matching guesswork.

Safety model:

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

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from coga.autoclose import GhError, parse_branch_name, parse_pr_url, pr_state
from coga.config import Config


@dataclass
class BranchCleanupResult:
    """What `delete_ticket_branch` did, for reporting and tests."""

    branch: str | None = None
    local_deleted: bool = False
    remote_deleted: bool = False
    notes: list[str] = field(default_factory=list)


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

    _delete_remote(cfg, root, branch, pr_merged, echo, result)
    _delete_local(root, branch, pr_merged, echo, result)
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


def _delete_remote(
    cfg: Config,
    root: Path,
    branch: str,
    pr_merged: bool,
    echo: Callable[[str], None],
    result: BranchCleanupResult,
) -> None:
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


def _delete_local(
    root: Path,
    branch: str,
    pr_merged: bool,
    echo: Callable[[str], None],
    result: BranchCleanupResult,
) -> None:
    if not _local_branch_exists(root, branch):
        _note(result, echo, f"Branch cleanup: local {branch!r} not present.")
        return

    # Ancestry into the checked-out control branch is the positive "did the work
    # land" signal. `git branch -d` alone is too loose: it also accepts a branch
    # merged only into its *upstream* (`origin/<branch>`), so a pushed branch
    # whose PR is still open would be deleted on the strength of being pushed.
    # Confirming the tip is reachable from HEAD (retire runs on the control
    # branch) means a real merge-commit or fast-forward landing — safe to `-d`.
    if _is_ancestor(root, branch, "HEAD"):
        safe = _git(root, "branch", "-d", branch)
        if safe.returncode == 0:
            result.local_deleted = True
            _note(result, echo, f"Branch cleanup: deleted local {branch!r}.")
            return
        stderr = (safe.stderr + safe.stdout).strip()
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
    )


__all__ = ["BranchCleanupResult", "delete_ticket_branch"]
