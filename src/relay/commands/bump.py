"""`relay bump` — move through a workflow."""

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
from relay.repl_supervisor import emit_done_marker
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
    to_step: int | None = typer.Option(
        None,
        "--to",
        help="Human-only: rewind to an earlier 1-based workflow step number.",
    ),
    backward: bool = typer.Option(
        False,
        "--backward",
        help="Human-only: rewind one workflow step.",
    ),
) -> None:
    """Advance one workflow step, or let a human rewind to an earlier step.

    Bumping past the last step is an error — call `relay mark done <slug>`
    to finish. Tickets without a workflow can't be bumped at all.
    """
    if message is not None and not message.strip():
        _bail("--message cannot be empty")
    if to_step is not None and backward:
        _bail("Use either --to or --backward, not both.")

    rewind = to_step is not None or backward
    if rewind and os.environ.get("RELAY_SUPERVISED"):
        _bail(
            "Agents cannot rewind from a supervised relay launch. "
            "Call `relay panic --task <id> --reason \"...\"`; a human can "
            "rewind with `relay bump <id> --to <step>`."
        )

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
    if current_idx > total:
        _bail(
            f"Task {ref.id_slug} has invalid step {ticket.step!r}. "
            f"Workflow has steps 1-{total}."
        )
    if backward:
        next_step = current_idx - 1
        if current_idx <= 1:
            _bail(f"Task {ref.id_slug} is on the first step. Cannot rewind.")
    elif to_step is not None:
        next_step = to_step
        if to_step < 1 or to_step > total:
            _bail(f"Unknown step {to_step}. Workflow has steps 1-{total}.")
        if to_step == current_idx:
            _bail(f"Task {ref.id_slug} is already on step {to_step}.")
        if to_step > current_idx:
            _bail("Cannot skip ahead with --to. Use `relay bump` to advance one step.")
    else:
        next_step = current_idx + 1
        if current_idx >= total:
            _bail(
                f"Task {ref.id_slug} is on the final step. "
                f"Run `relay mark done {ref.id_slug}` to finish."
            )

    new_step = steps[next_step - 1]
    new_step_name = new_step["name"]
    prev_step_name = (
        steps[current_idx - 1]["name"] if current_idx >= 1 else f"step {current_idx}"
    )

    role = new_step.get("assignee")
    new_assignee: str | None = None
    if role is not None:
        try:
            resolved = resolve_step_assignee(cfg, ticket, role)
        except AssigneeResolutionError as exc:
            _bail(str(exc))
        if resolved != ticket.assignee:
            new_assignee = resolved

    handoff = f" → assigned to {new_assignee}" if new_assignee else ""

    if rewind:
        actor = f"human:{cfg.current_user}"
        finisher = cfg.current_user
        verb = "rewound"
    else:
        actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"
        finisher = ticket.assignee or cfg.current_user
        verb = "advanced"

    # The assignee the supervisor will see after this bump: the freshly
    # resolved one if the step changed it, else the unchanged current assignee.
    # Captured before `advance_step` so it can't be perturbed by the write.
    next_assignee = new_assignee if new_assignee is not None else ticket.assignee

    try:
        advance_step(
            cfg, ref, ticket,
            next_step=next_step,
            new_step_name=new_step_name,
            actor=actor,
            log_message=f"{verb} to step {next_step} ({new_step_name}){handoff}{suffix}",
            slack_text=(
                f"👉 {finisher} {verb} *{ref.id_slug}* \"{ticket.title}\": "
                f"{prev_step_name} → {new_step_name} "
                f"(step {next_step}/{total}){handoff}{suffix}"
            ),
            digest_detail=(
                f"{finisher} {verb}: {prev_step_name} → {new_step_name} "
                f"(step {next_step}/{total}){handoff}{suffix}"
            ),
            new_assignee=new_assignee,
            notify_slack=message is not None,
            echo=f"{ref.id_slug}: step {next_step} ({new_step_name}){handoff}",
        )
    except TaskValidationError as exc:
        _bail(str(exc))

    # When this bump ran inside a supervised `relay launch`, the supervisor
    # tears down the agent's REPL via the done marker (see
    # `emit_done_marker` below) and then decides whether to chain. Tell the
    # human what happens next so a long-running interactive session isn't
    # surprising.
    if os.environ.get("RELAY_SUPERVISED"):
        # Mirror `_harness_stop_reason` (launch.py): the supervisor chains
        # whenever the next step's assignee is a configured agent — including an
        # agent *rotation* (e.g. claude -> codex for peer review) — and only
        # returns control to the caller when the next step hands off to a human
        # (an assignee that is not a configured agent type) or is unassigned.
        # The old `new_assignee is None` check wrongly framed every rotation as
        # a stop, so a claude -> codex bump printed "will stop" while the
        # supervisor actually chained.
        will_chain = bool(next_assignee) and next_assignee in cfg.agents
        if will_chain:
            hint = (
                "Supervised launch: step done. relay launch will spawn "
                "a fresh agent session for the next step."
            )
        else:
            who = next_assignee or "an unassigned step"
            hint = (
                f"Supervised launch: step done. Next step hands off to {who} "
                "— relay launch will stop and return to the caller."
            )
        typer.secho(hint, fg=typer.colors.CYAN)

    # Tell a supervising `relay launch` the session is done so the agent's
    # REPL tears down without `/exit`. Harmless tagged line otherwise. The
    # resolved task path scopes the signal to this ticket so an unrelated
    # nested `relay bump` (e.g. a test fixture) can't end our session.
    emit_done_marker(session_id=str(ref.path.resolve()))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
