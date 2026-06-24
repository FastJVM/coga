"""`relay secret get <ref>` — resolve and print one secret reference.

A human-facing query on top of the shared launch-time resolver. Secrets are
declared inline per-ticket (there is no `[secrets]` catalog), so `get` takes a
reference directly — `op://vault/item/field` (read live via `op read`) or
`env:VAR` — and resolves it through the same `select_launch_secrets` path
`relay launch` uses, so the two cannot diverge: same `op` shell-out, same
fail-loud errors (naming the reference, never the value). The resolved value is
printed to stdout only because the human explicitly asked for it; it is never
logged or posted.
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
    help="Resolve secret references on demand.",
    no_args_is_help=True,
)


@app.command("get")
def get(
    ref: str = typer.Argument(
        ...,
        help="The reference to resolve: `op://vault/item/field` or `env:VAR`.",
    ),
) -> None:
    """Resolve one `op://…` or `env:VAR` reference and print its value to stdout.

    Resolves through the same `select_launch_secrets` helper `relay launch`
    uses, so an `op://` reference is read live via `op read` and an unresolvable
    one fails loud (naming the reference, never the value). A raw literal is
    rejected — there is nothing to resolve.
    """
    try:
        load_config()
    except ConfigError as exc:
        _bail(str(exc))

    # Resolve the bare reference through the shared path by wrapping it in the
    # inline-secret shape a ticket carries. The name `value` is just a local
    # label for error messages; `select_launch_secrets` ignores `cfg`.
    try:
        resolved = select_launch_secrets(None, [{"value": ref}])
    except SecretError as exc:
        _bail(str(exc))

    typer.echo(resolved["value"])


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
