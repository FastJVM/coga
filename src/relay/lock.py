"""task.lock — serializes concurrent access to a task directory."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


class LockError(Exception):
    """Base class for lock errors."""


class LockHeldError(LockError):
    """Raised when trying to acquire a lock that's already held."""

    def __init__(self, info: "LockInfo") -> None:
        super().__init__(f"task.lock is held by {info.holder!r} since {info.acquired.isoformat()}")
        self.info = info


@dataclass(frozen=True)
class LockInfo:
    holder: str
    acquired: datetime


class TaskLock:
    """File-existence lock for a task directory."""

    def __init__(self, task_dir: Path) -> None:
        self.task_dir = task_dir
        self.path = task_dir / "task.lock"

    def read(self) -> LockInfo | None:
        if not self.path.exists():
            return None
        holder = "unknown"
        acquired = datetime.fromtimestamp(0, tz=timezone.utc)
        for line in self.path.read_text().splitlines():
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key == "holder":
                holder = value
            elif key == "acquired":
                try:
                    acquired = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    pass
        return LockInfo(holder=holder, acquired=acquired)

    def acquire(self, holder: str, force: bool = False) -> LockInfo:
        existing = self.read()
        if existing is not None and not force:
            raise LockHeldError(existing)
        info = LockInfo(holder=holder, acquired=datetime.now(timezone.utc))
        self.path.write_text(_render(info))
        return info

    def release(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    @contextmanager
    def held(self, holder: str, force: bool = False) -> Iterator[LockInfo]:
        info = self.acquire(holder=holder, force=force)
        try:
            yield info
        finally:
            self.release()

    def is_stale(self, max_age_hours: float = 24.0) -> bool:
        info = self.read()
        if info is None:
            return False
        age = datetime.now(timezone.utc) - info.acquired
        return age.total_seconds() > max_age_hours * 3600


def _render(info: LockInfo) -> str:
    acquired = info.acquired.astimezone(timezone.utc).isoformat(timespec="seconds")
    if acquired.endswith("+00:00"):
        acquired = acquired[:-6] + "Z"
    return f"holder: {info.holder}\nacquired: {acquired}\n"


__all__ = ["LockError", "LockHeldError", "LockInfo", "TaskLock"]
