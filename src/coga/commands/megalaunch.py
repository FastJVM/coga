"""`coga megalaunch` — sequentially attempt launchable active work."""

from __future__ import annotations

import sys

import typer

from coga.config import ConfigError, load_config
from coga.megalaunch import render_run_summary, run_megalaunch


def megalaunch(
    max_tasks: int | None = typer.Option(
        None,
        "--max-tasks",
        min=1,
        help="Stop after this many launchable tasks have been attempted.",
    ),
) -> None:
    """Run the shared megalaunch engine once."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    run = run_megalaunch(cfg, max_tasks=max_tasks)
    typer.echo(render_run_summary(run))
    if run.counts["failed"]:
        sys.exit(1)
