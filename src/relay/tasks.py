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
    """A task under `relay-os/tasks/`, in either of two interchangeable shapes.

    - **File form** (`file_form=True`): a single `tasks/<slug>.md` file; `path`
      is that file. Self-contained — no companion directory, so no sibling
      files (a snapshot, a `script:` file) are possible.
    - **Directory form** (`file_form=False`): a `tasks/<slug>/` directory
      holding `ticket.md` plus any siblings; `path` is the directory.

    `ticket_path` abstracts over the two; `task_dir` is the companion directory
    or `None` for file form. Addressing is always by `id_slug` (the path under
    `tasks/`), identical for both shapes.
    """

    slug: str
    path: Path
    directory: str | None = None
    file_form: bool = False

    @property
    def id_slug(self) -> str:
        """The universal task reference — the task's path under `tasks/`.

        A task directly under `tasks/` is its bare leaf slug; a task in a
        sub-directory is `<directory>/<leaf>` (the relative path, e.g.
        `marketing/social/relaunch`) so it stays unambiguous and reads the same
        in `relay status`, Slack, and the launch arg. The `.md` suffix of a
        file-form task is never part of the ref.
        """
        if self.directory:
            return f"{self.directory}/{self.slug}"
        return self.slug

    @property
    def ticket_path(self) -> Path:
        """The task's `ticket.md` — the `.md` file itself in file form, or
        `<dir>/ticket.md` in directory form."""
        return self.path if self.file_form else self.path / "ticket.md"

    @property
    def task_dir(self) -> Path | None:
        """The task's companion directory, or `None` for a self-contained
        file-form task (which has nowhere to put siblings)."""
        return None if self.file_form else self.path


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

    @property
    def ticket_path(self) -> Path:
        """Bootstrap shims are always directory form."""
        return self.path / "ticket.md"

    @property
    def task_dir(self) -> Path:
        return self.path


TargetRef = Union[TaskRef, BootstrapRef]


def list_tasks(cfg: Config) -> list[TaskRef]:
    """List all tasks under `relay-os/tasks/`, in either on-disk shape.

    A task is either a directory containing a `ticket.md` (**directory form**,
    `tasks/<slug>/ticket.md`) or a bare `tasks/<slug>.md` file (**file form**),
    at any depth under `tasks/`. The task is referenced by its path under
    `tasks/` (sans `.md` for file form), exposed as `TaskRef.id_slug`;
    `TaskRef.directory` is the relative parent path, or None at the top level.
    Plain sub-directories (those without a `ticket.md`) are recursed into. A
    task directory is never recursed into (no task inside a task). Names that
    start with `_` are treated as templates and skipped at every level.

    Raises `DuplicateTaskSlugError` if two tasks resolve to the same slug —
    notably a `tasks/<slug>.md` file alongside a `tasks/<slug>/` directory.
    """
    tasks_root = tasks_dir(cfg)
    if not tasks_root.is_dir():
        return []
    found: dict[str, TaskRef] = {}

    def add(entry: Path, *, file_form: bool) -> None:
        slug = entry.stem if file_form else entry.name
        rel = entry.relative_to(tasks_root)
        parent = rel.parent
        directory = None if parent == Path(".") else parent.as_posix()
        ref = TaskRef(slug=slug, path=entry, directory=directory, file_form=file_form)
        clash = found.get(ref.id_slug)
        if clash is not None:
            raise DuplicateTaskSlugError(ref.id_slug, [clash.path, entry])
        found[ref.id_slug] = ref

    def walk(directory: Path) -> None:
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith("_"):
                continue
            if entry.is_file():
                if entry.suffix == ".md" and entry.name != "ticket.md":
                    add(entry, file_form=True)  # file-form task
                continue
            if not entry.is_dir():
                continue
            if (entry / "ticket.md").is_file():
                add(entry, file_form=False)  # directory-form task — never recurse
            else:
                walk(entry)  # a plain sub-directory — keep descending

    walk(tasks_root)
    return sorted(found.values(), key=lambda t: t.id_slug)


def is_under(directory: str | None, target: str) -> bool:
    """True if a task's `directory` is `target` itself or nested below it.

    The subtree test shared by `filter_tasks_under` (the `relay status <dir>`
    filter) and the `tasks/recurring/` split in `relay status` — `target` and
    everything under `target/`. A top-level task (`directory is None`) is under
    nothing.
    """
    if directory is None:
        return False
    return directory == target or directory.startswith(target + "/")


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
            f"{listed}. Omit the directory (add --no-recurse) to list the "
            f"tasks directly under tasks/."
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
    refs: list[TaskRef], directory: str | None, cfg: Config, *, recurse: bool = True
) -> list[TaskRef]:
    """Narrow `refs` to a directory and (optionally) its sub-tree.

    Two orthogonal axes:

    - `directory` picks the directory — None for the `tasks/` root, or a path
      (`marketing`, `marketing/social`). A path that is not an existing
      directory raises `UnknownDirectoryError` — fail loud, not a silently
      empty list.
    - `recurse` picks the depth. True (default) keeps every task at or below
      that directory, nested ones included (`find <dir>`). False keeps only
      the tasks sitting directly in it, none from sub-directories (`ls <dir>`).

    So `recurse=False` with `directory=None` is "the tasks directly under
    `tasks/`" — the top-level slice that used to need a reserved `root` arg.

    Pure in-memory selection plus one `tasks/` walk; no ticket mutation, so the
    read-only contract of `relay status` holds.
    """
    if directory is None:
        if recurse:
            return refs
        return [r for r in refs if r.directory is None]
    target = directory.strip("/")
    available = list_task_dirs(cfg)
    if target not in available:
        raise UnknownDirectoryError(target, available)
    if recurse:
        return [r for r in refs if is_under(r.directory, target)]
    return [r for r in refs if r.directory == target]


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
    return Ticket.read(ref.ticket_path)


__all__ = [
    "TaskRef",
    "BootstrapRef",
    "TargetRef",
    "TaskNotFoundError",
    "DuplicateTaskSlugError",
    "UnknownDirectoryError",
    "is_under",
    "list_tasks",
    "list_task_dirs",
    "filter_tasks_under",
    "resolve_task",
    "resolve_bootstrap",
    "resolve_target",
    "read_ticket",
]
