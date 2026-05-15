"""`relay retire` — wrap up a done task: retro + delete + prune branch."""

from __future__ import annotations

import sys
from importlib.resources import files

import typer

from relay.config import Config, ConfigError, load_config
from relay.scaffold import scaffold_task
from relay.slugify import slugify
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def retire(
    task: str = typer.Argument(..., help="Done task ID or id-slug to retire."),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Agent nickname to assign. Defaults to the current user's first configured agent.",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        help="Launch mode for the retire run: auto or interactive.",
    ),
    no_launch: bool = typer.Option(
        False,
        "--no-launch",
        help="Create the retire task but do not launch it.",
    ),
) -> None:
    """Wrap up a done task by running retro/done-ticket against it.

    Validates the named task is `status: done`, then scaffolds a one-shot
    ad-hoc task whose body invokes the `retro/done-ticket` skill against it.
    The retro skill opens the PR that records the `## Retro` marker, edits the
    knowledge base if warranted, and deletes the source task directory in the
    same PR. Branch hygiene (local prune, stale-branch sweep) is a Dream
    concern, not retire's.
    """
    if mode not in {"auto", "interactive"}:
        _bail("--mode must be 'auto' or 'interactive'")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    typer.echo(f"Retire: target task {ref.id_slug} at {ref.path}")
    source = read_ticket(ref)
    if source.status != "done":
        _bail(
            f"Retire only operates on done tickets — {ref.id_slug} is "
            f"{source.status!r}. Bump it to done first."
        )

    try:
        assignee = agent or _default_agent(cfg)
        agent_type = cfg.agent_type_for(cfg.current_user, assignee)
    except ConfigError as exc:
        _bail(str(exc))
    typer.echo(
        f"Retire: using assignee {assignee} "
        f"(agent type {agent_type.name}, mode {mode})"
    )

    title = f"Retire {ref.slug}"
    slug_override = f"retire-{slugify(ref.slug)}"
    try:
        typer.echo(f"Retire: scaffolding task {title!r}")
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
            slug_override=slug_override,
            description=_retire_body(ref.slug),
            created_by="retire",
        )
    except (ConfigError, ValueError) as exc:
        _bail(str(exc))

    slug = result["slug"]
    typer.echo(f"Retire: created task {slug} at {result['path']}")
    typer.echo(f"Created {slug}")
    if no_launch:
        typer.echo("Retire: launch skipped (--no-launch)")
        typer.echo(f"Run `relay launch {slug}` to start the retire pass.")
        return

    typer.echo(f"Retire: launching {slug}")
    from relay.commands.launch import launch

    launch(slug, agent_override=None, prompt_report=False, no_verify=False)


def _default_agent(cfg: Config) -> str:
    current = cfg.assignees.get(cfg.current_user)
    if current is None or not current.agents:
        raise ConfigError(
            f"Current user {cfg.current_user!r} has no configured agent nicknames. "
            "Pass --agent or add one under [assignees.<user>].agents."
        )
    return next(iter(current.agents))


def _retire_body(target_slug: str) -> str:
    template = files("relay.resources").joinpath("retire.md").read_text()
    return template.format(slug=target_slug).strip()


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
