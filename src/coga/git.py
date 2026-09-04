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
dirty changes intact. A detached HEAD takes the cross-branch landing path and
normally skips the local commit (a commit on a detached HEAD would be
orphaned). A rewind opts into a scoped detached commit so its successfully
guarded ticket cannot remain dirty and ride a later unguarded sweep. After a
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
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from coga.config import Config
from coga.github_source import redacted_git_source
from coga.logfile import append_log, ref_tag_for_path
from coga.lifecycle import TERMINAL_STATUSES
from coga.paths import log_path, tasks_dir
from coga.taskfile import TaskFileError, split_body
from coga.ticket import Ticket, TicketError

# Bounded retries when racing `refs/heads/<control>`: each loss is a refetch +
# rebuild + repush, so a small ceiling is plenty under realistic contention
# (the coga launch auto-chain, manual commands).
_MAX_SYNC_ATTEMPTS = 5
_ANY_WORKTREE_BYTES = object()

# Process exit code meaning "the command deliberately retained retryable local
# state; do not run the catch-all end-of-command state sweep". The
# recurring-scan freshness gate uses it when the control checkout is stale, a
# recorded PR assist uses it when a leased log publication is refused, and a
# rewind uses it when control status no longer matches its retained local
# transition. In each case the ordinary sweep would destroy the refusal's
# safety property by committing exactly the bytes the narrow publisher
# intentionally left dirty.
# 75 is BSD's EX_TEMPFAIL ("temporary failure, retry later").
RETRY_WITHOUT_SWEEP_EXIT_CODE = 75

# Backward-compatible, domain-specific spelling used by recurring callers.
STALE_CONTROL_EXIT_CODE = RETRY_WITHOUT_SWEEP_EXIT_CODE

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
_FeaturePublicationGuard = Callable[[str], None]
_URL_IN_DIAGNOSTIC_RE = re.compile(r"https?://[^\s'\"<>]+")


class GitError(Exception):
    """Raised when a git operation fails (git missing, or a non-zero exit).

    Distinct from the soft "not a git repo" no-op: this signals a real
    failure on the control branch that the caller surfaces as a crash.
    """


class StateRegressionError(GitError):
    """Raised when catch-all Coga-state sync would commit stale task state."""


class FeaturePublicationError(GitError):
    """A strict generated feature-branch publication could not complete safely."""


class UncertainFeaturePublicationError(FeaturePublicationError):
    """A generated state update landed but its paired outcome is unknown.

    Callers must retain their generated local bytes: rolling them back could
    create or deepen a split with a remote ref that accepted the update before
    its acknowledgement or follow-up probe failed.
    """


@dataclass(frozen=True)
class FeaturePublicationLease:
    """Exact branch/control state authorizing one generated publication.

    ``control_ticket_state`` is the exact ``(status, step, assignee)`` tuple
    shared by the verified feature and control tips before the state command
    mutates its working-tree copy. ``control_task_oid`` pins the complete
    control-side task object at that same boundary (the ticket blob for a
    file-form task, or the task tree including attachments for directory form).
    Strict publication rechecks both against every candidate control tip.
    Ticket prose may legitimately differ on the PR branch at lease time, but a
    later control-side edit must force a retry rather than be overlaid.
    """

    branch: str
    local_oid: str
    remote_oid: str
    push_url: str | None = None
    control_ticket_state: tuple[str | None, str | None, str | None] | None = None
    control_task_oid: str | None = None


@dataclass
class FileMutationRollback:
    """Conditionally undo generated file bytes without erasing peer writes.

    Call ``arm`` with the exact bytes a command constructed after writing its
    generated ticket/log state and immediately before strict publication.
    ``restore`` rewinds an ordinary path only while its bytes still equal that
    generated snapshot. Append-only union paths instead remove just the
    generated lines, retaining additions a concurrent command made before
    publication failed.
    """

    originals: dict[Path, bytes | None]
    union_paths: frozenset[Path]
    generated: dict[Path, bytes | None] | None = None

    @classmethod
    def capture(
        cls,
        paths: Iterable[Path],
        *,
        union_paths: Iterable[Path] = (),
    ) -> FileMutationRollback:
        originals = {
            path: path.read_bytes() if path.is_file() else None
            for path in paths
        }
        return cls(
            originals=originals,
            union_paths=frozenset(union_paths),
        )

    def arm(self, updates: Mapping[Path, bytes | None]) -> None:
        """Record exact caller-constructed bytes without resampling live files."""
        unknown = set(updates) - set(self.originals)
        if unknown:
            names = ", ".join(str(path) for path in sorted(unknown, key=str))
            raise FeaturePublicationError(
                f"strict mutation snapshot does not cover {names}"
            )
        generated = dict(
            self.generated if self.generated is not None else self.originals
        )
        generated.update(updates)
        self.generated = generated

    def arm_append(self, path: Path, appended: bytes) -> None:
        """Record one exact append relative to the last owned path revision."""
        if path not in self.originals:
            raise FeaturePublicationError(
                f"strict mutation snapshot does not cover {path}"
            )
        source = self.generated if self.generated is not None else self.originals
        prior = source[path] or b""
        self.arm({path: prior + appended})

    def require_unchanged(self, path: Path) -> None:
        """Refuse a strict write when its captured input changed underneath it.

        Before the first generated mutation, ``originals`` is the expected
        revision. A multi-write state command may arm after an earlier generated
        edit (for example, appending a blocker before changing ``status``); in
        that case the latest armed snapshot is the only revision the next write
        may replace.
        """
        expected_by_path = (
            self.generated if self.generated is not None else self.originals
        )
        if path not in expected_by_path:
            raise FeaturePublicationError(
                f"strict mutation snapshot does not cover {path}"
            )
        expected = expected_by_path[path]
        current = path.read_bytes() if path.is_file() else None
        if current != expected:
            raise FeaturePublicationError(
                f"strict mutation input changed before writing {path}"
            )

    def restore(self) -> tuple[Path, ...]:
        """Undo generated bytes and return ordinary paths changed by a peer."""
        # Without an armed generated snapshot, current bytes might belong to a
        # peer that wrote after capture. Refuse every path rather than guessing
        # that those bytes are ours and erasing concurrent work.
        if self.generated is None:
            return tuple(self.originals)

        refused: list[Path] = []
        for path, prior in self.originals.items():
            current = path.read_bytes() if path.is_file() else None
            generated = self.generated[path]
            if current == prior:
                # A lower layer may already have restored this exact path
                # (notably a locally fast-forwarded compensation commit).
                continue
            if current == generated:
                _restore_file_bytes(path, prior)
                continue
            if (
                path in self.union_paths
                and current is not None
                and generated is not None
            ):
                try:
                    restored = _remove_generated_union_lines(
                        current=current,
                        prior=prior or b"",
                        generated=generated,
                        rel=str(path),
                    )
                except GitError:
                    refused.append(path)
                else:
                    if prior is None and not restored:
                        _restore_file_bytes(path, None)
                    else:
                        _restore_file_bytes(path, restored)
                continue
            refused.append(path)
        return tuple(refused)


def capture_task_file_bytes(
    task_path: Path,
    *,
    context: str = "strict task snapshot",
) -> dict[Path, bytes]:
    """Capture publishable regular task leaves without ignored local files.

    Git ignores are a hard publication boundary, not merely a convenience for
    ordinary ``git add``. Strict publishers build commits through a temporary
    index and can therefore bypass Git's normal ignore check; omit every
    ignored, untracked leaf explicitly while retaining tracked files that now
    match an ignore rule.
    """
    task_path = task_path.absolute()
    if task_path.is_symlink():
        raise FeaturePublicationError(
            f"{context} contains symbolic link {task_path}"
        )
    if task_path.is_file():
        candidates = [task_path]
    elif task_path.is_dir():
        # Classify Git-ignored entries before inspecting their file type.  An
        # ignored local environment may legitimately contain symlinks, FIFOs,
        # or sockets; those leaves are outside the publication boundary and
        # must not make a strict snapshot fail.  ``git check-ignore`` excludes
        # tracked matches, so a tracked symlink remains visible here and is
        # still rejected below.
        discovered = [child.absolute() for child in sorted(task_path.rglob("*"))]
        root = _toplevel(task_path)
        ignored = (
            _ignored_untracked_paths(root, discovered)
            if root is not None and discovered
            else frozenset()
        )
        candidates = []
        for child in discovered:
            if child in ignored:
                continue
            if child.is_symlink():
                raise FeaturePublicationError(
                    f"{context} contains symbolic link {child}"
                )
            if child.is_dir():
                continue
            if not child.is_file():
                raise FeaturePublicationError(
                    f"{context} is not a regular file: {child}"
                )
            candidates.append(child.absolute())
    else:
        candidates = []

    # A file-form task is the selected task anchor itself, not an incidental
    # ignored leaf.  Directory-form candidates were already filtered above.
    ignored = frozenset()
    return {
        path: path.read_bytes()
        for path in candidates
        if path not in ignored
    }


def capture_revision_file_bytes(
    task_path: Path,
    revision: str,
    *,
    context: str = "strict task revision",
) -> dict[Path, bytes]:
    """Capture every regular task leaf from one exact Git revision.

    This is the committed counterpart to :func:`capture_task_file_bytes`.
    Recovery code uses it only after a feature/control lease proves the named
    revision is authoritative, then conditionally replaces invalid generated
    worktree bytes with this exact task tree.  Git symlinks and submodules stay
    outside Coga's task-state publication model and therefore fail closed.
    """
    task_path = task_path.absolute()
    root = _toplevel(task_path)
    if root is None:
        raise FeaturePublicationError(
            f"{context} requires a git checkout"
        )
    task_rel = _relative_to_root(root, task_path)
    try:
        output = _run_git(
            root,
            "ls-tree",
            "-r",
            "-z",
            revision,
            "--",
            task_rel,
        )
    except GitError as exc:
        raise FeaturePublicationError(
            f"could not read {context} at {revision}: {exc}"
        ) from exc

    captured: dict[Path, bytes] = {}
    for entry in output.split("\x00"):
        if not entry:
            continue
        metadata, rel = entry.split("\t", 1)
        mode, kind, _oid = metadata.split(" ", 2)
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise FeaturePublicationError(
                f"{context} contains non-regular Git entry {rel}"
            )
        data = _tree_bytes(root, revision, rel)
        if data is None:  # pragma: no cover - ls-tree/cat-file invariant
            raise FeaturePublicationError(
                f"{context} lost Git entry {rel} while reading {revision}"
            )
        captured[(root / rel).absolute()] = data
    return captured


def _ignored_untracked_paths(
    root: Path,
    paths: Iterable[Path],
) -> frozenset[Path]:
    """Return paths Git ignores, excluding tracked ignore-pattern matches."""
    relative: list[str] = []
    for path in paths:
        try:
            relative.append(str(path.absolute().relative_to(root.absolute())))
        except ValueError:
            continue
    if not relative:
        return frozenset()

    payload = b"\0".join(os.fsencode(path) for path in relative) + b"\0"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-z", "--stdin"],
            input=payload,
            capture_output=True,
            check=False,
            env={**os.environ, **_noninteractive_git_env()},
        )
    except FileNotFoundError as exc:
        raise FeaturePublicationError(
            "could not enforce ignored-file publication boundaries: `git` "
            "was not found on PATH"
        ) from exc
    if result.returncode not in {0, 1}:
        detail = result.stderr.decode(errors="replace").strip()
        raise FeaturePublicationError(
            "could not enforce ignored-file publication boundaries: "
            f"`git check-ignore` exited {result.returncode}: {detail}"
        )
    return frozenset(
        (root / os.fsdecode(item)).absolute()
        for item in result.stdout.split(b"\0")
        if item
    )


def capture_task_mutation_snapshot(
    task_path: Path,
    *,
    extra_paths: Iterable[Path] = (),
    union_paths: Iterable[Path] = (),
) -> FileMutationRollback:
    """Capture every publishable task leaf and tracked deletion for strict reuse.

    A deterministic script may write an attachment before invoking a lifecycle
    command. That command must treat the exact existing task tree as its input,
    publish it with the transition, and roll back only its own later writes.
    Enumerating ``HEAD`` as well as the worktree records deleted tracked leaves
    as ``None``; symbolic links and special files are refused because the
    strict byte-overlay commit cannot preserve their identity safely.
    """
    task_path = task_path.absolute()
    originals: dict[Path, bytes | None] = dict(
        capture_task_file_bytes(
            task_path,
            context="strict task mutation input",
        )
    )

    root = _toplevel(task_path)
    if root is not None:
        task_rel = _relative_to_root(root, task_path)
        tracked = _run_git(
            root,
            "ls-tree",
            "-r",
            "-z",
            "--name-only",
            "HEAD",
            "--",
            task_rel,
        )
        for rel in (item for item in tracked.split("\x00") if item):
            path = (root / rel).absolute()
            originals.setdefault(
                path,
                path.read_bytes() if path.is_file() else None,
            )

    for path in extra_paths:
        resolved = path.absolute()
        originals[resolved] = resolved.read_bytes() if resolved.is_file() else None
    return FileMutationRollback(
        originals=originals,
        union_paths=frozenset(path.absolute() for path in union_paths),
    )


def _restore_file_bytes(path: Path, data: bytes | None) -> None:
    if data is None:
        if path.is_file():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


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


def _redact_git_command_text(text: str, args: Iterable[str]) -> str:
    """Remove credential-bearing URL userinfo from Git diagnostics."""
    safe = text
    for arg in args:
        redacted = redacted_git_source(arg)
        if redacted != arg:
            safe = safe.replace(arg, redacted)
    return _URL_IN_DIAGNOSTIC_RE.sub(
        lambda match: redacted_git_source(match.group(0)),
        safe,
    )


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
    publish_current_branch: bool = False,
    expected_current_branch: str | None = None,
    expected_current_branch_oid: str | None = None,
    expected_remote_branch_oid: str | None = None,
    feature_publication: FeaturePublicationLease | None = None,
    feature_publication_guard: _FeaturePublicationGuard | None = None,
    after_strict_publication: Callable[[], None] | None = None,
    generated_paths: Mapping[Path, bytes | None] | None = None,
    extra_paths: Iterable[Path] = (),
    land_union_files_to_control: bool = False,
    commit_detached: bool = False,
    raise_state_regression: bool = False,
    raise_git_error: bool = False,
) -> None:
    """Commit the task directory's files and push to the control branch.

    Always-on git analogue of the live notification path. Behaviour:

      - `[git].enabled = false` → suppressed, one stderr line, no crash.
      - Not a git repo → soft no-op, one stderr line, no crash.
      - HEAD is the control branch → `git add` the task dir, and if anything
        is staged, commit with `message` and push to the configured remote.
      - HEAD is a feature branch → commit the task dir on the current branch
        (so the checkout reflects ticket state), then land the same files on
        the control branch via the working-tree-free plumbing path. When
        `publish_current_branch` is true, also push that feature commit after
        the control landing; completion gates use this only once an artifact
        such as an open PR makes the branch itself shared state.
      - Detached HEAD → skip the local commit (it would be orphaned), still
        land on the control branch. A caller may set ``commit_detached`` when
        leaving the selected state dirty would let a later broad sweep publish
        it without the caller's narrower guard.

    Any git operation failure is non-fatal: it is reported to stderr + the
    task's `log.md` and then swallowed, so the local state transition still
    completes (the on-disk markdown is the source of truth; the push just
    didn't land). See the module docstring's failure model.

    `task_path` is the resolved task directory under `coga/tasks/`; only
    files under it are staged, never `git add -A`, so unrelated working-tree
    changes are not swept in.

    `guard` is forwarded to `sync_paths`; status-transition callers pass
    `guard_ticket_state` so a stale checkout cannot overlay its ticket onto a
    newer control tip. ``raise_state_regression`` is the transactional form
    for callers that gate later work on the guard's compare-and-set: a refusal
    is re-raised after the sync layer unwinds any unpushed commit. Ordinary
    human commands retain the non-fatal, locally-visible transition policy;
    rewind is the exception because its caller must suppress the generic state
    sweep after retaining a refused local step move.
    ``raise_git_error`` additionally makes every attempted Git publication
    failure observable to a caller that must not perform a dependent side
    effect without confirmed control state. It also refuses a requested
    strict publication when Git, the checkout, the control branch, or the
    configured remote is unavailable.
    `expected_current_branch` pins an explicitly requested
    feature publication to the branch the caller already verified; switching
    checkouts between verification and sync fails before any commit or push.
    `expected_current_branch_oid` proves no unrelated local commit appeared
    after verification. `expected_remote_branch_oid` leases the remote update,
    refusing a deleted or rewritten branch instead of restoring it.
    `feature_publication` supplies all three values as one strict capability:
    the generated commit is pushed first, by captured OID, and every later
    publication failure is raised so its caller can restore the pre-transition
    files. If the control landing fails after the feature push, a leased
    compensating commit restores the feature branch's prior tree before the
    error escapes. ``generated_paths`` supplies the state writer's armed
    byte snapshot; strict commits overlay only those exact leaves on the leased
    feature tree, so later worktree edits and unchanged attachments cannot be
    swept into the transaction. ``extra_paths`` lets a lifecycle transaction
    include explicitly owned siblings such as the digest spool; callers set
    ``land_union_files_to_control`` when those merge=union leaves must reach
    control in the same durable boundary.
    ``commit_detached`` advances a detached HEAD with a commit containing only
    the selected state paths. If control publication subsequently refuses or
    fails, that generated commit is unwound while its files stay dirty.
    """
    if feature_publication is not None:
        publish_current_branch = True
        expected_current_branch = feature_publication.branch
        expected_current_branch_oid = feature_publication.local_oid
        expected_remote_branch_oid = feature_publication.remote_oid
        if feature_publication.control_ticket_state is not None:
            guard = _assist_control_ticket_guard(
                task_path,
                feature_publication.control_ticket_state,
                expected_task_oid=feature_publication.control_task_oid,
                fallback=guard,
            )
    sync_paths(
        cfg,
        task_path,
        [task_path, *extra_paths],
        message=message,
        guard=guard,
        land_union_files_to_control=land_union_files_to_control,
        commit_detached=commit_detached,
        publish_current_branch=publish_current_branch,
        expected_current_branch=expected_current_branch,
        expected_current_branch_oid=expected_current_branch_oid,
        expected_remote_branch_oid=expected_remote_branch_oid,
        strict_feature_publication=feature_publication is not None,
        strict_push_url=(
            feature_publication.push_url
            if feature_publication is not None
            else None
        ),
        feature_publication_guard=feature_publication_guard,
        after_strict_publication=after_strict_publication,
        generated_paths=generated_paths,
        **(
            {"raise_state_regression": True}
            if raise_state_regression
            else {}
        ),
        **({"raise_git_error": True} if raise_git_error else {}),
    )


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
    OS-state subtree (the same current pathspecs `sync_coga_state` owns, plus a
    former contexts root recorded at the control base, all negated). The
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
        state_pathspecs = _coga_state_pathspecs(root, cfg)
        config_rel = _relative_to_root(root, cfg.repo_root / "coga.toml")
        base_contexts = _contexts_root_from_revision(
            root, cfg, config_rel, base
        )
        if base_contexts is not None:
            base_contexts_rel = _relative_to_root(root, base_contexts)
            if not any(
                _pathspec_covers(spec, base_contexts_rel)
                for spec in state_pathspecs
            ):
                # A feature branch may commit the relocation itself. Its
                # three-dot diff then contains a deletion at the control
                # branch's former contexts root; that is Coga state, not
                # stranded product code.
                state_pathspecs.append(base_contexts_rel)
        excludes = [f":(exclude){spec}" for spec in state_pathspecs]
        # `-z` (NUL-delimited, no path quoting) so a product file with
        # non-ASCII characters is named verbatim in the `mark done` error rather
        # than git-quoted — the same reason `_changed_paths_under` uses it.
        out = _run_git(
            root, "diff", "-z", "--name-only", f"{base}...{head}", "--", ".", *excludes
        )
        return [path for path in out.split("\x00") if path]
    except GitError:
        return []


@dataclass(frozen=True)
class _FeaturePublicationState:
    """Safety result for publishing a generated feature-branch commit."""

    aligned: bool
    may_commit: bool
    detail: str
    remote_oid: str | None


@dataclass(frozen=True)
class _RefreshCommit:
    """Generated refresh paths plus their before/after working-tree bytes."""

    paths: tuple[str, ...]
    originals: dict[str, bytes | None]
    generated: dict[str, bytes | None]
    oid: str


def sync_log(
    cfg: Config,
    *,
    message: str,
    publish_current_branch: bool = False,
    publish_if_remote_aligned: bool = False,
    allow_feature_fast_forward: bool = True,
    expected_feature_branch: str | None = None,
    feature_publication_guard: _FeaturePublicationGuard | None = None,
) -> bool:
    """Commit the repo-global `log.md` alone, and publish when required.

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
      - Feature branch: normally commit the log locally only. It reaches the
        control branch union-safely when the branch's PR merges — never via the
        cross-branch overlay, which replaces the file wholesale and would drop
        lines another branch appended. A successful artifact-gated handoff may
        set `publish_current_branch` so the final session-usage commit also
        reaches the already-open PR branch. An explicit human-step assist uses
        the narrower `publish_if_remote_aligned`: publish the log-only commit
        only from an aligned live configured remote tip. By default, a
        merely-behind branch is fast-forwarded first while its one dirty
        union-log append is preserved; a behind checkout with other dirt is
        left untouched rather than made divergent. A launch that already
        aligned before composing may set `allow_feature_fast_forward=False`:
        if the remote moved after composition, leave the log uncommitted and
        report failure so the caller can refuse to spawn with stale state.
        `expected_feature_branch` additionally pins an assist's pre-session
        and teardown commits to its recorded branch. If the agent changes
        branches, the audit append stays dirty for explicit recovery instead
        of being committed or pushed to the newly checked-out branch. A pinned
        call also requires an exact live remote tip and a branch name distinct
        from the control branch; it never falls back to a local-only generated
        commit. These rules keep an already-published PR branch aligned without
        accidentally publishing unrelated local commits.
      - Detached HEAD: skip (the commit would be orphaned); the line stays
        dirty, reported to stderr.

    Returns whether the log reached a safe terminal state. Most callers retain
    the non-fatal contract and ignore the result; the assist launcher checks it
    so a late remote move stops before the child starts.

    Same non-fatal failure model as `sync_paths` (stderr, never a crash) with
    one deliberate difference: it does **not** `append_log` on failure. That
    would re-dirty the very file it just failed to commit, recreating the
    dangling-line problem instead of closing it.
    """
    strict_assist = expected_feature_branch is not None
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (log sync suppressed): {message}\n")
        return False
    log_file = log_path(cfg)
    if not log_file.exists():
        return True
    try:
        root = _toplevel(log_file)
        if root is None:
            sys.stderr.write(f"[git] not a git repo (log sync skipped): {message}\n")
            return False
        if not _control_branch_present(root, cfg.git_control_branch, cfg.git_remote):
            sys.stderr.write(
                _control_branch_mismatch_message(cfg, root) + f" ({message})\n"
            )
            return False
        log_rel = _relative_worktree_file_to_root(root, log_file)
        branch = _current_branch(root)
        if (
            expected_feature_branch is not None
            and branch != expected_feature_branch
        ):
            sys.stderr.write(
                f"[git] expected feature branch {expected_feature_branch!r}, "
                f"but the checkout is on {branch!r} — log left uncommitted. "
                f"({message})\n"
            )
            return False
        if strict_assist and branch == cfg.git_control_branch:
            sys.stderr.write(
                f"[git] strict assist branch {branch!r} is also the configured "
                "control branch — log left uncommitted. "
                f"({message})\n"
            )
            return False
        # A commit is always local and never touches the remote, so it proceeds
        # even with no remote configured; only the *push* is soft-skipped in
        # that case (calm notice, no raw fatal). Every other push failure stays
        # loud via the `except GitError` below.
        remote_ok = _remote_configured(root, cfg.git_remote)
        if branch == cfg.git_control_branch:
            if _commit_paths(root, [log_rel], message):
                if remote_ok:
                    _push_control_branch(cfg, root)
                else:
                    sys.stderr.write(_no_remote_message(cfg) + f" ({message})\n")
        elif branch == "HEAD":
            sys.stderr.write(
                f"[git] detached HEAD — log append not committed locally. ({message})\n"
            )
            return False
        else:
            publication = _FeaturePublicationState(
                aligned=False,
                may_commit=True,
                detail=f"remote {cfg.git_remote!r} is not configured",
                remote_oid=None,
            )
            assist_push_url = (
                _single_assist_push_url(root, cfg.git_remote)
                if strict_assist
                else None
            )
            if publish_if_remote_aligned and remote_ok and (
                strict_assist or not publish_current_branch
            ):
                publication = _prepare_feature_branch_publication(
                    root,
                    cfg.git_remote,
                    branch,
                    preserve_union_rel=log_rel,
                    fast_forward_if_behind=allow_feature_fast_forward,
                    require_single_push_url=True,
                    push_url=assist_push_url,
                )
            if strict_assist and not publication.aligned:
                sys.stderr.write(
                    f"[git] strict assist branch {branch!r} was not at an exact "
                    f"remote tip ({publication.detail}) — log left uncommitted. "
                    f"({message})\n"
                )
                return False
            if (
                not strict_assist
                and publish_if_remote_aligned
                and not publication.may_commit
            ):
                sys.stderr.write(
                    f"[git] feature branch {branch!r} was not ready for aligned "
                    f"log publication ({publication.detail}) — log left "
                    f"uncommitted. ({message})\n"
                )
                return False
            before = (
                _run_git(root, "rev-parse", "HEAD").strip()
                if publication.aligned
                else None
            )
            if publication.aligned and before != publication.remote_oid:
                sys.stderr.write(
                    f"[git] feature branch {branch!r} moved locally after "
                    f"alignment — log left uncommitted. ({message})\n"
                )
                return False
            if publication.aligned and before is not None:
                captured_log = _working_tree_bytes(root, log_rel)
                committed, generated_oid = _commit_paths_at_expected_head(
                    root,
                    [log_rel],
                    message,
                    branch=branch,
                    expected_oid=before,
                    source_bytes={log_rel: captured_log},
                )
            else:
                committed = _commit_paths(root, [log_rel], message)
                generated_oid = _run_git(root, "rev-parse", "HEAD").strip()
            if publish_current_branch or publication.aligned:
                if not remote_ok:
                    sys.stderr.write(_no_remote_message(cfg) + f" ({message})\n")
                    return False
                push_started = False
                try:
                    if (
                        publication.aligned
                        and publication.remote_oid is not None
                        and feature_publication_guard is not None
                    ):
                        feature_publication_guard(publication.remote_oid)
                    push_started = True
                    result = _push_ref(
                        root,
                        assist_push_url or cfg.git_remote,
                        f"{generated_oid}:refs/heads/{branch}",
                        force_with_lease=(
                            (f"refs/heads/{branch}", publication.remote_oid)
                            if publication.aligned
                            and publication.remote_oid is not None
                            else None
                        ),
                    )
                    if result is not None:
                        raise GitError(
                            f"`git push {cfg.git_remote} {branch}` failed while "
                            f"publishing the session log: {result}"
                        )
                except BaseException as exc:
                    if not publication.aligned:
                        raise
                    if not push_started:
                        if committed and before is not None:
                            _restore_generated_feature_commit(
                                root,
                                branch,
                                before=before,
                                generated_oid=generated_oid,
                                rels=[log_rel],
                            )
                        raise
                    try:
                        published = _remote_contains_generated_commit(
                            root,
                            cfg.git_remote,
                            branch,
                            generated_oid,
                            push_url=assist_push_url,
                        )
                    except GitError as probe_exc:
                        raise UncertainFeaturePublicationError(
                            "could not determine whether the generated assist "
                            f"log reached {branch!r} after "
                            f"{type(exc).__name__}: {probe_exc}; retained the "
                            "generated local commit for reconciliation"
                        ) from exc
                    if published:
                        # A reported Git failure after server acceptance is a
                        # successful publication. Real interrupts still
                        # propagate, but retain the now-durable local commit.
                        if not isinstance(exc, GitError):
                            raise
                    else:
                        # The exact destination proves the generated commit did
                        # not land, so the local CAS can be safely unwound.
                        if committed and before is not None:
                            _restore_generated_feature_commit(
                                root,
                                branch,
                                before=before,
                                generated_oid=generated_oid,
                                rels=[log_rel],
                            )
                        raise
            elif publish_if_remote_aligned and committed:
                target = f"{cfg.git_remote}/{branch}" if remote_ok else cfg.git_remote
                sys.stderr.write(
                    f"[git] feature branch {branch!r} did not match {target!r} "
                    "before the log commit — log committed locally but not "
                    f"published ({publication.detail}). ({message})\n"
                )
        return True
    except GitError as exc:
        sys.stderr.write(f"[git] log sync failed: {exc}. Message was: {message}\n")
        return False


def sync_paths(
    cfg: Config,
    anchor_path: Path,
    paths: Iterable[Path],
    *,
    message: str,
    update_local_control_ref: bool = True,
    land_union_files_to_control: bool = False,
    commit_detached: bool = False,
    guard: _StateGuard | None = None,
    publish_current_branch: bool = False,
    expected_current_branch: str | None = None,
    expected_current_branch_oid: str | None = None,
    expected_remote_branch_oid: str | None = None,
    strict_feature_publication: bool = False,
    strict_push_url: str | None = None,
    feature_publication_guard: _FeaturePublicationGuard | None = None,
    after_strict_publication: Callable[[], None] | None = None,
    generated_paths: Mapping[Path, bytes | None] | None = None,
    raise_state_regression: bool = False,
    raise_git_error: bool = False,
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
    intentionally never merge. `publish_current_branch` is the narrower
    post-artifact path: after committing locally and landing the selected
    state on control, also fast-forward the current feature branch on the
    configured remote. `expected_current_branch` pins that generated
    publication to a branch the caller already verified.
    `expected_current_branch_oid` additionally proves the checkout has not
    acquired another local commit since verification.
    `expected_remote_branch_oid` leases the push to the exact remote tip that
    caller verified, so a deleted or force-reset PR branch cannot be recreated
    from stale local history. `strict_feature_publication` is the assist-only
    transactional form: publish the captured generated commit before landing
    control state, compensate that feature update if the control landing then
    fails, and re-raise every publication failure so the state writer can
    restore its pre-transition files.
    ``commit_detached=True`` commits only these selected paths on detached HEAD
    so a later catch-all sweep cannot republish them without this call's guard.
    A refused or failed control landing unwinds that commit and leaves the
    files dirty.

    `guard` is called with each candidate control-branch base before the
    overlay is built — including the base refetched after a non-fast-forward
    retry — and raises `StateRegressionError` to abort the landing. Status
    transitions pass `guard_ticket_state`: the overlay replaces the ticket
    wholesale on the control tip, so without it a stale checkout can bury a
    newer copy that another checkout already landed. Set
    ``raise_state_regression`` only when a dependent side effect must not run
    after that refusal; ordinary CLI transitions keep the refusal non-fatal.
    ``raise_git_error`` is the stronger transactional publication gate: it
    also propagates transport and repository-shape failures, including a
    configured remote that disappears, so the dependent side effect runs only
    after control was actually verified. Its exact generated snapshot is
    committed with a local ref lease, an unaccepted commit is unwound, and an
    ambiguous control push is probed by exact candidate OID before caller-owned
    files may be restored.
    """
    selected = _dedupe_paths(paths)
    if not selected:
        return

    if not cfg.git_enabled:
        if strict_feature_publication or raise_git_error:
            raise FeaturePublicationError(
                "strict state publication requires git sync"
            )
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return

    try:
        root = _toplevel(anchor_path)
        if root is None:
            if strict_feature_publication or raise_git_error:
                raise FeaturePublicationError(
                    "strict state publication requires a git checkout"
                )
            sys.stderr.write(
                f"[git] not a git repo (sync skipped): {message}\n"
            )
            return

        try:
            control_branch_present = _control_branch_present(
                root, cfg.git_control_branch, cfg.git_remote
            )
        except GitError as exc:
            if strict_feature_publication:
                raise FeaturePublicationError(
                    f"could not verify control branch "
                    f"{cfg.git_control_branch!r}: {exc}"
                ) from exc
            raise
        if not control_branch_present:
            if strict_feature_publication or raise_git_error:
                raise FeaturePublicationError(
                    _control_branch_mismatch_message(cfg, root)
                )
            sys.stderr.write(
                _control_branch_mismatch_message(cfg, root) + f" ({message})\n"
            )
            return

        if raise_git_error and not _remote_configured(root, cfg.git_remote):
            raise GitError(
                f"remote {cfg.git_remote!r} disappeared before strict state "
                "publication"
            )

        rels = [_relative_to_root(root, path) for path in selected]
        generated_rels = (
            {
                _relative_to_root(root, path): data
                for path, data in generated_paths.items()
            }
            if generated_paths is not None
            else None
        )
        # Merge=union files must NOT ride the cross-branch overlay — an overlay
        # replaces a file wholesale on the control tip, dropping lines another
        # branch appended concurrently. Instead they are folded into the local
        # commit and ordinarily reach control through a same-branch push or the
        # feature PR. Cancellation is the exception: its branch may never merge,
        # so the caller asks us to union-land the audit/digest evidence now.
        log_rel = _relative_worktree_file_to_root(root, log_path(cfg))
        local_rels = rels + [log_rel] if log_path(cfg).exists() else rels
        local_rels = list(dict.fromkeys(local_rels))
        if (strict_feature_publication or raise_git_error) and generated_rels is None:
            # Direct internal callers that do not own a FileMutationRollback
            # still get one exact pre-publication sample. Lifecycle commands
            # pass their earlier armed snapshot so peer writes between mutation
            # and sync are not mistaken for generated state.
            generated_rels = _snapshot_worktree_paths(root, local_rels)
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
            commit_detached=commit_detached,
            update_local_control_ref=update_local_control_ref,
            publish_current_branch=publish_current_branch,
            expected_current_branch=expected_current_branch,
            expected_current_branch_oid=expected_current_branch_oid,
            expected_remote_branch_oid=expected_remote_branch_oid,
            strict_feature_publication=strict_feature_publication,
            strict_state_publication=(
                raise_git_error and not strict_feature_publication
            ),
            strict_push_url=strict_push_url,
            feature_publication_guard=feature_publication_guard,
            after_strict_publication=after_strict_publication,
            generated_paths=generated_rels,
        )
    except FeaturePublicationError as exc:
        sys.stderr.write(
            f"[git] feature publication refused: {exc}. Message was: {message}\n"
        )
        if strict_feature_publication or raise_git_error:
            raise
    except StateRegressionError as exc:
        if strict_feature_publication:
            raise FeaturePublicationError(
                f"strict feature publication refused stale state: {exc}"
            ) from exc
        if raise_state_regression:
            raise
        # A refusal is not a failure to reach git — it is git refusing to bury
        # newer state, so it gets its own line and no `sync failed` log entry
        # (the guard already recorded the reason against the task). The local
        # write stands and the checkout is now knowingly behind control;
        # `stale_coga_task_rels` keeps surfacing that divergence in views.
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
    except GitError as exc:
        if strict_feature_publication:
            raise FeaturePublicationError(
                f"strict feature publication failed: {exc}"
            ) from exc
        if raise_git_error:
            raise
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
    """Commit dirty Coga OS state, including configured contexts, from any branch.

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

    Scope is the core `coga/` subtree (`cfg.repo_root`, where `coga.toml` lives)
    plus `cfg.contexts_root` when `[layout] contexts` moves it outside that
    subtree. During a move, tracked deletions from the last tree where the
    former contexts root was active are included too. This is *not* the
    forbidden `git add -A`: product code outside those explicit roots is never
    swept in. Enumeration is a scoped full `git status`, so modifications,
    deletions, renames, and new untracked files are captured.

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

        state_pathspecs = _coga_state_pathspecs(root, cfg)
        changed = _changed_paths_under(root, state_pathspecs)
        changed = list(
            dict.fromkeys(
                [*changed, *_removed_paths_from_previous_contexts_root(root, cfg)]
            )
        )
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
    cfg: Config,
    *,
    message: str = "Refresh coga state from control",
    publish_if_remote_aligned: bool = False,
    expected_feature_branch: str | None = None,
    feature_publication_guard: _FeaturePublicationGuard | None = None,
    require_control_verification: bool = False,
) -> bool:
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
        A proven single-checkout assist may set
        `publish_if_remote_aligned`: the refresh first fast-forwards a merely
        behind clean checkout, then publishes only when its pre-refresh tip
        matched the live feature remote. An ahead/diverged checkout retains
        ordinary local-only refresh behavior, while a behind dirty checkout is
        left untouched rather than turned into a divergence.
        `expected_feature_branch` pins the whole refresh to the branch the
        assist started on. If the agent switched branches, teardown skips
        before fetching, committing, or pushing anything in that checkout.
        A pinned refresh likewise requires an exact live remote tip and never
        creates a local-only refresh commit when that branch disappeared.
        Its control fetch comes from the same single verified push destination
        as the PR branch, which keeps a fork's assist state out of the base
        repository's potentially different control plane.
      - Detached HEAD → skip with a stderr note; the refresh commit would be
        orphaned. Launch runs this against the checkout it was invoked from.

    Returns whether the requested refresh was safe and complete. Failures keep
    the same non-raising model as `sync_paths` (stderr + `coga/log.md`).
    Ordinary launch callers treat a miss as advisory; a pinned assist uses the
    False result to suppress the catch-all sweep and request an explicit retry.
    ``require_control_verification`` is the recurring per-child form: an
    intentionally Git-disabled or genuinely non-Git workspace still succeeds
    locally, but a Git checkout whose control branch or configured remote
    disappeared is unverified and returns False instead of a permissive no-op.
    """
    strict_assist = expected_feature_branch is not None
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (refresh suppressed): {message}\n")
        return not strict_assist
    try:
        root = _toplevel(cfg.repo_root)
        if root is None:
            sys.stderr.write(f"[git] not a git repo (refresh skipped): {message}\n")
            return not strict_assist
        if not _control_branch_present(root, cfg.git_control_branch, cfg.git_remote):
            sys.stderr.write(
                _control_branch_mismatch_message(cfg, root) + f" ({message})\n"
            )
            return not (strict_assist or require_control_verification)
        if not _remote_configured(root, cfg.git_remote):
            sys.stderr.write(_no_remote_message(cfg) + f" ({message})\n")
            return not (strict_assist or require_control_verification)
        branch = _current_branch(root)
        if (
            expected_feature_branch is not None
            and branch != expected_feature_branch
        ):
            sys.stderr.write(
                f"[git] expected feature branch {expected_feature_branch!r}, "
                f"but the checkout is on {branch!r} — coga state refresh "
                f"skipped. ({message})\n"
            )
            return False
        if strict_assist and branch == cfg.git_control_branch:
            sys.stderr.write(
                f"[git] strict assist branch {branch!r} is also the configured "
                "control branch — coga state refresh skipped. "
                f"({message})\n"
            )
            return False
        if branch == "HEAD":
            sys.stderr.write(
                f"[git] detached HEAD — coga state not refreshed. ({message})\n"
            )
            return not (strict_assist or require_control_verification)
        publication = _FeaturePublicationState(
            aligned=False,
            may_commit=True,
            detail="aligned publication was not requested",
            remote_oid=None,
        )
        assist_push_url: str | None = None
        if branch != cfg.git_control_branch and publish_if_remote_aligned:
            assist_push_url = _single_assist_push_url(root, cfg.git_remote)
            publication = _prepare_feature_branch_publication(
                root,
                cfg.git_remote,
                branch,
                preserve_union_rel=_relative_worktree_file_to_root(
                    root,
                    log_path(cfg),
                ),
                require_single_push_url=True,
                push_url=assist_push_url,
            )
            if strict_assist and not publication.aligned:
                sys.stderr.write(
                    f"[git] strict assist branch {branch!r} was not at an exact "
                    f"remote tip ({publication.detail}) — refresh skipped. "
                    f"({message})\n"
                )
                return False
            if not strict_assist and not publication.may_commit:
                sys.stderr.write(
                    f"[git] feature branch {branch!r} was not ready for an "
                    f"aligned control-state refresh ({publication.detail}) — "
                    f"refresh skipped. ({message})\n"
                )
                return False
        control_source = assist_push_url or cfg.git_remote
        tip = _fetch_branch_oid(root, control_source, cfg.git_control_branch)
        if branch == cfg.git_control_branch:
            _run_git(root, "merge", "--ff-only", "--quiet", tip)
            return True
        refresh = _refresh_branch_from_control(
            cfg,
            root,
            tip,
            message,
            expected_head=publication.remote_oid if publication.aligned else None,
            expected_branch=branch if publication.aligned else None,
        )
        if publication.aligned:
            result: str | None = None
            push_started = False
            try:
                if (
                    publication.remote_oid is not None
                    and feature_publication_guard is not None
                ):
                    feature_publication_guard(publication.remote_oid)
                push_started = True
                result = _push_ref(
                    root,
                    assist_push_url or cfg.git_remote,
                    f"{refresh.oid}:refs/heads/{branch}",
                    force_with_lease=(
                        (f"refs/heads/{branch}", publication.remote_oid)
                        if publication.remote_oid is not None
                        else None
                    ),
                )
                if result is not None:
                    raise GitError(
                        f"`git push {cfg.git_remote} {branch}` failed while "
                        f"publishing the assist refresh: {result}"
                    )
            except BaseException as exc:
                if not push_started:
                    if refresh.paths:
                        _restore_generated_refresh(
                            root,
                            publication.remote_oid,
                            refresh,
                            branch=branch,
                        )
                    raise
                try:
                    published = _remote_contains_generated_commit(
                        root,
                        cfg.git_remote,
                        branch,
                        refresh.oid,
                        push_url=assist_push_url,
                    )
                except GitError as probe_exc:
                    raise UncertainFeaturePublicationError(
                        "could not determine whether the generated assist "
                        f"refresh reached {branch!r} after "
                        f"{type(exc).__name__}: {probe_exc}; retained the "
                        "generated local refresh for reconciliation"
                    ) from exc
                if published:
                    if not isinstance(exc, GitError):
                        raise
                else:
                    if refresh.paths:
                        _restore_generated_refresh(
                            root,
                            publication.remote_oid,
                            refresh,
                            branch=branch,
                        )
                    raise
        elif publish_if_remote_aligned:
            sys.stderr.write(
                f"[git] feature branch {branch!r} refreshed locally but was not "
                f"published ({publication.detail}). ({message})\n"
            )
            return False
        return True
    except GitError as exc:
        sys.stderr.write(f"[git] refresh failed: {exc}. Message was: {message}\n")
        if not strict_assist:
            append_log(
                cfg,
                ref_tag_for_path(cfg, cfg.repo_root),
                "git",
                f"refresh failed: {exc}",
            )
        return False


def _refresh_branch_from_control(
    cfg: Config,
    root: Path,
    tip: str,
    message: str,
    *,
    expected_head: str | None = None,
    expected_branch: str | None = None,
) -> _RefreshCommit:
    """Overlay the control tip's newer task paths onto a feature checkout."""
    if expected_head is not None and expected_branch is not None:
        _require_checkout_tip(
            root,
            expected_branch,
            expected_head,
            action="start an assist refresh",
        )
    tasks_rel = _relative_to_root(root, cfg.repo_root / "tasks")
    source_head = expected_head or "HEAD"
    ancestor = _run_git(root, "merge-base", source_head, tip).strip()
    out = _run_git(
        root, "diff", "-z", "--name-only", ancestor, tip, "--", tasks_rel
    )
    candidates = [rel for rel in out.split("\x00") if rel]
    dirty = set(_changed_paths_under(root, [tasks_rel]))
    sampled = {
        rel: _working_tree_bytes(root, rel)
        for rel in candidates
        if rel not in dirty
    }
    updated: list[str] = []
    originals: dict[str, bytes | None] = {}
    generated: dict[str, bytes | None] = {}
    try:
        # The rollback boundary begins before the first worktree write. Track a
        # path only after its guarded write succeeds, so cleanup never guesses
        # that a failed or peer-raced write belongs to this refresh.
        for rel in candidates:
            if rel in dirty:
                sys.stderr.write(
                    f"[git] refresh: leaving {rel} untouched — it has "
                    "uncommitted local changes (the next command's state sweep "
                    "owns them).\n"
                )
                continue
            control = _tree_bytes(root, tip, rel)
            reason = _refresh_regression_reason(cfg, root, rel, control)
            if reason is not None:
                sys.stderr.write(
                    f"[git] refresh: leaving {rel} untouched — {reason}.\n"
                )
                continue
            reason = _refresh_committed_divergence_reason(
                root, rel, control, ancestor, tip
            )
            if reason is not None:
                sys.stderr.write(
                    f"[git] refresh: leaving {rel} untouched — {reason}.\n"
                )
                continue
            if expected_head is not None and expected_branch is not None:
                _require_checkout_tip(
                    root,
                    expected_branch,
                    expected_head,
                    action=f"refresh {rel}",
                )
            if _changed_paths_under(root, [rel]):
                sys.stderr.write(
                    f"[git] refresh: leaving {rel} untouched — it became "
                    "dirty after the refresh scan.\n"
                )
                continue
            prior = sampled[rel]
            _write_worktree_bytes(
                root,
                rel,
                control,
                expected=prior,
                expected_branch=expected_branch,
                expected_oid=expected_head,
            )
            originals[rel] = prior
            generated[rel] = control
            updated.append(rel)

        log_update = _refresh_log_from_control(
            cfg,
            root,
            tip,
            expected_head=expected_head,
            expected_branch=expected_branch,
        )
        if log_update is not None:
            log_rel, log_before, log_after = log_update
            originals[log_rel] = log_before
            generated[log_rel] = log_after
            updated.append(log_rel)

        if expected_head is not None and expected_branch is not None:
            _committed, generated_oid = _commit_paths_at_expected_head(
                root,
                updated,
                message,
                branch=expected_branch,
                expected_oid=expected_head,
                source_bytes=generated,
            )
        elif updated:
            _commit_paths(root, updated, message)
            generated_oid = _run_git(root, "rev-parse", "HEAD").strip()
        else:
            generated_oid = _run_git(root, "rev-parse", "HEAD").strip()
    except UncertainFeaturePublicationError:
        # The local ref may still name a generated commit. Its matching bytes
        # are evidence needed for explicit reconciliation, never rollback input.
        raise
    except BaseException as exc:
        if expected_head is not None and expected_branch is not None:
            _require_checkout_tip(
                root,
                expected_branch,
                expected_head,
                action="restore a failed assist refresh",
            )
            _restore_refresh_worktree(
                root,
                originals=originals,
                generated=generated,
                expected_branch=expected_branch,
                expected_oid=expected_head,
            )
        elif isinstance(exc, GitError):
            _restore_refresh_worktree(
                root,
                originals=originals,
                generated=generated,
            )
        raise
    return _RefreshCommit(
        paths=tuple(updated),
        originals=originals,
        generated=generated,
        oid=generated_oid,
    )


def _restore_generated_refresh(
    root: Path,
    before: str | None,
    refresh: _RefreshCommit,
    *,
    branch: str,
) -> None:
    """Undo one failed generated refresh while preserving prior dirty bytes."""
    if before is None:
        return
    _restore_generated_feature_commit(
        root,
        branch,
        before=before,
        generated_oid=refresh.oid,
        rels=list(refresh.paths),
    )
    _require_checkout_tip(
        root,
        branch,
        before,
        action="restore assist refresh working-tree bytes",
    )
    _restore_refresh_worktree(
        root,
        originals=refresh.originals,
        generated=refresh.generated,
        expected_branch=branch,
        expected_oid=before,
    )


def _restore_refresh_worktree(
    root: Path,
    *,
    originals: dict[str, bytes | None],
    generated: dict[str, bytes | None],
    expected_branch: str | None = None,
    expected_oid: str | None = None,
) -> None:
    """Undo only refresh bytes still attributable to this generated update."""
    union_rels = _union_merge_paths(root, list(originals))
    paths = {rel: root / rel for rel in originals}
    rollback = FileMutationRollback(
        originals={paths[rel]: data for rel, data in originals.items()},
        union_paths=frozenset(paths[rel] for rel in union_rels),
        generated={paths[rel]: generated[rel] for rel in originals},
    )
    if expected_branch is not None and expected_oid is not None:
        _require_checkout_tip(
            root,
            expected_branch,
            expected_oid,
            action="restore assist refresh bytes",
        )
    refused = rollback.restore()
    if refused:
        names = ", ".join(str(path.relative_to(root)) for path in refused)
        raise GitError(
            "refresh cleanup retained concurrent working-tree edits at "
            f"{names}"
        )


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


def _refresh_log_from_control(
    cfg: Config,
    root: Path,
    tip: str,
    *,
    expected_head: str | None = None,
    expected_branch: str | None = None,
) -> tuple[str, bytes | None, bytes] | None:
    """Union-merge the control tip's `log.md` into the working tree.

    Returns ``(rel, before, generated)`` when the merge changed the local copy,
    else ``None``. Direction matters: `current` is the local working copy
    (committed or still dirty), so lines only this checkout has survive while
    the control branch's lines fold in — the same union contract the publish
    paths honor in the opposite direction.
    """
    log_rel = _relative_worktree_file_to_root(root, log_path(cfg))
    control = _tree_bytes(root, tip, log_rel)
    if control is None:
        return None
    local_snapshot = _working_tree_bytes(root, log_rel)
    local = local_snapshot or b""
    ancestor = _run_git(root, "merge-base", "HEAD", tip).strip()
    base = _tree_bytes(root, ancestor, log_rel) or b""
    merged = _merge_union_bytes(current=local, base=base, other=control)
    if merged == local:
        return None
    if expected_head is not None and expected_branch is not None:
        _require_checkout_tip(
            root,
            expected_branch,
            expected_head,
            action=f"refresh {log_rel}",
        )
    _write_worktree_bytes(
        root,
        log_rel,
        merged,
        expected=local_snapshot,
        expected_branch=expected_branch,
        expected_oid=expected_head,
    )
    return log_rel, local_snapshot, merged


def _write_worktree_bytes(
    root: Path,
    rel: str,
    data: bytes | None,
    *,
    expected: bytes | None | object = _ANY_WORKTREE_BYTES,
    expected_branch: str | None = None,
    expected_oid: str | None = None,
) -> None:
    """Write (or remove, for None) one repo-relative file in the working tree."""
    if expected_branch is not None and expected_oid is not None:
        _require_checkout_tip(
            root,
            expected_branch,
            expected_oid,
            action=f"write {rel}",
        )
    path = root / rel
    if expected is not _ANY_WORKTREE_BYTES:
        current = path.read_bytes() if path.is_file() else None
        if current != expected:
            raise GitError(
                f"working-tree path {rel!r} changed before its guarded write"
            )
    if data is None:
        if path.is_file():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _append_missing_union_bytes(
    root: Path,
    rel: str,
    desired: bytes,
    *,
    expected_branch: str | None = None,
    expected_oid: str | None = None,
) -> None:
    """Add desired union lines without replacing concurrent appends."""
    if expected_branch is not None and expected_oid is not None:
        _require_checkout_tip(
            root,
            expected_branch,
            expected_oid,
            action=f"restore union path {rel}",
        )
    path = root / rel
    current = path.read_bytes() if path.is_file() else b""
    pending = Counter(desired.splitlines(keepends=True)) - Counter(
        current.splitlines(keepends=True)
    )
    if not any(pending.values()):
        return
    addition: list[bytes] = []
    for line in desired.splitlines(keepends=True):
        if pending[line]:
            pending[line] -= 1
            addition.append(line)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(b"".join(addition))


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
    commit_detached: bool = False,
    update_local_control_ref: bool = True,
    publish_current_branch: bool = False,
    expected_current_branch: str | None = None,
    expected_current_branch_oid: str | None = None,
    expected_remote_branch_oid: str | None = None,
    strict_feature_publication: bool = False,
    strict_state_publication: bool = False,
    strict_push_url: str | None = None,
    feature_publication_guard: _FeaturePublicationGuard | None = None,
    after_strict_publication: Callable[[], None] | None = None,
    generated_paths: Mapping[str, bytes | None] | None = None,
) -> None:
    """Commit `local_rels` on the current branch and land `overlay_rels` on the
    control branch — the branch-aware core shared by `sync_paths` and
    `sync_coga_state`.

      - HEAD is the control branch → commit `local_rels` and push; the union
        files in `local_rels` ride the push-rebase's union merge.
      - Feature branch → commit `local_rels` locally (so the checkout reflects
        OS state), then land `overlay_rels` on the control branch via the
        working-tree-free overlay. A caller may also explicitly land selected
        merge=union files when their evidence cannot wait for a future PR, and
        may additionally publish that feature commit after the control
        landing.
      - Detached HEAD → normally skip the local commit (it would be orphaned);
        still land `overlay_rels` on the control branch. An explicit
        ``commit_detached`` seals these scoped paths in the detached checkout.

    ``strict_state_publication`` is the recurring lifecycle transaction. It
    captures exact generated bytes, leases control before committing locally,
    unwinds an unaccepted feature/control commit, and probes the exact candidate
    after an ambiguous push failure before allowing caller-owned file rollback.
    """
    control_union_rels = control_union_rels or []
    try:
        branch = _current_branch(root)
    except GitError as exc:
        if strict_feature_publication:
            raise FeaturePublicationError(
                f"could not verify the current feature branch: {exc}"
            ) from exc
        raise
    if expected_current_branch is not None and branch != expected_current_branch:
        error_type = (
            FeaturePublicationError if strict_feature_publication else GitError
        )
        raise error_type(
            f"expected current branch {expected_current_branch!r}, "
            f"but the checkout is on {branch!r}"
        )
    # The local commit never touches the remote, so it proceeds even with no
    # remote configured; only the control-branch *landing/push* is soft-skipped
    # in that case (calm notice, no raw fatal). Every other push failure stays
    # loud via the caller's `except GitError`.
    remote_ok = _remote_configured(root, cfg.git_remote)
    if (
        not remote_ok
        and branch != cfg.git_control_branch
        and guard is not None
        and not strict_feature_publication
        and not strict_state_publication
    ):
        # A missing remote skips the cross-branch landing, not the state guard.
        # A sibling worktree can still have advanced the shared local control
        # branch, so compare against that base before sealing a feature or
        # detached local commit.
        guard(
            _control_base_for_attempt(
                root,
                cfg.git_remote,
                cfg.git_control_branch,
                0,
            )
        )
    if branch == cfg.git_control_branch:
        if strict_feature_publication:
            raise FeaturePublicationError(
                "strict feature publication requires a non-control branch"
            )
        if strict_state_publication:
            _sync_paths_on_control_branch_strict(
                cfg,
                root,
                local_rels,
                message=message,
                guard=guard,
                generated_paths=generated_paths,
                after_strict_publication=after_strict_publication,
            )
            return
        committed = _sync_paths_on_control_branch(
            cfg, root, local_rels, message=message, guard=guard, push=remote_ok
        )
        # Only when something was actually saved: a clean no-op sync pushes
        # nothing even *with* a remote, so announcing a skipped push there would
        # claim a save that never happened.
        if not remote_ok and committed:
            sys.stderr.write(_no_remote_message(cfg) + f" ({message})\n")
        return

    if branch == "HEAD":
        # Detached HEAD normally has no local commit — it would be orphaned.
        # A rewind is different: leaving its successfully published ticket
        # dirty lets a later generic sweep overlay those retained bytes without
        # the rewind's exact-status guard. With a reachable remote, seal only
        # the caller-owned paths in a detached commit and reconcile every
        # attempted control push through the strict landing helper. Without a
        # remote there is no durable destination, so keep the debug state dirty.
        if not remote_ok:
            sys.stderr.write(_no_remote_message(cfg) + f" ({message})\n")
            return
        detached_before: str | None = None
        detached_committed = False
        detached_control_base: str | None = None
        if commit_detached:
            if strict_feature_publication or strict_state_publication:
                raise GitError(
                    "detached scoped commits cannot be combined with strict "
                    "state publication"
                )
            detached_control_base = _control_base_for_attempt(
                root,
                cfg.git_remote,
                cfg.git_control_branch,
                1,
            )
            detached_before = _run_git(root, "rev-parse", "HEAD").strip()
            detached_committed = _commit_paths(root, local_rels, message)
        overlay = set(overlay_rels)
        union_rels = list(
            dict.fromkeys(
                [rel for rel in local_rels if rel not in overlay]
                + control_union_rels
            )
        )
        if strict_state_publication:
            strict_control_tip = _control_base_for_attempt(
                root,
                cfg.git_remote,
                cfg.git_control_branch,
                1,
            )
            if guard is not None:
                guard(strict_control_tip)
            _land_strict_state_on_control(
                cfg,
                root,
                overlay_rels,
                union_rels=union_rels,
                message=message,
                guard=guard,
                update_local_control_ref=update_local_control_ref,
                initial_base=strict_control_tip,
                source_bytes=(
                    {
                        rel: generated_paths[rel]
                        for rel in generated_paths
                        if any(
                            rel == scope or rel.startswith(f"{scope}/")
                            for scope in overlay_rels
                        )
                    }
                    if generated_paths is not None
                    else None
                ),
                cleanup=None,
                after_strict_publication=after_strict_publication,
            )
            return
        if commit_detached:
            assert detached_control_base is not None
            assert detached_before is not None
            generated_oid = _run_git(root, "rev-parse", "HEAD").strip()

            def cleanup_detached_commit() -> None:
                if detached_committed:
                    _restore_unpushed_sync_commit(
                        root,
                        detached_before,
                        local_rels,
                    )

            _land_strict_state_on_control(
                cfg,
                root,
                overlay_rels,
                union_rels=union_rels,
                message=message,
                guard=guard,
                update_local_control_ref=update_local_control_ref,
                initial_base=detached_control_base,
                source_rev=generated_oid,
                cleanup=cleanup_detached_commit,
                after_strict_publication=None,
            )
            return
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
        strict_control_tip: str | None = None
        assist_push_url: str | None = None
        if strict_feature_publication:
            assist_push_url = (
                strict_push_url
                or _single_assist_push_url(root, cfg.git_remote)
            )
        if strict_feature_publication or strict_state_publication:
            try:
                # The feature update happens before the control landing, so
                # capture a fresh control tip before publishing anything to
                # the PR branch. A state guard, when supplied, rejects a
                # stale/terminal or otherwise changed task against that tip.
                strict_control_tip = _control_base_for_attempt(
                    root,
                    cfg.git_remote,
                    cfg.git_control_branch,
                    1,
                    push_url=assist_push_url,
                )
                if guard is not None:
                    guard(strict_control_tip)
            except StateRegressionError as exc:
                if strict_feature_publication:
                    raise FeaturePublicationError(
                        f"control state refused the assist transition: {exc}"
                    ) from exc
                raise
            except GitError as exc:
                if strict_feature_publication:
                    raise FeaturePublicationError(
                        "could not verify control state before assist "
                        f"publication: {exc}"
                    ) from exc
                raise
        try:
            current_oid = _run_git(root, "rev-parse", "HEAD").strip()
        except GitError as exc:
            if strict_feature_publication:
                raise FeaturePublicationError(
                    f"could not verify local {branch!r} tip: {exc}"
                ) from exc
            raise
        if (
            expected_current_branch_oid is not None
            and current_oid != expected_current_branch_oid
        ):
            error_type = (
                FeaturePublicationError if strict_feature_publication else GitError
            )
            raise error_type(
                f"local {branch!r} moved from verified tip "
                f"{expected_current_branch_oid} to {current_oid}"
            )
        before = (
            current_oid
            if guard or strict_feature_publication or strict_state_publication
            else None
        )
        try:
            if strict_feature_publication or strict_state_publication:
                committed, generated_oid = _commit_paths_at_expected_head(
                    root,
                    local_rels,
                    message,
                    branch=branch,
                    expected_oid=current_oid,
                    source_bytes=generated_paths,
                )
            else:
                committed = _commit_paths(root, local_rels, message)
                generated_oid = _run_git(root, "rev-parse", "HEAD").strip()
        except UncertainFeaturePublicationError:
            raise
        except GitError as exc:
            if strict_feature_publication:
                raise FeaturePublicationError(
                    f"could not create the generated {branch!r} state commit: "
                    f"{exc}"
                ) from exc
            raise
    if not remote_ok:
        # The feature-branch commit above already reflects OS state locally; the
        # control-branch landing is the only remote step, so soft-skip it.
        if strict_feature_publication or strict_state_publication:
            if committed and before is not None:
                _restore_generated_feature_commit(
                    root,
                    branch,
                    before=before,
                    generated_oid=generated_oid,
                    rels=local_rels,
                )
            error_type = (
                FeaturePublicationError
                if strict_feature_publication
                else GitError
            )
            raise error_type(f"remote {cfg.git_remote!r} is not configured")
        sys.stderr.write(_no_remote_message(cfg) + f" ({message})\n")
        return
    if strict_feature_publication:
        if not publish_current_branch or expected_remote_branch_oid is None:
            if committed and before is not None:
                _restore_generated_feature_commit(
                    root,
                    branch,
                    before=before,
                    generated_oid=generated_oid,
                    rels=local_rels,
                )
            raise FeaturePublicationError(
                "strict publication requires a branch and exact remote tip"
            )
        push_started = False
        try:
            if feature_publication_guard is not None:
                feature_publication_guard(expected_remote_branch_oid)
            push_started = True
            result = _push_ref(
                root,
                assist_push_url,
                f"{generated_oid}:refs/heads/{branch}",
                force_with_lease=(
                    f"refs/heads/{branch}",
                    expected_remote_branch_oid,
                ),
            )
            if result is not None:
                raise GitError(
                    f"`git push {cfg.git_remote} "
                    f"{generated_oid}:refs/heads/{branch}` failed: {result}"
                )
        except BaseException as exc:
            # A signal handler raises SystemExit asynchronously. If it lands
            # after Git accepted the push but before `_push_ref` returns, this
            # stack has no successful return value even though the PR branch
            # already contains the generated state. Probe the exact push
            # destination before deciding whether local-only cleanup is safe.
            if not push_started:
                if committed and before is not None:
                    _restore_generated_feature_commit(
                        root,
                        branch,
                        before=before,
                        generated_oid=generated_oid,
                        rels=local_rels,
                    )
                if isinstance(exc, GitError):
                    raise FeaturePublicationError(
                        f"could not authorize generated state publication to "
                        f"{branch!r}: {exc}"
                    ) from exc
                raise
            assert assist_push_url is not None
            try:
                remote_after_failure = _remote_branch_oid(
                    root,
                    cfg.git_remote,
                    branch,
                    push_urls=[assist_push_url],
                )
            except GitError as probe_exc:
                raise UncertainFeaturePublicationError(
                    f"could not determine whether generated state reached "
                    f"{branch!r} after {type(exc).__name__}: {probe_exc}; "
                    "retained the generated local state for reconciliation"
                ) from exc
            feature_was_published = (
                remote_after_failure == generated_oid
                or (
                    remote_after_failure is not None
                    and _remote_branch_descends_from(
                        root,
                        assist_push_url,
                        branch,
                        generated_oid,
                    )
                )
            )
            if feature_was_published:
                _raise_strict_control_landing_failure(
                    root,
                    cfg.git_remote,
                    assist_push_url,
                    branch,
                    before=before,
                    generated_oid=generated_oid,
                    local_rels=local_rels,
                    message=message,
                    failure=exc,
                    committed=committed,
                )
            if committed and before is not None:
                try:
                    _restore_generated_feature_commit(
                        root,
                        branch,
                        before=before,
                        generated_oid=generated_oid,
                        rels=local_rels,
                    )
                except GitError as restore_exc:
                    raise FeaturePublicationError(
                        f"could not publish generated state to {branch!r}: "
                        f"{exc}; local generated commit cleanup also refused: "
                        f"{restore_exc}"
                    ) from exc
            if isinstance(exc, GitError):
                raise FeaturePublicationError(
                    f"could not publish generated state to {branch!r}: {exc}"
                ) from exc
            raise
    if strict_state_publication:
        assert strict_control_tip is not None
        assert before is not None

        def cleanup_generated_commit() -> None:
            if committed:
                _restore_generated_feature_commit(
                    root,
                    branch,
                    before=before,
                    generated_oid=generated_oid,
                    rels=local_rels,
                )

        _land_strict_state_on_control(
            cfg,
            root,
            overlay_rels,
            union_rels=control_union_rels,
            message=message,
            guard=guard,
            update_local_control_ref=update_local_control_ref,
            initial_base=strict_control_tip,
            source_rev=generated_oid,
            cleanup=cleanup_generated_commit,
            after_strict_publication=after_strict_publication,
        )
        return
    try:
        _land_paths_on_control_branch(
            cfg,
            root,
            overlay_rels,
            union_rels=control_union_rels,
            message=message,
            guard=guard,
            update_local_control_ref=update_local_control_ref,
            initial_base=strict_control_tip,
            source_rev=generated_oid if strict_feature_publication else None,
            push_url=(
                assist_push_url
                if strict_feature_publication
                else None
            ),
            exact_base_lease=strict_feature_publication,
        )
        if strict_feature_publication and after_strict_publication is not None:
            after_strict_publication()
        if publish_current_branch and not strict_feature_publication:
            result = _push_ref(
                root,
                cfg.git_remote,
                f"{generated_oid}:refs/heads/{branch}",
                force_with_lease=(
                    (f"refs/heads/{branch}", expected_remote_branch_oid)
                    if expected_remote_branch_oid is not None
                    else None
                ),
            )
            if result is not None:
                raise GitError(
                    f"`git push {cfg.git_remote} {branch}` failed while "
                    f"publishing gated task state: {result}"
                )
    except BaseException as exc:
        if strict_feature_publication:
            assert strict_control_tip is not None
            try:
                control_contains_generated = (
                    _control_history_contains_generated_paths(
                        root,
                        cfg.git_remote,
                        cfg.git_control_branch,
                        push_url=assist_push_url,
                        initial_tip=strict_control_tip,
                        generated_oid=generated_oid,
                        rels=overlay_rels,
                    )
                )
            except GitError as probe_exc:
                raise UncertainFeaturePublicationError(
                    "could not determine whether the control branch accepted "
                    f"generated assist state after {type(exc).__name__}: "
                    f"{probe_exc}"
                    "; generated feature state was retained for explicit "
                    "reconciliation"
                ) from exc
            if control_contains_generated:
                # The signal/exception arrived only after both durable halves
                # accepted the same generated paths. Publish that boundary to
                # the caller before propagating so it retains the consistent
                # state instead of restoring local pre-transition bytes.
                if after_strict_publication is not None:
                    after_strict_publication()
                raise
            _raise_strict_control_landing_failure(
                root,
                cfg.git_remote,
                assist_push_url,
                branch,
                before=before,
                generated_oid=generated_oid,
                local_rels=local_rels,
                message=message,
                failure=exc,
                committed=committed,
            )
        if isinstance(exc, StateRegressionError) and before is not None:
            _restore_unpushed_sync_commit(root, before, local_rels)
        raise


def _restore_strict_state_commit(
    root: Path,
    branch: str,
    *,
    before: str,
    generated_oid: str,
    rels: list[str],
    failure: BaseException,
) -> None:
    """Unwind one unaccepted lifecycle commit or make uncertainty explicit."""
    try:
        _restore_generated_feature_commit(
            root,
            branch,
            before=before,
            generated_oid=generated_oid,
            rels=rels,
        )
    except GitError as restore_exc:
        raise UncertainFeaturePublicationError(
            "could not safely unwind the generated lifecycle commit after "
            f"{type(failure).__name__}: {restore_exc}; retained generated "
            "state for explicit reconciliation"
        ) from failure


def _sync_paths_on_control_branch_strict(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    message: str,
    guard: _StateGuard | None,
    generated_paths: Mapping[str, bytes | None] | None,
    after_strict_publication: Callable[[], None] | None,
) -> None:
    """Publish one exact lifecycle commit from the checked-out control branch."""
    control_tip = _control_base_for_attempt(
        root,
        cfg.git_remote,
        cfg.git_control_branch,
        1,
    )
    if guard is not None:
        guard(control_tip)
    current_oid = _run_git(root, "rev-parse", "HEAD").strip()
    if current_oid != control_tip:
        raise GitError(
            f"checked-out control branch moved from verified tip {control_tip} "
            f"to {current_oid} before strict state publication"
        )
    committed, generated_oid = _commit_paths_at_expected_head(
        root,
        rels,
        message,
        branch=cfg.git_control_branch,
        expected_oid=current_oid,
        source_bytes=generated_paths,
    )
    if not committed:
        if after_strict_publication is not None:
            after_strict_publication()
        return

    push_started = False
    try:
        push_started = True
        result = _push_ref(
            root,
            cfg.git_remote,
            f"{generated_oid}:refs/heads/{cfg.git_control_branch}",
            force_with_lease=(
                f"refs/heads/{cfg.git_control_branch}",
                control_tip,
            ),
        )
        if result is not None:
            raise GitError(
                f"`git push {cfg.git_remote} {cfg.git_control_branch}` failed "
                f"during strict state publication: {result}"
            )
    except BaseException as exc:
        if isinstance(exc, UncertainFeaturePublicationError):
            raise
        if push_started:
            try:
                published = _configured_remote_contains_generated_commit(
                    root,
                    cfg.git_remote,
                    cfg.git_control_branch,
                    generated_oid,
                )
            except GitError as probe_exc:
                raise UncertainFeaturePublicationError(
                    "could not determine whether control accepted generated "
                    f"lifecycle state after {type(exc).__name__}: {probe_exc}; "
                    "retained generated state for explicit reconciliation"
                ) from exc
            if published:
                if after_strict_publication is not None:
                    after_strict_publication()
                if isinstance(exc, GitError):
                    return
                raise
        _restore_strict_state_commit(
            root,
            cfg.git_control_branch,
            before=current_oid,
            generated_oid=generated_oid,
            rels=rels,
            failure=exc,
        )
        raise

    if after_strict_publication is not None:
        after_strict_publication()


def _land_strict_state_on_control(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    union_rels: list[str],
    message: str,
    guard: _StateGuard | None,
    update_local_control_ref: bool,
    initial_base: str,
    source_rev: str | None = None,
    source_bytes: Mapping[str, bytes | None] | None = None,
    cleanup: Callable[[], None] | None,
    after_strict_publication: Callable[[], None] | None,
) -> None:
    """Land exact state and reconcile every attempted candidate publication.

    ``candidate_oid`` is armed immediately before a push. Once armed, even a
    later guard regression must probe every effective destination before local
    cleanup: Git may have updated one push URL and failed another, leaving the
    next retry to observe the accepted candidate as concurrent control state.
    """
    candidate_oid: str | None = None

    def capture_candidate(oid: str) -> None:
        nonlocal candidate_oid
        candidate_oid = oid

    try:
        _land_paths_on_control_branch(
            cfg,
            root,
            rels,
            union_rels=union_rels,
            message=message,
            guard=guard,
            update_local_control_ref=update_local_control_ref,
            initial_base=initial_base,
            source_rev=source_rev,
            source_bytes=source_bytes,
            exact_base_lease=True,
            before_push=capture_candidate,
        )
    except BaseException as exc:
        if isinstance(exc, UncertainFeaturePublicationError):
            raise
        if candidate_oid is None:
            if cleanup is not None:
                try:
                    cleanup()
                except GitError as cleanup_exc:
                    raise UncertainFeaturePublicationError(
                        "could not safely unwind generated lifecycle state "
                        f"after {type(exc).__name__}: {cleanup_exc}; retained "
                        "generated state for explicit reconciliation"
                    ) from exc
            raise
        try:
            published = _configured_remote_contains_generated_commit(
                root,
                cfg.git_remote,
                cfg.git_control_branch,
                candidate_oid,
            )
        except GitError as probe_exc:
            raise UncertainFeaturePublicationError(
                "could not determine whether control accepted generated "
                f"lifecycle state after {type(exc).__name__}: {probe_exc}; "
                "retained generated state for explicit reconciliation"
            ) from exc
        if published:
            if after_strict_publication is not None:
                after_strict_publication()
            if isinstance(exc, GitError):
                return
            raise
        if cleanup is not None:
            try:
                cleanup()
            except GitError as cleanup_exc:
                raise UncertainFeaturePublicationError(
                    "could not safely unwind generated lifecycle state after "
                    f"{type(exc).__name__}: {cleanup_exc}; retained generated "
                    "state for explicit reconciliation"
                ) from exc
        raise

    if after_strict_publication is not None:
        after_strict_publication()


def _coga_state_pathspecs(root: Path, cfg: Config) -> list[str]:
    """Git pathspecs covering everything Coga owns as state, relative to `root`.

    Config-derived rather than a fixed list, because `[layout] contexts` can
    move the contexts directory anywhere in the checkout — including *outside*
    the coga root, which is the whole point of the key. In the nested layout
    the single `coga` spec no longer covers a relocated `docs/contexts/`, so
    the contexts path is appended as its own spec; in the root layout the
    literal `contexts` entry is substituted rather than appended, so the sweep
    never scans the vacated default location.

    With `[layout] contexts` unset both branches produce exactly what they
    produced before the key existed: the contexts directory is already covered
    by `coga` (nested) or is literally `contexts` (root layout).
    """
    contexts_rel = _relative_to_root(root, cfg.contexts_root)
    rel = _relative_to_root(root, cfg.repo_root)
    if rel != ".":
        if _pathspec_covers(rel, contexts_rel):
            return [rel]
        return [rel, contexts_rel]
    return [
        contexts_rel if spec == "contexts" else spec
        for spec in _ROOT_LAYOUT_COGA_PATHS
    ]


def _removed_paths_from_previous_contexts_root(
    root: Path, cfg: Config
) -> list[str]:
    """Tracked context paths deleted while `[layout] contexts` moved.

    The current config can name only the destination. In a root-layout repo the
    destination deliberately replaces the old `contexts` sweep path, and when
    one external directory replaces another neither old root is otherwise in
    scope. Find the most recent historical config that named a distinct root,
    then add deletions only for paths that existed in that historical tree and
    still survive in HEAD. This works whether config + content move together or
    the config lands before the old copy is removed, without adopting unrelated
    new files later created in the vacated directory.
    """
    out = _run_git(
        root,
        "--literal-pathspecs",
        "diff",
        "--no-renames",
        "--name-only",
        "--diff-filter=D",
        "-z",
        "HEAD",
        "--",
    )
    deleted = [path for path in out.split("\x00") if path]
    if not deleted:
        # The historical lookup may span many coga.toml revisions. Most sweeps
        # have no deletion at all, so keep that cost off the ordinary path.
        return []
    previous_state = _previous_contexts_root_snapshot(root, cfg)
    if previous_state is None:
        return []
    previous, revision = previous_state
    previous_rel = _relative_to_root(root, previous)
    historical = _tracked_tree_paths(root, revision, previous_rel)
    survivors = historical & _tracked_tree_paths(root, "HEAD", previous_rel)
    if not survivors:
        return []
    return [path for path in deleted if path in survivors]


def _previous_contexts_root_snapshot(
    root: Path, cfg: Config
) -> tuple[Path, str] | None:
    """Former contexts root and the last tree where that root was active.

    If the setting is only in the working tree, HEAD is that snapshot. If the
    setting already landed, walk the contiguous run of config revisions naming
    the current root and use the parent of the transition commit. Reading the
    older config-changing commit directly would miss contexts added between
    that commit and the later relocation.
    """
    config_rel = _relative_to_root(root, cfg.repo_root / "coga.toml")
    try:
        head_root = _contexts_root_from_revision(root, cfg, config_rel, "HEAD")
        if head_root is None:
            return None
        current = cfg.contexts_root.resolve()
        if head_root != current:
            return head_root, "HEAD"
        revisions = _run_git(
            root, "log", "--format=%H", "--", config_rel
        ).splitlines()
    except GitError:
        return None

    boundary: str | None = None
    for revision in revisions:
        historical = _contexts_root_from_revision(root, cfg, config_rel, revision)
        if historical == current:
            boundary = revision
            continue
        break
    if boundary is None:
        return None
    snapshot = f"{boundary}^"
    previous = _contexts_root_from_revision(root, cfg, config_rel, snapshot)
    if previous is None or previous == current:
        return None
    return previous, snapshot


def _contexts_root_from_revision(
    root: Path, cfg: Config, config_rel: str, revision: str
) -> Path | None:
    """Resolve one revision's configured contexts root without requiring it."""
    try:
        data = _tree_bytes(root, revision, config_rel)
    except GitError:
        return None
    if data is None:
        return None
    try:
        shared = tomllib.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None

    layout = shared.get("layout")
    if layout is None or (isinstance(layout, dict) and "contexts" not in layout):
        candidate = cfg.repo_root / "contexts"
    else:
        if not isinstance(layout, dict):
            return None
        value = layout.get("contexts")
        if not isinstance(value, str) or not value.strip():
            return None
        relative = Path(value)
        if relative.is_absolute():
            return None
        candidate_text = relative.as_posix()
        if candidate_text.startswith(":") or any(
            char in candidate_text for char in ("*", "?", "[")
        ):
            return None
        candidate = root / relative

    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        return None
    return resolved


def _tracked_tree_paths(root: Path, revision: str, pathspec: str) -> set[str]:
    """Tracked leaf paths under a literal pathspec in one committed tree."""
    out = _run_git(
        root,
        "--literal-pathspecs",
        "ls-tree",
        "-r",
        "--name-only",
        "-z",
        revision,
        "--",
        pathspec,
    )
    return {path for path in out.split("\x00") if path}


def _pathspec_covers(parent: str, child: str) -> bool:
    """True when git pathspec `parent` already selects everything under `child`."""
    return child == parent or child.startswith(f"{parent}/")


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
    allow_terminal_change: bool = False,
    expected_lifecycle: tuple[str | None, str | None, str | None] | None = None,
) -> None:
    """Refuse to land one ticket over a newer copy already on `base`.

    The per-transition counterpart of `_guard_coga_state_regressions`. The
    catch-all sweep guards whatever it happened to find dirty; a state
    transition knows exactly which ticket it is about to overlay, so it binds
    this to that ticket and hands the result to `sync_paths(guard=...)`. Same
    rules, same refusal: a terminal control-branch status is never replaced, and
    step/status never move backward. Automatic unresolved-resume cleanup is the
    narrow exception: it may set ``allow_terminal_change`` only while also
    pinning ``expected_lifecycle`` to the exact script result it is undoing.

    Pass the ticket file (`TaskRef.ticket_path`), not the task directory — the
    comparison reads ticket frontmatter, and a directory rel matches nothing.
    """
    root = _toplevel(ticket_path)
    if root is None:
        return
    if expected_lifecycle is not None:
        rel = _relative_to_root(root, ticket_path)
        committed_bytes = _tree_bytes(root, base, rel)
        actual = _ticket_lifecycle_state(committed_bytes)
        if actual != expected_lifecycle:
            raise StateRegressionError(
                f"{rel}: expected control lifecycle "
                f"{_lifecycle_state_summary(expected_lifecycle)}, but found "
                f"{_ticket_state_summary(committed_bytes)}"
            )
    _guard_coga_state_regressions(
        cfg,
        root,
        [_relative_to_root(root, ticket_path)],
        base,
        allow_step_rewind=allow_step_rewind,
        allow_terminal_change=allow_terminal_change,
    )


def ticket_state_guard(
    cfg: Config,
    ticket_path: Path,
    *,
    allow_step_rewind: bool = False,
    allow_terminal_change: bool = False,
    expected_lifecycle: tuple[str | None, str | None, str | None] | None = None,
) -> _StateGuard:
    """Bind `guard_ticket_state` to one ticket, ready for `sync_paths(guard=)`.

    Every publisher of ticket state uses this: `mark`'s status transitions,
    `bump`'s step moves, and `unblock`'s resolve-only write. The sync layer
    calls the result once per landing attempt, so the check re-runs against the
    tip refetched after a non-fast-forward retry.

    `allow_step_rewind=True` is for `coga bump --to/--backward` only: it allows
    the deliberate step regression while requiring exact status equality with
    the control copy. See `_ticket_state_regression_reason`.
    ``allow_terminal_change`` is reserved for automatic unresolved-resume
    cleanup and must be paired with the exact pre-cleanup
    ``expected_lifecycle``.
    """

    def guard(base: str) -> None:
        guard_ticket_state(
            cfg,
            ticket_path,
            base,
            allow_step_rewind=allow_step_rewind,
            allow_terminal_change=allow_terminal_change,
            expected_lifecycle=expected_lifecycle,
        )

    return guard


def _assist_control_ticket_guard(
    task_path: Path,
    expected: tuple[str | None, str | None, str | None],
    *,
    expected_task_oid: str | None,
    fallback: _StateGuard | None,
) -> _StateGuard:
    """Require an assist's exact leased control task on every candidate tip."""
    root = _toplevel(task_path)
    if root is None:
        raise FeaturePublicationError(
            "assist control-state verification requires a git checkout"
        )
    ticket_path = _ticket_path_for_task_path(task_path)
    rel = _relative_to_root(root, ticket_path)
    task_rel = _relative_to_root(root, task_path)

    def guard(base: str) -> None:
        actual_task_oid = _tree_entry_oid(root, base, task_rel)
        if (
            expected_task_oid is not None
            and actual_task_oid != expected_task_oid
        ):
            raise StateRegressionError(
                f"{task_rel}: control task changed after the assist lease "
                f"(expected object {expected_task_oid}; "
                f"found {actual_task_oid or 'missing'})"
            )
        actual_bytes = _tree_bytes(root, base, rel)
        actual = _ticket_lifecycle_state(actual_bytes)
        if actual != expected:
            raise StateRegressionError(
                f"{rel}: control ticket changed after the assist lease "
                f"(expected {_lifecycle_state_summary(expected)}; "
                f"found {_ticket_state_summary(actual_bytes)})"
            )
        if fallback is not None:
            fallback(base)

    return guard


def _ticket_path_for_task_path(task_path: Path) -> Path:
    """Resolve a file- or directory-form task path to its ticket markdown."""
    directory_ticket = task_path / "ticket.md"
    return directory_ticket if task_path.is_dir() else task_path


def _ticket_state_summary(data: bytes | None) -> str:
    """Compact lifecycle identity for an exact-ticket mismatch message."""
    if data is None:
        return "a missing ticket"
    try:
        ticket = Ticket.parse(data.decode("utf-8"))
    except (UnicodeDecodeError, TicketError):
        return "an unreadable ticket"
    return (
        f"status={ticket.status!r}, step={ticket.step!r}, "
        f"assignee={ticket.assignee!r}"
    )


def _ticket_lifecycle_state(
    data: bytes | None,
) -> tuple[str | None, str | None, str | None] | None:
    if data is None:
        return None
    try:
        ticket = Ticket.parse(data.decode("utf-8"))
    except (UnicodeDecodeError, TicketError):
        return None
    return ticket.status, ticket.step, ticket.assignee


def _lifecycle_state_summary(
    state: tuple[str | None, str | None, str | None],
) -> str:
    status, step, assignee = state
    return f"status={status!r}, step={step!r}, assignee={assignee!r}"


def _guard_coga_state_regressions(
    cfg: Config,
    root: Path,
    rels: list[str],
    base: str,
    *,
    allow_step_rewind: bool = False,
    allow_terminal_change: bool = False,
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
            allow_terminal_change=allow_terminal_change,
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
    allow_terminal_change: bool = False,
) -> str | None:
    """Why landing `working` over `committed` would lose state, or `None`.

    `allow_step_rewind=True` drops the step-backward rule for the one caller
    whose backward move is the point: a human `coga bump --to/--backward`
    rewind. It also requires exact status equality: a rewind never changes
    status, so any mismatch with the control copy means the checkout is stale,
    not deliberate.
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
        not allow_terminal_change
        and committed.status in TERMINAL_STATUSES
        and working.status != committed.status
    ):
        return (
            f"{rel}: terminal status would change from "
            f"{committed.status!r} to {working.status!r}"
        )

    if allow_step_rewind and committed.status != working.status:
        return (
            f"{rel}: rewind requires matching control and working statuses "
            f"(control {committed.status!r}, working {working.status!r})"
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
    push: bool = True,
) -> bool:
    """Stage explicit pathspecs, commit if anything changed, and push.

    Returns True when a commit was actually created, so the caller can scope the
    no-remote notice to a sync that really saved something.

    `push=False` is the no-remote path: commit locally but perform no remote
    step. The guard still runs — it just resolves its base locally (attempt 0 →
    `refs/heads/<control>`) instead of fetching the remote tip, which would be
    the very fatal we are suppressing. Skipping it outright would be wrong: with
    no remote, a *sibling worktree* can still advance the local control branch
    through the plumbing landing path, so a stale checkout here has newer state
    it could bury. A refusal propagates as `StateRegressionError` before any
    commit is made. The caller emits the calm no-remote notice.
    """
    before: str | None = None
    if guard is not None:
        base = _control_base_for_attempt(
            root, cfg.git_remote, cfg.git_control_branch, 1 if push else 0
        )
        guard(base)
        before = _run_git(root, "rev-parse", "HEAD").strip()
    if not _commit_paths(root, rels, message):
        return False
    if not push:
        return True
    try:
        _push_control_branch(cfg, root, guard=guard)
    except StateRegressionError:
        if before is not None:
            _restore_unpushed_sync_commit(root, before, rels)
        raise
    return True


def _restore_unpushed_sync_commit(root: Path, before: str, rels: list[str]) -> None:
    """Undo a just-created state-sync commit while keeping its files dirty."""
    _run_git(root, "reset", "--soft", before)
    _run_git(root, "reset", before, "--", *rels)


def _raise_strict_control_landing_failure(
    root: Path,
    remote: str,
    push_url: str,
    branch: str,
    *,
    before: str | None,
    generated_oid: str,
    local_rels: list[str],
    message: str,
    failure: BaseException,
    committed: bool,
) -> None:
    """Compensate a strict feature push whose control landing then failed.

    The feature push intentionally happens first: an assist may not announce or
    spawn against lifecycle state that never reached the PR branch. That leaves
    one failure window — control can reject the same transition after the
    feature update. Restore the prior feature *tree* with a fast-forward
    compensating commit, leased to the generated OID, rather than rewriting
    published history. The caller then restores its pre-transition working-tree
    bytes after this helper raises.
    """
    detail = f"control landing failed after feature publication: {failure}"
    if not committed or before is None:
        raise FeaturePublicationError(detail) from failure

    try:
        generated_output = _run_git(
            root,
            "diff",
            "--name-only",
            "-z",
            before,
            generated_oid,
            "--",
            *local_rels,
        )
        generated_rels = [
            rel for rel in generated_output.split("\x00") if rel
        ]
        if not generated_rels:
            raise GitError(
                "generated feature commit has no compensable state paths"
            )
        compensation_oid = ""
        compensated_parent = ""
        for _attempt in range(_MAX_SYNC_ATTEMPTS):
            compensated_parent = _fetch_branch_oid(root, push_url, branch)
            ancestor = _run_git(
                root, "merge-base", generated_oid, compensated_parent
            ).strip()
            if ancestor != generated_oid:
                raise GitError(
                    f"live {remote}/{branch} no longer descends from the "
                    f"generated state commit {generated_oid}"
                )
            tree = _build_feature_compensation_tree(
                root,
                current_tip=compensated_parent,
                before=before,
                generated_oid=generated_oid,
                rels=generated_rels,
            )
            compensation_oid = _run_git(
                root,
                "commit-tree",
                tree,
                "-p",
                compensated_parent,
                "-m",
                f"{message} (compensate failed control landing)",
            ).strip()
            push_failure: BaseException | None = None
            try:
                result = _push_ref(
                    root,
                    push_url,
                    f"{compensation_oid}:refs/heads/{branch}",
                    force_with_lease=(
                        f"refs/heads/{branch}",
                        compensated_parent,
                    ),
                )
            except BaseException as exc:
                push_failure = exc
            else:
                if result is None:
                    break
                if _is_non_fast_forward(result):
                    continue
                push_failure = GitError(
                    f"`git push {remote} "
                    f"{compensation_oid}:refs/heads/{branch}` failed: {result}"
                )

            # A transport failure or signal can arrive after the remote accepts
            # the compensating commit. Probe the sole push destination before
            # deciding whether local generated bytes may be rolled back.
            assert push_failure is not None
            try:
                compensation_landed = _remote_contains_generated_commit(
                    root,
                    remote,
                    branch,
                    compensation_oid,
                    push_url=push_url,
                )
            except BaseException as probe_error:
                raise UncertainFeaturePublicationError(
                    f"{detail}; could not determine whether compensating "
                    f"commit {compensation_oid} reached {remote}/{branch} "
                    f"after {type(push_failure).__name__}: {probe_error}; "
                    "retained the generated local state for explicit "
                    "reconciliation"
                ) from push_failure
            if compensation_landed:
                break
            raise UncertainFeaturePublicationError(
                f"{detail}; compensating commit {compensation_oid} did not "
                f"reach {remote}/{branch} after "
                f"{type(push_failure).__name__}; retained the generated local "
                "state for explicit reconciliation"
            ) from push_failure
        else:
            raise GitError(
                f"could not compensate {remote}/{branch} after "
                f"{_MAX_SYNC_ATTEMPTS} concurrent updates"
            )

        # Incorporate the same freshly fetched descendant locally when the
        # branch still points at either our generated commit or the exact
        # remote parent we compensated. A real fast-forward updates peer paths
        # in the worktree too. Keep those compensated bytes intact: rewriting
        # the pre-merge generated working copy here would hide same-path peer
        # edits that the reverse three-way merge deliberately preserved.
        ref = f"refs/heads/{branch}"
        try:
            local_tip = _run_git(root, "rev-parse", ref).strip()
            checkout_branch = _current_branch(root)
            checkout_tip = _run_git(root, "rev-parse", "HEAD").strip()
        except GitError:
            local_note = (
                f"; local {branch!r} checkout state could not be verified, so "
                "its ref was preserved"
            )
        else:
            if checkout_branch != branch or checkout_tip != local_tip:
                local_note = (
                    f"; checkout moved to {checkout_branch!r} at "
                    f"{checkout_tip}, so local {branch!r} was preserved"
                )
            elif local_tip in {generated_oid, compensated_parent}:
                try:
                    # Recheck immediately before merge: a concurrent checkout
                    # switch must not redirect compensation onto another
                    # branch after the feature ref inspection above.
                    if (
                        _current_branch(root) != branch
                        or _run_git(root, "rev-parse", "HEAD").strip()
                        != local_tip
                    ):
                        raise GitError(
                            "checkout changed before local compensation"
                        )
                    _run_git(
                        root,
                        "merge",
                        "--ff-only",
                        "--quiet",
                        compensation_oid,
                    )
                except GitError:
                    local_note = (
                        f"; local {branch!r} could not safely fast-forward "
                        "without changing another checkout or overwriting "
                        "concurrent working-tree state, so its ref was preserved"
                    )
                else:
                    local_note = ""
            else:
                local_note = (
                    f"; local {branch!r} moved independently to {local_tip}, "
                    "so its ref was preserved"
                )
    except UncertainFeaturePublicationError:
        raise
    except GitError as compensation_error:
        raise FeaturePublicationError(
            f"{detail}; compensating the feature branch also failed: "
            f"{compensation_error}"
        ) from failure

    raise FeaturePublicationError(
        f"{detail}; restored {remote}/{branch} with compensating commit "
        f"{compensation_oid}{local_note}"
    ) from failure


def _build_feature_compensation_tree(
    root: Path,
    *,
    current_tip: str,
    before: str,
    generated_oid: str,
    rels: list[str],
) -> str:
    """Revert generated state atop a live descendant without dropping its work.

    Ordinary paths use a reverse three-way merge: ``generated_oid`` is the
    base, the live descendant is current, and ``before`` is the inverse change
    being applied. A peer edit to the same file is therefore preserved when it
    does not overlap the generated transition, and compensation refuses rather
    than replacing the whole file when it does overlap.
    """
    union_rels = _union_merge_paths(root, rels)
    ordinary_rels = [rel for rel in rels if rel not in union_rels]

    fd, tmp_index = tempfile.mkstemp(prefix="coga-compensation-index-")
    os.close(fd)
    try:
        os.unlink(tmp_index)
        env = {"GIT_INDEX_FILE": tmp_index}
        _run_git(root, "read-tree", current_tip, env=env)
        for rel in ordinary_rels:
            current = _tree_bytes(root, current_tip, rel)
            prior = _tree_bytes(root, before, rel)
            generated = _tree_bytes(root, generated_oid, rel)
            compensated = _inverse_compensated_bytes(
                current=current,
                prior=prior,
                generated=generated,
                rel=rel,
            )
            _update_compensation_index(
                root,
                env,
                rel,
                data=compensated,
                mode=(
                    _tree_entry_mode(root, current_tip, rel)
                    or _tree_entry_mode(root, before, rel)
                    or "100644"
                ),
            )
        for rel in union_rels:
            current = _tree_bytes(root, current_tip, rel)
            prior = _tree_bytes(root, before, rel)
            generated = _tree_bytes(root, generated_oid, rel)
            if current is None or generated is None:
                raise GitError(
                    f"cannot compensate removed merge=union path {rel!r}"
                )
            compensated = _remove_generated_union_lines(
                current=current,
                prior=prior or b"",
                generated=generated,
                rel=rel,
            )
            _update_compensation_index(
                root,
                env,
                rel,
                data=None if prior is None and not compensated else compensated,
                mode=(
                    _tree_entry_mode(root, current_tip, rel)
                    or _tree_entry_mode(root, before, rel)
                    or "100644"
                ),
            )
        return _run_git(root, "write-tree", env=env).strip()
    finally:
        try:
            os.unlink(tmp_index)
        except FileNotFoundError:
            pass


def _inverse_compensated_bytes(
    *,
    current: bytes | None,
    prior: bytes | None,
    generated: bytes | None,
    rel: str,
) -> bytes | None:
    """Apply ``generated -> prior`` to a live descendant's path bytes."""
    if prior == generated:
        return current
    if current == generated:
        return prior
    if prior is None:
        if current is None:
            return None
        raise GitError(
            f"cannot compensate peer edits to generated path {rel!r}"
        )
    if generated is None:
        if current is None:
            return prior
        raise GitError(
            f"cannot compensate peer replacement of deleted path {rel!r}"
        )
    if current is None:
        raise GitError(
            f"cannot compensate peer deletion of generated path {rel!r}"
        )
    return _merge_inverse_bytes(
        current=current,
        generated=generated,
        prior=prior,
        rel=rel,
    )


def _merge_inverse_bytes(
    *,
    current: bytes,
    generated: bytes,
    prior: bytes,
    rel: str,
) -> bytes:
    """Three-way apply the inverse transition, refusing overlapping edits."""
    with tempfile.TemporaryDirectory(prefix="coga-inverse-merge-") as tmp:
        tmpdir = Path(tmp)
        current_path = tmpdir / "current"
        generated_path = tmpdir / "generated"
        prior_path = tmpdir / "prior"
        current_path.write_bytes(current)
        generated_path.write_bytes(generated)
        prior_path.write_bytes(prior)
        try:
            result = subprocess.run(
                [
                    "git",
                    "merge-file",
                    str(current_path),
                    str(generated_path),
                    str(prior_path),
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
                f"cannot compensate overlapping peer edits to {rel!r}"
            )
        return current_path.read_bytes()


def _tree_entry_mode(root: Path, rev: str, rel: str) -> str | None:
    output = _run_git(root, "ls-tree", "-z", rev, "--", rel)
    for entry in output.split("\x00"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        if path == rel:
            mode, _kind, _oid = metadata.split(" ", 2)
            return mode
    return None


def _tree_entry_oid(root: Path, rev: str, rel: str) -> str | None:
    """Return the exact blob/tree object named by ``rel`` at ``rev``."""
    output = _run_git(root, "ls-tree", "-z", rev, "--", rel)
    for entry in output.split("\x00"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        if path == rel:
            _mode, _kind, oid = metadata.split(" ", 2)
            return oid
    return None


def _update_compensation_index(
    root: Path,
    env: dict[str, str],
    rel: str,
    *,
    data: bytes | None,
    mode: str,
) -> None:
    _run_git(
        root,
        "rm",
        "-f",
        "--cached",
        "--ignore-unmatch",
        "--",
        rel,
        env=env,
    )
    if data is None:
        return
    blob = _hash_blob(root, data)
    _run_git(
        root,
        "update-index",
        "--add",
        "--cacheinfo",
        mode,
        blob,
        rel,
        env=env,
    )


def _remove_generated_union_lines(
    *,
    current: bytes,
    prior: bytes,
    generated: bytes,
    rel: str,
) -> bytes:
    """Remove only this transition's append-only union delta."""
    prior_lines = prior.splitlines(keepends=True)
    generated_lines = generated.splitlines(keepends=True)
    removed_by_generation = Counter(prior_lines) - Counter(generated_lines)
    if removed_by_generation:
        raise GitError(
            f"cannot compensate non-append change to merge=union path {rel!r}"
        )
    pending = Counter(generated_lines) - Counter(prior_lines)
    out: list[bytes] = []
    for line in current.splitlines(keepends=True):
        if pending[line]:
            pending[line] -= 1
        else:
            out.append(line)
    if any(pending.values()):
        raise GitError(
            f"live merge=union path {rel!r} no longer contains the generated "
            "append being compensated"
        )
    return b"".join(out)


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
    fetched_tip = _fetch_branch_oid(root, remote, branch)
    if guard is not None:
        guard(fetched_tip)
    orig = _run_git(root, "rev-parse", "HEAD").strip()
    stashed = _stash_if_dirty(root)

    rebase = subprocess.run(
        ["git", "-C", str(root), "rebase", fetched_tip],
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


def _commit_paths_at_expected_head(
    root: Path,
    rels: list[str],
    message: str,
    *,
    branch: str,
    expected_oid: str,
    source_bytes: Mapping[str, bytes | None] | None = None,
) -> tuple[bool, str]:
    """Create one generated commit only atop ``expected_oid``.

    Assist publishers verify a local tip before deriving lifecycle or audit
    state. An ordinary ``git commit`` would re-read ``HEAD`` internally and can
    silently parent the generated commit on a concurrent local commit. Build
    the exact selected-path tree in a temporary index, then move the branch
    with ``update-ref <new> <expected>`` so that parent selection and ref
    publication form one compare-and-swap.

    The real index is updated only after the ref CAS succeeds, and only for the
    selected paths, preserving unrelated staged work just like
    :func:`_commit_paths`.
    """
    ref = f"refs/heads/{branch}"
    tree = _build_overlay_tree(
        root,
        expected_oid,
        rels,
        source_bytes=source_bytes,
    )
    finalized_rels = list(source_bytes) if source_bytes is not None else rels
    prior_tree = _run_git(root, "rev-parse", f"{expected_oid}^{{tree}}").strip()
    if tree == prior_tree:
        # A no-op still verifies that the branch did not move while the tree was
        # derived. ``update-ref old old`` acquires the ref lock and performs the
        # same expected-value check without creating a commit.
        try:
            _run_git(root, "update-ref", ref, expected_oid, expected_oid)
        except GitError as exc:
            raise GitError(
                f"local {branch!r} moved while generated state was being built"
            ) from exc
        _require_checkout_tip(
            root,
            branch,
            expected_oid,
            action="finalize a no-op generated state commit",
        )
        return False, expected_oid

    generated_oid = _run_git(
        root,
        "commit-tree",
        tree,
        "-p",
        expected_oid,
        "-m",
        message,
    ).strip()
    try:
        _run_git(root, "update-ref", ref, generated_oid, expected_oid)
    except BaseException as exc:
        # A signal can arrive after `update-ref` performed the CAS but before
        # its subprocess result reached Python. Undo only our exact ref update;
        # never strand an unpushed generated commit or move over a follower.
        _run_git_quiet(
            root,
            "update-ref",
            ref,
            expected_oid,
            generated_oid,
        )
        try:
            live_ref = _run_git(root, "rev-parse", ref).strip()
        except GitError as probe_exc:
            raise UncertainFeaturePublicationError(
                f"could not verify cleanup of interrupted local {branch!r} "
                f"commit {generated_oid}: {probe_exc}"
            ) from exc
        if live_ref == generated_oid:
            raise UncertainFeaturePublicationError(
                f"interrupted local {branch!r} commit {generated_oid} could "
                "not be rolled back; generated bytes must be retained"
            ) from exc
        if isinstance(exc, GitError):
            raise GitError(
                f"local {branch!r} moved from verified tip {expected_oid} "
                "while generated state was being committed"
            ) from exc
        raise

    try:
        _require_checkout_tip(
            root,
            branch,
            generated_oid,
            action="finalize a generated state commit",
        )
        if finalized_rels:
            _run_git(root, "reset", generated_oid, "--", *finalized_rels)
    except BaseException as exc:
        # Best-effort ref rollback is itself compare-and-swap guarded: never
        # move over a concurrent commit that followed our generated one.
        _run_git_quiet(
            root,
            "update-ref",
            ref,
            expected_oid,
            generated_oid,
        )
        try:
            live_ref = _run_git(root, "rev-parse", ref).strip()
        except GitError as probe_exc:
            raise UncertainFeaturePublicationError(
                f"could not verify cleanup after finalizing local {branch!r} "
                f"commit {generated_oid}: {probe_exc}"
            ) from exc
        if live_ref == generated_oid:
            raise UncertainFeaturePublicationError(
                f"local {branch!r} retained interrupted generated commit "
                f"{generated_oid}; generated bytes must be retained"
            ) from exc
        try:
            checkout_branch = _current_branch(root)
            checkout_oid = _run_git(root, "rev-parse", "HEAD").strip()
        except GitError:
            checkout_branch = ""
            checkout_oid = ""
        if (
            live_ref == expected_oid
            and checkout_branch == branch
            and checkout_oid == expected_oid
            and finalized_rels
        ):
            _run_git_quiet(
                root,
                "reset",
                expected_oid,
                "--",
                *finalized_rels,
            )
        if isinstance(exc, GitError):
            raise GitError(
                f"could not finalize generated state on local {branch!r}: {exc}"
            ) from exc
        raise
    return True, generated_oid


def _restore_generated_feature_commit(
    root: Path,
    branch: str,
    *,
    before: str,
    generated_oid: str,
    rels: list[str],
) -> None:
    """Undo one unpushed generated commit without moving over newer work."""
    ref = f"refs/heads/{branch}"
    _require_checkout_tip(
        root,
        branch,
        generated_oid,
        action="restore a generated feature commit",
    )
    try:
        _run_git(root, "update-ref", ref, before, generated_oid)
    except GitError as exc:
        raise GitError(
            f"local {branch!r} moved after generated commit {generated_oid}; "
            "refusing to reset over the newer commit"
        ) from exc
    _require_checkout_tip(
        root,
        branch,
        before,
        action="reset generated feature paths",
    )
    _run_git(root, "reset", before, "--", *rels)


def _require_checkout_tip(
    root: Path,
    branch: str,
    expected_oid: str,
    *,
    action: str,
) -> None:
    """Fail if a worktree-changing operation was redirected after sampling."""
    current_branch = _current_branch(root)
    current_oid = _run_git(root, "rev-parse", "HEAD").strip()
    if current_branch != branch or current_oid != expected_oid:
        raise GitError(
            f"cannot {action}: expected checkout {branch!r} at "
            f"{expected_oid}, found {current_branch!r} at {current_oid}"
        )


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
    initial_base: str | None = None,
    source_rev: str | None = None,
    source_bytes: Mapping[str, bytes | None] | None = None,
    push_url: str | None = None,
    exact_base_lease: bool = False,
    before_push: Callable[[str], None] | None = None,
) -> None:
    """Land selected pathspecs on the control branch from any branch.

    ``source_rev`` pins the overlay to an already-created generated commit;
    ``source_bytes`` is the detached-checkout equivalent. They are mutually
    exclusive. ``before_push`` exposes the exact candidate commit to strict
    callers so they can reconcile a lost push acknowledgement.
    Ordinary callers overlay current working-tree bytes; strict assist
    publication uses the captured commit so a concurrent worktree edit cannot
    make control receive different state than the PR branch. When
    ``exact_base_lease`` is set, each candidate control push is leased to the
    exact base just guarded; a deletion or force-rewind loses that attempt
    instead of letting the stale candidate recreate the ref.
    """
    remote = cfg.git_remote
    branch = cfg.git_control_branch
    push_destination = push_url or remote
    union_rels = union_rels or []
    if source_rev is not None and source_bytes is not None:
        raise GitError("control landing cannot use both source_rev and source_bytes")

    for attempt in range(_MAX_SYNC_ATTEMPTS):
        base = (
            initial_base
            if attempt == 0 and initial_base is not None
            else _control_base_for_attempt(
                root,
                remote,
                branch,
                attempt,
                push_url=push_url,
            )
        )
        if guard is not None:
            guard(base)

        tree = _build_overlay_tree(
            root,
            base,
            rels,
            union_rels=union_rels,
            source_rev=source_rev,
            source_bytes=source_bytes,
        )
        if tree == _run_git(root, "rev-parse", f"{base}^{{tree}}").strip():
            if guard is None:
                return
            # A guarded no-op against a stale local control ref is not a
            # successful publication. Lease an identity push to the exact base:
            # if live control moved, the rejection drives the normal
            # refetch/re-guard retry without creating a contentless commit.
            result = _push_ref(
                root,
                push_destination,
                f"{base}:refs/heads/{branch}",
                force_with_lease=(f"refs/heads/{branch}", base),
            )
            if result is None:
                if update_local_control_ref:
                    _try_update_local_ref(root, branch, base)
                return
            if not _is_non_fast_forward(result):
                raise GitError(
                    f"`git push {remote} {base}:refs/heads/{branch}` failed: "
                    f"{result}"
                )
            continue

        new = _run_git(root, "commit-tree", tree, "-p", base, "-m", message).strip()
        if before_push is not None:
            before_push(new)
        if exact_base_lease:
            result = _push_ref(
                root,
                push_destination,
                f"{new}:refs/heads/{branch}",
                force_with_lease=(f"refs/heads/{branch}", base),
            )
        else:
            result = _push_ref(
                root,
                push_destination,
                f"{new}:refs/heads/{branch}",
            )
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


def _control_history_contains_generated_paths(
    root: Path,
    remote: str,
    branch: str,
    *,
    push_url: str | None = None,
    initial_tip: str,
    generated_oid: str,
    rels: list[str],
) -> bool:
    """Whether control durably absorbed one strict generated path snapshot.

    A signal can arrive after the control push succeeds but before the plumbing
    helper returns. Inspect the freshly fetched control history, not only its
    current tree: a concurrent descendant may already have edited the task
    again while still preserving the publication commit in history.
    """
    current_tip = _control_base_for_attempt(
        root,
        remote,
        branch,
        1,
        push_url=push_url,
    )
    generated = {
        rel: _tree_entry_oid(root, generated_oid, rel)
        for rel in rels
    }
    if not generated:
        return True
    history = _run_git(
        root,
        "rev-list",
        f"{initial_tip}..{current_tip}",
    ).splitlines()
    candidates = list(dict.fromkeys([current_tip, *history]))
    return any(
        all(
            _tree_entry_oid(root, commit, rel) == expected_oid
            for rel, expected_oid in generated.items()
        )
        for commit in candidates
    )


def _control_base_for_attempt(
    root: Path,
    remote: str,
    branch: str,
    attempt: int,
    *,
    push_url: str | None = None,
) -> str:
    if attempt == 0:
        local = _local_control_base(root, remote, branch)
        if local is not None:
            return local
    source = push_url or _remote_push_urls(root, remote)[0]
    return _fetch_branch_oid(root, source, branch)


def _local_control_base(root: Path, remote: str, branch: str) -> str | None:
    for ref in (f"refs/heads/{branch}", f"refs/remotes/{remote}/{branch}"):
        if _git_ref_present(root, ref):
            return _run_git(root, "rev-parse", ref).strip()
    return None


def _build_overlay_tree(
    root: Path,
    base: str,
    rels: list[str],
    *,
    union_rels: list[str] | None = None,
    source_rev: str | None = None,
    source_bytes: Mapping[str, bytes | None] | None = None,
) -> str:
    """Build a tree = `base`'s tree with selected pathspecs overlaid.

    Runs entirely against a throwaway temporary index (`GIT_INDEX_FILE`), so
    neither the real index nor the working tree is disturbed. Seeds the temp
    index from `base`, drops stale content for every selected path, re-adds the
    current working-tree content for paths that still exist (or the exact
    ``source_rev`` content when supplied), union-merges any detached-head
    `merge=union` files, and writes the resulting tree object.
    """
    union_rels = union_rels or []
    fd, tmp_index = tempfile.mkstemp(prefix="coga-git-index-")
    os.close(fd)
    try:
        os.unlink(tmp_index)  # read-tree wants to create it fresh
        env = {"GIT_INDEX_FILE": tmp_index}
        _run_git(root, "read-tree", base, env=env)
        if source_bytes is not None:
            _overlay_paths_from_bytes(root, env, base, source_bytes)
        elif source_rev is None:
            _overlay_paths(root, env, rels)
        else:
            _overlay_paths_from_revision(root, env, source_rev, rels)
        _overlay_union_paths(
            root,
            env,
            base,
            union_rels,
            source_rev=source_rev,
        )
        return _run_git(root, "write-tree", env=env).strip()
    finally:
        try:
            os.unlink(tmp_index)
        except FileNotFoundError:
            pass


def _overlay_paths_from_bytes(
    root: Path,
    env: dict[str, str],
    base: str,
    paths: Mapping[str, bytes | None],
) -> None:
    """Replace exact temp-index leaves with one captured byte snapshot."""
    for rel, data in paths.items():
        _run_git(
            root,
            "rm",
            "-f",
            "--cached",
            "--ignore-unmatch",
            "--",
            rel,
            env=env,
        )
        if data is None:
            continue
        blob = _hash_blob(root, data)
        mode = _tree_entry_mode(root, base, rel) or "100644"
        _run_git(
            root,
            "update-index",
            "--add",
            "--cacheinfo",
            mode,
            blob,
            rel,
            env=env,
        )


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


def _overlay_paths_from_revision(
    root: Path,
    env: dict[str, str],
    source_rev: str,
    rels: list[str],
) -> None:
    """Replace selected temp-index paths with their exact ``source_rev`` tree."""
    for rel in rels:
        _run_git(
            root,
            "rm",
            "-rf",
            "--cached",
            "--ignore-unmatch",
            "--",
            rel,
            env=env,
        )
    output = _run_git(
        root,
        "ls-tree",
        "-r",
        "-z",
        source_rev,
        "--",
        *rels,
    )
    for entry in output.split("\x00"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        mode, _kind, oid = metadata.split(" ", 2)
        _run_git(
            root,
            "update-index",
            "--add",
            "--cacheinfo",
            mode,
            oid,
            path,
            env=env,
        )


def _overlay_union_paths(
    root: Path,
    env: dict[str, str],
    base: str,
    rels: list[str],
    *,
    source_rev: str | None = None,
) -> None:
    if not rels:
        return
    source = source_rev or "HEAD"
    ancestor = _run_git(root, "merge-base", source, base).strip()
    for rel in rels:
        merged = _merge_union_path(
            root,
            current_rev=base,
            base_rev=ancestor,
            rel=rel,
            other_rev=source_rev,
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
    root: Path,
    *,
    current_rev: str,
    base_rev: str,
    rel: str,
    other_rev: str | None = None,
) -> bytes:
    """Three-way union-merge a working-tree file into `current_rev`.

    This is the temp-index equivalent of the `merge=union` driver used when a
    local branch commit later merges through Git. It is only used for detached
    checkouts, where there is no durable local branch commit for `log.md`
    / `spool.md` appends to ride.
    """
    working = (
        _tree_bytes(root, other_rev, rel)
        if other_rev is not None
        else _working_tree_bytes(root, rel)
    )
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


def _regular_worktree_mode(root: Path, rel: str) -> str | None:
    """Return a Git regular-file mode without following worktree symlinks."""
    path = Path(rel)
    if not path.is_absolute():
        path = root / path
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(mode):
        return None
    return "100755" if mode & 0o111 else "100644"


def _snapshot_worktree_paths(
    root: Path,
    rels: Iterable[str],
) -> dict[str, bytes | None]:
    """Capture exact file leaves beneath selected worktree pathspecs."""
    captured: dict[str, bytes | None] = {}
    for rel in rels:
        path = root / rel
        if path.is_file():
            captured[rel] = path.read_bytes()
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    captured[str(child.relative_to(root))] = child.read_bytes()
            continue
        captured[rel] = None
    return captured


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


def _push_ref(
    root: Path,
    remote: str,
    refspec: str,
    *,
    force_with_lease: tuple[str, str] | None = None,
) -> str | None:
    """Push `refspec` to `remote`. Return None on success, else stderr+stdout.

    Unlike `_run_git`, a non-zero exit is returned (not raised) so the caller
    can distinguish a recoverable non-fast-forward from a hard failure. An
    exact-tip lease is additionally constrained to a source that descends from
    the expected OID; the lease may authorize the race-safe update, never a
    history rewrite.
    """
    try:
        command = ["git", "-C", str(root), "push"]
        if force_with_lease is not None:
            ref, expected_oid = force_with_lease
            source = refspec.split(":", 1)[0]
            source_oid = _run_git(root, "rev-parse", source).strip()
            merge_base = _run_git(
                root, "merge-base", expected_oid, source_oid
            ).strip()
            if merge_base != expected_oid:
                return (
                    "refusing exact-tip leased push: source "
                    f"{source_oid} does not descend from expected remote "
                    f"tip {expected_oid}"
                )
            command.append(f"--force-with-lease={ref}:{expected_oid}")
        command.extend([remote, refspec])
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, **_noninteractive_git_env()},
        )
    except FileNotFoundError as exc:
        raise GitError("`git` not found on PATH") from exc
    if result.returncode == 0:
        return None
    return _redact_git_command_text(
        (result.stderr + result.stdout).strip(),
        (remote, refspec),
    )


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
        safe_args = [redacted_git_source(arg) for arg in args]
        stderr = _redact_git_command_text(result.stderr, args)
        stdout = _redact_git_command_text(result.stdout, args)
        raise GitError(
            f"`git {' '.join(safe_args)}` failed (exit {result.returncode}): "
            f"{summarize_git_failure(stderr) or summarize_git_failure(stdout)}"
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


def _remote_configured(root: Path, remote: str) -> bool:
    """True when `<remote>` has a URL (`git remote get-url` exits 0).

    The one push failure that is cleanly, positively knowable *before* the push:
    a repo freshly `git init`ed and `coga init`ed has no `origin` yet, so every
    sync would otherwise push straight into a raw two-paragraph git fatal. The
    sync helpers soft-skip on this with a short notice instead. Every *other*
    push failure — a configured remote that is offline, misauthed, protected, or
    simply lacks the branch — is not detectable here and stays a loud `GitError`,
    per this module's fail-loud model.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", remote],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _remote_push_urls(root: Path, remote: str) -> list[str]:
    """Return every destination affected by ``git push <remote>``."""
    output = _run_git(
        root,
        "remote",
        "get-url",
        "--push",
        "--all",
        remote,
    )
    urls = [line.strip() for line in output.splitlines() if line.strip()]
    if not urls:
        raise GitError(f"remote {remote!r} has no effective push URL")
    return urls


def _single_assist_push_url(
    root: Path,
    remote: str,
    *,
    push_urls: list[str] | None = None,
) -> str:
    """Return the sole assist destination; reject Git's non-atomic multi-push."""
    urls = push_urls or _remote_push_urls(root, remote)
    if len(urls) != 1:
        raise FeaturePublicationError(
            f"assist publication requires exactly one effective push URL for "
            f"remote {remote!r}; found {len(urls)}. Git can partially update a "
            "multi-push remote, so it cannot provide the assist's exact-tip "
            "transaction."
        )
    return urls[0]


def _remote_branch_oid(
    root: Path,
    remote: str,
    branch: str,
    *,
    push_urls: list[str] | None = None,
) -> str | None:
    """Return one OID shared by every effective push destination.

    Git reads a remote's fetch URL for ``ls-remote <name>`` but writes its
    ``pushurl`` values for ``push <name>``. Publication leases must inspect the
    destinations they actually update. Multiple push URLs are supported only
    while the named branch has the same presence and OID on all of them.
    """
    observed: list[str | None] = []
    for push_url in push_urls or _remote_push_urls(root, remote):
        output = _run_git(
            root,
            "ls-remote",
            "--heads",
            push_url,
            f"refs/heads/{branch}",
        )
        line = next((line for line in output.splitlines() if line.strip()), "")
        observed.append(line.split(maxsplit=1)[0] if line else None)
    if len(set(observed)) != 1:
        raise GitError(
            f"effective push destinations for {remote!r}/{branch} disagree "
            "about the branch tip"
        )
    return observed[0]


def _fetch_branch_oid(root: Path, source: str, branch: str) -> str:
    """Fetch one branch into a private ref and return its exact object ID.

    ``FETCH_HEAD`` is shared by every fetch in a checkout. Coga deliberately
    permits concurrent local processes, so reading it in a later subprocess
    can consume an unrelated fetch result. A UUID-scoped ref makes the fetch
    result command-owned; ``--no-write-fetch-head`` also leaves the shared
    pseudo-ref untouched.
    """
    fetched_ref = f"refs/coga/fetch/{uuid4().hex}"
    try:
        _run_git(
            root,
            "fetch",
            "--no-write-fetch-head",
            source,
            f"refs/heads/{branch}:{fetched_ref}",
        )
        return _run_git(root, "rev-parse", fetched_ref).strip()
    finally:
        _run_git_quiet(root, "update-ref", "-d", fetched_ref)


def _remote_branch_descends_from(
    root: Path,
    push_url: str,
    branch: str,
    ancestor: str,
) -> bool:
    """Whether the live push destination contains ``ancestor`` in its history."""
    fetched_tip = _fetch_branch_oid(root, push_url, branch)
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                ancestor,
                fetched_tip,
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, **_noninteractive_git_env()},
        )
    except FileNotFoundError as exc:
        raise GitError("`git` not found on PATH") from exc
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise GitError(
        "`git merge-base --is-ancestor` failed "
        f"(exit {result.returncode}): "
        f"{result.stderr.strip() or result.stdout.strip()}"
    )


def _remote_contains_generated_commit(
    root: Path,
    remote: str,
    branch: str,
    generated_oid: str,
    *,
    push_url: str | None = None,
) -> bool:
    """Whether the sole assist push destination accepted a generated commit."""
    push_url = push_url or _single_assist_push_url(root, remote)
    remote_oid = _remote_branch_oid(
        root,
        remote,
        branch,
        push_urls=[push_url],
    )
    return bool(
        remote_oid == generated_oid
        or (
            remote_oid is not None
            and _remote_branch_descends_from(
                root,
                push_url,
                branch,
                generated_oid,
            )
        )
    )


def _configured_remote_contains_generated_commit(
    root: Path,
    remote: str,
    branch: str,
    generated_oid: str,
) -> bool:
    """Verify one generated commit across every configured push destination."""
    push_urls = _remote_push_urls(root, remote)
    remote_oid = _remote_branch_oid(
        root,
        remote,
        branch,
        push_urls=push_urls,
    )
    return bool(
        remote_oid == generated_oid
        or (
            remote_oid is not None
            and _remote_branch_descends_from(
                root,
                push_urls[0],
                branch,
                generated_oid,
            )
        )
    )


def _prepare_feature_branch_publication(
    root: Path,
    remote: str,
    branch: str,
    *,
    preserve_union_rel: str | None = None,
    fast_forward_if_behind: bool = True,
    require_single_push_url: bool = False,
    push_url: str | None = None,
    permitted_dirty_bytes: Mapping[str, bytes | None] | None = None,
) -> _FeaturePublicationState:
    """Align a merely-behind feature checkout before a generated commit.

    Exact alignment is immediately publishable. By default, a local tip that
    is ahead or diverged remains eligible for an ordinary local-only generated
    commit, but is never pushed. A merely-behind checkout is fast-forwarded
    first so Coga does not turn a recoverable state into a divergence.
    Fast-forwarding needs a clean checkout, except that `sync_log` may name its
    one dirty union path; that append is three-way unioned over the fetched tip
    and restored after the fast-forward.

    `may_commit=False` means the branch is behind but cannot be safely
    fast-forwarded, or the caller explicitly required the exact
    post-composition tip and found any mismatch. Callers must skip their
    generated commit in that case.
    """
    push_urls = [push_url] if push_url is not None else _remote_push_urls(root, remote)
    if require_single_push_url:
        _single_assist_push_url(root, remote, push_urls=push_urls)
    remote_tip = _remote_branch_oid(
        root,
        remote,
        branch,
        push_urls=push_urls,
    )
    if remote_tip is None:
        return _FeaturePublicationState(
            aligned=False,
            may_commit=fast_forward_if_behind,
            detail=(
                f"{remote}/{branch} does not exist"
                + (
                    ""
                    if fast_forward_if_behind
                    else " after launch composition"
                )
            ),
            remote_oid=None,
        )

    # Fetch the exact branch after advertising it. The command-scoped ref is
    # the authority for both ancestry and the fast-forward if the branch moved
    # between the two network calls; a concurrent fetch cannot replace it.
    remote_tip = _fetch_branch_oid(root, push_urls[0], branch)
    local_tip = _run_git(root, "rev-parse", "HEAD").strip()
    strict_changed: set[str] | None = None
    if require_single_push_url:
        # An assist lease authorizes a generated state commit, never ambient
        # product/config/ticket dirt. Check this even at the exact remote tip;
        # returning early here used to let dirty bytes enter prompt composition
        # and the later scoped commit.
        strict_changed = set(_changed_paths_under(root, "."))
        permitted = set(permitted_dirty_bytes or ())
        if preserve_union_rel:
            permitted.add(preserve_union_rel)
        unexpected = sorted(strict_changed - permitted)
        if unexpected:
            return _FeaturePublicationState(
                aligned=False,
                may_commit=False,
                detail=(
                    f"checkout at {remote}/{branch} has other changes: "
                    f"{', '.join(unexpected)}"
                ),
                remote_oid=remote_tip,
            )
        captured_rels = list(permitted_dirty_bytes or ())
        if captured_rels and _has_staged_changes(root, captured_rels):
            return _FeaturePublicationState(
                aligned=False,
                may_commit=False,
                detail="captured task output has staged changes",
                remote_oid=remote_tip,
            )
        dirty_refusal = _permitted_dirty_bytes_refusal(
            root,
            local_tip,
            permitted_dirty_bytes or {},
        )
        if dirty_refusal is not None:
            return _FeaturePublicationState(
                aligned=False,
                may_commit=False,
                detail=dirty_refusal,
                remote_oid=remote_tip,
            )
        if preserve_union_rel and _has_staged_changes(root, [preserve_union_rel]):
            return _FeaturePublicationState(
                aligned=False,
                may_commit=False,
                detail=f"{preserve_union_rel} has staged changes",
                remote_oid=remote_tip,
            )
        if (
            preserve_union_rel
            and preserve_union_rel in strict_changed
        ):
            committed_mode = _tree_entry_mode(
                root,
                local_tip,
                preserve_union_rel,
            )
            working_mode = _regular_worktree_mode(root, preserve_union_rel)
            if (
                (
                    committed_mode is not None
                    and committed_mode not in {"100644", "100755"}
                )
                or working_mode != (committed_mode or "100644")
            ):
                return _FeaturePublicationState(
                    aligned=False,
                    may_commit=False,
                    detail=(
                        f"{preserve_union_rel} changed file type or mode; "
                        "the append-only exception requires the same regular "
                        "file mode"
                    ),
                    remote_oid=remote_tip,
                )
            working = _working_tree_bytes(root, preserve_union_rel)
            if working is None:
                return _FeaturePublicationState(
                    aligned=False,
                    may_commit=False,
                    detail=f"{preserve_union_rel} was deleted",
                    remote_oid=remote_tip,
                )
            committed = _tree_bytes(root, local_tip, preserve_union_rel) or b""
            if (
                len(working) <= len(committed)
                or not working.startswith(committed)
            ):
                return _FeaturePublicationState(
                    aligned=False,
                    may_commit=False,
                    detail=(
                        f"{preserve_union_rel} is not an append-only change"
                    ),
                    remote_oid=remote_tip,
                )
    if local_tip == remote_tip:
        return _FeaturePublicationState(
            aligned=True,
            may_commit=True,
            detail=f"matched {remote}/{branch}",
            remote_oid=remote_tip,
        )

    merge_base = _run_git(root, "merge-base", local_tip, remote_tip).strip()
    relation = (
        "behind"
        if merge_base == local_tip
        else "ahead"
        if merge_base == remote_tip
        else "diverged"
    )
    if not fast_forward_if_behind:
        return _FeaturePublicationState(
            aligned=False,
            may_commit=False,
            detail=(
                f"local tip moved {relation} relative to {remote}/{branch} "
                "after launch composition"
            ),
            remote_oid=remote_tip,
        )
    if relation != "behind":
        return _FeaturePublicationState(
            aligned=False,
            may_commit=True,
            detail=f"local tip is {relation} relative to {remote}/{branch}",
            remote_oid=remote_tip,
        )

    changed = (
        strict_changed
        if strict_changed is not None
        else set(_changed_paths_under(root, "."))
    )
    permitted = set(permitted_dirty_bytes or ())
    if preserve_union_rel:
        permitted.add(preserve_union_rel)
    unexpected = sorted(changed - permitted)
    if unexpected:
        return _FeaturePublicationState(
            aligned=False,
            may_commit=False,
            detail=(
                f"local tip is behind {remote}/{branch} and the checkout has "
                f"other changes: {', '.join(unexpected)}"
            ),
            remote_oid=remote_tip,
        )

    if preserve_union_rel and _has_staged_changes(root, [preserve_union_rel]):
        return _FeaturePublicationState(
            aligned=False,
            may_commit=False,
            detail=(
                f"local tip is behind {remote}/{branch} and "
                f"{preserve_union_rel} has staged changes"
            ),
            remote_oid=remote_tip,
        )

    if preserve_union_rel and preserve_union_rel in changed:
        working = _working_tree_bytes(root, preserve_union_rel)
        if working is None:
            return _FeaturePublicationState(
                aligned=False,
                may_commit=False,
                detail=(
                    f"local tip is behind {remote}/{branch} and "
                    f"{preserve_union_rel} was deleted"
                ),
                remote_oid=remote_tip,
            )
        base = _tree_bytes(root, local_tip, preserve_union_rel)
        fetched = _tree_bytes(root, remote_tip, preserve_union_rel)
        merged = _merge_union_bytes(
            current=fetched or b"",
            base=base or b"",
            other=working,
        )
        _require_checkout_tip(
            root,
            branch,
            local_tip,
            action=f"fast-forward {remote}/{branch}",
        )
        try:
            _write_worktree_bytes(
                root,
                preserve_union_rel,
                base,
                expected=working,
                expected_branch=branch,
                expected_oid=local_tip,
            )
            _require_checkout_tip(
                root,
                branch,
                local_tip,
                action=f"fast-forward {remote}/{branch}",
            )
            _run_git(root, "merge", "--ff-only", "--quiet", remote_tip)
            # Never replace the fetched file with the stale pre-merge sample:
            # another Coga process may have appended after our sample. Add only
            # the union lines still missing from the live file.
            _append_missing_union_bytes(
                root,
                preserve_union_rel,
                merged,
                expected_branch=branch,
                expected_oid=remote_tip,
            )
        except BaseException as exc:
            # The dirty audit append was temporarily hidden so `git merge`
            # could fast-forward. A signal can arrive before or after that
            # merge updates HEAD, and the post-merge union append can fail too.
            # Restore the pending lines against either exact owned tip before
            # propagating; never write them onto a switched checkout.
            try:
                checkout_branch = _current_branch(root)
                checkout_oid = _run_git(root, "rev-parse", "HEAD").strip()
                if (
                    checkout_branch != branch
                    or checkout_oid not in {local_tip, remote_tip}
                ):
                    raise GitError(
                        "checkout changed while restoring the pending audit "
                        "append after assist alignment"
                    )
                _append_missing_union_bytes(
                    root,
                    preserve_union_rel,
                    working,
                    expected_branch=branch,
                    expected_oid=checkout_oid,
                )
            except BaseException as restore_exc:
                raise UncertainFeaturePublicationError(
                    "could not restore the pending audit append after assist "
                    f"alignment failed: {restore_exc}"
                ) from exc
            raise
    else:
        _require_checkout_tip(
            root,
            branch,
            local_tip,
            action=f"fast-forward {remote}/{branch}",
        )
        _run_git(root, "merge", "--ff-only", "--quiet", remote_tip)

    return _FeaturePublicationState(
        aligned=True,
        may_commit=True,
        detail=f"fast-forwarded to {remote}/{branch}",
        remote_oid=remote_tip,
    )


def _permitted_dirty_bytes_refusal(
    root: Path,
    base_oid: str,
    expected_by_rel: Mapping[str, bytes | None],
) -> str | None:
    """Return why a captured strict task leaf is no longer byte/mode exact."""
    for rel, expected in expected_by_rel.items():
        path = root / rel
        if path.is_symlink():
            return f"captured task path {rel} became a symbolic link"
        if expected is None:
            if path.exists():
                return f"captured deleted task path {rel} was recreated"
            continue
        if not path.is_file():
            return f"captured task path {rel} is no longer a regular file"
        try:
            current = path.read_bytes()
        except OSError as exc:
            return f"could not re-read captured task path {rel}: {exc}"
        if current != expected:
            return f"captured task path {rel} changed during lease acquisition"
        committed_mode = _tree_entry_mode(root, base_oid, rel)
        if committed_mode is not None and committed_mode not in {"100644", "100755"}:
            return f"captured task path {rel} replaced a non-regular Git entry"
        expected_mode = committed_mode or "100644"
        if _regular_worktree_mode(root, rel) != expected_mode:
            return f"captured task path {rel} changed file mode"
    return None


def feature_publication_lease(
    cfg: Config,
    task_path: Path,
    branch: str,
    *,
    allow_append_only_log: bool = False,
    allowed_dirty_paths: Mapping[Path, bytes | None] | None = None,
) -> FeaturePublicationLease:
    """Normalize every lower-level lease probe into a fail-closed refusal."""
    try:
        return _feature_publication_lease(
            cfg,
            task_path,
            branch,
            allow_append_only_log=allow_append_only_log,
            allowed_dirty_paths=allowed_dirty_paths,
        )
    except FeaturePublicationError:
        raise
    except GitError as exc:
        raise FeaturePublicationError(
            f"could not verify assist publication lease: {exc}"
        ) from exc


def _feature_publication_lease(
    cfg: Config,
    task_path: Path,
    branch: str,
    *,
    allow_append_only_log: bool = False,
    allowed_dirty_paths: Mapping[Path, bytes | None] | None = None,
) -> FeaturePublicationLease:
    """Verify and lease one exact aligned feature/control state.

    Both the child-facing environment reader and launch's post-session
    blocked-resume reblock use this primitive. It never fast-forwards: once a
    prompt has run, a moved branch requires a fresh launch rather than silently
    changing the state the agent worked against. The feature tip's committed
    lifecycle tuple must also exactly match a freshly fetched control copy; the
    returned lease rechecks that pre-transition tuple during publication.
    Automatic post-session re-blocking may retain one uncommitted usage-log
    append; its caller opts into that sole append-only exception explicitly.
    """
    if not cfg.git_enabled:
        raise FeaturePublicationError("assist publication requires git sync")
    if branch == cfg.git_control_branch:
        raise FeaturePublicationError(
            f"assist branch {branch!r} is also the configured control branch; "
            "strict assist publication requires a distinct branch"
        )
    root = _toplevel(task_path)
    if root is None:
        raise FeaturePublicationError(
            "assist publication requires a git checkout"
        )
    current_branch = _current_branch(root)
    if current_branch != branch:
        raise FeaturePublicationError(
            f"expected assist branch {branch!r}, but the checkout changed to "
            f"{current_branch!r}"
        )
    if not _remote_configured(root, cfg.git_remote):
        raise FeaturePublicationError(
            f"assist publication requires configured remote {cfg.git_remote!r}"
        )
    preserve_union_rel = (
        _relative_worktree_file_to_root(root, log_path(cfg))
        if allow_append_only_log
        else None
    )
    push_url = _single_assist_push_url(root, cfg.git_remote)
    permitted_dirty_bytes: dict[str, bytes | None] = {}
    for path, data in (allowed_dirty_paths or {}).items():
        candidate = path.absolute()
        try:
            candidate.relative_to(root.absolute())
        except ValueError as exc:
            raise FeaturePublicationError(
                f"captured assist path is outside the repository: {candidate}"
            ) from exc
        permitted_dirty_bytes[_relative_to_root(root, candidate)] = data
    publication = _prepare_feature_branch_publication(
        root,
        cfg.git_remote,
        branch,
        preserve_union_rel=preserve_union_rel,
        fast_forward_if_behind=False,
        require_single_push_url=True,
        push_url=push_url,
        permitted_dirty_bytes=permitted_dirty_bytes,
    )
    local_oid = _run_git(root, "rev-parse", "HEAD").strip()
    if (
        not publication.aligned
        or publication.remote_oid is None
        or local_oid != publication.remote_oid
    ):
        raise FeaturePublicationError(publication.detail)

    ticket_path = _ticket_path_for_task_path(task_path)
    ticket_rel = _relative_to_root(root, ticket_path)
    task_rel = _relative_to_root(root, task_path)
    feature_ticket = _tree_bytes(root, local_oid, ticket_rel)
    try:
        control_tip = _control_base_for_attempt(
            root,
            cfg.git_remote,
            cfg.git_control_branch,
            1,
            push_url=push_url,
        )
        control_ticket = _tree_bytes(root, control_tip, ticket_rel)
        control_task_oid = _tree_entry_oid(root, control_tip, task_rel)
    except GitError as exc:
        raise FeaturePublicationError(
            f"could not verify the assist ticket on control branch "
            f"{cfg.git_control_branch!r}: {exc}"
        ) from exc
    if feature_ticket is None:
        raise FeaturePublicationError(
            f"assist feature tip has no ticket at {ticket_rel}"
        )
    if control_task_oid is None:
        raise FeaturePublicationError(
            f"assist control tip has no task at {task_rel}"
        )
    feature_state = _ticket_lifecycle_state(feature_ticket)
    control_state = _ticket_lifecycle_state(control_ticket)
    if feature_state is None:
        raise FeaturePublicationError(
            f"assist feature tip has an unreadable ticket at {ticket_rel}"
        )
    if control_state != feature_state:
        raise FeaturePublicationError(
            f"assist ticket does not match fresh control state "
            f"(feature {_ticket_state_summary(feature_ticket)}; "
            f"control {_ticket_state_summary(control_ticket)})"
        )
    return FeaturePublicationLease(
        branch=branch,
        local_oid=local_oid,
        remote_oid=publication.remote_oid,
        push_url=push_url,
        control_ticket_state=feature_state,
        control_task_oid=control_task_oid,
    )


def _remote_branch_present(root: Path, remote: str, branch: str) -> bool:
    """True when the configured remote has `refs/heads/<branch>`."""
    if not _remote_configured(root, remote):
        return False
    return _remote_branch_oid(root, remote, branch) is not None


def _control_branch_present(
    root: Path,
    branch: str,
    remote: str,
    *,
    probe_remote: bool = True,
) -> bool:
    """True when the configured control branch exists locally or remotely.

    Local refs cover the common same-branch and cloned-feature cases without a
    remote probe. When no local ref exists, ask the configured remote exactly:
    a remote-only `origin/main` is still valid because the cross-branch landing
    path fetches that branch before pushing. Callers that must stay local, such
    as `coga init`, set ``probe_remote=False`` and use only existing local and
    remote-tracking refs.
    """
    if _git_ref_present(root, f"refs/heads/{branch}"):
        return True
    if _git_ref_present(root, f"refs/remotes/{remote}/{branch}"):
        return True
    if not probe_remote:
        return False
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


def _no_remote_message(cfg: Config) -> str:
    """Actionable one-liner for a repo with no configured `<remote>`.

    The expected first-run state after `git init` + `coga init` ("push when
    ready"). Surfaced in place of the raw two-paragraph `git push` fatal the
    absent remote would otherwise raise — the same short-notice treatment the
    "git disabled" and "not a git repo" cases already get. The local commit
    still happens (only the push is skipped), except on a detached HEAD where no
    durable commit is made; "saved locally" is accurate for both.
    """
    return (
        f"[git] no {cfg.git_remote!r} remote configured — coga state saved "
        f"locally; add a remote to sync"
    )


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


def _relative_worktree_file_to_root(root: Path, path: Path) -> str:
    """Return a worktree leaf path without following that leaf if it is a link."""
    lexical = path.parent.resolve() / path.name
    try:
        return str(lexical.relative_to(root.resolve()))
    except ValueError:
        return str(lexical)


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
    "capture_revision_file_bytes",
    "capture_task_file_bytes",
    "capture_task_mutation_snapshot",
    "FileMutationRollback",
    "FeaturePublicationError",
    "FeaturePublicationLease",
    "GitError",
    "StateRegressionError",
    "feature_publication_lease",
    "guard_ticket_state",
    "is_linked_worktree",
    "refresh_coga_state_from_control",
    "stale_coga_task_rels",
    "sync_coga_state",
    "sync_log",
    "sync_paths",
    "sync_task_state",
    "ticket_state_guard",
    "UncertainFeaturePublicationError",
]
