"""Git sync — publish Coga state to the control branch, the git analogue of Slack.

Every Coga command that mutates task state writes markdown to disk and then
calls `sync_task_state`, `sync_log`, or (at the CLI boundary) the catch-all
`sync_coga_state`. All three are thin wrappers over one primitive, `publish`,
which builds a commit on top of `origin/<control>` in a temporary index and
pushes it straight to `refs/heads/<control>` — never committing on any local
branch and never touching the working tree. The local `<control>` only
fast-forwards, or realigns over local commits proven to be Coga state control
already carries (`fast_forward_control`), and `refresh` is the one integrate
path (fetch + that move) used by exempt launches and the recurring gate.

Invariants, in the order they matter:

- **Canonical.** `<remote>/<control>` is the only durable home of Coga state.
  With no remote configured, the local `<control>` branch plays that role and
  the push is skipped — the one stated exception.
- **Nothing is lost.** The on-disk markdown is the write. A publish that
  cannot reach control leaves the file exactly as written (dirty), reports
  once on stderr and in `coga/log.md`, never crashes the command, and is
  retried by the next command's sweep. The audit log uses event-aware reconciliation and guarded mutations;
  `merge=union` worklists retain their three-way merge.
- **Nothing moves backward.** Each published path is a compare-and-swap
  against control: the control blob must be one this checkout derived its
  working copy from — its HEAD copy, the merge-base copy, a copy this
  worktree itself published (`refs/worktree/coga/published`), or the working
  bytes themselves — else the publish is refused and names the fix. A
  control ticket carrying `pending:<uuid>` accepts only its own admission.
- **One integrate path.** `fast_forward_control` is the only code that moves
  the local control ref, after a publish and inside `refresh` alike (and
  `prepare_control_checkout` applies the same `_local_control_subsumed`
  proof). It checks ancestry explicitly rather than trusting `merge
  --ff-only`'s exit, and never stashes, rebases, resets, or commits.

Outcomes: `publish` returns `True` (pushed), `False` (control already held
the built tree), or `None` (soft-skipped: git disabled, not a repo, control
branch absent). It raises `StateRegressionError` when the write was refused,
`GitError` when it definitely did not land (offline, rejected transport), and
`UncertainPublishError` when the push reported failure but control could not
be re-read to tell; in every case the working file stays as written and the
next sweep retries it.

Subprocess usage mirrors `autoclose.py` (`gh` shell-out): no third-party git
binding, just `subprocess.run` with `check=False` and explicit error handling.
"""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import threading
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from coga.oscompat import lock_dir, lock_fd, unlock_fd
from coga.config import Config
from coga.github_source import redacted_git_source
from coga.logfile import append_log, ref_tag_for_path
from coga.paths import log_path, tasks_dir
from coga.ticket import (
    Ticket,
    TicketError,
    admitted_launch_generation,
    pending_launch_generation,
    released_launch_generation,
)

# Bounded retries when racing `refs/heads/<control>`: each loss is a refetch +
# rebuild + repush, so a small ceiling is plenty under realistic contention.
MAX_PUBLISH_ATTEMPTS = 5
# Planning attempts `prepare_control_checkout` allows while control refs move.
PREPARATION_ATTEMPTS = 3

# Process exit code meaning "the command deliberately retained retryable local
# state; do not run the catch-all end-of-command state sweep". The recurring
# freshness gate uses it when the control checkout is stale. 75 is BSD's
# EX_TEMPFAIL ("temporary failure, retry later").
RETRY_WITHOUT_SWEEP_EXIT_CODE = 75
STALE_CONTROL_EXIT_CODE = RETRY_WITHOUT_SWEEP_EXIT_CODE

# Set when a launch's checkout return refused or stopped mid-way: the
# preserved dirt is exactly what the end-of-command sweep must not publish.
# `cli.main` scopes it to one invocation, so an in-process `coga recurring`
# run withholds its final sweep too; the next command's entry publication
# picks the routine state back up. The command's exit status is unaffected.
state_sweep_withheld: ContextVar[bool] = ContextVar("state_sweep_withheld", default=False)

# Set by `recurring_runner` once it forwards a command to the control-branch
# relay. Scoped by `cli.main`: the forwarding process must not sweep its own
# checkout, even when the child fails or is interrupted. This is
# process-local, so the child retains its ordinary end-of-command publication.
control_relay_started: ContextVar[bool] = ContextVar("control_relay_started", default=False)

# Per-worktree ref (git keeps `refs/worktree/*` private to each checkout)
# holding a tree of the blobs this checkout itself published. It is what lets
# a feature-branch or detached checkout keep publishing the same ticket: its
# HEAD never advances with control, so its own previous publishes are the
# provenance of its working copy.
PUBLISHED_REF = "refs/worktree/coga/published"

_STATUS_RANK = {"draft": 0, "active": 1, "in_progress": 2, "done": 3, "canceled": 3}
_URL_IN_DIAGNOSTIC_RE = re.compile(r"https?://[^\s'\"<>]+")
_CHECK_ATTR_BATCH = 200


class GitError(Exception):
    """A git operation failed, or its outcome is unknown."""


class StateRegressionError(GitError):
    """The publish was refused before anything reached control."""


class UncertainPublishError(GitError):
    """The push reported failure and control could not be re-read to tell."""


class ObjectWriteError(GitError):
    """`git hash-object -w` could not store a blob for a checkout file.

    Writing the checkout file and writing Git's object storage are separate
    operations, so the working copy can be written while this fails. Carries
    where Git was writing — the absolute checkout and the object directory Git
    itself resolves, looked up only after the failure (`None` when that lookup
    failed too). It names the operation, not a cause: a clean filter applied
    through `--path` fails here as well, so permission is never implied.
    """

    def __init__(
        self, *, rel: str, checkout: Path, object_dir: Path | None, detail: str
    ) -> None:
        self.rel = rel
        self.checkout = checkout
        self.object_dir = object_dir
        self.detail = detail
        location = str(object_dir) if object_dir is not None else "unavailable"
        super().__init__(
            f"`git hash-object -w` failed for {rel} (checkout {checkout}; "
            f"object directory {location}): {detail}"
        )


# --- lock ---------------------------------------------------------------------

_HELD_LOCKS: dict[tuple[str, int], list[int]] = {}


@contextmanager
def state_lock(cfg: Config, *, blocking: bool = True) -> Iterator[None]:
    """Serialize this checkout's Coga writers and publishers.

    A short, kernel-released advisory lock around a ticket's
    read-modify-write and its publication. Reentrant within one thread, so
    a caller that holds it across a longer window (megalaunch's admission)
    can still call `publish`; every other thread and process waits. Its file
    lives outside the worktree, so it can never enter a state sweep, and a
    crashed process leaves nothing behind.
    """
    checkout = hashlib.sha256(os.fsencode(cfg.repo_root.resolve())).hexdigest()
    key = (checkout, threading.get_ident())
    held = _HELD_LOCKS.get(key)
    if held is not None:
        held[1] += 1
        try:
            yield
        finally:
            held[1] -= 1
        return
    lock_root = lock_dir("coga-state-publication")
    try:
        lock_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(lock_root / f"{checkout}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    except OSError as exc:
        raise GitError(f"could not open local state lock: {exc}") from exc
    try:
        lock_fd(fd, blocking=blocking)
    except OSError as exc:
        os.close(fd)
        raise GitError(f"local state lock failed: {exc}") from exc
    _HELD_LOCKS[key] = [fd, 1]
    try:
        yield
    finally:
        del _HELD_LOCKS[key]
        try:
            unlock_fd(fd)
        finally:
            os.close(fd)


def write_ticket(
    cfg: Config, ticket: Ticket, path: Path, *, prepared: "PreparedTicket | None" = None,
) -> bytes:
    """Render and write a ticket under `state_lock`; return the bytes written.

    With `prepared`, the write is the commit of a prepared transaction: it
    refuses with `TicketChangedError` unless the file still holds the bytes
    preparation (or its previous prepared write) left, so an edit made after
    the command read the ticket is never overwritten. The preparation then
    tracks the new bytes.
    """
    rendered = ticket.render().encode("utf-8")
    with state_lock(cfg):
        if prepared is not None:
            try:
                current: bytes | None = path.read_bytes()
            except FileNotFoundError:
                current = None
            if current != prepared.local:
                raise TicketChangedError(
                    f"{path}: changed after this command read it; nothing was "
                    "written. Retry from the current ticket"
                )
        ticket.write(path)
        if prepared is not None:
            prepared.local = path.read_bytes()
    return rendered


# --- entry points -------------------------------------------------------------


def sync_task_state(
    cfg: Config,
    task_path: Path,
    *,
    message: str,
    expect: Mapping[Path, bytes | None] | None = None,
    strict: bool = False,
    command: str | None = None,
    prepared: "PreparedTicket | None" = None,
) -> bool | None:
    """Publish one task (file or directory) plus `coga/log.md`.

    `prepared` publishes a prepared transaction: its exact control bytes
    become the ticket's expectation (unless `expect` already pins it), and a
    failed or refused attempt is remembered so later retries keep that
    expectation (see `publish`'s `remember`).

    Non-fatal by default: a refusal or failure is written to stderr and the
    task's log, then swallowed, so the local transition stands. `strict=True`
    re-raises after reporting, for callers that gate later work on it; its
    report stays neutral because the caller may still restore state.
    `command` names the CLI spelling (`"bump"`) the best-effort recovery hint
    tells the operator not to rerun.
    """
    if prepared is not None and prepared.fresh:
        expect = {**prepared.expect(), **(expect or {})}
    try:
        return publish(
            cfg, [task_path, log_path(cfg)], message, expect=expect,
            remember=prepared is not None and prepared.fresh,
        )
    except StateRegressionError as exc:
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
        if strict:
            raise
    except GitError as exc:
        # Log first, so the recovery hint can name the log it just wrote.
        record_sync_failure(cfg, ref_tag_for_path(cfg, task_path), exc)
        sys.stderr.write(sync_failure_report(
            cfg, exc, message=message,
            retained=None if strict else "Local task state was saved",
            command=command,
            recovery_paths=(task_path, log_path(cfg)),
        ))
        if strict:
            raise
    return None


def sync_log(cfg: Config, *, message: str) -> bool | None:
    """Publish the required log; return True/False for published/already held.

    A failed or skipped publication returns None, with its reason on stderr.
    Requiring the log prevents an ignored new log from silently succeeding
    as a no-op. Callers can distinguish that failure from an unchanged log.
    """
    try:
        path = log_path(cfg)
        return publish(cfg, [path], message, require_paths=[path])
    except GitError as exc:
        sys.stderr.write(sync_failure_report(
            cfg, exc, message=message, label="log sync failed",
            retained="The local log was retained", recovery_paths=[path],
        ))
        return None


def retry_session_publication(cfg: Config, task_path: Path, *, slug: str) -> bool | None:
    """Republish a supervised session's ticket plus the log after it exits.

    Runs in the invoking process, outside the child's sandbox, so a lifecycle
    write the child could not publish (for example a read-only object store)
    lands now. It fetches first, so bytes another process already landed are
    confirmed — `publish` returns False and records them as this worktree's
    provenance. No lifecycle command is replayed: the working files are the
    write, guarded as always, with any prepared expectation the child
    remembered. A refused ticket still lets the log publish on its own.
    Returns the log outcome in `sync_log`'s convention (`None`: not
    confirmed); every miss is reported on stderr and the local files stay.
    """
    # Name the commit after what it carries: a ticket the session changed,
    # or (the common case, its own bump already landed) only the log.
    message = f"Log: {slug}"
    if cfg.git_enabled:
        try:
            root = toplevel(cfg.repo_root)
            if root is not None and remote_configured(root, cfg.git_remote):
                _fetch_control(root, cfg.git_remote, cfg.git_control_branch)
            if root is not None and _differs_from_control(cfg, root, task_path):
                message = f"Ticket: {slug} — session state"
        except GitError as exc:
            sys.stderr.write(f"[git] note: could not fetch control before session publication: {exc}\n")
    try:
        return publish(cfg, [task_path, log_path(cfg)], message)
    except StateRegressionError as exc:
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
        return sync_log(cfg, message=f"Log: {slug}")
    except GitError as exc:
        record_sync_failure(cfg, ref_tag_for_path(cfg, task_path), exc)
        sys.stderr.write(sync_failure_report(
            cfg, exc, message=message, retained="Local task state was saved",
            recovery_paths=(task_path, log_path(cfg)),
        ))
        return None


def _differs_from_control(cfg: Config, root: Path, path: Path) -> bool:
    """Whether any file of the task at `path` differs from known control."""
    rev = known_control_revision(cfg, root)
    if rev is None:
        return True
    rel = relative_to_root(root, path)
    local = run_git(root, "ls-files", "-z", "-co", "--exclude-standard", "--", rel)
    remote = run_git(root, "ls-tree", "-r", "-z", "--name-only", rev, "--", rel)
    names = {name for name in (local + remote).split("\x00") if name}
    for name in names:
        data = _working_tree_bytes(root, name)
        if (None if data is None else _blob_id(root, data, name)) != _blob_oid(root, rev, name):
            return True
    return False


def sync_coga_state(
    cfg: Config, *, message: str = "Sync coga state",
    previous_contexts_root: Path | None = None,
) -> None:
    """The catch-all sweep: publish eligible files under the Coga roots.

    Runs at the CLI dispatch boundary and is the retry for every earlier miss.
    The whole of `coga_root_paths` — the Coga root and the contexts root —
    goes to `publish`, so tickets, the log, recurring templates, skills,
    workflows, shared config, and contexts all land through the same guarded
    path. `_candidates` selects every dirty, unignored file there plus
    committed state this checkout derived (a hand commit on local control, or
    routine task state committed on a feature branch); clean state merely
    behind control is not a write.
    """
    try:
        root = _publishable_root(cfg, message)
        if root is None:
            return
        publish(cfg, coga_root_paths(cfg, previous_contexts_root), message)
    except StateRegressionError as exc:
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
    except GitError as exc:
        sys.stderr.write(sync_failure_report(
            cfg, exc, message=message, retained="Local Coga files were retained",
        ))
        record_sync_failure(cfg, ref_tag_for_path(cfg, cfg.repo_root), exc)


def sync_failure_report(
    cfg: Config,
    exc: GitError,
    *,
    message: str | None = None,
    label: str = "sync failed",
    retained: str | None = None,
    command: str | None = None,
    recovery_paths: Iterable[Path] = (),
) -> str:
    """The stderr text for a failed state publication; policy stays with the caller.

    The first line is the recognizable `[git] <label>: <exc>`, with the
    publication subject when given. `retained` is for best-effort callers
    whose local write stands: a second line separates that kept local state
    from the failed Git publication, says not to repeat the command (`coga
    <command>` when named), and points to `coga run publish-state` from this
    checkout. Strict and adoption callers omit it and get the neutral line
    alone. A refusal never gets the retry hint (its own reconciliation
    guidance governs), an uncertain push is "could not be confirmed", and only
    an `ObjectWriteError` adds the conditional restore-access step.
    `recovery_paths` become the recipe's required files where each still is
    a regular file (a task directory contributes its `ticket.md`); deleted or
    missing paths drop out, leaving the no-path form, which sweeps them anyway.
    """
    text = f"[git] {label}: {exc}."
    if message:
        text += f" Message was: {message}"
    text += "\n"
    if retained is None or isinstance(exc, StateRegressionError):
        return text
    outcome = "could not be confirmed" if isinstance(exc, UncertainPublishError) else "failed"
    rerun = f"`coga {command}`" if command else "the command"
    required: list[str] = []
    for path in recovery_paths:
        if path.is_dir():
            path = path / "ticket.md"
        if path.is_file() and not path.is_symlink():
            required.append(shlex.quote(os.path.relpath(path, cfg.repo_root)))
    recipe = " ".join(["coga run publish-state", *required])
    run = f"run `{recipe}` from {shlex.quote(str(Path(os.path.abspath(cfg.repo_root))))}"
    if isinstance(exc, ObjectWriteError):
        step = (
            "If Git could not write to the object storage shown above, restore "
            f"permitted access to it first, then {run}"
        )
    else:
        step = run[0].upper() + run[1:]
    return text + (
        f"[git] {retained}; Git publication {outcome}. Do not rerun {rerun} to "
        f"recover. {step}; it publishes all eligible Coga state without another "
        "transition.\n"
    )


def record_sync_failure(cfg: Config, tag: str, exc: GitError) -> None:
    """Append the concise `sync failed` audit line, never masking `exc`.

    A failure handler that cannot write the log (the same restricted checkout
    can refuse it) reports that on stderr and returns, so the original
    failure still propagates or is swallowed per the caller's policy.
    """
    try:
        append_log(cfg, tag, "git", f"sync failed: {exc}")
    except OSError as log_exc:
        sys.stderr.write(f"[git] could not record the sync failure in the log: {log_exc}\n")


def coga_root_paths(
    cfg: Config, previous_contexts_root: Path | None = None,
) -> tuple[Path, ...]:
    """The directories whose eligible files Coga publishes on its own.

    The Coga root and the contexts root (`Config.contexts_root`, which
    `[layout] contexts` may move outside it). This is the one membership
    definition shared by the sweep, guided authoring, checkout preparation
    and return, state-only commit recovery, and the `mark done` stranding
    guard. A root nested in another (the default `coga/contexts/`) is not
    listed twice. In the root layout the Coga root is the checkout itself.
    Ignored files are never candidates: every consumer asks Git, which
    honors `.gitignore`.
    """
    roots: list[Path] = []
    paths = (cfg.repo_root, cfg.contexts_root)
    if previous_contexts_root is not None:
        paths += (previous_contexts_root,)
    for path in paths:
        # Membership is lexical: a link under these roots never expands the
        # publication boundary to its target (including a former root).
        resolved = Path(os.path.abspath(path))
        if any(resolved == kept or kept in resolved.parents for kept in roots):
            continue
        roots = [kept for kept in roots if resolved not in kept.parents]
        roots.append(resolved)
    return tuple(roots)


# --- publish ------------------------------------------------------------------


def publish(
    cfg: Config,
    paths: Iterable[Path],
    message: str,
    *,
    expect: Mapping[Path, bytes | None] | None = None,
    guard: Callable[[str], None] | None = None,
    fast_forward: bool = True,
    require_paths: Iterable[Path] = (),
    log_mutation: "LogMutation | None" = None,
    remember: bool = False,
) -> bool | None:
    """Land the dirty files under `paths` on the control branch.

    `expect` maps a path to the bytes the writer read before writing (`None`
    for "must not exist"); it replaces the default provenance check for that
    path with that exact blob, and for a `merge=union` path it adds one.
    `guard` is called with the control commit each attempt builds on — the
    remote-tracking ref, re-fetched after every rejected push — before any
    tree is built; it may raise to refuse. It exists for a decision `expect`
    cannot express: shared audit state whose *content* matters (the
    recurring serviced-period ledger), where pinning the whole blob would
    refuse every unrelated concurrent append. `fast_forward=False` leaves the
    local control checkout untouched after a successful push (Retro's
    isolated delete).
    `require_paths` names files which must either be selected for this publish
    or already match control. It refuses before any write when a required
    authored file is excluded as committed feature-branch review work.

    A ticket path named in `expect` is published whenever its working copy
    differs from control, even if it equals HEAD. `remember=True` (a prepared
    lifecycle transaction) records each expectation in this checkout's
    pending-expectation file when the attempt fails retryably, or marks it
    rejected when it is refused, so the supervisor retry and the sweep reuse
    the exact expectation rather than the broader provenance check (see
    `_PENDING_FILE`).
    """
    root = _publishable_root(cfg, message)
    if root is None:
        return None
    pathspecs = [relative_to_root(root, path) for path in paths]
    if not control_branch_present(root, cfg.git_control_branch, cfg.git_remote):
        sys.stderr.write(control_branch_mismatch_message(cfg, root) + f" ({message})\n")
        return None
    expected = {
        relative_to_root(root, path): (
            None if data is None
            else _blob_id(root, data, relative_to_root(root, path))
        )
        for path, data in (expect or {}).items()
    }
    with state_lock(cfg):
        required = [relative_to_root(root, path) for path in require_paths]
        pending = _load_pending(cfg)
        before = dict(pending)
        try:
            return _publish_locked(
                cfg, root, pathspecs, message, expected, guard, fast_forward,
                required, log_mutation, pending=pending,
            )
        except StateRegressionError:
            if remember:
                pending.update({rel: {"expect": oid, "state": "rejected"} for rel, oid in expected.items()})
            raise
        except GitError:
            if remember:
                pending.update({rel: {"expect": oid, "state": "pending"} for rel, oid in expected.items()})
            raise
        finally:
            if pending != before:
                _save_pending(cfg, pending)


def _publishable_root(cfg: Config, message: str) -> Path | None:
    """The git toplevel, or `None` after one calm line for each soft-skip."""
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return None
    try:
        root = toplevel(cfg.repo_root)
    except GitError as exc:
        sys.stderr.write(f"[git] {exc} (sync skipped): {message}\n")
        return None
    if root is None:
        sys.stderr.write(f"[git] not a git repo (sync skipped): {message}\n")
        return None
    return root


def _publish_locked(
    cfg: Config,
    root: Path,
    pathspecs: list[str],
    message: str,
    expected: Mapping[str, str | None],
    guard: Callable[[str], None] | None,
    fast_forward: bool,
    required: list[str],
    log_mutation: "LogMutation | None" = None,
    *,
    pending: dict[str, dict[str, Any]] | None = None,
) -> bool:
    from coga import log_transaction
    from coga.log_publication import reconcile
    log_transaction.ensure_clear(cfg, log_mutation)
    today = date.today()
    log_rel = relative_to_root(root, log_path(cfg))
    remote, control = cfg.git_remote, cfg.git_control_branch
    have_remote = remote_configured(root, remote)
    fetched = False
    # A commit on a feature or detached checkout is review work: only routine
    # task-directory state and the log are adopted from it. Committed recurring
    # files and other knowledge edits wait for their merge.
    adopt_only = None if symbolic_head(root) == control else _routine_state_areas(cfg, root)
    for _attempt in range(MAX_PUBLISH_ATTEMPTS):
        base = _control_base(root, remote, control, have_remote, fetched=fetched)
        if base is None:
            _fetch_control(root, remote, control)
            fetched = True
            base = _control_base(root, remote, control, have_remote, fetched=True)
            if base is None:
                raise GitError(f"control branch {control!r} not found locally or on {remote!r}")
        if guard is not None:
            guard(base)
        ancestor = _run(["git", "-C", str(root), "merge-base", "HEAD", base]).stdout.decode().strip() or None
        rels = _candidates(root, pathspecs, base, ancestor, adopt_only, log_rel=log_rel)
        # The pending-expectation record is machine-local even where `.coga/`
        # is not ignored.
        pending_rel = relative_to_root(root, cfg.repo_root / _PENDING_FILE)
        rels = [rel for rel in rels if rel != pending_rel]
        # A prepared ticket participates whenever it differs from control,
        # even when its final bytes happen to equal HEAD.
        for rel in _ticket_rels(cfg, root, [rel for rel in expected if rel not in rels]):
            if not any(rel == spec or rel.startswith(spec.rstrip("/") + "/") for spec in pathspecs):
                continue
            data = _working_tree_bytes(root, rel)
            if (None if data is None else _blob_id(root, data, rel)) != _blob_oid(root, base, rel):
                rels.append(rel)
        index_modes = _index_modes(root) if required and os.name != "posix" else None
        for rel in required:
            if rel in rels:
                continue
            _working_tree_bytes(root, rel)  # refuses a symlinked path
            working = _regular_working_file(root, rel, index_modes=index_modes)
            entry = (working[0], _hash_blob(root, working[1], rel)) if working else None
            # Mode counts too: a mode-only edit control lacks is not on control.
            if entry != _tree_entry(root, base, rel):
                raise GitError(
                    f"{rel}: required file is excluded from publication "
                    "and differs from control; check ignore rules or merge its "
                    "reviewed change before retrying"
                )
        if not rels:
            return False
        if not have_remote and _attempt == 0:
            sys.stderr.write(
                f"[git] no {remote!r} remote configured — coga state committed on "
                f"local {control!r} only; add a remote to sync ({message})\n"
            )
        working = {rel: _working_tree_bytes(root, rel) for rel in rels}
        attempt_expected = _pending_expectations(cfg, root, rels, base, working, expected, pending)
        union = union_merge_paths(root, rels) - {log_rel}
        landed = _guard(cfg, root, rels, base, working, union, _provenance(root, rels, ancestor), attempt_expected)
        if log_rel in rels:
            if working[log_rel] is None:
                raise StateRegressionError("audit log is missing locally; restore it before publication")
            landed[log_rel] = reconcile(
                cfg, root, base, _clean_bytes(root, working[log_rel], log_rel),
                source_base=(tree_bytes(root, ancestor, log_rel) or b"") if ancestor else b"",
                head=tree_bytes(root, "HEAD", log_rel) or b"", overlays=landed,
                today=today, mutation=log_mutation,
            )
        tree = _build_tree(root, base, rels, working, union, ancestor, landed)
        staged = {rel: (working[rel], landed[rel]) for rel in rels}
        if tree == run_git(root, "rev-parse", f"{base}^{{tree}}").strip():
            # Already on control. A control checkout still catches up so its
            # dirty-but-equal files come clean; nothing reaches other checkouts.
            if fast_forward and current_branch(root) == control:
                fast_forward_control(cfg, root, base, staged=staged, **({"log_mutation": log_mutation} if log_mutation else {}))
            # Control already holds these exact bytes — perhaps landed by
            # another process from a sandboxed write here. That is confirmed
            # publication, so this worktree records it as provenance.
            _record_published(root, {rel: _blob_oid(root, base, rel) for rel in rels})
            _clear_pending(pending, rels)
            return False
        new = run_git(root, "commit-tree", tree, "-p", base, "-m", message).strip()
        if log_mutation is not None:
            log_transaction.attempted(cfg, new)
        if not have_remote:
            break
        failure = _push(root, remote, f"{new}:refs/heads/{control}")
        if failure is None:
            break
        rejected = any(
            marker in failure.lower()
            for marker in ("non-fast-forward", "fetch first", "rejected", "stale info")
        )
        if not rejected:
            try:
                carried = _control_carries(root, remote, control, new)
            except GitError as exc:
                raise UncertainPublishError(
                    f"push to {remote}/{control} failed: {failure}; "
                    f"control could not be re-read: {exc}"
                ) from exc
            if carried:
                break  # accepted before the connection dropped
            raise GitError(f"push to {remote}/{control} failed: {failure}")
        _fetch_control(root, remote, control)
        fetched = True
    else:
        raise GitError(
            f"could not publish to {remote}/{control} after "
            f"{MAX_PUBLISH_ATTEMPTS} attempts — contention"
        )
    if not have_remote:
        # Local control is the only durable destination here: a commit it does
        # not point at is dangling, so a refused fast-forward is a failed
        # publish, not a note. Nothing is recorded as published for it.
        if not fast_forward_control(cfg, root, new, staged=staged, **({"log_mutation": log_mutation} if log_mutation else {})):
            raise GitError(
                f"no {remote!r} remote configured and local {control!r} could not "
                f"be fast-forwarded to the new commit; the write stays dirty"
            )
        _record_published(root, {rel: _blob_oid(root, new, rel) for rel in rels})
        _clear_pending(pending, rels)
        return True
    _record_published(root, {rel: _blob_oid(root, new, rel) for rel in rels})
    _clear_pending(pending, rels)
    if fast_forward:
        fast_forward_control(cfg, root, new, staged=staged, **({"log_mutation": log_mutation} if log_mutation else {}))
    return True


# Per-checkout record of prepared ticket expectations whose publication has
# not landed (`.coga/` is machine-local and ignored). It lives in the working
# tree rather than under `.git` because the failure it remembers is often a
# read-only object store. Each entry maps a repo-relative ticket path to the
# exact control blob its transition was prepared against (`expect`, `None`
# for "absent") and `state`: `pending` (a retryable failure) or `rejected`
# (control refused it). The supervisor retry and the sweep publish a pending
# path only against that blob, and refuse a rejected one until its working
# copy matches control again or a new prepared transaction replaces it.
_PENDING_FILE = Path(".coga") / "pending-publication.json"


def _load_pending(cfg: Config) -> dict[str, dict[str, Any]]:
    import json

    try:
        data = json.loads((cfg.repo_root / _PENDING_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"[git] note: ignoring unreadable {_PENDING_FILE}: {exc}\n")
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        rel: entry for rel, entry in data.items()
        if isinstance(entry, dict) and entry.get("state") in ("pending", "rejected")
    }


def _save_pending(cfg: Config, pending: Mapping[str, Mapping[str, Any]]) -> None:
    import json

    from coga.atomicio import atomic_write_text

    path = cfg.repo_root / _PENDING_FILE
    try:
        if not pending:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(dict(pending), indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        sys.stderr.write(f"[git] note: could not record pending publication expectations: {exc}\n")


def _clear_pending(pending: dict[str, dict[str, Any]] | None, rels: Iterable[str]) -> None:
    if pending:
        for rel in rels:
            pending.pop(rel, None)


def _pending_expectations(
    cfg: Config,
    root: Path,
    rels: list[str],
    base: str,
    working: Mapping[str, bytes | None],
    expected: Mapping[str, str | None],
    pending: dict[str, dict[str, Any]] | None,
) -> dict[str, str | None]:
    """`expected` plus each remembered prepared expectation for `rels`.

    An explicit expectation wins. A remembered path whose working copy already
    equals control is settled and forgotten; a rejected one refuses.
    """
    result = dict(expected)
    if not pending:
        return result
    for rel in rels:
        entry = pending.get(rel)
        if entry is None or rel in expected:
            continue
        data = working[rel]
        if (None if data is None else _blob_id(root, data, rel)) == _blob_oid(root, base, rel):
            pending.pop(rel)
            continue
        if entry.get("state") == "rejected":
            raise StateRegressionError(
                f"{rel}: control refused this checkout's prepared transition; "
                f"take control's copy with `git checkout {cfg.git_remote}/"
                f"{cfg.git_control_branch} -- {rel}` and redo the edit, or rerun "
                "the lifecycle command to reconcile it"
            )
        result[rel] = entry.get("expect")
    return result


def _control_base(
    root: Path, remote: str, control: str, have_remote: bool, *, fetched: bool
) -> str | None:
    """The commit to build on: the remote-tracking ref, else local control."""
    if have_remote:
        if _ref_present(root, f"refs/remotes/{remote}/{control}"):
            return run_git(root, "rev-parse", f"refs/remotes/{remote}/{control}").strip()
        if not fetched:
            return None
    if _ref_present(root, f"refs/heads/{control}"):
        return run_git(root, "rev-parse", f"refs/heads/{control}").strip()
    return None


def _fetch_control(root: Path, remote: str, control: str) -> None:
    """Refresh `refs/remotes/<remote>/<control>`; a branch the remote lacks is not an error."""
    try:
        run_git(
            root, "fetch", "--quiet", remote,
            f"+refs/heads/{control}:refs/remotes/{remote}/{control}",
            env=_MESSAGE_LOCALE,
        )
    except GitError as exc:
        if "couldn't find remote ref" not in str(exc).lower():
            raise


def known_control_revision(cfg: Config, root: Path) -> str | None:
    """The control commit this checkout currently knows, without fetching.

    The remote-tracking ref (which a successful `publish` push advances), or
    local `<control>` with no remote. `None` when neither exists yet.
    """
    remote, control = cfg.git_remote, cfg.git_control_branch
    return _control_base(root, remote, control, remote_configured(root, remote), fetched=True)


def fetch_control(cfg: Config, root: Path) -> str:
    """Fetch the control branch and return the commit to read control state from.

    The remote-tracking ref after the fetch, or local `<control>` when no
    remote is configured. Megalaunch and the recurring gate read a ticket's
    control copy through `tree_bytes(root, fetch_control(cfg, root), rel)`.
    """
    remote, control = cfg.git_remote, cfg.git_control_branch
    have_remote = remote_configured(root, remote)
    if have_remote:
        _fetch_control(root, remote, control)
    base = _control_base(root, remote, control, have_remote, fetched=True)
    if base is None:
        raise GitError(f"control branch {control!r} not found locally or on {remote!r}")
    return base


def _candidates(
    root: Path,
    pathspecs: list[str],
    base: str,
    ancestor: str | None,
    adopt_only: tuple[tuple[str, ...], tuple[str, ...]] | None = None,
    *, log_rel: str | None = None,
) -> list[str]:
    """The files under `pathspecs` this publish carries.

    Every path dirty against HEAD (a write no commit holds yet), plus a
    clean path whose HEAD copy moved past control from a copy this checkout
    derived from — a feature branch that committed Coga state it had itself
    published, or a hand commit on local control — restricted to `adopt_only`
    areas when given. A clean path that is merely *behind* control — HEAD's copy
    unchanged since the merge base, even when control holds a copy this
    worktree published — is not a write and is left alone.

    An untracked symlink found under a directory pathspec is not eligible and
    is skipped, so a generated agent-skill view in a repo missing its ignore
    rule cannot stall every publish behind the guard's symlink refusal. One
    named explicitly, or replacing a tracked file, still reaches the guard.
    """
    rels = [
        rel for rel in _dirty_paths(root, pathspecs)
        if rel in pathspecs
        or not (root / rel).is_symlink()
        or _blob_oid(root, "HEAD", rel) is not None
    ]
    committed = run_git(root, "diff", "-z", "--name-only", base, "HEAD", "--", *pathspecs)
    for rel in (
        rel for rel in committed.split("\x00")
        if rel and rel not in rels and (adopt_only is None or _in_areas(rel, adopt_only))
    ):
        head_oid = _blob_oid(root, "HEAD", rel)
        if ancestor is not None and head_oid == _blob_oid(root, ancestor, rel):
            continue
        derived = _provenance(root, [rel], ancestor)[rel] - {head_oid}
        if rel == log_rel or _blob_oid(root, base, rel) in derived:
            rels.append(rel)
    return rels


def _provenance(root: Path, rels: list[str], ancestor: str | None) -> dict[str, set[str | None]]:
    """Per path, the control blobs this checkout's working copy may derive from."""
    revs = ["HEAD"]
    if _ref_present(root, PUBLISHED_REF):
        revs.append(PUBLISHED_REF)
    if ancestor:
        revs.append(ancestor)
    return {rel: {_blob_oid(root, rev, rel) for rev in revs} for rel in rels}


def _guard(
    cfg: Config,
    root: Path,
    rels: list[str],
    base: str,
    working: Mapping[str, bytes | None],
    union: set[str],
    baseline: Mapping[str, set[str | None]],
    expected: Mapping[str, str | None],
) -> dict[str, bytes | None]:
    """Refuse stale or sealed writes; return the bytes each path will land."""
    refusals: list[str] = []
    landed: dict[str, bytes | None] = dict(working)
    tickets = set(_ticket_rels(cfg, root, rels))
    # Git status names a dirty submodule by its directory. Reading that as
    # bytes returns None, which must never be interpreted as its deletion.
    gitlinks: set[str] = set()
    for rev in ("HEAD", base):
        entries = run_git(root, "ls-tree", "-r", "-z", rev)
        gitlinks.update(
            record.partition("\t")[2]
            for record in entries.split("\x00") if record.startswith("160000 ")
        )
    staged = run_git(root, "ls-files", "--stage", "-z")
    gitlinks.update(
        record.partition("\t")[2]
        for record in staged.split("\x00") if record.startswith("160000 ")
    )
    for rel in rels:
        data = working[rel]
        if rel in gitlinks:
            refusals.append(f"{rel}: is a submodule; publish its changes through Git review")
            continue
        if symlink_component(root / rel) is not None:
            # `_working_tree_bytes` follows links, so publishing one would land
            # its target's bytes — possibly from outside the repo — as a
            # regular file on control. Coga state is plain files only.
            refusals.append(
                f"{rel}: is a symlink or has a symlinked ancestor; "
                "replace it with regular files before publication"
            )
            continue
        if rel == relative_to_root(root, log_path(cfg)):
            if data is None and _blob_oid(root, base, rel) is not None:
                refusals.append(f"{rel}: append-only file is missing locally; restore it with `git checkout {cfg.git_remote}/{cfg.git_control_branch} -- {rel}` before publication")
            elif rel in expected and _blob_oid(root, base, rel) != expected[rel]:
                refusals.append(f"{rel}: control copy changed since it was read")
            continue
        if rel in union:
            # Union paths merge rather than overlay, so they need no
            # provenance — unless the writer decided something from control's
            # exact copy (a recurring create reading the serviced ledger).
            if data is None and _blob_oid(root, base, rel) is not None:
                # The union merge is skipped for a missing file, which would
                # publish its deletion; an append-only audit file is never
                # deleted through sync.
                refusals.append(
                    f"{rel}: append-only file is missing locally; restore it with "
                    f"`git checkout {cfg.git_remote}/{cfg.git_control_branch} -- {rel}` "
                    "rather than publishing its deletion"
                )
                continue
            if rel in expected and _blob_oid(root, base, rel) != expected[rel]:
                refusals.append(f"{rel}: control copy changed since it was read")
            continue
        if rel in tickets:
            reason = ticket_regression_reason(
                rel, control=tree_bytes(root, base, rel), working=data
            )
            if reason:
                refusals.append(reason)
                continue
        control_oid = _blob_oid(root, base, rel)
        working_oid = None if data is None else _hash_blob(root, data, rel)
        allowed = {expected[rel]} if rel in expected else baseline[rel] | {working_oid}
        if control_oid not in allowed:
            delta = ""
            if rel in tickets:
                theirs = _lifecycle(tree_bytes(root, base, rel))
                mine = _lifecycle(data)
                if theirs and mine:
                    delta = (
                        f" (control: status={theirs[0]!r} step={theirs[1]!r}; "
                        f"here: status={mine[0]!r} step={mine[1]!r})"
                    )
            refusals.append(
                f"{rel}: control copy changed since this checkout last saw it{delta}"
                f"; take control's copy with `git checkout "
                f"{cfg.git_remote}/{cfg.git_control_branch} -- {rel}` and redo the edit"
            )
    log_rel = relative_to_root(root, log_path(cfg))
    for reason in refusals:
        rel = reason.split(":", 1)[0]
        if log_rel in rels and working.get(log_rel) is None:
            # Logging would recreate the missing audit file as a one-line
            # truncation, which the next sweep could then publish; stderr
            # carries the refusal instead.
            break
        append_log(cfg, ref_tag_for_path(cfg, root / rel), "git", f"sync refused: {reason}")
    if refusals:
        raise StateRegressionError("; ".join(refusals))
    return landed


def ticket_regression_reason(
    rel: str, *, control: bytes | None, working: bytes | None
) -> str | None:
    """Why `working` may not replace `control` for a launch-claimed ticket.

    A control copy carrying `pending:<uuid>` is sealed while megalaunch holds
    the child: the only accepted replacement is the identical ticket with the
    prefix stripped (the admission the supervisor publishes after release). A
    working copy carrying `released:` is a local recovery witness and is never
    published. Everything else — step, status, prose — is the provenance check
    in `publish`, which needs no lifecycle rules once it has a real baseline.
    """
    working_ticket = _parse_ticket(working)
    if working_ticket is not None and released_launch_generation(
        working_ticket.launch_generation
    ):
        return f"{rel}: a released launch witness is local-only; `coga launch` reconciles it"
    control_ticket = _parse_ticket(control)
    if control_ticket is None or working == control:
        return None
    generation = control_ticket.launch_generation
    if not pending_launch_generation(generation):
        return None
    assert generation is not None
    admitted = Ticket(frontmatter=dict(control_ticket.frontmatter), body=control_ticket.body)
    admitted.frontmatter["launch_generation"] = admitted_launch_generation(generation)
    if working == admitted.render().encode("utf-8"):
        return None
    return (
        f"{rel}: pending launch admission {generation!r} cannot change "
        "before the held child is released"
    )


# --- prepared ticket transactions ---------------------------------------------
#
# A lifecycle command derives its transition from the ticket it reads. Reading
# only this checkout's copy lets a stale clone (a feature checkout, a dirty
# control checkout that cannot fast-forward) decide from old state and then
# have its write refused at publication. `prepare_ticket` reads control first:
# it fetches, pins the control commit, reconciles the local copy with control's
# copy over a proven shared base, and returns the reconciled ticket together
# with the exact control bytes it read. The caller validates and edits that
# view in memory, writes it once (`write_ticket(..., prepared=)` rechecks the
# local bytes), and publishes with the control bytes as its exact expectation.
# `coga/state-publication` ("Prepared ticket transactions") owns the contract.


class TicketConflictError(StateRegressionError):
    """Preparation could not reconcile the local ticket with control's copy.

    Raised before any transition is written. `status_conflict` marks the case
    where both sides changed `status:` and the lifecycle ordering cannot pick
    a winner (paused/blocked against another status, or done versus
    canceled) — reserved for a human decision.
    """

    def __init__(self, message: str, *, rel: str, status_conflict: bool = False) -> None:
        self.rel = rel
        self.status_conflict = status_conflict
        super().__init__(message)


class TicketChangedError(StateRegressionError):
    """The local ticket changed between preparation and the prepared write."""


@dataclass(frozen=True)
class ControlFetch:
    """The control revision a preparation may read, and how it was obtained.

    `state` is `fresh` (fetched just now from the configured remote), `local`
    (no remote is configured: local `<control>` is canonical), `missing` (the
    remote answered but has no control branch), or `failed` (the fetch could
    not run). Only `fresh` and `local` carry a revision a reader may call
    current; a remote-tracking ref left over from an earlier fetch is never
    reported as fresh.
    """

    state: Literal["fresh", "local", "missing", "failed"]
    revision: str | None = None
    detail: str = ""


def fetch_control_state(cfg: Config, root: Path) -> ControlFetch:
    """Fetch control and say whether the result is current."""
    remote, control = cfg.git_remote, cfg.git_control_branch
    if not remote_configured(root, remote):
        if _ref_present(root, f"refs/heads/{control}"):
            return ControlFetch(
                "local", run_git(root, "rev-parse", f"refs/heads/{control}").strip()
            )
        return ControlFetch("missing", detail=f"no local {control!r} branch")
    try:
        run_git(
            root, "fetch", "--quiet", remote,
            f"+refs/heads/{control}:refs/remotes/{remote}/{control}",
            env=_MESSAGE_LOCALE,
        )
    except GitError as exc:
        if "couldn't find remote ref" in str(exc).lower():
            return ControlFetch("missing", detail=f"{remote!r} has no {control!r} branch")
        return ControlFetch("failed", detail=str(exc))
    tip = run_git(root, "rev-parse", f"refs/remotes/{remote}/{control}").strip()
    return ControlFetch("fresh", tip)


@dataclass
class PreparedTicket:
    """One ticket read from fresh control and reconciled with this checkout.

    `ticket` is the reconciled view every eligibility check and edit must use.
    `local` is the exact working bytes preparation started from (`None` when
    absent); `write_ticket(..., prepared=)` refuses if the file no longer
    holds them, and advances it after each prepared write. `control` is the
    exact control copy read at `revision` — the publication expectation —
    and is meaningful only when `fresh`. `outcome` names what preparation
    did: `local` (no fresh control: today's local behavior), `same`,
    `adopted` (no unpublished local edit: control's copy), `kept` (only this
    checkout changed it), `merged`, or `new` (absent on control).
    """

    path: Path
    ticket: Ticket
    local: bytes | None
    control: bytes | None = None
    revision: str | None = None
    fresh: bool = False
    outcome: str = "local"

    def expect(self) -> dict[Path, bytes | None] | None:
        """The exact-control expectation for publication, or `None` offline."""
        if not self.fresh:
            return None
        return {self.path: self.control}


def local_ticket_preparation(path: Path) -> PreparedTicket:
    """A preparation that reads only this checkout (no control available)."""
    local = path.read_bytes()
    return PreparedTicket(path=path, ticket=Ticket.parse(local.decode("utf-8")), local=local)


def prepare_ticket(cfg: Config, path: Path) -> PreparedTicket:
    """Read control's copy of the ticket at `path` and reconcile it with ours.

    Offline, git-disabled, non-Git, and no-control checkouts get today's local
    read (reported once on stderr when a configured fetch could not run). A
    fresh read compares the local copy with control's over the newest shared
    snapshot this checkout provably derived from (`_shared_base`): no local
    edit adopts control, a one-sided edit keeps that side, and both-sided
    edits merge structurally (`merge_ticket_bytes`). Raises
    `TicketConflictError` when they cannot be reconciled; nothing is written.
    """
    if not cfg.git_enabled:
        return local_ticket_preparation(path)
    try:
        root = toplevel(cfg.repo_root)
    except GitError:
        return local_ticket_preparation(path)
    if root is None:
        return local_ticket_preparation(path)
    with state_lock(cfg):
        local = path.read_bytes()
        fetched = fetch_control_state(cfg, root)
        rel = relative_to_root(root, path)
        if fetched.state in ("missing", "failed"):
            sys.stderr.write(
                f"[git] could not read current control for {rel} "
                f"({fetched.detail}); using this checkout's copy\n"
            )
            return PreparedTicket(path=path, ticket=Ticket.parse(local.decode("utf-8")), local=local)
        rev = fetched.revision
        assert rev is not None
        control_oid = _blob_oid(root, rev, rel)
        control = tree_bytes(root, rev, rel) if control_oid is not None else None
        local_oid = _blob_id(root, local, rel)

        def result(data: bytes, outcome: str) -> PreparedTicket:
            try:
                ticket = Ticket.parse(data.decode("utf-8"))
            except (UnicodeDecodeError, TicketError) as exc:
                if data is local:
                    raise  # this checkout's own malformed ticket: the usual error
                raise TicketConflictError(
                    _conflict_message(cfg, rel, f"the reconciled ticket does not parse: {exc}"),
                    rel=rel,
                ) from exc
            return PreparedTicket(
                path=path, ticket=ticket, local=local, control=control,
                revision=rev, fresh=True, outcome=outcome,
            )

        if control_oid == local_oid:
            return result(local, "same")
        base_oid = _shared_base(root, rev, rel)
        if control is None:
            if base_oid is None:
                # Never published: the ordinary create path lands it.
                return result(local, "new")
            raise TicketConflictError(
                _conflict_message(cfg, rel, "control deleted this ticket after this checkout last shared it"),
                rel=rel,
            )
        if base_oid is None:
            raise TicketConflictError(
                _conflict_message(
                    cfg, rel,
                    "no shared copy proves where this checkout's ticket and control's diverged",
                ),
                rel=rel,
            )
        if local_oid == base_oid:
            return result(control, "adopted")
        if control_oid == base_oid:
            return result(local, "kept")
        merged = merge_ticket_bytes(
            rel, base=_blob_bytes(root, base_oid), local=local, control=control,
            conflict=lambda detail, status=False: TicketConflictError(
                _conflict_message(cfg, rel, detail, status_conflict=status),
                rel=rel, status_conflict=status,
            ),
        )
        return result(merged, "merged")


def _conflict_message(cfg: Config, rel: str, detail: str, *, status_conflict: bool = False) -> str:
    remedy = (
        "A human must decide which lifecycle status stands"
        if status_conflict else "Save or reconcile this checkout's local edits first"
    )
    return (
        f"{rel}: cannot reconcile this checkout's ticket with control: {detail}. "
        f"{remedy}; then take control's copy with `git checkout "
        f"{cfg.git_remote}/{cfg.git_control_branch} -- {rel}`, redo the edit, "
        "and retry. Nothing was written"
    )


def _blob_id(root: Path, data: bytes, rel: str) -> str:
    """The blob id `git add` would give `data` at `rel`, without writing it.

    Unlike `_hash_blob` this stores nothing, so preparation works where the
    object store is read-only.
    """
    result = _run(
        ["git", "-C", str(root), "hash-object", f"--path={rel}", "--stdin"], input=data,
    )
    if result.returncode != 0:
        raise GitError(
            f"`git hash-object --path={rel}` failed: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout.decode().strip()


def _shared_base(root: Path, rev: str, rel: str) -> str | None:
    """The newest copy of `rel` this checkout and control provably share.

    Candidates are this checkout's derivation sources (`_provenance`): its
    HEAD copy, the HEAD/control merge-base copy, and the copy this worktree
    last published (`PUBLISHED_REF`). A candidate counts only when control's
    own history of `rel` carried it, so an unpublished feature-branch commit
    stays a local edit. Among those, the one control carried most recently
    wins, ordered by control's commit history rather than timestamps: a later
    publication beats an older branch point, and a copy HEAD incorporated
    afterwards beats an older publication record. `None` when none is proven.
    """
    ancestor = _run(["git", "-C", str(root), "merge-base", "HEAD", rev]).stdout.decode().strip() or None
    candidates = {oid for oid in _provenance(root, [rel], ancestor)[rel] if oid is not None}
    if not candidates:
        return None
    for oid in _path_history_blobs(root, rev, rel):
        if oid in candidates:
            return oid
    return None


def _path_history_blobs(root: Path, rev: str, rel: str) -> Iterator[str]:
    """Each blob `rel` held in `rev`'s history, newest commit first."""
    current = _blob_oid(root, rev, rel)
    if current is not None:
        yield current
    out = run_git(
        root, "log", "--format=%x01", "--raw", "--no-abbrev", "--no-renames",
        rev, "--", rel, env={"GIT_LITERAL_PATHSPECS": "1"},
    )
    for line in out.splitlines():
        if not line.startswith(":"):
            continue
        meta, _, name = line.partition("\t")
        if name != rel:
            continue
        fields = meta.split()
        if len(fields) >= 4 and set(fields[3]) != {"0"}:
            yield fields[3]


_MISSING = object()
_LIFECYCLE_KEYS = ("status", "step")


def lifecycle_winner(
    mine: tuple[str | None, int | None], theirs: tuple[str | None, int | None],
    *, same_workflow: bool,
) -> Literal["mine", "theirs"] | None:
    """Which of two divergent lifecycle positions is demonstrably later.

    Ranked progress is draft, active, in_progress, then terminal; within one
    status and an unchanged frozen workflow, the higher numeric step. `None`
    when the ordering cannot decide: an unranked status (paused, blocked),
    tied terminal outcomes (done versus canceled), a changed workflow, or an
    unparseable step.
    """
    (my_status, my_step), (their_status, their_step) = mine, theirs
    if my_status != their_status:
        my_rank = _STATUS_RANK.get(my_status or "")
        their_rank = _STATUS_RANK.get(their_status or "")
        if my_rank is None or their_rank is None or my_rank == their_rank:
            return None
        return "mine" if my_rank > their_rank else "theirs"
    if not same_workflow or my_step is None or their_step is None or my_step == their_step:
        return None
    return "mine" if my_step > their_step else "theirs"


def merge_ticket_bytes(
    rel: str, *, base: bytes, local: bytes, control: bytes,
    conflict: Callable[..., Exception],
) -> bytes:
    """Three-way merge of a ticket's frontmatter and body.

    Frontmatter merges per key (absence is a value): identical sides agree,
    an unchanged side yields, and different edits of one key conflict. The
    frozen workflow is one routing value. `status`/`step` merge as one
    lifecycle position; when both sides moved it, `lifecycle_winner` picks
    the demonstrably later one as a whole (a terminal winner carries no
    step), and an undecidable status pair raises with `status=True`. The
    body, blackboard included, is a standard `git merge-file` three-way merge
    (never `--union`). `conflict(detail, status=False)` builds the exception.
    """
    tickets = []
    for label, data in (("shared base", base), ("local", local), ("control", control)):
        try:
            tickets.append(Ticket.parse(data.decode("utf-8")))
        except (UnicodeDecodeError, TicketError) as exc:
            raise conflict(f"the {label} copy does not parse ({exc})") from exc
    b, l, c = (ticket.frontmatter for ticket in tickets)
    keys = list(dict.fromkeys([*c, *l, *b]))
    merged: dict[str, Any] = {}
    conflicts: list[str] = []
    for key in keys:
        if key in _LIFECYCLE_KEYS:
            continue
        value = _merge_value(b.get(key, _MISSING), l.get(key, _MISSING), c.get(key, _MISSING))
        if value is _CONFLICT:
            conflicts.append(key)
        elif value is not _MISSING:
            merged[key] = value
    if conflicts:
        raise conflict("both sides changed " + ", ".join(f"`{key}`" for key in conflicts))
    position = tuple(
        tuple(fm.get(key, _MISSING) for key in _LIFECYCLE_KEYS) for fm in (b, l, c)
    )
    lifecycle = _merge_value(*position)
    if lifecycle is _CONFLICT:
        same_workflow = (
            b.get("workflow", _MISSING) == l.get("workflow", _MISSING)
            == c.get("workflow", _MISSING)
        )
        winner = lifecycle_winner(
            (l.get("status"), tickets[1].step_index()),
            (c.get("status"), tickets[2].step_index()),
            same_workflow=same_workflow,
        )
        if winner is None:
            status = l.get("status") != c.get("status")
            raise conflict(
                f"both sides moved its lifecycle (control: status={c.get('status')!r} "
                f"step={c.get('step')!r}; here: status={l.get('status')!r} "
                f"step={l.get('step')!r}) and neither is demonstrably later",
                status=status,
            )
        lifecycle = position[1] if winner == "mine" else position[2]
    for key, value in zip(_LIFECYCLE_KEYS, lifecycle):
        if value is not _MISSING:
            merged[key] = value
    # Keep control's key order; lifecycle keys return to their usual place.
    order = [key for key in keys if key in merged]
    frontmatter = {key: merged[key] for key in order}
    body = _merge_text(tickets[0].body, tickets[1].body, tickets[2].body)
    if body is None:
        raise conflict("the body or blackboard has overlapping edits")
    return Ticket(frontmatter=frontmatter, body=body).render().encode("utf-8")


_CONFLICT = object()


def _merge_value(base: Any, mine: Any, theirs: Any) -> Any:
    if mine == theirs:
        return mine
    if mine == base:
        return theirs
    if theirs == base:
        return mine
    return _CONFLICT


def _merge_text(base: str, mine: str, theirs: str) -> str | None:
    """`git merge-file` of three texts; `None` on any overlapping edit."""
    if mine == theirs or theirs == base:
        return mine
    if mine == base:
        return theirs
    with tempfile.TemporaryDirectory(prefix="coga-ticket-merge-") as tmp:
        files = [Path(tmp) / name for name in ("local", "base", "control")]
        for path, text in zip(files, (mine, base, theirs)):
            path.write_bytes(text.encode("utf-8"))
        result = _run(["git", "merge-file", "-p", *map(str, files)])
    if result.returncode != 0:
        if result.returncode < 0 or result.returncode > 127:
            raise GitError(
                f"`git merge-file` failed (exit {result.returncode}): "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
        return None
    return result.stdout.decode("utf-8")


def _build_tree(
    root: Path,
    base: str,
    rels: list[str],
    working: Mapping[str, bytes | None],
    union: set[str],
    ancestor: str | None,
    landed: dict[str, bytes | None],
) -> str:
    """`base`'s tree with `rels` overlaid (union-merged for `merge=union` paths)."""
    fd, index = tempfile.mkstemp(prefix="coga-git-index-")
    os.close(fd)
    os.unlink(index)
    env = {"GIT_INDEX_FILE": index}
    index_modes = _index_modes(root) if os.name != "posix" else {}
    try:
        run_git(root, "read-tree", base, env=env)
        for rel in rels:
            data = landed[rel]
            if rel in union and data is not None:
                data = _merge_union_bytes(
                    current=tree_bytes(root, base, rel) or b"",
                    base=(tree_bytes(root, ancestor, rel) or b"") if ancestor else b"",
                    other=_clean_bytes(root, data, rel),
                )
                landed[rel] = data
            run_git(root, "rm", "-rf", "--cached", "--ignore-unmatch", "--", rel, env=env)
            if data is not None:
                mode = (
                    "100755" if os.access(root / rel, os.X_OK) else "100644"
                ) if os.name == "posix" else index_modes.get(rel, "100644")
                run_git(
                    root, "update-index", "--add", "--cacheinfo",
                    mode, _hash_blob(root, data, rel), rel, env=env,
                )
        return run_git(root, "write-tree", env=env).strip()
    finally:
        try:
            os.unlink(index)
        except FileNotFoundError:
            pass


def _merge_union_bytes(*, current: bytes, base: bytes, other: bytes) -> bytes:
    """`git merge-file --union` of the three copies, minus re-added lines.

    A union-merged publication never increases the occurrence count of a
    line already on control (`current`); see `coga-dev/internals/spool-merge`.
    Pass `other` through `_clean_bytes` first so all three copies compare in
    the blob form control stores.
    """
    with tempfile.TemporaryDirectory(prefix="coga-union-merge-") as tmp:
        files = [Path(tmp) / name for name in ("current", "base", "other")]
        for path, data in zip(files, (current, base, other)):
            path.write_bytes(data)
        result = _run(["git", "merge-file", "--union", *map(str, files)])
        if result.returncode != 0:
            raise GitError(
                f"`git merge-file --union` failed (exit {result.returncode}): "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
        return _drop_reinserted_lines(current, files[0].read_bytes())


def _drop_reinserted_lines(current: bytes, merged: bytes) -> bytes:
    """`merged` with each line of `current` capped at its count there.

    A line on control keeps `min(control count, merged count)` occurrences; a
    new line keeps all of them. When `merged` holds all of `current` as a
    subsequence, its earliest such embedding is kept; otherwise the earliest
    occurrences within each cap are. Lines keep their ends, so the result is
    a subsequence of `merged` and never splits a line.
    """
    control = _lf_lines(current)
    lines = _lf_lines(merged)
    protected: set[int] = set()
    cursor = 0
    for index, line in enumerate(lines):
        if cursor < len(control) and line == control[cursor]:
            protected.add(index)
            cursor += 1
    if cursor < len(control):
        protected = set()
    counts = Counter(control)
    budget = counts - Counter(lines[index] for index in protected)
    kept: list[bytes] = []
    for index, line in enumerate(lines):
        if index in protected or line not in counts:
            kept.append(line)
        elif budget[line] > 0:
            budget[line] -= 1
            kept.append(line)
    return b"".join(kept)


def _lf_lines(data: bytes) -> list[bytes]:
    """`data` split after each LF, keeping ends.

    `git merge-file` delimits lines by LF only; `bytes.splitlines` would also
    split at a bare CR, which Git treats as content within a line.
    """
    lines = [line + b"\n" for line in data.split(b"\n")]
    lines[-1] = lines[-1][:-1]
    return lines if lines[-1] else lines[:-1]


def _push(root: Path, remote: str, refspec: str) -> str | None:
    """Push; return `None` on success, else the (redacted) failure text."""
    result = _run(["git", "-C", str(root), "push", "--quiet", remote, refspec])
    if result.returncode == 0:
        return None
    text = (result.stderr + result.stdout).decode(errors="replace").strip()
    return _redact(text, (remote, refspec))


def _control_carries(root: Path, remote: str, control: str, new: str) -> bool:
    """After an ambiguous push failure: did the server take `new` anyway?"""
    _fetch_control(root, remote, control)
    tip = run_git(root, "rev-parse", f"refs/remotes/{remote}/{control}").strip()
    return tip == new or _is_ancestor(root, new, tip)


def _record_published(root: Path, blobs: Mapping[str, str | None]) -> None:
    """Remember the blobs this worktree just published (see `PUBLISHED_REF`)."""
    try:
        _write_published(root, blobs)
    except GitError as exc:
        sys.stderr.write(f"[git] note: could not record published blobs: {exc}\n")


def record_projected_baseline(cfg: Config, root: Path, rel: str, oid: str) -> None:
    """Strictly remember one verified, projected control blob as provenance.

    Checkout preparation projects a ticket from a verified control revision
    onto a feature branch. The blob is a copy this worktree derived its
    working file from, exactly like one it published, so later publication
    of that ticket (a bump from another process) may land over it while a
    competing control change still refuses. Unlike `_record_published`,
    failure raises, and the entry is read back before returning: launch must
    not admit an agent whose handoff it cannot publish. Other entries are
    preserved.
    """
    with state_lock(cfg):
        _write_published(root, {rel: oid})
        if _blob_oid(root, PUBLISHED_REF, rel) != oid:
            raise GitError(
                f"{PUBLISHED_REF} does not record {rel} at {oid} after writing it"
            )


def _write_published(root: Path, blobs: Mapping[str, str | None]) -> None:
    fd, index = tempfile.mkstemp(prefix="coga-git-index-")
    os.close(fd)
    os.unlink(index)
    env = {"GIT_INDEX_FILE": index}
    try:
        if _ref_present(root, PUBLISHED_REF):
            run_git(root, "read-tree", PUBLISHED_REF, env=env)
        else:
            run_git(root, "read-tree", "--empty", env=env)
        for rel, oid in blobs.items():
            run_git(root, "rm", "-f", "--cached", "--ignore-unmatch", "--", rel, env=env)
            if oid is not None:
                run_git(root, "update-index", "--add", "--cacheinfo", "100644", oid, rel, env=env)
        run_git(root, "update-ref", PUBLISHED_REF, run_git(root, "write-tree", env=env).strip())
    finally:
        try:
            os.unlink(index)
        except FileNotFoundError:
            pass


# --- integrate ----------------------------------------------------------------


def fast_forward_control(
    cfg: Config, root: Path, new: str, *,
    staged: Mapping[str, tuple[bytes | None, bytes | None]] | None = None,
    log_mutation: "LogMutation | None" = None,
) -> bool:
    from coga import log_transaction
    with state_lock(cfg):
        log_transaction.ensure_clear(cfg, log_mutation)
        return _fast_forward_control_locked(cfg, root, new, staged=staged)


def _fast_forward_control_locked(
    cfg: Config,
    root: Path,
    new: str,
    *,
    staged: Mapping[str, tuple[bytes | None, bytes | None]] | None = None,
) -> bool:
    """Move the local control branch to `new`: fast-forward, or realign.

    Ancestry is checked first. When local control is behind `new`, this is a
    fast-forward: another worktree holding the branch moves through `merge
    --ff-only`; with no holder the ref moves directly under an old-value
    guard. When local control is ahead or diverged, it *realigns* only when
    `_local_control_subsumed` proves every local-only commit is Coga state
    whose content `new` already carries; the invoking checkout must have no
    Git operation in progress, a control branch held by another worktree is
    left alone, and the dropped commits are named on stderr (they stay in the
    reflog). Local control that already contains `new` and is itself
    contained in the remote-tracking ref moved forward under the caller (a
    concurrent publish): it is level, and is left alone. Anything else is
    left alone with one stderr line naming the fix.
    When this checkout holds the branch, `staged` — path → (bytes read,
    bytes landed) — lets a file this process just published be brought to its
    landed bytes and staged, so the move is not refused by the very edit it
    carries; a file a peer changed meanwhile is left dirty for the next sweep.
    """
    control = cfg.git_control_branch
    ref = f"refs/heads/{control}"
    if not _ref_present(root, ref):
        return True
    local = run_git(root, "rev-parse", ref).strip()
    if local == new:
        return True
    if not _is_ancestor(root, local, new):
        if _is_ancestor(root, new, local) and _published_control(cfg, root, local):
            # A peer (another process, or a sibling worktree sharing the ref)
            # published past `new` between our read of control and this one.
            return True
        return _realign_control(cfg, root, local, new, staged)
    try:
        holder = worktree_holding_branch(root, control)
    except GitError as exc:
        sys.stderr.write(f"[git] note: local {control!r} not fast-forwarded: {exc}\n")
        return False
    if holder is None:
        try:
            run_git(root, "update-ref", ref, new, local)
        except GitError as exc:
            sys.stderr.write(f"[git] note: local {control!r} not fast-forwarded: {exc}\n")
            return False
        return True
    if holder.resolve() == root.resolve() and not _stage_landed(cfg, root, staged, revision=new):
        return False
    try:
        holder_cfg = replace(cfg, repo_root=holder / cfg.repo_root.resolve().relative_to(root.resolve()))
        with state_lock(holder_cfg, blocking=False):
            from coga.log_transaction import pending
            if holder.resolve() != root.resolve() and pending(holder_cfg):
                return False
            result = _run(
                ["git", "-C", str(holder), "merge", "--ff-only", "--quiet", new],
                env=_MESSAGE_LOCALE,
            )
    except GitError as exc:
        sys.stderr.write(f"[git] note: control checkout left for its own locked catch-up: {exc}\n")
        return False
    if result.returncode != 0:
        sys.stderr.write(
            f"[git] note: local {control!r} in {holder} not fast-forwarded: "
            f"{summarize_git_failure(result.stderr.decode(errors='replace'))}\n"
        )
        return False
    return True


def _published_control(cfg: Config, root: Path, commit: str) -> bool:
    """Whether `commit` is on the remote-tracking control ref as last observed."""
    remote_ref = f"refs/remotes/{cfg.git_remote}/{cfg.git_control_branch}"
    if not _ref_present(root, remote_ref):
        return False
    return _is_ancestor(root, commit, run_git(root, "rev-parse", remote_ref).strip())


def _stage_landed(
    cfg: Config,
    root: Path,
    staged: Mapping[str, tuple[bytes | None, bytes | None]] | None,
    *, revision: str,
) -> bool:
    """Stage landed files only after proving no distinct index copy is lost.

    Publication reads working files, not the user's index. Check the entire
    set before writing even its first path; a later staged draft must not
    leave earlier paths partially cleaned. Exact mode/blob equality with
    HEAD or the landed revision is required, including for union files.
    """
    try:
        if staged:
            literal = {"GIT_LITERAL_PATHSPECS": "1"}
            head = run_git(root, "rev-parse", "HEAD").strip()
            argv = ("ls-files", "--stage", "-z", "--", *staged)
            snapshot = run_git(root, *argv, env=literal)
            entries: dict[str, tuple[str, str]] = {}
            for record in snapshot.split("\x00"):
                if not record:
                    continue
                meta, rel = record.split("\t", 1)
                mode, oid, stage = meta.split()
                if stage != "0":
                    raise GitError(f"{rel}: unmerged index; staged work preserved")
                entries[rel] = (mode, oid)
            for rel in staged:
                entry = entries.get(rel)
                if entry not in (_tree_entry(root, head, rel), _tree_entry(root, revision, rel)):
                    raise GitError(
                        f"{rel}: staged copy differs from HEAD and publication result; "
                        "index and checkout preserved for reconciliation"
                    )
            if snapshot != run_git(root, *argv, env=literal) or head != run_git(root, "rev-parse", "HEAD").strip():
                raise GitError("index or HEAD changed while examining landed files; retry")
        for rel, (read, landed) in (staged or {}).items():
            if _working_tree_bytes(root, rel) != read:
                continue
            # A guarded trim already installed the exact surviving bytes.
            # The committed log is clean-filtered (usually LF), so preserve
            # the local postimage when it represents that same blob.
            equivalent_log = (
                rel == relative_to_root(root, log_path(cfg))
                and read is not None
                and landed is not None
                and _clean_bytes(root, read, rel) == landed
            )
            if landed is not None and not equivalent_log:
                from coga.atomicio import atomic_write_bytes
                atomic_write_bytes(root / rel, landed)
            if landed is None:
                run_git(root, "update-index", "--remove", "--", rel)
            else:
                run_git(root, "add", "--all", "--", rel, env={"GIT_LITERAL_PATHSPECS": "1"})
    except (GitError, OSError) as exc:
        sys.stderr.write(f"[git] note: local {cfg.git_control_branch!r} not moved: {exc}\n")
        return False
    return True


def _realign_control(
    cfg: Config,
    root: Path,
    local: str,
    new: str,
    staged: Mapping[str, tuple[bytes | None, bytes | None]] | None,
) -> bool:
    """`fast_forward_control`'s path for an ahead or diverged local control."""
    control, remote = cfg.git_control_branch, cfg.git_remote
    ref = f"refs/heads/{control}"
    try:
        operation = _operation_in_progress(root)
    except GitError as exc:
        sys.stderr.write(
            f"[git] note: local {control!r} not realigned: could not inspect "
            f"{root} for an in-progress Git operation: {exc}\n"
        )
        return False
    if operation is not None:
        sys.stderr.write(
            f"[git] note: local {control!r} not realigned to {remote}/{control}: "
            f"{operation} is in progress in {root}; finish or abort it and retry\n"
        )
        return False
    verdict = _local_control_subsumed(cfg, root, local, new)
    if verdict.kind != "ok":
        sys.stderr.write(f"[git] note: {_divergence_message(cfg, verdict, on_control=True)}\n")
        return False
    try:
        holder = worktree_holding_branch(root, control)
        if holder is not None and holder.resolve() != root.resolve():
            sys.stderr.write(
                f"[git] note: local {control!r} in {holder} has commits not on "
                f"{remote}/{control}; left alone — realign it from that checkout\n"
            )
            return False
        if holder is not None:
            if not _stage_landed(cfg, root, staged, revision=new):
                return False
            run_git(root, "read-tree", "-m", "-u", "HEAD", new)
        run_git(
            root, "update-ref", "-m", f"coga: realign to {remote}/{control}",
            ref, new, local,
        )
    except GitError as exc:
        sys.stderr.write(f"[git] note: local {control!r} not realigned: {exc}\n")
        return False
    _report_realignment(cfg, verdict, new)
    return True


def refresh(cfg: Config) -> bool:
    """Make a control checkout equal to `<remote>/<control>`.

    Fetches, then fast-forwards (or realigns, see `fast_forward_control`) when
    HEAD is the control branch; it never publishes. A feature
    or detached checkout is stale-by-design for tickets other checkouts
    advance: the fetch still lands (so `coga status` can warn) but no file
    moves, and the result is `True`. `False` means the control checkout could
    not be brought level; the reason was written to stderr.
    """
    if not cfg.git_enabled:
        return True
    try:
        root = toplevel(cfg.repo_root)
        if root is None or not remote_configured(root, cfg.git_remote):
            return True
        if not control_branch_present(root, cfg.git_control_branch, cfg.git_remote):
            return True
        _fetch_control(root, cfg.git_remote, cfg.git_control_branch)
        remote_ref = f"refs/remotes/{cfg.git_remote}/{cfg.git_control_branch}"
        if current_branch(root) != cfg.git_control_branch or not _ref_present(root, remote_ref):
            return True
        return fast_forward_control(cfg, root, run_git(root, "rev-parse", remote_ref).strip())
    except GitError as exc:
        sys.stderr.write(f"[git] refresh failed: {exc}\n")
        append_log(cfg, ref_tag_for_path(cfg, cfg.repo_root), "git", f"refresh failed: {exc}")
        return False


# --- checkout preparation -----------------------------------------------------

CheckoutPreparationKind = Literal["prepared", "exempt", "refused", "failed"]

# Git's own markers for an operation that owns the index until it finishes.
_IN_PROGRESS_MARKERS = (
    ("MERGE_HEAD", "a merge"),
    ("CHERRY_PICK_HEAD", "a cherry-pick"),
    ("REVERT_HEAD", "a revert"),
    ("rebase-merge", "a rebase"),
    ("rebase-apply", "a rebase or `git am`"),
    ("BISECT_LOG", "a bisect"),
)
_REGULAR_MODES = frozenset({"100644", "100755"})
_ABSENT_MODE = "000000"


@dataclass(frozen=True)
class CheckoutObservation:
    """Diagnostic evidence only; never an additional permission to clean."""

    path: str
    state: bool
    untracked: bool = False
    index: Literal["head", "control", "differs", "unknown"] = "unknown"
    working: Literal["matches", "published", "differs", "unknown"] = "unknown"


@dataclass(frozen=True)
class CheckoutPreparation:
    """`prepare_control_checkout`'s verdict on the invoking checkout.

    - `"prepared"` — HEAD is the control branch at `commit`, the fetched
      remote control tip, and the tree is clean.
    - `"exempt"` — Git sync disabled, not a checkout, no remote, or the remote
      has no control branch yet: nothing was examined or moved, and no
      freshness is claimed.
    - `"refused"` — a safety check failed before anything changed HEAD, the
      index, working files, or local branches (the fetch may still have
      updated the remote-tracking ref). `blocking` names the paths or branch
      and `reason` the remedy.
    - `"failed"` — an unexpected Git or I/O error after mutation began;
      `reason` says exactly where the routine stopped. Nothing is rolled back.
    """

    kind: CheckoutPreparationKind
    reason: str = ""
    commit: str | None = None
    blocking: tuple[str, ...] = ()
    observations: tuple[CheckoutObservation, ...] = ()
    branch: str | None = None


@dataclass(frozen=True)
class _PreparationPlan:
    branch: str
    local_control: str
    restore: tuple[str, ...]
    remove: tuple[str, ...]
    evidence: tuple[object, ...]
    realign: _Subsumption | None = None


SubsumptionKind = Literal["ok", "foreign", "unpublished", "unproven"]


@dataclass(frozen=True)
class _Subsumption:
    """`_local_control_subsumed`'s verdict on local control's own commits.

    - `"ok"` — every local-only commit touches only Coga state and its net
      change is already on the target: the local ref may move to the target.
    - `"foreign"` — some local-only commit touches a path outside the state
      areas; `blocking` names those paths.
    - `"unpublished"` — the commits are state-only, but `blocking` lists the
      paths whose content is not yet on the target, each with why.
    - `"unproven"` — no single merge base, an unsupported entry (symlink,
      submodule), or a failed Git probe; `reason` names what failed.

    `dropped` is `(commit, subject)` per local-only commit, oldest first;
    `evidence` is everything the verdict was decided from.
    """

    kind: SubsumptionKind
    reason: str = ""
    blocking: tuple[str, ...] = ()
    dropped: tuple[tuple[str, str], ...] = ()
    evidence: tuple[object, ...] = ()


def prepare_control_checkout(
    cfg: Config, *, require_remote_control: bool = False,
    previous_contexts_root: Path | None = None,
) -> CheckoutPreparation:
    """Bring the invoking checkout to a clean control branch at the fetched tip.

    Confined to this one checkout: a sibling worktree is never switched,
    fast-forwarded, or cleaned. The fetched `<remote>/<control>` commit is
    pinned under the same `state_lock` hold as the plan; when the tracking ref
    moves past the pin before the plan is applied (a sibling worktree's
    publish), it is re-pinned and re-planned, a bounded number of times.
    Local control must exist and be equal to or behind it, or
    carry only commits `_local_control_subsumed` proves are Coga state already
    on the pinned tip (it is then realigned, not merged); a detached HEAD, an
    in-progress Git operation, or control checked out in another worktree
    refuses. Every staged, tracked, and untracked change in
    the checkout is examined: only files under `coga_root_paths` (the Coga
    root and the contexts root) may be cleaned, and only when their
    existence, mode, and content already match the pinned tree (a
    `merge=union` file when union-merging it onto that tree changes nothing),
    with any staged copy equal to HEAD's or the published one. Ignored files
    are never candidates, and one the move would overwrite refuses. The whole
    plan is validated and then re-observed before the first mutation. Only a
    published forward move of local control (and HEAD when on control) may
    re-plan within the same bound; other changed evidence refuses.
    Only then are proven paths restored to HEAD or removed,
    HEAD switched to control, and control fast-forwarded — or realigned with
    `read-tree -m -u` and an old-value-guarded `update-ref`, naming the
    dropped commits on stderr. Never stashes, rebases, resets, force-switches,
    commits, deletes a branch, or publishes anything.

    `require_remote_control` is for a boundary after a prepared entry: a
    remote or control ref that disappeared mid-run is refused rather than
    newly exempted.
    """
    if not cfg.git_enabled:
        return CheckoutPreparation("exempt", "Git sync is disabled")
    remote, control = cfg.git_remote, cfg.git_control_branch
    try:
        root = toplevel(cfg.repo_root)
        if root is None:
            return CheckoutPreparation("exempt", "not a Git checkout")
        if not remote_configured(root, remote):
            if require_remote_control:
                return CheckoutPreparation(
                    "refused", f"remote {remote!r} is no longer configured"
                )
            return CheckoutPreparation("exempt", f"no {remote!r} remote configured")
        # Pin and plan under one lock hold, so a publish from this checkout
        # cannot move local control past a stale pin in between.
        with state_lock(cfg):
            _fetch_control(root, remote, control)
            remote_ref = f"refs/remotes/{remote}/{control}"
            if not _ref_present(root, remote_ref):
                if require_remote_control:
                    return CheckoutPreparation(
                        "refused", f"{remote}/{control} no longer exists"
                    )
                return CheckoutPreparation("exempt", f"{remote}/{control} does not exist")
            pinned = run_git(root, "rev-parse", remote_ref).strip()
            # A sibling worktree publishes under its own lock but moves the
            # shared control refs: a tracking ref that moved past the pin
            # re-pins and re-plans instead of refusing or applying stale.
            for _attempt in range(PREPARATION_ATTEMPTS):
                plan = _plan_preparation(cfg, root, pinned, previous_contexts_root)
                moved = _moved_pin(root, remote_ref, pinned)
                if moved is not None:
                    pinned = moved
                    continue
                if isinstance(plan, CheckoutPreparation):
                    return plan
                # Re-observe immediately before mutating. A sibling's local
                # fast-forward can lag its push; retry that published advance,
                # but refuse other changed evidence instead of discarding it.
                again = _plan_preparation(cfg, root, pinned, previous_contexts_root)
                moved = _moved_pin(root, remote_ref, pinned)
                if moved is not None:
                    pinned = moved
                    continue
                if isinstance(again, CheckoutPreparation):
                    return again
                if again.evidence != plan.evidence:
                    if _only_published_control_advanced(root, control, pinned, plan, again):
                        continue
                    return CheckoutPreparation(
                        "refused",
                        "the checkout changed while it was being examined; retry",
                    )
                return _apply_preparation(cfg, root, pinned, plan, previous_contexts_root)
            return CheckoutPreparation(
                "refused",
                "control refs kept moving while the checkout was being examined; retry",
            )
    except GitError as exc:
        return CheckoutPreparation("refused", f"could not inspect the checkout: {exc}")


def _moved_pin(root: Path, remote_ref: str, pinned: str) -> str | None:
    """The remote-tracking control commit when it is no longer `pinned`."""
    if not _ref_present(root, remote_ref):
        return None
    current = run_git(root, "rev-parse", remote_ref).strip()
    return None if current == pinned else current


def _only_published_control_advanced(
    root: Path, control: str, pinned: str,
    plan: _PreparationPlan, again: _PreparationPlan,
) -> bool:
    """Retry a peer's delayed fast-forward without accepting other changed evidence."""
    if plan.local_control == again.local_control:
        return False
    branch, head, _local, *state = plan.evidence
    new_branch, new_head, _new_local, *new_state = again.evidence
    if branch != new_branch or state != new_state:
        return False
    if branch == control:
        # HEAD must follow the same control move in both observations.
        if head != plan.local_control or new_head != again.local_control:
            return False
    elif head != new_head:
        return False
    return (
        _is_ancestor(root, plan.local_control, again.local_control)
        and _is_ancestor(root, again.local_control, pinned)
    )


def _plan_preparation(
    cfg: Config, root: Path, pinned: str, previous_contexts_root: Path | None = None,
) -> _PreparationPlan | CheckoutPreparation:
    """Every check `prepare_control_checkout` makes before its first write."""
    from coga import log_transaction
    if log_transaction.pending(cfg):
        return CheckoutPreparation("refused", "pending audit mutation; rerun trim-log to recover before returning checkout", blocking=("log.md",))
    remote, control = cfg.git_remote, cfg.git_control_branch
    branch = symbolic_head(root)
    if branch is None:
        head = run_git(root, "rev-parse", "--short", "HEAD").strip()
        return CheckoutPreparation(
            "refused",
            f"HEAD is detached at {head}; switch to a branch "
            f"(`git switch {control}`) and retry",
            blocking=("HEAD",),
        )
    operation = _operation_in_progress(root)
    if operation is not None:
        return CheckoutPreparation(
            "refused",
            f"{operation} is in progress on {branch!r}; finish or abort it and retry",
            blocking=(branch,),
        )
    control_ref = f"refs/heads/{control}"
    if not _ref_present(root, control_ref):
        return CheckoutPreparation(
            "refused",
            f"local branch {control!r} does not exist; create it with "
            f"`git branch {control} {remote}/{control}` and retry",
            blocking=(control,),
        )
    local = run_git(root, "rev-parse", control_ref).strip()
    realign: _Subsumption | None = None
    if local != pinned and not _is_ancestor(root, local, pinned):
        realign = _local_control_subsumed(cfg, root, local, pinned, previous_contexts_root)
        if realign.kind != "ok":
            return CheckoutPreparation(
                "refused",
                _divergence_message(cfg, realign, on_control=branch == control),
                blocking=(control, *(() if realign.kind == "foreign" else realign.blocking)),
            )
    holder = worktree_holding_branch(root, control)
    if holder is not None and holder.resolve() != root.resolve():
        return CheckoutPreparation(
            "refused",
            f"{control!r} is checked out in another worktree ({holder}); switch "
            f"it off {control!r} or `git worktree remove {holder}` and retry",
            blocking=(str(holder),),
        )

    status = run_git(
        root,
        "status", "--porcelain=v2", "-z", "--untracked-files=all",
        "--no-renames", "--ignore-submodules=none",
    )
    areas = _state_areas(cfg, root, previous_contexts_root)
    union = set()
    restore: list[str] = []
    remove: list[str] = []
    blocking: list[str] = []
    observations: list[CheckoutObservation] = []
    candidate_bytes: dict[str, bytes | None] = {}
    entries = _status_v2_entries(status)
    index_modes = _index_modes(root) if entries and os.name != "posix" else None
    paths = [rel for _kind, _fields, rel in entries]
    if paths:
        union = union_merge_paths(root, paths)
    for kind, fields, rel in entries:
        observation = CheckoutObservation(rel, _in_areas(rel, areas), untracked=kind == "?")
        observations.append(observation)
        if kind == "u" or kind == "2":
            blocking.append(f"{rel} (unmerged or renamed index entry)")
            continue
        if not _in_areas(rel, areas):
            blocking.append(f"{rel} (not Coga state)")
            continue
        working = _regular_working_file(root, rel, index_modes=index_modes)
        published = _tree_entry(root, pinned, rel)
        if kind == "?":
            if working is False:
                blocking.append(f"{rel} (not a regular file)")
                continue
            proof = _published_proof(
                root, rel, working, published, head_entry=None, union=rel in union, cfg=cfg, revision=pinned
            )
            observations[-1] = replace(observation, working=_working_observation(root, rel, working, published, proof))
            if proof:
                blocking.append(f"{rel} ({proof})")
                continue
            remove.append(rel)
            candidate_bytes[rel] = working[1] if working else None
            continue
        # kind == "1": XY sub mH mI mW hH hI
        sub, mode_head, mode_index, mode_work, oid_head, oid_index = fields[2:8]
        if sub != "N...":
            blocking.append(f"{rel} (submodule)")
            continue
        modes = {mode_head, mode_index, mode_work} - {_ABSENT_MODE}
        if not modes <= _REGULAR_MODES or working is False:
            blocking.append(f"{rel} (symlink, submodule, or non-regular file)")
            continue
        head_entry = None if mode_head == _ABSENT_MODE else (mode_head, oid_head)
        index_entry = None if mode_index == _ABSENT_MODE else (mode_index, oid_index)
        proof = _published_proof(
            root, rel, working, published, head_entry=head_entry, union=rel in union, cfg=cfg, revision=pinned
        )
        index = "head" if index_entry == head_entry else "control" if index_entry == published else "differs"
        observations[-1] = replace(
            observation, index=index,
            working=_working_observation(root, rel, working, published, proof),
        )
        if index == "differs":
            blocking.append(f"{rel} (staged content is not the published version)")
            continue
        if proof:
            blocking.append(f"{rel} ({proof})")
            continue
        (restore if head_entry is not None else remove).append(rel)
        candidate_bytes[rel] = working[1] if working else None
    if blocking:
        return CheckoutPreparation(
            "refused",
            "uncommitted changes would be lost by moving to "
            f"{control!r}; inspect and reconcile the retained versions before retrying",
            blocking=tuple(blocking),
            commit=pinned, branch=branch, observations=tuple(observations),
        )

    collisions = _ignored_collisions(root, ["HEAD", local, pinned])
    if collisions:
        return CheckoutPreparation(
            "refused",
            f"ignored files would be overwritten by moving to {remote}/{control}; "
            "move them aside and retry",
            blocking=tuple(collisions),
            commit=pinned, branch=branch,
            observations=tuple(
                CheckoutObservation(rel, _in_areas(rel, areas), untracked=True)
                for rel in collisions
            ),
        )
    head_oid = run_git(root, "rev-parse", "HEAD").strip()
    evidence = (
        branch,
        head_oid,
        local,
        status,
        tuple(sorted((rel, _digest(data)) for rel, data in candidate_bytes.items())),
        realign.evidence if realign is not None else None,
    )
    return _PreparationPlan(branch, local, tuple(restore), tuple(remove), evidence, realign)


def _working_observation(
    root: Path, rel: str, working: tuple[str, bytes] | None,
    published: tuple[str, str] | None, proof: str | None,
) -> Literal["matches", "published", "differs"]:
    if proof is not None:
        return "differs"
    entry = (working[0], _hash_blob(root, working[1], rel)) if working else None
    return "matches" if entry == published else "published"


def _apply_preparation(
    cfg: Config, root: Path, pinned: str, plan: _PreparationPlan,
    previous_contexts_root: Path | None = None,
) -> CheckoutPreparation:
    """Mutate in order; on an unexpected failure, say where it stopped."""
    control = cfg.git_control_branch
    literal = {"GIT_LITERAL_PATHSPECS": "1"}
    stage = "restoring published Coga state to HEAD"
    try:
        if plan.restore:
            run_git(
                root, "restore", "--source=HEAD", "--staged", "--worktree",
                "--", *plan.restore, env=literal,
            )
        stage = "removing published untracked Coga state"
        areas = _state_areas(cfg, root, previous_contexts_root)
        for rel in plan.remove:
            run_git(
                root, "rm", "--cached", "--quiet", "--ignore-unmatch", "--", rel,
                env=literal,
            )
            (root / rel).unlink(missing_ok=True)
            _prune_empty_parents(root, rel, areas)
        if plan.realign is not None:
            if plan.branch == control:
                stage = f"realigning the working tree to {pinned[:12]}"
                run_git(root, "read-tree", "-m", "-u", "HEAD", pinned)
            stage = f"realigning {control!r} to {pinned[:12]}"
            run_git(
                root, "update-ref", "-m", f"coga: realign to {cfg.git_remote}/{control}",
                f"refs/heads/{control}", pinned, plan.local_control,
            )
            _report_realignment(cfg, plan.realign, pinned)
        if plan.branch != control:
            stage = f"switching from {plan.branch!r} to {control!r}"
            run_git(root, "switch", "--quiet", control)
        if plan.realign is None and plan.local_control != pinned:
            stage = f"fast-forwarding {control!r} to {pinned[:12]}"
            run_git(root, "merge", "--ff-only", "--quiet", pinned)
        stage = "verifying the prepared checkout"
        head = run_git(root, "rev-parse", "HEAD").strip()
        dirty = run_git(root, "status", "--porcelain", "--untracked-files=all").strip()
        if symbolic_head(root) != control or head != pinned or dirty:
            return CheckoutPreparation(
                "failed",
                f"stopped while {stage}: expected a clean {control!r} at "
                f"{pinned[:12]}, found {symbolic_head(root) or 'detached HEAD'} "
                f"at {head[:12]}" + (f" with changes:\n{dirty}" if dirty else ""),
                blocking=tuple(line[3:] for line in dirty.splitlines()),
            )
    except (GitError, OSError) as exc:
        return CheckoutPreparation("failed", f"stopped while {stage}: {exc}")
    return CheckoutPreparation("prepared", commit=pinned)


def _status_v2_entries(out: str) -> list[tuple[str, list[str], str]]:
    """`(kind, fields, path)` per `git status --porcelain=v2 -z --no-renames` record."""
    entries: list[tuple[str, list[str], str]] = []
    records = out.split("\x00")
    i = 0
    while i < len(records):
        record = records[i]
        i += 1
        if not record or record.startswith("#"):
            continue
        kind = record[0]
        if kind in "?!":
            entries.append((kind, [], record[2:]))
        elif kind == "1":
            fields = record.split(" ", 8)
            entries.append((kind, fields, fields[8]))
        elif kind == "2":
            fields = record.split(" ", 9)
            entries.append((kind, fields, fields[9]))
            i += 1  # the rename source
        elif kind == "u":
            fields = record.split(" ", 10)
            entries.append((kind, fields, fields[10]))
    return entries


def _state_areas(
    cfg: Config, root: Path, previous_contexts_root: Path | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(directory prefixes, exact files) of `coga_root_paths` in this checkout.

    The empty prefix is the whole checkout (the root layout).
    """
    dirs = []
    for path in coga_root_paths(cfg, previous_contexts_root):
        rel = relative_to_root(root, path).rstrip("/")
        dirs.append("" if rel == "." else rel + "/")
    return tuple(dirs), ()


def _routine_state_areas(cfg: Config, root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The task directory and log: committed state adopted off control.

    Only `_candidates`' committed-path adoption on a non-control checkout
    reads this narrower set; membership everywhere else is `_state_areas`.
    """
    task_prefix = relative_to_root(root, tasks_dir(cfg)).rstrip("/") + "/"
    return (task_prefix,), (relative_to_root(root, log_path(cfg)),)


def _in_areas(rel: str, areas: tuple[tuple[str, ...], tuple[str, ...]]) -> bool:
    dirs, files = areas
    return rel in files or any(rel.startswith(prefix) for prefix in dirs)


def _index_modes(root: Path) -> dict[str, str]:
    """Git owns executable bits on platforms without POSIX file modes."""
    modes: dict[str, str] = {}
    for record in run_git(root, "ls-files", "--stage", "-z").split("\x00"):
        if record:
            meta, _, rel = record.partition("\t")
            mode, _oid, stage = meta.split()
            if stage == "0" and mode in _REGULAR_MODES:
                modes[rel] = mode
    return modes


def _regular_working_file(
    root: Path, rel: str, *, index_modes: Mapping[str, str] | None = None,
) -> tuple[str, bytes] | None | Literal[False]:
    """`(mode, bytes)` of a regular working file, `None` when absent, `False` otherwise."""
    path = root / rel
    if symlink_component(path) is not None:
        return False
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    except NotADirectoryError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return False
    mode = "100755" if info.st_mode & 0o111 else "100644"
    if os.name != "posix":
        mode = (index_modes if index_modes is not None else _index_modes(root)).get(rel, "100644")
    return mode, path.read_bytes()


def _tree_entry(root: Path, rev: str, rel: str) -> tuple[str, str] | None:
    """`(mode, oid)` of `rel` in `rev`, or `None` when absent."""
    out = run_git(root, "ls-tree", "-z", rev, "--", rel, env={"GIT_LITERAL_PATHSPECS": "1"})
    for record in out.split("\x00"):
        if not record:
            continue
        meta, _, name = record.partition("\t")
        mode, _type, oid = meta.split()
        if name == rel:
            return mode, oid
    return None


def _published_proof(
    root: Path,
    rel: str,
    working: tuple[str, bytes] | None,
    published: tuple[str, str] | None,
    *,
    head_entry: tuple[str, str] | None,
    union: bool,
    cfg: Config | None = None,
    revision: str | None = None,
) -> str | None:
    """`None` when the working copy of `rel` is already on control, else why not."""
    if working is None:
        return None if published is None else "deleted here but present on control"
    if published is None:
        return "not on control"
    mode, data = working
    if mode != published[0]:
        return "file mode differs from control"
    if cfg is not None and revision is not None and rel == relative_to_root(root, log_path(cfg)):
        from coga.log_publication import reconcile
        control_bytes = _blob_bytes(root, published[1])
        merged = reconcile(cfg, root, revision, _clean_bytes(root, data, rel))
        return None if merged == control_bytes else "lines not yet on control"
    if not union:
        if _hash_blob(root, data, rel) == published[1]:
            return None
        return "content differs from control"
    control_bytes = _blob_bytes(root, published[1])
    base = _blob_bytes(root, head_entry[1]) if head_entry is not None else b""
    merged = _merge_union_bytes(
        current=control_bytes, base=base, other=_clean_bytes(root, data, rel)
    )
    return None if merged == control_bytes else "lines not yet on control"


def _clean_bytes(root: Path, data: bytes, rel: str) -> bytes:
    """`data` as the blob `git add` would store for `rel` (see `_hash_blob`)."""
    return _blob_bytes(root, _hash_blob(root, data, rel))


def _blob_bytes(root: Path, oid: str) -> bytes:
    result = _run(["git", "-C", str(root), "cat-file", "blob", oid])
    if result.returncode != 0:
        raise GitError(f"`git cat-file blob {oid}` failed: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def _operation_in_progress(root: Path) -> str | None:
    """The Git operation that owns this checkout's index, or `None`.

    Raises `GitError` when the checkout cannot be inspected, so every caller
    refuses before mutating rather than mistaking a failed probe for "none".
    """
    git_dir = Path(run_git(root, "rev-parse", "--path-format=absolute", "--git-dir").strip())
    for marker, what in _IN_PROGRESS_MARKERS:
        if (git_dir / marker).exists():
            return what
    return None


def _local_control_subsumed(
    cfg: Config, root: Path, local: str, target: str,
    previous_contexts_root: Path | None = None,
) -> _Subsumption:
    """Whether moving local control from `local` to `target` loses nothing.

    `ok` only when `local` and `target` have exactly one merge base, every
    commit in `target..local` — each checked on its own, merges against every
    parent — touches only the configured state areas, and every path in the
    net `base..local` diff is already on `target`: same existence, mode, and
    bytes, or, for a `merge=union` path, union-merging the local copy onto
    the target changes nothing (`_published_proof` with the merge base as the
    three-way base). Fails closed: anything it cannot prove is `unproven`.
    """
    literal = {"GIT_LITERAL_PATHSPECS": "1"}
    stage = f"finding the merge base of {local[:12]} and {target[:12]}"
    try:
        result = _run(["git", "-C", str(root), "merge-base", "--all", local, target])
        if result.returncode not in (0, 1):
            raise GitError(
                f"`git merge-base --all` failed (exit {result.returncode}): "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
        bases = result.stdout.decode().split()
        if len(bases) != 1:
            return _Subsumption(
                "unproven",
                f"{local[:12]} and {target[:12]} have "
                f"{'no' if not bases else len(bases)} merge bases, not exactly one",
                evidence=(local, target, tuple(bases)),
            )
        base = bases[0]
        stage = f"listing the commits in {target[:12]}..{local[:12]}"
        dropped = tuple(
            tuple(line.split("\x1f", 1))
            for line in run_git(
                root, "log", "--reverse", "--format=%H%x1f%s", f"{target}..{local}"
            ).splitlines()
            if line
        )
        areas = _state_areas(cfg, root, previous_contexts_root)
        foreign: list[str] = []
        offenders: list[str] = []
        for commit, subject in dropped:
            stage = f"listing the paths commit {commit[:12]} touches"
            touched = run_git(
                root, "diff-tree", "-r", "-z", "-m", "--root", "--no-commit-id",
                "--no-renames", "--name-only", commit,
            )
            outside = sorted({rel for rel in touched.split("\x00") if rel and not _in_areas(rel, areas)})
            if outside:
                offenders.append(f"{commit[:12]} {subject!r} touches {', '.join(outside)}")
                foreign.extend(rel for rel in outside if rel not in foreign)
        if foreign:
            return _Subsumption(
                "foreign",
                "local commits touch more than Coga state: " + "; ".join(offenders),
                blocking=tuple(foreign),
                dropped=dropped,
                evidence=(local, target, base, dropped),
            )
        stage = f"diffing {base[:12]}..{local[:12]}"
        rels = [
            rel
            for rel in run_git(
                root, "diff", "-z", "--no-renames", "--name-only", base, local
            ).split("\x00")
            if rel
        ]
        stage = "reading `merge` attributes"
        union = union_merge_paths(root, rels) if rels else set()
        examined: list[tuple[object, ...]] = []
        failed: list[str] = []
        for rel in rels:
            stage = f"proving {rel} is on {target[:12]}"
            mine = _tree_entry(root, local, rel)
            published = _tree_entry(root, target, rel)
            head_entry = _tree_entry(root, base, rel)
            examined.append((rel, mine, published, head_entry))
            unsupported = [
                entry for entry in (mine, published, head_entry)
                if entry is not None and entry[0] not in _REGULAR_MODES
            ]
            if unsupported:
                return _Subsumption(
                    "unproven",
                    f"{rel} is a symlink, submodule, or other non-regular entry "
                    f"(mode {unsupported[0][0]})",
                    blocking=(rel,),
                    dropped=dropped,
                    evidence=(local, target, base, dropped, tuple(examined)),
                )
            working = None if mine is None else (mine[0], _blob_bytes(root, mine[1]))
            proof = _published_proof(
                root, rel, working, published, head_entry=head_entry, union=rel in union, cfg=cfg, revision=target
            )
            if proof:
                failed.append(f"{rel} ({proof})")
    except GitError as exc:
        return _Subsumption(
            "unproven", f"failed while {stage}: {exc}", evidence=(local, target)
        )
    evidence = (local, target, base, dropped, tuple(examined), tuple(sorted(union)))
    if failed:
        return _Subsumption(
            "unpublished",
            "local Coga state commits are not yet on control: " + "; ".join(failed),
            blocking=tuple(failed),
            dropped=dropped,
            evidence=evidence,
        )
    return _Subsumption("ok", dropped=dropped, evidence=evidence)


def _divergence_message(cfg: Config, verdict: _Subsumption, *, on_control: bool) -> str:
    """The refusal and remedy for an ahead or diverged local control."""
    remote, control = cfg.git_remote, cfg.git_control_branch
    pull = f"`git pull --rebase --autostash {remote} {control}`"
    head = f"local {control!r} has commits not on {remote}/{control}"
    if verdict.kind == "foreign":
        return f"{head} ({verdict.reason}); reconcile them ({pull} and push) and retry"
    if verdict.kind == "unpublished":
        where = (
            f"run {pull} on {control!r}" if on_control
            else f"switch to {control!r} (`git switch {control}`), run {pull} there"
        )
        return f"{head} ({verdict.reason}); {where}, then retry the command"
    return (
        f"{head} and could not prove them already on control ({verdict.reason}); "
        f"inspect them (`git log {remote}/{control}..{control}`), reconcile by hand, "
        "and retry"
    )


def _report_realignment(cfg: Config, verdict: _Subsumption, new: str) -> None:
    """The one stderr line naming the commits a realignment dropped."""
    remote, control = cfg.git_remote, cfg.git_control_branch
    dropped = "; ".join(f"{commit[:12]} {subject}" for commit, subject in verdict.dropped)
    sys.stderr.write(
        f"[git] realigned local {control!r} to {remote}/{control} ({new[:12]}); "
        f"dropped commits whose Coga state is already there: {dropped}. "
        f"They remain in the reflog (`git reflog {control}`)\n"
    )


def _ignored_collisions(root: Path, revs: list[str]) -> list[str]:
    """Ignored working files at paths the move across `revs` would write."""
    touched: list[str] = []
    for old, new in zip(revs, revs[1:]):
        if old == new:
            continue
        out = run_git(root, "diff", "-z", "--name-only", "--no-renames", old, new)
        touched.extend(rel for rel in out.split("\x00") if rel and rel not in touched)
    collisions: list[str] = []
    for start in range(0, len(touched), _CHECK_ATTR_BATCH):
        out = run_git(
            root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard",
            "--", *touched[start:start + _CHECK_ATTR_BATCH],
            env={"GIT_LITERAL_PATHSPECS": "1"},
        )
        collisions.extend(rel for rel in out.split("\x00") if rel)
    return collisions


def _digest(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()


def _prune_empty_parents(
    root: Path, rel: str, areas: tuple[tuple[str, ...], tuple[str, ...]]
) -> None:
    """Remove directories a deleted state file left empty, never an area root."""
    prefix = next((p for p in areas[0] if rel.startswith(p)), None)
    if prefix is None:
        return
    stop = (root / prefix.rstrip("/")).resolve()
    parent = (root / rel).parent
    while parent.resolve() != stop:
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


# --- read-only probes ---------------------------------------------------------


def stale_coga_task_rels(cfg: Config) -> list[str]:
    """Task paths where the remote-tracking control ref is provably ahead.

    Local refs only, never a fetch, so `coga status` stays no-network. Counts
    a ticket whose remote copy is further along in status/step, or present on
    control and absent here. Fail-open: any git failure returns `[]`.
    """
    if not cfg.git_enabled:
        return []
    try:
        root = toplevel(cfg.repo_root)
        if root is None:
            return []
        ref = f"refs/remotes/{cfg.git_remote}/{cfg.git_control_branch}"
        if not _ref_present(root, ref):
            return []
        out = run_git(
            root, "diff", "-z", "--name-only", ref, "--", relative_to_root(root, tasks_dir(cfg))
        )
        stale = []
        for rel in _ticket_rels(cfg, root, [rel for rel in out.split("\x00") if rel]):
            remote = _lifecycle(tree_bytes(root, ref, rel))
            if remote is None:
                continue
            local_bytes = _working_tree_bytes(root, rel)
            local = _lifecycle(local_bytes)
            if local_bytes is None:
                stale.append(rel)
            elif local is not None:
                remote_rank = _STATUS_RANK.get(remote[0] or "")
                local_rank = _STATUS_RANK.get(local[0] or "")
                if remote_rank is not None and local_rank is not None and remote_rank != local_rank:
                    ahead = remote_rank > local_rank
                else:
                    ahead = remote[1] is not None and local[1] is not None and remote[1] > local[1]
                if ahead:
                    stale.append(rel)
        return stale
    except GitError:
        return []


def _lifecycle(data: bytes | None) -> tuple[str | None, int | None] | None:
    ticket = _parse_ticket(data)
    if ticket is None:
        return None
    status = ticket.frontmatter.get("status")
    return (str(status) if status is not None else None, ticket.step_index())


def _parse_ticket(data: bytes | None) -> Ticket | None:
    if data is None:
        return None
    try:
        return Ticket.parse(data.decode("utf-8"))
    except (UnicodeDecodeError, TicketError):
        return None


# Past this many uncovered tasks, one walk of all of `tasks/` beats a long
# pathspec list (and stays clear of argv limits).
_COMMIT_TIMES_MAX_PATHSPECS = 200


def last_commit_times(
    cfg: Config, paths: list[str] | None = None
) -> dict[str, datetime]:
    """Map each path under `tasks/` to the commit time it was last touched.

    Keys are posix paths relative to `tasks/`. The fallback source for
    `coga status`'s `Updated` column when the log has no line for a task
    (moved directory, hand-authored ticket). `paths` (relative to `tasks/`)
    narrows the history walk to those entries; `[]` asks nothing and skips
    git. Read-only; `{}` on any failure.
    """
    if not cfg.git_enabled or paths == []:
        return {}
    root = toplevel(tasks_dir(cfg))
    if root is None:
        return {}
    rel = relative_to_root(root, tasks_dir(cfg))
    prefix = rel.rstrip("/") + "/"
    if paths is None or len(paths) > _COMMIT_TIMES_MAX_PATHSPECS:
        pathspecs = [rel]
    else:
        pathspecs = [prefix + path for path in paths]
    try:
        out = run_git(
            root, "--literal-pathspecs", "log", "--format=%ct", "--name-only",
            "--", *pathspecs,
        )
    except GitError:
        return {}
    times: dict[str, datetime] = {}
    stamp: datetime | None = None
    for line in out.splitlines():
        if not line:
            continue
        if line.isdigit():
            stamp = datetime.fromtimestamp(int(line))
        elif stamp is not None and line.startswith(prefix):
            # Newest-first walk: the first mention of a path is its latest.
            times.setdefault(line[len(prefix):], stamp)
    return times


def union_merge_paths(root: Path, rels: list[str]) -> set[str]:
    """Subset of `rels` carrying the `merge=union` git attribute.

    Asked of git (`git check-attr merge -z`) rather than hardcoding `log.md`.
    Shared with `open_pr`; raises `GitError` when the probe fails because both
    callers decide something important on the answer.
    """
    union: set[str] = set()
    for start in range(0, len(rels), _CHECK_ATTR_BATCH):
        out = run_git(
            root, "check-attr", "merge", "-z", "--", *rels[start:start + _CHECK_ATTR_BATCH]
        )
        fields = out.split("\x00")
        for j in range(0, len(fields) - 2, 3):
            if fields[j + 2] == "union":
                union.add(fields[j])
    return union


def is_linked_worktree(start: Path) -> bool:
    """True only when `start` belongs to a linked git worktree."""
    root = toplevel(start)
    if root is None:
        return False
    try:
        git_dir = run_git(root, "rev-parse", "--path-format=absolute", "--git-dir").strip()
        common = run_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    except GitError:
        return False
    return Path(git_dir).resolve() != Path(common).resolve()


CheckoutKind = Literal["primary", "linked", "foreign-linked", "foreign-primary"]


@dataclass(frozen=True)
class CheckoutRelation:
    """`classify_checkout`'s verdict on one recorded checkout.

    `owner` is set for `"foreign-linked"` and `"foreign-primary"`: the main
    working tree of the repository the checkout belongs to, where a human runs
    `git worktree remove` / `git branch -d` that no Coga command here can.
    """

    kind: CheckoutKind
    owner: Path | None = None


def classify_checkout(root: Path, path: Path) -> CheckoutRelation | None:
    """How the checkout at `path` relates to the repository `root` belongs to.

    One probe for every caller that must judge a recorded `worktree:` before
    acting on it, so they cannot disagree:

    - `"linked"` — a linked worktree of `root`'s repository: its own
      administrative git dir under the shared common dir. The one shape
      `coga retire` and the autoclose disposal phase ever remove.
    - `"primary"` — the primary checkout of `root`'s repository, whose git dir
      *is* the common dir. A ticket worked in the single-checkout layout
      records it as its own `worktree:`; nobody ever disposes of it, so it is
      never retire debt.
    - `"foreign-linked"` — a linked worktree of some *other* repository, with
      that repository's main working tree as `owner`.
    - `"foreign-primary"` — the primary checkout of another repository: an
      independent clone (including the sandbox `/tmp` fallback) or unrelated
      repo. Its resolved root is `owner`; topology cannot prove disposability.
    - `None` — no answer: `path` or `root` is not a git checkout git can read,
      `path` is a directory *inside* a checkout rather than its root, or `git`
      could not run. Every caller fails closed on it.

    The comparison is between common dirs, never between `root` and `path`
    themselves, so the verdict does not change when the caller runs from a
    linked worktree (a recurring control worktree) instead of the primary
    checkout. `is_linked_worktree` above answers the unscoped "is this
    checkout linked at all" and folds its unknowns into `False`.
    """
    probed = _checkout_dirs(path)
    anchor = _checkout_dirs(root)
    if probed is None or anchor is None:
        return None
    git_dir, common_dir, top = probed
    try:
        resolved = path.resolve()
    except OSError:
        return None
    if top != resolved:
        return None
    linked = git_dir != common_dir
    if common_dir == anchor[1]:
        return CheckoutRelation("linked" if linked else "primary")
    if not linked:
        return CheckoutRelation("foreign-primary", owner=top)
    return CheckoutRelation(
        "foreign-linked", owner=_main_worktree(path) or common_dir.parent
    )


def _checkout_dirs(path: Path) -> tuple[Path, Path, Path] | None:
    """`path`'s resolved git dir, common dir, and toplevel, or `None`.

    Decoded with `os.fsdecode` so a path that does not decode under the
    ambient locale yields a comparable path rather than an exception in the
    middle of a sweep.
    """
    try:
        result = _run(
            [
                "git",
                "-C",
                str(path),
                "rev-parse",
                "--path-format=absolute",
                "--git-dir",
                "--git-common-dir",
                "--show-toplevel",
            ]
        )
    except GitError:
        return None
    if result.returncode != 0:
        return None
    lines = os.fsdecode(result.stdout).splitlines()
    if len(lines) != 3 or not all(lines):
        return None
    try:
        git_dir, common_dir, top = (Path(line).resolve() for line in lines)
    except OSError:
        return None
    return git_dir, common_dir, top


def _main_worktree(path: Path) -> Path | None:
    """The main working tree of the repository containing `path`, or `None`.

    `git worktree list --porcelain` always lists the main working tree first.
    """
    try:
        result = _run(["git", "-C", str(path), "worktree", "list", "--porcelain"])
    except GitError:
        return None
    if result.returncode != 0:
        return None
    for line in os.fsdecode(result.stdout).splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree "):])
    return None


def summarize_git_failure(output: str) -> str:
    """Keep actionable errors and bounded overwrite path lists, deduped.

    Falls back to the last non-empty line so an unrecognized failure is never
    silently emptied.
    """
    keep: list[str] = []
    last = ""
    path_limit = 10
    in_paths = False
    path_count = 0
    # The sentinel closes a path list even when Git's output ends with it.
    for raw in [*output.splitlines(), ""]:
        line = raw.strip().split("\r")[-1].strip()
        if in_paths and raw.startswith("\t") and len(raw) > 1:
            path_count += 1
            if path_count <= path_limit:
                separator = " " if path_count == 1 else ", "
                # Remove only Git's indent; whitespace can belong to the path.
                keep[-1] += separator + raw[1:]
            continue
        if in_paths and path_count > path_limit:
            keep[-1] += f", ... (+{path_count - path_limit} more files)"
        in_paths = False
        if not line:
            continue
        last = line
        if line.startswith(("error:", "fatal:", "CONFLICT")):
            keep.append(line)
            in_paths = (
                line.startswith("error:")
                and "would be overwritten by" in line
                and line.endswith(":")
            )
            path_count = 0
    return "; ".join(dict.fromkeys(keep)) if keep else last


# --- plumbing -----------------------------------------------------------------


def run_git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """Run a git subcommand in `root` and return stdout; raise `GitError` on failure.

    Always non-interactive: a logged-out HTTPS push or an unloaded SSH key
    fails loud instead of hanging an unattended launch on a prompt.
    """
    result = _run(["git", "-C", str(root), *args], env=env)
    if result.returncode != 0:
        stderr = _redact(result.stderr.decode(errors="replace"), args)
        stdout = _redact(result.stdout.decode(errors="replace"), args)
        safe = " ".join(redacted_git_source(arg) for arg in args)
        raise GitError(
            f"`git {safe}` failed (exit {result.returncode}): "
            f"{summarize_git_failure(stderr) or summarize_git_failure(stdout)}"
        )
    return result.stdout.decode(errors="replace")


def _run(
    argv: list[str], *, env: dict[str, str] | None = None, input: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            argv, capture_output=True, check=False, env=_git_env(env), input=input
        )
    except FileNotFoundError as exc:
        raise GitError("`git` not found on PATH") from exc


# Pins Git's diagnostics to English for the calls whose outcome depends on
# matching message text; other calls keep the operator's locale for hooks.
_MESSAGE_LOCALE = {"LC_ALL": "C"}


def _git_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    if extra:
        env.update(extra)
    return env


def _redact(text: str, args: Iterable[str]) -> str:
    for arg in args:
        text = text.replace(arg, redacted_git_source(arg))
    return _URL_IN_DIAGNOSTIC_RE.sub(lambda m: redacted_git_source(m.group(0)), text)


def toplevel(start: Path) -> Path | None:
    """The git working-tree root containing `start`, or `None` outside a repo."""
    if not start.is_dir():
        start = start.parent
    result = _run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"], env=_MESSAGE_LOCALE
    )
    if result.returncode != 0:
        if b"not a git repository" in result.stderr:
            return None
        raise GitError(
            "`git rev-parse --show-toplevel` failed "
            f"(exit {result.returncode}): {result.stderr.decode(errors='replace').strip()}"
        )
    top = result.stdout.decode().strip()
    return Path(top) if top else None


def current_branch(root: Path) -> str:
    """The current branch name (`HEAD` when detached)."""
    return run_git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()


def symbolic_head(root: Path) -> str | None:
    """The current branch via `symbolic-ref` (valid before the first commit); `None` when detached."""
    result = _run(["git", "-C", str(root), "symbolic-ref", "--short", "-q", "HEAD"])
    return result.stdout.decode().strip() or None


def remote_configured(root: Path, remote: str) -> bool:
    """True when `<remote>` has a URL."""
    return _run(["git", "-C", str(root), "remote", "get-url", remote]).returncode == 0


def remote_branch_oid(root: Path, remote: str, branch: str) -> str | None:
    """`refs/heads/<branch>` on the remote as `ls-remote` reports it, or `None`."""
    out = run_git(root, "ls-remote", "--heads", remote, f"refs/heads/{branch}")
    line = next((line for line in out.splitlines() if line.strip()), "")
    return line.split(maxsplit=1)[0] if line else None


def control_branch_present(
    root: Path, branch: str, remote: str, *, probe_remote: bool = True
) -> bool:
    """True when the control branch exists locally, as a remote-tracking ref, or on the remote."""
    if _ref_present(root, f"refs/heads/{branch}") or _ref_present(
        root, f"refs/remotes/{remote}/{branch}"
    ):
        return True
    if not probe_remote or not remote_configured(root, remote):
        return False
    return remote_branch_oid(root, remote, branch) is not None


def control_branch_mismatch_message(cfg: Config, root: Path) -> str:
    """One actionable line for a control branch that does not exist."""
    actual = symbolic_head(root)
    on = f" (you are on {actual!r})" if actual else ""
    return (
        f"[git] control branch {cfg.git_control_branch!r} does not exist{on}; "
        f"sync skipped. Set it to match your branch in coga.toml:\n"
        f"    [git]\n"
        f'    control_branch = "{actual or "<your-branch>"}"'
    )


def relative_to_root(root: Path, path: Path) -> str:
    """`path` relative to the git root, without following any symlink."""
    lexical = Path(os.path.abspath(path))
    try:
        return lexical.relative_to(root.resolve()).as_posix()
    except ValueError:
        return lexical.as_posix()


def symlink_component(path: Path) -> Path | None:
    """Return a symlink in this lexical path, including missing-target links."""
    return next(
        (part for part in (path, *path.parents) if part.is_symlink()), None,
    )


def tree_bytes(root: Path, rev: str, rel: str) -> bytes | None:
    """The bytes of `rel` in `rev`'s tree, or `None` when absent."""
    if _blob_oid(root, rev, rel) is None:
        return None
    result = _run(["git", "-C", str(root), "show", f"{rev}:{rel}"])
    if result.returncode != 0:
        raise GitError(
            f"`git show {rev}:{rel}` failed: {result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def _blob_oid(root: Path, rev: str, rel: str) -> str | None:
    result = _run(["git", "-C", str(root), "rev-parse", "-q", "--verify", f"{rev}:{rel}"])
    if result.returncode != 0:
        return None
    return result.stdout.decode().strip() or None


def _hash_blob(root: Path, data: bytes, rel: str) -> str:
    """Store `data` as the blob `git add` would make for `rel`.

    `--path` applies the checkout's clean filters (`core.autocrlf`,
    `.gitattributes`), so a CRLF working copy hashes to the same LF blob the
    index holds. Raw bytes would land a CRLF blob on control that no staged
    or re-added copy of the file can ever match.
    """
    result = _run(
        ["git", "-C", str(root), "hash-object", "-w", f"--path={rel}", "--stdin"],
        input=data,
    )
    if result.returncode != 0:
        args = ("hash-object", "-w", f"--path={rel}", "--stdin")
        stderr = _redact(result.stderr.decode(errors="replace"), args)
        raise ObjectWriteError(
            rel=rel,
            checkout=Path(os.path.abspath(root)),
            object_dir=_object_dir(root),
            detail=summarize_git_failure(stderr) or f"exit {result.returncode}",
        )
    return result.stdout.decode().strip()


def _object_dir(root: Path) -> Path | None:
    """The object directory Git writes to from `root`, or `None` if unknowable.

    Asked of Git with the same inherited environment as the failed write, so a
    linked checkout's shared store and an absolute or relative
    `GIT_OBJECT_DIRECTORY` resolve exactly as the write saw them. Only a
    diagnostic: any failure here yields `None` rather than replacing the
    original error.
    """
    try:
        result = _run(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute",
             "--git-path", "objects"]
        )
    except (GitError, OSError):
        return None
    out = result.stdout.decode(errors="replace").strip()
    if result.returncode != 0 or not out or "\n" in out:
        return None
    return Path(out)


def _ref_present(root: Path, ref: str) -> bool:
    result = _run(["git", "-C", str(root), "show-ref", "--verify", "--quiet", ref])
    if result.returncode in (0, 1):
        return result.returncode == 0
    raise GitError(
        f"`git show-ref --verify {ref}` failed (exit {result.returncode}): "
        f"{result.stderr.decode(errors='replace').strip()}"
    )


def _is_ancestor(root: Path, old: str, new: str) -> bool:
    return _run(["git", "-C", str(root), "merge-base", "--is-ancestor", old, new]).returncode == 0


def _working_tree_bytes(root: Path, rel: str) -> bytes | None:
    if symlink_component(root / rel) is not None:
        raise StateRegressionError(
            f"{rel}: is a symlink or has a symlinked ancestor; "
            "replace it with regular files before publication"
        )
    try:
        return (root / rel).read_bytes()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return None
    except PermissionError:
        # Opening a directory reports EACCES on Windows, not EISDIR. Let the
        # existing tree-mode guard diagnose a submodule or non-regular entry.
        if os.name == "nt" and (root / rel).is_dir():
            return None
        raise


def _dirty_paths(root: Path, pathspecs: list[str]) -> list[str]:
    """Repo-relative files with working-tree changes under `pathspecs` (incl. deletions)."""
    if not pathspecs:
        return []
    out = run_git(root, "status", "--porcelain", "-z", "--untracked-files=all", "--", *pathspecs)
    fields = out.split("\x00")
    rels: list[str] = []
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry:
            continue
        path = entry[3:]
        if path and path not in rels:
            rels.append(path)
        if entry[0] in "RC" and i < len(fields):
            # A rename stores its source in the next field: commit it as a delete.
            source = fields[i]
            i += 1
            if source and source not in rels:
                rels.append(source)
    return rels


def _ticket_rels(cfg: Config, root: Path, rels: Iterable[str]) -> list[str]:
    """The ticket files among `rels` (`ticket.md`, or a file-form `<slug>.md`)."""
    tasks_rel = relative_to_root(root, tasks_dir(cfg))
    prefix = f"{tasks_rel}/" if tasks_rel != "." else ""
    out: list[str] = []
    for rel in rels:
        if not rel.startswith(prefix):
            continue
        path = Path(rel)
        if path.name == "ticket.md" or (
            path.suffix == ".md" and not (root / path.parent / "ticket.md").exists()
        ):
            out.append(rel)
    return out


def worktree_holding_branch(root: Path, branch: str) -> Path | None:
    """Path of the worktree with `branch` checked out, or `None`; raises on a failed listing."""
    target = f"branch refs/heads/{branch}"
    current: Path | None = None
    for line in run_git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            current = Path(line[len("worktree "):])
        elif line == target:
            return current
    return None


__all__ = [
    "CheckoutKind",
    "CheckoutPreparation",
    "CheckoutRelation",
    "GitError",
    "MAX_PUBLISH_ATTEMPTS",
    "ObjectWriteError",
    "PUBLISHED_REF",
    "RETRY_WITHOUT_SWEEP_EXIT_CODE",
    "STALE_CONTROL_EXIT_CODE",
    "StateRegressionError",
    "UncertainPublishError",
    "classify_checkout",
    "control_relay_started",
    "control_branch_mismatch_message",
    "control_branch_present",
    "current_branch",
    "fast_forward_control",
    "fetch_control",
    "is_linked_worktree",
    "last_commit_times",
    "prepare_control_checkout",
    "publish",
    "record_projected_baseline",
    "refresh",
    "relative_to_root",
    "remote_branch_oid",
    "record_sync_failure",
    "remote_configured",
    "run_git",
    "stale_coga_task_rels",
    "state_lock",
    "state_sweep_withheld",
    "summarize_git_failure",
    "symbolic_head",
    "sync_coga_state",
    "sync_failure_report",
    "sync_log",
    "sync_task_state",
    "ticket_regression_reason",
    "toplevel",
    "tree_bytes",
    "union_merge_paths",
    "worktree_holding_branch",
    "write_ticket",
]
