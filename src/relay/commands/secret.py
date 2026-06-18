"""`relay secret get <key>` — resolve and print one declared `[secrets]` value.

A human-facing query on top of the shared launch-time resolver. The reusable
behavior lives in `relay.config.select_launch_secrets` so this command and
`relay launch` cannot diverge: `get` resolves exactly the requested key through
that same least-privilege path (including live `op read` for `op://` references
and the same fail-loud errors), then prints the value to stdout — only because
the human explicitly asked for it. The value is never logged or posted.
"""

from __future__ import annotations

import sys

import typer

from relay.config import (
    ConfigError,
    SecretError,
    load_config,
    select_launch_secrets,
)

app = typer.Typer(
    name="secret",
    help="Resolve declared secret values on demand.",
    no_args_is_help=True,
)


@app.command("get")
def get(
    key: str = typer.Argument(..., help="The [secrets] key to resolve."),
) -> None:
    """Resolve one declared secret and print its value to stdout.

    Resolves through the same shared helper `relay launch` uses, so an `op://`
    reference is read live via `op read` and a missing/unresolvable secret fails
    loud (naming the key and reference, never the value).
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        resolved = select_launch_secrets(cfg, [key])
    except SecretError as exc:
        _bail(str(exc))

    typer.echo(resolved[key])


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
