"""`relay automerge` — finish started tickets whose linked PR has merged.

Thin wrapper over `automerge.auto_bump_merged`. Designed to be called by
the post-merge git hook (which `relay init` installs) and to be safe to
run by hand.

Failures from `gh` (missing, unauthed, network) bubble up here as a
non-zero exit so the caller sees them. The opportunistic call inside
`relay status` swallows them instead.
"""

from __future__ import annotations

import sys

import typer

from relay.automerge import GhError, auto_bump_merged
from relay.config import ConfigError, load_config


def automerge() -> None:
    """Scan active/in-progress tickets; finish any whose linked PR has merged."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        count = auto_bump_merged(cfg, quiet=False)
    except GhError as exc:
        typer.secho(f"automerge: {exc}", fg=typer.colors.RED, err=True)
        sys.exit(2)

    if count == 0:
        typer.echo("automerge: no tickets bumped.")
