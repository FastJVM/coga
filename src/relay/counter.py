"""Per-project task ID counter. Atomic read-increment-write."""

from __future__ import annotations

import fcntl
from pathlib import Path


def next_id(project_relay_dir: Path) -> int:
    """Atomically read the `counter` file, increment, write back. Return the new value.

    The project's counter lives at `<project_path>/relay-os/counter`. If the
    file doesn't exist it is created with initial value `1` (the returned ID).
    Concurrent callers are serialized via fcntl.flock on the file itself.
    """
    project_relay_dir.mkdir(parents=True, exist_ok=True)
    counter_path = project_relay_dir / "counter"
    counter_path.touch(exist_ok=True)

    with counter_path.open("r+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            raw = f.read().strip()
            current = int(raw) if raw else 0
            new = current + 1
            f.seek(0)
            f.truncate()
            f.write(f"{new}\n")
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return new


__all__ = ["next_id"]
