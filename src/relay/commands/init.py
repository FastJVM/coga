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
        help="Target directory. Created if missing. Must be empty.",
    ),
) -> None:
    """Copy the relay repo template into PATH."""
    target = path.resolve()

    if target.exists() and any(target.iterdir()):
        typer.secho(
            f"{target} is not empty — refusing to overwrite.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    template = resources.files("relay.resources").joinpath("templates")
    with resources.as_file(template) as src:
        shutil.copytree(src, target, dirs_exist_ok=True)

    typer.echo(f"Initialized relay repo at {target}")
