"""Migration helpers — backfill new ticket fields on existing repos.

Called from `relay init --update`. Each migration is idempotent: re-running
on an already-migrated repo is a no-op. Migrations only touch fields they
own; everything else in ticket frontmatter is preserved.
"""

from __future__ import annotations

from pathlib import Path

from relay.config import Config
from relay.tasks import list_tasks
from relay.ticket import Ticket, TicketError


def backfill_role_fields(cfg: Config) -> list[str]:
    """Add `human:` and `agent:` to tickets that predate per-step assignees.

    Heuristic:
      - `human` ← ticket's `owner` (humans usually own tasks).
      - `agent` ← ticket's current `assignee` if config knows it as an agent
        nickname, else the owner's lone configured agent if exactly one exists.

    Tickets that already have both fields are skipped. Returns the list of
    relative paths (under `tasks/`) that were rewritten.
    """
    agent_nicknames = {nick for a in cfg.assignees.values() for nick in a.agents}
    rewritten: list[str] = []
    for ref in list_tasks(cfg):
        ticket_path = ref.path / "ticket.md"
        try:
            ticket = Ticket.read(ticket_path)
        except (TicketError, FileNotFoundError):
            continue

        changed = False
        if "human" not in ticket.frontmatter and ticket.owner:
            ticket.frontmatter["human"] = ticket.owner
            changed = True
        if "agent" not in ticket.frontmatter:
            inferred = _infer_agent(ticket, cfg, agent_nicknames)
            if inferred:
                ticket.frontmatter["agent"] = inferred
                changed = True

        if changed:
            _reorder_role_fields(ticket.frontmatter)
            ticket.write(ticket_path)
            rewritten.append(ref.slug)
    return rewritten


def _infer_agent(ticket: Ticket, cfg: Config, agent_nicknames: set[str]) -> str | None:
    if ticket.assignee and ticket.assignee in agent_nicknames:
        return ticket.assignee
    if ticket.owner:
        owner_cfg = cfg.assignees.get(ticket.owner)
        if owner_cfg and len(owner_cfg.agents) == 1:
            return next(iter(owner_cfg.agents))
    return None


def _reorder_role_fields(fm: dict) -> None:
    """Place `human:` and `agent:` next to `owner:` for readability.

    Frontmatter dicts are insertion-ordered by yaml.safe_dump (we set
    `sort_keys=False`), so the simplest way to insert fields at a specific
    position is to rebuild the dict in the desired order.
    """
    # Canonical order: title, status, mode, owner, human, agent, assignee, ...
    preferred = ["title", "status", "mode", "owner", "human", "agent", "assignee"]
    leading: dict = {}
    for key in preferred:
        if key in fm:
            leading[key] = fm[key]
    rest = {k: v for k, v in fm.items() if k not in leading}
    fm.clear()
    fm.update(leading)
    fm.update(rest)


__all__ = ["backfill_role_fields"]
