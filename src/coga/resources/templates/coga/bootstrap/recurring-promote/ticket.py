"""Command entry point for the recurring promotion ticket."""

from __future__ import annotations

import sys

import typer

from coga.config import ConfigError, load_config
from coga.recurring import RecurringError
from coga.taskfile import TaskFileError
from coga.tasks import TaskNotFoundError, resolve_task
from coga.ticket import TicketError

from promotion import RetainedPromotionError, promote_task


app = typer.Typer(add_completion=False)


@app.command()
def promote(
    task: str = typer.Argument(..., help="Task ID or id-slug to promote."),
    schedule: str = typer.Option(
        ...,
        "--schedule",
        help='5-field cron string the template fires on, e.g. "0 9 * * 1".',
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Recurring template directory name. Defaults to the task's slug.",
    ),
) -> None:
    """Move a task into `coga/recurring/<name>/` as a recurring template.

    The authoring path for "this ticket should run every period": the ticket
    body travels verbatim, task-only frontmatter is dropped, the validated
    `--schedule` is stamped on, and the blackboard is reset for cross-run
    state. Refuses rather than overwriting an existing template, and validates
    the cron before anything moves.
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        outcome = promote_task(cfg, ref, schedule=schedule, name=name)
    except RetainedPromotionError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except (RecurringError, TaskFileError, TicketError, OSError, UnicodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    typer.echo(
        f"Promoted {outcome.source_slug} → recurring/{outcome.name} "
        f"({outcome.path}) on schedule {schedule!r}."
    )
    if outcome.dropped_skills:
        typer.secho(
            "Dropped ticket-level skills "
            f"{', '.join(outcome.dropped_skills)}: `skills:` is never copied "
            "into a period task. Put them on the template workflow's steps.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    if outcome.dropped_blackboard:
        typer.secho(
            "Dropped the task's blackboard: a template blackboard holds "
            "cross-run state, not one run's scratch. Recover it with `git show` "
            "if you need it.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    typer.echo("Run `coga validate --json` to check the new template.")


if __name__ == "__main__":
    app(prog_name="coga promote-recurring")
