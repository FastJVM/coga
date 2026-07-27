"""`coga recurring` — command heads for recurring scan, launch, and list."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from coga import git
from coga.config import ConfigError, load_config
from coga.recurring import (
    RecurringError,
    TemplateStatus,
    firing_stamp,
    list_templates,
    promote_task,
)
from coga.recurring_runner import run_recurring_all_repos, run_recurring_named
from coga.runner import run_recipe
from coga.taskfile import TaskFileError
from coga.tasks import TaskNotFoundError, TaskRef, list_tasks, read_ticket, resolve_task
from coga.ticket import TicketError


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
        help="Launch due agent tasks as a human-stepped run, leaving REPL "
        "liveness backstops unarmed. Ticket files are not modified.",
    ),
    all_root: Path | None = typer.Option(
        None,
        "--all",
        metavar="PATH",
        help="Discover every Coga repo below PATH and run each repo's due "
        "recurring sweep once, skipping `_`-prefixed trees and unconfigured "
        "repos. May be combined with --force.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force a real, full run of EVERY template: bypass the schedule "
        "and the already-serviced/done/paused status filter, then get-or-create "
        "and launch each template's real `recurring/<name>` task. Identical to a "
        "bare `coga recurring` (real Slack, spool drain, git sync, "
        "`last_serviced_period` advance) — just forced. A template that already "
        "ran this period is re-launched. A canceled period task is refused; "
        "delete it before starting a fresh run.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Agent type to use for agent-backed recurring tasks in this "
        "sweep. Recipe and script tasks remain deterministic; ticket "
        "assignees are not rewritten.",
    ),
) -> None:
    """Run the registered recurring scanner recipe."""
    ctx.ensure_object(dict)["agent_override"] = agent
    if ctx.invoked_subcommand is not None:
        if all_root is not None or force:
            typer.secho(
                "--all and --force apply to recurring sweeps, not recurring "
                "subcommands.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)
        return

    if all_root is not None:
        code = run_recurring_all_repos(
            all_root,
            force=force,
            interactive=interactive,
            agent_override=agent,
        )
        if code:
            sys.exit(code)
        return

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    recipe_argv: list[str] = []
    if force:
        recipe_argv.append("--force")
    if interactive:
        recipe_argv.append("--interactive")
    if agent:
        recipe_argv.extend(("--agent", agent))
    code = run_recipe(cfg, "recurring-scan", recipe_argv)
    if code:
        raise typer.Exit(code)


@app.command("launch")
def launch(
    ctx: typer.Context,
    name: str = typer.Argument(
        ...,
        help="Recurring task name — the directory under coga/recurring/.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Launch as a human-stepped run, leaving REPL liveness backstops "
        "unarmed. Ticket files are not modified.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Agent type to use for this agent-backed recurring launch. "
        "Recipe and script tasks remain deterministic; the ticket assignee "
        "is not rewritten.",
    ),
) -> None:
    """Create a named recurring template now and launch it."""
    inherited_agent = (ctx.obj or {}).get("agent_override")
    if (
        agent is not None
        and inherited_agent is not None
        and agent != inherited_agent
    ):
        typer.secho(
            f"Conflicting recurring agent overrides: {inherited_agent!r} and "
            f"{agent!r}.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    agent_override = agent or inherited_agent

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    code = run_recurring_named(
        cfg, name, interactive=interactive, agent_override=agent_override
    )
    if code:
        sys.exit(code)


@app.command("promote")
def promote(
    ctx: typer.Context,
    task: str = typer.Argument(..., help="Task ID or id-slug to promote."),
    schedule: str = typer.Option(
        ...,
        "--schedule",
        help='5-field cron string the template fires on, e.g. "0 9 * * 1".',
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Recurring template directory name. Defaults to the task's slug.",
    ),
) -> None:
    """Move a task into `coga/recurring/<name>/` as a recurring template.

    The authoring path for "this ticket should run every period": the ticket
    body travels verbatim, task-only frontmatter is dropped, the validated
    `--schedule` is stamped on, and the blackboard is reset for cross-run
    state. Refuses rather than overwriting an existing template, and validates
    the cron before anything moves.
    """
    if (ctx.obj or {}).get("agent_override") is not None:
        typer.secho(
            "--agent is only supported when recurring launches work.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    source_path = ref.path
    try:
        outcome = promote_task(cfg, ref, schedule=schedule, name=name)
    except (RecurringError, TaskFileError, TicketError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    # One sync for the whole move: the task removal and the new template land
    # together, so no checkout ever sees the ticket in both places (or in
    # neither). The task path is gone now, so anchor on its still-present
    # parent for git-root resolution, the way `coga delete` does.
    git.sync_paths(
        cfg,
        source_path.parent,
        [source_path, outcome.path],
        message=(
            f"Recurring: promoted {outcome.source_slug} → recurring/{outcome.name}"
        ),
    )

    typer.echo(
        f"Promoted {outcome.source_slug} → recurring/{outcome.name} "
        f"({outcome.path}) on schedule {schedule!r}."
    )
    if outcome.dropped_skills:
        typer.secho(
            "Dropped ticket-level skills "
            f"{', '.join(outcome.dropped_skills)}: `skills:` is never copied "
            "into a period task. Put them on the template workflow's steps.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    if outcome.dropped_blackboard:
        typer.secho(
            "Dropped the task's blackboard: a template blackboard holds "
            "cross-run state, not one run's scratch. Recover it with `git show` "
            "if you need it.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    if outcome.script_file:
        typer.secho(
            f"Kept `script: {outcome.script_file}`, but a companion script file "
            "is not materialized into period tasks. Move that logic into a "
            "script-backed workflow skill, or use `script: inline`.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    typer.echo("Run `coga validate --json` to check the new template.")


@app.command("list")
def list_recurring(ctx: typer.Context) -> None:
    """List recurring templates with their schedules, plus instantiated tasks.

    Read-only — the inspectable counterpart of a bare `coga recurring`, which
    get-or-creates each due period's task and launches it. This creates
    nothing and launches nothing (principle 6: a view never mutates). Two
    tables: every template with its schedule and the current period's state,
    then the picked tasks — the recurring period tasks already on disk.
    """
    if (ctx.obj or {}).get("agent_override") is not None:
        typer.secho(
            "--agent is only supported when recurring launches work.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    try:
        cfg = load_config(require_user=False)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    statuses = list_templates(cfg)
    picked = [ref for ref in list_tasks(cfg) if ref.directory == "recurring"]

    if not statuses and not picked:
        typer.echo("(no recurring templates)")
        return

    console = Console()
    now = datetime.now()
    _print_templates_table(console, statuses, now)
    _print_picked_table(console, picked)


def _print_templates_table(
    console: Console, statuses: list[TemplateStatus], now: datetime
) -> None:
    if not statuses:
        return
    table = Table(title="Recurring templates", title_justify="left", show_edge=False)
    for col in ("template", "schedule", "last fire", "next fire", "current period"):
        table.add_column(col, no_wrap=True)
    for s in sorted(statuses, key=lambda x: x.name):
        if s.error:
            table.add_row(s.name, f"[red]error: {s.error}[/red]", "-", "-", "-")
            continue
        if s.instance is not None and s.stale_done:
            period = (
                f"[yellow]stale done run — due, replaced next sweep"
                f" · {s.instance.id_slug}[/yellow]"
            )
        elif s.instance is not None:
            period = f"{s.instance_status} · {s.instance.id_slug}"
        elif s.due:
            period = "[green]due — not created[/green]"
        else:
            period = "[dim]ran this period — task reaped[/dim]"
        table.add_row(
            s.name,
            s.schedule or "-",
            firing_stamp(s.last_fire),
            firing_stamp(s.next_fire),
            period,
        )
    console.print(table)


def _print_picked_table(console: Console, picked: list[TaskRef]) -> None:
    if not picked:
        console.print("No instantiated recurring tasks.", style="dim")
        return
    table = Table(
        title="Picked tasks (instantiated)",
        title_justify="left",
        show_edge=False,
    )
    for col in ("slug", "status", "step"):
        table.add_column(col, no_wrap=True)
    for ref in picked:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            table.add_row(ref.id_slug, "(unreadable)", "-")
            continue
        table.add_row(
            ref.id_slug,
            ticket.status or "-",
            ticket.step or "-",
        )
    console.print(table)
