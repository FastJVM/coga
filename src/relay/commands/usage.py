"""`relay usage` — read token-usage records from task blackboards."""

from __future__ import annotations

import json
import sys

import typer

from relay.config import ConfigError, load_config
from relay.usage import Rollup, load_records, rollup


BY_CHOICES = ("task", "model", "agent", "step")


def usage(
    by: str = typer.Option(
        "task",
        "--by",
        help=f"Group rows by one of: {', '.join(BY_CHOICES)}.",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Include records at or after this ISO timestamp or YYYY-MM-DD date.",
    ),
    until: str | None = typer.Option(
        None,
        "--until",
        help="Include records at or before this ISO timestamp or YYYY-MM-DD date.",
    ),
    task: str | None = typer.Option(
        None,
        "--task",
        help="Include records for one task slug only.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON for downstream consumers.",
    ),
) -> None:
    """Show LLM token usage recorded under task blackboards."""
    if by not in BY_CHOICES:
        typer.secho(
            f"--by must be one of: {', '.join(BY_CHOICES)}",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        result = rollup(
            load_records(cfg.repo_root),
            by=by,
            since=since,
            until=until,
            task=task,
        )
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    if json_output:
        typer.echo(json.dumps(result.to_dict(), sort_keys=True))
        return
    typer.echo(_format_rollup(result))


def _format_rollup(result: Rollup) -> str:
    lines = [f"Usage totals by {result.by}", _format_overall(result)]
    if not result.groups:
        lines.append("(no usage records)")
        return "\n".join(lines)
    lines.extend([
        "",
        f"{'key':<34} {'sessions':>8} {'unknown':>8} {'total':>12} "
        f"{'input':>12} {'cache_create':>14} {'cache_read':>12} {'output':>12}",
    ])
    for row in result.groups:
        key = row.key if len(row.key) <= 34 else row.key[:31] + "..."
        lines.append(
            f"{key:<34} {row.sessions:>8} {row.unknown_sessions:>8} "
            f"{row.total_tokens:>12} {row.input_tokens:>12} "
            f"{row.cache_creation_input_tokens:>14} "
            f"{row.cache_read_input_tokens:>12} {row.output_tokens:>12}"
        )
    return "\n".join(lines)


def _format_overall(result: Rollup) -> str:
    overall = result.overall
    return (
        "Overall: "
        f"sessions={overall.sessions} "
        f"unknown={overall.unknown_sessions} "
        f"total={overall.total_tokens} "
        f"input={overall.input_tokens} "
        f"cache_create={overall.cache_creation_input_tokens} "
        f"cache_read={overall.cache_read_input_tokens} "
        f"output={overall.output_tokens}"
    )
