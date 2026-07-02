"""Sweep stale git branches as a scheduled safety net behind retire-time deletion.

`coga retire` deletes a ticket's branch as soon as the ticket finishes (see
`branchcleanup.py`), but that cleanup is best-effort: `git`/`gh` failures are
swallowed there, and a branch also leaks when its ticket is deleted without
going through retire, or a session dies before retire runs. `sweep_branches`
is the net behind that — it walks every local and `origin` branch directly
(no ticket lookup) and deletes the ones GitHub confirms have already landed.

The merge signal differs from retire's: retire trusts a single ticket's
recorded `pr:` link (`autoclose.pr_state`, URL-keyed). A swept branch has no
ticket to point at a PR, so the check here is by **head branch name**
(`gh pr list --head <branch>`), and it requires a merged PR **and no open
PR** for that head — a branch that once merged a PR and was later reused for
a new open PR must survive; ancestry can't tell "landed" from "in flight"
once history has moved past the old merge.

Live tickets are consulted defensively before any gh lookup: a not-`done`
ticket's `## Dev` `branch:` line is skipped outright, so a ticket still
mid-workflow never loses its branch even if its PR already merged.

Reuses `branchcleanup.py`'s `delete_remote_branch` / `delete_local_branch`
for the actual git plumbing (ancestry check, `-d` then logged `-D` fallback,
never force without a merged PR) — only the merge-signal lookup differs, so
those two functions were exported (dropped their leading underscore) rather
than duplicated.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from coga.autoclose import GhError, parse_branch_name
from coga.branchcleanup import (
    BranchCleanupResult,
    delete_local_branch,
    delete_remote_branch,
)
from coga.config import Config
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import list_tasks, read_ticket
from coga.ticket import TicketError


@dataclass
class BranchSweepResult:
    """What one `sweep_branches` run did, for reporting and tests."""

    local_deleted: list[str] = field(default_factory=list)
    remote_deleted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    gh_unavailable: str | None = None


def sweep_branches(
    cfg: Config, root: Path, *, echo: Callable[[str], None] = print
) -> BranchSweepResult:
    """Delete local/`origin` branches whose PR has merged, skipping live ones.

    `root` is the git working-tree root. Never touches `cfg.git_control_branch`,
    the currently checked-out branch, or a branch recorded on a not-`done`
    ticket. If `gh` is unavailable, the rest of the sweep is skipped and
    reported rather than force-deleting anything.
    """
    result = BranchSweepResult()
    current = _current_branch(root)
    live_branches = _live_ticket_branches(cfg)
    local = set(_local_branches(root))
    remote = set(_remote_branches(cfg, root))

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

        try:
            pr_merged = branch_merged_without_open_pr(branch)
        except GhError as exc:
            result.gh_unavailable = str(exc)
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: gh unavailable ({exc}) — no gated deletes this run.")
            continue

        cleanup = BranchCleanupResult(branch=branch)
        if branch in remote:
            delete_remote_branch(cfg, root, branch, pr_merged, echo, cleanup)
        if branch in local:
            delete_local_branch(root, branch, pr_merged, echo, cleanup)

        if cleanup.local_deleted:
            result.local_deleted.append(branch)
        if cleanup.remote_deleted:
            result.remote_deleted.append(branch)
        if not cleanup.local_deleted and not cleanup.remote_deleted:
            result.skipped.append(branch)

    return result


def branch_merged_without_open_pr(branch: str) -> bool:
    """True iff `branch` has a merged PR on GitHub and no currently open PR.

    Raises `GhError` if `gh` is missing, unauthed, or errors.
    """
    return bool(_gh_pr_numbers(branch, "merged")) and not _gh_pr_numbers(branch, "open")


def _gh_pr_numbers(branch: str, state: str) -> list[int]:
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--state", state, "--json", "number"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhError("`gh` not found on PATH") from exc
    if result.returncode != 0:
        raise GhError(
            f"`gh pr list --head {branch} --state {state}` failed "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GhError(f"`gh pr list --head {branch}` returned non-JSON: {exc}") from exc
    return [item["number"] for item in data]


def _live_ticket_branches(cfg: Config) -> set[str]:
    """Branch names recorded under `## Dev` on any not-`done` ticket."""
    branches: set[str] = set()
    for ref in list_tasks(cfg):
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.status == "done":
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


def _local_branches(root: Path) -> list[str]:
    proc = _git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    return [line for line in proc.stdout.splitlines() if line]


def _remote_branches(cfg: Config, root: Path) -> list[str]:
    remote_prefix = f"{cfg.git_remote}/"
    proc = _git(root, "for-each-ref", "--format=%(refname:short)", f"refs/remotes/{cfg.git_remote}/")
    branches = []
    for line in proc.stdout.splitlines():
        if not line or line == f"{cfg.git_remote}/HEAD":
            continue
        branches.append(line[len(remote_prefix):] if line.startswith(remote_prefix) else line)
    return branches


def _current_branch(root: Path) -> str:
    proc = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


__all__ = ["BranchSweepResult", "sweep_branches", "branch_merged_without_open_pr"]
