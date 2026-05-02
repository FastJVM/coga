"""log.md — append-only structured log written exclusively by CLI commands."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\b")


def append_log(task_dir: Path, actor: str, message: str) -> None:
    """Append a line to `task_dir/log.md`.

    Format: `YYYY-MM-DD HH:MM [actor] message`
    `actor` is conventionally `agent:<nickname>` or `human:<name>` or `system`.
    """
    log_path = task_dir / "log.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"{timestamp} [{actor}] {message}\n"
    with log_path.open("a") as f:
        f.write(line)


def last_activity(task_dir: Path) -> datetime | None:
    """Return the timestamp of the last log.md entry, or None.

    Walks the file backwards looking for a parseable `YYYY-MM-DD HH:MM`
    prefix. Returns None if log is missing, empty, or has no parseable
    line — callers decide how to handle (sort to end, render as `-`).
    """
    log_path = task_dir / "log.md"
    if not log_path.is_file():
        return None
    try:
        text = log_path.read_text()
    except OSError:
        return None
    for line in reversed(text.splitlines()):
        match = _TIMESTAMP_RE.match(line)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
            except ValueError:
                continue
    return None


__all__ = ["append_log", "last_activity"]
