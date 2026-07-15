"""`coga recurring` — command heads for recurring scan, launch, and list."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

import typer
from rich.console import Console
from rich.table import Table

from coga.config import ConfigError, load_config
from coga.recurring import TemplateStatus, firing_stamp, list_templates
from coga.recurring_runner import run_recurring_named
from coga.tasks import TaskRef, list_tasks, read_ticket
from coga.ticket import TicketError


_SCAN_TARGET = "bootstrap/recurring-scan"
_FORCE_ENV = "COGA_RECURRING_FORCE"
_INTERACTIVE_ENV = "COGA_RECURRING_INTERACTIVE"


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
    """Launch the stateless bootstrap recurring scan target.

    The command head owns only Typer parameter parsing and the explicit script
    env contract. The scan/get-or-create/sync/launch body lives in
    `coga.recurring_runner`, reached through `bootstrap/recurring-scan`.
    """
    if ctx.invoked_subcommand is not None:
        return

    try:
        load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    from coga.commands.launch import launch as launch_cmd

    with _scan_env(force=all_, interactive=interactive):
        launch_cmd(
            _SCAN_TARGET,
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
    """Create a named recurring template now and launch it."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    code = run_recurring_named(cfg, name, interactive=interactive)
    if code:
        sys.exit(code)


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


@contextmanager
def _scan_env(*, force: bool, interactive: bool) -> Iterator[None]:
    updates = {
        _FORCE_ENV: _bool_env(force),
        _INTERACTIVE_ENV: _bool_env(interactive),
    }
    previous = {name: os.environ.get(name) for name in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _bool_env(value: bool) -> str:
    return "1" if value else "0"


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
