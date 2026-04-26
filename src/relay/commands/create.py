"""`relay create` — scaffold a new task directory."""

from __future__ import annotations

import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

import typer

from relay.config import Config, ConfigError, load_config
from relay.counter import next_id
from relay.logfile import append_log
from relay.paths import (
    context_path,
    project_relay_dir,
    project_tasks_dir,
    skill_path,
    workflow_path,
)
from relay.slugify import slugify
from relay.ticket import Ticket
from relay.workflow import Workflow, WorkflowError

VALID_MODES = {"interactive", "auto", "script"}
VALID_STATUSES = {"design", "ready", "active", "paused", "done", "canceled", "failed"}


def create(
    project: str = typer.Option(None, "--project", help="Project name from relay.toml."),
    title: str = typer.Option(None, "--title", help="Human-readable title."),
    workflow: str = typer.Option(None, "--workflow", help="Workflow name (e.g. code/with-review)."),
    context: list[str] = typer.Option([], "--context", help="Context ref. Repeatable."),
    mode: str = typer.Option("interactive", "--mode", help="interactive | auto | script."),
    owner: str = typer.Option(None, "--owner", help="Defaults to current user."),
    assignee: str = typer.Option(None, "--assignee", help="Defaults to owner."),
    watcher: list[str] = typer.Option([], "--watcher", help="Additional watcher. Repeatable."),
    status: str = typer.Option(None, "--status", help="Defaults to project default_status."),
    suggest: bool = typer.Option(False, "--suggest/--no-suggest", help="Launch create-suggest after scaffold."),
    check_recurring: bool = typer.Option(False, "--check-recurring", help="Scan recurring templates and create due tasks."),
) -> None:
    """Scaffold a new task (or scan recurring templates)."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    if check_recurring:
        from relay.recurring import check_recurring as do_check

        created = do_check(cfg)
        if not created:
            typer.echo("No recurring tasks due.")
            return
        for ref in created:
            typer.echo(f"Created {ref.project}/{ref.id_slug}")
        return

    if not project:
        _bail("--project is required")
    if not title:
        _bail("--title is required")
    if mode not in VALID_MODES:
        _bail(f"--mode must be one of {sorted(VALID_MODES)}")
    if status is not None and status not in VALID_STATUSES:
        _bail(f"--status must be one of {sorted(VALID_STATUSES)}")

    try:
        ref = scaffold_task(
            cfg=cfg,
            project=project,
            title=title,
            workflow_name=workflow,
            contexts=list(context),
            mode=mode,
            owner=owner,
            assignee=assignee,
            watchers=list(watcher),
            status=status,
        )
    except (ConfigError, WorkflowError, FileNotFoundError, ValueError) as exc:
        _bail(str(exc))

    typer.echo(f"Created {ref['project']}/{ref['id_slug']} at {ref['path']}")

    if suggest:
        typer.secho("--suggest not yet implemented (M6).", fg=typer.colors.YELLOW)


# --- core scaffold ------------------------------------------------------------


def scaffold_task(
    *,
    cfg: Config,
    project: str,
    title: str,
    workflow_name: str | None,
    contexts: list[str],
    mode: str,
    owner: str | None,
    assignee: str | None,
    watchers: list[str],
    status: str | None,
    slug_override: str | None = None,
    description: str | None = None,
    created_by: str = "human",
) -> dict[str, Any]:
    """Create a task directory. Returns dict with {project, id_slug, path}."""
    proj = cfg.project(project)
    owner = owner or cfg.current_user
    assignee = assignee or owner
    status = status or proj.default_status

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

    # Allocate ID + slug
    relay_dir = project_relay_dir(cfg, project)
    task_id = next_id(relay_dir)
    slug = slug_override or slugify(title)
    id_slug = f"{task_id:03d}-{slug}"
    tasks_dir = project_tasks_dir(cfg, project)
    task_dir = tasks_dir / id_slug
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
    if contexts:
        fm["contexts"] = list(contexts)

    desc_body = (description or "").strip()
    body = f"## Description\n\n{desc_body}\n\n## Context\n\n"
    Ticket(frontmatter=fm, body=body).write(task_dir / "ticket.md")

    # Blackboard from template
    template = files("relay.resources").joinpath("blackboard.md").read_text()
    (task_dir / "blackboard.md").write_text(
        template.replace("{task_id}", f"{task_id:03d}").replace("{task_title}", title)
    )

    # Empty log, then first entry
    (task_dir / "log.md").write_text("")
    actor = f"{created_by}:{cfg.current_user}" if created_by == "human" else created_by
    append_log(task_dir, actor, f"created (mode={mode}, status={status})")

    return {"project": project, "id_slug": id_slug, "path": task_dir}


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
