"""`relay retire` — run Retro against a done task."""

from __future__ import annotations

import sys
from importlib.resources import files

import typer

from relay import git
from relay.config import Config, ConfigError, load_config
from relay.scaffold import scaffold_task
from relay.slugify import slugify
from relay.tasks import (
    TaskRef,
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
        "interactive",
        "--mode",
        help="Launch mode for the retire run: interactive. (Auto is temporarily disabled.)",
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
    The retro skill opens a PR when it extracts new durable knowledge; that PR
    records the `## Retro` marker, edits the knowledge base, and deletes the
    source task directory in the same PR. If no new durable knowledge exists,
    Retro direct-deletes the task via `relay delete` (no PR, no marker; recover
    with `git restore`). Branch hygiene (local prune, stale-branch sweep) is a
    Dream concern, not retire's.
    """
    if mode == "auto":
        _bail(
            "mode=auto is temporarily disabled: auto runs produce no live "
            "console output. Run `relay retire <slug> --mode interactive` "
            "from a TTY instead."
        )
    if mode != "interactive":
        _bail("--mode must be 'interactive'")

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
        agent_type = cfg.agent_type(assignee)
    except ConfigError as exc:
        _bail(str(exc))
    typer.echo(
        f"Retire: using assignee {assignee} "
        f"(agent type {agent_type.name}, mode {mode})"
    )

    title = f"Retire {ref.id_slug}"
    slug_override = f"retire-{slugify(ref.id_slug)}"
    try:
        typer.echo(f"Retire: scaffolding task {title!r}")
        result = scaffold_task(
            cfg=cfg,
            title=title,
            # Retire scaffolds straight to `active`; every task past `draft`
            # carries a workflow, so it runs its body through the one-step
            # `direct/body` workflow rather than being a workflow-less active
            # task the validator (rightly) rejects as un-bumpable.
            workflow_name="direct/body",
            contexts=[],
            mode=mode,
            owner=cfg.current_user,
            assignee=assignee,
            watchers=[],
            status="active",
            slug_override=slug_override,
            description=_retire_body(ref.id_slug),
            created_by="retire",
        )
    except (ConfigError, ValueError) as exc:
        _bail(str(exc))

    slug = result["slug"]
    created = TaskRef(slug=slug, path=result["path"])
    typer.echo(f"Retire: created task {slug} at {result['path']} (active)")
    typer.echo(f"Created {slug}")
    git.sync_task_state(
        cfg, created.path, message=f"Ticket: {created.id_slug} — created (retire)"
    )
    if no_launch:
        typer.echo("Retire: launch skipped (--no-launch)")
        typer.echo(f"Run `relay launch {slug}` to start the retire pass.")
        return

    typer.echo(f"Retire: launching {slug}")
    from relay.commands.launch import launch

    launch(
        slug,
        agent_override=None,
        prompt_report=False,
        no_verify=False,
        mode_override=None,
    )


def _default_agent(cfg: Config) -> str:
    default = cfg.default_agent()
    if default is None:
        raise ConfigError(
            "No agent types declared in [agents]. Pass --agent or declare "
            "at least one `[agents.*]` table in relay.toml."
        )
    return default.name


def _retire_body(target_slug: str) -> str:
    template = files("relay.resources").joinpath("retire.md").read_text()
    return template.format(slug=target_slug).strip()


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
