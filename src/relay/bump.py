"""Step transitions — the shared core of `relay bump` and `relay automerge`.

Both commands need to:
  - mutate ticket frontmatter (advance step OR mark done)
  - append a line to log.md
  - release the lock when done
  - echo the local outcome to stdout
  - post to Slack

The CLI command (`relay bump`) and the auto-merge scanner reuse the
finalizers below so the on-disk shape stays identical regardless of who
triggered the transition. Only the log line, the Slack text, and the
actor differ between the two callers — those come in as arguments.
"""

from __future__ import annotations

import typer

from relay.config import Config
from relay.lock import TaskLock
from relay.logfile import append_log
from relay.slack import post
from relay.tasks import TaskRef
from relay.ticket import Ticket


def mark_done(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    image_url: str | None = None,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `done`: write frontmatter, log, release lock, post.

    `echo` is the stdout line printed before the Slack post (so the local
    outcome is visible even if Slack crashes). Pass `None` to suppress —
    used by the quiet auto-bump path inside `relay status`.
    """
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    append_log(ref.path, actor, log_message)
    TaskLock(ref.path).release()
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path, image_url=image_url)


def advance_step(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    next_step: int,
    new_step_name: str,
    actor: str,
    log_message: str,
    slack_text: str,
    echo: str | None = None,
) -> None:
    """Advance a ticket to the next workflow step."""
    ticket.frontmatter["step"] = f"{next_step} ({new_step_name})"
    ticket.write(ref.path / "ticket.md")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path)


__all__ = ["mark_done", "advance_step"]
