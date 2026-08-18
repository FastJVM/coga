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
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from coga.config import Config
from coga.paths import log_path, recurring_dir, tasks_dir

# `YYYY-MM-DD HH:MM [<ref>] ...` — captures the timestamp and the ref tag.
_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \[([^\]]*)\]")
# The same line with its actor and message — `... [<ref>] [<actor>] <message>`.
_ENTRY_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} \[([^\]]*)\] \[([^\]]*)\] (.*)$"
)


def append_log(cfg: Config, task_ref: str, actor: str, message: str) -> bytes:
    """Append and return one exact encoded repo-global audit-log line."""
    path = log_path(cfg)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"{timestamp} [{task_ref}] [{actor}] {message}\n".encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as f:
        f.write(line)
    return line


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


def first_activity_map(cfg: Config) -> dict[str, datetime]:
    """Map each task ref to the timestamp of its earliest log line.

    The mirror of `last_activity_map`: the earliest parseable line per ref is
    the draft/create entry, so this is "creation time" as committed content —
    it survives clone/checkout, unlike file mtimes. The minimum timestamp is
    kept rather than the first line seen because `merge=union` can leave the
    log unsorted. Megalaunch's oldest-first drain order and
    `coga status --order-by created` both read it.
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
        ref = match.group(2)
        prev = out.get(ref)
        if prev is None or dt < prev:
            out[ref] = dt
    return out


def first_activity(cfg: Config, task_ref: str) -> datetime | None:
    """Return the timestamp of `task_ref`'s first log line, or None."""
    return first_activity_map(cfg).get(task_ref)


def iter_log_messages(cfg: Config) -> Iterator[tuple[str, str]]:
    """Yield `(task_ref, message)` for every parseable line, in file order.

    One pass over the whole log for callers that need to reconstruct state for
    *many* refs at once — reading it once per ref would re-scan the one file
    Coga lets grow without bound. Callers own their own message parsing; this
    only splits the line's fixed envelope.
    """
    path = log_path(cfg)
    if not path.is_file():
        return
    try:
        text = path.read_text()
    except OSError:
        return
    for line in text.splitlines():
        match = _ENTRY_RE.match(line)
        if match:
            yield match.group(1), match.group(3)


def iter_log_messages_reverse(
    cfg: Config, *, block_size: int = 65536
) -> Iterator[tuple[str, str]]:
    """Yield `(task_ref, message)` newest-line-first, reading only the tail.

    The forward twin above has to touch every byte before it can answer
    anything. That is the right shape for a caller reconstructing *all* of
    history, and the wrong shape for one asking "what is the newest record for
    these few refs?" — the log is the one file Coga lets grow without bound, so
    a question answered by its last few lines must not cost a full read.

    The file is walked backwards a block at a time and each block's complete
    lines are yielded in reverse; a partial line at a block's leading edge is
    carried into the next (earlier) block. A consumer that stops early leaves
    the rest of the file unread — that short-circuit is the whole point.

    `block_size` exists so tests can force multi-block reads on small logs.
    """
    path = log_path(cfg)
    if not path.is_file():
        return
    try:
        handle = path.open("rb")
    except OSError:
        return
    with handle:
        handle.seek(0, 2)
        remaining = handle.tell()
        tail = b""
        while remaining > 0:
            step = min(block_size, remaining)
            remaining -= step
            handle.seek(remaining)
            chunk = handle.read(step) + tail
            lines = chunk.split(b"\n")
            # The first element is only a whole line once the file's start is
            # reached; until then it is the head of a line that continues into
            # the block we have not read yet.
            tail = b"" if remaining == 0 else lines.pop(0)
            for raw in reversed(lines):
                try:
                    line = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                match = _ENTRY_RE.match(line)
                if match:
                    yield match.group(1), match.group(3)


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
    "first_activity_map",
    "first_activity",
    "last_activity_map",
    "last_activity",
    "iter_log_messages",
    "iter_log_messages_reverse",
    "task_log_lines",
]
