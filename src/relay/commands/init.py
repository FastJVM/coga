"""`relay init` — scaffold a new relay repo, or refresh an existing one.

Default mode (`relay init`) writes everything from scratch into `<path>/relay-os/`
and refuses to overwrite if it already exists. `--update` mode refreshes the
vendored CLI in `.relay/` and any `_*` template scaffolds, leaving user-edited
config (`relay.toml`, `rules.md`, etc.) untouched. Both modes (re)build the
self-contained venv that backs the `relay` console script.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import typer

from relay.commands.update import (
    TEMPLATE_SUBPATH,
    clone_upstream,
    install_venv,
    refresh_cli,
    refresh_templates,
    write_bin_wrapper,
)
from relay.config import find_repo_root


LOCAL_TOML_TEMPLATE = """\
# Machine-local config — gitignored. Holds your assignee name, project paths,
# and secrets. Override anything from relay.toml here without committing it.
user = ""

# [paths]
# my-project = "/absolute/path/to/checkout"

# [secrets]
# stripe_key = "env:STRIPE_SECRET_KEY"
"""


def init(
    path: Path = typer.Argument(
        Path("."),
        help=(
            "Target dir for fresh init (created if missing). "
            "Ignored under --update — refreshes the current relay-os/."
        ),
    ),
    update: bool = typer.Option(
        False,
        "--update",
        help="Refresh vendored CLI + `_*` templates in the current relay-os/. Leaves user config alone.",
    ),
) -> None:
    """Scaffold `relay-os/` from upstream, or refresh it with --update."""
    if update:
        _do_update()
    else:
        _do_init(path)


def _do_init(path: Path) -> None:
    target = path.resolve()
    relay_os = target / "relay-os"

    if relay_os.exists():
        typer.secho(
            f"{relay_os} already exists — use `relay init --update` to refresh.",
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

    install_venv(relay_os)
    write_bin_wrapper(relay_os / ".relay" / "bin")

    local_toml = relay_os / "relay.local.toml"
    local_toml.write_text(LOCAL_TOML_TEMPLATE)

    bin_dir = relay_os / ".relay" / "bin"
    shim = _try_install_shim(bin_dir / "relay")

    typer.echo("")
    typer.echo(f"Initialized relay repo at {relay_os}")
    typer.echo(f"Wrote {local_toml} (set `user` to your assignee name).")
    typer.echo("")
    typer.echo("Next steps:")
    if shim is not None:
        typer.echo(f"  1. `relay` is on your PATH via {shim}.")
    else:
        typer.echo(f"  1. Add the bin dir to your PATH so `relay` runs from this repo:")
        typer.echo(f"       export PATH=\"{bin_dir}:$PATH\"")
    typer.echo(f"  2. Edit {relay_os}/relay.toml — set your projects, agents, channels.")
    typer.echo(f"  3. Set `user` in {local_toml} to match an [assignees.x] in relay.toml.")
    typer.echo(f"  4. Run `relay --help` to see what's available.")


def _do_update() -> None:
    relay_os = find_repo_root()

    with tempfile.TemporaryDirectory(prefix="relay-init-update-") as tmp:
        clone_dir = clone_upstream(Path(tmp) / "repo")
        refresh_cli(clone_dir, relay_os)
        copied = refresh_templates(clone_dir, relay_os)

    install_venv(relay_os)
    write_bin_wrapper(relay_os / ".relay" / "bin")

    typer.echo("")
    typer.echo(f"Refreshed CLI at {relay_os / '.relay'}")
    if copied:
        typer.echo(f"Refreshed {len(copied)} template file(s):")
        for rel in copied:
            typer.echo(f"  {rel}")


def _try_install_shim(wrapper: Path) -> Path | None:
    """Symlink `~/.local/bin/relay` -> wrapper if that dir is on PATH and unclaimed.

    Returns the symlink path on success, None if we skipped (dir not on PATH,
    target already exists, or symlink failed).
    """
    target_dir = Path.home() / ".local" / "bin"
    if not _on_path(target_dir):
        return None
    target = target_dir / "relay"
    if target.exists() or target.is_symlink():
        return None
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target.symlink_to(wrapper)
    except OSError:
        return None
    return target


def _on_path(directory: Path) -> bool:
    resolved = directory.resolve() if directory.exists() else directory
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            if Path(entry).resolve() == resolved:
                return True
        except OSError:
            continue
    return False
