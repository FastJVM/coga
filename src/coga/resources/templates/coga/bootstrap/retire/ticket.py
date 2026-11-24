"""`coga retire` — dispose of a finished task: delete a done one, retro a canceled one.

The script half of the stateless `bootstrap/retire` command ticket, reached by
the default `retire = "launch bootstrap/retire --"` alias. Launch runs it with
the alias's trailing argv; `ticket.md` beside it describes the job.
"""

from __future__ import annotations

import sys
import os

import typer

from coga.config import Config, ConfigError, load_config
from coga.create import create_task
from coga.delete_task import DeleteTaskError, run_delete_task
from coga.paths import RepoResourceUnreadable, load_resource
from coga.slugify import slugify
from coga.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)
from coga.validate import TaskValidationError


app = typer.Typer(add_completion=False)


@app.command()
def retire(
    task: str = typer.Argument(..., help="Done or canceled task ID or id-slug to retire."),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help=(
            "Agent nickname to assign. Defaults to the configured "
            "`default_agent`, else the first declared `[agents.*]` type."
        ),
    ),
    no_launch: bool = typer.Option(
        False,
        "--no-launch",
        help="Canceled tickets only: create the retire task but do not launch it.",
    ),
) -> None:
    """Wrap up a finished task: delete a done one, run Retro on a canceled one.

    A `done` ticket is deleted locally through `coga delete`.

    For a `canceled` ticket, retire creates a one-shot task that invokes
    the `retro/done-ticket` skill. Retro opens a PR when it extracts durable
    knowledge. That PR records `## Retro`, updates the knowledge base and
    deletes the source ticket. If there is no new durable knowledge,
    Retro deletes the ticket locally through `coga delete`.
    """
    if os.environ.get("COGA_SCRIPT_HELP") == "1":
        raise typer.Exit(2)
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
    if source.status not in {"done", "canceled"}:
        _bail(
            f"Retire only operates on done or canceled tickets — {ref.id_slug} "
            f"is {source.status!r}. Finish or cancel it first."
        )

    if source.status == "done":
        try:
            typer.echo("Retire: " + run_delete_task(cfg, ref), nl=False)
        except DeleteTaskError as exc:
            _bail(str(exc))
        return

    try:
        main_agent = agent or _default_agent(cfg)
        agent_type = cfg.agent_type(main_agent)
    except ConfigError as exc:
        _bail(str(exc))
    typer.echo(
        f"Retire: using main agent {main_agent} "
        f"(agent type {agent_type.name})"
    )

    title = f"Retire {ref.id_slug}"
    slug_override = f"retire-{slugify(ref.id_slug)}"
    try:
        typer.echo(f"Retire: creating task {title!r}")
        result = create_task(
            cfg=cfg,
            title=title,
            # Retire creates straight to `active`; every task past `draft`
            # carries a workflow, so it runs its body through the one-step
            # `direct/body` workflow rather than being a workflow-less active
            # task the validator (rightly) rejects as un-bumpable.
            workflow_name="direct/body",
            contexts=[],
            owner=cfg.current_user,
            agent=main_agent,
            status="active",
            slug_override=slug_override,
            description=_retire_body(cfg, ref.id_slug),
            created_by="retire",
        )
    except (
        ConfigError, TaskValidationError, ValueError, RepoResourceUnreadable,
    ) as exc:
        _bail(str(exc))

    slug = result["slug"]
    typer.echo(f"Retire: created task {slug} at {result['path']} (active)")
    typer.echo(f"Created {slug}")
    if no_launch:
        typer.echo("Retire: launch skipped (--no-launch)")
        typer.echo(f"Run `coga launch {slug}` to start the retire pass.")
        return

    typer.echo(f"Retire: launching {slug}")
    raise typer.Exit(_launch_retire_task(slug))


def _launch_retire_task(slug: str) -> int:
    """Launch the retire task in-process and return the command's exit code."""
    from coga.launch import LaunchBail, launch

    try:
        result = launch(slug, agent_override=None, prompt_report=False)
    except LaunchBail as exc:
        if exc.reason:
            typer.secho(exc.reason, fg=typer.colors.RED, err=True)
        return exc.code
    return result.exit_code


def _default_agent(cfg: Config) -> str:
    default = cfg.default_agent()
    if default is None:
        raise ConfigError(
            "No agent types declared in [agents]. Pass --agent or declare "
            "at least one `[agents.*]` table in coga.toml or coga.local.toml."
        )
    return default.name


def _retire_body(
    cfg: Config,
    target_slug: str,
) -> str:
    template, override = load_resource(cfg, "retire.md")
    try:
        body = template.format(slug=target_slug).strip()
    except (KeyError, IndexError, ValueError, AttributeError, TypeError) as exc:
        if override is None:
            raise
        # `retire.md` renders with `str.format`, so a stray brace in a repo
        # override must name the file rather than surface as a bare KeyError.
        raise RepoResourceUnreadable(
            f"repo resource override {override} is not a valid `retire.md` "
            f"template ({type(exc).__name__}: {exc}); only `{{slug}}` is "
            "substituted — double any literal brace as `{{` / `}}`"
        ) from exc
    return body


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)


if __name__ == "__main__":
    app(prog_name="coga retire")
