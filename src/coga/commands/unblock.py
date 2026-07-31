"""`coga unblock` — record the human answer and reactivate blocked work."""

from __future__ import annotations

import sys

import typer

from coga import git
from coga import pr_assist
from coga.blackboard import open_blockers, resolve_open_blockers
from coga.config import Config, ConfigError, load_config
from coga.logfile import append_log
from coga.mark import RequiredExtensionMissing, WorkflowMissing, mark_active
from coga.paths import log_path
from coga.tasks import TaskNotFoundError, TaskRef, list_tasks, read_ticket, resolve_task
from coga.ticket import TicketError
from coga.validate import TaskValidationError
from coga.workflow import WorkflowError


class _UnblockError(Exception):
    """A single ticket could not be unblocked (reported, loop continues)."""

    def __init__(self, message: str, *, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


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
    """Resolve open blockers; move `blocked -> active` (in_progress stays put)."""
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

    # `blocked` is the normal case (resolve the asks + reactivate). An
    # `in_progress` ticket with open asks is the interactive-launch-of-blocked
    # session recording its resolution mid-step: launch already reactivated the
    # ticket, so unblock resolves the asks only and leaves status and step
    # untouched.
    ticket = read_ticket(ref)
    if ticket.status not in {"blocked", "in_progress"}:
        _bail(
            f"Task {ref.id_slug} is {ticket.status!r}; unblock requires "
            "'blocked' (or 'in_progress' with open asks)."
        )

    blockers = open_blockers(ref.ticket_path)
    if not blockers:
        _bail(f"Task {ref.id_slug} is {ticket.status} but has no open blockers.")

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
        _bail(str(exc), exit_code=exc.exit_code)


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
            if exc.exit_code == git.RETRY_WITHOUT_SWEEP_EXIT_CODE:
                _bail(str(exc), exit_code=exc.exit_code)
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            skipped += 1

    typer.echo("")
    typer.echo(f"Unblocked {unblocked}, skipped {skipped}.")


def _apply_unblock(cfg: Config, ref: TaskRef, answer: str) -> None:
    """Resolve open blockers on one ticket; reactivate it unless mid-step.

    A `blocked` ticket is marked active. An `in_progress` ticket (interactive
    launch already reactivated it) gets its asks resolved with status and
    `step:` untouched. Raises `_UnblockError` (never exits) so `--all` can
    report and continue.
    """
    actor = f"human:{cfg.current_user}"
    try:
        assist = pr_assist.assist_publication_from_env(cfg, ref)
    except git.FeaturePublicationError as exc:
        raise _UnblockError(
            str(exc),
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        ) from exc
    assist_publication = assist.lease if assist is not None else None
    assist_guard = assist.guard if assist is not None else None
    rollback = None
    if assist is not None:
        rollback = git.FileMutationRollback.capture(
            (ref.ticket_path, log_path(cfg)),
            union_paths=(log_path(cfg),),
        )
    publication_succeeded = False

    def record_publication() -> None:
        nonlocal publication_succeeded
        publication_succeeded = True

    try:
        resolve_open_blockers(
            ref.ticket_path,
            actor,
            answer,
            expected_bytes=(
                rollback.originals[ref.ticket_path]
                if rollback is not None
                else None
            ),
            after_write=(
                (lambda written: rollback.arm({ref.ticket_path: written}))
                if rollback is not None
                else None
            ),
        )
        ticket = read_ticket(ref)

        if ticket.status == "in_progress":
            # Launch already reactivated the ticket (blocked → active →
            # in_progress); the session is recording its resolution mid-step.
            # Resolve-only: no status flip, `step:` untouched.
            audit_append = append_log(
                cfg,
                ref.id_slug,
                actor,
                f"unblocked (asks resolved, still in_progress): {answer}",
            )
            if rollback is not None:
                rollback.arm_append(log_path(cfg), audit_append)
            git.sync_task_state(
                cfg,
                ref.path,
                message=f"Ticket: {ref.id_slug} — asks resolved",
                guard=git.ticket_state_guard(cfg, ref.ticket_path),
                feature_publication=assist_publication,
                feature_publication_guard=assist_guard,
                after_strict_publication=(
                    record_publication if rollback is not None else None
                ),
                generated_paths=(
                    rollback.generated if rollback is not None else None
                ),
            )
            typer.echo(f"{ref.id_slug}: open asks resolved (still in_progress)")
            return

        if assist_publication is None:
            mark_active(
                cfg,
                ref,
                ticket,
                actor=actor,
                log_message=f"unblocked ({ticket.status} → active): {answer}",
                echo=f"{ref.id_slug}: active (unblocked)",
            )
        else:
            assert rollback is not None
            mark_active(
                cfg,
                ref,
                ticket,
                actor=actor,
                log_message=f"unblocked ({ticket.status} → active): {answer}",
                sync_state=False,
                mutation_snapshot=rollback,
            )
            git.sync_task_state(
                cfg,
                ref.path,
                message=f"Ticket: {ref.id_slug} — active",
                guard=git.ticket_state_guard(cfg, ref.ticket_path),
                feature_publication=assist_publication,
                feature_publication_guard=assist_guard,
                after_strict_publication=record_publication,
                generated_paths=rollback.generated,
            )
            typer.echo(f"{ref.id_slug}: active (unblocked)")
    except git.FeaturePublicationError as exc:
        if rollback is not None:
            _raise_strict_unblock_error(
                "Could not publish the blocker resolution to the recorded "
                f"assist branch: {exc}",
                exc,
                rollback,
                publication_succeeded=publication_succeeded,
            )
        raise _UnblockError(
            f"Could not publish {ref.id_slug}'s unblock state: {exc}",
        ) from exc
    except WorkflowMissing:
        _raise_unblock_error(
            f"Cannot unblock {ref.id_slug}: ticket has no workflow. Set "
            "`workflow: <name>` in `ticket.md`, then retry.",
            rollback,
        )
    except WorkflowError as exc:
        _raise_unblock_error(
            f"Cannot unblock {ref.id_slug}: its `workflow:` ref could not "
            f"be frozen — {exc}",
            rollback,
        )
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        _raise_unblock_error(
            f"Cannot unblock {ref.id_slug}: required extension field(s) "
            f"empty: {names}. Fill them in `ticket.md` then retry.",
            rollback,
        )
    except TaskValidationError as exc:
        _raise_unblock_error(str(exc), rollback)
    except BaseException as exc:
        if rollback is None:
            raise
        detail = str(exc).strip() or type(exc).__name__
        _raise_strict_unblock_error(
            f"Could not complete {ref.id_slug}'s strict unblock transition "
            f"after {type(exc).__name__}: {detail}",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )


def _raise_unblock_error(
    message: str,
    rollback: git.FileMutationRollback | None,
) -> None:
    rollback_note = ""
    if rollback is not None:
        rollback_note = _rollback_note(rollback)
    raise _UnblockError(
        f"{message}{rollback_note}",
        exit_code=(
            git.RETRY_WITHOUT_SWEEP_EXIT_CODE
            if rollback is not None
            else 2
        ),
    )


def _raise_strict_unblock_error(
    message: str,
    cause: BaseException,
    rollback: git.FileMutationRollback,
    *,
    publication_succeeded: bool,
) -> None:
    if (
        publication_succeeded
        or isinstance(cause, git.UncertainFeaturePublicationError)
    ):
        rollback_note = (
            "; generated state was retained because publication succeeded or "
            "could not be determined"
        )
    else:
        rollback_note = _rollback_note(rollback)
    raise _UnblockError(
        f"{message}{rollback_note}",
        exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
    ) from cause


def _rollback_note(rollback: git.FileMutationRollback) -> str:
    refused = rollback.restore()
    if not refused:
        return ""
    names = ", ".join(str(path) for path in refused)
    return (
        "; concurrent edits were retained instead of being overwritten at "
        f"{names}"
    )


def _bail(msg: str, *, exit_code: int = 2) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(exit_code)
