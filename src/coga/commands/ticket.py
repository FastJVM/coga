"""`coga ticket [target]` — run guided ticket authoring."""

from __future__ import annotations

import os
import shutil
import sys

import typer

from coga.authoring import (
    AuthoringError,
    finalize_authored,
    snapshot_authoring_state,
)
from coga.commands.create import create_draft
from coga.commands.launch import (
    _interactive_stdio_has_tty,
    spawn_agent_session,
)
from coga.compose import ComposeError
from coga.config import Config, ConfigError, load_config
from coga.dependencies import agent_cli_missing_message
from coga.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    list_tasks,
    read_ticket,
    resolve_bootstrap,
    resolve_task,
)
from coga.ticket import Ticket
from coga.validate import TaskValidationError


AUTHORING_SKILL = "bootstrap/ticket"
# Guided editing is allowed from any lifecycle status — the human owns the
# ticket and may revise it at any stage. `in_progress` and terminal tickets are
# unusual enough to warrant a heads-up (see CAUTION_STATUSES) but are not refused.
EDITABLE_STATUSES = {
    "draft",
    "active",
    "in_progress",
    "paused",
    "done",
    "canceled",
}
CAUTION_STATUSES = {"in_progress", "done", "canceled"}

# Kickoff tokens — the authoring session's first user turn, which the
# `bootstrap/ticket` skill reads to greet the human as the right launch shape.
# `coga ticket` already knows create-vs-edit definitively (it just resolved or
# created the target), so it tells the skill via this token rather than letting
# the skill guess from body-emptiness — which misfires on `coga create`d empty
# drafts. Bare `Begin` is the no-target empty interview (the skill also detects
# that structurally from the `bootstrap/ticket` header).
AUTHORING_KICKOFF = "Begin"
AUTHORING_KICKOFF_NEW = "Begin (new ticket)"
AUTHORING_KICKOFF_EDIT = "Begin (editing existing ticket)"


def ticket(
    target: str | None = typer.Argument(
        None,
        help=(
            "Existing task slug to edit (any status), or a new title to draft "
            "— prefix the title with a sub-directory path (e.g. "
            "'v2/Build the flow') to draft it there. Omit to start an empty "
            "interview."
        ),
    ),
    agent_override: str | None = typer.Option(
        None,
        "--agent",
        help="Agent nickname to use for the authoring interview.",
    ),
) -> None:
    """Run the bootstrap/ticket authoring skill."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        bootstrap_ref = resolve_bootstrap(cfg, "ticket")
    except TaskNotFoundError as exc:
        _bail(str(exc))
    bootstrap_ticket = read_ticket(bootstrap_ref)

    ref: TaskRef | BootstrapRef
    source_ticket: Ticket

    if target is None:
        ref = bootstrap_ref
        source_ticket = bootstrap_ticket
        kickoff = AUTHORING_KICKOFF
    else:
        ref, source_ticket, created = _resolve_or_create_target(cfg, target)
        kickoff = AUTHORING_KICKOFF_NEW if created else AUTHORING_KICKOFF_EDIT

    launch_assignee = (
        agent_override
        or bootstrap_ticket.assignee
        or source_ticket.agent
        or source_ticket.assignee
    )
    if not launch_assignee:
        _bail("No authoring agent configured; pass --agent <nickname>.")

    _run_authoring_session(
        cfg=cfg,
        ref=ref,
        ticket=_authoring_ticket(source_ticket),
        launch_assignee=launch_assignee,
        kickoff=kickoff,
        bootstrap_title=bootstrap_ticket.title or "",
    )


def _resolve_or_create_target(
    cfg: Config, target: str
) -> tuple[TaskRef, Ticket, bool]:
    """Resolve `target` to an existing task to edit, or scaffold a new draft.

    Returns `(ref, ticket, created)` — `created` is True only when a brand-new
    draft was scaffolded here, False when an existing task was resolved. The
    boolean is the authoritative create-vs-edit signal `coga ticket` already
    knows; it flows into the authoring kickoff token so the skill greets off it
    instead of guessing from body-emptiness.
    """
    try:
        ref = resolve_task(cfg, target)
    except TaskNotFoundError as exc:
        msg = str(exc)
        if msg.startswith("Ambiguous task ref"):
            _bail(msg)
        # `resolve_task` matches a nested task only by its full `<dir>/<slug>`
        # path, so `coga ticket <bare-leaf>` for a nested ticket lands here even
        # though the ticket exists. Scan the leaf names before scaffolding a
        # duplicate top-level draft: exactly one leaf match *is* that existing
        # ticket (edit it); several are ambiguous (re-run with the qualified
        # slug); none is genuinely new. This leaves `resolve_task`'s global
        # semantics — and `coga launch` / `coga status` — untouched.
        leaf_matches = [t for t in list_tasks(cfg) if t.slug == target]
        if len(leaf_matches) == 1:
            return _resolve_existing(leaf_matches[0])
        if len(leaf_matches) > 1:
            slugs = ", ".join(t.id_slug for t in leaf_matches)
            _bail(
                f"Ambiguous task ref {target!r}: matches {slugs}. "
                "Re-run with the qualified `<dir>/<slug>` to disambiguate."
            )
        result = create_draft(title=target)
        # Re-resolve through discovery so the TaskRef carries the correct shape
        # (file-form vs directory-form) — create may land a bare `<slug>.md`.
        ref = resolve_task(cfg, str(result["slug"]))
        typer.echo(f"{ref.id_slug}: launching guided ticket authoring")
        return ref, read_ticket(ref), True

    return _resolve_existing(ref)


def _resolve_existing(ref: TaskRef) -> tuple[TaskRef, Ticket, bool]:
    """Read an existing task for editing, gating on its status.

    Shared by the normal `resolve_task` hit and the nested bare-leaf scan, so
    both edit paths apply the same status guard and caution heads-up. `created`
    is always False — an existing ticket is never a fresh draft.
    """
    ticket = read_ticket(ref)
    if ticket.status not in EDITABLE_STATUSES:
        _bail(
            f"Task {ref.id_slug} has unknown status {ticket.status!r}; "
            "refusing guided ticket editing."
        )
    if ticket.status in CAUTION_STATUSES:
        lifecycle_note = {
            "in_progress": "already in flight",
            "done": "already finished",
            "canceled": "already canceled",
        }[ticket.status]
        typer.secho(
            f"Note: {ref.id_slug} is {ticket.status!r}. Editing leaves its "
            f"status unchanged; this revises a ticket {lifecycle_note}",
            fg=typer.colors.YELLOW,
            err=True,
        )
    return ref, ticket, False


def _authoring_ticket(ticket: Ticket) -> Ticket:
    fm = dict(ticket.frontmatter)
    fm["skills"] = [AUTHORING_SKILL]
    return Ticket(frontmatter=fm, body=ticket.body)


def _run_authoring_session(
    *,
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    ticket: Ticket,
    launch_assignee: str,
    kickoff: str = AUTHORING_KICKOFF,
    bootstrap_title: str,
) -> None:
    if not _interactive_stdio_has_tty():
        _bail(
            "Cannot launch guided ticket authoring: it requires "
            "a TTY (stdin and stdout must both be terminals)."
        )

    try:
        agent = cfg.agent_type(launch_assignee)
    except ConfigError as exc:
        _bail(str(exc))

    agent_path = shutil.which(agent.cli)
    if agent_path is None:
        _bail(agent_cli_missing_message(agent.cli))

    typer.echo(
        f"Ticket: authoring {ref.id_slug} with {launch_assignee} -> {agent.name}"
    )
    before_authoring = snapshot_authoring_state(cfg)

    # Ticket authoring routes through the shared single-shot spawn without the
    # launch supervisor chain. It runs no task work, so it receives no Coga
    # secret injection; secrets flow through the `coga launch` chokepoint only
    # (least privilege). The kickoff token makes `coga ticket` greet first.
    try:
        session = spawn_agent_session(
            cfg,
            ref,
            ticket,
            agent,
            env=os.environ.copy(),
            actor=f"human:{cfg.current_user}",
            log_message=(
                "ticket authoring launched "
                f"(assignee={launch_assignee}, agent={agent.name})"
            ),
            discussion=True,
            kickoff=kickoff,
            label="Ticket",
            secrets_are_scoped=False,
            stateless_identity=(AUTHORING_SKILL, bootstrap_title),
        )
    except ComposeError as exc:
        _bail(str(exc))
    except FileNotFoundError:
        _bail(f"Failed to spawn agent: {agent.cli!r} not found.")

    if session.exit_code != 0:
        typer.secho(
            f"Agent exited with code {session.exit_code}.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        sys.exit(session.exit_code)

    try:
        finalize_authored(cfg, before_snapshot=before_authoring, ref=ref)
    except (AuthoringError, TaskValidationError) as exc:
        _bail(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
