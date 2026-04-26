"""`relay step` — advance to next workflow step (or mark done)."""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.lock import TaskLock
from relay.logfile import append_log
from relay.slack import post_feed
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def step(
    next_step: int = typer.Argument(..., help="Next step number (1-indexed)."),
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
) -> None:
    """Advance to the next workflow step (or mark done)."""
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
    if not wf or not wf.get("steps"):
        _bail(f"Task {ref.id_slug} has no workflow steps.")

    steps = wf["steps"]
    total = len(steps)
    current_idx = ticket.step_index() or 0

    if next_step < current_idx or next_step < 1:
        _bail(f"Cannot move backward (current step {current_idx}, requested {next_step}).")
    if next_step > total + 1:
        _bail(f"Workflow has {total} steps; can advance at most to {total + 1} (done).")

    actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"

    if next_step == total + 1 or (next_step == total and current_idx == total):
        # Crossed the final step: mark done.
        ticket.frontmatter["status"] = "done"
        ticket.write(ref.path / "ticket.md")
        append_log(ref.path, actor, "task done")
        TaskLock(ref.path).release()
        post_feed(
            cfg,
            f"{ref.id_slug} \"{ticket.title}\" done ✓",
        )
        typer.echo(f"{ref.id_slug}: done")
        return

    new_step_name = steps[next_step - 1]["name"]
    ticket.frontmatter["step"] = f"{next_step} ({new_step_name})"
    ticket.write(ref.path / "ticket.md")
    append_log(ref.path, actor, f"advanced to step {next_step} ({new_step_name})")
    post_feed(
        cfg,
        f"{ticket.assignee or cfg.current_user} advanced "
        f"{ref.id_slug} to step {next_step} ({new_step_name})",
    )
    typer.echo(f"{ref.id_slug}: step {next_step} ({new_step_name})")


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
