"""`coga validate` — deterministic repo + config check."""

from __future__ import annotations


import typer

from coga.blackboard import BLACKBOARD_WARN_BYTES
from coga.config import ConfigError, load_config
from coga.validate import ValidationOptionError, emit_report, execute_validation


def validate(
    json_output: bool = typer.Option(
        False, "--json", help="Emit JSON instead of text."
    ),
    task: str | None = typer.Option(
        None,
        "--task",
        help=(
            "Validate exactly one task slug instead of the whole repo. "
            "Skips Slack and idle-stuck checks."
        ),
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Apply conservative safe repairs before reporting.",
    ),
    idle_hours: float = typer.Option(
        72.0, "--idle-hours", help="Active-task idle threshold."
    ),
    max_blackboard_kb: float = typer.Option(
        BLACKBOARD_WARN_BYTES / 1024,
        "--max-blackboard-kb",
        help="Blackboard size above which to warn about prompt bloat.",
    ),
    check_slack: bool = typer.Option(
        False,
        "--check-slack",
        help="Probe the Slack webhook with an empty-text payload (network call).",
    ),
) -> None:
    """Validate repo + config; exits 1 if any errors are found."""
    try:
        cfg = load_config(require_user=False)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    try:
        report = execute_validation(
            cfg, task=task, fix=fix, idle_hours=idle_hours,
            max_blackboard_kb=max_blackboard_kb,
            check_slack=check_slack,
        )
    except ValidationOptionError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    raise typer.Exit(emit_report(report, json_output=json_output))
