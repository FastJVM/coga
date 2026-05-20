"""Migration helpers — backfill new ticket fields on existing repos.

Called from `relay init --update`. Each migration is idempotent: re-running
on an already-migrated repo is a no-op. Migrations only touch fields they
own; everything else in ticket frontmatter is preserved.
"""

from __future__ import annotations

from relay.config import Config
from relay.paths import workflow_path
from relay.tasks import list_tasks
from relay.ticket import Ticket, TicketError
from relay.workflow import Workflow, WorkflowError


def backfill_role_fields(cfg: Config) -> list[str]:
    """Backfill canonical ticket frontmatter on existing repos.

    Two layers:
      - `human` ← ticket's `owner` (humans usually own tasks).
      - `agent` ← ticket's current `assignee` if config knows it as an agent
        type, else the first-declared agent type in `[agents]`.
      - `assignee` ← the current workflow step's declared role target when
        available, else the ticket owner.
      - `contexts: []`, `skills: []`, `workflow: null` filled in if missing
        — these are required keys in the canonical schema.
      - Legacy string workflow refs are frozen from `workflows/<ref>.md` when
        that workflow file exists.
      - Legacy workflow-step singular `skill:` is migrated to plural `skills:`.

    Tickets already canonical are skipped. Returns the list of slugs rewritten.
    """
    agent_types = set(cfg.agents)
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
            inferred = _infer_agent(ticket, cfg, agent_types)
            if inferred:
                ticket.frontmatter["agent"] = inferred
                changed = True
        if "contexts" not in ticket.frontmatter:
            ticket.frontmatter["contexts"] = []
            changed = True
        # Legacy `skill:` singular at ticket level → `skills:` plural.
        if "skill" in ticket.frontmatter and "skills" not in ticket.frontmatter:
            legacy = ticket.frontmatter.pop("skill")
            if isinstance(legacy, str) and legacy.strip():
                ticket.frontmatter["skills"] = [legacy]
            else:
                ticket.frontmatter["skills"] = []
            changed = True
        elif "skills" not in ticket.frontmatter:
            ticket.frontmatter["skills"] = []
            changed = True
        if "workflow" not in ticket.frontmatter:
            ticket.frontmatter["workflow"] = None
            changed = True
        elif isinstance(ticket.frontmatter["workflow"], str):
            if _freeze_legacy_workflow_ref(ticket, cfg):
                changed = True
        if _migrate_frozen_workflow_step_skill(ticket.frontmatter.get("workflow")):
            changed = True
        if "assignee" not in ticket.frontmatter:
            inferred = _infer_assignee(ticket)
            if inferred:
                ticket.frontmatter["assignee"] = inferred
                changed = True

        if changed:
            _reorder_role_fields(ticket.frontmatter)
            ticket.write(ticket_path)
            rewritten.append(ref.slug)
    return rewritten


def _migrate_frozen_workflow_step_skill(wf: object) -> bool:
    """Rewrite legacy singular `skill:` → plural `skills:` inside frozen steps.

    Mutates the frozen workflow dict in place; returns True if anything changed.
    """
    if not isinstance(wf, dict):
        return False
    steps = wf.get("steps")
    if not isinstance(steps, list):
        return False
    changed = False
    for step in steps:
        if not isinstance(step, dict):
            continue
        if "skill" in step and "skills" not in step:
            legacy = step.pop("skill")
            if isinstance(legacy, str) and legacy.strip():
                step["skills"] = [legacy]
            else:
                step["skills"] = []
            changed = True
    return changed


def _infer_agent(ticket: Ticket, cfg: Config, agent_types: set[str]) -> str | None:
    if ticket.assignee and ticket.assignee in agent_types:
        return ticket.assignee
    default = cfg.default_agent()
    return default.name if default else None


def _infer_assignee(ticket: Ticket) -> str | None:
    role_fields = {
        "owner": ticket.owner,
        "human": ticket.frontmatter.get("human"),
        "agent": ticket.frontmatter.get("agent"),
    }
    wf = ticket.frontmatter.get("workflow")
    if isinstance(wf, dict):
        idx = ticket.step_index()
        steps = wf.get("steps")
        if idx is not None and isinstance(steps, list) and 1 <= idx <= len(steps):
            step = steps[idx - 1]
            if isinstance(step, dict):
                role = step.get("assignee")
                if isinstance(role, str):
                    resolved = role_fields.get(role)
                    if isinstance(resolved, str) and resolved.strip():
                        return resolved
    for key in ("owner", "human", "agent"):
        value = role_fields.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _freeze_legacy_workflow_ref(ticket: Ticket, cfg: Config) -> bool:
    ref = ticket.frontmatter.get("workflow")
    if not isinstance(ref, str) or not ref.strip():
        return False
    try:
        ticket.frontmatter["workflow"] = Workflow.load(workflow_path(cfg, ref)).freeze()
    except WorkflowError:
        return False
    return True


def _reorder_role_fields(fm: dict) -> None:
    """Place `human:` and `agent:` next to `owner:` for readability.

    Frontmatter dicts are insertion-ordered by yaml.safe_dump (we set
    `sort_keys=False`), so the simplest way to insert fields at a specific
    position is to rebuild the dict in the desired order.
    """
    # Canonical order matches scaffold.py.
    preferred = [
        "title",
        "status",
        "mode",
        "owner",
        "human",
        "agent",
        "assignee",
        "contexts",
        "skills",
        "workflow",
    ]
    leading: dict = {}
    for key in preferred:
        if key in fm:
            leading[key] = fm[key]
    rest = {k: v for k, v in fm.items() if k not in leading}
    fm.clear()
    fm.update(leading)
    fm.update(rest)


__all__ = ["backfill_role_fields"]
