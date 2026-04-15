"""relay feed — post an FYI to the shared Slack channel.

Stub. Implementation lands in a subsequent ticket.
"""

from __future__ import annotations

import click


@click.command()
@click.option("--task", required=True, help="Task ID or directory name.")
@click.option("--message", required=True, help="Short FYI message.")
def feed(task: str, message: str) -> None:
    """Post an FYI message to the Slack feed."""
    click.echo("not implemented")
