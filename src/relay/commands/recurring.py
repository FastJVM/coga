"""`relay recurring` — manage recurring task templates."""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.recurring import check_recurring as do_check
from relay.slack import post
from relay.tasks import read_ticket

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
