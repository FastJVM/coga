"""relay create — scaffold a new task directory.

Stub. Implementation lands in a subsequent ticket.
"""

from __future__ import annotations

import click


@click.command()
@click.option("--project", help="Project name from relay.toml.")
@click.option("--title", help="Human-readable task title.")
@click.option("--owner", help="Human accountable for the task.")
@click.option("--assignee", help="Agent nickname or human name doing the work.")
@click.option(
    "--mode",
    type=click.Choice(["interactive", "auto", "script"]),
    default="interactive",
    show_default=True,
    help="How relay launch should run this task.",
)
@click.option("--workflow", help="Workflow name, e.g. code/with-review.")
@click.option(
    "--context",
    "contexts",
    multiple=True,
    metavar="REF",
    help="Context ref to attach (repeatable), e.g. email/payment-flow.",
)
@click.option(
    "--check-recurring",
    is_flag=True,
    help="Scan recurring/ templates and create any due tasks. Used by "
    "scripts/cron.sh.",
)
def create(
    project: str | None,
    title: str | None,
    owner: str | None,
    assignee: str | None,
    mode: str,
    workflow: str | None,
    contexts: tuple[str, ...],
    check_recurring: bool,
) -> None:
    """Create a new task."""
    click.echo("not implemented")
