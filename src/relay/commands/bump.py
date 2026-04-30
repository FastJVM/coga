"""`relay bump` — advance one workflow step (or mark done)."""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.lock import TaskLock
from relay.logfile import append_log
from relay.slack import post
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def bump(
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
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

    # No workflow → bump marks done. The only "step" is the whole ticket.
    if not wf or not wf.get("steps"):
        ticket.frontmatter["status"] = "done"
        ticket.write(ref.path / "ticket.md")
        append_log(ref.path, actor, f"task done{suffix}")
        TaskLock(ref.path).release()
        # Echo before post: state has already changed; if slack crashes the
        # user still sees the local outcome on stdout before the error on stderr.
        typer.echo(f"{ref.id_slug}: done")
        post(
            cfg,
            f"🎉 {ticket.assignee or cfg.current_user} finished "
            f"*{ref.id_slug}* \"{ticket.title}\"{suffix}",
            task_path=ref.path,
            image_url=cfg.gif_for("done"),
        )
        return

    steps = wf["steps"]
    total = len(steps)
    current_idx = ticket.step_index() or 0
    next_step = current_idx + 1

    if current_idx >= total:
        # Already on the final step: bump marks done.
        ticket.frontmatter["status"] = "done"
        ticket.write(ref.path / "ticket.md")
        append_log(ref.path, actor, f"task done{suffix}")
        TaskLock(ref.path).release()
        typer.echo(f"{ref.id_slug}: done")
        post(
            cfg,
            f"🎉 {ticket.assignee or cfg.current_user} finished "
            f"*{ref.id_slug}* \"{ticket.title}\"{suffix}",
            task_path=ref.path,
            image_url=cfg.gif_for("done"),
        )
        return

    new_step_name = steps[next_step - 1]["name"]
    ticket.frontmatter["step"] = f"{next_step} ({new_step_name})"
    ticket.write(ref.path / "ticket.md")
    append_log(ref.path, actor, f"advanced to step {next_step} ({new_step_name}){suffix}")
    typer.echo(f"{ref.id_slug}: step {next_step} ({new_step_name})")
    post(
        cfg,
        f"👉 {ticket.assignee or cfg.current_user} advanced "
        f"*{ref.id_slug}* → step {next_step} ({new_step_name}){suffix}",
        task_path=ref.path,
    )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
