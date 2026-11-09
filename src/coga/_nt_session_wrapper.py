"""Join a Coga Job Object, wait for admission, then run one interactive agent.

``oscompat.ProcessTree(interactive=True)`` runs this file by path with the
base interpreter in isolated mode (``python -I``), so it imports only the
standard library. Arguments: the Job name, the gate event name (``-`` for
none), the mode, then either ``native <executable> <argv...>`` or
``shell <cmd.exe> <raw command line>``.
"""

import ctypes
import signal
import subprocess
import sys


def _signed_exit_status(code: int) -> int:
    # Python 3.11 converts SystemExit codes through a signed 32-bit C long on
    # Windows; an unsigned NTSTATUS would overflow to -1. The signed
    # equivalent leaves the same DWORD for GetExitCodeProcess.
    code &= 0xFFFFFFFF
    return code if code < 0x80000000 else code - 0x100000000


def _join(job_name: str, gate_name: str) -> bool:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenJobObjectW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
    kernel.OpenJobObjectW.restype = ctypes.c_void_p
    kernel.OpenEventW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
    kernel.OpenEventW.restype = ctypes.c_void_p
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel.AssignProcessToJobObject.restype = ctypes.c_int
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    job = kernel.OpenJobObjectW(0x0001, False, job_name)  # JOB_OBJECT_ASSIGN_PROCESS
    if not job:
        return False
    try:
        if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
            return False
    finally:
        kernel.CloseHandle(job)
    if gate_name == "-":
        return True
    gate = kernel.OpenEventW(0x00100000, False, gate_name)  # SYNCHRONIZE
    if not gate:
        return False
    try:
        # The parent's SetEvent is the admission commit point; until then the
        # agent does not exist. A refused admission terminates the Job.
        return kernel.WaitForSingleObject(gate, 0xFFFFFFFF) == 0
    finally:
        kernel.CloseHandle(gate)


def main(argv: list[str]) -> int:
    # A CTRL_BREAK sent to this process group stops the agent; this wrapper
    # must survive it to report the agent's own exit code. Ctrl+C reaches the
    # agent as console input or its own signal, never this wrapper.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGBREAK, signal.SIG_IGN)
    job_name, gate_name, mode, *rest = argv
    if not _join(job_name, gate_name):
        return 126
    try:
        if mode == "native":
            return subprocess.call(rest, executable=rest[0])
        if mode == "shell":
            shell, command_line = rest
            # A string is CreateProcess's raw command line: no second quoting.
            return subprocess.call(command_line, executable=shell)
    except OSError as exc:
        sys.stderr.write(f"coga: start {rest[0]} failed: {exc}\n")
        return 127
    return 2


if __name__ == "__main__":
    raise SystemExit(_signed_exit_status(main(sys.argv[1:])))
