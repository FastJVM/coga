"""`relay dream` — create an ad-hoc Dream cleanup run."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import typer

from relay.config import Config, ConfigError, load_config
from relay.scaffold import scaffold_task
from relay.tasks import TaskRef
from relay.ticket import Ticket


@dataclass(frozen=True)
class DreamScriptWorker:
    slug: str
    skill: str
    title: str
    description: str


def dream(
    title: str = typer.Option(
        "Dream",
        "--title",
        help="Title for the Dream task. Slug suffixes avoid collisions.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Agent nickname to assign. Defaults to the current user's first configured agent.",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        help="Launch mode for the Dream run: auto or interactive.",
    ),
    no_launch: bool = typer.Option(
        False,
        "--no-launch",
        help="Create the Dream task but do not launch it.",
    ),
) -> None:
    """Create and launch an ad-hoc Dream cleanup run."""
    if mode not in {"auto", "interactive"}:
        _bail("--mode must be 'auto' or 'interactive'")

    try:
        cfg = load_config()
        typer.echo(f"Dream: repo root {cfg.repo_root}")
        assignee = agent or _default_agent(cfg)
        agent_type = cfg.agent_type_for(cfg.current_user, assignee)
        typer.echo(
            f"Dream: using assignee {assignee} "
            f"(agent type {agent_type.name}, mode {mode})"
        )
    except ConfigError as exc:
        _bail(str(exc))

    try:
        typer.echo(f"Dream: scaffolding task {title!r}")
        result = scaffold_task(
            cfg=cfg,
            title=title,
            workflow_name=None,
            contexts=[],
            mode=mode,
            owner=cfg.current_user,
            assignee=assignee,
            watchers=[],
            status="draft",
            description=_dream_body(),
            created_by="dream",
        )
    except (ConfigError, ValueError) as exc:
        _bail(str(exc))

    slug = result["slug"]
    typer.echo(f"Dream: created task {slug} at {result['path']}")
    typer.echo(f"Created {slug}")
    if no_launch:
        typer.echo("Dream: launch skipped (--no-launch)")
        typer.echo(f"Run `relay launch {slug}` to start the Dream pass.")
        return

    _run_deterministic_workers(cfg, slug, Path(result["path"]), assignee=assignee)

    typer.echo(f"Dream: launching agent for {slug}")
    from relay.commands.launch import launch

    launch(slug, title=None, agent_override=None, prompt_report=False, force=False)


def _default_agent(cfg: Config) -> str:
    current = cfg.assignees.get(cfg.current_user)
    if current is None or not current.agents:
        raise ConfigError(
            f"Current user {cfg.current_user!r} has no configured agent nicknames. "
            "Pass --agent or add one under [assignees.<user>].agents."
        )
    return next(iter(current.agents))


def _dream_body() -> str:
    return files("relay.resources").joinpath("dream.md").read_text().strip()


def _run_deterministic_workers(
    cfg: Config, slug: str, task_path: Path, *, assignee: str
) -> None:
    """Run Dream's deterministic workers as ordinary Relay script tasks."""
    workers = [
        DreamScriptWorker(
            slug="validate-drift",
            skill="bootstrap/dream/tasks/validate-drift",
            title="Dream worker: validate drift",
            description="Run the deterministic validate-drift worker for a parent Dream run.",
        ),
        DreamScriptWorker(
            slug="cleanup-orphan-markers",
            skill="bootstrap/dream/tasks/cleanup-orphan-markers",
            title="Dream worker: cleanup orphan markers",
            description="Run the deterministic orphan-marker cleanup worker for a parent Dream run.",
        ),
    ]

    for worker in workers:
        typer.echo(f"Dream: scaffolding script worker {worker.slug}")
        child = _scaffold_script_worker_task(cfg, slug, worker, assignee=assignee)
        typer.echo(f"Dream: launching script worker {child.slug}")
        from relay.commands.launch import launch

        try:
            launch(
                child.slug,
                title=None,
                agent_override=None,
                prompt_report=False,
                force=False,
            )
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            if code != 0:
                _bail(
                    f"Dream script worker {child.slug} exited with {code}; "
                    "agent launch skipped."
                )

        typer.echo(f"Dream: marking script worker {child.slug} done")
        from relay.commands.bump import bump

        bump(child.slug, message=f"parent Dream run: {slug}")
        _append_child_worker_result(task_path / "blackboard.md", child)
        typer.echo(f"Dream: script worker {child.slug} complete")


def _scaffold_script_worker_task(
    cfg: Config,
    parent_slug: str,
    worker: DreamScriptWorker,
    *,
    assignee: str,
) -> TaskRef:
    result = scaffold_task(
        cfg=cfg,
        title=f"{worker.title} ({parent_slug})",
        workflow_name=None,
        contexts=[],
        mode="script",
        owner=cfg.current_user,
        assignee=assignee,
        watchers=[],
        status="active",
        slug_override=f"{parent_slug}-{worker.slug}",
        description=(
            f"Parent Dream task: `{parent_slug}`.\n\n"
            f"{worker.description}\n\n"
            "This is a child script task created by `relay dream`; do not edit "
            "its workflow by hand."
        ),
        created_by="dream",
    )
    ref = TaskRef(slug=result["slug"], path=Path(result["path"]))
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["workflow"] = {
        "name": "dream/script-worker",
        "steps": [{"name": "run", "skill": worker.skill}],
    }
    ticket.frontmatter["step"] = "1 (run)"
    ticket.write(ref.path / "ticket.md")
    return ref


def _append_child_worker_result(parent_blackboard: Path, child: TaskRef) -> None:
    child_blackboard = child.path / "blackboard.md"
    text = child_blackboard.read_text() if child_blackboard.is_file() else ""
    start = text.find("## Dream Worker:")
    result = text[start:].strip() if start >= 0 else text.strip()
    if not result:
        result = "(worker wrote no blackboard result)"

    existing = parent_blackboard.read_text() if parent_blackboard.is_file() else ""
    separator = "" if not existing or existing.endswith("\n\n") else "\n\n"
    section = (
        f"## Dream Child Worker: {child.slug}\n\n"
        f"Source task: `relay-os/tasks/{child.slug}/`\n\n"
        f"{result}\n"
    )
    parent_blackboard.write_text(existing + separator + section)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
