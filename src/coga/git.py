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
  retried by the next command's sweep. `merge=union` files (`coga/log.md`)
  are three-way union-merged, never overlaid.
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

import fcntl
import hashlib
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from coga.config import Config
from coga.github_source import redacted_git_source
from coga.logfile import append_log, ref_tag_for_path
from coga.paths import log_path, recurring_dir, tasks_dir
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


# --- lock ---------------------------------------------------------------------

_HELD_LOCKS: dict[tuple[str, int], list[int]] = {}


@contextmanager
def state_lock(cfg: Config) -> Iterator[None]:
    """Serialize this checkout's Coga writers and publishers.

    A short, kernel-released advisory `flock` around a ticket's
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
    lock_root = Path(tempfile.gettempdir()) / f"coga-state-publication-{os.getuid()}"
    try:
        lock_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(lock_root / f"{checkout}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    except OSError as exc:
        raise GitError(f"could not open local state lock: {exc}") from exc
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError as exc:
        os.close(fd)
        raise GitError(f"local state lock failed: {exc}") from exc
    _HELD_LOCKS[key] = [fd, 1]
    try:
        yield
    finally:
        del _HELD_LOCKS[key]
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def write_ticket(cfg: Config, ticket: Ticket, path: Path) -> bytes:
    """Render and write a ticket under `state_lock`; return the bytes written."""
    rendered = ticket.render().encode("utf-8")
    with state_lock(cfg):
        ticket.write(path)
    return rendered


# --- entry points -------------------------------------------------------------


def sync_task_state(
    cfg: Config,
    task_path: Path,
    *,
    message: str,
    expect: Mapping[Path, bytes | None] | None = None,
    strict: bool = False,
) -> bool | None:
    """Publish one task (file or directory) plus `coga/log.md`.

    Non-fatal by default: a refusal or failure is written to stderr and the
    task's log, then swallowed, so the local transition stands. `strict=True`
    re-raises after reporting, for callers that gate later work on it.
    """
    try:
        return publish(cfg, [task_path, log_path(cfg)], message, expect=expect)
    except StateRegressionError as exc:
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
        if strict:
            raise
    except GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        append_log(cfg, ref_tag_for_path(cfg, task_path), "git", f"sync failed: {exc}")
        if strict:
            raise
    return None


def sync_log(cfg: Config, *, message: str) -> bool:
    """Publish `coga/log.md` alone (stateless launches); stderr-only on failure."""
    try:
        return bool(publish(cfg, [log_path(cfg)], message))
    except GitError as exc:
        sys.stderr.write(f"[git] log sync failed: {exc}. Message was: {message}\n")
        return False


def sync_coga_state(cfg: Config, *, message: str = "Sync coga state") -> None:
    """The catch-all sweep: publish eligible task, log, and recurring state.

    Runs at the CLI dispatch boundary and is the retry for every earlier miss.
    The whole configured state areas go to `publish`, so `_candidates` selects
    committed state this checkout derived (a hand commit on local control) as
    well as dirty state; clean state merely behind control is not a write.
    Hand-authored contexts, skills, and workflows are review work and are left
    alone.
    """
    try:
        root = _publishable_root(cfg, message)
        if root is None:
            return
        publish(cfg, [tasks_dir(cfg), log_path(cfg), recurring_dir(cfg)], message)
    except StateRegressionError as exc:
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
    except GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        append_log(cfg, ref_tag_for_path(cfg, cfg.repo_root), "git", f"sync failed: {exc}")


# --- publish ------------------------------------------------------------------


def publish(
    cfg: Config,
    paths: Iterable[Path],
    message: str,
    *,
    expect: Mapping[Path, bytes | None] | None = None,
    guard: Callable[[str], None] | None = None,
    fast_forward: bool = True,
) -> bool | None:
    """Land the dirty files under `paths` on the control branch.

    `expect` maps a path to the bytes the writer read before writing (`None`
    for "must not exist"); it replaces the default provenance check for that
    path with that exact blob, and for a `merge=union` path it adds one.
    `guard` is called with the control commit each attempt builds on — the
    remote-tracking ref, re-fetched after every rejected push — before any
    tree is built; it may raise to refuse. It exists for a decision `expect`
    cannot express: a `merge=union` file whose *content* matters (the
    recurring serviced-period ledger), where pinning the whole blob would
    refuse every unrelated concurrent append. `fast_forward=False` leaves the
    local control checkout untouched after a successful push (Retro's
    isolated delete).
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
            else _hash_blob(root, data, relative_to_root(root, path))
        )
        for path, data in (expect or {}).items()
    }
    with state_lock(cfg):
        return _publish_locked(cfg, root, pathspecs, message, expected, guard, fast_forward)


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
) -> bool:
    remote, control = cfg.git_remote, cfg.git_control_branch
    have_remote = remote_configured(root, remote)
    fetched = False
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
        rels = _candidates(root, pathspecs, base, ancestor)
        if not rels:
            return False
        if not have_remote and _attempt == 0:
            sys.stderr.write(
                f"[git] no {remote!r} remote configured — coga state committed on "
                f"local {control!r} only; add a remote to sync ({message})\n"
            )
        working = {rel: _working_tree_bytes(root, rel) for rel in rels}
        union = union_merge_paths(root, rels)
        landed = _guard(cfg, root, rels, base, working, union, _provenance(root, rels, ancestor), expected)
        tree = _build_tree(root, base, rels, working, union, ancestor, landed)
        staged = {rel: (working[rel], landed[rel]) for rel in rels}
        if tree == run_git(root, "rev-parse", f"{base}^{{tree}}").strip():
            # Already on control. A control checkout still catches up so its
            # dirty-but-equal files come clean; nothing reaches other checkouts.
            if fast_forward and current_branch(root) == control:
                fast_forward_control(cfg, root, base, staged=staged)
            return False
        new = run_git(root, "commit-tree", tree, "-p", base, "-m", message).strip()
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
        if not fast_forward_control(cfg, root, new, staged=staged):
            raise GitError(
                f"no {remote!r} remote configured and local {control!r} could not "
                f"be fast-forwarded to the new commit; the write stays dirty"
            )
        _record_published(root, {rel: _blob_oid(root, new, rel) for rel in rels})
        return True
    _record_published(root, {rel: _blob_oid(root, new, rel) for rel in rels})
    if fast_forward:
        fast_forward_control(cfg, root, new, staged=staged)
    return True


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


def _candidates(root: Path, pathspecs: list[str], base: str, ancestor: str | None) -> list[str]:
    """The files under `pathspecs` this publish carries.

    Every path dirty against HEAD (a write no commit holds yet), plus a
    clean path whose HEAD copy moved past control from a copy this checkout
    derived from — a feature branch that committed Coga state it had itself
    published, or a hand commit on local control. A clean path that is merely
    *behind* control — HEAD's copy unchanged since the merge base, even when
    control holds a copy this worktree published — is not a write and is left
    alone.
    """
    rels = _dirty_paths(root, pathspecs)
    committed = run_git(root, "diff", "-z", "--name-only", base, "HEAD", "--", *pathspecs)
    for rel in (rel for rel in committed.split("\x00") if rel and rel not in rels):
        head_oid = _blob_oid(root, "HEAD", rel)
        if ancestor is not None and head_oid == _blob_oid(root, ancestor, rel):
            continue
        derived = _provenance(root, [rel], ancestor)[rel] - {head_oid}
        if _blob_oid(root, base, rel) in derived:
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
    for rel in rels:
        data = working[rel]
        if (root / rel).is_symlink():
            # `_working_tree_bytes` follows links, so publishing one would land
            # its target's bytes — possibly from outside the repo — as a
            # regular file on control. Coga state is plain files only.
            refusals.append(
                f"{rel}: is a symlink; replace it with a regular file before it "
                "can be published"
            )
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
    try:
        run_git(root, "read-tree", base, env=env)
        for rel in rels:
            data = working[rel]
            if rel in union and data is not None:
                data = _merge_union_bytes(
                    current=tree_bytes(root, base, rel) or b"",
                    base=(tree_bytes(root, ancestor, rel) or b"") if ancestor else b"",
                    other=data,
                )
                landed[rel] = data
            run_git(root, "rm", "-rf", "--cached", "--ignore-unmatch", "--", rel, env=env)
            if data is not None:
                mode = "100755" if os.access(root / rel, os.X_OK) else "100644"
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
        return files[0].read_bytes()


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
    except GitError as exc:
        sys.stderr.write(f"[git] note: could not record published blobs: {exc}\n")
    finally:
        try:
            os.unlink(index)
        except FileNotFoundError:
            pass


# --- integrate ----------------------------------------------------------------


def fast_forward_control(
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
    reflog). Anything else is left alone with one stderr line naming the fix.
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
    if holder.resolve() == root.resolve() and not _stage_landed(cfg, root, staged):
        return False
    result = _run(["git", "-C", str(holder), "merge", "--ff-only", "--quiet", new])
    if result.returncode != 0:
        sys.stderr.write(
            f"[git] note: local {control!r} in {holder} not fast-forwarded: "
            f"{summarize_git_failure(result.stderr.decode(errors='replace'))}\n"
        )
        return False
    return True


def _stage_landed(
    cfg: Config,
    root: Path,
    staged: Mapping[str, tuple[bytes | None, bytes | None]] | None,
) -> bool:
    """Bring files this process just published to their landed bytes and stage them."""
    try:
        for rel, (read, landed) in (staged or {}).items():
            if _working_tree_bytes(root, rel) != read:
                continue
            if landed is not None:
                (root / rel).write_bytes(landed)
            run_git(root, "add", "--all", "--", rel)
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
            if not _stage_landed(cfg, root, staged):
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
    cfg: Config, *, require_remote_control: bool = False
) -> CheckoutPreparation:
    """Bring the invoking checkout to a clean control branch at the fetched tip.

    Confined to this one checkout: a sibling worktree is never switched,
    fast-forwarded, or cleaned. The fetched `<remote>/<control>` commit is
    pinned once. Local control must exist and be equal to or behind it, or
    carry only commits `_local_control_subsumed` proves are Coga state already
    on the pinned tip (it is then realigned, not merged); a detached HEAD, an
    in-progress Git operation, or control checked out in another worktree
    refuses. Every staged, tracked, and untracked change in
    the checkout is examined: only files under the tasks directory, the
    recurring directory, and the log may be cleaned, and only when their
    existence, mode, and content already match the pinned tree (a
    `merge=union` file when union-merging it onto that tree changes nothing),
    with any staged copy equal to HEAD's or the published one. Ignored files
    are never candidates, and one the move would overwrite refuses. The whole
    plan is validated and then re-observed before the first mutation; changed
    evidence refuses. Only then are proven paths restored to HEAD or removed,
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
        _fetch_control(root, remote, control)
        remote_ref = f"refs/remotes/{remote}/{control}"
        if not _ref_present(root, remote_ref):
            if require_remote_control:
                return CheckoutPreparation(
                    "refused", f"{remote}/{control} no longer exists"
                )
            return CheckoutPreparation("exempt", f"{remote}/{control} does not exist")
        pinned = run_git(root, "rev-parse", remote_ref).strip()
        with state_lock(cfg):
            plan = _plan_preparation(cfg, root, pinned)
            if isinstance(plan, CheckoutPreparation):
                return plan
            # Re-observe immediately before mutating: a concurrent edit,
            # stage, or branch move between the checks and the first write
            # refuses instead of being discarded on stale evidence.
            again = _plan_preparation(cfg, root, pinned)
            if isinstance(again, CheckoutPreparation):
                return again
            if again.evidence != plan.evidence:
                return CheckoutPreparation(
                    "refused",
                    "the checkout changed while it was being examined; retry",
                )
            return _apply_preparation(cfg, root, pinned, plan)
    except GitError as exc:
        return CheckoutPreparation("refused", f"could not inspect the checkout: {exc}")


def _plan_preparation(
    cfg: Config, root: Path, pinned: str
) -> _PreparationPlan | CheckoutPreparation:
    """Every check `prepare_control_checkout` makes before its first write."""
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
        realign = _local_control_subsumed(cfg, root, local, pinned)
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
    areas = _state_areas(cfg, root)
    union = set()
    restore: list[str] = []
    remove: list[str] = []
    blocking: list[str] = []
    candidate_bytes: dict[str, bytes | None] = {}
    entries = _status_v2_entries(status)
    paths = [rel for _kind, _fields, rel in entries]
    if paths:
        union = union_merge_paths(root, paths)
    for kind, fields, rel in entries:
        if kind == "u" or kind == "2":
            blocking.append(f"{rel} (unmerged or renamed index entry)")
            continue
        if not _in_state_area(rel, areas):
            blocking.append(f"{rel} (not Coga state)")
            continue
        working = _regular_working_file(root, rel)
        published = _tree_entry(root, pinned, rel)
        if kind == "?":
            if working is False:
                blocking.append(f"{rel} (not a regular file)")
                continue
            proof = _published_proof(
                root, rel, working, published, head_entry=None, union=rel in union
            )
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
        if index_entry != head_entry and index_entry != published:
            blocking.append(f"{rel} (staged content is not the published version)")
            continue
        proof = _published_proof(
            root, rel, working, published, head_entry=head_entry, union=rel in union
        )
        if proof:
            blocking.append(f"{rel} ({proof})")
            continue
        (restore if head_entry is not None else remove).append(rel)
        candidate_bytes[rel] = working[1] if working else None
    if blocking:
        return CheckoutPreparation(
            "refused",
            "uncommitted changes would be lost by moving to "
            f"{control!r}; commit, publish, or remove them and retry",
            blocking=tuple(blocking),
        )

    collisions = _ignored_collisions(root, ["HEAD", local, pinned])
    if collisions:
        return CheckoutPreparation(
            "refused",
            f"ignored files would be overwritten by moving to {remote}/{control}; "
            "move them aside and retry",
            blocking=tuple(collisions),
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


def _apply_preparation(
    cfg: Config, root: Path, pinned: str, plan: _PreparationPlan
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
        areas = _state_areas(cfg, root)
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


def _state_areas(cfg: Config, root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(directory prefixes, exact files) Coga state may occupy in this checkout."""
    dirs = tuple(
        relative_to_root(root, path).rstrip("/") + "/"
        for path in (tasks_dir(cfg), recurring_dir(cfg))
    )
    return dirs, (relative_to_root(root, log_path(cfg)),)


def _in_state_area(rel: str, areas: tuple[tuple[str, ...], tuple[str, ...]]) -> bool:
    dirs, files = areas
    return rel in files or any(rel.startswith(prefix) for prefix in dirs)


def _regular_working_file(root: Path, rel: str) -> tuple[str, bytes] | None | Literal[False]:
    """`(mode, bytes)` of a regular working file, `None` when absent, `False` otherwise."""
    path = root / rel
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    except NotADirectoryError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return False
    mode = "100755" if info.st_mode & 0o111 else "100644"
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
) -> str | None:
    """`None` when the working copy of `rel` is already on control, else why not."""
    if working is None:
        return None if published is None else "deleted here but present on control"
    if published is None:
        return "not on control"
    mode, data = working
    if mode != published[0]:
        return "file mode differs from control"
    if not union:
        if _hash_blob(root, data, rel) == published[1]:
            return None
        return "content differs from control"
    control_bytes = _blob_bytes(root, published[1])
    base = _blob_bytes(root, head_entry[1]) if head_entry is not None else b""
    merged = _merge_union_bytes(current=control_bytes, base=base, other=data)
    return None if merged == control_bytes else "lines not yet on control"


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


def _local_control_subsumed(cfg: Config, root: Path, local: str, target: str) -> _Subsumption:
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
        areas = _state_areas(cfg, root)
        foreign: list[str] = []
        offenders: list[str] = []
        for commit, subject in dropped:
            stage = f"listing the paths commit {commit[:12]} touches"
            touched = run_git(
                root, "diff-tree", "-r", "-z", "-m", "--root", "--no-commit-id",
                "--no-renames", "--name-only", commit,
            )
            outside = sorted({rel for rel in touched.split("\x00") if rel and not _in_state_area(rel, areas)})
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
                root, rel, working, published, head_entry=head_entry, union=rel in union
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


def last_commit_times(cfg: Config) -> dict[str, datetime]:
    """Map each path under `tasks/` to the commit time it was last touched.

    Keys are posix paths relative to `tasks/`. The fallback source for
    `coga status`'s `Updated` column when the log has no line for a task
    (moved directory, hand-authored ticket). Read-only; `{}` on any failure.
    """
    if not cfg.git_enabled:
        return {}
    root = toplevel(tasks_dir(cfg))
    if root is None:
        return {}
    rel = relative_to_root(root, tasks_dir(cfg))
    try:
        out = run_git(root, "log", "--format=%ct", "--name-only", "--", rel)
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
    """Keep only the `error:`/`fatal:`/`CONFLICT` lines of git output, deduped.

    Falls back to the last non-empty line so an unrecognized failure is never
    silently emptied.
    """
    keep: list[str] = []
    last = ""
    for raw in output.splitlines():
        line = raw.strip().split("\r")[-1].strip()
        if not line:
            continue
        last = line
        if line.startswith(("error:", "fatal:", "CONFLICT")) and line not in keep:
            keep.append(line)
    return "; ".join(keep) if keep else last


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
    result = _run(["git", "-C", str(start), "rev-parse", "--show-toplevel"])
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
    """`path` relative to the git root, without following a final symlink."""
    lexical = path.parent.resolve() / path.name
    try:
        return str(lexical.relative_to(root.resolve()))
    except ValueError:
        return str(lexical)


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
        raise GitError(f"`git hash-object` failed: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout.decode().strip()


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
    try:
        return (root / rel).read_bytes()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return None


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
    "PUBLISHED_REF",
    "RETRY_WITHOUT_SWEEP_EXIT_CODE",
    "STALE_CONTROL_EXIT_CODE",
    "StateRegressionError",
    "UncertainPublishError",
    "classify_checkout",
    "control_branch_mismatch_message",
    "control_branch_present",
    "current_branch",
    "fast_forward_control",
    "fetch_control",
    "is_linked_worktree",
    "last_commit_times",
    "prepare_control_checkout",
    "publish",
    "refresh",
    "relative_to_root",
    "remote_branch_oid",
    "remote_configured",
    "run_git",
    "stale_coga_task_rels",
    "state_lock",
    "state_sweep_withheld",
    "summarize_git_failure",
    "symbolic_head",
    "sync_coga_state",
    "sync_log",
    "sync_task_state",
    "ticket_regression_reason",
    "toplevel",
    "tree_bytes",
    "union_merge_paths",
    "worktree_holding_branch",
    "write_ticket",
]
