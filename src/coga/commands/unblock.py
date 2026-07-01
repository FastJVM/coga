"""`coga unblock` — record the human answer and reactivate blocked work."""

from __future__ import annotations

import sys

import typer

from coga.blackboard import open_blockers, resolve_open_blockers
from coga.config import Config, ConfigError, load_config
from coga.mark import RequiredExtensionMissing, WorkflowMissing, mark_active
from coga.tasks import TaskNotFoundError, TaskRef, list_tasks, read_ticket, resolve_task
from coga.ticket import TicketError
from coga.validate import TaskValidationError
from coga.workflow import WorkflowError


class _UnblockError(Exception):
    """A single ticket could not be unblocked (reported, loop continues)."""


def unblock(
    task: str | None = typer.Argument(
        None, help="Task ID or id-slug. Omit when using --all."
    ),
    answer: str | None = typer.Option(
        None,
        "--answer",
        help="Answer or resolution to record for all open blockers.",
    ),
    all_blocked: bool = typer.Option(
        False,
        "--all",
        help="Walk every blocked task, show its cause, and prompt for an "
        "answer per ticket (blank to skip).",
    ),
) -> None:
    """Resolve open blockers and move `blocked -> active`."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    if all_blocked and task is not None:
        _bail("Pass a task id or --all, not both.")
    if not all_blocked and task is None:
        _bail("Provide a task id, or --all to walk every blocked task.")
    if all_blocked and answer is not None:
        _bail(
            "--answer is per-ticket; omit it with --all and answer each task "
            "when prompted."
        )

    if all_blocked:
        _unblock_all(cfg)
        return

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

    try:
        _apply_unblock(cfg, ref, answer)
    except _UnblockError as exc:
        _bail(str(exc))


def _unblock_all(cfg: Config) -> None:
    """Interactively walk every blocked task, answering each in turn."""
    blocked: list[TaskRef] = []
    for ref in list_tasks(cfg):
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.status == "blocked":
            blocked.append(ref)

    if not blocked:
        typer.echo("No blocked tasks.")
        return

    typer.echo(f"{len(blocked)} blocked task(s). Blank answer skips a task.")
    unblocked = 0
    skipped = 0
    for ref in blocked:
        typer.echo("")
        typer.echo(f"=== {ref.id_slug} ===")
        blockers = open_blockers(ref.ticket_path)
        if blockers:
            for blocker in blockers:
                typer.echo(f"- {blocker.reason}")
        else:
            typer.echo("(blocked; no open blocker recorded)")

        answer = typer.prompt(
            "Answer/resolution", default="", show_default=False
        ).strip()
        if not answer:
            typer.echo(f"skipped {ref.id_slug}")
            skipped += 1
            continue

        try:
            _apply_unblock(cfg, ref, answer)
            unblocked += 1
        except _UnblockError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            skipped += 1

    typer.echo("")
    typer.echo(f"Unblocked {unblocked}, skipped {skipped}.")


def _apply_unblock(cfg: Config, ref: TaskRef, answer: str) -> None:
    """Resolve open blockers on one ticket and mark it active.

    Raises `_UnblockError` (never exits) so `--all` can report and continue.
    """
    actor = f"human:{cfg.current_user}"
    resolve_open_blockers(ref.ticket_path, actor, answer)
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
        raise _UnblockError(
            f"Cannot unblock {ref.id_slug}: ticket has no workflow. Set "
            "`workflow: <name>` in `ticket.md`, then retry."
        )
    except WorkflowError as exc:
        raise _UnblockError(
            f"Cannot unblock {ref.id_slug}: its `workflow:` ref could not "
            f"be frozen — {exc}"
        )
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        raise _UnblockError(
            f"Cannot unblock {ref.id_slug}: required extension field(s) "
            f"empty: {names}. Fill them in `ticket.md` then retry."
        )
    except TaskValidationError as exc:
        raise _UnblockError(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
