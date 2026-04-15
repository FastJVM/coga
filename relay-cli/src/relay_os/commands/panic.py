"""relay panic — agent is stuck, escalate to the task owner.

Stub. Implementation lands in a subsequent ticket.
"""

from __future__ import annotations

import click


@click.command()
@click.option("--task", required=True, help="Task ID or directory name.")
@click.option(
    "--reason",
    required=True,
    help="Short, concrete reason the agent is stuck.",
)
def panic(task: str, reason: str) -> None:
    """Record a blocker and notify the task owner."""
    click.echo("not implemented")
