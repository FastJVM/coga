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
    notes: list[str] = field(default_factory=list)
    gh_unavailable: str | None = None
    remote_unavailable: str | None = None


def sweep_branches(
    cfg: Config, root: Path, *, echo: Callable[[str], None] = print
) -> BranchSweepResult:
    """Delete local/`origin` branches whose PR has merged, skipping live ones.

    `root` is the git working-tree root. Never touches `cfg.git_control_branch`,
    the currently checked-out branch, or a branch recorded on a non-terminal
    ticket. If `gh` is unavailable, the rest of the sweep is skipped and
    reported rather than force-deleting anything.
    """
    result = BranchSweepResult()
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

        cleanup = BranchCleanupResult(branch=branch)
        if branch in remote:
            delete_remote_branch(cfg, root, branch, remote_merged, echo, cleanup)
        if branch in local:
            delete_local_branch(root, branch, local_merged, echo, cleanup)

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
        item.get("headRefOid") == current_tip for item in _gh_prs(branch, "merged")
    )
    return merged and not _gh_prs(branch, "open")


def _merged_for_tip(
    branch: str, tip: str, cache: dict[tuple[str, str], bool]
) -> bool:
    key = (branch, tip)
    if key not in cache:
        cache[key] = branch_merged_without_open_pr(branch, tip)
    return cache[key]


def _gh_prs(branch: str, state: str) -> list[dict[str, object]]:
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                state,
                "--json",
                "number,headRefOid",
            ],
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
    if not isinstance(data, list):
        raise GhError(f"`gh pr list --head {branch}` returned unexpected JSON")
    return [item for item in data if isinstance(item, dict)]


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


__all__ = ["BranchSweepResult", "sweep_branches", "branch_merged_without_open_pr"]
