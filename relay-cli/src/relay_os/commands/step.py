"""relay step — advance a task to its next workflow step, or mark done.

Stub. Implementation lands in a subsequent ticket.
"""

from __future__ import annotations

import click


@click.command()
@click.option("--task", required=True, help="Task ID or directory name.")
def step(task: str) -> None:
    """Advance to the next workflow step."""
    click.echo("not implemented")
