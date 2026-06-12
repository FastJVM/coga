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


class DuplicateTaskSlugError(Exception):
    """Two task directories resolve to the same group-qualified slug.

    The qualified slug (`<group>/<leaf>`, or bare `<leaf>` for a top-level
    task) is the universal task reference. Because it tracks the directory
    path, a clash is normally impossible — but discovery still fails loud if
    one ever appears rather than silently dropping a task. `relay validate`
    catches this and reports the colliding paths instead of crashing.
    """

    def __init__(self, slug: str, paths: list[Path]) -> None:
        self.slug = slug
        self.paths = paths
        listed = ", ".join(str(p) for p in paths)
        super().__init__(
            f"Duplicate task slug {slug!r}: {listed} — "
            f"task directory names must be unique across `tasks/` and its "
            f"group directories; rename one of them."
        )


_BOOTSTRAP_PREFIX = "bootstrap/"


@dataclass(frozen=True)
class TaskRef:
    slug: str
    path: Path
    group: str | None = None

    @property
    def id_slug(self) -> str:
        """The universal task reference.

        A top-level task is its bare leaf slug; a task nested inside a group
        directory is `<group>/<leaf>` so it stays unambiguous and reads the
        same in `relay status`, Slack, and the launch arg.
        """
        if self.group:
            return f"{self.group}/{self.slug}"
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

    A task is any directory containing a `ticket.md`, either a direct child
    of `tasks/` or one level deeper inside a *group* directory — a child of
    `tasks/` without a `ticket.md` of its own (e.g. `tasks/marketing/`). A
    top-level task is referenced by its bare leaf slug; a nested task is
    referenced by its group-qualified slug (`marketing/relay-crm`), exposed
    as `TaskRef.id_slug`. Two groups may therefore reuse a leaf name.
    Directories whose names start with `_` are treated as templates and
    skipped at both levels. A task directory is never recursed into, and
    groups don't nest.

    Raises `DuplicateTaskSlugError` if two task directories ever resolve to
    the same qualified slug (path-unique, so normally impossible).
    """
    tasks_root = tasks_dir(cfg)
    if not tasks_root.is_dir():
        return []
    found: dict[str, TaskRef] = {}

    def add(entry: Path, group: str | None) -> None:
        ref = TaskRef(slug=entry.name, path=entry, group=group)
        clash = found.get(ref.id_slug)
        if clash is not None:
            raise DuplicateTaskSlugError(ref.id_slug, [clash.path, entry])
        found[ref.id_slug] = ref

    for entry in sorted(tasks_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if (entry / "ticket.md").is_file():
            add(entry, None)
            continue
        # Group directory: its direct children may be tasks.
        for sub in sorted(entry.iterdir()):
            if not sub.is_dir() or sub.name.startswith("_"):
                continue
            if (sub / "ticket.md").is_file():
                add(sub, entry.name)
    return sorted(found.values(), key=lambda t: t.id_slug)


def resolve_task(cfg: Config, task_arg: str) -> TaskRef:
    """Resolve a task arg to a TaskRef.

    Matches against the group-qualified slug (`TaskRef.id_slug`): a top-level
    task by its bare leaf (`fix-retry-logic`), a nested task by its qualified
    form (`marketing/relay-crm`). Accepts an exact match or any unique prefix
    (`marketing/rel`), git-short-SHA-style. A grouped task's bare leaf does
    not resolve. Ambiguous prefixes raise with the matching slugs listed.
    """
    tasks = list_tasks(cfg)
    if not tasks:
        raise TaskNotFoundError(f"No tasks found (looked for {task_arg!r})")

    exact = [t for t in tasks if t.id_slug == task_arg]
    if exact:
        return exact[0]

    matches = [t for t in tasks if t.id_slug.startswith(task_arg)]
    if not matches:
        raise TaskNotFoundError(f"No task matches {task_arg!r}")
    if len(matches) > 1:
        slugs = ", ".join(t.id_slug for t in matches)
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
    "DuplicateTaskSlugError",
    "list_tasks",
    "resolve_task",
    "resolve_bootstrap",
    "resolve_target",
    "read_ticket",
]
