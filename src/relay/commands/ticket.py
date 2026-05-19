"""`relay ticket [target]` — run guided ticket authoring."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

import typer

from relay.commands.create import scaffold_draft
from relay.commands.launch import (
    _format_agent_command_for_console,
    _interactive_stdio_has_tty,
    build_agent_command,
)
from relay.compose import compose_prompt, write_prompt_file
from relay.config import Config, ConfigError, load_config
from relay.logfile import append_log
from relay.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_bootstrap,
    resolve_task,
)
from relay.ticket import Ticket
from relay.validate import format_task_issues, validate_task_dir


AUTHORING_SKILL = "bootstrap/ticket"
EDITABLE_STATUSES = {"draft", "active", "paused"}
PROTECTED_STATUSES = {"in_progress", "done"}


def ticket(
    target: str | None = typer.Argument(
        None,
        help=(
            "Existing draft/active task slug to edit, or a new title to draft. "
            "Omit to start an empty interview."
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
    else:
        ref, source_ticket = _resolve_or_create_target(cfg, target)

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
    )


def _resolve_or_create_target(cfg: Config, target: str) -> tuple[TaskRef, Ticket]:
    try:
        ref = resolve_task(cfg, target)
    except TaskNotFoundError as exc:
        msg = str(exc)
        if msg.startswith("Ambiguous task ref"):
            _bail(msg)
        result = scaffold_draft(
            title=target, mode="interactive", allow_no_workflow=True
        )
        ref = TaskRef(slug=str(result["slug"]), path=cast(Path, result["path"]))
        typer.echo(f"{ref.id_slug}: launching guided ticket authoring")
        return ref, read_ticket(ref)

    ticket = read_ticket(ref)
    if ticket.status in PROTECTED_STATUSES:
        _bail(
            f"Task {ref.id_slug} is {ticket.status!r}; guided ticket editing is "
            "for draft, active, or paused tickets."
        )
    if ticket.status not in EDITABLE_STATUSES:
        _bail(
            f"Task {ref.id_slug} has unknown status {ticket.status!r}; "
            "refusing guided ticket editing."
        )
    return ref, ticket


def _authoring_ticket(ticket: Ticket) -> Ticket:
    fm = dict(ticket.frontmatter)
    fm["mode"] = "interactive"
    fm["skills"] = [AUTHORING_SKILL]
    return Ticket(frontmatter=fm, body=ticket.body)


def _run_authoring_session(
    *,
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    ticket: Ticket,
    launch_assignee: str,
) -> None:
    if not _interactive_stdio_has_tty():
        _bail(
            "Cannot launch guided ticket authoring: mode=interactive requires "
            "a TTY (stdin and stdout must both be terminals)."
        )

    try:
        agent = cfg.agent_type_for(cfg.current_user, launch_assignee)
    except ConfigError as exc:
        _bail(str(exc))

    agent_path = shutil.which(agent.cli)
    if agent_path is None:
        _bail(f"Agent CLI {agent.cli!r} not found in PATH.")

    typer.echo(
        f"Ticket: authoring {ref.id_slug} with {launch_assignee} -> {agent.name}"
    )
    prompt = compose_prompt(cfg, ref, ticket)
    prompt_file = write_prompt_file(prompt, ref)
    cmd = build_agent_command(agent, "interactive", prompt)
    typer.echo(
        "Ticket: command: "
        f"{_format_agent_command_for_console(cmd, prompt)}"
    )
    append_log(
        ref.path,
        f"human:{cfg.current_user}",
        f"ticket authoring launched (assignee={launch_assignee}, agent={agent.name})",
    )

    env = os.environ.copy()
    env.update(cfg.secrets)
    try:
        result = subprocess.run(cmd, env=env, check=False)
    except FileNotFoundError:
        _bail(f"Failed to spawn agent: {agent.cli!r} not found.")
    finally:
        try:
            prompt_file.unlink()
        except FileNotFoundError:
            pass

    if result.returncode != 0:
        typer.secho(
            f"Agent exited with code {result.returncode}.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        sys.exit(result.returncode)

    # Post-authoring validation: the agent edited the ticket directly during
    # the session. Surface schema breakage now, while the user is at the
    # terminal and can fix it before launch / Dream picks it up later.
    if isinstance(ref, TaskRef):
        issues = validate_task_dir(cfg, ref)
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            typer.secho(
                "Ticket validation failed after authoring:\n"
                + format_task_issues(errors),
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
