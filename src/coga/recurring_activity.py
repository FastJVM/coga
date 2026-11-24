"""Local audit inactivity gate for recurring jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from coga.config import Config
from coga.logfile import last_activity_map


@dataclass(frozen=True)
class RepoActivity:
    last_human: date | None = None
    inactive: bool = False
    error: str | None = None

    @property
    def inactive_since(self) -> str | None:
        if not self.inactive:
            return None
        return self.last_human.isoformat() if self.last_human else "never"


def check_activity(cfg: Config, today: date) -> RepoActivity:
    """Check local non-recurring ticket activity."""
    if cfg.recurring_idle_days == 0:
        return RepoActivity()
    try:
        last = max(
            (stamp.date() for ref, stamp in last_activity_map(cfg).items()
             if not ref.startswith(("recurring/", "autofix/"))),
            default=None,
        )
    except OSError as exc:
        return RepoActivity(error=str(exc))
    return RepoActivity(
        last_human=last,
        inactive=last is not None and (today - last).days >= cfg.recurring_idle_days,
    )
