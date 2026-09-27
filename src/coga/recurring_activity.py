"""Control-history inactivity gate for the recurring-scan recipe."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime

from coga.config import Config


_MACHINE_SUBJECT = re.compile(
    r"^(Log:(?! bootstrap/)|Sync coga state|Dream|Ticket: recurring/|Autofix:"
    r"|Ticket: autofix/|Update Coga-managed skills"
    r"|Merge pull request #\d+ from [^/\s]+/(?:claude/dream-|coga/dream|dream/|coga/skill-update))"
    r"|— blocker reminder$"
)


def is_machine_commit(subject: str) -> bool:
    return _MACHINE_SUBJECT.search(subject) is not None


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
    """Read both control refs without fetching; unknown history fails open.

    Compare every human timestamp: Git's traversal order (even with date-order)
    does not guarantee timestamp order when a commit's clock goes backwards.
    None last_human with inactive=True means resolved, machine-only history.
    """
    if not cfg.git_enabled or cfg.recurring_idle_days == 0:
        return RepoActivity()
    try:
        refs: list[str] = []
        for ref in (
            f"refs/heads/{cfg.git_control_branch}",
            f"refs/remotes/{cfg.git_remote}/{cfg.git_control_branch}",
        ):
            resolved = subprocess.run(
                ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                cwd=cfg.repo_root, capture_output=True, text=True,
            )
            if resolved.returncode == 0:
                refs.append(resolved.stdout.strip())
            elif resolved.returncode != 1:
                return RepoActivity(error="could not resolve control history")
        if not refs:
            return RepoActivity(error="neither control ref resolves")
        history = subprocess.run(
            ["git", "log", "--first-parent", "--format=%ct%x09%s", *refs, "--"],
            cwd=cfg.repo_root, capture_output=True, text=True, check=True,
        )
        newest: int | None = None
        for line in history.stdout.splitlines():
            stamp, subject = line.split("\t", 1)
            if not is_machine_commit(subject):
                timestamp = int(stamp)
                newest = timestamp if newest is None else max(newest, timestamp)
        last = datetime.fromtimestamp(newest).date() if newest is not None else None
        return RepoActivity(
            last_human=last,
            inactive=last is None or (today - last).days >= cfg.recurring_idle_days,
        )
    except (OSError, subprocess.SubprocessError, ValueError, OverflowError):
        return RepoActivity(error="could not read control history")
