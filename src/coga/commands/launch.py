"""CLI argument parsing, presentation, and exit handling for launch."""

from __future__ import annotations

import os

import typer

from coga import git
from coga import launch as launch_service
from coga.oscompat import process_exit_status

WINDOWS_IDLE_TIMEOUT_REFUSAL = (
    "--idle-timeout is unavailable on native Windows: the agent owns the "
    "console directly, so Coga cannot observe its output to measure "
    "idleness. Use --max-session <seconds> for a wall-clock limit instead."
)


def _idle_timeout_unavailable() -> bool:
    return os.name == "nt"


def launch(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>` ticket."),
    args: list[str] | None = typer.Argument(
        None,
        help="Trailing positional arguments for the launch target. They appear "
        "as an ordered Launch arguments block in the composed agent prompt; a "
        "bootstrap ticket.py receives them as its argv, and a stateful "
        "ticket.py target refuses them.",
    ),
    agent_override: str | None = typer.Option(
        None,
        "--agent",
        help="Explicit agent override for this launch, including an assist on "
        "a human-owned step; never rewrites the ticket assignee.",
    ),
    prompt_report: bool = typer.Option(
        False,
        "--prompt-report",
        help="Print composed prompt layers and approximate token counts, then exit without launching.",
    ),
    idle_timeout: float | None = typer.Option(
        None,
        "--idle-timeout",
        help="Tear down a stalled interactive REPL after this many seconds with "
        "no output or input (it never signalled done). Off by default — an "
        "attended launch waits indefinitely. `coga recurring` sets it so one "
        "stuck agent can't block the sweep. Unavailable on native Windows; "
        "use --max-session there.",
    ),
    max_session: float | None = typer.Option(
        None,
        "--max-session",
        help="Tear down an interactive REPL after this many seconds of wall-clock, "
        "even while it is still producing output (the runaway-loop case idle "
        "timeout misses). Off by default. `coga recurring` sets it from "
        "`[launch].max_session` so a busy-but-wedged agent can't block the sweep.",
    ),
    return_timeout: bool = typer.Option(
        False,
        "--return-timeout",
        hidden=True,
        help="Internal: return the script/timeout stop kind, or a spawned "
        "bootstrap session's termination kind, to the caller.",
    ),
    script_failure_important: bool = typer.Option(
        False,
        "--script-failure-important",
        hidden=True,
        help=(
            "Internal: route ticket.py failures to the important notification "
            "channel."
        ),
    ),
) -> None:
    """Compose context, start work on a task."""
    if idle_timeout is not None and _idle_timeout_unavailable():
        # Refuse before any state change, and keep the CLI's final sweep from
        # publishing pre-existing dirt on the way out (exit stays 2).
        git.state_sweep_withheld.set(True)
        typer.secho(WINDOWS_IDLE_TIMEOUT_REFUSAL, fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    try:
        with launch_service.launch_reporting(typer.secho):
            result = launch_service.launch(
                task, args=args, agent_override=agent_override,
                prompt_report=prompt_report, idle_timeout=idle_timeout,
                max_session=max_session, return_timeout=return_timeout,
                script_failure_important=script_failure_important,
            )
    except launch_service.LaunchBail as exc:
        if exc.reason:
            typer.secho(exc.reason, fg=typer.colors.RED, err=True)
        # An agent's Windows exit code is a DWORD; keep it exact (see
        # `process_exit_status`). Every other code passes unchanged.
        raise typer.Exit(process_exit_status(exc.code)) from exc
    if result.exit_code:
        raise typer.Exit(process_exit_status(result.exit_code))
