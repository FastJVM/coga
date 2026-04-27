"""Task directory discovery and resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from relay.config import Config
from relay.paths import tasks_dir
from relay.ticket import Ticket


class TaskNotFoundError(Exception):
    pass


_ID_RE = re.compile(r"^(\d+)-")


@dataclass(frozen=True)
class TaskRef:
    id: int
    slug: str
    path: Path

    @property
    def id_slug(self) -> str:
        return f"{self.id:03d}-{self.slug}"


def list_tasks(cfg: Config) -> list[TaskRef]:
    """List all task directories under `relay-os/tasks/`."""
    tasks_root = tasks_dir(cfg)
    if not tasks_root.is_dir():
        return []
    out: list[TaskRef] = []
    for entry in sorted(tasks_root.iterdir()):
        if not entry.is_dir():
            continue
        m = _ID_RE.match(entry.name)
        if not m:
            continue
        task_id = int(m.group(1))
        slug = entry.name[len(m.group(0)):]
        out.append(TaskRef(id=task_id, slug=slug, path=entry))
    return out


def resolve_task(cfg: Config, task_arg: str) -> TaskRef:
    """Resolve a `--task` argument to a TaskRef.

    Accepts:
      - "003"                     — numeric ID
      - "003-fix-retry-logic"     — fully qualified id+slug
    """
    m = _ID_RE.match(task_arg) or re.match(r"^(\d+)$", task_arg)
    if not m:
        raise TaskNotFoundError(f"Can't parse task id from {task_arg!r}")
    target_id = int(m.group(1))

    candidates = [t for t in list_tasks(cfg) if t.id == target_id]
    if not candidates:
        raise TaskNotFoundError(f"No task with id {target_id:03d}")
    return candidates[0]


def read_ticket(ref: TaskRef) -> Ticket:
    return Ticket.read(ref.path / "ticket.md")


__all__ = [
    "TaskRef",
    "TaskNotFoundError",
    "list_tasks",
    "resolve_task",
    "read_ticket",
]
