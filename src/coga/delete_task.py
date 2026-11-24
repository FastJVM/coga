"""The single implementation of Coga task deletion.

Both `coga delete` and `coga run delete-task` remove the resolved local
task. Recovery is via `git restore` when the task was committed.

Both task shapes are handled, keyed off the resolved ticket path:

- **Directory form** (`<dir>/ticket.md`) — removes that one task directory and
  nothing else, after confirming it holds the ticket.
- **File form** (`tasks/<slug>.md`) — removes that single file only. It never
  touches the parent (a shared `tasks/` subtree), so a self-contained task can
  be deleted without risking its neighbours.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from coga.config import Config
from coga.tasks import TaskNotFoundError, TaskRef, resolve_task


class DeleteTaskError(RuntimeError):
    """Task deletion refused to remove its target, or could not complete it."""


def run_delete_task(cfg: Config, ref: TaskRef) -> str:
    """Delete one resolved task and return the report line."""
    ticket = ref.ticket_path
    try:
        if not ticket.is_file():
            raise DeleteTaskError(f"{ticket} is not a file — refusing to delete")
        if ticket.name == "ticket.md":
            target = ticket.parent
            shutil.rmtree(target)
        else:
            target = ticket
            ticket.unlink()
    except OSError as exc:
        raise DeleteTaskError(f"could not delete {ticket}: {exc}") from exc

    return f"{ref.id_slug}: deleted {target}\n"


def run_delete_task_recipe(cfg: Config, argv: list[str]) -> int:
    """Remove one task from the working tree."""
    if len(argv) != 1 or not argv[0].strip():
        sys.stderr.write(
            "Usage: coga run delete-task <task> — exactly one task ref is "
            f"required (got {len(argv)}).\n"
        )
        return 2

    try:
        ref = resolve_task(cfg, argv[0].strip())
    except TaskNotFoundError as exc:
        sys.stderr.write(f"delete-task: {exc}\n")
        return 2

    try:
        report = run_delete_task(cfg, ref)
    except DeleteTaskError as exc:
        sys.stderr.write(f"delete-task: {exc}\n")
        return 2

    sys.stdout.write(report)
    return 0


__all__ = ["DeleteTaskError", "run_delete_task", "run_delete_task_recipe"]
