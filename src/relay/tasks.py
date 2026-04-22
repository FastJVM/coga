"""Task directory discovery and resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from relay.config import Config
from relay.paths import project_tasks_dir
from relay.ticket import Ticket


class TaskNotFoundError(Exception):
    pass


class AmbiguousTaskError(Exception):
    pass


_ID_RE = re.compile(r"^(\d+)-")


@dataclass(frozen=True)
class TaskRef:
    project: str
    id: int
    slug: str
    path: Path

    @property
    def id_slug(self) -> str:
        return f"{self.id:03d}-{self.slug}"


def list_tasks(cfg: Config, project: str | None = None) -> list[TaskRef]:
    """List all task directories. If project is given, only that project."""
    projects = [project] if project else list(cfg.projects)
    out: list[TaskRef] = []
    for proj in projects:
        try:
            tasks_root = project_tasks_dir(cfg, proj)
        except ValueError:
            continue
        if not tasks_root.is_dir():
            continue
        for entry in sorted(tasks_root.iterdir()):
            if not entry.is_dir():
                continue
            m = _ID_RE.match(entry.name)
            if not m:
                continue
            task_id = int(m.group(1))
            slug = entry.name[len(m.group(0)):]
            out.append(TaskRef(project=proj, id=task_id, slug=slug, path=entry))
    return out


def resolve_task(cfg: Config, task_arg: str, project: str | None = None) -> TaskRef:
    """Resolve a `--task` argument to a TaskRef.

    Accepts:
      - "003"                  — numeric ID, requires --project OR unambiguous across projects
      - "email-tool/003"       — project-qualified
      - "email-tool/003-fix-retry-logic" — fully qualified id+slug
    """
    if "/" in task_arg:
        proj, _, rest = task_arg.partition("/")
        project = proj
        task_arg = rest

    m = _ID_RE.match(task_arg) or re.match(r"^(\d+)$", task_arg)
    if not m:
        raise TaskNotFoundError(f"Can't parse task id from {task_arg!r}")
    target_id = int(m.group(1))

    candidates = [t for t in list_tasks(cfg, project) if t.id == target_id]
    if not candidates:
        raise TaskNotFoundError(
            f"No task with id {target_id:03d}" + (f" in project {project!r}" if project else "")
        )
    if len(candidates) > 1:
        pretty = ", ".join(f"{t.project}/{t.id_slug}" for t in candidates)
        raise AmbiguousTaskError(
            f"Task id {target_id:03d} exists in multiple projects: {pretty}. "
            "Disambiguate with project/id syntax."
        )
    return candidates[0]


def read_ticket(ref: TaskRef) -> Ticket:
    return Ticket.read(ref.path / "ticket.md")


__all__ = [
    "TaskRef",
    "TaskNotFoundError",
    "AmbiguousTaskError",
    "list_tasks",
    "resolve_task",
    "read_ticket",
]
