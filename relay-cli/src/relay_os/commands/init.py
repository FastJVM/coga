"""relay init — initialize a new Relay repo or project.

Stub. Implementation lands in a subsequent ticket.
"""

from __future__ import annotations

import click


@click.command()
@click.option(
    "--project",
    help="Initialize a project directory (creates relay-os/ inside). "
    "Omit to initialize the repo root.",
)
def init(project: str | None) -> None:
    """Initialize a new Relay repo or project."""
    click.echo("not implemented")
