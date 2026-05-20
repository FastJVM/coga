"""`relay recurring` — manage recurring task templates."""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.recurring import RecurringError
from relay.recurring import check_recurring as do_check
from relay.recurring import scaffold_named
from relay.slack import post
from relay.tasks import TaskRef, read_ticket

app = typer.Typer(
    name="recurring",
    help="Manage recurring task templates under `relay-os/recurring/`.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("check")
def check() -> None:
    """Scan recurring templates and create any due tasks."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    result = do_check(cfg)

    for ref in result.created:
        ticket = read_ticket(ref)
        typer.echo(f"Created {ref.id_slug}")
        post(
            cfg,
            f"🔁 recurring scaffolded *{ref.id_slug}* "
            f"\"{ticket.title}\" in {cfg.project_name} — "
            f"assignee {ticket.assignee or 'unassigned'}",
            task_path=ref.path,
        )

    if result.errors:
        n = len(result.errors)
        plural = "" if n == 1 else "s"
        bullets = "\n".join(f"• {name}: {msg}" for name, msg in result.errors)
        post(
            cfg,
            f"⚠️ recurring check skipped {n} template{plural}\n{bullets}",
        )

    if not result.created and not result.errors:
        typer.echo("No recurring tasks due.")


@app.command("scaffold")
def scaffold(
    name: str = typer.Argument(
        ...,
        help="Recurring template name — the file stem under relay-os/recurring/.",
    ),
    launch: bool = typer.Option(
        False,
        "--launch",
        help="Launch the scaffolded task instead of leaving it idle.",
    ),
) -> None:
    """Scaffold a named recurring template now, ignoring its schedule.

    The task slug still uses the template's schedule-derived period key, so
    this and the cron `relay recurring check` converge on one task directory
    per period. This is the on-demand entry point behind aliases like
    `relay dream`.
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        outcome = scaffold_named(cfg, name)
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    ref = outcome.ref
    if outcome.created:
        ticket = read_ticket(ref)
        typer.echo(f"Created {ref.id_slug}")
        post(
            cfg,
            f"🔁 recurring scaffolded *{ref.id_slug}* "
            f"\"{ticket.title}\" in {cfg.project_name} — "
            f"assignee {ticket.assignee or 'unassigned'}",
            task_path=ref.path,
        )
    else:
        typer.echo(f"{ref.id_slug} already scaffolded for this period")

    if launch:
        _launch_scaffolded(ref)


def _launch_scaffolded(ref: TaskRef) -> None:
    """Launch a freshly scaffolded recurring task.

    Recurring tasks scaffold straight to `active` — they are machine-authored
    ready jobs, so there is no separate activation step. A task already past
    `active` (a finished or paused run, e.g. re-running `relay dream` mid-week)
    is left alone — re-launching it would be wrong, and saying so beats
    silently doing nothing.
    """
    ticket = read_ticket(ref)
    if ticket.status != "active":
        typer.secho(
            f"{ref.id_slug} is {ticket.status}; not launching.",
            fg=typer.colors.YELLOW,
        )
        return

    typer.echo(f"Launching {ref.id_slug}")
    from relay.commands.launch import launch as launch_cmd

    launch_cmd(ref.slug, agent_override=None, prompt_report=False, no_verify=False)
