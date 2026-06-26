"""`coga mark <state> <slug>` — change a ticket's status.

Three subcommands: `mark active`, `mark paused`, `mark done`. Each verb is
the literal `status` value it sets, so the command shape mirrors the
frontmatter field.

`coga launch` owns the `active` → `in_progress` start transition. `coga
bump` no longer marks final-step tickets done.
"""

from __future__ import annotations

import sys

import typer

from coga.config import ConfigError, load_config
from coga.mark import RequiredExtensionMissing, WorkflowMissing
from coga.mark import mark_active as _mark_active
from coga.mark import mark_done as _mark_done
from coga.mark import mark_paused as _mark_paused
from coga.repl_supervisor import emit_done_marker
from coga.tasks import TaskNotFoundError, read_ticket, resolve_task
from coga.validate import TaskValidationError
from coga.workflow import WorkflowError

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

    try:
        _mark_active(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
            echo=f"{ref.id_slug}: active",
        )
    except WorkflowMissing:
        _bail(
            f"Cannot activate {ref.id_slug}: ticket has no workflow. A "
            "workflow-less ticket has no steps and can't be advanced via "
            "`coga bump`. Set `workflow: <name>` in `ticket.md` (see "
            f"coga-os/workflows/) or run `coga ticket {ref.id_slug}` to "
            "fill it in, then retry."
        )
    except WorkflowError as exc:
        _bail(
            f"Cannot activate {ref.id_slug}: its `workflow:` ref could not "
            f"be frozen — {exc}"
        )
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        _bail(
            f"Cannot activate {ref.id_slug}: required extension field(s) "
            f"empty: {names}. Fill them in `ticket.md` then retry."
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

    try:
        _mark_paused(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
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
    # A workflow-less ticket has no current step, so collapse the transition.
    prev = ticket.current_step()
    transition = f": {prev['name']} → done" if prev else ""
    slack_text = (
        f"🎉 {finisher} finished *{ref.id_slug}* "
        f"\"{ticket.title}\"{transition}{suffix}"
    )

    try:
        _mark_done(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
            slack_text=slack_text,
            digest_detail=f"{finisher} finished{transition or ' → done'} ✅{suffix}",
            image_url=cfg.gif_for("done"),
            echo=f"{ref.id_slug}: done",
        )
    except TaskValidationError as exc:
        _bail(str(exc))

    # `mark done` is a session-end transition; tell a supervising
    # `coga launch` to tear down the agent's REPL. Other `mark`
    # transitions (active / paused) are not terminal and intentionally
    # skip the marker. The resolved task path scopes the signal to this
    # ticket (see `emit_done_marker`).
    emit_done_marker(session_id=str(ref.path.resolve()))


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
