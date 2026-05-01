"""`relay bump` — advance one workflow step (or mark done)."""

from __future__ import annotations

import sys

import typer

from relay.bump import advance_step, mark_done
from relay.config import ConfigError, load_config
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def bump(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
) -> None:
    """Advance one workflow step (or mark done if past the last step)."""
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

    if ticket.status != "active":
        _bail(f"Task {ref.id_slug} is {ticket.status!r}. Cannot advance.")

    wf = ticket.workflow
    actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"
    finisher = ticket.assignee or cfg.current_user
    done_slack = (
        f"🎉 {finisher} finished *{ref.id_slug}* \"{ticket.title}\"{suffix}"
    )

    # No workflow → bump marks done. The only "step" is the whole ticket.
    if not wf or not wf.get("steps"):
        mark_done(
            cfg, ref, ticket,
            actor=actor,
            log_message=f"task done{suffix}",
            slack_text=done_slack,
            image_url=cfg.gif_for("done"),
            echo=f"{ref.id_slug}: done",
        )
        return

    steps = wf["steps"]
    total = len(steps)
    current_idx = ticket.step_index() or 0
    next_step = current_idx + 1

    if current_idx >= total:
        # Already on the final step: bump marks done.
        mark_done(
            cfg, ref, ticket,
            actor=actor,
            log_message=f"task done{suffix}",
            slack_text=done_slack,
            image_url=cfg.gif_for("done"),
            echo=f"{ref.id_slug}: done",
        )
        return

    new_step_name = steps[next_step - 1]["name"]
    advance_step(
        cfg, ref, ticket,
        next_step=next_step,
        new_step_name=new_step_name,
        actor=actor,
        log_message=f"advanced to step {next_step} ({new_step_name}){suffix}",
        slack_text=(
            f"👉 {finisher} advanced "
            f"*{ref.id_slug}* → step {next_step} ({new_step_name}){suffix}"
        ),
        echo=f"{ref.id_slug}: step {next_step} ({new_step_name})",
    )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
