"""relay status — one-line-per-task view across all projects.

Stub. Implementation lands in a subsequent ticket.
"""

from __future__ import annotations

import click


@click.command()
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Include done, canceled, and failed tasks.",
)
def status(show_all: bool) -> None:
    """Show tasks across all projects."""
    click.echo("not implemented")
