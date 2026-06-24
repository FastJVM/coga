"""Task directory creating — write a fresh ticket directory to disk."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from relay.blackboard import render_blackboard
from relay.bump import AssigneeResolutionError, resolve_other_agent
from relay.config import Config
from relay.logfile import append_log
from relay.paths import (
    resolve_context_path,
    resolve_skill_path,
    resolve_workflow_path,
    tasks_dir,
)
from relay.slugify import slugify
from relay.taskfile import join_task_body, split_body
from relay.tasks import TaskRef, list_tasks
from relay.ticket import Ticket
from relay.workflow import Workflow


def create_task(
    *,
    cfg: Config,
    title: str,
    workflow_name: str | None,
    contexts: list[str],
    autonomy: str,
    owner: str | None,
    assignee: str | None,
    watchers: list[str],
    status: str | None,
    human: str | None = None,
    agent: str | None = None,
    skills: list[str] | None = None,
    slug_override: str | None = None,
    description: str | None = None,
    body: str | None = None,
    secrets: Any = None,
    script: Any = None,
    created_by: str = "human",
) -> dict[str, Any]:
    """Create a task directory. Returns dict with {slug, path}.

    Pass `description` for the common case — the body is built as the canonical
    `## Description` / `## Context` skeleton. Pass `body` instead to write a
    full ticket body verbatim (recurring creating does this so template
    sections like `## Script config` survive); a `## Context` section is
    appended when the verbatim body lacks one. `body` takes precedence over
    `description`.
    """
    from relay.validate import format_task_issues, validate_task_dir

    owner = owner or cfg.current_user
    status = status or cfg.default_status
    human = human or owner
    agent = agent or _default_agent_for(cfg, assignee)
    if not agent:
        raise ValueError(
            "No default agent configured; declare at least one `[agents.*]` "
            "table in relay.toml (e.g. `[agents.claude]`)."
        )

    contexts = _dedupe(contexts)
    missing_ctx = [c for c in contexts if resolve_context_path(cfg, c) is None]
    if missing_ctx:
        raise ValueError(f"Unknown contexts: {missing_ctx}")

    skills = _dedupe(list(skills or []))
    missing_skills_top = [s for s in skills if resolve_skill_path(cfg, s) is None]
    if missing_skills_top:
        raise ValueError(f"Unknown skills: {missing_skills_top}")

    wf: Workflow | None = None
    if workflow_name:
        wf = Workflow.load(resolve_workflow_path(cfg, workflow_name))
        missing_step_skills: list[str] = []
        for s in wf.steps:
            for ref in s.skills:
                if resolve_skill_path(cfg, ref) is None:
                    missing_step_skills.append(ref)
        if missing_step_skills:
            raise ValueError(
                f"Workflow {workflow_name!r} references missing skills: {missing_step_skills}"
            )

    # Initial assignee: if step 1 declares a role, resolve against the
    # ticket's role fields (or, for `other-agent`, the peer agent from
    # config). Otherwise honor the explicit `assignee` arg or fall back to
    # the owner.
    role_fields = {"owner": owner, "human": human, "agent": agent}
    if wf and wf.steps[0].assignee:
        role = wf.steps[0].assignee
        if role == "other-agent":
            try:
                assignee = resolve_other_agent(cfg, agent)
            except AssigneeResolutionError as exc:
                raise ValueError(
                    f"Workflow {workflow_name!r} step 1 assignee='other-agent': {exc}"
                ) from exc
        else:
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
    # Creates land at the top level (`tasks/<slug>/`), so uniqueness only
    # needs to clear other top-level slugs — a task in a sub-directory may
    # reuse the leaf.
    existing_slugs = {t.slug for t in list_tasks(cfg) if t.directory is None}
    slug = base_slug
    n = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{n}"
        n += 1
    task_dir = tasks_dir(cfg) / slug
    if task_dir.exists():
        raise ValueError(f"Task directory already exists: {task_dir}")
    task_dir.mkdir(parents=True)

    # The TaskRef discovery will report for this new dir — its `id_slug` is the
    # canonical task reference, recorded on the ticket as `slug:` so the file is
    # self-describing.
    created_ref = _task_ref_for_created_dir(slug, task_dir)

    # Canonical frontmatter order. Every key is always present so tasks have
    # a single legible shape on disk, even when contexts / skills / workflow
    # are empty.
    fm: dict[str, Any] = {
        "slug": created_ref.id_slug,
        "title": title,
        "status": status,
        "autonomy": autonomy,
        "owner": owner,
        "human": human,
        "agent": agent,
        "assignee": assignee,
        "contexts": list(contexts),
        "skills": list(skills),
        "workflow": wf.freeze() if wf else None,
        "secrets": secrets,
        "script": script,
    }
    if wf and status != "done":
        first_step = wf.steps[0].name
        fm["step"] = f"1 ({first_step})"
    if watchers:
        fm["watchers"] = list(watchers)

    # Repo-declared extension fields (`[ticket.fields.<name>]`). Seeded
    # with the declared default (or "" if none). Required-but-empty is fine
    # at draft time; `relay mark active` enforces required values at
    # activation time.
    for field_name, spec in cfg.ticket_fields.items():
        fm[field_name] = spec.default

    if body is not None:
        # Recurring creating passes the template body verbatim so sections
        # beyond `## Description` survive into the period task — notably
        # `## Script config`, which drives a script step's mode/sync. Ensure
        # the canonical `## Context` section exists so the body shape stays
        # uniform and compose can read inline task context. A template body may
        # itself carry a blackboard fence + region; strip it so the period task
        # starts from a fresh blackboard (the template's working state stays on
        # the template, not copied into each run).
        above, _ = split_body(body, blackboard_required=False)
        ticket_body = above.rstrip() + "\n"
        if not re.search(r"(?m)^##\s+Context\s*$", ticket_body):
            ticket_body += "\n## Context\n\n"
    else:
        desc_body = (description or "").strip()
        ticket_body = f"## Description\n\n{desc_body}\n\n## Context\n\n"
    # One file per task: body + fence + blackboard, no sibling blackboard.md /
    # log.md. The append-only history goes to the repo-global log.
    full_body = join_task_body(ticket_body, render_blackboard(title))
    Ticket(frontmatter=fm, body=full_body).write(task_dir / "ticket.md")

    actor = f"{created_by}:{cfg.current_user}" if created_by == "human" else created_by
    append_log(cfg, created_ref.id_slug, actor, f"created (autonomy={autonomy}, status={status})")

    issues = validate_task_dir(cfg, created_ref)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise ValueError(
            "Created task failed validation:\n" + format_task_issues(errors)
        )

    return {"slug": created_ref.id_slug, "path": task_dir}


def _task_ref_for_created_dir(slug: str, task_dir: Path) -> TaskRef:
    """Build the same TaskRef that discovery will report for a new task dir."""
    head, sep, leaf = slug.rpartition("/")
    if sep and head:
        return TaskRef(slug=leaf, path=task_dir, directory=head)
    return TaskRef(slug=slug, path=task_dir)


def _default_agent_for(cfg: Config, assignee: str | None) -> str | None:
    """Best-effort default for the new ticket's `agent:` field.

    If the explicit `assignee` arg names a known agent type, use it. Else
    use the first-declared agent type in `[agents]`. TOML preserves
    declaration order, so the team's default agent is whichever block
    appears first.

    Returns None when no agent types are declared; the caller rejects that
    before writing invalid canonical frontmatter.
    """
    if assignee and assignee in cfg.agents:
        return assignee
    default = cfg.default_agent()
    return default.name if default else None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


__all__ = ["create_task"]
