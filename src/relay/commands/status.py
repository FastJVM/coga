"""`relay status` — one line per task in the repo."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from relay.config import Config, ConfigError, load_config
from relay.slack import FAILURES_LOG
from relay.tasks import list_tasks, read_ticket
from relay.ticket import TicketError


def status(
    all: bool = typer.Option(False, "--all", help="Include done tasks."),
) -> None:
    """Show tasks in the repo."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    refs = list_tasks(cfg)
    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    # Slugs can be long; don't let rich wrap them mid-string in narrow terminals.
    table.add_column("slug", no_wrap=True, overflow="fold")
    for col in ("title", "status", "assignee", "step", "mode"):
        table.add_column(col)

    hidden = {"done"}
    rows = 0
    for ref in refs:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if not all and ticket.status in hidden:
            continue
        step = ticket.step or "-"
        assignee = ticket.assignee or "-"
        table.add_row(
            ref.slug,
            ticket.title or "-",
            ticket.status or "-",
            assignee,
            step,
            ticket.mode,
        )
        rows += 1

    if rows == 0:
        typer.echo("(no tasks)")
    else:
        Console().print(table)

    _print_slack_failures_footer(cfg)


def _print_slack_failures_footer(cfg: Config) -> None:
    """If the slack-failures log exists and is non-empty, print a footer line."""
    log_path = cfg.repo_root / FAILURES_LOG
    try:
        with log_path.open("r", encoding="utf-8") as f:
            count = sum(1 for line in f if line.strip())
    except FileNotFoundError:
        return
    except OSError:
        return
    if count == 0:
        return
    rel = log_path.relative_to(cfg.repo_root.parent) if log_path.is_relative_to(cfg.repo_root.parent) else log_path
    typer.secho(
        f"⚠ {count} Slack post failures — see {rel}",
        fg=typer.colors.YELLOW,
    )
