"""Git sync — commit and push ticket-state changes, the git analogue of Slack.

Every relay command that mutates ticket state writes files to disk and posts
to Slack, but historically did no git: the git-backed repo drifted from the
team's live state until a human committed by hand. `sync_task_state` closes
that gap. It is always-on (no per-command flag), the same way Slack is — the
only opt-out is `[git].enabled = false`.

This module is ticket A: the **same-branch** case only. When HEAD is already
the control branch (normally `main`), it commits the changed task files and
pushes. When HEAD is a feature branch, it no-ops with a warning — making task
state reach `main` *from* a feature branch is ticket B's job, and the public
signature here is shaped so B can slot that path in without reworking any
call site.

Failure model (settled with the owner, mirrors `relay/sync`'s crash-loud
philosophy): a failed git *operation* on the control branch raises `GitError`,
which is caught at the boundary, written to stderr + the task's `log.md`, and
re-raised as `typer.Exit(1)`. The one carve-out is "not a git repo": that is a
soft no-op (single stderr line), not a crash — otherwise every command run in
a non-git `relay-os/` checkout would fail. The git opt-out is `[git].enabled`.

Subprocess usage mirrors `automerge.py` (`gh` shell-out): no third-party git
binding, just `subprocess.run` with `check=False` and explicit error handling.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

from relay.config import Config
from relay.logfile import append_log


class GitError(Exception):
    """Raised when a git operation fails (git missing, or a non-zero exit).

    Distinct from the soft "not a git repo" no-op: this signals a real
    failure on the control branch that the caller surfaces as a crash.
    """


def sync_task_state(cfg: Config, task_path: Path, *, message: str) -> None:
    """Commit the task directory's files and push to the control branch.

    Always-on git analogue of `slack.post`. Behaviour:

      - `[git].enabled = false` → suppressed, one stderr line, no crash.
      - Not a git repo → soft no-op, one stderr line, no crash.
      - HEAD is a feature branch → soft no-op + warning (ticket B handles
        cross-branch land-on-`main`).
      - HEAD is the control branch → `git add` the task dir, and if anything
        is staged, commit with `message` and push to the configured remote.
        Any git operation failure raises `GitError`, which is reported to
        stderr + the task's `log.md` and re-raised as `typer.Exit(1)`.

    `task_path` is the task directory (`relay-os/tasks/<slug>/`); only files
    under it are staged, never `git add -A`, so unrelated working-tree changes
    are not swept in.
    """
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return

    try:
        root = _toplevel(task_path)
        if root is None:
            sys.stderr.write(
                f"[git] not a git repo (sync skipped): {message}\n"
            )
            return

        branch = _current_branch(root)
        if branch != cfg.git_control_branch:
            sys.stderr.write(
                f"[git] on feature branch {branch!r} — ticket state not synced to "
                f"{cfg.git_control_branch!r}; ticket B handles cross-branch sync. "
                f"({message})\n"
            )
            return

        _sync_on_control_branch(cfg, root, task_path, message=message)
    except GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        append_log(task_path, "git", f"sync failed: {exc}")
        raise typer.Exit(1)


def _sync_on_control_branch(
    cfg: Config, root: Path, task_path: Path, *, message: str
) -> None:
    """Stage the task dir, commit if anything changed, and push.

    A no-change transition (nothing staged) is a clean no-op: there is
    nothing to sync, so we neither commit nor push.
    """
    rel = _relative_to_root(root, task_path)
    _run_git(root, "add", "--", rel)
    if not _has_staged_changes(root, rel):
        return
    _run_git(root, "commit", "--only", "-m", message, "--", rel)
    _run_git(root, "push", cfg.git_remote, cfg.git_control_branch)


# --- low-level git plumbing ----------------------------------------------------


def _run_git(root: Path, *args: str) -> str:
    """Run a git subcommand in `root`, returning stdout. Raise GitError on
    failure or a missing git binary."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("`git` not found on PATH") from exc
    if result.returncode != 0:
        raise GitError(
            f"`git {' '.join(args)}` failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def _toplevel(start: Path) -> Path | None:
    """Resolve the git working-tree root containing `start`, or None when
    `start` is not inside a git repo.

    Uses `git rev-parse --show-toplevel` so worktrees and nested checkouts
    resolve correctly — unlike `cfg.repo_root`, which walks for `relay.toml`
    and may itself be `relay-os/`, not the git root.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("`git` not found on PATH") from exc
    if result.returncode != 0:
        if "not a git repository" in result.stderr:
            return None
        raise GitError(
            "`git rev-parse --show-toplevel` failed "
            f"(exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    top = result.stdout.strip()
    return Path(top) if top else None


def _current_branch(root: Path) -> str:
    """Return the current branch name (`HEAD` for a detached checkout)."""
    return _run_git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()


def _has_staged_changes(root: Path, pathspec: str) -> bool:
    """True when `pathspec` has staged changes relative to HEAD."""
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--cached", "--quiet", "--", pathspec],
        capture_output=True,
        text=True,
        check=False,
    )
    # `--quiet` exits 1 when there ARE differences, 0 when clean. Any other
    # code is a real error.
    if result.returncode == 1:
        return True
    if result.returncode == 0:
        return False
    raise GitError(
        f"`git diff --cached --quiet` failed (exit {result.returncode}): "
        f"{result.stderr.strip()}"
    )


def _relative_to_root(root: Path, task_path: Path) -> str:
    """Path of `task_path` relative to the git root, as a string for git.

    Falls back to the absolute path if `task_path` is not under `root`
    (git still accepts an absolute pathspec).
    """
    try:
        return str(task_path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(task_path.resolve())


__all__ = ["GitError", "sync_task_state"]
