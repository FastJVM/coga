"""`coga validate` — deterministic repo + config check."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Any

import typer

from coga.blackboard import BLACKBOARD_WARN_BYTES
from coga.config import ConfigError, load_config
from coga.validate import run, validate_task
from coga.version_skew import warn_if_installed_predates_source


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
    check_github: bool = typer.Option(
        False,
        "--check-github",
        help="Probe git/GitHub auth readiness via git/gh (network call).",
    ),
) -> None:
    """Validate repo + config; exits 1 if any errors are found."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    # Diagnostic surface: validate is where a developer looks when something is
    # off, so surface a stale installed binary here too. Warn-only, to stderr
    # (never stdout, so `--json` output stays clean), silent outside a source
    # checkout.
    warn_if_installed_predates_source(cfg.repo_root)

    if task is not None:
        if check_slack:
            typer.secho(
                "--check-slack is not supported with --task; "
                "it probes the Slack webhook, which is a whole-repo concern.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(2)
        if check_github:
            typer.secho(
                "--check-github is not supported with --task; "
                "it probes git/GitHub auth, which is a whole-repo concern.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(2)
        report = validate_task(
            cfg,
            task,
            fix=fix,
            max_blackboard_bytes=int(max_blackboard_kb * 1024),
            idle_hours=idle_hours,
        )
    else:
        report = run(
            cfg,
            idle_hours=idle_hours,
            max_blackboard_bytes=int(max_blackboard_kb * 1024),
            check_slack=check_slack,
            check_github=check_github,
            fix=fix,
        )

    if json_output:
        payload: dict[str, Any] = {
            "generated_at": report.generated_at,
            "ok_count": report.ok_count,
            "fixes": [asdict(f) for f in report.fixes],
            "issues": [asdict(i) for i in report.issues],
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not report.issues:
            for fix_item in report.fixes:
                typer.echo(f"[FIX] {fix_item.task}: {fix_item.kind} — {fix_item.message}")
            typer.echo(f"All good ({report.ok_count} tasks checked).")
        else:
            for fix_item in report.fixes:
                typer.echo(f"[FIX] {fix_item.task}: {fix_item.kind} — {fix_item.message}")
            for issue in report.issues:
                sev = issue.severity.upper()
                typer.echo(f"[{sev}] {issue.task}: {issue.kind} — {issue.message}")

    if any(i.severity == "error" for i in report.issues):
        raise typer.Exit(1)
