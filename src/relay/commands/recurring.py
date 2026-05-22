"""`relay recurring` — scan recurring templates and launch what's due."""

from __future__ import annotations

import sys
from datetime import datetime

import typer

from relay.config import ConfigError, load_config
from relay.recurring import DueScan, RecurringError, scaffold_named, scan_due
from relay.slack import post
from relay.tasks import TaskRef, read_ticket

app = typer.Typer(
    name="recurring",
    help="Scan recurring task templates and launch any that are due.",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Launch every due task in interactive mode for this run, even "
        "ones whose ticket says `mode: auto`. For debugging; ticket files "
        "are not modified.",
    ),
) -> None:
    """Scan every recurring template and launch any due tasks, sequentially.

    Bare `relay recurring` is the default action. For each template under
    `relay-os/recurring/` it get-or-creates the current period's task, then
    launches every one still `active` — most-overdue first, one at a time.
    Current period only: running this once a month for a weekly template
    produces one run, not a backlog. It does not install or manage system
    cron; nothing runs unless you invoke it.

    `relay recurring launch <name>` force-runs one named template now.
    """
    if ctx.invoked_subcommand is not None:
        return

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    scan = scan_due(cfg)
    _broadcast_scan(cfg, scan)
    _print_table(scan)

    due = scan.due
    if not due:
        typer.echo("No recurring tasks due.")
        return

    mode_override = "interactive" if interactive else None
    typer.echo(f"\nLaunching {len(due)} due task(s) sequentially...\n")
    from relay.commands.launch import launch as launch_cmd

    for i, task in enumerate(due, 1):
        typer.secho(
            f"[{i}/{len(due)}] {task.ref.id_slug}", fg=typer.colors.CYAN, bold=True
        )
        # Sequential by design: each launch blocks until the agent session
        # exits before the next begins. A launch that bails (e.g. an
        # interactive template with no TTY) stops the run here — re-running
        # `relay recurring` is safe, since finished tasks are skipped.
        launch_cmd(
            task.ref.slug,
            agent_override=None,
            prompt_report=False,
            no_verify=False,
            mode_override=mode_override,
        )


@app.command("launch")
def launch(
    name: str = typer.Argument(
        ...,
        help="Recurring task name — the directory under relay-os/recurring/.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Launch in interactive mode even if the template says "
        "`mode: auto`. For debugging; the ticket file is not modified.",
    ),
) -> None:
    """Scaffold a named recurring template now and launch it.

    Ignores the template's schedule — the on-demand entry point behind
    aliases like `relay dream`. The task slug still uses the schedule-derived
    period key, so this and a bare `relay recurring` converge on one task
    directory per period: a second `launch` in the same period reuses the
    existing task instead of creating a duplicate.
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

    _launch_scaffolded(ref, mode_override="interactive" if interactive else None)


def _launch_scaffolded(ref: TaskRef, *, mode_override: str | None = None) -> None:
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

    launch_cmd(
        ref.slug,
        agent_override=None,
        prompt_report=False,
        no_verify=False,
        mode_override=mode_override,
    )


# --- scan reporting -----------------------------------------------------------


def _broadcast_scan(cfg, scan: DueScan) -> None:
    """Post Slack lines for newly scaffolded tasks and skipped templates."""
    for task in scan.tasks:
        if not task.created:
            continue
        ticket = read_ticket(task.ref)
        typer.echo(f"Created {task.ref.id_slug}")
        post(
            cfg,
            f"🔁 recurring scaffolded *{task.ref.id_slug}* "
            f"\"{ticket.title}\" in {cfg.project_name} — "
            f"assignee {ticket.assignee or 'unassigned'}",
            task_path=task.ref.path,
        )

    if scan.errors:
        n = len(scan.errors)
        plural = "" if n == 1 else "s"
        bullets = "\n".join(f"• {name}: {msg}" for name, msg in scan.errors)
        post(cfg, f"⚠️ recurring scan skipped {n} template{plural}\n{bullets}")


def _print_table(scan: DueScan) -> None:
    """Print a one-line-per-template scan summary."""
    if not scan.tasks and not scan.errors:
        return

    now = datetime.now()
    typer.echo(f"Recurring scan — {now:%Y-%m-%d %H:%M}\n")
    for task in scan.tasks:
        when = _firing_label(task.last_fire, now)
        if task.launchable:
            action = typer.style("→ launch", fg=typer.colors.GREEN)
        else:
            action = typer.style(
                f"skip ({task.status})", fg=typer.colors.BRIGHT_BLACK
            )
        typer.echo(f"  {task.template:<20} {when:<26} {action}")

    for name, msg in scan.errors:
        bad = typer.style(f"skip (error: {msg})", fg=typer.colors.RED)
        typer.echo(f"  {name:<20} {'':<26} {bad}")


def _firing_label(last_fire: datetime, now: datetime) -> str:
    """Human label for a scheduled firing — 'ready' or 'overdue Nd'."""
    delta = now - last_fire
    stamp = last_fire.strftime("%a %H:%M")
    if delta.total_seconds() < 86400:
        return f"ready ({stamp})"
    return f"overdue {delta.days}d ({stamp})"
