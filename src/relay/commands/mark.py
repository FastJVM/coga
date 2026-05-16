"""`relay mark <state> <slug>` — change a ticket's status.

Three subcommands: `mark active`, `mark paused`, `mark done`. Each verb is
the literal `status` value it sets, so the command shape mirrors the
frontmatter field.

`relay launch` owns the `active` → `in_progress` start transition. `relay
bump` no longer marks final-step tickets done.
"""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.mark import mark_active as _mark_active
from relay.mark import mark_done as _mark_done
from relay.mark import mark_paused as _mark_paused
from relay.tasks import TaskNotFoundError, read_ticket, resolve_task
from relay.validate import TaskValidationError

app = typer.Typer(
    name="mark",
    help="Change a ticket's status (active / paused / done).",
    no_args_is_help=True,
    add_completion=False,
)


_ACTIVE_FROM = {"draft", "paused"}
_PAUSED_FROM = {"active", "in_progress"}
_DONE_FROM = {"active", "in_progress"}


@app.command("active")
def active(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
) -> None:
    """Set status to `active`. Allowed from `draft` or `paused`."""
    cfg, ref, ticket = _load(task)
    _require_message_nonempty(message)
    _check_transition(ref.id_slug, ticket.status, _ACTIVE_FROM, "active")

    suffix = f" — {message}" if message else ""
    actor = f"human:{cfg.current_user}"
    log_message = f"activated ({ticket.status} → active){suffix}"
    slack_text = (
        f"🚀 {cfg.current_user} activated *{ref.id_slug}* "
        f"\"{ticket.title}\" — assignee {ticket.assignee or 'unassigned'}{suffix}"
    )

    try:
        _mark_active(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
            slack_text=slack_text,
            echo=f"{ref.id_slug}: active",
        )
    except TaskValidationError as exc:
        _bail(str(exc))


@app.command("paused")
def paused(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
) -> None:
    """Set status to `paused`. Allowed from `active` or `in_progress`."""
    cfg, ref, ticket = _load(task)
    _require_message_nonempty(message)
    _check_transition(ref.id_slug, ticket.status, _PAUSED_FROM, "paused")

    suffix = f" — {message}" if message else ""
    actor = f"human:{cfg.current_user}"
    log_message = f"paused ({ticket.status} → paused){suffix}"
    slack_text = (
        f"⏸️ {cfg.current_user} paused *{ref.id_slug}* "
        f"\"{ticket.title}\"{suffix}"
    )

    try:
        _mark_paused(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
            slack_text=slack_text,
            echo=f"{ref.id_slug}: paused",
        )
    except TaskValidationError as exc:
        _bail(str(exc))


@app.command("done")
def done(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
) -> None:
    """Set status to `done`. Allowed from `active` or `in_progress`."""
    cfg, ref, ticket = _load(task)
    _require_message_nonempty(message)
    _check_transition(ref.id_slug, ticket.status, _DONE_FROM, "done")

    suffix = f" — {message}" if message else ""
    finisher = ticket.assignee or cfg.current_user
    actor = f"human:{cfg.current_user}"
    log_message = f"task done{suffix}"
    slack_text = (
        f"🎉 {finisher} finished *{ref.id_slug}* \"{ticket.title}\"{suffix}"
    )

    try:
        _mark_done(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
            slack_text=slack_text,
            image_url=cfg.gif_for("done"),
            echo=f"{ref.id_slug}: done",
        )
    except TaskValidationError as exc:
        _bail(str(exc))


# --- helpers -----------------------------------------------------------------


def _load(task: str):
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)
    return cfg, ref, ticket


def _require_message_nonempty(message: str | None) -> None:
    if message is not None and not message.strip():
        _bail("--message cannot be empty")


def _check_transition(
    id_slug: str, current: str, allowed_from: set[str], target: str
) -> None:
    if current == target:
        _bail(f"Task {id_slug} is already {target!r}.")
    if current not in allowed_from:
        allowed = " or ".join(repr(s) for s in sorted(allowed_from))
        _bail(
            f"Task {id_slug} is {current!r}; mark {target} requires {allowed}."
        )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
