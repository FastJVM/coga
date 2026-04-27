"""`relay create` — scaffold a draft ticket and launch the bootstrap/ticket skill."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer

from relay.blackboard import render_blackboard
from relay.config import Config, ConfigError, load_config
from relay.logfile import append_log
from relay.paths import (
    context_path,
    skill_path,
    tasks_dir,
    workflow_path,
)
from relay.slugify import slugify
from relay.tasks import (
    TaskNotFoundError,
    list_tasks,
    read_ticket,
    resolve_bootstrap,
)
from relay.ticket import Ticket
from relay.workflow import Workflow, WorkflowError

VALID_MODES = {"interactive", "auto", "script"}
VALID_STATUSES = {"draft", "active", "paused", "done"}


def create(
    title: str = typer.Argument(..., help="Ticket title."),
    description: str = typer.Option(None, "--description", "-d", help="One-line description for the ticket body."),
    no_launch: bool = typer.Option(False, "--no-launch", help="Scaffold only; skip auto-launching the bootstrap/ticket skill."),
) -> None:
    """Scaffold a `draft` ticket seeded from the `bootstrap/ticket` shim,
    then auto-launch that skill on it so the agent can interview the human
    and fill in workflow / contexts / assignee / description.

    Scripted callers and the recurring scaffolder use the `scaffold_task()`
    Python API directly with the full keyword surface.
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        shim = resolve_bootstrap(cfg, "ticket")
    except TaskNotFoundError as exc:
        _bail(
            f"{exc}\n"
            "`relay create` requires a `bootstrap/ticket` shim. "
            "Run `relay init` (or `relay init --update`) to install it."
        )
    shim_ticket = read_ticket(shim)

    try:
        ref = scaffold_task(
            cfg=cfg,
            title=title,
            workflow_name=None,
            contexts=[],
            mode=shim_ticket.mode,
            owner=cfg.current_user,
            assignee=shim_ticket.assignee,
            watchers=[],
            status="draft",
            skill=shim_ticket.skill,
            description=description,
        )
    except (ConfigError, WorkflowError, FileNotFoundError, ValueError) as exc:
        _bail(str(exc))

    typer.echo(f"Created {ref['slug']} at {ref['path']}")

    if no_launch:
        return

    # Hand off to launch — composes the bootstrap/ticket skill into the
    # prompt and starts an interactive session on the freshly-scaffolded
    # draft. Imported lazily to avoid a circular import at module load.
    # Calling the typer-decorated function directly bypasses Typer's arg
    # parsing, so explicit defaults are required for `title` and `force`.
    from relay.commands.launch import launch as launch_command

    launch_command(task=ref["slug"], title=None, force=False)


# --- core scaffold ------------------------------------------------------------


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
    skill: str | None = None,
    slug_override: str | None = None,
    description: str | None = None,
    created_by: str = "human",
) -> dict[str, Any]:
    """Create a task directory. Returns dict with {id_slug, path}."""
    owner = owner or cfg.current_user
    assignee = assignee or owner
    status = status or cfg.default_status

    # Validate contexts exist, dedupe
    contexts = _dedupe(contexts)
    missing_ctx = [c for c in contexts if not context_path(cfg, c).is_file()]
    if missing_ctx:
        raise ValueError(f"Unknown contexts: {missing_ctx}")

    # Load & validate workflow (if given)
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

    # Pick a slug. If it collides with an existing task dir, auto-suffix
    # `-2`, `-3`, … so two tasks with the same title don't clash.
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

    # Build frontmatter
    fm: dict[str, Any] = {"title": title, "status": status, "mode": mode}
    if owner:
        fm["owner"] = owner
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

    # Blackboard from template
    (task_dir / "blackboard.md").write_text(render_blackboard(title))

    # Empty log, then first entry
    (task_dir / "log.md").write_text("")
    actor = f"{created_by}:{cfg.current_user}" if created_by == "human" else created_by
    append_log(task_dir, actor, f"created (mode={mode}, status={status})")

    return {"slug": slug, "path": task_dir}


# --- helpers ------------------------------------------------------------------


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
