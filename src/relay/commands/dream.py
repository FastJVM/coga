"""`relay dream` — create an ad-hoc Dream cleanup run."""

from __future__ import annotations

import sys
from importlib.resources import files

import typer

from relay.config import Config, ConfigError, load_config
from relay.scaffold import scaffold_task


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
        assignee = agent or _default_agent(cfg)
        cfg.agent_type_for(cfg.current_user, assignee)
    except ConfigError as exc:
        _bail(str(exc))

    try:
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
    typer.echo(f"Created {slug}")
    if no_launch:
        typer.echo(f"Run `relay launch {slug}` to start the Dream pass.")
        return

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


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)

