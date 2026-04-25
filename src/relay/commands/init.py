"""`relay init` — scaffold a new relay repo from the bundled template."""

from __future__ import annotations

import shutil
import sys
from importlib import resources
from pathlib import Path

import typer


def init(
    path: Path = typer.Argument(
        Path("."),
        help="Target directory (created if missing). `relay-os/` is scaffolded inside it.",
    ),
) -> None:
    """Scaffold `relay-os/` inside PATH from the bundled template."""
    target = path.resolve()
    relay_os = target / "relay-os"

    if relay_os.exists():
        typer.secho(
            f"{relay_os} already exists — refusing to overwrite.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    template = resources.files("relay.resources").joinpath("templates")
    with resources.as_file(template) as src:
        shutil.copytree(src, target, dirs_exist_ok=True)

    typer.echo(f"Initialized relay repo at {relay_os}")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo(f"  1. Edit {relay_os}/relay.toml — set your projects, agents, channels.")
    typer.echo(f"  2. Optionally create relay.local.toml for paths and credentials.")
    typer.echo(f"  3. Run `relay --help` to see what's available.")
