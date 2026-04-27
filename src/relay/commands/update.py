"""Bootstrap helpers used by `relay init` (with or without --update).

Pulls upstream into `relay-os/.relay/` and stands up the self-contained venv
the vendored CLI runs out of. No Typer commands live here.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer


RELAY_REPO_URL = "https://github.com/FastJVM/relay"
TEMPLATE_SUBPATH = Path("src/relay/resources/templates/relay-os")
CLI_SRC_SUBPATH = Path("src/relay")


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


def upstream_sha(clone_dir: Path) -> str | None:
    """Return the HEAD SHA of `clone_dir`, or None if `git rev-parse` fails."""
    result = subprocess.run(
        ["git", "-C", str(clone_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def write_pin(relay_os: Path, sha: str | None) -> Path | None:
    """Record the upstream commit `relay-os/.relay/` was vendored from.

    Skips the write if `sha` is None (clone-without-git in tests, mostly).
    Returns the pin path on success.
    """
    if sha is None:
        return None
    pin = relay_os / ".relay" / "RELAY_PIN"
    pin.parent.mkdir(parents=True, exist_ok=True)
    pin.write_text(f"{RELAY_REPO_URL}\n{sha}\n")
    return pin


def read_pin(relay_os: Path) -> str | None:
    """Return the pinned upstream SHA from `.relay/RELAY_PIN`, or None if absent/garbled."""
    pin = relay_os / ".relay" / "RELAY_PIN"
    if not pin.is_file():
        return None
    lines = [line.strip() for line in pin.read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return lines[1]


def refresh_cli(clone_dir: Path, relay_os: Path) -> None:
    """Replace `relay-os/.relay/src/relay/` (+ pyproject + requirements) from the clone."""
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

    for fname in ("pyproject.toml", "requirements.txt"):
        upstream_file = clone_dir / fname
        if upstream_file.is_file():
            shutil.copy2(upstream_file, dst_relay / fname)


def refresh_templates(clone_dir: Path, relay_os: Path) -> list[str]:
    """Refresh relay-owned scaffolds under `relay_os/` from the clone.

    Two trees are treated as upstream-owned (always overwritten on update):
      - `_*` template scaffolds (`_template/` etc.)
      - `bootstrap/` shims — these are infra, not user content.
    """
    src_root = clone_dir / TEMPLATE_SUBPATH
    if not src_root.is_dir():
        typer.secho(
            f"Upstream layout changed — {TEMPLATE_SUBPATH} not found in clone.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    copied = _copy_templates(src_root, relay_os)
    copied.extend(_copy_bootstrap(src_root, relay_os))
    return copied


def write_bin_wrapper(bin_dir: Path) -> None:
    """Drop `bin/relay` — a relative symlink to the venv's `relay` console script.

    Resolved chain at runtime: `<.relay>/bin/relay` → `<.relay>/.venv/bin/relay`,
    whose pip-generated shebang points at `<.relay>/.venv/bin/python`. Works even
    when `bin/relay` itself is reached via another symlink (e.g. `~/.local/bin`).
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "relay"
    if wrapper.exists() or wrapper.is_symlink():
        wrapper.unlink()
    wrapper.symlink_to(Path("..") / ".venv" / "bin" / "relay")


def install_venv(relay_os: Path) -> Path:
    """Create `.relay/.venv/` and `pip install` the vendored relay package into it.

    Idempotent: re-running upgrades the venv in place. Returns the venv path.
    Exits with a clear error if Python venv/pip aren't usable.
    """
    dst_relay = relay_os / ".relay"
    venv_dir = dst_relay / ".venv"
    pyproject = dst_relay / "pyproject.toml"
    if not pyproject.is_file():
        typer.secho(
            f"Cannot bootstrap venv: missing {pyproject}.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    if not (venv_dir / "bin" / "python").is_file():
        typer.echo(f"Creating venv at {venv_dir}…")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            typer.secho(
                f"venv creation failed:\n{result.stderr}",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)

    typer.echo("Installing vendored CLI into venv (pip install)…")
    result = subprocess.run(
        [
            str(venv_dir / "bin" / "python"),
            "-m", "pip", "install",
            "--quiet", "--upgrade",
            str(dst_relay),
        ],
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
    return venv_dir


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


def _copy_bootstrap(src_root: Path, dst_root: Path) -> list[str]:
    """Refresh every file under `bootstrap/` from upstream.

    Bootstrap shims are part of the relay infra (launch entry points for
    relay-owned skills), not user content — same overwrite semantics as
    `_*` scaffolds. Files only present locally (custom shims) are kept.
    """
    src_bootstrap = src_root / "bootstrap"
    if not src_bootstrap.is_dir():
        return []
    copied: list[str] = []
    for src in src_bootstrap.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(rel))
    return copied
