"""`relay validate` — deterministic repo + config check."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Any

import typer

from relay.config import ConfigError, load_config
from relay.validate import run


def validate(
    json_output: bool = typer.Option(
        False, "--json", help="Emit JSON instead of text."
    ),
    max_lock_hours: float = typer.Option(
        24.0, "--max-lock-hours", help="Lock age above which to flag as stale."
    ),
    idle_hours: float = typer.Option(
        72.0, "--idle-hours", help="Active-task idle threshold."
    ),
    check_slack: bool = typer.Option(
        False,
        "--check-slack",
        help="Probe the Slack webhook with an empty-text payload (network call).",
    ),
) -> None:
    """Validate repo + config; exits 1 if any errors are found."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    report = run(
        cfg,
        max_lock_hours=max_lock_hours,
        idle_hours=idle_hours,
        check_slack=check_slack,
    )

    if json_output:
        payload: dict[str, Any] = {
            "generated_at": report.generated_at,
            "ok_count": report.ok_count,
            "issues": [asdict(i) for i in report.issues],
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not report.issues:
            typer.echo(f"All good ({report.ok_count} tasks checked).")
        else:
            for issue in report.issues:
                sev = issue.severity.upper()
                typer.echo(f"[{sev}] {issue.task}: {issue.kind} — {issue.message}")

    if any(i.severity == "error" for i in report.issues):
        raise typer.Exit(1)
