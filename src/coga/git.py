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
so the agent's checkout reflects the ticket state it works against. Detached
launch worktrees take the same temp-index path; `merge=union` files that cannot
ride a local branch commit are union-merged directly into the control commit.

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
skips the local commit (a commit on a detached HEAD would be orphaned). After a
successful landing push, the local control ref is fast-forwarded best-effort:
directly via `update-ref` when no worktree holds the branch, or through the
holding worktree with `merge --ff-only` — the launch-worktree default leaves
the primary checkout on `main`, and without this it would fall behind origin
after every launch until a manual pull.

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
push: when the control branch is absent locally and on the configured remote —
the `git init` default of `master` against the `[git].control_branch` default
of `main`, the classic fresh-repo mismatch — sync would otherwise fetch/push a
branch that isn't there and raise a confusing swallowed `GitError`. Instead we
detect the absent branch up front and print one actionable line naming the fix
(`set [git].control_branch`), then return without committing. No auto-detection
of the "right" branch — the user owns that choice in config; we only stop the
failure from being silent.

Subprocess usage mirrors `autoclose.py` (`gh` shell-out): no third-party git
binding, just `subprocess.run` with `check=False` and explicit error handling.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from coga.config import Config
from coga.logfile import append_log, ref_tag_for_path
from coga.paths import log_path
from coga.taskfile import TaskFileError, split_body
from coga.ticket import Ticket, TicketError

# Bounded retries when racing `refs/heads/<control>`: each loss is a refetch +
# rebuild + repush, so a small ceiling is plenty under realistic contention
# (the coga launch auto-chain, manual commands).
_MAX_SYNC_ATTEMPTS = 5

_ROOT_LAYOUT_COGA_PATHS = (
    "bootstrap",
    "coga.toml",
    "context.md",
    "contexts",
    "log.md",
    "recurring",
    "skills",
    "tasks",
    "workflows",
)

_STATUS_PROGRESS = {
    "draft": 0,
    "active": 1,
    "in_progress": 2,
    "done": 3,
}

_StateGuard = Callable[[str], None]


class GitError(Exception):
    """Raised when a git operation fails (git missing, or a non-zero exit).

    Distinct from the soft "not a git repo" no-op: this signals a real
    failure on the control branch that the caller surfaces as a crash.
    """


class StateRegressionError(GitError):
    """Raised when catch-all Coga-state sync would commit stale task state."""


@dataclass(frozen=True)
class _TicketState:
    status: str | None
    step: str | None
    step_index: int | None
    blackboard_bytes: int | None


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
        if not _control_branch_present(root, cfg.git_control_branch, cfg.git_remote):
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

        if not _control_branch_present(root, cfg.git_control_branch, cfg.git_remote):
            sys.stderr.write(
                _control_branch_mismatch_message(cfg, root) + f" ({message})\n"
            )
            return

        rels = [_relative_to_root(root, path) for path in selected]

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

        _dispatch_branch_sync(
            cfg, root, local_rels=local_rels, overlay_rels=rels, message=message
        )
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


def sync_coga_state(cfg: Config, *, message: str = "Sync coga state") -> None:
    """Commit everything dirty under the `coga/` OS-state subtree, from any branch.

    The catch-all sweep behind the always-on sync contract. The per-transition
    syncs (`sync_task_state` / `sync_paths` / `sync_log`) commit the file a
    command *intended* to change, with a human-readable per-transition message;
    this sweep mops up the rest of the `coga/` subtree so the working tree never
    accumulates dirty OS state. Two structural sources motivate it: machine
    side-effects written *past* the last per-command sync (the per-session
    `## Usage` record `coga launch` appends after the agent's final
    `bump`/`mark`, the digest spool, stray launch log lines) and human
    hand-edits to tickets/blackboards/contexts that no command touched. Both
    converge on git at the *next* coga invocation — lazy, on-access, no daemon
    (see `coga/architecture`'s "no database, no daemon, no in-memory state").

    Scope is the `coga/` subtree (`cfg.repo_root`, where `coga.toml` lives), the
    OS-state boundary. This is *not* the forbidden `git add -A`: it stages only
    paths under `coga/`, so product code (`src/`, `tests/`) is never swept in —
    that is exactly the line the "Scope is narrow" rule draws. Enumeration is a
    full `git status` under the subtree, so modifications, deletions, renames
    **and new untracked files** are all captured.

    Branch and union-file handling mirror `sync_paths`: the `merge=union` files
    (`log.md`, the digest spool) are committed locally + union-merged onto the
    control branch, never landed via the wholesale overlay (which would drop
    concurrently-appended lines). Detached HEAD has no durable local branch
    commit, so it performs that union merge directly while building the control
    branch tree. Everything else lands on the control branch from any branch. A
    clean subtree is a no-op.

    Same non-fatal failure model as `sync_paths` (stderr + `coga/log.md`, never
    a crash): the on-disk markdown is the source of truth; a sweep that can't
    reach the control branch must not abort the command it trails.
    """
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return

    subtree = cfg.repo_root
    try:
        root = _toplevel(subtree)
        if root is None:
            sys.stderr.write(f"[git] not a git repo (sync skipped): {message}\n")
            return

        state_pathspecs = _coga_state_pathspecs(root, subtree)
        changed = _changed_paths_under(root, state_pathspecs)
        if not changed:
            return

        if not _control_branch_present(root, cfg.git_control_branch, cfg.git_remote):
            sys.stderr.write(
                _control_branch_mismatch_message(cfg, root) + f" ({message})\n"
            )
            return

        def guard(base: str) -> None:
            _guard_coga_state_regressions(cfg, root, changed, base)

        # `merge=union` files (log.md, the digest spool) must stay out of the
        # cross-branch overlay set — same reason `sync_paths` keeps the log out:
        # the overlay replaces a file wholesale on the control tip and would drop
        # lines another branch appended. They ride the local commit and reach the
        # control branch union-safely (same-branch push rebase, or PR merge).
        union = _union_merge_paths(root, changed)
        overlay_rels = [rel for rel in changed if rel not in union]

        _dispatch_branch_sync(
            cfg,
            root,
            local_rels=changed,
            overlay_rels=overlay_rels,
            message=message,
            guard=guard,
        )
    except StateRegressionError as exc:
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
    except GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        append_log(cfg, ref_tag_for_path(cfg, subtree), "git", f"sync failed: {exc}")


def _dispatch_branch_sync(
    cfg: Config,
    root: Path,
    *,
    local_rels: list[str],
    overlay_rels: list[str],
    message: str,
    guard: _StateGuard | None = None,
) -> None:
    """Commit `local_rels` on the current branch and land `overlay_rels` on the
    control branch — the branch-aware core shared by `sync_paths` and
    `sync_coga_state`.

      - HEAD is the control branch → commit `local_rels` and push; the union
        files in `local_rels` ride the push-rebase's union merge.
      - Feature branch → commit `local_rels` locally (so the checkout reflects
        OS state), then land `overlay_rels` on the control branch via the
        working-tree-free overlay.
      - Detached HEAD → skip the local commit (it would be orphaned); still land
        `overlay_rels` on the control branch.
    """
    branch = _current_branch(root)
    if branch == cfg.git_control_branch:
        _sync_paths_on_control_branch(
            cfg, root, local_rels, message=message, guard=guard
        )
        return

    if branch == "HEAD":
        # Detached HEAD (the per-launch worktree default): no local commit —
        # it would be orphaned. The landing pushes the control branch and
        # fast-forwards the primary checkout via `_try_update_local_ref`;
        # only a fast-forward miss warrants a stderr note, printed there.
        overlay = set(overlay_rels)
        union_rels = [rel for rel in local_rels if rel not in overlay]
        _land_paths_on_control_branch(
            cfg,
            root,
            overlay_rels,
            union_rels=union_rels,
            message=message,
            guard=guard,
        )
        return
    else:
        before = _run_git(root, "rev-parse", "HEAD").strip() if guard else None
        _commit_paths(root, local_rels, message)
    try:
        _land_paths_on_control_branch(
            cfg, root, overlay_rels, message=message, guard=guard
        )
    except StateRegressionError:
        if before is not None:
            _restore_unpushed_sync_commit(root, before, local_rels)
        raise


def _coga_state_pathspecs(root: Path, coga_root: Path) -> list[str]:
    rel = _relative_to_root(root, coga_root)
    if rel != ".":
        return [rel]
    return list(_ROOT_LAYOUT_COGA_PATHS)


def _changed_paths_under(root: Path, pathspecs: str | Iterable[str]) -> list[str]:
    """Repo-relative paths with working-tree changes under `pathspecs`.

    A full `git status --porcelain -z` scoped to the Coga pathspecs: captures
    staged and unstaged modifications, deletions, renames, and untracked files
    alike. `-z` is NUL-delimited so paths with spaces or special characters need
    no unquoting. Rename entries (`R`/`C`) emit the new path then the old path as
    two NUL fields; both are returned so the rename commits as a delete + add.
    """
    selected = [pathspecs] if isinstance(pathspecs, str) else list(pathspecs)
    if not selected:
        return []
    out = _run_git(
        root, "status", "--porcelain", "-z", "--untracked-files=all", "--", *selected
    )
    fields = out.split("\x00")
    rels: list[str] = []
    seen: set[str] = set()
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:]
        for rel in _status_paths(status, path):
            if rel not in seen:
                seen.add(rel)
                rels.append(rel)
        # A rename/copy stores the source path in the next NUL field.
        if status[0] in ("R", "C"):
            if i < len(fields):
                src = fields[i]
                i += 1
                if src and src not in seen:
                    seen.add(src)
                    rels.append(src)
    return rels


def _status_paths(status: str, path: str) -> list[str]:
    """The path(s) a porcelain status entry contributes to the commit set."""
    return [path] if path else []


def _union_merge_paths(root: Path, rels: list[str]) -> set[str]:
    """Subset of `rels` carrying the `merge=union` git attribute.

    Asked of git directly (`git check-attr merge -z`) rather than hardcoding
    `log.md` / the spool, so any file `.gitattributes` marks `merge=union`
    automatically stays out of the cross-branch overlay. `-z` keeps path/value
    parsing robust against special characters.
    """
    if not rels:
        return set()
    out = _run_git(root, "check-attr", "merge", "-z", "--", *rels)
    fields = out.split("\x00")
    union: set[str] = set()
    # `check-attr -z` emits flat triples: path, attr-name, value.
    for j in range(0, len(fields) - 2, 3):
        path, _attr, value = fields[j], fields[j + 1], fields[j + 2]
        if value == "union":
            union.add(path)
    return union


def _guard_coga_state_regressions(
    cfg: Config, root: Path, rels: list[str], base: str
) -> None:
    """Fail loud before a catch-all sweep commits stale task frontmatter.

    `sync_coga_state` is intentionally broad within the Coga OS subtree. That
    breadth is safe for usage records and hand-edits, but not for a stale launch
    worktree whose task file predates a newer bump. Compare dirty task tickets
    against the committed control-branch copy and leave the stale file dirty
    instead of burying it in a generic "Sync coga state" commit.
    """
    refusals: list[str] = []
    for rel in _changed_task_ticket_rels(root, cfg.repo_root, rels):
        working = _working_tree_bytes(root, rel)
        if working is None:
            continue
        committed = _tree_bytes(root, base, rel)
        if committed is None:
            continue
        working_state = _ticket_state_from_bytes(working)
        committed_state = _ticket_state_from_bytes(committed)
        if working_state is None or committed_state is None:
            continue
        reason = _ticket_state_regression_reason(
            rel, committed=committed_state, working=working_state
        )
        if reason is None:
            continue

        task_ref = _task_ref_for_ticket_rel(cfg, root, rel)
        append_log(cfg, task_ref, "git", f"sync refused: {reason}")
        refusals.append(reason)

    if refusals:
        raise StateRegressionError("; ".join(refusals))


def _changed_task_ticket_rels(
    root: Path, coga_root: Path, rels: list[str]
) -> list[str]:
    tasks_rel = _relative_to_root(root, coga_root / "tasks")
    prefix = f"{tasks_rel}/" if tasks_rel != "." else ""
    out: list[str] = []
    for rel in rels:
        if not rel.startswith(prefix):
            continue
        path = Path(rel)
        if path.name == "ticket.md":
            out.append(rel)
            continue
        if path.suffix != ".md":
            continue
        # A markdown file inside a directory-form task is an attachment, not a
        # file-form ticket. File-form tickets have no sibling `ticket.md`.
        if not (root / path.parent / "ticket.md").exists():
            out.append(rel)
    return out


def _task_ref_for_ticket_rel(cfg: Config, root: Path, rel: str) -> str:
    path = root / rel
    if path.name == "ticket.md":
        return ref_tag_for_path(cfg, path.parent)
    return ref_tag_for_path(cfg, path)


def _ticket_state_from_bytes(data: bytes) -> _TicketState | None:
    try:
        ticket = Ticket.parse(data.decode("utf-8"))
    except (UnicodeDecodeError, TicketError):
        return None
    blackboard_bytes: int | None = None
    try:
        _body, blackboard = split_body(ticket.body, blackboard_required=False)
    except TaskFileError:
        blackboard = None
    if blackboard is not None:
        blackboard_bytes = len(blackboard.encode("utf-8"))
    status = ticket.frontmatter.get("status")
    step = ticket.frontmatter.get("step")
    return _TicketState(
        status=str(status) if status is not None else None,
        step=str(step) if step is not None else None,
        step_index=ticket.step_index(),
        blackboard_bytes=blackboard_bytes,
    )


def _ticket_state_regression_reason(
    rel: str, *, committed: _TicketState, working: _TicketState
) -> str | None:
    if (
        committed.step_index is not None
        and working.step_index is not None
        and working.step_index < committed.step_index
    ):
        detail = (
            f"{rel}: step would move backward from "
            f"{committed.step!r} to {working.step!r}"
        )
        if (
            committed.blackboard_bytes is not None
            and working.blackboard_bytes is not None
            and working.blackboard_bytes < committed.blackboard_bytes
        ):
            detail += (
                f"; blackboard would shrink from {committed.blackboard_bytes} "
                f"to {working.blackboard_bytes} bytes"
            )
        return detail

    committed_status = _STATUS_PROGRESS.get(committed.status or "")
    working_status = _STATUS_PROGRESS.get(working.status or "")
    if (
        committed_status is not None
        and working_status is not None
        and working_status < committed_status
    ):
        return (
            f"{rel}: status would move backward from "
            f"{committed.status!r} to {working.status!r}"
        )

    return None


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
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    message: str,
    guard: _StateGuard | None = None,
) -> None:
    """Stage explicit pathspecs, commit if anything changed, and push."""
    before: str | None = None
    if guard is not None:
        base = _control_base_for_attempt(
            root, cfg.git_remote, cfg.git_control_branch, 1
        )
        guard(base)
        before = _run_git(root, "rev-parse", "HEAD").strip()
    if not _commit_paths(root, rels, message):
        return
    try:
        _push_control_branch(cfg, root, guard=guard)
    except StateRegressionError:
        if before is not None:
            _restore_unpushed_sync_commit(root, before, rels)
        raise


def _restore_unpushed_sync_commit(root: Path, before: str, rels: list[str]) -> None:
    """Undo a just-created state-sync commit while keeping its files dirty."""
    _run_git(root, "reset", "--soft", before)
    _run_git(root, "reset", before, "--", *rels)


def _push_control_branch(
    cfg: Config, root: Path, *, guard: _StateGuard | None = None
) -> None:
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
        _rebase_onto_remote(root, remote, branch, guard=guard)

    raise GitError(
        f"could not push {branch!r} after {_MAX_SYNC_ATTEMPTS} attempts — "
        f"contention on {remote}/{branch}"
    )


def _rebase_onto_remote(
    root: Path,
    remote: str,
    branch: str,
    *,
    guard: _StateGuard | None = None,
) -> None:
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
    if guard is not None:
        guard(_run_git(root, "rev-parse", "FETCH_HEAD").strip())
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

    for attempt in range(_MAX_SYNC_ATTEMPTS):
        base = _control_base_for_attempt(root, remote, branch, attempt)

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
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    union_rels: list[str] | None = None,
    message: str,
    guard: _StateGuard | None = None,
) -> None:
    """Land selected pathspecs on the control branch from any branch."""
    remote = cfg.git_remote
    branch = cfg.git_control_branch
    union_rels = union_rels or []

    for attempt in range(_MAX_SYNC_ATTEMPTS):
        base = _control_base_for_attempt(root, remote, branch, attempt)
        if guard is not None:
            guard(base)

        tree = _build_overlay_tree(root, base, rels, union_rels=union_rels)
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


def _control_base_for_attempt(
    root: Path, remote: str, branch: str, attempt: int
) -> str:
    if attempt == 0:
        local = _local_control_base(root, remote, branch)
        if local is not None:
            return local
    _run_git(root, "fetch", remote, branch)
    return _run_git(root, "rev-parse", "FETCH_HEAD").strip()


def _local_control_base(root: Path, remote: str, branch: str) -> str | None:
    for ref in (f"refs/heads/{branch}", f"refs/remotes/{remote}/{branch}"):
        if _git_ref_present(root, ref):
            return _run_git(root, "rev-parse", ref).strip()
    return None


def _build_overlay_tree(
    root: Path, base: str, rels: list[str], *, union_rels: list[str] | None = None
) -> str:
    """Build a tree = `base`'s tree with selected pathspecs overlaid.

    Runs entirely against a throwaway temporary index (`GIT_INDEX_FILE`), so
    neither the real index nor the working tree is disturbed. Seeds the temp
    index from `base`, drops stale content for every selected path, re-adds the
    current working-tree content for paths that still exist, union-merges any
    detached-head `merge=union` files, and writes the resulting tree object.
    """
    union_rels = union_rels or []
    fd, tmp_index = tempfile.mkstemp(prefix="coga-git-index-")
    os.close(fd)
    try:
        os.unlink(tmp_index)  # read-tree wants to create it fresh
        env = {"GIT_INDEX_FILE": tmp_index}
        _run_git(root, "read-tree", base, env=env)
        _overlay_paths(root, env, rels)
        _overlay_union_paths(root, env, base, union_rels)
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


def _overlay_union_paths(
    root: Path, env: dict[str, str], base: str, rels: list[str]
) -> None:
    if not rels:
        return
    ancestor = _run_git(root, "merge-base", "HEAD", base).strip()
    for rel in rels:
        merged = _merge_union_path(
            root, current_rev=base, base_rev=ancestor, rel=rel
        )
        blob = _hash_blob(root, merged)
        _run_git(
            root,
            "update-index",
            "--add",
            "--cacheinfo",
            "100644",
            blob,
            rel,
            env=env,
        )


def _merge_union_path(
    root: Path, *, current_rev: str, base_rev: str, rel: str
) -> bytes:
    """Three-way union-merge a working-tree file into `current_rev`.

    This is the temp-index equivalent of the `merge=union` driver used when a
    local branch commit later merges through Git. It is only used for detached
    launch worktrees, where there is no durable local branch commit for `log.md`
    / `spool.md` appends to ride.
    """
    working = _working_tree_bytes(root, rel)
    if working is None:
        raise GitError(
            "cannot safely land deleted merge=union path "
            f"{rel!r} from detached HEAD"
        )
    current = _tree_bytes(root, current_rev, rel) or b""
    base = _tree_bytes(root, base_rev, rel) or b""
    return _merge_union_bytes(current=current, base=base, other=working)


def _merge_union_bytes(*, current: bytes, base: bytes, other: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="coga-union-merge-") as tmp:
        tmpdir = Path(tmp)
        current_path = tmpdir / "current"
        base_path = tmpdir / "base"
        other_path = tmpdir / "other"
        current_path.write_bytes(current)
        base_path.write_bytes(base)
        other_path.write_bytes(other)
        try:
            result = subprocess.run(
                [
                    "git",
                    "merge-file",
                    "--union",
                    str(current_path),
                    str(base_path),
                    str(other_path),
                ],
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, **_noninteractive_git_env()},
            )
        except FileNotFoundError as exc:
            raise GitError("`git` not found on PATH") from exc
        if result.returncode != 0:
            raise GitError(
                "`git merge-file --union` failed "
                f"(exit {result.returncode}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return current_path.read_bytes()


def _tree_bytes(root: Path, rev: str, rel: str) -> bytes | None:
    spec = f"{rev}:{rel}"
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", spec],
            capture_output=True,
            check=False,
            env={**os.environ, **_noninteractive_git_env()},
        )
    except FileNotFoundError as exc:
        raise GitError("`git` not found on PATH") from exc
    if probe.returncode != 0:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "show", spec],
        capture_output=True,
        check=False,
        env={**os.environ, **_noninteractive_git_env()},
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        stdout = result.stdout.decode(errors="replace").strip()
        raise GitError(
            f"`git show {spec}` failed (exit {result.returncode}): "
            f"{stderr or stdout}"
        )
    return result.stdout


def _working_tree_bytes(root: Path, rel: str) -> bytes | None:
    path = Path(rel)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return None
    if not path.is_file():
        raise GitError(f"merge=union path {rel!r} is not a file")
    return path.read_bytes()


def _hash_blob(root: Path, data: bytes) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "hash-object", "-w", "--stdin"],
            input=data,
            capture_output=True,
            check=False,
            env={**os.environ, **_noninteractive_git_env()},
        )
    except FileNotFoundError as exc:
        raise GitError("`git` not found on PATH") from exc
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        stdout = result.stdout.decode(errors="replace").strip()
        raise GitError(
            "`git hash-object -w --stdin` failed "
            f"(exit {result.returncode}): {stderr or stdout}"
        )
    return result.stdout.decode().strip()


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
    branch moved on locally, or a checkout has conflicting dirty edits) only
    means a later local checkout of the control branch must fetch. When no
    worktree has the branch checked out, a bare `update-ref` is enough. When
    one does — the common case: the primary checkout holds `main` while a
    detached launch worktree syncs — the ref must not be moved directly
    (that desyncs the attached worktree's index and makes stale files look
    like fresh edits to the next catch-all sweep); instead fast-forward
    *through* that worktree with `merge --ff-only`, which moves ref, index,
    and working tree together and refuses divergence or overwriting local
    edits.
    """
    worktree = _worktree_holding_branch(root, branch)
    if worktree is _WORKTREES_UNKNOWN:
        return
    if worktree is None:
        result = subprocess.run(
            ["git", "-C", str(root), "update-ref", f"refs/heads/{branch}", new],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        result = subprocess.run(
            ["git", "-C", str(worktree), "merge", "--ff-only", "--quiet", new],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, **_noninteractive_git_env()},
        )
    if result.returncode != 0:
        sys.stderr.write(
            f"[git] note: local {branch!r} not fast-forwarded "
            f"(origin has the commit): {result.stderr.strip()}\n"
        )


# Sentinel for "could not inspect worktrees" — distinct from "no worktree has
# the branch" (None), which safely takes the bare `update-ref` path.
_WORKTREES_UNKNOWN = Path("")


def _worktree_holding_branch(root: Path, branch: str) -> Path | None:
    """Path of the worktree with `branch` checked out, if any.

    Returns None when no worktree holds the branch, and `_WORKTREES_UNKNOWN`
    when the worktree listing itself fails (reported to stderr) — the caller
    must then skip ref updates entirely rather than assume the branch is free.
    """
    target = f"branch refs/heads/{branch}"
    try:
        listing = _run_git(root, "worktree", "list", "--porcelain")
    except GitError as exc:
        sys.stderr.write(
            f"[git] note: local {branch!r} not fast-forwarded "
            f"(could not inspect worktrees): {exc}\n"
        )
        return _WORKTREES_UNKNOWN
    current: Path | None = None
    for line in listing.splitlines():
        if line.startswith("worktree "):
            current = Path(line[len("worktree "):])
        elif line == target:
            return current
    return None


def list_worktrees(root: Path) -> list[tuple[Path, str | None]]:
    """Every git worktree as `(path, branch_name_or_None)`.

    Branch is `None` for a detached-HEAD worktree (the per-launch isolation
    default). Best-effort: returns `[]` when the listing fails or the checkout
    is not git-backed, so callers degrade to "can't tell" rather than crash.
    """
    try:
        listing = _run_git(root, "worktree", "list", "--porcelain")
    except GitError:
        return []
    out: list[tuple[Path, str | None]] = []
    path: Path | None = None
    branch: str | None = None
    for line in listing.splitlines():
        if line.startswith("worktree "):
            if path is not None:
                out.append((path, branch))
            path = Path(line[len("worktree "):])
            branch = None
        elif line.startswith("branch refs/heads/"):
            branch = line[len("branch refs/heads/"):]
    if path is not None:
        out.append((path, branch))
    return out


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


def _git_ref_present(root: Path, ref: str) -> bool:
    """True when an exact git ref exists in the local ref database."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "show-ref",
            "--verify",
            "--quiet",
            ref,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise GitError(
        f"`git show-ref --verify {ref}` failed "
        f"(exit {result.returncode}): {result.stderr.strip()}"
    )


def _remote_branch_present(root: Path, remote: str, branch: str) -> bool:
    """True when the configured remote has `refs/heads/<branch>`."""
    configured = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", remote],
        capture_output=True,
        text=True,
        check=False,
    )
    if configured.returncode != 0:
        return False

    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-remote",
            "--exit-code",
            "--heads",
            remote,
            branch,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 2:
        return False
    raise GitError(
        f"`git ls-remote --heads {remote} {branch}` failed "
        f"(exit {result.returncode}): {result.stderr.strip()}"
    )


def _control_branch_present(root: Path, branch: str, remote: str) -> bool:
    """True when the configured control branch exists locally or remotely.

    Local refs cover the common same-branch and cloned-feature cases without a
    remote probe. When no local ref exists, ask the configured remote exactly:
    a remote-only `origin/main` is still valid because the cross-branch landing
    path fetches that branch before pushing.
    """
    if _git_ref_present(root, f"refs/heads/{branch}"):
        return True
    if _git_ref_present(root, f"refs/remotes/{remote}/{branch}"):
        return True
    return _remote_branch_present(root, remote, branch)


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


# --- per-launch worktree isolation -------------------------------------------

# Default directory (relative to the git toplevel) holding per-launch `git
# worktree` checkouts when `[launch].worktree` is on. It lives under a gitignored
# `.coga/` so the primary checkout's `git status` never shows it and the
# `sync_coga_state` sweep never touches it (the sweep scopes to the `coga/` OS
# subtree, which this sits entirely outside of). Overridable per repo via
# `[launch].worktree_path` (`cfg.launch_worktree_path`); a custom in-repo path
# must be gitignored by the operator to keep those two properties.
_LAUNCH_WORKTREE_DIR = (".coga", "worktrees")


def _launch_worktree_base_dir(root: Path, cfg: Config) -> Path:
    """Resolve the configured per-launch worktree root.

    A relative `[launch].worktree_path` is anchored at the git toplevel; an
    absolute one is used verbatim. Falls back to the packaged default when the
    config carries no path (older `Config` shapes in tests).
    """
    configured = getattr(cfg, "launch_worktree_path", None) or os.path.join(
        *_LAUNCH_WORKTREE_DIR
    )
    candidate = Path(configured)
    if candidate.is_absolute():
        return candidate
    return root / candidate


# A launch worktree this old is treated as a crash orphan and reaped on the next
# launch. Deliberately generous: the per-launch `finally` removal is the primary
# cleanup, so this only mops up worktrees a hard crash (SIGKILL / power loss)
# left behind. An attended interactive session running continuously past this
# threshold is vanishingly unlikely, and reaping one only makes that session's
# syncs fail loudly rather than corrupting anything.
_ORPHAN_WORKTREE_MAX_AGE_SECONDS = 24 * 60 * 60


def add_launch_worktree(cfg: Config, key: str) -> Path | None:
    """Create a detached worktree at the control-branch tip for one launch.

    Returns the worktree's absolute path, or None when there is no git repo to
    isolate within — without git sync there is no shared-index race, so the
    caller just runs in the primary checkout unchanged.

    The checkout is **detached** at the control branch's commit rather than on a
    branch: the control branch is already checked out in the primary tree (git
    forbids a second worktree on the same branch), and a detached HEAD routes
    every task-state sync through the cross-branch temp-index overlay — the path
    that never touches a shared `.git/index`, which is the entire point of the
    isolation. Falls back to detaching at the current `HEAD` when the control
    branch ref is absent (e.g. a launch from a checkout that predates it).

    Raises `GitError` on a real `git worktree add` failure; the caller decides
    whether that aborts the launch.
    """
    root = _toplevel(cfg.repo_root)
    if root is None:
        return None
    base = _launch_worktree_base_dir(root, cfg)
    base.mkdir(parents=True, exist_ok=True)
    path = base / key
    commitish = _launch_worktree_base(root, cfg.git_remote, cfg.git_control_branch)
    _run_git(root, "worktree", "add", "--detach", str(path), commitish)
    return path


def _launch_worktree_base(root: Path, remote: str, branch: str) -> str:
    """Best local ref to detach a launch worktree from."""
    local_ref = f"refs/heads/{branch}"
    if _git_ref_present(root, local_ref):
        return local_ref
    remote_ref = f"refs/remotes/{remote}/{branch}"
    if _git_ref_present(root, remote_ref):
        return remote_ref
    return "HEAD"


def launch_worktree_has_dirty_coga_state(cfg: Config, path: Path) -> bool:
    """True when a launch worktree still has recoverable Coga OS changes.

    Used before teardown. Detached launch worktrees may retain state that the
    non-fatal git sync layer could not land; force-removing such a checkout
    would delete the only local copy. Dirt relative to the worktree's detached
    base is expected after a successful sync, so this compares dirty Coga paths
    to the fetched control tip and preserves the worktree only when applying
    those paths would still change that tip. Non-Coga scratch files do not block
    cleanup.
    """
    root = _toplevel(path)
    if root is None:
        return False
    coga_root = repo_root_in_worktree(cfg, path)
    state_pathspecs = _coga_state_pathspecs(root, coga_root)
    changed = _changed_paths_under(root, state_pathspecs)
    if not changed:
        return False
    return not _changed_paths_match_control_tip(cfg, root, changed)


def _changed_paths_match_control_tip(
    cfg: Config, root: Path, rels: list[str]
) -> bool:
    """Whether dirty working-tree paths are already represented on control."""
    _run_git(root, "fetch", cfg.git_remote, cfg.git_control_branch)
    control = _run_git(root, "rev-parse", "FETCH_HEAD").strip()
    ancestor = _run_git(root, "merge-base", "HEAD", control).strip()
    union = _union_merge_paths(root, rels)
    for rel in rels:
        if rel in union:
            if not _union_path_includes_worktree(
                root, current_rev=control, base_rev=ancestor, rel=rel
            ):
                return False
            continue
        if _working_tree_bytes(root, rel) != _tree_bytes(root, control, rel):
            return False
    return True


def _union_path_includes_worktree(
    root: Path, *, current_rev: str, base_rev: str, rel: str
) -> bool:
    current = _tree_bytes(root, current_rev, rel) or b""
    try:
        merged = _merge_union_path(
            root, current_rev=current_rev, base_rev=base_rev, rel=rel
        )
    except GitError:
        return False
    return merged == current


def remove_launch_worktree(cfg: Config, path: Path) -> None:
    """Remove a per-launch worktree and prune its registry entry. Best-effort.

    Never raises: cleanup runs in `coga launch`'s `finally`, so a failed removal
    must not mask the launch's real outcome. Callers that care about recoverable
    Coga state should check first; this primitive is intentionally forceful so a
    stray scratch file cannot wedge teardown. Removal is driven from the
    *primary* git root, never from inside `path` itself, so git does not refuse
    it as "the current working tree".
    """
    root = _toplevel(cfg.repo_root)
    if root is None:
        return
    try:
        _run_git(root, "worktree", "remove", "--force", str(path))
    except GitError:
        pass
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    try:
        _run_git(root, "worktree", "prune")
    except GitError:
        pass


def reap_orphan_launch_worktrees(
    cfg: Config, *, max_age_seconds: float = _ORPHAN_WORKTREE_MAX_AGE_SECONDS
) -> None:
    """Force-remove crash-orphaned launch worktrees, best-effort.

    Normal teardown removes a launch worktree in `coga launch`'s `finally`; this
    is the backstop for a hard crash that skipped it. Run on launch entry: prune
    git's registry, then force-remove any directory under the worktree root older
    than `max_age_seconds` (a live session is created far more recently). Never
    raises — orphan cleanup must not block a fresh launch.
    """
    root = _toplevel(cfg.repo_root)
    if root is None:
        return
    try:
        _run_git(root, "worktree", "prune")
    except GitError:
        pass
    base = _launch_worktree_base_dir(root, cfg)
    if not base.is_dir():
        return
    now = time.time()
    try:
        entries = list(base.iterdir())
    except OSError:
        return
    for entry in entries:
        if not entry.is_dir():
            continue
        try:
            age = now - entry.stat().st_mtime
        except OSError:
            continue
        if age >= max_age_seconds:
            remove_launch_worktree(cfg, entry)


def repo_root_in_worktree(cfg: Config, worktree_path: Path) -> Path:
    """Map `cfg.repo_root` (the coga OS dir) into a sibling worktree checkout.

    `cfg.repo_root` may be the git toplevel or a nested `coga/` under it;
    preserve that relative position inside `worktree_path` so a re-loaded config
    rooted there resolves the same task tree.
    """
    root = _toplevel(cfg.repo_root)
    if root is None:
        return worktree_path
    return worktree_path / cfg.repo_root.relative_to(root)


__all__ = [
    "GitError",
    "add_launch_worktree",
    "launch_worktree_has_dirty_coga_state",
    "reap_orphan_launch_worktrees",
    "remove_launch_worktree",
    "repo_root_in_worktree",
    "sync_coga_state",
    "sync_log",
    "sync_paths",
    "sync_task_state",
]
