"""The retained repo-global audit log, written by CLI commands.

Events use `YYYY-MM-DD HH:MM v1 [ref] [actor] message` and one LF-terminated
line; encode/decode preserve literal backslashes, LF and CR. Legacy events can
own untagged continuation lines. `parse_events` preserves original spans and
keeps uncertain data opaque. Readers retain their established history semantics.

The log is never a prompt-composition layer. The trim-log ticket owns retention;
`coga-dev/internals/spool-merge` owns event publication and guarded deletion.
Native Git uses `/log.md -merge`, while Coga reconciles appends explicitly.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from coga.config import Config
from coga.paths import log_path, recurring_dir, tasks_dir

# `YYYY-MM-DD HH:MM [<ref>] ...` — captures the timestamp and the ref tag.
_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) (?:v1 )?\[([^\]]*)\]")
# The same line with its actor and message — `... [<ref>] [<actor>] <message>`.
_ENTRY_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} (?P<version>v1 )?"
    r"\[(?P<ref>[^\]]*)\] \[[^\]]*\] (?P<message>.*)$"
)
_LINE_BYTES_RE = re.compile(rb"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} (?:v1 )?\[([^\]]*)\]")
_ESCAPES = {"\\": "\\\\", "\n": "\\n", "\r": "\\r"}
_ESCAPE_RE = re.compile(r"[\\\n\r]")
_UNESCAPES = {"\\": "\\", "n": "\n", "r": "\r"}
_UNESCAPE_RE = re.compile(r"\\([\\nr])")


def encode_log_message(message: str) -> str:
    """Escape `\\`, LF, and CR so `message` fits on one physical log line."""
    return _ESCAPE_RE.sub(lambda m: _ESCAPES[m.group(0)], message)


def decode_log_message(message: str) -> str:
    """Invert `encode_log_message`; other backslash sequences pass through."""
    return _UNESCAPE_RE.sub(lambda m: _UNESCAPES[m.group(1)], message)


def log_lines(text: str) -> list[str]:
    """Split log text into physical lines on LF only.

    `str.splitlines` also breaks on VT, FF, U+2028 and friends, which the
    encoding passes through unchanged inside one event.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def append_log(cfg: Config, task_ref: str, actor: str, message: str) -> bytes:
    """Append and return one exact encoded repo-global audit-log line.

    `message` is encoded here (`encode_log_message`), so callers pass raw text
    such as multiline Git stderr and still produce exactly one line.
    """
    path = log_path(cfg)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    encoded = encode_log_message(message)
    line = f"{timestamp} v1 [{task_ref}] [{actor}] {encoded}\n".encode("utf-8")
    from coga import git

    with git.state_lock(cfg):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as f:
            f.write(line)
    return line


@dataclass(frozen=True)
class LogEvent:
    """An original byte span. Opaque/incomplete spans never acquire an age."""

    start: int
    end: int
    raw: bytes
    timestamp: datetime | None = None
    ref: str | None = None
    actor: str | None = None
    message: str | None = None
    version: str | None = None
    complete: bool = True

    @property
    def canonical(self) -> bytes:
        # Only CRLF terminators are normalized; bare CR remains content.
        return self.raw.replace(b"\r\n", b"\n")


_EVENT_RE = re.compile(
    r"^(?P<stamp>[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}) "
    r"(?P<version>v1 )?\[(?P<ref>[^\]\r\n]*)\] "
    r"\[(?P<actor>[^\]\r\n]*)\] (?P<message>[^\r\n]*)$"
)
_TIMESTAMP_LIKE = re.compile(rb"^[0-9]{4}-[0-9]{2}-[0-9]{2}")


def parse_events(raw: bytes) -> tuple[LogEvent, ...]:
    """Split at LF, preserving bytes and legacy continuations conservatively.

    Malformed timestamp-looking headers, unknown versions, invalid UTF-8 and
    continuations after v1 are independent opaque blocks. A partial legacy
    tail makes its entire event incomplete. No retained byte is repaired.
    """
    events: list[LogEvent] = []
    offset = 0
    parts = raw.split(b"\n")
    for index, part in enumerate(parts):
        complete = index < len(parts) - 1
        if not complete and not part:
            break
        line = part + (b"\n" if complete else b"")
        try:
            text = part.removesuffix(b"\r").decode("utf-8")
            match = _EVENT_RE.fullmatch(text)
            stamp = datetime.strptime(match["stamp"], "%Y-%m-%d %H:%M") if match else None
        except (UnicodeError, ValueError):
            match, stamp = None, None
            text = None
        if match is not None:
            message = match["message"]
            version = "v1" if match["version"] else None
            events.append(LogEvent(
                offset, offset + len(line), line, stamp, match["ref"],
                match["actor"], decode_log_message(message) if version else message,
                version, complete,
            ))
        elif (events and events[-1].timestamp is not None
              and events[-1].version is None and text is not None
              and not _TIMESTAMP_LIKE.match(part)):
            prev = events[-1]
            events[-1] = replace(prev, end=offset + len(line), raw=prev.raw + line,
                                 complete=complete)
        else:
            events.append(LogEvent(offset, offset + len(line), line, complete=complete))
        offset += len(line)
    return tuple(events)


@dataclass(frozen=True)
class LogMutation:
    """Authority to remove exact whole-event occurrences from one preimage.

    Receipts are also used for local rollback. Publication verifies the control
    preimage and the local postimage independently; a short file is no receipt.
    """

    preimage: bytes
    removed: tuple[int, ...]

    @property
    def postimage(self) -> bytes:
        events = parse_events(self.preimage)
        indices = set(self.removed)
        if len(indices) != len(self.removed) or any(type(i) is not int or i < 0 or i >= len(events) for i in indices):
            raise ValueError("invalid audit mutation occurrences")
        return b"".join(event.raw for i, event in enumerate(events) if i not in indices)


def replace_log(cfg: Config, mutation: LogMutation) -> None:
    """Apply a local receipt atomically, refusing any intervening file write."""
    from coga import git
    from coga.atomicio import atomic_write_bytes

    with git.state_lock(cfg):
        path = log_path(cfg)
        raw = path.read_bytes() if path.exists() else b""
        if raw != mutation.preimage:
            raise git.StateRegressionError("audit log changed since the mutation was planned")
        atomic_write_bytes(path, mutation.postimage)


def retract_log_append(cfg: Config, before: bytes | None, appended: bytes) -> bool:
    """Retract the exact returned append, preserving peer events and duplicates."""
    from coga import git

    with git.state_lock(cfg):
        path = log_path(cfg)
        if not path.exists():
            return before is None
        raw = path.read_bytes()
        # Prefer the appended occurrence after the observed prefix. Never use
        # a substring match inside another event (including legacy messages).
        old_count = sum(e.raw == appended for e in parse_events(before or b""))
        matches = [i for i, e in enumerate(parse_events(raw)) if e.raw == appended]
        if len(matches) <= old_count:
            return False
        replace_log(cfg, LogMutation(raw, (matches[old_count],)))
        if before is None and not path.read_bytes():
            path.unlink()
        return True


def retract_log_lines(cfg: Config, task_ref: str, before: bytes | None) -> None:
    """Undo this ref's post-snapshot events while the caller holds state_lock.

    A changed prefix is a visible refusal, never a silently abandoned rollback.
    Callers unable to hold the transaction use returned append identities.
    """
    from coga import git

    with git.state_lock(cfg):
        path = log_path(cfg)
        if not path.exists():
            return
        raw = path.read_bytes()
        prefix = before or b""
        if not raw.startswith(prefix):
            raise git.StateRegressionError("audit prefix changed during rollback; retain state for recovery")
        removed = tuple(i for i, e in enumerate(parse_events(raw))
                        if e.start >= len(prefix) and e.ref == task_ref)
        if removed:
            replace_log(cfg, LogMutation(raw, removed))


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
        return f"{prefix}{rel.as_posix()}" if str(rel) != "." else prefix.rstrip("/")
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
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in log_lines(text):
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
    kept rather than the first line seen because cross-checkout publication
    can leave the log unsorted. Megalaunch's oldest-first drain order and
    `coga status --order-by created` both read it.
    """
    path = log_path(cfg)
    out: dict[str, datetime] = {}
    if not path.is_file():
        return out
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in log_lines(text):
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
    """Yield `(task_ref, decoded message)` for every parseable line, in order.

    One pass over the whole log for callers that need to reconstruct state for
    *many* refs at once — reading it once per ref would re-scan the retained global audit file. Callers own their own message parsing; this
    only splits the line's fixed envelope.
    """
    path = log_path(cfg)
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in log_lines(text):
        match = _ENTRY_RE.match(line)
        if match:
            yield match.group("ref"), (
                decode_log_message(match.group("message"))
                if match.group("version") else match.group("message")
            )


def iter_log_messages_reverse(
    cfg: Config, *, block_size: int = 65536
) -> Iterator[tuple[str, str]]:
    """Yield `(task_ref, message)` newest-line-first, reading only the tail.

    The forward twin above has to touch every byte before it can answer
    anything. That is the right shape for a caller reconstructing *all* of
    history, and the wrong shape for one asking "what is the newest record for
    these few refs?" — the log is the retained global audit file, so
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
                    yield match.group("ref"), (
                        decode_log_message(match.group("message"))
                        if match.group("version") else match.group("message")
                    )


def task_log_lines(cfg: Config, task_ref: str) -> list[str]:
    """Return the global log's lines for `task_ref`, in file order.

    Filters the global log on the `[<task-ref>]` tag. Used by `coga show` to
    reconstruct a single task's history. Lines are returned as written (still
    encoded); a legacy untagged continuation line is kept with the event it
    follows.
    """
    path = log_path(cfg)
    if not path.is_file():
        return []
    out: list[str] = []
    keeping = False
    for line in log_lines(path.read_text(encoding="utf-8")):
        match = _LINE_RE.match(line)
        if match:
            keeping = match.group(2) == task_ref
        if keeping:
            out.append(line)
    return out


__all__ = [
    "retract_log_lines",
    "append_log",
    "decode_log_message",
    "encode_log_message",
    "log_lines",
    "ref_tag_for_path",
    "first_activity_map",
    "first_activity",
    "last_activity_map",
    "last_activity",
    "iter_log_messages",
    "iter_log_messages_reverse",
    "task_log_lines",
]
