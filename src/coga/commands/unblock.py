"""`coga unblock` — record the human answer and reactivate blocked work."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from coga.blackboard import open_blockers, parse_blockers_text, resolve_open_blockers_text
from coga.config import Config, ConfigError, load_config
from coga.logfile import append_log
from coga.mark import RequiredExtensionMissing, WorkflowMissing, prepare_active
from coga.taskfile import TaskFileError, split_body, with_blackboard
from coga.tasks import TaskNotFoundError, TaskRef, list_tasks, read_ticket, resolve_task
from coga.ticket import Ticket, TicketError
from coga.validate import TaskValidationError, assert_task_valid
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
    """Resolve open blockers and resume work locally.

    A paused recurring period with open asks has them resolved and stays
    `paused`; the next sweep or named launch resumes it.
    """
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
    try:
        _check_unblockable(ref, ticket)
    except _UnblockError as exc:
        _bail(str(exc))

    if answer is None:
        typer.echo(f"Open blocker(s) for {ref.id_slug}:")
        for blocker in _open_asks(ticket):
            typer.echo(f"- {blocker.reason}")
        answer = typer.prompt("Answer/resolution").strip()
        ticket = None
    else:
        answer = answer.strip()
    if not answer:
        _bail("--answer cannot be empty")

    try:
        _apply_unblock(cfg, ref, answer, ticket=ticket)
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


def _paused_period(ref: TaskRef, status: str) -> bool:
    """A paused `recurring/` period — the one paused status unblock accepts."""
    return status == "paused" and ref.id_slug.startswith("recurring/")


def _open_asks(ticket: Ticket) -> list:
    region = split_body(ticket.body)[1] or ""
    return [b for b in parse_blockers_text(region) if not b.resolved]


def _check_unblockable(ref: TaskRef, ticket: Ticket) -> None:
    if ticket.status not in {"blocked", "in_progress"} and not _paused_period(
        ref, ticket.status
    ):
        raise _UnblockError(
            f"Task {ref.id_slug} is {ticket.status!r}; unblock requires "
            "'blocked' (or 'in_progress' or a paused recurring period with "
            "open asks)."
        )
    if not _open_asks(ticket):
        raise _UnblockError(
            f"Task {ref.id_slug} is {ticket.status} but has no open blockers."
        )


def _apply_unblock(
    cfg: Config, ref: TaskRef, answer: str, *, ticket: Ticket | None = None
) -> None:
    """Resolve asks and update the ticket in one local write."""
    actor = f"human:{cfg.current_user}"
    try:
        ticket = ticket if ticket is not None else read_ticket(ref)
        _check_unblockable(ref, ticket)
        prior = ticket.status
        region = split_body(ticket.body)[1] or ""
        ticket.body = with_blackboard(ticket.body, resolve_open_blockers_text(region, actor, answer))

        if prior == "blocked":
            prepare_active(cfg, ref, ticket)
            session_ticket = os.environ.get("COGA_TASK_TICKET")
            if session_ticket and Path(session_ticket).resolve() == ref.ticket_path.resolve():
                ticket.frontmatter["status"] = "in_progress"
            assert_task_valid(cfg, ref, action="unblock", ticket_override=ticket)
        ticket.write(ref.ticket_path)
        status = ticket.status
        detail = f"{prior} → {status}" if prior != status else f"asks resolved, still {status}"
        append_log(cfg, ref.id_slug, actor, f"unblocked ({detail}): {answer}")
        if prior == status:
            typer.echo(f"{ref.id_slug}: open asks resolved (still {status})")
        else:
            typer.echo(f"{ref.id_slug}: {status} (unblocked)")
    except WorkflowMissing:
        raise _UnblockError(
            f"Cannot unblock {ref.id_slug}: ticket has no workflow. Set "
            "`workflow: <name>` in `ticket.md`, then retry."
        )
    except WorkflowError as exc:
        raise _UnblockError(
            f"Cannot unblock {ref.id_slug}: its `workflow:` ref could not "
            f"be frozen — {exc}"
        ) from exc
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        raise _UnblockError(
            f"Cannot unblock {ref.id_slug}: required extension field(s) "
            f"empty: {names}. Fill them in `ticket.md` then retry."
        ) from exc
    except (TaskFileError, TaskValidationError) as exc:
        raise _UnblockError(str(exc)) from exc


def _bail(msg: str, *, exit_code: int = 2) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(exit_code)
