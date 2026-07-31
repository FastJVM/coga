"""`coga block` — normal workflow stop for concrete human input."""

from __future__ import annotations

import sys

import typer

from coga import git
from coga import pr_assist
from coga.blackboard import append_blocker
from coga.config import ConfigError, load_config
from coga.logfile import log_path
from coga.mark import mark_blocked
from coga.notification import preflight_post
from coga.repl_supervisor import emit_done_marker
from coga.tasks import TaskNotFoundError, read_ticket, resolve_task
from coga.validate import TaskValidationError


def block(
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
    reason: str = typer.Option(
        ...,
        "--reason",
        help="Specific answer needed before the task can continue.",
    ),
) -> None:
    """Record an unresolved blocker and set the ticket to `blocked`."""
    reason = reason.strip()
    if not reason:
        _bail("--reason cannot be empty")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)
    if ticket.status not in {"active", "in_progress", "blocked"}:
        _bail(
            f"Task {ref.id_slug} is {ticket.status!r}; block requires "
            "'active', 'in_progress', or 'blocked'."
        )

    try:
        assist = pr_assist.assist_publication_from_env(cfg, ref)
    except git.FeaturePublicationError as exc:
        _bail(
            "Could not verify the recorded assist branch before blocking "
            f"{ref.id_slug}: {exc}",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    assist_publication = assist.lease if assist is not None else None
    assist_guard = assist.guard if assist is not None else None
    if assist is not None:
        try:
            preflight_post(cfg)
        except typer.Exit:
            _bail(
                "Could not block from the recorded assist branch: "
                "notification configuration must be valid before strict "
                "state publication.",
                exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
            )
    rollback = None
    if assist is not None:
        rollback = git.FileMutationRollback.capture(
            (ref.ticket_path, log_path(cfg)),
            union_paths=(log_path(cfg),),
        )
    effective_assignee = assist.agent if assist is not None else ticket.assignee
    actor = (
        f"agent:{effective_assignee}"
        if effective_assignee
        else f"human:{cfg.current_user}"
    )
    owner = ticket.owner or cfg.current_user
    blocker = effective_assignee or cfg.current_user
    publication_succeeded = False

    def record_publication() -> None:
        nonlocal publication_succeeded
        publication_succeeded = True

    try:
        append_blocker(
            ref.ticket_path,
            actor,
            reason,
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
        mark_blocked(
            cfg,
            ref,
            ticket,
            actor=actor,
            log_message=f"blocked: {reason}",
            slack_text=(
                f"🛑 {blocker} blocked *{ref.id_slug}* "
                f"\"{ticket.title}\": {reason}"
            ),
            image_url=cfg.gif_for("block") or cfg.gif_for("panic"),
            echo=f"{ref.id_slug}: blocked (owner {owner} needs to answer)",
            feature_publication=assist_publication,
            feature_publication_guard=assist_guard,
            mutation_snapshot=rollback,
            after_sync=record_publication if rollback is not None else None,
        )
    except git.FeaturePublicationError as exc:
        rollback_note = ""
        if (
            publication_succeeded
            or isinstance(exc, git.UncertainFeaturePublicationError)
        ):
            rollback_note = (
                "; generated state was retained because publication succeeded "
                "or could not be determined"
            )
        elif rollback is not None:
            rollback_note = _rollback_note(rollback)
        _bail(
            f"Could not publish {ref.id_slug}'s blocked state to the recorded "
            f"assist branch: {exc}{rollback_note}",
            exit_code=(
                git.RETRY_WITHOUT_SWEEP_EXIT_CODE
                if rollback is not None
                else 2
            ),
        )
    except TaskValidationError as exc:
        rollback_note = ""
        if rollback is not None:
            rollback_note = _rollback_note(rollback)
        _bail(
            f"{exc}{rollback_note}",
            exit_code=(
                git.RETRY_WITHOUT_SWEEP_EXIT_CODE
                if rollback is not None
                else 2
            ),
        )
    except BaseException as exc:
        if rollback is None:
            raise
        if publication_succeeded:
            rollback_note = (
                "; generated state was retained because feature and control "
                "publication already succeeded"
            )
        else:
            rollback_note = _rollback_note(rollback)
        detail = str(exc).strip() or type(exc).__name__
        _bail(
            f"Could not complete {ref.id_slug}'s strict blocked transition "
            f"after {type(exc).__name__}: {detail}{rollback_note}",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )

    # `id_slug` (not the resolved path) scopes the signal so it matches the
    # supervisor regardless of which checkout the command runs in. See
    # `bump.py` for the path-drift rationale.
    emit_done_marker(session_id=ref.id_slug)


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
