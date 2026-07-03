"""`coga megalaunch` — sequentially attempt launchable active work."""

from __future__ import annotations

import sys

import typer

from coga import notification
from coga.config import ConfigError, load_config
from coga.megalaunch import (
    MegalaunchError,
    MegalaunchRun,
    render_run_summary,
    run_megalaunch,
)


def megalaunch(
    max_tasks: int | None = typer.Option(
        None,
        "--max-tasks",
        min=1,
        help="Stop after this many launchable tasks have been attempted.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Only drain tasks currently assigned to this configured agent type.",
    ),
) -> None:
    """Run the shared megalaunch engine once."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    if agent is not None:
        try:
            cfg.agent_type(agent)
        except ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            sys.exit(2)

    try:
        run = run_megalaunch(cfg, max_tasks=max_tasks, agent_filter=agent)
    except MegalaunchError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    # Local outcome to stdout before the notification post, so a Slack crash
    # still leaves the run summary visible (coga/sync convention).
    typer.echo(render_run_summary(run))
    message = _drain_post_text(run)
    if message is not None:
        notification.post(cfg, message)
    if run.counts["failed"]:
        sys.exit(1)


def _drain_post_text(run: MegalaunchRun) -> str | None:
    """One live line: what was drained, or that budget skipped everything.

    Silent when the run had no results at all — an empty repo is lifecycle
    noise, not an outcome a teammate needs within minutes.
    """
    if not run.results:
        return None
    counts = run.counts
    launched = [result.slug for result in run.results if result.launched]
    parts = [
        "launched " + ", ".join(f"*{slug}*" for slug in launched)
        if launched
        else "nothing launched"
    ]
    if counts["skipped-budget"]:
        parts.append(f"{counts['skipped-budget']} skipped for budget")
    if counts["skipped-unresolved-blocker"] or counts["skipped-human-gate"]:
        skipped = counts["skipped-unresolved-blocker"] + counts["skipped-human-gate"]
        parts.append(f"{skipped} not launchable")
    if counts["failed"]:
        parts.append(f"{counts['failed']} failed")
    label = (
        f"Megalaunch drain ({run.agent_filter})"
        if run.agent_filter is not None
        else "Megalaunch drain"
    )
    return label + ": " + "; ".join(parts)
