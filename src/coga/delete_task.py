"""The single implementation of Coga task deletion.

Two spellings, one body: `coga delete <task>` (which adds the resolution
flags and the control-branch sync every other state mutation performs) and the
`delete-task` registered recipe, `coga run delete-task <task>` (the bare
working-tree removal, which is also what the `bootstrap/delete-task` skill
contract names). Recovery is via `git restore`; git history is the audit
trail, so deletion posts no Slack broadcast.

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


def run_delete_task(ref: TaskRef) -> str:
    """Delete one resolved task and return the report line.

    Callers own synchronization. `coga delete` lands the removal immediately;
    recurring replacement recreates the task at the same path and syncs that
    replacement as one state transition.

    `DeleteTaskError` is the *only* failure this raises. Deletion used to run
    behind a subprocess, where a filesystem error surfaced as a non-zero exit
    and became one; in-process, `rmtree`/`unlink` raise `OSError` directly, so
    it is translated here. Every caller — `coga delete`, the recipe, and
    recurring replacement, which runs unattended — catches that one type, and a
    read-only file or a held handle must not abort them with a traceback.
    """
    ticket = ref.ticket_path
    if not ticket.is_file():
        raise DeleteTaskError(f"{ticket} is not a file — refusing to delete")

    try:
        if ticket.name == "ticket.md":
            # Directory form: remove the whole task directory (ticket + siblings).
            shutil.rmtree(ticket.parent)
            target: Path = ticket.parent
        else:
            # File form: remove just the single-file ticket; leave the parent
            # (a shared tasks/ subtree) untouched.
            ticket.unlink()
            target = ticket
    except OSError as exc:
        raise DeleteTaskError(f"could not delete {ticket}: {exc}") from exc

    return f"{ref.id_slug}: deleted {target}\n"


def run_delete_task_recipe(cfg: Config, argv: list[str]) -> int:
    """`coga run delete-task <task>` — remove one task from the working tree.

    The removal only; landing it on the control branch is `coga delete`'s job.
    """
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
        report = run_delete_task(ref)
    except DeleteTaskError as exc:
        sys.stderr.write(f"delete-task: {exc}\n")
        return 2

    sys.stdout.write(report)
    return 0


__all__ = ["DeleteTaskError", "run_delete_task", "run_delete_task_recipe"]
