"""`coga ticket [target]` — run guided ticket authoring."""

from __future__ import annotations

import os
import shutil
import sys

import typer

from coga.authoring import (
    AUTHORING_AGENT_ENV,
    AuthoringError,
    finalize_authored,
    resolve_authoring_agent,
    snapshot_authoring_state,
)
from coga.commands.create import create_draft
from coga.commands.launch import (
    _interactive_stdio_has_tty,
    missing_launch_file_message,
    spawn_agent_session,
)
from coga.compose import ComposeError
from coga.repl_supervisor import AgentCliNotFound
from coga.config import Config, ConfigError, load_config, scrub_op_auth_env
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

TTY_REQUIRED_MESSAGE = (
    "Cannot launch guided ticket authoring: it requires "
    "a TTY (stdin and stdout must both be terminals)."
)


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
    pick_agent: bool = typer.Option(
        False,
        "--pick-agent",
        help=(
            "Choose the authoring interview's agent from the configured types "
            "for this run. Nothing is saved."
        ),
    ),
) -> None:
    """Run the bootstrap/ticket authoring skill."""
    if pick_agent and agent_override:
        _bail("Pass --agent or --pick-agent, not both.")
    # Checked before any target is scaffolded, so a non-TTY `--pick-agent`
    # never leaves a fresh draft behind or blocks on a prompt.
    if pick_agent and not _interactive_stdio_has_tty():
        _bail(TTY_REQUIRED_MESSAGE)
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

    # Interviewer selection is `resolve_authoring_agent`'s precedence chain,
    # shared with megalaunch's picked-draft pass. It selects the *interviewer*
    # only — the interview never writes an agent onto the ticket it is editing;
    # the human chooses that through the authoring allowlist.
    if pick_agent:
        agent_override = _pick_authoring_agent(
            cfg, source_ticket=source_ticket, bootstrap_ticket=bootstrap_ticket
        )
    try:
        launch_agent = resolve_authoring_agent(
            cfg,
            source_ticket=source_ticket,
            bootstrap_ticket=bootstrap_ticket,
            agent_override=agent_override,
        )
    except ConfigError as exc:
        _bail(f"No authoring agent available: {exc}")
        return

    _run_authoring_session(
        cfg=cfg,
        ref=ref,
        ticket=_authoring_ticket(source_ticket),
        launch_agent=launch_agent,
        kickoff=kickoff,
        bootstrap_title=bootstrap_ticket.title or "",
    )


def _pick_authoring_agent(
    cfg: Config, *, source_ticket: Ticket, bootstrap_ticket: Ticket
) -> str:
    """Ask which configured agent type runs this authoring interview.

    Lives in the command module, not `coga.authoring`, so megalaunch's batched
    authoring pass can never reach a prompt. Always returns a configured name:
    zero agents fail loud, a single agent is selected without asking, and with
    no valid default an empty answer re-prompts instead of guessing.
    """
    names = list(cfg.agents)
    if not names:
        _bail(
            "No agent types are configured; declare at least one `[agents.*]` "
            "table in coga.toml or coga.local.toml (e.g. `[agents.claude]`)."
        )
    if len(names) == 1:
        typer.echo(f"Only one agent type is configured; using {names[0]}.")
        return names[0]
    try:
        current: str | None = resolve_authoring_agent(
            cfg, source_ticket=source_ticket, bootstrap_ticket=bootstrap_ticket
        )
    except ConfigError as exc:
        typer.secho(f"No default agent: {exc}", fg=typer.colors.YELLOW, err=True)
        current = None
    typer.echo("Authoring agent:")
    for index, name in enumerate(names, start=1):
        marker = "  (default)" if name == current else ""
        typer.echo(f"  {index}. {name}{marker}")
    while True:
        answer = typer.prompt(
            "Pick a number or name",
            default=current or "",
            show_default=bool(current),
        ).strip()
        if answer.isdigit() and 1 <= int(answer) <= len(names):
            choice = names[int(answer) - 1]
            break
        if answer in cfg.agents:
            choice = answer
            break
        typer.secho(
            f"Enter 1-{len(names)} or one of: {', '.join(names)}.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    typer.echo(
        f'To keep {choice} for authoring, set `[authoring] agent = "{choice}"` '
        f"in coga.local.toml or `export {AUTHORING_AGENT_ENV}={choice}`."
    )
    return choice


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
    """Read an existing task for guided editing.

    Shared by the normal `resolve_task` hit and the nested bare-leaf scan, so
    both edit paths behave identically. `created` is always False — an existing
    ticket is never a fresh draft.
    """
    ticket = read_ticket(ref)
    return ref, ticket, False


def _authoring_ticket(ticket: Ticket) -> Ticket:
    """Project a ticket into an authoring-only prompt without mutating it.

    The real ticket's workflow and step remain on disk for the interviewer to
    preserve. Removing ``step`` only from this ephemeral copy prevents prompt
    composition from mixing the current task-execution skill into the
    ``bootstrap/ticket`` authoring interview.
    """
    fm = dict(ticket.frontmatter)
    fm["skills"] = [AUTHORING_SKILL]
    fm.pop("step", None)
    return Ticket(frontmatter=fm, body=ticket.body)


def _run_authoring_session(
    *,
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    ticket: Ticket,
    launch_agent: str,
    kickoff: str = AUTHORING_KICKOFF,
    bootstrap_title: str,
) -> None:
    if not _interactive_stdio_has_tty():
        _bail(TTY_REQUIRED_MESSAGE)

    try:
        agent = cfg.agent_type(launch_agent)
    except ConfigError as exc:
        _bail(str(exc))

    agent_path = shutil.which(agent.cli)
    if agent_path is None:
        _bail(agent_cli_missing_message(agent.cli))

    typer.echo(
        f"Ticket: authoring {ref.id_slug} with {launch_agent} -> {agent.name}"
    )
    before_authoring = snapshot_authoring_state(cfg)

    # Ticket authoring routes through the shared single-shot spawn without the
    # launch supervisor chain. It runs no task work, so it receives no Coga
    # secret injection; secrets flow through the `coga launch` chokepoint only
    # (least privilege), and 1Password CLI auth is scrubbed so the interviewer
    # cannot `op read` either. The kickoff token makes `coga ticket` greet first.
    try:
        session = spawn_agent_session(
            cfg,
            ref,
            ticket,
            agent,
            env=scrub_op_auth_env(os.environ),
            actor=f"human:{cfg.current_user}",
            log_message=(
                "ticket authoring launched "
                f"(interviewer={launch_agent}, agent={agent.name})"
            ),
            discussion=True,
            kickoff=kickoff,
            label="Ticket",
            secrets_are_scoped=False,
            stateless_identity=(AUTHORING_SKILL, bootstrap_title),
            include_blocker_preamble=False,
        )
    except ComposeError as exc:
        _bail(str(exc))
    except AgentCliNotFound:
        _bail(f"Failed to spawn agent: {agent.cli!r} not found.")
    except FileNotFoundError as exc:
        _bail(missing_launch_file_message(exc))

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
