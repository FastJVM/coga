"""Task directory discovery and resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from relay.config import Config
from relay.paths import bootstrap_path, tasks_dir
from relay.ticket import Ticket


class TaskNotFoundError(Exception):
    pass


_BOOTSTRAP_PREFIX = "bootstrap/"


@dataclass(frozen=True)
class TaskRef:
    slug: str
    path: Path

    @property
    def id_slug(self) -> str:
        return self.slug


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
    """List all task directories under `relay-os/tasks/`.

    A task is any direct child directory of `tasks/` that contains a
    `ticket.md`. The directory name is the task's slug. Directories whose
    names start with `_` are treated as templates and skipped (matching
    the convention used elsewhere in the layout).
    """
    tasks_root = tasks_dir(cfg)
    if not tasks_root.is_dir():
        return []
    out: list[TaskRef] = []
    for entry in sorted(tasks_root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("_"):
            continue
        if not (entry / "ticket.md").is_file():
            continue
        out.append(TaskRef(slug=entry.name, path=entry))
    return out


def resolve_task(cfg: Config, task_arg: str) -> TaskRef:
    """Resolve a task arg to a TaskRef.

    Accepts an exact slug (`fix-retry-logic`) or any unique slug prefix
    (`fix-ret`), git-short-SHA-style. Ambiguous prefixes raise with the
    matching slugs listed.
    """
    tasks = list_tasks(cfg)
    if not tasks:
        raise TaskNotFoundError(f"No tasks found (looked for {task_arg!r})")

    exact = [t for t in tasks if t.slug == task_arg]
    if exact:
        return exact[0]

    matches = [t for t in tasks if t.slug.startswith(task_arg)]
    if not matches:
        raise TaskNotFoundError(f"No task matches {task_arg!r}")
    if len(matches) > 1:
        slugs = ", ".join(t.slug for t in matches)
        raise TaskNotFoundError(
            f"Ambiguous task ref {task_arg!r}: matches {slugs}. "
            f"Use a longer prefix to disambiguate."
        )
    return matches[0]


def resolve_bootstrap(cfg: Config, name: str) -> BootstrapRef:
    """Resolve a bootstrap shim by name (e.g. "ticket" or "bootstrap/ticket")."""
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
    """Resolve a target arg to either a task slug or a bootstrap shim."""
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
