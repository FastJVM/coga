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
checkouts take the same temp-index path; `merge=union` files that cannot
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
successful landing push, the local control ref is normally fast-forwarded
best-effort: directly via `update-ref` when no worktree holds the branch, or
through the holding worktree with `merge --ff-only` — without this, a checkout
left on `main` would fall behind origin after every cross-branch landing until
a manual pull. The narrow exception is Retro's verified linked-worktree direct
delete: `sync_paths(update_local_control_ref=False)` deliberately leaves the
operator's control checkout untouched after the remote landing.

That best-effort fast-forward moves only the control *ref*: a checkout parked
on any other branch keeps rendering task state as of its own last commit, so
the operator who just watched a launch finish still saw the old step in
`coga status`. `refresh_coga_state_from_control` is the pull-back half that
closes the loop — `coga launch` runs it against the launch checkout on every
exit path, fetching `origin/<control>` and folding its `coga/tasks/**` (and,
union-safely, `log.md`) back into the working tree. `stale_coga_task_rels` is
the read-only companion probe `coga status` uses to at least *warn* when the
remote-tracking control ref is known to be ahead — local refs only, no fetch,
so the render stays no-network.

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
from datetime import datetime
from pathlib import Path

from coga.config import Config
from coga.logfile import append_log, ref_tag_for_path
from coga.lifecycle import TERMINAL_STATUSES
from coga.paths import log_path, tasks_dir
from coga.taskfile import TaskFileError, split_body
from coga.ticket import Ticket, TicketError

# Bounded retries when racing `refs/heads/<control>`: each loss is a refetch +
# rebuild + repush, so a small ceiling is plenty under realistic contention
# (the coga launch auto-chain, manual commands).
_MAX_SYNC_ATTEMPTS = 5

# Process exit code meaning "refused because the control checkout could not
# integrate the latest control tip; nothing was mutated". The recurring-scan
# freshness gate exits with it, and the layers wrapping a launch key off it to
# skip their post-run git catch-up (launch's control refresh — bootstrap-script
# launches only, since bootstrap scripts are coga-owned — and the CLI
# end-of-command state sweep): on a checkout already known to be diverged those
# attempts are guaranteed to fail — re-dumping the same conflict — and the
# end-of-command sweep would stack a new local commit per failed run, deepening
# the divergence a human must eventually resolve. 75 is BSD's EX_TEMPFAIL
# ("temporary failure, retry later"), deliberately far from the small codes
# user ticket scripts commonly exit with, so an ordinary script failure is
# never mistaken for this refusal.
STALE_CONTROL_EXIT_CODE = 75

_ROOT_LAYOUT_COGA_PATHS = (
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
    "canceled": 3,
}

_StateGuard = Callable[[str], None]


class GitError(Exception):
    """Raised when a git operation fails (git missing, or a non-zero exit).

    Distinct from the soft "not a git repo" no-op: this signals a real
    failure on the control branch that the caller surfaces as a crash.
    """


class StateRegressionError(GitError):
    """Raised when catch-all Coga-state sync would commit stale task state."""


def summarize_git_failure(output: str) -> str:
    """Distill raw git failure output to the lines a human acts on.

    A failed rebase/merge dumps per-commit progress (`Rebasing (1/14)`),
    `Auto-merging` lines, autostash notes, and multi-line `hint:` blocks around
    the two lines that matter: `error:`/`fatal:` and `CONFLICT … in <file>`.
    Coga error paths embed this output verbatim into messages that then get
    printed by several layers, so one conflict became ~60 lines of spew. Keep
    only the actionable lines (deduped, order preserved); fall back to the last
    non-empty line so an unrecognized failure is never silently emptied.
    """
    keep: list[str] = []
    seen: set[str] = set()
    last_nonempty = ""
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        # `git rebase` progress rides carriage returns on one line; the last
        # segment is the real message.
        line = line.split("\r")[-1].strip()
        if line:
            last_nonempty = line
        if (
            line.startswith(("error:", "fatal:", "CONFLICT"))
            and line not in seen
        ):
            seen.add(line)
            keep.append(line)
    if not keep:
        return last_nonempty
    return "; ".join(keep)


@dataclass(frozen=True)
class _TicketState:
    status: str | None
    step: str | None
    step_index: int | None
    blackboard_bytes: int | None


def sync_task_state(
    cfg: Config,
    task_path: Path,
    *,
    message: str,
    guard: _StateGuard | None = None,
) -> None:
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

    `guard` is forwarded to `sync_paths`; status-transition callers pass
    `guard_ticket_state` so a stale checkout cannot overlay its ticket onto a
    newer control tip.
    """
    sync_paths(cfg, task_path, [task_path], message=message, guard=guard)


def stranded_product_paths(cfg: Config, anchor_path: Path) -> list[str]:
    """Tracked non-Coga paths this checkout committed that the control branch lacks.

    The detection half of the `direct/body` stranding guard. A workflow with no
    push/PR step (`direct/body`) can leave committed *product* code on a
    throwaway branch or detached checkout: coga's scoped state-sync lands only
    the `coga/` OS-state subtree on the control branch (never `git add -A`), so
    the product commit rides no branch that reaches `main`. When that checkout
    is deleted its ref goes with it and the commits dangle — the 2026-07-06
    DaCapo incident. This surfaces that code *before* `mark done` closes the
    task.

    Compares the current HEAD against the control branch with a merge-base
    (three-dot) diff, `--name-only`, restricted to paths **outside** the Coga
    OS-state subtree (the same pathspecs `sync_coga_state` owns, negated). The
    three-dot form isolates what HEAD introduced since it forked, so an
    independently-advanced control branch is not mistaken for stranded work; and
    a HEAD already level with the control branch (the on-`main` `mark done`) is a
    fast `[]`. Only tracked, committed files appear, so ignored files and the
    dirty working tree are out of scope by construction.

    Fail-open — returns `[]` and never raises when git is disabled, this is not a
    git repo, the control branch is absent, or any git probe fails: a guard that
    cannot inspect git must not block a local `mark done` transition (the on-disk
    markdown is the source of truth, per this module's failure model).
    """
    if not cfg.git_enabled:
        return []
    try:
        root = _toplevel(anchor_path)
        if root is None:
            return []
        # A local base is all this function needs (the three-dot diff is
        # against a local rev); `_local_control_base` returns None when neither
        # the local branch nor the fetched remote-tracking ref exists, which
        # already covers "control branch absent". Unlike the sync helpers this
        # never fetches/pushes, so it skips their `_control_branch_present`
        # pre-check and its remote-only `ls-remote` probe.
        base = _local_control_base(root, cfg.git_remote, cfg.git_control_branch)
        if base is None:
            return []
        head = _run_git(root, "rev-parse", "HEAD").strip()
        if head == base:
            return []
        excludes = [
            f":(exclude){spec}"
            for spec in _coga_state_pathspecs(root, cfg.repo_root)
        ]
        # `-z` (NUL-delimited, no path quoting) so a product file with
        # non-ASCII characters is named verbatim in the `mark done` error rather
        # than git-quoted — the same reason `_changed_paths_under` uses it.
        out = _run_git(
            root, "diff", "-z", "--name-only", f"{base}...{head}", "--", ".", *excludes
        )
        return [path for path in out.split("\x00") if path]
    except GitError:
        return []


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
    update_local_control_ref: bool = True,
    land_union_files_to_control: bool = False,
    guard: _StateGuard | None = None,
) -> None:
    """Commit explicit paths and push them to the control branch.

    This is the multi-path variant used by `coga ticket` authoring, where the
    subprocess may edit a task and create supporting local context/skill files.
    Callers must pass exact paths they own; Coga still never stages the whole
    worktree. `anchor_path` is used to find the git root and to record a sync
    failure in an appropriate log. `update_local_control_ref=False` is the
    narrow isolated-worktree escape hatch used by Retro's direct deletes: the
    removal still lands on the remote control branch, but Coga does not then
    fast-forward a different worktree that has the local control branch
    checked out. ``land_union_files_to_control=True`` is the narrow terminal-
    abandonment path: merge=union evidence files are three-way unioned onto
    the control branch immediately because the current feature branch may
    intentionally never merge.

    `guard` is called with each candidate control-branch base before the
    overlay is built — including the base refetched after a non-fast-forward
    retry — and raises `StateRegressionError` to abort the landing. Status
    transitions pass `guard_ticket_state`: the overlay replaces the ticket
    wholesale on the control tip, so without it a stale checkout can bury a
    newer copy that another checkout already landed.
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

        # Merge=union files must NOT ride the cross-branch overlay — an overlay
        # replaces a file wholesale on the control tip, dropping lines another
        # branch appended concurrently. Instead they are folded into the local
        # commit and ordinarily reach control through a same-branch push or the
        # feature PR. Cancellation is the exception: its branch may never merge,
        # so the caller asks us to union-land the audit/digest evidence now.
        log_rel = _relative_to_root(root, log_path(cfg))
        local_rels = rels + [log_rel] if log_path(cfg).exists() else rels
        local_rels = list(dict.fromkeys(local_rels))
        union_rels = _union_merge_paths(root, local_rels)
        overlay_rels = [rel for rel in rels if rel not in union_rels]
        control_union_rels = (
            [rel for rel in local_rels if rel in union_rels]
            if land_union_files_to_control
            else []
        )

        _dispatch_branch_sync(
            cfg,
            root,
            local_rels=local_rels,
            overlay_rels=overlay_rels,
            control_union_rels=control_union_rels,
            message=message,
            guard=guard,
            update_local_control_ref=update_local_control_ref,
        )
    except StateRegressionError as exc:
        # A refusal is not a failure to reach git — it is git refusing to bury
        # newer state, so it gets its own line and no `sync failed` log entry
        # (the guard already recorded the reason against the task). The local
        # write stands and the checkout is now knowingly behind control;
        # `stale_coga_task_rels` keeps surfacing that divergence in views.
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
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
    side-effects written *past* the last per-command sync (the digest spool and
    stray log lines) and human hand-edits to tickets/blackboards/contexts that
    no command touched. Per-session usage records are not part of this sweep:
    launch appends them to `log.md` and commits that file directly with
    `sync_log`. The remaining side effects and hand-edits converge on git at the
    *next* coga invocation — lazy, on-access, no daemon (see
    `coga/architecture`'s "no database, no daemon, no in-memory state").

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


def refresh_coga_state_from_control(
    cfg: Config, *, message: str = "Refresh coga state from control"
) -> None:
    """Pull the control branch's task state back into this checkout.

    The pull-back half of the always-on sync contract, run by `coga launch`
    when a run ends (bump handoff, `mark done`, `mark canceled`, `block`,
    agent exit — every
    exit path the supervisor sees). The publish half above lands each
    transition on `origin/<control>` but fast-forwards only the local control
    *ref*, so a checkout parked on any other branch keeps rendering task state
    as of its own last commit: the operator watches a launch finish, runs
    `coga status` in the same terminal, and sees the completed step missing.

    Branch handling:

      - Control branch → fetch + `merge --ff-only` onto the fetched tip. The
        checkout *is* the control branch, so a plain fast-forward is the whole
        refresh; a diverged local control is a loud non-fatal miss, never an
        implicit merge.
      - Feature branch → fetch, overlay the `coga/tasks/**` files changed on
        the fetched control tip since its merge base with HEAD, and commit them
        on the current branch — the same local-commit shape the mid-run
        feature-branch sync uses, so the branch's product tree is never
        touched. `coga/log.md` is three-way union-merged (local ∪ control) so
        locally appended log lines survive. Three guards keep the overlay
        safe: a path dirty in the working tree is skipped (a hand-edit in
        flight belongs to the catch-all sweep and its regression guard, not a
        blind overwrite); committed local divergence is preserved unless the
        control history proves it already absorbed that exact local version;
        and a ticket whose local state is *ahead* of the control copy is skipped
        (`_guard_coga_state_regressions`'s rule pointed the other way — a
        refresh must never move local state backward).
      - Detached HEAD → skip with a stderr note; the refresh commit would be
        orphaned. Launch runs this against the checkout it was invoked from.

    Same non-fatal failure model as `sync_paths` (stderr + `coga/log.md`,
    never a crash): a checkout that cannot refresh is exactly as stale as it
    already was, and surfacing the run's real outcome matters more.
    """
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (refresh suppressed): {message}\n")
        return
    try:
        root = _toplevel(cfg.repo_root)
        if root is None:
            sys.stderr.write(f"[git] not a git repo (refresh skipped): {message}\n")
            return
        if not _control_branch_present(root, cfg.git_control_branch, cfg.git_remote):
            sys.stderr.write(
                _control_branch_mismatch_message(cfg, root) + f" ({message})\n"
            )
            return
        branch = _current_branch(root)
        if branch == "HEAD":
            sys.stderr.write(
                f"[git] detached HEAD — coga state not refreshed. ({message})\n"
            )
            return
        _run_git(root, "fetch", cfg.git_remote, cfg.git_control_branch)
        tip = _run_git(root, "rev-parse", "FETCH_HEAD").strip()
        if branch == cfg.git_control_branch:
            _run_git(root, "merge", "--ff-only", "--quiet", tip)
            return
        _refresh_branch_from_control(cfg, root, tip, message)
    except GitError as exc:
        sys.stderr.write(f"[git] refresh failed: {exc}. Message was: {message}\n")
        append_log(
            cfg, ref_tag_for_path(cfg, cfg.repo_root), "git", f"refresh failed: {exc}"
        )


def _refresh_branch_from_control(
    cfg: Config, root: Path, tip: str, message: str
) -> None:
    """Overlay the control tip's newer task paths onto a feature checkout."""
    tasks_rel = _relative_to_root(root, cfg.repo_root / "tasks")
    ancestor = _run_git(root, "merge-base", "HEAD", tip).strip()
    out = _run_git(
        root, "diff", "-z", "--name-only", ancestor, tip, "--", tasks_rel
    )
    candidates = [rel for rel in out.split("\x00") if rel]
    dirty = set(_changed_paths_under(root, [tasks_rel]))
    updated: list[str] = []
    for rel in candidates:
        if rel in dirty:
            sys.stderr.write(
                f"[git] refresh: leaving {rel} untouched — it has uncommitted "
                "local changes (the next command's state sweep owns them).\n"
            )
            continue
        control = _tree_bytes(root, tip, rel)
        reason = _refresh_regression_reason(cfg, root, rel, control)
        if reason is not None:
            sys.stderr.write(f"[git] refresh: leaving {rel} untouched — {reason}.\n")
            continue
        reason = _refresh_committed_divergence_reason(
            root, rel, control, ancestor, tip
        )
        if reason is not None:
            sys.stderr.write(f"[git] refresh: leaving {rel} untouched — {reason}.\n")
            continue
        _write_worktree_bytes(root, rel, control)
        updated.append(rel)
    updated.extend(_refresh_log_from_control(cfg, root, tip))
    if updated:
        _commit_paths(root, updated, message)


def _refresh_regression_reason(
    cfg: Config, root: Path, rel: str, control: bytes | None
) -> str | None:
    """Why overwriting `rel` from the control tip would regress local state.

    None when the overwrite is safe. Only ticket files carry orderable state;
    attachments and other task files always follow the control copy. A path
    deleted on the control branch propagates too — a retire/delete that landed
    elsewhere is newer state, and any in-flight local edit was already kept by
    the dirty-path guard.
    """
    if rel not in _changed_task_ticket_rels(root, cfg.repo_root, [rel]):
        return None
    if control is None:
        return None
    local = _working_tree_bytes(root, rel)
    if local is None:
        return None
    local_state = _ticket_state_from_bytes(local)
    control_state = _ticket_state_from_bytes(control)
    if local_state is None or control_state is None:
        return None
    reason = _ticket_state_regression_reason(
        rel, committed=local_state, working=control_state
    )
    if reason is None:
        return None
    return f"the local copy is ahead of the control branch ({reason})"


def _refresh_committed_divergence_reason(
    root: Path,
    rel: str,
    control: bytes | None,
    ancestor: str,
    tip: str,
) -> str | None:
    """Preserve committed feature-side task changes that control did not absorb.

    A two-tip task diff cannot tell which branch introduced a difference. The
    caller narrows candidates to control-side changes since the merge base;
    this second guard handles paths changed on *both* sides. Control may replace
    the local version only when that exact blob appears in the control path's
    post-fork history: proof the publish half absorbed it before later state
    advanced. Otherwise choosing either side would discard committed content.
    """
    local = _tree_bytes(root, "HEAD", rel)
    base = _tree_bytes(root, ancestor, rel)
    if local == base or local == control:
        return None
    if local is not None:
        commits = _run_git(root, "rev-list", f"{ancestor}..{tip}", "--", rel)
        if any(
            _tree_bytes(root, commit, rel) == local
            for commit in commits.splitlines()
        ):
            return None

    return "it has committed local changes not superseded by newer control state"


def _refresh_log_from_control(cfg: Config, root: Path, tip: str) -> list[str]:
    """Union-merge the control tip's `log.md` into the working tree.

    Returns `[log_rel]` when the merge changed the local copy, else `[]`.
    Direction matters: `current` is the local working copy (committed or
    still dirty), so lines only this checkout has survive while the control
    branch's lines fold in — the same union contract the publish paths honor
    in the opposite direction.
    """
    log_rel = _relative_to_root(root, log_path(cfg))
    control = _tree_bytes(root, tip, log_rel)
    if control is None:
        return []
    local = _working_tree_bytes(root, log_rel) or b""
    ancestor = _run_git(root, "merge-base", "HEAD", tip).strip()
    base = _tree_bytes(root, ancestor, log_rel) or b""
    merged = _merge_union_bytes(current=local, base=base, other=control)
    if merged == local:
        return []
    _write_worktree_bytes(root, log_rel, merged)
    return [log_rel]


def _write_worktree_bytes(root: Path, rel: str, data: bytes | None) -> None:
    """Write (or remove, for None) one repo-relative file in the working tree."""
    path = root / rel
    if data is None:
        if path.is_file():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def stale_coga_task_rels(cfg: Config) -> list[str]:
    """Task paths where the remote-tracking control ref is ahead of this checkout.

    The read-only staleness probe behind `coga status`'s warning. Compares the
    working tree against `refs/remotes/<remote>/<control>` — local refs only,
    never a fetch, so a render stays no-network (`coga/principles` #6); the
    answer is as fresh as the last fetch, which is exactly the information the
    stale view itself was built from. Counts only differences that are
    provably *newer* on the remote side: a ticket whose remote copy is ahead
    on step/status progress, or a ticket present in the remote tree and absent
    locally. Locally-ahead or merely-divergent files are not staleness — a
    warning that cries wolf on every hand-edit would be tuned out. Fail-open:
    any git failure returns [] (a warning probe must never break `status`).
    """
    if not cfg.git_enabled:
        return []
    try:
        root = _toplevel(cfg.repo_root)
        if root is None:
            return []
        ref = f"refs/remotes/{cfg.git_remote}/{cfg.git_control_branch}"
        if not _git_ref_present(root, ref):
            return []
        tasks_rel = _relative_to_root(root, cfg.repo_root / "tasks")
        out = _run_git(root, "diff", "-z", "--name-only", ref, "--", tasks_rel)
        return [
            rel
            for rel in out.split("\x00")
            if rel and _remote_ticket_is_newer(cfg, root, ref, rel)
        ]
    except GitError:
        return []


def _remote_ticket_is_newer(cfg: Config, root: Path, rev: str, rel: str) -> bool:
    """Whether `rev`'s copy of ticket `rel` is strictly ahead of the checkout's."""
    if rel not in _changed_task_ticket_rels(root, cfg.repo_root, [rel]):
        return False
    remote = _tree_bytes(root, rev, rel)
    if remote is None:
        # Only exists locally — local-ahead (e.g. a fresh draft), not stale.
        return False
    try:
        local = _working_tree_bytes(root, rel)
    except GitError:
        return False
    if local is None:
        # Landed on control, absent here — definitionally behind.
        return True
    remote_state = _ticket_state_from_bytes(remote)
    local_state = _ticket_state_from_bytes(local)
    if remote_state is None or local_state is None:
        return False
    return (
        _ticket_state_regression_reason(
            rel, committed=remote_state, working=local_state
        )
        is not None
    )


def _dispatch_branch_sync(
    cfg: Config,
    root: Path,
    *,
    local_rels: list[str],
    overlay_rels: list[str],
    control_union_rels: list[str] | None = None,
    message: str,
    guard: _StateGuard | None = None,
    update_local_control_ref: bool = True,
) -> None:
    """Commit `local_rels` on the current branch and land `overlay_rels` on the
    control branch — the branch-aware core shared by `sync_paths` and
    `sync_coga_state`.

      - HEAD is the control branch → commit `local_rels` and push; the union
        files in `local_rels` ride the push-rebase's union merge.
      - Feature branch → commit `local_rels` locally (so the checkout reflects
        OS state), then land `overlay_rels` on the control branch via the
        working-tree-free overlay. A caller may also explicitly land selected
        merge=union files when their evidence cannot wait for a future PR.
      - Detached HEAD → skip the local commit (it would be orphaned); still land
        `overlay_rels` on the control branch.
    """
    control_union_rels = control_union_rels or []
    branch = _current_branch(root)
    if branch == cfg.git_control_branch:
        _sync_paths_on_control_branch(
            cfg, root, local_rels, message=message, guard=guard
        )
        return

    if branch == "HEAD":
        # Detached HEAD: no local commit — it would be orphaned. The landing
        # pushes the control branch and normally fast-forwards the primary
        # checkout via `_try_update_local_ref`; Retro's verified linked-
        # worktree delete can suppress that refresh. Only a fast-forward miss
        # warrants a stderr note, printed there.
        overlay = set(overlay_rels)
        union_rels = list(
            dict.fromkeys(
                [rel for rel in local_rels if rel not in overlay]
                + control_union_rels
            )
        )
        _land_paths_on_control_branch(
            cfg,
            root,
            overlay_rels,
            union_rels=union_rels,
            message=message,
            guard=guard,
            update_local_control_ref=update_local_control_ref,
        )
        return
    else:
        before = _run_git(root, "rev-parse", "HEAD").strip() if guard else None
        _commit_paths(root, local_rels, message)
    try:
        _land_paths_on_control_branch(
            cfg,
            root,
            overlay_rels,
            union_rels=control_union_rels,
            message=message,
            guard=guard,
            update_local_control_ref=update_local_control_ref,
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


def guard_ticket_state(
    cfg: Config,
    ticket_path: Path,
    base: str,
    *,
    allow_step_rewind: bool = False,
) -> None:
    """Refuse to land one ticket over a newer copy already on `base`.

    The per-transition counterpart of `_guard_coga_state_regressions`. The
    catch-all sweep guards whatever it happened to find dirty; a state
    transition knows exactly which ticket it is about to overlay, so it binds
    this to that ticket and hands the result to `sync_paths(guard=...)`. Same
    rules, same refusal: a terminal control-branch status is never replaced, and
    step/status never move backward.

    Pass the ticket file (`TaskRef.ticket_path`), not the task directory — the
    comparison reads ticket frontmatter, and a directory rel matches nothing.
    """
    root = _toplevel(ticket_path)
    if root is None:
        return
    _guard_coga_state_regressions(
        cfg,
        root,
        [_relative_to_root(root, ticket_path)],
        base,
        allow_step_rewind=allow_step_rewind,
    )


def ticket_state_guard(
    cfg: Config, ticket_path: Path, *, allow_step_rewind: bool = False
) -> _StateGuard:
    """Bind `guard_ticket_state` to one ticket, ready for `sync_paths(guard=)`.

    Every publisher of ticket state uses this: `mark`'s status transitions,
    `bump`'s step moves, and `unblock`'s resolve-only write. The sync layer
    calls the result once per landing attempt, so the check re-runs against the
    tip refetched after a non-fast-forward retry.

    `allow_step_rewind=True` is for `coga bump --to/--backward` only — see
    `_ticket_state_regression_reason`.
    """

    def guard(base: str) -> None:
        guard_ticket_state(
            cfg, ticket_path, base, allow_step_rewind=allow_step_rewind
        )

    return guard


def _guard_coga_state_regressions(
    cfg: Config,
    root: Path,
    rels: list[str],
    base: str,
    *,
    allow_step_rewind: bool = False,
) -> None:
    """Fail loud before a catch-all sweep commits stale task frontmatter.

    `sync_coga_state` is intentionally broad within the Coga OS subtree. That
    breadth is safe for usage records and hand-edits, but not for a stale
    checkout whose task file predates a newer bump. Compare dirty task tickets
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
            rel,
            committed=committed_state,
            working=working_state,
            allow_step_rewind=allow_step_rewind,
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
    rel: str,
    *,
    committed: _TicketState,
    working: _TicketState,
    allow_step_rewind: bool = False,
) -> str | None:
    """Why landing `working` over `committed` would lose state, or `None`.

    `allow_step_rewind=True` drops *only* the step-backward rule, for the one
    caller whose backward move is the point: a human `coga bump --to/--backward`
    rewind. The status rules below still apply — a rewind never changes status,
    so a status regression there means the checkout is stale, not deliberate.
    """
    if (
        not allow_step_rewind
        and committed.step_index is not None
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

    if (
        committed.status in TERMINAL_STATUSES
        and working.status != committed.status
    ):
        return (
            f"{rel}: terminal status would change from "
            f"{committed.status!r} to {working.status!r}"
        )

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
            f"{summarize_git_failure(rebase.stderr + rebase.stdout)}"
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
    update_local_control_ref: bool = True,
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
            if update_local_control_ref:
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
    checkouts, where there is no durable local branch commit for `log.md`
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
    one does — e.g. the primary checkout holds `main` while a sync lands from
    a feature worktree or detached checkout — the ref must not be moved directly
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
            f"{summarize_git_failure(result.stderr) or summarize_git_failure(result.stdout)}"
        )
    return result.stdout


def last_commit_times(cfg: Config) -> dict[str, datetime]:
    """Map each path under `tasks/` to the commit time it was last touched.

    Keys are posix paths relative to `tasks/` (`v2/foo.md`,
    `cleanup/bar/ticket.md`) — raw git data, deliberately not resolved to task
    refs here, so this stays a plain "when did git last see this file" query
    with no task-shape knowledge in it. Mapping paths onto tasks is the
    caller's job (`_git_updated_by_slug`).

    The fallback source for `coga status`'s `Updated` column. The primary
    source is `coga/log.md`, keyed by task ref — which goes blank in two
    situations the log cannot express:

      - **A task directory was moved.** Refs are path-qualified and log lines
        are append-only, so a `mv` orphans every existing line under the old
        ref and the task reads as though nothing ever happened to it.
      - **A task never passed through a logging command.** Bulk migrations and
        hand-authored tickets land on disk without a `created` line.

    Git already knows both — a rename is a commit touching the new path, and
    a hand-written ticket still had to be committed. One
    `git log --name-only` pass over `tasks/` costs a single subprocess for the
    whole render (~0.1s on a 2k-commit history), rather than a `--follow` per
    task.

    Read-only by construction: `git log` mutates nothing and touches no
    network, so `status` stays a pure view (principle 6). Returns `{}` rather
    than raising when git is disabled, absent, or the checkout has no commits
    yet — a missing timestamp degrades to today's blank cell, which is strictly
    better than a view that crashes.
    """
    if not cfg.git_enabled:
        return {}
    root = _toplevel(tasks_dir(cfg))
    if root is None:
        return {}
    rel = _relative_to_root(root, tasks_dir(cfg))
    try:
        out = _run_git(root, "log", "--format=%ct", "--name-only", "--", rel)
    except GitError:
        return {}

    prefix = rel.rstrip("/") + "/"
    times: dict[str, datetime] = {}
    stamp: datetime | None = None
    for line in out.splitlines():
        if not line:
            continue
        if line.isdigit():
            stamp = datetime.fromtimestamp(int(line))
            continue
        if stamp is None or not line.startswith(prefix):
            continue
        key = line[len(prefix) :]
        # `git log` walks newest-first, so the first time a path appears is
        # its most recent commit; later (older) mentions must not overwrite it.
        if key not in times:
            times[key] = stamp
    return times


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


def is_linked_worktree(start: Path) -> bool:
    """True only when `start` belongs to a linked git worktree.

    A linked worktree has its own administrative git dir under the repository's
    common git dir. The primary checkout (and an independent clone) reports the
    same path for both. Retro uses this read-only guard before a direct delete
    requests that Coga leave another checkout's control branch untouched.
    """
    root = _toplevel(start)
    if root is None:
        return False
    try:
        git_dir = _run_git(
            root, "rev-parse", "--path-format=absolute", "--git-dir"
        ).strip()
        common_dir = _run_git(
            root, "rev-parse", "--path-format=absolute", "--git-common-dir"
        ).strip()
    except GitError:
        return False
    return Path(git_dir).resolve() != Path(common_dir).resolve()


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


__all__ = [
    "GitError",
    "StateRegressionError",
    "guard_ticket_state",
    "is_linked_worktree",
    "refresh_coga_state_from_control",
    "stale_coga_task_rels",
    "sync_coga_state",
    "sync_log",
    "sync_paths",
    "sync_task_state",
    "ticket_state_guard",
]
