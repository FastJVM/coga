#!/usr/bin/env python3
"""Delete a Relay task.

The single implementation of task deletion: the body behind `relay delete`, and
a standalone script skill. Works for both task shapes, keyed off the
unambiguous `RELAY_TASK_TICKET`:

- **Directory form** (`<dir>/ticket.md`) — removes that one task directory and
  nothing else, after confirming it holds the ticket.
- **File form** (`tasks/<slug>.md`) — removes that single file only. It never
  touches the parent (a shared `tasks/` subtree), so a self-contained task can
  be deleted without risking its neighbours.
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
    raw = os.environ.get("RELAY_TASK_TICKET")
    if not raw:
        return _fail("RELAY_TASK_TICKET is not set")

    ticket = Path(raw)
    slug = os.environ.get("RELAY_TASK_SLUG") or ticket.stem

    if not ticket.is_file():
        return _fail(f"{ticket} is not a file — refusing to delete")

    if ticket.name == "ticket.md":
        # Directory form: remove the whole task directory (ticket + siblings).
        shutil.rmtree(ticket.parent)
        target = ticket.parent
    else:
        # File form: remove just the single-file ticket; leave the parent
        # (a shared tasks/ subtree) untouched.
        ticket.unlink()
        target = ticket

    sys.stdout.write(f"{slug}: deleted {target}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
