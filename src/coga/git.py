"""Git sync — commit and push ticket-state changes, the git analogue of Slack.

Every coga command that mutates ticket state writes files to disk and posts
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

`sync_log` is the narrow companion for callers that append to the repo-global
`log.md` with no task-dir sync to ride along — chiefly stateless bootstrap-ticket
launches. Those appends would otherwise sit uncommitted and block the next
`git pull` at the checkout gate (`merge=union` only resolves committed content),
so it commits `log.md` alone, union-safely.

A non-fast-forward `origin/<control>` (it moved under us) is absorbed by a
bounded retry loop on both push paths. On the cross-branch landing path the
`git push <sha>:refs/heads/<control>` is the atomic compare-and-swap that
serializes concurrent coga processes (local or cross-machine), so no lock is
introduced — consistent with coga's no-mutex architecture; it rebuilds the
overlay tree on the new tip and repushes. On the same-branch path (HEAD *is*
the control branch) a rejected push triggers a fetch + `rebase --autostash`
onto the new tip, then a retry — the working tree is already checked out there,
so integrating the remote move means a rebase, with autostash keeping unrelated
dirty changes intact. A detached HEAD takes the cross-branch landing path but
skips the local commit (a commit on a detached HEAD would be orphaned).

Failure model: a failed git *operation* raises `GitError` internally, but at
the boundary (`sync_paths`) it is non-fatal — written to stderr + the task's
`log.md`, then swallowed so the command keeps running. The task markdown on
disk is the source of truth; git is only the sync layer, so a push that can't
reach the control branch (protected `main`, offline, or a recovery that itself
fails — e.g. a rebase conflict when integrating a moved `origin/<control>`)
must NOT abort a local state transition. Earlier this re-raised as `typer.Exit(1)`, which broke the
supervised launch chain: `coga bump`'s sync aborted before `emit_done_marker`
fired, so the supervisor never relaunched the next step, and launch's own
`active → in_progress` flip died before spawning the agent. "Fail loud" here
means surface the miss (stderr + log), not crash. "Not a git repo" stays a
soft no-op (single stderr line). The git opt-out is `[git].enabled`.

A missing control branch is a distinct soft-skip handled *before* any fetch or
push: when `refs/heads/<control>` doesn't exist locally — the `git init` default
of `master` against the `[git].control_branch` default of `main`, the classic
fresh-repo mismatch — sync would otherwise fetch/push a branch that isn't there
and raise a confusing swallowed `GitError`. Instead we detect the absent ref up
front and print one actionable line naming the fix (`set [git].control_branch`),
then return without committing. No auto-detection of the "right" branch — the
user owns that choice in config; we only stop the failure from being silent.

Subprocess usage mirrors `autoclose.py` (`gh` shell-out): no third-party git
binding, just `subprocess.run` with `check=False` and explicit error handling.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

from coga.config import Config
from coga.logfile import append_log, ref_tag_for_path
from coga.paths import log_path

# Bounded retries when racing `refs/heads/<control>`: each loss is a refetch +
# rebuild + repush, so a small ceiling is plenty under realistic contention
# (the coga launch auto-chain, manual commands).
_MAX_SYNC_ATTEMPTS = 5


class GitError(Exception):
    """Raised when a git operation fails (git missing, or a non-zero exit).

    Distinct from the soft "not a git repo" no-op: this signals a real
    failure on the control branch that the caller surfaces as a crash.
    """


def sync_task_state(cfg: Config, task_path: Path, *, message: str) -> None:
    """Commit the task directory's files and push to the control branch.

    Always-on git analogue of the live notification path. Behaviour:

      - `[git].enabled = false` → suppressed, one stderr line, no crash.
      - Not a git repo → soft no-op, one stderr line, no crash.
      - HEAD is the control branch → `git add` the task dir, and if anything
        is staged, commit with `message` and push to the configured remote.
      - HEAD is a feature branch → commit the task dir on the current branch
        (so the checkout reflects ticket state), then land the same files on
        the control branch via the working-tree-free plumbing path.
      - Detached HEAD → skip the local commit (it would be orphaned), still
        land on the control branch.

    Any git operation failure is non-fatal: it is reported to stderr + the
    task's `log.md` and then swallowed, so the local state transition still
    completes (the on-disk markdown is the source of truth; the push just
    didn't land). See the module docstring's failure model.

    `task_path` is the resolved task directory under `coga/tasks/`; only
    files under it are staged, never `git add -A`, so unrelated working-tree
    changes are not swept in.
    """
    sync_paths(cfg, task_path, [task_path], message=message)


def sync_log(cfg: Config, *, message: str) -> None:
    """Commit (and on the control branch, push) the repo-global `log.md` alone.

    For the union-safe audit log to survive a `git pull`, its appended lines
    must be *committed*: `merge=union` only resolves committed-vs-committed
    content, never a dirty working-tree file (git refuses the pull at the
    checkout gate, before any merge driver runs). Most commands sweep the log
    in via the task-dir sync — `sync_paths` folds `log.md` into `local_rels` —
    but a caller that appends without any task-dir sync, notably a stateless
    bootstrap-ticket launch, leaves the line dangling and dirty. `sync_log`
    closes that hole by committing exactly `log.md`, nothing else.

    Branch handling mirrors `sync_paths`'s log invariant:

      - Control branch: commit + push. A moved `origin/<control>` is absorbed by
        `_push_control_branch`'s fetch + rebase, which union-merges the log, so
        a concurrent append is never clobbered.
      - Feature branch: commit the log locally only. It reaches the control
        branch union-safely when the branch's PR merges — never via the
        cross-branch overlay, which replaces the file wholesale and would drop
        lines another branch appended.
      - Detached HEAD: skip (the commit would be orphaned); the line stays
        dirty, reported to stderr.

    Same non-fatal failure model as `sync_paths` (stderr, never a crash) with
    one deliberate difference: it does **not** `append_log` on failure. That
    would re-dirty the very file it just failed to commit, recreating the
    dangling-line problem instead of closing it.
    """
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (log sync suppressed): {message}\n")
        return
    log_file = log_path(cfg)
    if not log_file.exists():
        return
    try:
        root = _toplevel(log_file)
        if root is None:
            sys.stderr.write(f"[git] not a git repo (log sync skipped): {message}\n")
            return
        if not _control_branch_present(root, cfg.git_control_branch):
            sys.stderr.write(
                _control_branch_mismatch_message(cfg, root) + f" ({message})\n"
            )
            return
        log_rel = _relative_to_root(root, log_file)
        branch = _current_branch(root)
        if branch == cfg.git_control_branch:
            if _commit_paths(root, [log_rel], message):
                _push_control_branch(cfg, root)
        elif branch == "HEAD":
            sys.stderr.write(
                f"[git] detached HEAD — log append not committed locally. ({message})\n"
            )
        else:
            _commit_paths(root, [log_rel], message)
    except GitError as exc:
        sys.stderr.write(f"[git] log sync failed: {exc}. Message was: {message}\n")


def sync_paths(
    cfg: Config,
    anchor_path: Path,
    paths: Iterable[Path],
    *,
    message: str,
) -> None:
    """Commit explicit paths and push them to the control branch.

    This is the multi-path variant used by `coga ticket` authoring, where the
    subprocess may edit a task and create supporting local context/skill files.
    Callers must pass exact paths they own; Coga still never stages the whole
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

        if not _control_branch_present(root, cfg.git_control_branch):
            sys.stderr.write(
                _control_branch_mismatch_message(cfg, root) + f" ({message})\n"
            )
            return

        rels = [_relative_to_root(root, path) for path in selected]
        branch = _current_branch(root)

        # The repo-global `coga/log.md` is `merge=union`, so it must NOT
        # ride the cross-branch overlay — an overlay replaces the file wholesale
        # on the control tip, dropping log lines another branch appended
        # concurrently. Instead it is folded into the *local* commit only and
        # reaches the control branch the union-safe way: the same-branch push
        # rebases (union-merging the log), or the feature branch's PR merges
        # (union again). `local_rels` therefore carries the log; `rels` (the
        # overlay set) never does.
        log_rel = _relative_to_root(root, log_path(cfg))
        local_rels = rels + [log_rel] if log_path(cfg).exists() else rels

        if branch == cfg.git_control_branch:
            # On the control branch the commit+push *is* the union-safe path, so
            # the log can ride along — a rejected push rebases and union-merges.
            _sync_paths_on_control_branch(cfg, root, local_rels, message=message)
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
            _commit_paths(root, local_rels, message)
        _land_paths_on_control_branch(cfg, root, rels, message=message)
    except GitError as exc:
        # Non-fatal: surface loudly (stderr + log.md) but do NOT abort the
        # command. The task's markdown on disk is the source of truth; git is
        # only the sync layer. A push that can't reach the control branch
        # (protected `main`, offline, agent on a feature branch, origin moved
        # under us) must not block a local state transition — coupling
        # `coga bump` / `mark` / launch's `in_progress` flip to a remote push
        # is what stalled the supervised launch chain (the bump exited before
        # `emit_done_marker` fired, so the supervisor never relaunched the next
        # step). "Fail loud" here means make the miss visible, not crash.
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        append_log(cfg, ref_tag_for_path(cfg, anchor_path), "git", f"sync failed: {exc}")


def _sync_on_control_branch(
    cfg: Config, root: Path, rel: str, *, message: str
) -> None:
    """Stage the task dir, commit if anything changed, and push.

    A no-change transition (nothing staged) is a clean no-op: there is
    nothing to sync, so we neither commit nor push.
    """
    if not _commit_task_dir(root, rel, message):
        return
    _push_control_branch(cfg, root)


def _sync_paths_on_control_branch(
    cfg: Config, root: Path, rels: list[str], *, message: str
) -> None:
    """Stage explicit pathspecs, commit if anything changed, and push."""
    if not _commit_paths(root, rels, message):
        return
    _push_control_branch(cfg, root)


def _push_control_branch(cfg: Config, root: Path) -> None:
    """Push the checked-out control branch, absorbing a moved `origin/<control>`.

    The fast path is a single `git push <remote> <control>`. If `origin/<control>`
    advanced under us (another coga process, another machine, or a merged PR),
    the push is rejected non-fast-forward; we fetch and rebase the local control
    branch onto the new tip — protecting any unrelated dirty working-tree changes
    with autostash — and retry. Bounded by `_MAX_SYNC_ATTEMPTS`.

    This gives the same-branch path the same resilience the cross-branch landing
    path already has. Without it, the bare push had no fetch-first and no retry,
    so any concurrent remote commit left every later coga push on the control
    branch rejected and the local branch silently accumulating unpushed commits.
    """
    remote = cfg.git_remote
    branch = cfg.git_control_branch
    for _ in range(_MAX_SYNC_ATTEMPTS):
        result = _push_ref(root, remote, branch)
        if result is None:
            return
        if not _is_non_fast_forward(result):
            raise GitError(f"`git push {remote} {branch}` failed: {result}")
        # `origin/<control>` moved under us — integrate it and retry.
        _rebase_onto_remote(root, remote, branch)

    raise GitError(
        f"could not push {branch!r} after {_MAX_SYNC_ATTEMPTS} attempts — "
        f"contention on {remote}/{branch}"
    )


def _rebase_onto_remote(root: Path, remote: str, branch: str) -> None:
    """Rebase the local control branch onto the freshly-fetched remote tip,
    preserving unrelated dirty changes without ever leaving a conflicted tree
    or an orphaned stash.

    This replaces git's implicit `rebase --autostash`. Autostash couples the
    stash and the rebase: when the popped changes conflict with the integrated
    remote move, its abort path fails to re-apply the autostash, leaving
    **conflict markers in the working tree AND an undropped stash** — the exact
    wound this command was hardened against (a contended digest spool, popped
    back over a moved `origin/main`, re-conflicting on every `rebase --abort`).

    Here the stash is explicit and every failure exit restores the pre-sync
    state — dirty changes intact, working tree clean, no leftover stash — by
    resetting to the original local tip (`orig`) and re-applying the stash
    there, where it is guaranteed to apply because that is where it was taken.
    The caller surfaces the raised `GitError` as a non-fatal sync miss (stderr +
    log), never a crash: the on-disk markdown is still the source of truth.
    """
    _run_git(root, "fetch", remote, branch)
    orig = _run_git(root, "rev-parse", "HEAD").strip()
    stashed = _stash_if_dirty(root)

    rebase = subprocess.run(
        ["git", "-C", str(root), "rebase", "FETCH_HEAD"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **_noninteractive_git_env()},
    )
    if rebase.returncode != 0:
        _run_git_quiet(root, "rebase", "--abort")
        _restore_to_orig(root, orig, stashed=stashed)
        raise GitError(
            f"could not rebase {branch!r} onto {remote}/{branch}: "
            f"{(rebase.stderr + rebase.stdout).strip()}"
        )

    if stashed and not _pop_stash(root):
        # Rebase succeeded, but the dirty changes don't replay onto the new tip.
        # Roll all the way back so nothing is left half-applied or orphaned.
        _restore_to_orig(root, orig, stashed=True)
        raise GitError(
            f"could not reapply local changes after rebasing {branch!r} onto "
            f"{remote}/{branch}; restored pre-sync state"
        )


def _stash_if_dirty(root: Path) -> bool:
    """Stash tracked working-tree changes if any; return whether a stash was made.

    Untracked files are deliberately left in place — coga never sweeps them, so
    they neither enter the stash nor block the rebase (which ignores untracked
    paths). Staged and unstaged tracked changes are both captured so the rebase
    runs against a clean tree.
    """
    if not _run_git(root, "status", "--porcelain", "--untracked-files=no").strip():
        return False
    _run_git(root, "stash", "push", "--quiet", "--message", "coga-sync-autostash")
    return True


def _pop_stash(root: Path) -> bool:
    """Pop the most recent stash; return True on a clean pop, False on conflict.

    A conflicted `stash pop` leaves the stash entry intact (git drops it only on
    a clean apply), so the caller can roll back and re-apply it elsewhere.
    """
    proc = subprocess.run(
        ["git", "-C", str(root), "stash", "pop"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **_noninteractive_git_env()},
    )
    return proc.returncode == 0


def _restore_to_orig(root: Path, orig: str, *, stashed: bool) -> None:
    """Hard-restore the working tree to `orig` and re-apply the stash there.

    Used on every failure exit of `_rebase_onto_remote`. `reset --hard orig`
    clears any conflict markers, index conflicts, or partial-rebase state and
    moves the branch back to its pre-sync tip; the stash (taken from `orig`'s
    tree) then applies cleanly, leaving no orphaned stash and no markers.
    Best-effort — this already runs inside a `GitError` path the caller reports
    as a sync miss — so cleanup git calls do not themselves raise.
    """
    _run_git_quiet(root, "reset", "--hard", orig)
    if stashed:
        _run_git_quiet(root, "stash", "pop")


def _run_git_quiet(root: Path, *args: str) -> None:
    """Run a git subcommand for best-effort cleanup, ignoring any failure."""
    subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **_noninteractive_git_env()},
    )


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
    fd, tmp_index = tempfile.mkstemp(prefix="coga-git-index-")
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
            env={**os.environ, **_noninteractive_git_env()},
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


def _noninteractive_git_env() -> dict[str, str]:
    """Env overlay that makes git fail fast instead of prompting for creds.

    Coga's git sync runs unattended inside `coga launch` / `bump` / `mark`.
    A logged-out HTTPS push (or an unloaded SSH key) must surface as a loud,
    catchable `GitError` — never an interactive credential/passphrase prompt
    that silently hangs the launch waiting on a human who isn't watching.
    `GIT_TERMINAL_PROMPT=0` disables git's terminal credential prompt;
    `GIT_SSH_COMMAND` adds `BatchMode=yes` for SSH remotes, but only when the
    operator hasn't set their own (so a custom SSH command is preserved).
    Mirrors `github_preflight.py`, which already runs every probe
    non-interactively for the same fail-fast reason.
    """
    env = {"GIT_TERMINAL_PROMPT": "0"}
    if "GIT_SSH_COMMAND" not in os.environ:
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"
    return env


def _run_git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """Run a git subcommand in `root`, returning stdout. Raise GitError on
    failure or a missing git binary.

    `env` entries are overlaid on the current environment (not replacing it) —
    used to thread `GIT_INDEX_FILE` through the temp-index plumbing without
    losing the caller's PATH/HOME/git config. The non-interactive overlay is
    always applied so a credential-less network op fails loud instead of
    hanging on a prompt.
    """
    run_env = {**os.environ, **_noninteractive_git_env()}
    if env:
        run_env.update(env)
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
    resolve correctly — unlike `cfg.repo_root`, which walks for `coga.toml`
    and may itself be `coga/`, not the git root.

    `git -C` needs a directory, but the anchor may now be a file-form task's
    `tasks/<slug>.md` file; resolve to its parent directory first.
    """
    if not start.is_dir():
        start = start.parent
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


def _control_branch_present(root: Path, branch: str) -> bool:
    """True when `refs/heads/<branch>` exists locally.

    Uses `git show-ref --verify --quiet`, which exits non-zero (without error
    output) when the ref is absent. Distinct from `_current_branch`: it asks
    *does the control branch exist at all*, not *what is checked out*. On a
    fresh `git init` whose default branch is `master`, `refs/heads/main` is
    absent here, which is exactly the mismatch we want to catch before the sync
    fetches/pushes a `main` that isn't there.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "show-ref", "--verify", "--quiet",
         f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise GitError(
        f"`git show-ref --verify refs/heads/{branch}` failed "
        f"(exit {result.returncode}): {result.stderr.strip()}"
    )


def _symbolic_head(root: Path) -> str | None:
    """The current branch name via `symbolic-ref`, or None when detached.

    Unlike `_current_branch` (`rev-parse --abbrev-ref HEAD`), this resolves the
    branch name even before the first commit, where HEAD points at an unborn
    branch and `rev-parse` *raises* — precisely the fresh-repo case. Used only
    to name the user's actual branch in the mismatch guidance, so it is
    best-effort: `-q` makes a detached HEAD a quiet None rather than an error.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "symbolic-ref", "--short", "-q", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    name = result.stdout.strip()
    return name or None


def _control_branch_mismatch_message(cfg: Config, root: Path) -> str:
    """Actionable one-liner for a control branch that doesn't exist locally.

    Names the missing branch, the branch the user is actually on (when it can
    be resolved), and the exact `coga.toml` edit that fixes it. Surfaced in
    place of the swallowed-and-confusing `GitError` the fetch/push would
    otherwise raise against a nonexistent branch.
    """
    actual = _symbolic_head(root)
    on = f" (you are on {actual!r})" if actual else ""
    suggested = actual or "<your-branch>"
    return (
        f"[git] control branch {cfg.git_control_branch!r} does not exist{on}; "
        f"sync skipped. Set it to match your branch in coga.toml:\n"
        f"    [git]\n"
        f'    control_branch = "{suggested}"'
    )


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


__all__ = ["GitError", "sync_log", "sync_paths", "sync_task_state"]
