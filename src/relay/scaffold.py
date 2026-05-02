"""Task directory scaffolding — write a fresh ticket directory to disk."""

from __future__ import annotations

from typing import Any

from relay.blackboard import render_blackboard
from relay.config import Config
from relay.logfile import append_log
from relay.paths import (
    context_path,
    skill_path,
    tasks_dir,
    workflow_path,
)
from relay.slugify import slugify
from relay.tasks import list_tasks
from relay.ticket import Ticket
from relay.workflow import VALID_ASSIGNEE_ROLES, Workflow


def scaffold_task(
    *,
    cfg: Config,
    title: str,
    workflow_name: str | None,
    contexts: list[str],
    mode: str,
    owner: str | None,
    assignee: str | None,
    watchers: list[str],
    status: str | None,
    human: str | None = None,
    agent: str | None = None,
    skill: str | None = None,
    slug_override: str | None = None,
    description: str | None = None,
    created_by: str = "human",
) -> dict[str, Any]:
    """Create a task directory. Returns dict with {slug, path}."""
    owner = owner or cfg.current_user
    status = status or cfg.default_status
    human = human or owner
    agent = agent or _default_agent_for(cfg, owner, assignee)

    contexts = _dedupe(contexts)
    missing_ctx = [c for c in contexts if not context_path(cfg, c).is_file()]
    if missing_ctx:
        raise ValueError(f"Unknown contexts: {missing_ctx}")

    wf: Workflow | None = None
    if workflow_name:
        wf = Workflow.load(workflow_path(cfg, workflow_name))
        missing_skills = [
            s.skill for s in wf.steps if s.skill and not skill_path(cfg, s.skill).is_file()
        ]
        if missing_skills:
            raise ValueError(
                f"Workflow {workflow_name!r} references missing skills: {missing_skills}"
            )

    # Initial assignee: if step 1 declares a role, resolve against the
    # ticket's role fields. Otherwise honor the explicit `assignee` arg or
    # fall back to the owner.
    role_fields = {"owner": owner, "human": human, "agent": agent}
    if wf and wf.steps[0].assignee:
        role = wf.steps[0].assignee
        resolved = role_fields.get(role)
        if not resolved:
            raise ValueError(
                f"Workflow {workflow_name!r} step 1 assignee={role!r} but no `{role}` "
                f"set on the new ticket."
            )
        assignee = resolved
    else:
        assignee = assignee or owner

    base_slug = slug_override or slugify(title)
    existing_slugs = {t.slug for t in list_tasks(cfg)}
    slug = base_slug
    n = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{n}"
        n += 1
    task_dir = tasks_dir(cfg) / slug
    if task_dir.exists():
        raise ValueError(f"Task directory already exists: {task_dir}")
    task_dir.mkdir(parents=True)

    fm: dict[str, Any] = {"title": title, "status": status, "mode": mode}
    if owner:
        fm["owner"] = owner
    if human:
        fm["human"] = human
    if agent:
        fm["agent"] = agent
    if assignee:
        fm["assignee"] = assignee
    if watchers:
        fm["watchers"] = list(watchers)
    if wf:
        fm["workflow"] = wf.freeze()
        first_step = wf.steps[0].name
        fm["step"] = f"1 ({first_step})"
    if skill:
        fm["skill"] = skill
    if contexts:
        fm["contexts"] = list(contexts)

    desc_body = (description or "").strip()
    body = f"## Description\n\n{desc_body}\n\n## Context\n\n"
    Ticket(frontmatter=fm, body=body).write(task_dir / "ticket.md")

    (task_dir / "blackboard.md").write_text(render_blackboard(title))

    (task_dir / "log.md").write_text("")
    actor = f"{created_by}:{cfg.current_user}" if created_by == "human" else created_by
    append_log(task_dir, actor, f"created (mode={mode}, status={status})")

    return {"slug": slug, "path": task_dir}


def _default_agent_for(
    cfg: Config, owner: str | None, assignee: str | None
) -> str | None:
    """Best-effort default for the new ticket's `agent:` field.

    Two signals, in order:
      1. If the explicit `assignee` arg is a known agent nickname, use it —
         the caller already named the agent.
      2. Else if `owner` has exactly one configured agent, use that.

    Returns None if neither signal resolves; better to leave the field blank
    than guess wrong.
    """
    agent_nicknames = {nick for a in cfg.assignees.values() for nick in a.agents}
    if assignee and assignee in agent_nicknames:
        return assignee
    if owner:
        owner_cfg = cfg.assignees.get(owner)
        if owner_cfg and len(owner_cfg.agents) == 1:
            return next(iter(owner_cfg.agents))
    return None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


__all__ = ["scaffold_task"]
