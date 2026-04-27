"""`relay recurring` — manage recurring task templates."""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.recurring import check_recurring as do_check

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

    created = do_check(cfg)
    if not created:
        typer.echo("No recurring tasks due.")
        return
    for ref in created:
        typer.echo(f"Created {ref.id_slug}")
