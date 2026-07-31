"""`coga block` — normal workflow stop for concrete human input."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from coga import git
from coga.blackboard import append_blocker
from coga.config import ConfigError, load_config
from coga.logfile import log_path
from coga.mark import mark_blocked
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
        assist_publication = git.assist_publication_lease_from_env(cfg, ref.path)
    except git.FeaturePublicationError as exc:
        _bail(
            "Could not verify the recorded assist branch before blocking "
            f"{ref.id_slug}: {exc}"
        )
    rollback = (
        _snapshot_files((ref.ticket_path, log_path(cfg)))
        if assist_publication is not None
        else None
    )
    actor = (
        f"agent:{ticket.assignee}"
        if ticket.assignee
        else f"human:{cfg.current_user}"
    )
    append_blocker(ref.ticket_path, actor, reason)

    owner = ticket.owner or cfg.current_user
    blocker = ticket.assignee or cfg.current_user
    ticket = read_ticket(ref)
    try:
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
        )
    except git.FeaturePublicationError as exc:
        if rollback is not None:
            _restore_files(rollback)
        _bail(
            f"Could not publish {ref.id_slug}'s blocked state to the recorded "
            f"assist branch: {exc}"
        )
    except TaskValidationError as exc:
        if rollback is not None:
            _restore_files(rollback)
        _bail(str(exc))

    # `id_slug` (not the resolved path) scopes the signal so it matches the
    # supervisor regardless of which checkout the command runs in. See
    # `bump.py` for the path-drift rationale.
    emit_done_marker(session_id=ref.id_slug)


def _snapshot_files(paths: tuple[Path, ...]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.is_file() else None for path in paths}


def _restore_files(snapshot: dict[Path, bytes | None]) -> None:
    for path, data in snapshot.items():
        if data is None:
            if path.is_file():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
