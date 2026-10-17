"""Clone-scoped recurring templates: per-clone work with no shared period task.

A recurring template is `scope: repo` by default: one shared period task per
firing, serviced by whichever clone sweeps first and recorded in `coga/log.md`.
That is wrong for work on clone- or machine-local state — local branch refs,
linked worktrees, machine-local `[upstream]` paths — because every other clone
of the repository never runs it. A `scope: clone` template is instead serviced
once per period *in every clone*: the sweep runs its reserved `ticket.py`
directly, with no period task or log line, and records the serviced period in
a clone-local ledger under the primary checkout's `.coga/`. The runner makes
no commit; a template may publish its own state under the scheduling contract.

The ledger lives in the primary checkout (resolved through git's common dir),
not in whichever working tree the sweep ran from, so a run serviced from a
temporary control worktree still counts for the clone that owns it.

The `coga/recurring/scheduling` context owns this contract.
"""

from __future__ import annotations

import codecs
import json
import math
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from coga import git
from coga.atomicio import atomic_write_text
from coga.config import Config, build_launch_env
from coga.task_env import TASK_ENV_KEYS, host_repo_root

SCOPE_REPO = "repo"
SCOPE_CLONE = "clone"
SCOPES = (SCOPE_REPO, SCOPE_CLONE)

# What a clone-scoped `ticket.py` can read to tell it is not inside a period
# task (no `COGA_TASK_SLUG`, nothing to bump) and which period it services.
SCOPE_ENV = "COGA_RECURRING_SCOPE"
TEMPLATE_ENV = "COGA_RECURRING_TEMPLATE"
PERIOD_ENV = "COGA_RECURRING_PERIOD"

_STATE_DIR = Path(".coga") / "recurring-clone"
# Bounded so a chatty run cannot grow the run record without limit.
_OUTPUT_TAIL_CHARS = 4000
_OUTPUT_LOG_CHARS = 1_000_000
_CLONE_SCRIPT_TIMEOUT = 15 * 60
_TERMINATE_GRACE = 2.0
_TRUNCATED = "\n[output truncated; final output follows in the log]\n"


@dataclass(frozen=True)
class CloneLedgerEntry:
    period: str
    serviced_at: str


@dataclass(frozen=True)
class CloneRunResult:
    template: str
    period: str
    exit_code: int
    output: str
    log_path: Path


def clone_state_dir(cfg: Config) -> Path:
    """The clone-local state directory, anchored at the primary checkout.

    A linked worktree (the temporary control worktree `--all` services an
    off-control clone from) shares refs with its primary, so it records against
    the primary's Coga workspace at the same relative path. Outside git, or when
    git cannot say, the invoking workspace is the clone.
    """
    root = cfg.repo_root
    if cfg.git_enabled:
        try:
            top = git.toplevel(root)
        except git.GitError:
            top = None
        if top is not None:
            try:
                common = Path(
                    git.run_git(
                        top, "rev-parse", "--path-format=absolute", "--git-common-dir"
                    ).strip()
                )
            except git.GitError:
                common = None
            if common is not None and common.name == ".git":
                primary = common.parent
                try:
                    rel = cfg.repo_root.resolve().relative_to(top.resolve())
                except ValueError:
                    rel = Path()
                root = primary / rel
    return root / _STATE_DIR


def _ledger_path(cfg: Config, name: str) -> Path:
    return clone_state_dir(cfg) / f"{name}.json"


def _log_path(cfg: Config, name: str) -> Path:
    return clone_state_dir(cfg) / f"{name}.log"


def read_clone_ledger(cfg: Config, name: str) -> CloneLedgerEntry | None:
    """The last period this clone serviced for `name`, or `None`.

    An unreadable or malformed ledger file reads as never serviced: the cost is
    one extra run of an idempotent per-clone job, never a skipped one.
    """
    path = _ledger_path(cfg, name)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("period"), str):
        return None
    return CloneLedgerEntry(
        period=data["period"], serviced_at=str(data.get("serviced_at", ""))
    )


def record_clone_period(cfg: Config, name: str, period: str, now: datetime) -> None:
    path = _ledger_path(cfg, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        path,
        json.dumps(
            {"period": period, "serviced_at": now.isoformat(timespec="seconds")},
            indent=2,
        )
        + "\n",
    )


def run_clone_template(
    cfg: Config,
    name: str,
    script: Path,
    period: str,
    *,
    secrets: object = None,
    now: datetime | None = None,
    timeout: float = _CLONE_SCRIPT_TIMEOUT,
) -> CloneRunResult:
    """Run one clone-scoped template's `ticket.py` and record a clean exit.

    The script runs from the host repository with the template's declared
    secrets and none of the period-task variables, so a shim that would bump a
    task cannot find one. Output is echoed, kept in a per-template log beside
    the ledger, and returned for the sweep's run record. Only exit 0 advances
    the ledger; a failure is retried by the next sweep.
    """
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("clone script timeout must be finite and positive")
    now = now or datetime.now()
    env = build_launch_env(cfg, secrets)
    for key in TASK_ENV_KEYS:
        env.pop(key, None)
    env["COGA_COGA_OS_ROOT"] = str(cfg.repo_root.resolve())
    env["COGA_REPO_ROOT"] = str(host_repo_root(cfg).resolve())
    env[SCOPE_ENV] = SCOPE_CLONE
    env[TEMPLATE_ENV] = name
    env[PERIOD_ENV] = period
    exit_code, output, log_output = _run_clone_script(
        [sys.executable, str(script)],
        cwd=host_repo_root(cfg),
        env=env,
        timeout=timeout,
    )
    log_path = _log_path(cfg, name)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            log_path,
            f"# {name} — period {period} — {now.isoformat(timespec='seconds')} "
            f"— exit {exit_code}\n\n{log_output}",
        )
    except OSError as exc:
        sys.stderr.write(f"Warning: could not write {log_path}: {exc}\n")
    if exit_code == 0:
        record_clone_period(cfg, name, period, now)
    return CloneRunResult(
        template=name,
        period=period,
        exit_code=exit_code,
        output=output,
        log_path=log_path,
    )


_WINDOWS_JOB_WRAPPER = """
import ctypes
import subprocess
import sys

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.OpenJobObjectW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
kernel.OpenJobObjectW.restype = ctypes.c_void_p
kernel.GetCurrentProcess.argtypes = []
kernel.GetCurrentProcess.restype = ctypes.c_void_p
kernel.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
kernel.AssignProcessToJobObject.restype = ctypes.c_int
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
kernel.CloseHandle.restype = ctypes.c_int
job = kernel.OpenJobObjectW(0x0001, False, sys.argv[1])  # JOB_OBJECT_ASSIGN_PROCESS
if not job:
    raise ctypes.WinError(ctypes.get_last_error())
try:
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
finally:
    if not kernel.CloseHandle(job):
        raise ctypes.WinError(ctypes.get_last_error())
# Join before starting any script code; descendants inherit the job. The
# supervisor alone retains a handle, so its exit also terminates the tree.
raise SystemExit(subprocess.call(sys.argv[2:]))
"""


class _WindowsJob:
    """Retain process-tree ownership even after the script's parent exits."""

    def __init__(self) -> None:
        import ctypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32),
            ]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimits),
                ("IoInfo", ctypes.c_uint64 * 6),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        self._kernel.CreateJobObjectW.restype = ctypes.c_void_p
        self._kernel.SetInformationJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
        ]
        self._kernel.SetInformationJobObject.restype = ctypes.c_int
        self._kernel.TerminateJobObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self._kernel.TerminateJobObject.restype = ctypes.c_int
        self._kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self._kernel.CloseHandle.restype = ctypes.c_int
        self.name = f"Local\\coga-clone-{uuid4().hex}"
        self._handle = self._kernel.CreateJobObjectW(None, self.name)
        if not self._handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        try:
            if not self._kernel.SetInformationJobObject(
                self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits),
            ):  # JobObjectExtendedLimitInformation
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> _WindowsJob:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def command(self, argv: list[str]) -> list[str]:
        return [sys.executable, "-c", _WINDOWS_JOB_WRAPPER, self.name, *argv]

    def terminate(self) -> None:
        import ctypes

        if not self._kernel.TerminateJobObject(self._handle, 124):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        import ctypes

        if self._handle:
            if not self._kernel.CloseHandle(self._handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self._handle = None


def _stop_clone_script(
    child: subprocess.Popen[bytes], job: _WindowsJob | None = None,
) -> None:
    """Stop the script's process group and reap the direct child."""
    if job is not None:
        job.terminate()
    elif os.name == "posix":
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=_TERMINATE_GRACE)
        except subprocess.TimeoutExpired:
            pass
        # The parent may exit before descendants that still hold stdout open.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        child.kill()
    child.wait(timeout=_TERMINATE_GRACE)


def _run_clone_script(
    argv: list[str], *, cwd: Path, env: dict[str, str], timeout: float,
) -> tuple[int, str, str]:
    if os.name == "nt":
        with _WindowsJob() as job:
            return _drain_clone_script(
                job.command(argv), cwd=cwd, env=env, timeout=timeout, job=job,
            )
    return _drain_clone_script(argv, cwd=cwd, env=env, timeout=timeout)


def _drain_clone_script(
    argv: list[str], *, cwd: Path, env: dict[str, str], timeout: float,
    job: _WindowsJob | None = None,
) -> tuple[int, str, str]:
    """Drain stdout with bounded storage, including while enforcing a deadline."""
    child = subprocess.Popen(
        argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, bufsize=0,
        start_new_session=os.name == "posix",
    )
    assert child.stdout is not None
    chunks: queue.Queue[bytes | OSError | None] = queue.Queue(maxsize=8)
    stop = threading.Event()

    def offer(chunk: bytes | OSError | None) -> None:
        while not stop.is_set():
            try:
                chunks.put(chunk, timeout=0.1)
                return
            except queue.Full:
                pass

    def read_output() -> None:
        try:
            while not stop.is_set():
                chunk = child.stdout.read(8192)
                if not chunk:
                    break
                offer(chunk)
        except OSError as exc:
            offer(exc)
        finally:
            offer(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    log_chunks: list[str] = []
    log_chars = 0
    tail = ""
    truncated = False

    def consume(text: str) -> None:
        nonlocal log_chars, tail, truncated
        tail = (tail + text)[-_OUTPUT_TAIL_CHARS:]
        prefix = text[:max(0, _OUTPUT_LOG_CHARS - log_chars)]
        if prefix:
            log_chunks.append(prefix)
            log_chars += len(prefix)
            sys.stdout.write(prefix)
        if len(prefix) < len(text) and not truncated:
            truncated = True
            sys.stdout.write(_TRUNCATED)

    deadline = time.monotonic() + timeout
    eof = False
    timed_out = False
    stopped = False
    try:
        while not eof or child.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                _stop_clone_script(child, job)
                stopped = True
                break
            try:
                chunk = chunks.get(timeout=min(0.1, remaining))
            except queue.Empty:
                continue
            if isinstance(chunk, OSError):
                raise chunk
            if chunk is None:
                eof = True
            else:
                consume(decoder.decode(chunk))
        if timed_out:
            # Drain only already queued bytes; a detached descendant must not
            # keep the sweep waiting for EOF after its parent has been stopped.
            while True:
                try:
                    chunk = chunks.get_nowait()
                except queue.Empty:
                    break
                if isinstance(chunk, bytes):
                    consume(decoder.decode(chunk))
        consume(decoder.decode(b"", final=True))
    finally:
        stop.set()
        try:
            if not stopped and (child.poll() is None or not eof):
                _stop_clone_script(child, job)
        finally:
            # Kill-on-close is also the fallback if explicit termination fails.
            # Release ownership before joining a reader waiting on descendants.
            if job is not None:
                job.close()
                child.wait(timeout=_TERMINATE_GRACE)
            reader.join(timeout=_TERMINATE_GRACE)
            child.stdout.close()
    exit_code = 124 if timed_out else child.returncode
    assert exit_code is not None
    log_output = "".join(log_chunks)
    if truncated:
        log_output += _TRUNCATED + tail
    if timed_out:
        reason = f"\nClone script timed out after {timeout:g}s (exit 124).\n"
        sys.stderr.write(reason)
        tail = (tail + reason)[-_OUTPUT_TAIL_CHARS:]
        log_output += reason
    return exit_code, tail, log_output

