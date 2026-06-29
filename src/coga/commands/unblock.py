"""`coga unblock` — record the human answer and reactivate blocked work."""

from __future__ import annotations

import sys

import typer

from coga.blackboard import open_blockers, resolve_open_blockers
from coga.config import ConfigError, load_config
from coga.mark import RequiredExtensionMissing, WorkflowMissing, mark_active
from coga.tasks import TaskNotFoundError, read_ticket, resolve_task
from coga.validate import TaskValidationError
from coga.workflow import WorkflowError


def unblock(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    answer: str | None = typer.Option(
        None,
        "--answer",
        help="Answer or resolution to record for all open blockers.",
    ),
) -> None:
    """Resolve open blockers and move `blocked -> active`."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)
    if ticket.status != "blocked":
        _bail(f"Task {ref.id_slug} is {ticket.status!r}; unblock requires 'blocked'.")

    blockers = open_blockers(ref.ticket_path)
    if not blockers:
        _bail(f"Task {ref.id_slug} is blocked but has no open blockers.")

    if answer is None:
        typer.echo(f"Open blocker(s) for {ref.id_slug}:")
        for blocker in blockers:
            typer.echo(f"- {blocker.reason}")
        answer = typer.prompt("Answer/resolution").strip()
    else:
        answer = answer.strip()
    if not answer:
        _bail("--answer cannot be empty")

    actor = f"human:{cfg.current_user}"
    resolved = resolve_open_blockers(ref.ticket_path, actor, answer)
    if not resolved:
        _bail(f"Task {ref.id_slug} has no open blockers to resolve.")
    ticket = read_ticket(ref)

    try:
        mark_active(
            cfg,
            ref,
            ticket,
            actor=actor,
            log_message=f"unblocked ({ticket.status} → active): {answer}",
            echo=f"{ref.id_slug}: active (unblocked)",
        )
    except WorkflowMissing:
        _bail(
            f"Cannot unblock {ref.id_slug}: ticket has no workflow. Set "
            "`workflow: <name>` in `ticket.md`, then retry."
        )
    except WorkflowError as exc:
        _bail(
            f"Cannot unblock {ref.id_slug}: its `workflow:` ref could not "
            f"be frozen — {exc}"
        )
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        _bail(
            f"Cannot unblock {ref.id_slug}: required extension field(s) "
            f"empty: {names}. Fill them in `ticket.md` then retry."
        )
    except TaskValidationError as exc:
        _bail(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
