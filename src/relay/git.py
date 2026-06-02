"""Git sync — commit and push ticket-state changes, the git analogue of Slack.

Every relay command that mutates ticket state writes files to disk and posts
to Slack, but historically did no git: the git-backed repo drifted from the
team's live state until a human committed by hand. `sync_task_state` closes
that gap. It is always-on (no per-command flag), the same way Slack is — the
only opt-out is `[git].enabled = false`.

When HEAD is already the control branch (normally `main`), it commits the
changed task files and pushes (the same-branch path). When HEAD is a feature
branch, it still lands the task state on the control branch — by building the
control branch's tree in a *temporary index* and pushing a fresh commit
straight to `refs/heads/<control>`, never checking out `main` or touching the
feature working tree — and *also* commits the task files on the current branch
so the agent's checkout reflects the ticket state it works against.

A non-fast-forward `origin/<control>` (it moved under us) is absorbed by a
bounded fetch-rebuild-retry loop: the `git push <sha>:refs/heads/<control>` is
the atomic compare-and-swap that serializes concurrent relay processes (local
or cross-machine), so no lock is introduced — consistent with relay's no-mutex
architecture. A detached HEAD takes the cross-branch landing path but skips the
local commit (a commit on a detached HEAD would be orphaned).

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

import os
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

import typer

from relay.config import Config
from relay.logfile import append_log

# Bounded retries when racing `refs/heads/<control>`: each loss is a refetch +
# rebuild + repush, so a small ceiling is plenty under realistic contention
# (the relay launch auto-chain, the post-merge hook, manual commands).
_MAX_SYNC_ATTEMPTS = 5


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
      - HEAD is the control branch → `git add` the task dir, and if anything
        is staged, commit with `message` and push to the configured remote.
      - HEAD is a feature branch → commit the task dir on the current branch
        (so the checkout reflects ticket state), then land the same files on
        the control branch via the working-tree-free plumbing path.
      - Detached HEAD → skip the local commit (it would be orphaned), still
        land on the control branch.

    Any git operation failure on the control-branch path raises `GitError`,
    which is reported to stderr + the task's `log.md` and re-raised as
    `typer.Exit(1)`.

    `task_path` is the task directory (`relay-os/tasks/<slug>/`); only files
    under it are staged, never `git add -A`, so unrelated working-tree changes
    are not swept in.
    """
    sync_paths(cfg, task_path, [task_path], message=message)


def sync_paths(
    cfg: Config,
    anchor_path: Path,
    paths: Iterable[Path],
    *,
    message: str,
) -> None:
    """Commit explicit paths and push them to the control branch.

    This is the multi-path variant used by `relay ticket` authoring, where the
    subprocess may edit a task and create supporting local context/skill files.
    Callers must pass exact paths they own; Relay still never stages the whole
    worktree. `anchor_path` is used to find the git root and to record a sync
    failure in an appropriate log.
    """
    selected = _dedupe_paths(paths)
    if not selected:
        return

    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return

    try:
        root = _toplevel(anchor_path)
        if root is None:
            sys.stderr.write(
                f"[git] not a git repo (sync skipped): {message}\n"
            )
            return

        rels = [_relative_to_root(root, path) for path in selected]
        branch = _current_branch(root)

        if branch == cfg.git_control_branch:
            _sync_paths_on_control_branch(cfg, root, rels, message=message)
            return

        # Feature branch (or detached HEAD): commit on the current branch so
        # the checkout reflects ticket state, then land on the control branch
        # without ever touching the feature working tree.
        if branch == "HEAD":
            sys.stderr.write(
                f"[git] detached HEAD — task state landed on "
                f"{cfg.git_control_branch!r} but not committed locally. ({message})\n"
            )
        else:
            _commit_paths(root, rels, message)
        _land_paths_on_control_branch(cfg, root, rels, message=message)
    except GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        append_log(anchor_path, "git", f"sync failed: {exc}")
        raise typer.Exit(1)


def _sync_on_control_branch(
    cfg: Config, root: Path, rel: str, *, message: str
) -> None:
    """Stage the task dir, commit if anything changed, and push.

    A no-change transition (nothing staged) is a clean no-op: there is
    nothing to sync, so we neither commit nor push.
    """
    if not _commit_task_dir(root, rel, message):
        return
    _run_git(root, "push", cfg.git_remote, cfg.git_control_branch)


def _sync_paths_on_control_branch(
    cfg: Config, root: Path, rels: list[str], *, message: str
) -> None:
    """Stage explicit pathspecs, commit if anything changed, and push."""
    if not _commit_paths(root, rels, message):
        return
    _run_git(root, "push", cfg.git_remote, cfg.git_control_branch)


def _commit_task_dir(root: Path, rel: str, message: str) -> bool:
    """Stage and commit the task dir on the current branch; return whether a
    commit was made.

    Working-tree-safe: `git add -- rel` only stages the task pathspec, and
    `git commit --only -- rel` commits exactly that pathspec, leaving any
    unrelated staged or unstaged changes untouched. A no-change transition
    (nothing staged under `rel`) is a clean no-op returning False.
    """
    _run_git(root, "add", "--", rel)
    if not _has_staged_changes(root, rel):
        return False
    _run_git(root, "commit", "--only", "-m", message, "--", rel)
    return True


def _commit_paths(root: Path, rels: list[str], message: str) -> bool:
    """Commit exactly the selected pathspecs on the current branch.

    Existing paths are added from the working tree; missing paths are removed
    from the index. Both operations are scoped to the caller-selected pathspecs,
    so unrelated staged and unstaged files survive untouched.
    """
    existing = [rel for rel in rels if _path_exists(root, rel)]
    missing = [rel for rel in rels if rel not in existing]
    if existing:
        _run_git(root, "add", "--", *existing)
    if missing:
        _run_git(root, "rm", "-rf", "--cached", "--ignore-unmatch", "--", *missing)
    if not _has_staged_changes(root, rels):
        return False
    _run_git(root, "commit", "--only", "-m", message, "--", *rels)
    return True


def _land_on_control_branch(
    cfg: Config, root: Path, rel: str, *, message: str
) -> None:
    """Land the working-tree task dir on the control branch from any branch.

    Pure plumbing: build the control branch's tree in a *temporary index*
    (never the real index, never the working tree), overlay the current task
    dir onto it, commit-tree, and push the new commit straight to
    `refs/heads/<control>`. The push is a compare-and-swap — a non-fast-forward
    rejection means another process landed first, so we refetch and rebuild on
    the new tip. Bounded by `_MAX_SYNC_ATTEMPTS`.
    """
    remote = cfg.git_remote
    branch = cfg.git_control_branch

    for _ in range(_MAX_SYNC_ATTEMPTS):
        _run_git(root, "fetch", remote, branch)
        base = _run_git(root, "rev-parse", "FETCH_HEAD").strip()

        tree = _build_overlay_tree(root, base, [rel])
        if tree == _run_git(root, "rev-parse", f"{base}^{{tree}}").strip():
            # The control branch already has identical task content — nothing
            # to land. (Common: same-content reruns, or the feature commit and
            # the control branch already agree.)
            return

        new = _run_git(root, "commit-tree", tree, "-p", base, "-m", message).strip()
        result = _push_ref(root, remote, f"{new}:refs/heads/{branch}")
        if result is None:
            # Pushed. Best-effort fast-forward the local control ref so a later
            # same-branch checkout sees it; failure here is non-fatal because
            # origin already has the commit.
            _try_update_local_ref(root, branch, new)
            return
        if not _is_non_fast_forward(result):
            raise GitError(
                f"`git push {remote} {new}:refs/heads/{branch}` failed: {result}"
            )
        # Non-fast-forward: another process moved the branch. Loop refetches.

    raise GitError(
        f"could not land on {branch!r} after {_MAX_SYNC_ATTEMPTS} attempts — "
        f"contention on refs/heads/{branch}"
    )


def _land_paths_on_control_branch(
    cfg: Config, root: Path, rels: list[str], *, message: str
) -> None:
    """Land selected pathspecs on the control branch from any branch."""
    remote = cfg.git_remote
    branch = cfg.git_control_branch

    for _ in range(_MAX_SYNC_ATTEMPTS):
        _run_git(root, "fetch", remote, branch)
        base = _run_git(root, "rev-parse", "FETCH_HEAD").strip()

        tree = _build_overlay_tree(root, base, rels)
        if tree == _run_git(root, "rev-parse", f"{base}^{{tree}}").strip():
            return

        new = _run_git(root, "commit-tree", tree, "-p", base, "-m", message).strip()
        result = _push_ref(root, remote, f"{new}:refs/heads/{branch}")
        if result is None:
            _try_update_local_ref(root, branch, new)
            return
        if not _is_non_fast_forward(result):
            raise GitError(
                f"`git push {remote} {new}:refs/heads/{branch}` failed: {result}"
            )

    raise GitError(
        f"could not land on {branch!r} after {_MAX_SYNC_ATTEMPTS} attempts — "
        f"contention on refs/heads/{branch}"
    )


def _build_overlay_tree(root: Path, base: str, rels: list[str]) -> str:
    """Build a tree = `base`'s tree with selected pathspecs overlaid.

    Runs entirely against a throwaway temporary index (`GIT_INDEX_FILE`), so
    neither the real index nor the working tree is disturbed. Seeds the temp
    index from `base`, drops stale content for every selected path, re-adds the
    current working-tree content for paths that still exist, and writes the
    resulting tree object.
    """
    fd, tmp_index = tempfile.mkstemp(prefix="relay-git-index-")
    os.close(fd)
    try:
        os.unlink(tmp_index)  # read-tree wants to create it fresh
        env = {"GIT_INDEX_FILE": tmp_index}
        _run_git(root, "read-tree", base, env=env)
        _overlay_paths(root, env, rels)
        return _run_git(root, "write-tree", env=env).strip()
    finally:
        try:
            os.unlink(tmp_index)
        except FileNotFoundError:
            pass


def _overlay_paths(root: Path, env: dict[str, str], rels: list[str]) -> None:
    for rel in rels:
        # `-f`: this is a throwaway index we immediately rewrite, so `git rm`'s
        # "staged content differs from file/HEAD" safety check is meaningless
        # here — and it would otherwise *refuse* whenever the task already
        # exists on the control branch and the feature HEAD changed it (the
        # common cross-branch panic case). Force removal, then re-add from the
        # working tree.
        _run_git(
            root, "rm", "-rf", "--cached", "--ignore-unmatch", "--", rel, env=env
        )
        if _path_exists(root, rel):
            _run_git(root, "add", "--", rel, env=env)


def _push_ref(root: Path, remote: str, refspec: str) -> str | None:
    """Push `refspec` to `remote`. Return None on success, else stderr+stdout.

    Unlike `_run_git`, a non-zero exit is returned (not raised) so the caller
    can distinguish a recoverable non-fast-forward from a hard failure.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "push", remote, refspec],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("`git` not found on PATH") from exc
    if result.returncode == 0:
        return None
    return (result.stderr + result.stdout).strip()


def _is_non_fast_forward(push_output: str) -> bool:
    """True when a push was rejected because the remote ref moved under us."""
    lowered = push_output.lower()
    return any(
        marker in lowered
        for marker in ("non-fast-forward", "fetch first", "rejected", "stale info")
    )


def _try_update_local_ref(root: Path, branch: str, new: str) -> None:
    """Best-effort fast-forward the local control ref to `new`.

    Non-fatal: origin already has the commit, so a failure here (e.g. the
    branch isn't checked out anywhere, or moved on locally) only means a later
    local checkout of the control branch must fetch. We don't update the ref if
    HEAD points at it, since that would desync the index/working tree.
    """
    head = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if head == branch:
        return
    result = subprocess.run(
        ["git", "-C", str(root), "update-ref", f"refs/heads/{branch}", new],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(
            f"[git] note: local {branch!r} not fast-forwarded "
            f"(origin has the commit): {result.stderr.strip()}\n"
        )


# --- low-level git plumbing ----------------------------------------------------


def _run_git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """Run a git subcommand in `root`, returning stdout. Raise GitError on
    failure or a missing git binary.

    `env` entries are overlaid on the current environment (not replacing it) —
    used to thread `GIT_INDEX_FILE` through the temp-index plumbing without
    losing the caller's PATH/HOME/git config.
    """
    run_env = {**os.environ, **env} if env else None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            env=run_env,
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


def _has_staged_changes(root: Path, pathspec: str | list[str]) -> bool:
    """True when selected pathspecs have staged changes relative to HEAD."""
    paths = [pathspec] if isinstance(pathspec, str) else list(pathspec)
    if not paths:
        return False
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--cached", "--quiet", "--", *paths],
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


def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def _path_exists(root: Path, rel: str) -> bool:
    path = Path(rel)
    if not path.is_absolute():
        path = root / path
    return path.exists()


__all__ = ["GitError", "sync_paths", "sync_task_state"]
