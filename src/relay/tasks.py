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
    """Two task directories resolve to the same qualified slug.

    The qualified slug is the task's path under `tasks/` (`<dir>/<leaf>`, or
    bare `<leaf>` for a task directly under `tasks/`) and is the universal task
    reference. Because it *is* the directory path, a clash is impossible by
    construction — but discovery still fails loud if one ever appears rather
    than silently dropping a task. `relay validate` catches this and reports
    the colliding paths instead of crashing.
    """

    def __init__(self, slug: str, paths: list[Path]) -> None:
        self.slug = slug
        self.paths = paths
        listed = ", ".join(str(p) for p in paths)
        super().__init__(
            f"Duplicate task slug {slug!r}: {listed} — "
            f"a task's path under `tasks/` must be unique; rename one of them."
        )


_BOOTSTRAP_PREFIX = "bootstrap/"


@dataclass(frozen=True)
class TaskRef:
    slug: str
    path: Path
    directory: str | None = None

    @property
    def id_slug(self) -> str:
        """The universal task reference — the task's path under `tasks/`.

        A task directly under `tasks/` is its bare leaf slug; a task in a
        sub-directory is `<directory>/<leaf>` (the relative path, e.g.
        `marketing/social/relaunch`) so it stays unambiguous and reads the same
        in `relay status`, Slack, and the launch arg.
        """
        if self.directory:
            return f"{self.directory}/{self.slug}"
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

    A task is any directory containing a `ticket.md`, at any depth under
    `tasks/` — directly (`tasks/<slug>/`) or in any sub-directory
    (`tasks/marketing/social/relaunch/`). The task is referenced by its path
    under `tasks/`, exposed as `TaskRef.id_slug` (`marketing/social/relaunch`);
    `TaskRef.directory` is the relative parent path, or None at the top level.
    Sub-directories are plain directories — make them with `mkdir`, nest them
    freely — and are recursed into until a `ticket.md` is found. A task
    directory is never recursed into (no task inside a task). Directories whose
    names start with `_` are treated as templates and skipped at every level.

    Raises `DuplicateTaskSlugError` if two task directories ever resolve to the
    same path (impossible by construction, but checked anyway — fail loud).
    """
    tasks_root = tasks_dir(cfg)
    if not tasks_root.is_dir():
        return []
    found: dict[str, TaskRef] = {}

    def add(entry: Path) -> None:
        rel = entry.relative_to(tasks_root)
        parent = rel.parent
        directory = None if parent == Path(".") else parent.as_posix()
        ref = TaskRef(slug=entry.name, path=entry, directory=directory)
        clash = found.get(ref.id_slug)
        if clash is not None:
            raise DuplicateTaskSlugError(ref.id_slug, [clash.path, entry])
        found[ref.id_slug] = ref

    def walk(directory: Path) -> None:
        for entry in sorted(directory.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            if (entry / "ticket.md").is_file():
                add(entry)  # a task — never recurse into it
            else:
                walk(entry)  # a plain sub-directory — keep descending

    walk(tasks_root)
    return sorted(found.values(), key=lambda t: t.id_slug)


# Reserved arg meaning "tasks directly under `tasks/`, no sub-directories".
# A directory literally named `root` would be shadowed by it; that collision
# is documented rather than guarded, keeping the sentinel a plain word.
ROOT_DIR = "root"


class UnknownDirectoryError(Exception):
    """A filter named a directory with no matching `tasks/<dir>/` on disk.

    Carries the directories that do exist so the caller can fail loud
    (principle 6) instead of rendering a silently-empty list.
    """

    def __init__(self, directory: str, available: list[str]) -> None:
        self.directory = directory
        self.available = available
        listed = ", ".join(available) if available else "(none)"
        super().__init__(
            f"Unknown directory {directory!r}. Directories under tasks/: "
            f"{listed}. Use '{ROOT_DIR}' for tasks directly under tasks/."
        )


def list_task_dirs(cfg: Config) -> list[str]:
    """List the (non-task) directories under `relay-os/tasks/`, at any depth.

    These are the plain directories you can filter on — every directory under
    `tasks/` that isn't itself a task (no `ticket.md`), returned as a path
    relative to `tasks/` (`marketing`, `marketing/social`). A directory exists
    because you made it (`mkdir`), so an empty one with no tasks yet is still
    listed. `_`-prefixed template dirs are skipped, matching discovery.
    """
    tasks_root = tasks_dir(cfg)
    if not tasks_root.is_dir():
        return []
    dirs: list[str] = []

    def walk(directory: Path) -> None:
        for entry in sorted(directory.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            if (entry / "ticket.md").is_file():
                continue  # a task, not a plain directory
            dirs.append(entry.relative_to(tasks_root).as_posix())
            walk(entry)

    walk(tasks_root)
    return dirs


def filter_tasks_under(
    refs: list[TaskRef], directory: str | None, cfg: Config
) -> list[TaskRef]:
    """Narrow `refs` to a directory sub-tree, or to the top level.

    `directory` is None (no filter), `ROOT_DIR` (only tasks directly under
    `tasks/`), or a directory path (`marketing`, `marketing/social`) — keeping
    every task at or below `tasks/<directory>/`, nested ones included. A path
    that is not an existing directory raises `UnknownDirectoryError` — fail
    loud, not a silently empty list. Pure in-memory selection plus one `tasks/`
    walk; no ticket mutation, so the read-only contract of `relay status` holds.
    """
    if directory is None:
        return refs
    if directory == ROOT_DIR:
        return [r for r in refs if r.directory is None]
    target = directory.strip("/")
    if target not in list_task_dirs(cfg):
        raise UnknownDirectoryError(target, list_task_dirs(cfg))
    prefix = target + "/"
    return [
        r for r in refs
        if r.directory == target or (r.directory or "").startswith(prefix)
    ]


def resolve_task(cfg: Config, task_arg: str) -> TaskRef:
    """Resolve a task arg to a TaskRef.

    Matches against the qualified slug (`TaskRef.id_slug`, the task's path
    under `tasks/`): a top-level task by its bare leaf (`fix-retry-logic`), a
    nested task by its path (`marketing/relay-crm`). Accepts an exact match or
    any unique prefix (`marketing/rel`), git-short-SHA-style. A nested task's
    bare leaf does not resolve. Ambiguous prefixes raise with the matching
    slugs listed.
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
    "ROOT_DIR",
    "UnknownDirectoryError",
    "list_tasks",
    "list_task_dirs",
    "filter_tasks_under",
    "resolve_task",
    "resolve_bootstrap",
    "resolve_target",
    "read_ticket",
]
