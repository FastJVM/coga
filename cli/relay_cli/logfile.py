"""Append-only task log. Written by CLI commands only — never by agents."""
from datetime import datetime, timezone
from pathlib import Path


def append(task_dir: Path, actor: str, message: str) -> None:
    log = task_dir / "log.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    line = f"{ts} [{actor}] {message}\n"
    with log.open("a") as f:
        f.write(line)
