"""Atomic file writes for self-managed state files.

A bare `path.write_text(...)` truncates the target before writing, so a crash
mid-write (SIGKILL, disk full) leaves a truncated file — exactly the failure
mode `relay validate` then trips on. Writing to a temp file in the *same
directory* and `os.replace`-ing it into place gives an atomic swap: a reader
sees either the old complete file or the new complete file, never a partial
one. Same-directory is load-bearing — a cross-filesystem rename degrades to a
non-atomic copy, defeating the point.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, data: str, *, fsync: bool = True) -> None:
    """Atomically write `data` to `path` via a same-directory temp + rename.

    The temp file is created alongside the target so `os.replace` is a true
    atomic rename. With `fsync` (the default) the data is flushed to disk
    before the rename, so a crash after the rename can't surface an empty file
    whose directory entry merely points at unwritten blocks.
    """
    path = Path(path)
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(
        dir=directory, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
            f.flush()
            if fsync:
                os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


__all__ = ["atomic_write_text"]
