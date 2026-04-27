"""Task directory discovery and resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from relay.config import Config
from relay.paths import bootstrap_dir, bootstrap_path, tasks_dir
from relay.ticket import Ticket


class TaskNotFoundError(Exception):
    pass


_ID_RE = re.compile(r"^(\d+)-")
_BOOTSTRAP_PREFIX = "bootstrap/"


@dataclass(frozen=True)
class TaskRef:
    id: int
    slug: str
    path: Path

    @property
    def id_slug(self) -> str:
        return f"{self.id:03d}-{self.slug}"


@dataclass(frozen=True)
class BootstrapRef:
    """A persistent launch-shim ticket under `relay-os/bootstrap/<name>/`.

    Bootstrap tickets are stateless re-entry points (no status flips, no lock).
    `id_slug` matches the launch arg form so logs read naturally.
    """

    name: str
    path: Path

    @property
    def id_slug(self) -> str:
        return f"bootstrap/{self.name}"


TargetRef = Union[TaskRef, BootstrapRef]


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


def resolve_bootstrap(cfg: Config, name: str) -> BootstrapRef:
    """Resolve a bootstrap shim by name (e.g. "create" or "bootstrap/create")."""
    if name.startswith(_BOOTSTRAP_PREFIX):
        name = name[len(_BOOTSTRAP_PREFIX):]
    path = bootstrap_path(cfg, name)
    if not (path / "ticket.md").is_file():
        raise TaskNotFoundError(
            f"No bootstrap ticket at {path / 'ticket.md'} "
            f"(expected for `bootstrap/{name}`)"
        )
    return BootstrapRef(name=name, path=path)


def resolve_target(cfg: Config, arg: str) -> TargetRef:
    """Resolve a `--task` argument to either a numeric task or a bootstrap shim."""
    if arg.startswith(_BOOTSTRAP_PREFIX):
        return resolve_bootstrap(cfg, arg)
    return resolve_task(cfg, arg)


def read_ticket(ref: TargetRef) -> Ticket:
    return Ticket.read(ref.path / "ticket.md")


__all__ = [
    "TaskRef",
    "BootstrapRef",
    "TargetRef",
    "TaskNotFoundError",
    "list_tasks",
    "resolve_task",
    "resolve_bootstrap",
    "resolve_target",
    "read_ticket",
]
