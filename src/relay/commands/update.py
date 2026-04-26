"""`relay update` — refresh the vendored CLI + `_template` scaffolds from upstream."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

from relay.config import find_repo_root


RELAY_REPO_URL = "https://github.com/FastJVM/relay"
TEMPLATE_SUBPATH = Path("src/relay/resources/templates/relay-os")
CLI_SRC_SUBPATH = Path("src/relay")


def update() -> None:
    """Pull the latest CLI + `_template` scaffolds from upstream into relay-os/."""
    relay_os = find_repo_root()

    with tempfile.TemporaryDirectory(prefix="relay-update-") as tmp:
        clone_dir = clone_upstream(Path(tmp) / "repo")
        refresh_cli(clone_dir, relay_os)
        copied = refresh_templates(clone_dir, relay_os)

    typer.echo("")
    typer.echo(f"Refreshed CLI at {relay_os / '.relay'}")
    if copied:
        typer.echo(f"Refreshed {len(copied)} template file(s):")
        for rel in copied:
            typer.echo(f"  {rel}")


def clone_upstream(into: Path) -> Path:
    """Shallow-clone the relay repo into `into`. Exit on failure. Return the path."""
    typer.echo(f"Cloning {RELAY_REPO_URL} (shallow)…")
    result = subprocess.run(
        ["git", "clone", "--depth=1", RELAY_REPO_URL, str(into)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        typer.secho(
            f"git clone failed:\n{result.stderr}",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return into


def refresh_cli(clone_dir: Path, relay_os: Path) -> None:
    """Replace `relay-os/.relay/src/relay/` with the version from the clone.

    Also writes the `bin/relay` wrapper so the CLI is callable from PATH.
    """
    src = clone_dir / CLI_SRC_SUBPATH
    if not src.is_dir():
        typer.secho(
            f"Upstream layout changed — {CLI_SRC_SUBPATH} not found in clone.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    dst_relay = relay_os / ".relay"
    dst_src = dst_relay / "src" / "relay"
    if dst_src.exists():
        shutil.rmtree(dst_src)
    dst_src.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst_src)

    pyproject = clone_dir / "pyproject.toml"
    if pyproject.is_file():
        shutil.copy2(pyproject, dst_relay / "pyproject.toml")

    write_bin_wrapper(dst_relay / "bin")


def refresh_templates(clone_dir: Path, relay_os: Path) -> list[str]:
    """Refresh `_*` scaffolds under `relay_os/` from the clone."""
    src_root = clone_dir / TEMPLATE_SUBPATH
    if not src_root.is_dir():
        typer.secho(
            f"Upstream layout changed — {TEMPLATE_SUBPATH} not found in clone.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return _copy_templates(src_root, relay_os)


def write_bin_wrapper(bin_dir: Path) -> None:
    """Drop `bin/relay` — execs `python3 -m relay` against the vendored source."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "relay"
    wrapper.write_text(
        '#!/bin/sh\n'
        'set -e\n'
        'HERE="$(cd "$(dirname "$0")/.." && pwd)"\n'
        'PYTHONPATH="${HERE}/src:${PYTHONPATH:-}" exec python3 -m relay "$@"\n'
    )
    wrapper.chmod(0o755)


def _copy_templates(src_root: Path, dst_root: Path) -> list[str]:
    """Copy every `_*` scaffold under `src_root` into `dst_root`.

    Always overwrites; matches nested under another `_*` ancestor are skipped
    so each scaffold is processed once.
    """
    copied: list[str] = []
    for src in src_root.rglob("_*"):
        rel = src.relative_to(src_root)
        if any(part.startswith("_") for part in rel.parts[:-1]):
            continue

        dst = dst_root / rel
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            for f in src.rglob("*"):
                if f.is_file():
                    copied.append(str(f.relative_to(src_root)))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(str(rel))

    return copied
