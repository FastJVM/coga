"""Auto-close started tickets whose linked PR has merged.

Scope: tickets whose `## Dev` blackboard section names a PR, where the PR
is merged on GitHub, and where the ticket is on its final workflow step
(or has no workflow). One bump = `done`. Mid-workflow merges stay alone
— a merge there is suspicious and the human should bump explicitly.

The PR link convention lives in the `dev/code` context: a `pr:` line
under `## Dev` on the blackboard. We parse it directly; relay-the-CLI
treats the blackboard as plain text on purpose.

One caller: the `autoclose-merged` recurring sweep skill, which runs
`sweep_merged` on a schedule to finish tickets whose PR merged out of
band. That daily sweep is the *sole* trigger for auto-closing merged
tickets — there is intentionally no manual command and no launch-time or
status-time side effect. Accepted tradeoff: a ticket merged today won't
auto-close until the next sweep (≤24h lag).

`relay status` deliberately does NOT call this — it is a read-only view
(principle 6, fail loud, forbids `status`/`show`/`validate` from mutating
state or hitting the network as a side effect of rendering).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from relay.mark import mark_done
from relay.config import Config
from relay.taskfile import TaskFileError, read_blackboard
from relay.tasks import TaskRef, list_tasks, read_ticket
from relay.ticket import Ticket, TicketError


class GhError(Exception):
    """Raised when `gh` is missing, unauthed, or returns a non-zero exit."""


_DEV_SECTION_RE = re.compile(
    r"^##\s+Dev\s*\n(.*?)(?=\n##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
# Tolerate an optional `- ` list prefix, exactly like `_BRANCH_LINE_RE` below:
# `## Dev` lines are written both bare (`pr: <url>`) and bulleted
# (`- pr: <url>`), and the bulleted shape is perfectly natural. Without the
# prefix group a bulleted `pr:` line is invisible to the sweep, so a merged
# final-step ticket is silently skipped and left stranded `in_progress`.
_PR_LINE_RE = re.compile(r"^\s*(?:-\s*)?pr:\s*(\S+)\s*$", re.MULTILINE)
_PR_NUMBER_RE = re.compile(r"/pull/(\d+)")
# The `branch:` line is written inconsistently across existing tickets:
# `branch: my-branch`, `- branch: \`my-branch\``, ``branch: `my-branch` ``.
# Tolerate an optional `- ` list prefix and capture the rest of the line; the
# surrounding backticks/whitespace are stripped in `parse_branch_name`. A
# naive `(\S+)` here would swallow the trailing backtick or miss the list form.
_BRANCH_LINE_RE = re.compile(r"^\s*(?:-\s*)?branch:\s*(.+?)\s*$", re.MULTILINE)


def parse_pr_url(blackboard_text: str) -> str | None:
    """Return the `pr:` URL under `## Dev`, or None if absent."""
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    pr = _PR_LINE_RE.search(section.group(1))
    return pr.group(1) if pr else None


def parse_branch_name(blackboard_text: str) -> str | None:
    """Return the normalized `branch:` name under `## Dev`, or None if absent.

    Normalizes the inconsistent shapes the convention has accreted: tolerates a
    leading "- " list prefix and strips surrounding backticks/whitespace, so the
    bare, list-item, and backtick-wrapped forms all yield the same plain name.
    Without this, `git branch -d <raw>` would target a backtick-wrapped name and
    silently no-op. Returns None for a missing or empty branch line.
    """
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    match = _BRANCH_LINE_RE.search(section.group(1))
    if not match:
        return None
    name = match.group(1).strip().strip("`").strip()
    return name or None


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
    return ticket.status in {"active", "in_progress"} and _on_final_step(ticket)


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

    url = _read_pr_url(ref.ticket_path)
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
    pr_link = f"<{url}|{pr_label}>"
    actor = f"human:{cfg.current_user}"
    # A workflow-less ticket has no current step, so collapse the transition.
    prev = ticket.current_step()
    transition = f": {prev['name']} → done" if prev else " finished"
    digest_transition = f"{prev['name']} → done" if prev else "finished"
    slack_text = (
        f"🎉 *{ref.id_slug}* \"{ticket.title}\"{transition} — {pr_link} merged"
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
        digest_detail=f"auto-bumped: {digest_transition} — {pr_link} merged ✅",
        image_url=cfg.gif_for("done"),
        echo=echo,
    )
    return True


def sweep_merged(cfg: Config, *, quiet: bool = False) -> int:
    """Walk active/in-progress tickets; finish those whose linked PR has merged.

    Returns the count of bumped tickets.

    `quiet=True` suppresses stdout echoes and swallows `GhError` (gh
    missing or unauthed). The recurring sweep skill sets `quiet=False` so a
    missing `gh` surfaces as a real failure.
    """
    bumped = 0
    for ref in list_tasks(cfg):
        try:
            if _try_bump_one(cfg, ref, quiet=quiet):
                bumped += 1
        except GhError:
            if quiet:
                # Quiet callers use this as a best-effort check; the recurring
                # sweep runs loud so gh failures surface.
                return bumped
            raise
    return bumped


def _read_pr_url(ticket: Path) -> str | None:
    if not ticket.is_file():
        return None
    try:
        # The `## Dev` PR link lives in the blackboard region below the fence.
        return parse_pr_url(read_blackboard(ticket, blackboard_required=False))
    except (OSError, TaskFileError) as exc:
        # A read error on a single ticket shouldn't sink the scanner.
        sys.stderr.write(f"[autoclose] could not read {ticket}: {exc}\n")
        return None


__all__ = [
    "GhError",
    "sweep_merged",
    "parse_pr_number",
    "parse_pr_url",
    "parse_branch_name",
    "pr_state",
]
