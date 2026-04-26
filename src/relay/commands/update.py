"""`relay update` — pull the latest CLI + `_template` scaffolds from upstream."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

import typer

from relay.config import find_repo_root


RELAY_REPO_URL = "https://github.com/FastJVM/relay"
TEMPLATE_SUBPATH = Path("src/relay/resources/templates/relay-os")


def update() -> None:
    """Refresh the relay CLI and `_template` scaffolds from upstream."""
    relay_os = find_repo_root()

    with tempfile.TemporaryDirectory(prefix="relay-update-") as tmp:
        clone_dir = Path(tmp) / "repo"

        typer.echo(f"Cloning {RELAY_REPO_URL} (shallow)…")
        result = subprocess.run(
            ["git", "clone", "--depth=1", RELAY_REPO_URL, str(clone_dir)],
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

        upstream_templates = clone_dir / TEMPLATE_SUBPATH
        if not upstream_templates.is_dir():
            typer.secho(
                f"Upstream layout changed — {TEMPLATE_SUBPATH} not found in clone.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)

        copied = _copy_templates(upstream_templates, relay_os)
        _update_cli(clone_dir)

    typer.echo("")
    if copied:
        typer.echo(f"Refreshed {len(copied)} template file(s) in {relay_os}:")
        for rel in copied:
            typer.echo(f"  {rel}")
    else:
        typer.echo("No `_template` files found upstream — nothing to refresh.")


def _copy_templates(src_root: Path, dst_root: Path) -> list[str]:
    """Copy every `_*` scaffold under `src_root` into `dst_root`.

    `_`-prefixed paths are the relay-owned scaffold contract — directories
    are copied wholesale (with everything inside), files are copied verbatim.
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


def _update_cli(clone_dir: Path) -> None:
    """`pip install --upgrade <clone_dir>` to update the relay CLI itself.

    Skipped (with a hint) for editable installs — those track a developer's
    own checkout and shouldn't be clobbered by an upstream pip install.
    """
    if _is_editable_install():
        typer.secho(
            "Editable install detected — skipping CLI update. "
            "Run `git pull` in your relay checkout to update the CLI.",
            fg=typer.colors.YELLOW,
        )
        return

    typer.echo("Upgrading relay CLI from upstream…")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", str(clone_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        typer.secho(
            f"pip install failed:\n{result.stderr}",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)


def _is_editable_install() -> bool:
    try:
        dist = metadata.distribution("relay-os")
    except metadata.PackageNotFoundError:
        return False

    raw = dist.read_text("direct_url.json")
    if not raw:
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return bool(data.get("dir_info", {}).get("editable", False))
