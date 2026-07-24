"""Reminder scan for first-class blocked tasks.

This is the deterministic recipe for the `coga/blockers/remind` skill (run by
the `blocker-reminders` recurring sweep). It is a single-consumer maintenance
recipe, so under the microkernel policy it lives in the skill dir rather than in
core `src/coga/` — it imports only shared core infra (`git`, `blackboard`,
`config`, `notification`, `taskfile`, `tasks`, `ticket`).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from coga import git
from coga.blackboard import (
    Blocker,
    append_to_section_text,
    parse_blockers_text,
)
from coga.config import Config
from coga.notification import post
from coga.taskfile import TaskFileError, read_blackboard, replace_blackboard
from coga.tasks import TaskRef, list_tasks, read_ticket
from coga.ticket import TicketError


REMINDERS_HEADING = "Blocker reminders"

_REMINDER_RE = re.compile(
    r"^\s*[-*]\s+(?P<fingerprint>[0-9a-f]{12})\s+last_reminded:\s*(?P<ts>.+?)\s*$"
)


@dataclass(frozen=True)
class BlockerReminder:
    """One open blocker eligible for a recurring reminder."""

    slug: str
    title: str
    status: str
    step: str
    owner: str | None
    watchers: list[str]
    blocker: Blocker
    fingerprint: str
    reminded: bool
    task_path: Path
    ticket_path: Path

    @property
    def next_command(self) -> str:
        return f'coga unblock {self.slug} --answer "..."'


def scan_blocker_reminders(
    cfg: Config,
    *,
    refs: Iterable[TaskRef] | None = None,
) -> list[BlockerReminder]:
    """Scan `status: blocked` tasks for unresolved blockers."""
    out: list[BlockerReminder] = []
    for ref in refs if refs is not None else list_tasks(cfg):
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.status != "blocked":
            continue

        try:
            blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
        except (OSError, TaskFileError):
            continue

        reminded = reminder_fingerprints(blackboard)
        for blocker in parse_blockers_text(blackboard):
            if blocker.resolved:
                continue
            fingerprint = _fingerprint(blocker)
            out.append(
                BlockerReminder(
                    slug=ref.id_slug,
                    title=ticket.title,
                    status=ticket.status or "-",
                    step=ticket.step or "-",
                    owner=ticket.owner,
                    watchers=ticket.watchers,
                    blocker=blocker,
                    fingerprint=fingerprint,
                    reminded=fingerprint in reminded,
                    task_path=ref.path,
                    ticket_path=ref.ticket_path,
                )
            )
    return out


def reminder_fingerprints(blackboard_text: str) -> set[str]:
    """Return blocker reminder fingerprints already recorded on a task."""
    section = _section(blackboard_text, REMINDERS_HEADING)
    if not section:
        return set()
    found: set[str] = set()
    for line in section.splitlines():
        match = _REMINDER_RE.match(line)
        if match:
            found.add(match.group("fingerprint"))
    return found


def record_reminder(ticket_path: Path, fingerprint: str, *, now: datetime) -> bool:
    """Record one reminder watermark in the task blackboard.

    Returns False when the fingerprint is already present.
    """
    blackboard = read_blackboard(ticket_path)
    if fingerprint in reminder_fingerprints(blackboard):
        return False
    stamp = now.strftime("%Y-%m-%d %H:%M")
    entry = f"- {fingerprint} last_reminded: {stamp}"
    replace_blackboard(
        ticket_path,
        append_to_section_text(blackboard, REMINDERS_HEADING, entry),
    )
    return True


def remind_blocked_tasks(cfg: Config, *, now: datetime | None = None) -> int:
    """Post one reminder for each blocked-task ask not yet watermarked."""
    now = now or datetime.now()
    reminded = 0
    for reminder in scan_blocker_reminders(cfg):
        if reminder.reminded:
            continue
        owner = reminder.owner or cfg.current_user
        post(
            cfg,
            (
                f"Blocker reminder: *{reminder.slug}* \"{reminder.title}\" "
                f"is blocked: {reminder.blocker.reason}. Run "
                f"`{reminder.next_command}` to record the answer and resume."
            ),
            task_path=reminder.task_path,
            owner=owner,
            watchers=reminder.watchers,
        )
        if record_reminder(reminder.ticket_path, reminder.fingerprint, now=now):
            git.sync_task_state(
                cfg,
                reminder.task_path,
                message=f"Ticket: {reminder.slug} — blocker reminder",
            )
        reminded += 1
    return reminded


_SECTION_RE = re.compile(r"^##[ \t]+(?P<heading>.+?)\s*$", re.MULTILINE)


def _section(markdown: str, heading: str) -> str:
    target = heading.strip().casefold()
    matches = list(_SECTION_RE.finditer(markdown))
    for i, match in enumerate(matches):
        if match.group("heading").strip().casefold() != target:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        return markdown[match.end():end]
    return ""


def _fingerprint(blocker: Blocker) -> str:
    stamp = blocker.created_at.strftime("%Y-%m-%d %H:%M") if blocker.created_at else ""
    normalized = " ".join(blocker.reason.split()).casefold()
    raw = f"{blocker.id}\n{stamp}\n{blocker.actor}\n{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


__all__ = [
    "BlockerReminder",
    "REMINDERS_HEADING",
    "record_reminder",
    "remind_blocked_tasks",
    "reminder_fingerprints",
    "scan_blocker_reminders",
]
