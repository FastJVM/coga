"""Foreground child waits shared by command scripts and control relays."""
from __future__ import annotations

import signal
import subprocess
from pathlib import Path
from collections.abc import Mapping, Sequence


def run_foreground_child(
    argv: Sequence[str], *, cwd: Path, env: Mapping[str, str],
    defer_interrupt: bool = False,
) -> tuple[int, bool]:
    """Wait without killing an interrupted child; forward SIGTERM once.

    Console interrupts already reach the foreground child. A Python no-op
    handler resets to default at exec, unlike SIG_IGN. Recurring callers keep
    KeyboardInterrupt after waiting; command scripts return the child's status.
    """
    process: subprocess.Popen[bytes] | None = None
    terminated = False
    forwarded = False

    def forward_termination(signum: int, _frame: object) -> None:
        nonlocal terminated, forwarded
        terminated = True
        if process is not None and not forwarded:
            forwarded = True
            try:
                process.send_signal(signum)
            except ProcessLookupError:
                pass

    previous = {signal.SIGTERM: signal.signal(signal.SIGTERM, forward_termination)}
    if defer_interrupt:
        for name in ("SIGINT", "SIGBREAK"):
            signum = getattr(signal, name, None)
            if signum is not None:
                previous[signum] = signal.signal(signum, lambda *_: None)
    try:
        process = subprocess.Popen(list(argv), cwd=cwd, env=env)
        if terminated:
            forward_termination(signal.SIGTERM, None)
        try:
            code = process.wait()
        except KeyboardInterrupt:
            process.wait()
            raise
        return (128 - code if code < 0 else code), terminated
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
