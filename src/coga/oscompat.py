"""Native locks and owned subprocess trees shared by launch and recurring work."""

from __future__ import annotations

import errno
import getpass
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

if os.name == "posix":
    import fcntl
else:
    import msvcrt


def lock_dir(prefix: str) -> Path:
    """Locate a user's locks outside every checkout (keep POSIX names stable)."""
    user = str(os.getuid()) if os.name == "posix" else re.sub(
        r"[^a-zA-Z0-9_.-]", "_", getpass.getuser()
    )
    return Path(tempfile.gettempdir()) / f"{prefix}-{user}"


def lock_fd(fd: int, *, blocking: bool) -> None:
    """Lock byte zero on Windows, or the file on POSIX; wait without a limit."""
    if os.name == "posix":
        fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        return
    while True:
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise
            if not blocking:
                raise BlockingIOError(exc.errno, str(exc)) from exc
            # LK_LOCK gives up after ten retries; state publication must wait
            # indefinitely, including when a competing publish uses a network.
            time.sleep(0.05)


def unlock_fd(fd: int) -> None:
    if os.name == "posix":
        fcntl.flock(fd, fcntl.LOCK_UN)
    else:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


def process_exit_status(code: int, *, windows: bool | None = None) -> int:
    """The value to pass to ``SystemExit`` so a parent observes ``code``.

    Windows exit codes are DWORDs, but Python 3.11 converts a ``SystemExit``
    code through a signed 32-bit C long there, so an unsigned NTSTATUS such as
    0xC0000005 would overflow to -1. Its signed equivalent leaves the same
    DWORD. Codes below 0x80000000, and every POSIX code, pass unchanged.
    """
    if windows is None:
        windows = os.name == "nt"
    if windows and 0x80000000 <= code <= 0xFFFFFFFF:
        return code - 0x100000000
    return code


def process_is_running(pid: int) -> bool:
    """Inspect ownership conservatively, never sending a Windows signal."""
    if pid <= 0:
        return True
    if os.name == "posix":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except OSError:
            pass
        return True
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
    if not handle:
        return ctypes.get_last_error() != 87  # ERROR_INVALID_PARAMETER: no PID
    try:
        return kernel.WaitForSingleObject(handle, 0) != 0  # WAIT_OBJECT_0
    finally:
        kernel.CloseHandle(handle)


def process_tree_is_running(identity: int | str) -> bool:
    """Probe a persisted PGID or named Job Object; uncertainty retains work."""
    if os.name == "posix":
        if not isinstance(identity, int) or identity <= 0:
            return True
        try:
            os.killpg(identity, 0)
        except ProcessLookupError:
            return False
        except OSError:
            pass
        return True
    if not isinstance(identity, str) or not re.fullmatch(
        r"Global\\coga-process-[0-9a-f]{32}", identity
    ):
        return True
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenJobObjectW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
    kernel.OpenJobObjectW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    handle = kernel.OpenJobObjectW(0x0004, False, identity)  # JOB_OBJECT_QUERY
    if not handle:
        return ctypes.get_last_error() != 2  # ERROR_FILE_NOT_FOUND
    try:
        return _job_has_processes(kernel, handle)
    except OSError:
        return True
    finally:
        kernel.CloseHandle(handle)


def _job_has_processes(kernel, handle: int) -> bool:
    import ctypes

    class Accounting(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", ctypes.c_int64),
            ("TotalKernelTime", ctypes.c_int64),
            ("ThisPeriodTotalUserTime", ctypes.c_int64),
            ("ThisPeriodTotalKernelTime", ctypes.c_int64),
            ("TotalPageFaultCount", ctypes.c_uint32),
            ("TotalProcesses", ctypes.c_uint32),
            ("ActiveProcesses", ctypes.c_uint32),
            ("TotalTerminatedProcesses", ctypes.c_uint32),
        ]

    kernel.QueryInformationJobObject.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    kernel.QueryInformationJobObject.restype = ctypes.c_int
    info = Accounting()
    if not kernel.QueryInformationJobObject(
        handle, 1, ctypes.byref(info), ctypes.sizeof(info), None,
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return info.ActiveProcesses != 0


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


_INTERACTIVE_WRAPPER = Path(__file__).with_name("_nt_session_wrapper.py")

# Fixed-width names, so a command-line budget measured with these
# placeholders holds for every real uuid4 hex identifier.
JOB_NAME_PLACEHOLDER = "Global\\coga-process-" + "0" * 32
GATE_NAME_PLACEHOLDER = "Local\\coga-gate-" + "0" * 32


def _wrapper_python() -> str:
    # A venv launcher owns another kill-on-close job. Nesting our job inside
    # it would kill descendants when the wrapper exits, before our supervisor
    # decides whether the tree has finished or timed out. The stdlib-only
    # wrappers need no venv; the requested argv keeps it.
    return getattr(sys, "_base_executable", None) or sys.executable


def interactive_wrapper_argv(
    job_name: str,
    gate_name: str | None,
    argv: list[str],
    shell: tuple[str, str] | None = None,
) -> list[str]:
    """The exact interactive-wrapper argv, also used to measure its budget.

    ``argv[0]`` must already be the resolved executable. With ``shell``
    (absolute ``cmd.exe``, raw command line) the wrapper runs that line
    instead of ``argv``; the native argv is then not passed at all.
    """
    head = [_wrapper_python(), "-I", str(_INTERACTIVE_WRAPPER), job_name, gate_name or "-"]
    if shell is not None:
        return [*head, "shell", *shell]
    return [*head, "native", *argv]


class _WindowsGate:
    """A per-spawn named manual-reset event the held wrapper waits on."""

    def __init__(self) -> None:
        import ctypes

        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateEventW.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p,
        ]
        self._kernel.CreateEventW.restype = ctypes.c_void_p
        self._kernel.SetEvent.argtypes = [ctypes.c_void_p]
        self._kernel.SetEvent.restype = ctypes.c_int
        self._kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self._kernel.CloseHandle.restype = ctypes.c_int
        self.name = f"Local\\coga-gate-{uuid4().hex}"
        self._handle = self._kernel.CreateEventW(None, True, False, self.name)
        if not self._handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            self.close()
            raise FileExistsError(f"gate event {self.name} already exists")

    def release(self) -> None:
        import ctypes

        if not self._kernel.SetEvent(self._handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self._handle:
            self._kernel.CloseHandle(self._handle)
            self._handle = None


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
        self.name = f"Global\\coga-process-{uuid4().hex}"
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
        return [_wrapper_python(), "-c", _WINDOWS_JOB_WRAPPER, self.name, *argv]

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

    def wait_started(self, process: subprocess.Popen) -> None:
        """Do not expose a tree whose wrapper can still enter after a stop."""
        deadline = time.monotonic() + 10
        while process.poll() is None:
            # A venv's python.exe can be a launcher waiting for the actual
            # interpreter. Its Popen handle need not itself join the job;
            # the wrapper's assignment is proven by the job's membership.
            if _job_has_processes(self._kernel, self._handle):
                return
            if time.monotonic() >= deadline:
                raise TimeoutError("Windows child did not join its process job")
            time.sleep(0.01)


class ProcessTree:
    """A child plus every descendant, even after the child exits.

    Callers retain their own POSIX timeout/TERM/KILL policy. Windows uses
    the clone runner's kill-on-close Job Object; ``kill``/``terminate`` end
    the whole Job. ``identity`` can be persisted for conservative recovery
    after a crash.

    The interactive agent supervisor opts into more, all Windows-only:
    ``interactive`` runs the signal-ignoring, lossless-exit wrapper (with
    ``shell`` as its batch-file transport), ``gate`` holds that wrapper after
    it joins the Job until ``release``, and ``new_process_group`` lets
    ``interrupt`` deliver CTRL_BREAK to the tree. Recurring and clone callers
    use none of them and keep their hard-kill semantics.
    """

    def __init__(
        self,
        argv: list[str],
        *,
        interactive: bool = False,
        gate: bool = False,
        new_process_group: bool = False,
        shell: tuple[str, str] | None = None,
        **kwargs,
    ) -> None:
        if (interactive or gate or shell is not None) and os.name != "nt":
            raise ValueError("interactive process trees are Windows-only")
        if (gate or shell is not None) and not interactive:
            raise ValueError("gate and shell require the interactive wrapper")
        self._job = _WindowsJob() if os.name == "nt" else None
        self._gate: _WindowsGate | None = None
        self.process: subprocess.Popen
        try:
            if gate:
                self._gate = _WindowsGate()
            if self._job is None:
                command = argv
            elif interactive:
                command = interactive_wrapper_argv(
                    self._job.name,
                    self._gate.name if self._gate is not None else None,
                    argv,
                    shell,
                )
            else:
                command = self._job.command(argv)
            if new_process_group and os.name == "nt":
                kwargs["creationflags"] = (
                    kwargs.get("creationflags", 0)
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            self.process = subprocess.Popen(
                command, start_new_session=os.name == "posix", **kwargs,
            )
            if self._job is not None:
                self._job.wait_started(self.process)
        except BaseException:
            # A failed startup must not leave a wrapper able to start user
            # code after its job has been terminated.
            if hasattr(self, "process"):
                self.process.kill()
                self.process.wait()
            if self._gate is not None:
                self._gate.close()
            if self._job is not None:
                self._job.close()
            raise

    @property
    def identity(self) -> int | str:
        return self._job.name if self._job is not None else self.process.pid

    def release(self) -> None:
        """Let a gated wrapper start its command (the admission commit)."""
        if self._gate is None:
            raise RuntimeError("process tree has no start gate")
        self._gate.release()

    def interrupt(self) -> None:
        """Ask the tree to stop: CTRL_BREAK on Windows, SIGINT on POSIX."""
        if self._job is not None:
            import ctypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GenerateConsoleCtrlEvent.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
            kernel.GenerateConsoleCtrlEvent.restype = ctypes.c_int
            if not kernel.GenerateConsoleCtrlEvent(1, self.process.pid):  # CTRL_BREAK_EVENT
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            os.killpg(self.process.pid, signal.SIGINT)

    def terminate(self) -> None:
        if self._job is not None:
            self._job.terminate()
        else:
            os.killpg(self.process.pid, signal.SIGTERM)

    def kill(self) -> None:
        if self._job is not None:
            self._job.terminate()
        else:
            os.killpg(self.process.pid, signal.SIGKILL)

    def exists(self) -> bool:
        if self._job is not None:
            return _job_has_processes(self._job._kernel, self._job._handle)
        return process_tree_is_running(self.identity)

    def wait_empty(self, *, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while self.exists():
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        return True

    def close(self) -> None:
        try:
            if self._job is not None and self._job._handle is not None:
                try:
                    self._job.terminate()
                    if not self.wait_empty(timeout=10):
                        raise TimeoutError("Windows process job did not stop")
                finally:
                    self._job.close()
        finally:
            if self._gate is not None:
                self._gate.close()

    def __enter__(self) -> ProcessTree:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
