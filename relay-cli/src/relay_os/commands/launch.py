"""relay launch — compose prompt, inject secrets, spawn agent or run script.

Stub. Implementation lands in a subsequent ticket.
"""

from __future__ import annotations

import click


@click.command()
@click.option("--task", required=True, help="Task ID or directory name.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Compose the prompt and print a summary without spawning the agent "
    "or running the script.",
)
def launch(task: str, dry_run: bool) -> None:
    """Compose prompt and start work on a task."""
    click.echo("not implemented")
