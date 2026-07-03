"""`coga recurring` — scan recurring templates and launch what's due.

Thin command head. The bare sweep's substance (scan, get-or-create,
high-water dedup, control-branch sync, and sequential launch) lives behind the
packaged `bootstrap/recurring-scan` script target and the shared
`coga.recurring_runner` / `coga.recurring_sync` modules, per
`coga/extension-model`. `main` only parses `--interactive` / `--all`, writes a
narrow env contract, and launches that stateless script target; `launch`
delegates to `run_recurring_named`. `list_recurring` (a read view) stays here
until `cli-extension-model/move-read-views-to-tickets-as-scripts` moves it.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from coga.config import ConfigError, load_config
from coga.recurring import RecurringError, TemplateStatus, list_templates
from coga.recurring_runner import run_recurring_named
from coga.tasks import TaskRef, list_tasks, read_ticket
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
        help="Launch due agent-mode tasks as a human-stepped run, leaving REPL "
        "liveness backstops unarmed. Ticket files are not modified.",
    ),
    all_: bool = typer.Option(
        False,
        "--all",
        help="Force a real, full run of EVERY template: bypass the schedule "
        "and the already-serviced/done/paused status filter, then get-or-create "
        "and launch each template's real `recurring/<name>` task. Identical to a "
        "bare `coga recurring` (real Slack, spool drain, git sync, "
        "`last_serviced_period` advance) — just forced. A template that already "
        "ran this period is re-launched (coga launch re-activates a finished "
        "ticket).",
    ),
) -> None:
    """Scan every recurring template and launch any due tasks, sequentially.

    Bare `coga recurring` is the default action. The sweep itself is a stateless
    packaged script target (`bootstrap/recurring-scan`): this head loads config,
    parses the runtime flags, writes them into a narrow env contract
    (`COGA_RECURRING_FORCE` / `COGA_RECURRING_INTERACTIVE`), and launches that
    target — which scans `coga/recurring/`, get-or-creates each due period's
    task, and launches every one still `active` or orphaned `in_progress`,
    most-overdue first, one at a time.

    `--all` forces a real, full run: it ignores the schedule and the status
    filter, so every template is launched — including ones already serviced this
    period (re-launched) and `done`/`paused` ones (`coga launch` re-activates
    them). `coga recurring launch <name>` force-runs one named template now.
    """
    if ctx.invoked_subcommand is not None:
        return

    try:
        load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    # The runtime flags reach the stateless scan script only through this narrow,
    # per-invocation env contract — never a generic launch-time parameter channel
    # (recurring state stays a pure function of files on disk).
    os.environ["COGA_RECURRING_FORCE"] = "1" if all_ else "0"
    os.environ["COGA_RECURRING_INTERACTIVE"] = "1" if interactive else "0"

    from coga.commands.launch import launch as launch_cmd

    # The scan script is itself a `mode: script` launch, so idle/max-session
    # backstops (which guard interactive agent REPLs) do not apply to it; the
    # child due-task launches it spawns compute their own from config/env.
    launch_cmd(
        "bootstrap/recurring-scan",
        agent_override=None,
        prompt_report=False,
        idle_timeout=None,
        max_session=None,
        return_timeout=False,
    )


@app.command("launch")
def launch(
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
) -> None:
    """Create a named recurring template now and launch it.

    Ignores the template's schedule — the on-demand entry point behind
    aliases like `coga dream`. The task slug is the stable qualified
    `recurring/<name>`, so this and a bare `coga recurring` converge on one
    instantiated task directory.
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        code = run_recurring_named(cfg, name, interactive=interactive)
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    if code:
        raise SystemExit(code)


@app.command("list")
def list_recurring() -> None:
    """List recurring templates with their schedules, plus instantiated tasks.

    Read-only — the inspectable counterpart of a bare `coga recurring`, which
    get-or-creates each due period's task and launches it. This creates
    nothing and launches nothing (principle 6: a view never mutates). Two
    tables: every template with its schedule and the current period's state,
    then the picked tasks — the recurring period tasks already on disk.
    """
    try:
        cfg = load_config()
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
        if s.instance is not None:
            period = f"{s.instance_status} · {s.instance.id_slug}"
        elif s.due:
            period = "[green]due — not created[/green]"
        else:
            period = "none"
        table.add_row(
            s.name,
            s.schedule or "-",
            _firing_stamp(s.last_fire),
            _firing_stamp(s.next_fire),
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
    for col in ("slug", "status", "step", "mode"):
        table.add_column(col, no_wrap=True)
    for ref in picked:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            table.add_row(ref.id_slug, "(unreadable)", "-", "-")
            continue
        table.add_row(
            ref.id_slug,
            ticket.status or "-",
            ticket.step or "-",
            ticket.mode or "-",
        )
    console.print(table)


def _firing_stamp(when: datetime | None) -> str:
    """Compact firing label for the templates table (`Mon 06-15 09:00`)."""
    if when is None:
        return "-"
    return when.strftime("%a %m-%d %H:%M")
