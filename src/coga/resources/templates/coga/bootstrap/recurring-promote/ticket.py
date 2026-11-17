"""Command entry point for the recurring promotion ticket."""

from __future__ import annotations

import sys

import typer

from coga import git
from coga.config import ConfigError, load_config
from coga.paths import log_path
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

    source_path = ref.path
    try:
        outcome = promote_task(cfg, ref, schedule=schedule, name=name)
    except RetainedPromotionError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE) from exc
    except (RecurringError, TaskFileError, TicketError, OSError, UnicodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    # One sync for the whole move: the task removal and the new template land
    # together, so no checkout ever sees the ticket in both places (or in
    # neither).
    try:
        required = [*outcome.source_files, log_path(cfg)]
        required.extend(outcome.path / path for path in outcome.attachments)
        required.append(outcome.path / "ticket.md")
        if cfg.git_enabled:
            for path in required:
                if git.symlink_component(path) is not None:
                    raise git.GitError(f"Cannot publish symlink path {path}")
        published = git.publish(
            cfg,
            [source_path, outcome.path, log_path(cfg)],
            f"Recurring: promoted {outcome.source_slug} → recurring/{outcome.name}",
            require_paths=required,
        )
        if cfg.git_enabled and published is None:
            raise git.GitError("Control branch publication was skipped")
    except git.GitError as exc:
        typer.secho(
            f"Promotion publication failed: {exc}. Local move retained from "
            f"{source_path} to {outcome.path}. Reconcile these paths and the "
            "audit log with control before retrying publication.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE) from exc

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
