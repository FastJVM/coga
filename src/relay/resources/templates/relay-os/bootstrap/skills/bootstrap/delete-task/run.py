#!/usr/bin/env python3
"""Delete a Relay task directory.

The single implementation of task deletion: the body behind `relay delete`,
and a standalone `mode: script` skill. Removes exactly the directory named by
`RELAY_TASK_DIR` — nothing else — after confirming it is a task directory.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _fail(msg: str) -> int:
    sys.stderr.write(f"delete-task: {msg}\n")
    return 2


def main() -> int:
    raw = os.environ.get("RELAY_TASK_DIR")
    if not raw:
        return _fail("RELAY_TASK_DIR is not set")

    task_dir = Path(raw)
    slug = os.environ.get("RELAY_TASK_SLUG") or task_dir.name

    if not task_dir.is_dir():
        return _fail(f"{task_dir} is not a directory")
    if not (task_dir / "ticket.md").is_file():
        return _fail(
            f"{task_dir} has no ticket.md — refusing to delete a non-task directory"
        )

    shutil.rmtree(task_dir)
    sys.stdout.write(f"{slug}: deleted\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
