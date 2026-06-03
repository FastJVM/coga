"""`relay digest` — flush the spooled state-change events into one Slack post.

This is the **consumer** half of the daily-digest pipeline. Batchable events
(`create`, `bump`, `mark`, `retire`, automerge done, recurring scaffolds) spool
structured JSONL records onto the `recurring/digest/` ticket's blackboard as
they happen (see `relay.slack.notify`). Once a day the digest recurring ticket
fires as a `mode: script` task, and its script step runs this command:

  drain the spool → group project → person → ticket → render one message →
  post via the webhook → leave the spool emptied.

Idempotent: an empty spool is a silent no-op, so a same-day re-run (or a quiet
day) posts nothing. `drain` empties the section under the same single-process
serialization every other relay command runs under, so a record spooled after
the drain simply waits for the next day's flush.
"""

from __future__ import annotations

import sys
from datetime import datetime

import typer

from relay import spool
from relay.config import ConfigError, load_config
from relay.slack import digest_spool_path, post, render_digest


def digest(
    quiet_empty: bool = typer.Option(
        True,
        "--quiet-empty/--announce-empty",
        help="On an empty spool, stay silent (default) or print a one-line note.",
    ),
) -> None:
    """Render and post the day's spooled events, then empty the spool."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    posted = run_digest(cfg, quiet_empty=quiet_empty)
    if not posted and not quiet_empty:
        typer.echo("digest: spool empty — nothing to post.")


def run_digest(cfg, *, quiet_empty: bool = True) -> bool:
    """Drain the spool, post the digest, and return whether anything was sent.

    Returns False (no-op) when the digest ticket isn't installed or the spool
    is empty. The drain-then-post order means records are removed before the
    post; a post failure crashes loud (per `post`), and re-running re-derives an
    empty digest rather than double-posting.
    """
    spool_path = digest_spool_path(cfg)
    if spool_path is None:
        if not quiet_empty:
            typer.secho(
                "digest: no recurring/digest/ ticket installed — nothing to flush.",
                fg=typer.colors.YELLOW,
                err=True,
            )
        return False

    records = spool.drain(spool_path)
    if not records:
        return False

    date_label = datetime.now().strftime("%Y-%m-%d")
    message = render_digest(cfg, records, date_label=date_label)
    typer.echo(f"digest: posting {len(records)} event(s) for {date_label}")
    post(cfg, message, task_path=spool_path.parent)
    return True
