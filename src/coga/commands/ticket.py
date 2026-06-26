"""`coga ticket [target]` — run guided ticket authoring."""

from __future__ import annotations

import os
import shutil
import sys
from hashlib import sha256
from pathlib import Path
from typing import cast

import typer

from coga import git
from coga.commands.create import create_draft
from coga.commands.launch import (
    _interactive_stdio_has_tty,
    spawn_agent_session,
)
from coga.compose import ComposeError
from coga.config import Config, ConfigError, load_config
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
from coga.validate import format_task_issues, validate_task_dir


AUTHORING_SKILL = "bootstrap/ticket"
# Guided editing is allowed from any lifecycle status — the human owns the
# ticket and may revise it at any stage. `in_progress` and `done` are unusual
# enough to warrant a heads-up (see CAUTION_STATUSES) but are not refused.
EDITABLE_STATUSES = {"draft", "active", "in_progress", "paused", "done"}
CAUTION_STATUSES = {"in_progress", "done"}
AUTHORING_SYNC_DIRS = ("tasks", "contexts", "skills")


def ticket(
    target: str | None = typer.Argument(
        None,
        help=(
            "Existing task slug to edit (any status), or a new title to draft. "
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
        result = create_draft(title=target, autonomy="interactive")
        # Re-resolve through discovery so the TaskRef carries the correct shape
        # (file-form vs directory-form) — create may land a bare `<slug>.md`.
        ref = resolve_task(cfg, str(result["slug"]))
        typer.echo(f"{ref.id_slug}: launching guided ticket authoring")
        return ref, read_ticket(ref)

    ticket = read_ticket(ref)
    if ticket.status not in EDITABLE_STATUSES:
        _bail(
            f"Task {ref.id_slug} has unknown status {ticket.status!r}; "
            "refusing guided ticket editing."
        )
    if ticket.status in CAUTION_STATUSES:
        typer.secho(
            f"Note: {ref.id_slug} is {ticket.status!r}. Editing leaves its "
            "status unchanged; this revises a ticket already in flight"
            if ticket.status == "in_progress"
            else f"Note: {ref.id_slug} is {ticket.status!r}. Editing leaves its "
            "status unchanged; this revises a finished ticket",
            fg=typer.colors.YELLOW,
            err=True,
        )
    return ref, ticket


def _authoring_ticket(ticket: Ticket) -> Ticket:
    fm = dict(ticket.frontmatter)
    fm["autonomy"] = "interactive"
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
        agent = cfg.agent_type(launch_assignee)
    except ConfigError as exc:
        _bail(str(exc))

    agent_path = shutil.which(agent.cli)
    if agent_path is None:
        _bail(f"Agent CLI {agent.cli!r} not found in PATH.")

    typer.echo(
        f"Ticket: authoring {ref.id_slug} with {launch_assignee} -> {agent.name}"
    )
    before_tasks = {task_ref.id_slug for task_ref in list_tasks(cfg)}
    before_authoring = _snapshot_authoring_files(cfg)

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
            "interactive",
            env=os.environ.copy(),
            actor=f"human:{cfg.current_user}",
            log_message=(
                "ticket authoring launched "
                f"(assignee={launch_assignee}, agent={agent.name})"
            ),
            discussion=True,
            kickoff="Begin",
            label="Ticket",
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

    # Post-authoring validation: the agent edited the ticket directly during
    # the session. Surface schema breakage now, while the user is at the
    # terminal and can fix it before launch / Dream picks it up later.
    changed_paths = _changed_authoring_paths(before_authoring, cfg)
    authored_refs = (
        [ref] if isinstance(ref, TaskRef)
        else _authored_task_refs(cfg, changed_paths, before_tasks)
    )
    for authored_ref in authored_refs:
        _validate_authored_task(cfg, authored_ref)

    sync_paths = [authored_ref.path for authored_ref in authored_refs]
    sync_paths.extend(_support_paths(cfg, changed_paths))
    if sync_paths:
        anchor = authored_refs[0].path if authored_refs else ref.path
        git.sync_paths(
            cfg,
            anchor,
            sync_paths,
            message=_authoring_sync_message(authored_refs),
        )


def _validate_authored_task(cfg: Config, ref: TaskRef) -> None:
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

    # Guided authoring of a draft must land on a workflow. A workflow-less
    # draft can't be activated (`coga mark active` refuses it), so handing
    # one back would strand the human. Catch it here, at the terminal,
    # rather than later at activation. Only drafts are gated — an already
    # `active` ticket edited here may be a workflow-less recurring/retire
    # task, which is legitimate.
    authored = read_ticket(ref)
    if authored.status == "draft" and not authored.workflow:
        typer.secho(
            f"Ticket authoring left {ref.id_slug} with no workflow. "
            "Every ticket needs one to be activated — relaunch "
            f"`coga ticket {ref.id_slug}` and pick a workflow "
            "(see coga/workflows/).",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)


def _snapshot_authoring_files(cfg: Config) -> dict[Path, str]:
    snapshot: dict[Path, str] = {}
    for root_name in AUTHORING_SYNC_DIRS:
        root = cfg.repo_root / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                snapshot[path.resolve(strict=False)] = sha256(path.read_bytes()).hexdigest()
    return snapshot


def _changed_authoring_paths(before: dict[Path, str], cfg: Config) -> set[Path]:
    after = _snapshot_authoring_files(cfg)
    changed = {path for path, digest in after.items() if before.get(path) != digest}
    changed.update(path for path in before if path not in after)
    return changed


def _authored_task_refs(
    cfg: Config,
    changed_paths: set[Path],
    before_tasks: set[str],
) -> list[TaskRef]:
    # Resolve changed paths against discovered task dirs rather than
    # reconstructing `tasks/<first-part>` — tasks may live in a sub-directory
    # at any depth (e.g. `tasks/auto/<slug>/`).
    refs: dict[str, TaskRef] = {}
    tasks = list_tasks(cfg)
    resolved = [path.resolve(strict=False) for path in changed_paths]
    for task_ref in tasks:
        task_root = task_ref.path.resolve(strict=False)
        if any(task_root in path.parents for path in resolved):
            refs[task_ref.id_slug] = task_ref

    for task_ref in tasks:
        if task_ref.id_slug not in before_tasks:
            refs.setdefault(task_ref.id_slug, task_ref)
    return [refs[slug] for slug in sorted(refs)]


def _support_paths(cfg: Config, changed_paths: set[Path]) -> list[Path]:
    support: list[Path] = []
    for root_name in ("contexts", "skills"):
        root = (cfg.repo_root / root_name).resolve(strict=False)
        for path in changed_paths:
            try:
                path.resolve(strict=False).relative_to(root)
            except ValueError:
                continue
            support.append(path)
    return sorted(support)


def _authoring_sync_message(authored_refs: list[TaskRef]) -> str:
    if len(authored_refs) == 1:
        return f"Ticket: {authored_refs[0].id_slug} — authored"
    if authored_refs:
        slugs = ", ".join(ref.id_slug for ref in authored_refs)
        return f"Ticket authoring — authored {slugs}"
    return "Ticket authoring — support files"


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
