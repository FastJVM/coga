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
import subprocess
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
    upstream_sha,
    write_bin_wrapper,
    write_pin,
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
        sha = upstream_sha(clone_dir)

    install_venv(relay_os)
    write_bin_wrapper(relay_os / ".relay" / "bin")
    write_pin(relay_os, sha)

    local_toml = relay_os / "relay.local.toml"
    local_toml.write_text(LOCAL_TOML_TEMPLATE)

    bin_dir = relay_os / ".relay" / "bin"
    shim = _try_install_shim(bin_dir / "relay")
    commit_sha = _git_commit_relay_os(target, relay_os)

    typer.echo("")
    typer.echo(f"Initialized relay repo at {relay_os}")
    typer.echo(f"Wrote {local_toml} (set `user` to your assignee name).")
    if sha is not None:
        typer.echo(f"Pinned to upstream {sha[:12]}.")
    if commit_sha is not None:
        typer.echo(f"Committed relay-os/ as {commit_sha[:12]} (push when ready).")

    # Whether the user already has a working `relay` they can run as-is.
    # `shutil.which` honors the executable bit, so a stale non-executable
    # file at `~/.local/bin/relay` won't fool us.
    existing = shutil.which("relay")
    if shim is not None:
        typer.echo(f"`relay` is on your PATH via {shim}.")
    elif existing:
        typer.echo(f"`relay` is already on your PATH at {existing}.")

    steps: list[str] = []
    if shim is None and not existing:
        steps.append(
            "Add the bin dir to your PATH so `relay` runs:\n"
            f"       export PATH=\"{bin_dir}:$PATH\""
        )
    steps.append(f"Edit {relay_os}/relay.toml — set your projects, agents, channels.")
    steps.append(f"Set `user` in {local_toml} to match an [assignees.x] in relay.toml.")
    steps.append("Run `relay --help` to see what's available.")

    typer.echo("")
    typer.echo("Next steps:")
    for i, step in enumerate(steps, 1):
        typer.echo(f"  {i}. {step}")


def _do_update() -> None:
    relay_os = find_repo_root()

    with tempfile.TemporaryDirectory(prefix="relay-init-update-") as tmp:
        clone_dir = clone_upstream(Path(tmp) / "repo")
        refresh_cli(clone_dir, relay_os)
        copied = refresh_templates(clone_dir, relay_os)
        sha = upstream_sha(clone_dir)

    install_venv(relay_os)
    write_bin_wrapper(relay_os / ".relay" / "bin")
    write_pin(relay_os, sha)

    typer.echo("")
    typer.echo(f"Refreshed CLI at {relay_os / '.relay'}")
    if sha is not None:
        typer.echo(f"Pinned to upstream {sha[:12]}.")
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


def _git_commit_relay_os(target: Path, relay_os: Path) -> str | None:
    """If `target` is a git repo, stage relay-os/ and commit. Don't push.

    Returns the new commit SHA on success, None if we skipped (not a git repo,
    nothing to stage, or git invocation failed). Never raises.
    """
    if not (target / ".git").exists():
        return None
    try:
        subprocess.run(
            ["git", "-C", str(target), "add", "--", "relay-os"],
            check=True,
            capture_output=True,
            text=True,
        )
        # Anything actually staged?
        diff = subprocess.run(
            ["git", "-C", str(target), "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if diff.returncode == 0:
            return None
        subprocess.run(
            ["git", "-C", str(target), "commit", "-m", "Scaffold relay-os via `relay init`"],
            check=True,
            capture_output=True,
            text=True,
        )
        rev = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return rev.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


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
