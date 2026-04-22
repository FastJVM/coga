"""log.md — append-only structured log written exclusively by CLI commands."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


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


__all__ = ["append_log"]
