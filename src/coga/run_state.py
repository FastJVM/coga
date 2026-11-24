"""Coga-managed unversioned state: the durable `data/` and per-launch `tmp/` areas.

The layout lives under the machine-local `.coga/` directory that `coga init`
already ignores (`coga/launch` "Run state" owns the contract):

    <coga root>/.coga/
      data/tasks/<id_slug>/    durable, one per task          (COGA_TASK_DATA_DIR)
      data/bootstrap/<name>/   durable, one per bootstrap target
      data/_shared/            durable, cross-ticket state
      tmp/<token>/             one per launch                 (TMPDIR, TMP, TEMP)
      tmp/<token>.lock         liveness lock held by that launch

`data/` resolves to the primary checkout when the configured root is inside a
linked Git worktree, so durable state survives `git worktree remove`; `tmp/`
always belongs to the current checkout. Each owned data directory carries a
`.coga-owner` record naming its target, which makes attribution independent of
how task paths nest.
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import stat
import sys
import tempfile
import time
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from coga.config import Config
from coga.oscompat import SYSTEM_TMPDIR_ENV, lock_fd, system_tmpdir, unlock_fd
from coga.tasks import BootstrapRef, TargetRef

DATA_DIR_ENV = "COGA_DATA_DIR"
TASK_DATA_DIR_ENV = "COGA_TASK_DATA_DIR"
TMP_ENV_NAMES = ("TMPDIR", "TMP", "TEMP")
SHARED = "_shared"
OWNER_FILE = ".coga-owner"
SOCKET_WARN_BYTES = 64
ORPHAN_GRACE_SECONDS = 60.0

_TOKEN_RE = re.compile(r"^[0-9a-f]{8}$")


# --- layout -------------------------------------------------------------------


def state_root(cfg: Config) -> Path:
    """This checkout's machine-local `.coga/` directory."""
    return cfg.repo_root / ".coga"


def tmp_root(cfg: Config) -> Path:
    return state_root(cfg) / "tmp"


def data_root(cfg: Config) -> Path:
    """The durable area, in the primary checkout when run from a linked worktree."""
    return _primary_coga_root(cfg.repo_root.resolve()) / ".coga" / "data"


@lru_cache(maxsize=None)
def _primary_coga_root(repo_root: Path) -> Path:
    """Map a Coga root in a linked worktree to the same root in the primary checkout.

    Reads Git's on-disk worktree link (`.git` file → `gitdir` → `commondir`)
    instead of running `git`, so building a launch environment stays a pure
    filesystem read. Falls back to `repo_root` outside Git, in a submodule or
    a separate-git-dir checkout, or when the primary checkout has no such
    directory. Coga works without Git; this only refines where data lives.
    """
    for toplevel in (repo_root, *repo_root.parents):
        marker = toplevel / ".git"
        if marker.is_dir():
            return repo_root
        if marker.is_file():
            break
    else:
        return repo_root
    try:
        line = marker.read_text(encoding="utf-8").strip()
        if not line.startswith("gitdir:"):
            return repo_root
        gitdir = Path(line[len("gitdir:"):].strip())
        if not gitdir.is_absolute():
            gitdir = toplevel / gitdir
        common = (gitdir / "commondir").read_text(encoding="utf-8").strip()
    except OSError:
        return repo_root
    common_dir = Path(common) if Path(common).is_absolute() else gitdir / common
    common_dir = common_dir.resolve()
    if common_dir.name != ".git":
        return repo_root
    candidate = common_dir.parent / repo_root.relative_to(toplevel)
    return candidate if candidate.is_dir() else repo_root


def task_data_dir(cfg: Config, ref: TargetRef) -> Path:
    """The durable directory owned by one target; collision-free by kind."""
    if isinstance(ref, BootstrapRef):
        return data_root(cfg) / "bootstrap" / ref.name
    return data_root(cfg) / "tasks" / ref.id_slug


def _owner_record(ref: TargetRef) -> str:
    kind = "bootstrap" if isinstance(ref, BootstrapRef) else "task"
    return f"{kind} {ref.id_slug}\n"


def ensure_layout(repo_root: Path) -> None:
    """Create the durable and temporary roots for a Coga root (idempotent).

    Takes the root rather than a loaded config so `coga init` can call it on
    the scaffold it is still building.
    """
    (_primary_coga_root(repo_root.resolve()) / ".coga" / "data").mkdir(
        parents=True, exist_ok=True
    )
    (repo_root / ".coga" / "tmp").mkdir(parents=True, exist_ok=True)


def ensure_task_data_dir(cfg: Config, ref: TargetRef) -> Path:
    """Create a target's durable directory and its ownership record."""
    path = task_data_dir(cfg, ref)
    path.mkdir(parents=True, exist_ok=True)
    record = path / OWNER_FILE
    if not record.is_file():
        record.write_text(_owner_record(ref), encoding="utf-8")
    return path


def data_env(cfg: Config, ref: TargetRef | None) -> dict[str, str]:
    """The data variables for an executor; `ref=None` has no task identity."""
    env = {DATA_DIR_ENV: str(data_root(cfg))}
    if ref is not None:
        env[TASK_DATA_DIR_ENV] = str(task_data_dir(cfg, ref))
    return env


# --- tmp scope ----------------------------------------------------------------


@dataclass(frozen=True)
class TmpScope:
    path: Path
    env_overrides: Mapping[str, str]


def apply_tmp_env(env: Mapping[str, str], scope: TmpScope | None) -> dict[str, str]:
    """Return a copy of `env` with the scope's temp redirection applied."""
    updated = dict(env)
    if scope is not None:
        updated.update(scope.env_overrides)
    return updated


@contextmanager
def launch_tmp_scope(cfg: Config, *, sweep: bool = True) -> Iterator[TmpScope]:
    """Own one `tmp/<token>/` for the duration of a launch.

    The original system temp is captured before any override so Coga's own
    temp users keep resolving to it in nested processes. On exit, normal or
    not, the directory is removed while the lock is still held, then the lock
    file is retired; removal problems warn and never fail the launch.
    `sweep=False` (read-only dispatch) never removes another launch's state.
    """
    system_tmp = system_tmpdir()
    root = tmp_root(cfg)
    root.mkdir(parents=True, exist_ok=True)
    if sweep:
        for failure in sweep_orphans(cfg).failures:
            _warn(failure)
    fd, token = _create_locked_token(root)
    path = root / token
    lock_path = root / f"{token}.lock"
    created = False
    try:
        path.mkdir()
        created = True
        absolute = str(path.resolve())
        if len(absolute.encode()) > SOCKET_WARN_BYTES:
            _warn(
                f"run-state tmp path is {len(absolute.encode())} bytes ({absolute}); "
                "Unix socket paths are limited to about 108 bytes, so tools that "
                "create sockets under $TMPDIR may fail"
            )
        overrides = {name: absolute for name in TMP_ENV_NAMES}
        overrides[SYSTEM_TMPDIR_ENV] = system_tmp
        yield TmpScope(path=Path(absolute), env_overrides=overrides)
    finally:
        try:
            problems = _remove_tree(path) if created else []
        finally:
            lock_problems = _retire_lock(fd, lock_path)
        problems.extend(lock_problems)
        if problems:
            _warn(f"could not fully remove launch tmp {path}: {', '.join(problems)}")


def _create_locked_token(root: Path) -> tuple[int, str]:
    while True:
        token = secrets.token_hex(4)
        lock_path = root / f"{token}.lock"
        if os.path.lexists(root / token):
            continue
        fd = _try_lock(lock_path, create=True)
        if fd is not None:
            return fd, token


def _retire_lock(fd: int, lock_path: Path) -> list[str]:
    """Remove a held lock file and release it, in the order each OS allows."""
    problems: list[str] = []
    if os.name == "posix":
        # Unlink while held: a sweeper that opened the old inode re-checks
        # identity after locking and finds the path gone.
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            problems.append(f"{lock_path}: {exc}")
        os.close(fd)
        return problems
    # Windows cannot delete an open file: release, close, then unlink. A lock
    # file left by a racing opener is retired by a later sweep.
    try:
        unlock_fd(fd)
    except OSError:
        pass
    os.close(fd)
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        problems.append(f"{lock_path}: {exc}")
    return problems


def _remove_tree(path: Path) -> list[str]:
    """Remove a Coga-owned tmp tree, including read-only parts tools left in it.

    A first pass that hits a permission error makes the remaining tree
    owner-writable (never following symlinks out of it) and retries once.
    """
    if not os.path.lexists(path):
        return []
    problems: list[str] = []
    denied = False

    def record(_func, failed, exc_info) -> None:
        nonlocal denied
        exc = exc_info[1] if isinstance(exc_info, tuple) else exc_info
        denied = denied or isinstance(exc, PermissionError)
        problems.append(f"{failed}: {exc}")

    def rmtree() -> None:
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=record)
        else:  # pragma: no cover - exercised on 3.11 only
            shutil.rmtree(path, onerror=record)

    rmtree()
    if denied and os.path.lexists(path):
        problems.clear()
        _make_owner_writable(path)
        rmtree()
    return problems


def _make_owner_writable(root: Path) -> None:
    """Grant the owner rwx on directories and w on files under ``root``."""
    pending = [str(root)]
    while pending:
        current = pending.pop()
        try:
            mode = os.lstat(current).st_mode
            if stat.S_ISLNK(mode):
                continue
            if stat.S_ISDIR(mode):
                os.chmod(current, stat.S_IMODE(mode) | stat.S_IRWXU)
                with os.scandir(current) as entries:
                    pending.extend(entry.path for entry in entries)
            else:
                os.chmod(current, stat.S_IMODE(mode) | stat.S_IWUSR)
        except OSError:
            continue  # the retry reports whatever still cannot be removed


def _warn(message: str) -> None:
    sys.stderr.write(f"Warning: {message}\n")


# --- orphans ------------------------------------------------------------------


@dataclass(frozen=True)
class Orphan:
    token: str
    path: Path
    lock_path: Path

    @property
    def dir_exists(self) -> bool:
        return self.path.is_dir()


@dataclass
class SweepResult:
    removed: list[Orphan] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def _tokens(root: Path) -> list[str]:
    try:
        names = os.listdir(root)
    except FileNotFoundError:
        return []
    tokens: set[str] = set()
    for name in names:
        stem = name[: -len(".lock")] if name.endswith(".lock") else name
        if _TOKEN_RE.match(stem):
            tokens.add(stem)
    return sorted(tokens)


def _grace_expired(path: Path, now: float) -> bool:
    try:
        return now - path.lstat().st_mtime >= ORPHAN_GRACE_SECONDS
    except FileNotFoundError:
        return False


def _try_lock(lock_path: Path, *, create: bool = False) -> int | None:
    """Take the named lock without waiting, optionally creating it exclusively."""
    flags = os.O_RDWR | (os.O_CREAT | os.O_EXCL if create else 0)
    try:
        fd = os.open(lock_path, flags, 0o600)
    except FileExistsError:
        return None
    except FileNotFoundError:
        if create:
            raise
        return None
    keep = False
    try:
        lock_fd(fd, blocking=False)
        # A sweeper may have retired the inode before even its creator locked it.
        # Windows prevents unlink while our descriptor is open.
        keep = os.name != "posix" or os.path.samestat(lock_path.stat(), os.fstat(fd))
        return fd if keep else None
    except (BlockingIOError, PermissionError, FileNotFoundError):
        return None
    finally:
        if not keep:
            os.close(fd)


def _classify(root: Path, token: str, now: float) -> tuple[str, int | None]:
    """Return ("live" | "orphan" | "grace", held lock fd for an orphan with a lock)."""
    path, lock_path = root / token, root / f"{token}.lock"
    if os.path.lexists(lock_path):
        fd = _try_lock(lock_path)
        if fd is None:
            return ("live" if os.path.lexists(lock_path) else "grace"), None
        return "orphan", fd
    return ("orphan" if _grace_expired(path, now) else "grace"), None


def find_orphans(cfg: Config) -> list[Orphan]:
    """Report unowned tmp areas without removing or creating anything."""
    root = tmp_root(cfg)
    now = time.time()
    orphans: list[Orphan] = []
    for token in _tokens(root):
        verdict, fd = _classify(root, token, now)
        if fd is not None:
            try:
                unlock_fd(fd)
            except OSError:
                pass
            os.close(fd)
        if verdict == "orphan":
            orphans.append(Orphan(token, root / token, root / f"{token}.lock"))
    return orphans


def sweep_orphans(cfg: Config) -> SweepResult:
    """Remove every tmp area whose launch is gone, holding its lock throughout."""
    root = tmp_root(cfg)
    now = time.time()
    result = SweepResult()
    for token in _tokens(root):
        verdict, fd = _classify(root, token, now)
        if verdict != "orphan":
            continue
        orphan = Orphan(token, root / token, root / f"{token}.lock")
        if fd is None:
            fd = _try_lock(orphan.lock_path, create=True)
            if fd is None:
                continue
            # The original directory may have been replaced before we claimed it.
            if not _grace_expired(orphan.path, now):
                for problem in _retire_lock(fd, orphan.lock_path):
                    result.failures.append(f"could not retire orphan lock: {problem}")
                continue
        try:
            problems = _remove_tree(orphan.path)
        finally:
            lock_problems = _retire_lock(fd, orphan.lock_path)
        problems.extend(lock_problems)
        if problems:
            result.failures.extend(
                f"could not remove orphan tmp {orphan.path}: {p}" for p in problems
            )
        else:
            result.removed.append(orphan)
    return result


# --- usage --------------------------------------------------------------------


@dataclass
class StateEntry:
    owner: str          # "<id_slug>" | "(shared)" | "(unattributed)" | "(tmp)"
    path: str
    bytes: int
    files: int
    kind: str           # "data" | "tmp-live" | "tmp-orphan"
    target: str | None = None  # "task" | "bootstrap" for owned data entries


@dataclass
class StateReport:
    root: str
    data_root: str
    total_bytes: int = 0
    entries: list[StateEntry] = field(default_factory=list)


def _walk_files(top: Path) -> Iterator[tuple[Path, int, bool]]:
    """Yield (path, size, is_dir) for everything under `top`, never following links."""
    stack = [top]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                items = list(it)
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            continue
        for item in items:
            path = Path(item.path)
            try:
                info = item.stat(follow_symlinks=False)
            except OSError:
                continue
            if stat.S_ISDIR(info.st_mode):
                yield path, 0, True
                stack.append(path)
            else:
                yield path, info.st_size, False


def read_owner(directory: Path) -> tuple[str, str] | None:
    """Return (kind, id_slug) from a `.coga-owner` record, or None."""
    try:
        text = (directory / OWNER_FILE).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    kind, _, slug = text.partition(" ")
    if kind not in {"task", "bootstrap"} or not slug:
        return None
    return kind, slug


def _data_entries(root: Path) -> list[StateEntry]:
    if not root.is_dir():
        return []
    files: list[tuple[Path, int]] = []
    owners: dict[Path, tuple[str, str | None]] = {root / SHARED: ("(shared)", None)}
    for path, size, is_dir in _walk_files(root):
        if is_dir:
            record = read_owner(path)
            if record is not None:
                owners[path] = (record[1], record[0])
        elif path.name != OWNER_FILE:
            files.append((path, size))
    owner_ancestors = {parent for owner in owners for parent in owner.parents}

    totals: dict[Path, list] = {}
    for path, size in files:
        key: Path | None = None
        for parent in path.parents:
            if parent in owners:
                key = parent
                break
            if parent == root:
                break
        if key is None:
            # The topmost directory below the root that holds no owner, or the
            # file itself when it sits beside owned directories.
            relative = path.relative_to(root)
            key = path
            candidate = root
            for part in relative.parts[:-1]:
                candidate = candidate / part
                if candidate not in owner_ancestors:
                    key = candidate
                    break
        bucket = totals.setdefault(key, [0, 0])
        bucket[0] += size
        bucket[1] += 1

    entries = []
    for key, (size, count) in sorted(totals.items(), key=lambda item: str(item[0])):
        owner, target = owners.get(key, ("(unattributed)", None))
        entries.append(StateEntry(owner, str(key), size, count, "data", target))
    return entries


def _tmp_entries(cfg: Config) -> list[StateEntry]:
    root = tmp_root(cfg)
    orphan_tokens = {o.token for o in find_orphans(cfg)}
    entries = []
    for token in _tokens(root):
        path = root / token
        if not path.is_dir():
            continue
        size = count = 0
        for _p, s, is_dir in _walk_files(path):
            if not is_dir:
                size += s
                count += 1
        if count == 0:
            continue
        kind = "tmp-orphan" if token in orphan_tokens else "tmp-live"
        entries.append(StateEntry("(tmp)", str(path), size, count, kind))
    return entries


def usage(cfg: Config, *, ref: TargetRef | None = None) -> StateReport:
    """Walk managed state read-only; `ref` limits the report to one target's data."""
    report = StateReport(root=str(state_root(cfg)), data_root=str(data_root(cfg)))
    entries = _data_entries(data_root(cfg))
    if ref is not None:
        own = str(task_data_dir(cfg, ref))
        entries = [e for e in entries if e.path == own]
    else:
        entries.extend(_tmp_entries(cfg))
    report.entries = entries
    report.total_bytes = sum(e.bytes for e in entries)
    return report


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"  # pragma: no cover


def owned_entries(report: StateReport) -> Iterable[StateEntry]:
    return (e for e in report.entries if e.kind == "data" and e.target is not None)
