"""Auto-bump active tickets whose linked PR has merged.

Scope: tickets whose `## Dev` blackboard section names a PR, where the PR
is merged on GitHub, and where the ticket is on its final workflow step
(or has no workflow). One bump = `done`. Mid-workflow merges stay alone
— a merge there is suspicious and the human should bump explicitly.

The PR link convention lives in the `dev/code` context: a `pr:` line
under `## Dev` on the blackboard. We parse it directly; relay-the-CLI
treats the blackboard as plain text on purpose.

Three callers:
  - `relay automerge` (post-merge git hook + manual invocation) — uses
    `auto_bump_merged` to sweep all active tickets.
  - `relay status` (opportunistic fallback, `quiet=True` — gh failures
    swallowed so the fast command stays fast).
  - `relay launch <slug>` (pre-launch freshness check) — uses
    `auto_bump_one` to check just the ticket about to be launched.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from relay.bump import mark_done
from relay.config import Config
from relay.tasks import TaskRef, list_tasks, read_ticket
from relay.ticket import Ticket, TicketError


class GhError(Exception):
    """Raised when `gh` is missing, unauthed, or returns a non-zero exit."""


_DEV_SECTION_RE = re.compile(
    r"^##\s+Dev\s*\n(.*?)(?=\n##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
_PR_LINE_RE = re.compile(r"^\s*pr:\s*(\S+)\s*$", re.MULTILINE)
_PR_NUMBER_RE = re.compile(r"/pull/(\d+)")


def parse_pr_url(blackboard_text: str) -> str | None:
    """Return the `pr:` URL under `## Dev`, or None if absent."""
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    pr = _PR_LINE_RE.search(section.group(1))
    return pr.group(1) if pr else None


def parse_pr_number(url: str) -> int | None:
    m = _PR_NUMBER_RE.search(url)
    return int(m.group(1)) if m else None


def pr_state(url: str) -> str:
    """Query `gh` for the PR's state. Raises GhError on any failure.

    Returns the raw state string ("MERGED", "CLOSED", "OPEN").
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "view", url, "--json", "state"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhError("`gh` not found on PATH") from exc
    if result.returncode != 0:
        raise GhError(
            f"`gh pr view {url}` failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GhError(f"`gh pr view {url}` returned non-JSON: {exc}") from exc
    return str(data.get("state", ""))


def _on_final_step(ticket: Ticket) -> bool:
    wf = ticket.workflow
    if not isinstance(wf, dict) or not wf.get("steps"):
        # No workflow → bump = done. Treat as "final step".
        return True
    steps = wf["steps"]
    idx = ticket.step_index()
    return idx is not None and idx >= len(steps)


def _candidate(ticket: Ticket) -> bool:
    return ticket.status == "active" and _on_final_step(ticket)


def _try_bump_one(cfg: Config, ref: TaskRef, *, quiet: bool) -> bool:
    """Check `ref`; bump to done iff its linked PR has merged.

    Returns True iff the ticket was bumped. Always raises `GhError` on
    `gh` failure — callers decide whether to swallow or surface.
    """
    try:
        ticket = read_ticket(ref)
    except TicketError:
        return False
    if not _candidate(ticket):
        return False

    url = _read_pr_url(ref.path)
    if not url:
        return False

    state = pr_state(url)
    if state != "MERGED":
        return False

    # Re-read in case a concurrent caller (other hook, status, manual
    # bump) already handled this ticket. Mark_done is the gate.
    try:
        ticket = read_ticket(ref)
    except TicketError:
        return False
    if not _candidate(ticket):
        return False

    number = parse_pr_number(url)
    pr_label = f"PR #{number}" if number is not None else "the linked PR"
    actor = f"human:{cfg.current_user}"
    slack_text = (
        f"🎉 *{ref.id_slug}* \"{ticket.title}\" "
        f"auto-bumped on merge of {pr_label}"
    )
    log_message = f"auto-bumped on merge of {pr_label} → done"
    echo = None if quiet else f"{ref.id_slug}: done (auto, {pr_label})"

    mark_done(
        cfg,
        ref,
        ticket,
        actor=actor,
        log_message=log_message,
        slack_text=slack_text,
        image_url=cfg.gif_for("done"),
        echo=echo,
    )
    return True


def auto_bump_merged(cfg: Config, *, quiet: bool = False) -> int:
    """Walk active tickets; bump those whose linked PR has merged.

    Returns the count of bumped tickets.

    `quiet=True` suppresses stdout echoes and swallows `GhError` (gh
    missing or unauthed). The explicit `relay automerge` command sets
    `quiet=False` so a missing `gh` surfaces as a real failure;
    `relay status` sets `quiet=True` so a missing `gh` doesn't break
    the fast command.
    """
    bumped = 0
    for ref in list_tasks(cfg):
        try:
            if _try_bump_one(cfg, ref, quiet=quiet):
                bumped += 1
        except GhError:
            if quiet:
                # Status fallback: don't break the fast command. The
                # explicit `relay automerge` path will surface this.
                return bumped
            raise
    return bumped


def auto_bump_one(cfg: Config, ref: TaskRef, *, quiet: bool = False) -> bool:
    """Check a single ticket; bump to done iff its linked PR has merged.

    Same gating as `auto_bump_merged`: ticket must be active, on its
    final workflow step (or have no workflow), and have a `pr:` line
    under `## Dev` in the blackboard.

    Always raises `GhError` if the `gh` lookup fails. Callers (e.g.
    `relay launch`) decide whether to surface as a hard failure or
    warn-and-continue.

    Returns True iff the ticket was bumped to done.
    """
    return _try_bump_one(cfg, ref, quiet=quiet)


def _read_pr_url(task_path: Path) -> str | None:
    bb = task_path / "blackboard.md"
    if not bb.is_file():
        return None
    try:
        return parse_pr_url(bb.read_text())
    except OSError as exc:
        # A read error on a single blackboard shouldn't sink the scanner.
        sys.stderr.write(f"[automerge] could not read {bb}: {exc}\n")
        return None


__all__ = [
    "GhError",
    "auto_bump_merged",
    "auto_bump_one",
    "parse_pr_number",
    "parse_pr_url",
    "pr_state",
]
