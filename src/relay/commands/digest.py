"""`relay digest` — flush the spooled state-change events into one Slack post.

This is the **consumer** half of the daily-digest pipeline. Batchable events
(`create`, `bump`, `mark`, `retire`, automerge done, recurring scaffolds) spool
structured JSONL records onto the `recurring/digest/` ticket's blackboard as
they happen (see `relay.slack.notify`). Once a day the digest recurring ticket
fires as a `mode: script` task, and its script step runs this command:

  read the spool → group project → person → ticket → render one message →
  post via the webhook → empty the spool.

Idempotent: an empty spool is a silent no-op, so a same-day re-run (or a quiet
day) posts nothing. The spool is emptied only after the post succeeds, under
the same single-process serialization every other relay command runs under, so
a failed post leaves the records for the next run and a record spooled after
the flush simply waits for the next day's flush.
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

    run_digest(cfg, quiet_empty=quiet_empty)


def run_digest(cfg, *, quiet_empty: bool = True) -> bool:
    """Render and post the day's spool, then empty it; return whether anything sent.

    Returns False (no-op) when the digest ticket isn't installed or the spool
    is empty. Posts *before* draining: the records are cleared only after a
    successful `post`, so a webhook failure (which `post` turns into a
    crash-loud `typer.Exit`) leaves the spool intact for the next run to retry,
    rather than silently dropping the day's events. Both steps run under the
    single-process serialization every relay command shares, so nothing spooled
    mid-run is lost.
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

    records = spool.read_records(spool_path)
    if not records:
        if not quiet_empty:
            typer.echo("digest: spool empty — nothing to post.")
        return False

    date_label = datetime.now().strftime("%Y-%m-%d")
    message = render_digest(cfg, records, date_label=date_label)
    typer.echo(f"digest: posting {len(records)} event(s) for {date_label}")
    post(cfg, message, task_path=spool_path.parent)
    spool.drain(spool_path)
    return True
