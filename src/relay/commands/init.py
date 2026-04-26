"""`relay init` — scaffold a new relay repo from upstream."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import typer

from relay.commands.update import (
    TEMPLATE_SUBPATH,
    clone_upstream,
    refresh_cli,
)


def init(
    path: Path = typer.Argument(
        Path("."),
        help="Target directory (created if missing). `relay-os/` is scaffolded inside it.",
    ),
) -> None:
    """Scaffold `relay-os/` inside PATH from upstream."""
    target = path.resolve()
    relay_os = target / "relay-os"

    if relay_os.exists():
        typer.secho(
            f"{relay_os} already exists — refusing to overwrite.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    target.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="relay-init-") as tmp:
        clone_dir = clone_upstream(Path(tmp) / "repo")

        upstream_templates = clone_dir / TEMPLATE_SUBPATH
        if not upstream_templates.is_dir():
            typer.secho(
                f"Upstream layout changed — {TEMPLATE_SUBPATH} not found in clone.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)

        shutil.copytree(upstream_templates, relay_os)
        refresh_cli(clone_dir, relay_os)

    bin_dir = relay_os / ".relay" / "bin"
    typer.echo("")
    typer.echo(f"Initialized relay repo at {relay_os}")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo(f"  1. Install Python deps for the vendored CLI (one-time):")
    typer.echo(f"       pip install -r {relay_os / '.relay' / 'requirements.txt'}")
    typer.echo(f"  2. Add the bin dir to your PATH so `relay` runs from this repo:")
    typer.echo(f"       export PATH=\"{bin_dir}:$PATH\"")
    typer.echo(f"  3. Edit {relay_os}/relay.toml — set your projects, agents, channels.")
    typer.echo(f"  4. Create {relay_os}/relay.local.toml with `user = \"<your-name>\"`.")
    typer.echo(f"  5. Run `relay --help` to see what's available.")
