"""Recurring catalog presentation, owned by bootstrap/recurring-list."""

from __future__ import annotations

import sys
from datetime import datetime
import typer
from rich.console import Console
from rich.table import Table
from coga.config import ConfigError, load_config
from coga.recurring import TemplateStatus, firing_stamp, list_templates
from coga.tasks import TaskRef, list_tasks, read_ticket
from coga.ticket import TicketError

app = typer.Typer(add_completion=False)


@app.command()
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

    statuses = list_templates(cfg, include_available=True)
    picked = [ref for ref in list_tasks(cfg) if ref.directory == "recurring"]

    configured = [
        s for s in statuses
        if s.error or not (s.selection == "unselected" and s.origin == "package")
    ]
    if not configured and not picked:
        typer.echo("(no recurring templates)")
        _print_templates_table(Console(), statuses, datetime.now())
        return

    console = Console()
    now = datetime.now()
    _print_templates_table(console, statuses, now)
    _print_picked_table(console, picked)


def _print_templates_table(
    console: Console, statuses: list[TemplateStatus], now: datetime
) -> None:
    # Bundled jobs a repo never selected are available, not configured:
    # summarize them in one line instead of one row each.
    available = sorted(
        s.name for s in statuses
        if not s.error and s.selection == "unselected" and s.origin == "package"
    )
    statuses = [
        s for s in statuses
        if s.error or not (s.selection == "unselected" and s.origin == "package")
    ]
    if available:
        console.print(
            "[dim]Bundled recurring jobs available but not selected: "
            + ", ".join(available)
            + " — enable one with `<name> = true` under \\[jobs] in "
            "coga/recurring/jobs.toml[/dim]"
        )
    if not statuses:
        return
    table = Table(title="Recurring templates", title_justify="left", show_edge=False)
    for col, width in (("template", 24), ("schedule", 22), ("last fire", 17),
                       ("next fire", 17), ("current period", 36)):
        table.add_column(col, max_width=width, overflow="fold")
    for s in sorted(statuses, key=lambda x: x.name):
        if s.error:
            table.add_row(s.name, "[red]error[/red]", "-", "-", "-")
            continue
        if s.selection != "enabled":
            table.add_row(
                s.name, f"[dim]{s.selection} ({s.origin or 'no definition'})[/dim]",
                "-", "-", "-",
            )
            continue
        name = s.name if s.origin != "package" else f"{s.name} [dim](bundled)[/dim]"
        if s.scope == "clone":
            # Serviced per clone; this row describes only this clone's ledger.
            if s.serviced and s.clone_ledger is not None:
                period = f"[dim]clone · ran here {s.clone_ledger.serviced_at}[/dim]"
            else:
                period = "[green]clone · due in this clone[/green]"
        elif s.instance is not None and s.stale_done:
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
            name,
            s.schedule or "-",
            firing_stamp(s.last_fire),
            firing_stamp(s.next_fire),
            period,
        )
    console.print(table)
    for s in sorted(statuses, key=lambda x: x.name):
        if s.error:
            console.print(f"{s.name}: error: {s.error}", style="red", markup=False, highlight=False)
        elif s.selection != "enabled" and s.reason:
            # Long paths/remedies must not consume the table width and hide
            # names or firing times. Print the complete reason below it.
            console.print(f"{s.name}: {s.reason}", style="dim", markup=False, highlight=False)


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


if __name__ == "__main__":
    app(prog_name="coga recurring list")
