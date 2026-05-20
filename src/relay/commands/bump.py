"""`relay bump` — advance one workflow step."""

from __future__ import annotations

import os
import sys

import typer

from relay.bump import (
    AssigneeResolutionError,
    advance_step,
    resolve_step_assignee,
)
from relay.config import ConfigError, load_config
from relay.paths import workflow_path
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)
from relay.validate import TaskValidationError, assert_task_valid
from relay.workflow import Workflow, WorkflowError


def bump(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
) -> None:
    """Advance one workflow step.

    Bumping past the last step is an error — call `relay mark done <slug>`
    to finish. Tickets without a workflow can't be bumped at all.
    """
    if message is not None and not message.strip():
        _bail("--message cannot be empty")

    suffix = f" — {message}" if message else ""

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)

    if ticket.status != "in_progress":
        _bail(f"Task {ref.id_slug} is {ticket.status!r}. Cannot advance.")

    # Hand-authored / pre-freeze tickets carry `workflow:` as a bare string
    # ref instead of the frozen dict scaffold produces. Resolve and freeze
    # in-place so the rest of bump (and future bumps) sees a normal shape.
    if isinstance(ticket.workflow, str):
        try:
            wf_def = Workflow.load(workflow_path(cfg, ticket.workflow))
        except WorkflowError as exc:
            _bail(str(exc))
        ticket.frontmatter["workflow"] = wf_def.freeze()
        if not ticket.step:
            ticket.frontmatter["step"] = f"1 ({wf_def.steps[0].name})"
        ticket.write(ref.path / "ticket.md")
        try:
            assert_task_valid(cfg, ref, action="freeze workflow on bump")
        except TaskValidationError as exc:
            _bail(str(exc))

    wf = ticket.workflow

    if not wf or not wf.get("steps"):
        _bail(
            f"Task {ref.id_slug} has no workflow. "
            f"Run `relay mark done {ref.id_slug}` to finish."
        )

    steps = wf["steps"]
    total = len(steps)
    current_idx = ticket.step_index() or 0
    next_step = current_idx + 1

    if current_idx >= total:
        _bail(
            f"Task {ref.id_slug} is on the final step. "
            f"Run `relay mark done {ref.id_slug}` to finish."
        )

    new_step = steps[next_step - 1]
    new_step_name = new_step["name"]

    role = new_step.get("assignee")
    new_assignee: str | None = None
    if role is not None:
        try:
            resolved = resolve_step_assignee(ticket, role)
        except AssigneeResolutionError as exc:
            _bail(str(exc))
        if resolved != ticket.assignee:
            new_assignee = resolved

    handoff = f" → assigned to {new_assignee}" if new_assignee else ""

    actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"
    finisher = ticket.assignee or cfg.current_user

    try:
        advance_step(
            cfg, ref, ticket,
            next_step=next_step,
            new_step_name=new_step_name,
            actor=actor,
            log_message=f"advanced to step {next_step} ({new_step_name}){handoff}{suffix}",
            slack_text=(
                f"👉 {finisher} advanced "
                f"*{ref.id_slug}* → step {next_step} ({new_step_name}){handoff}{suffix}"
            ),
            new_assignee=new_assignee,
            echo=f"{ref.id_slug}: step {next_step} ({new_step_name}){handoff}",
        )
    except TaskValidationError as exc:
        _bail(str(exc))

    # The step advanced. When this bump ran inside a supervised
    # `relay launch` (interactive mode), the agent process is a REPL that
    # only exits when the human quits it — the launch supervisor can't
    # pick up the next step until then. Tell the human so the chain
    # isn't silently stalled waiting on a quit nobody knows to make.
    if os.environ.get("RELAY_SUPERVISED"):
        will_chain = bool(new_step.get("skills")) and new_assignee is None
        if will_chain:
            hint = (
                "Supervised launch: step done. Exit the agent session "
                "(Ctrl-D or /exit) — relay launch will start the next step."
            )
        else:
            hint = (
                "Supervised launch: step done. Exit the agent session "
                "(Ctrl-D or /exit) — the next step is a handoff, so "
                "relay launch will stop there."
            )
        typer.secho(hint, fg=typer.colors.CYAN)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
