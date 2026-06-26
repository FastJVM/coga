"""The repo-global append-only log, written exclusively by CLI commands.

Coga keeps one audit log per repo at `coga/log.md` (not one per task). Each
line is tagged with the task ref it belongs to::

    YYYY-MM-DD HH:MM [<task-ref>] [<actor>] <message>

so a single task's history is reconstructable by filtering on its ref. `actor`
is conventionally `agent:<nickname>`, `human:<name>`, `git`, `slack`, or
`system`.

Why global rather than per-task: the log is the one thing that grows without
bound, and it is deliberately **never** a prompt-composition layer. Pulling it
out of the task directory keeps every per-task `ticket.md` small and bounded
(frontmatter + body + blackboard), so compose can read the small file and
ignore the log entirely. `coga/.gitattributes` marks `log.md` `merge=union`
so concurrent appends across branches merge without conflict — readers sort on
display, so union's possible duplicate/unsorted lines are harmless for an
append-only audit trail.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from coga.config import Config
from coga.paths import log_path, recurring_dir, tasks_dir

# `YYYY-MM-DD HH:MM [<ref>] ...` — captures the timestamp and the ref tag.
_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \[([^\]]*)\]")


def append_log(cfg: Config, task_ref: str, actor: str, message: str) -> None:
    """Append one line to the repo-global `coga/log.md`, tagged `task_ref`."""
    path = log_path(cfg)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"{timestamp} [{task_ref}] [{actor}] {message}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(line)


def ref_tag_for_path(cfg: Config, path: Path) -> str:
    """Derive a task ref tag from a task (or recurring-template) directory path.

    A task under `tasks/` tags with its path-qualified slug; a recurring
    template under `recurring/<name>/` tags `recurring/<name>`. Used by the few
    callers that hold a path rather than a `TaskRef` (git sync failures, the
    notification post-failure log).
    """
    resolved = path.resolve()
    for root, prefix in ((tasks_dir(cfg), ""), (recurring_dir(cfg), "recurring/")):
        try:
            rel = resolved.relative_to(root.resolve())
        except ValueError:
            continue
        # A file-form task's anchor is `<slug>.md`; its ref drops the suffix
        # (a directory-form anchor is `<slug>` / `<slug>/ticket.md` unaffected).
        if rel.suffix == ".md" and rel.name != "ticket.md":
            rel = rel.with_suffix("")
        return f"{prefix}{rel}" if str(rel) != "." else prefix.rstrip("/")
    return Path(path.name).stem if path.suffix == ".md" else path.name


def last_activity_map(cfg: Config) -> dict[str, datetime]:
    """Map each task ref to the timestamp of its most recent log line.

    A single pass over the global log; later lines overwrite earlier ones, so
    each ref ends on its last activity. Lines without a parseable timestamp are
    skipped. `coga status` uses this instead of re-scanning per task.
    """
    path = log_path(cfg)
    out: dict[str, datetime] = {}
    if not path.is_file():
        return out
    try:
        text = path.read_text()
    except OSError:
        return out
    for line in text.splitlines():
        match = _LINE_RE.match(line)
        if not match:
            continue
        try:
            dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        out[match.group(2)] = dt
    return out


def last_activity(cfg: Config, task_ref: str) -> datetime | None:
    """Return the timestamp of `task_ref`'s last log line, or None."""
    return last_activity_map(cfg).get(task_ref)


def task_log_lines(cfg: Config, task_ref: str) -> list[str]:
    """Return the global log's lines for `task_ref`, in file order.

    Filters the global log on the `[<task-ref>]` tag. Used by `coga show` to
    reconstruct a single task's history.
    """
    path = log_path(cfg)
    if not path.is_file():
        return []
    out: list[str] = []
    for line in path.read_text().splitlines():
        match = _LINE_RE.match(line)
        if match and match.group(2) == task_ref:
            out.append(line)
    return out


__all__ = [
    "append_log",
    "ref_tag_for_path",
    "last_activity_map",
    "last_activity",
    "task_log_lines",
]
