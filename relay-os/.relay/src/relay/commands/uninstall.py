"""`relay uninstall` — the symmetric inverse of `relay init`.

`relay init` writes a self-contained relay footprint into a host repo: the
`relay-os/` tree (with its own vendored venv), agent skill symlinks, root-level
`CLAUDE.md`/`AGENTS.md` orientation guides, a relay-managed `.gitignore` block,
a `~/.local/bin/relay` shim, and the global `relay-os` pip/pipx package.
`relay uninstall` removes that footprint so trying Relay is a reversible
decision.

By default it removes everything *local to this repo* (plus the machine-global
shim that points back at it) and prints the one command to drop the global pip
package. `--purge` also runs that package uninstall. Destructive, so it prints
the plan and asks for confirmation unless `--yes` is passed.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import typer

from relay.commands.init import AGENT_GUIDE_TEMPLATE, _AGENT_GUIDE_FILES
from relay.commands.update import (
    HOST_GITIGNORE_BEGIN,
    RELAY_PIPX_PACKAGE,
    RELAY_REPO_URL,
    remove_host_gitignore,
    running_cli_location,
)
from relay.config import ConfigError, find_repo_root


# Agent skill links init wires up: `<target>/<dir>/skills/relay` symlinks.
_AGENT_SKILL_DIRS: tuple[str, ...] = (".claude", ".codex")

# Suffix for backing up a CLAUDE.md/AGENTS.md the user has edited away from the
# shipped template, rather than deleting their work.
_GUIDE_BACKUP_SUFFIX = ".relay-bak"


@dataclass
class _Plan:
    """What `relay uninstall` is about to do, gathered before any deletion so we
    can show it and confirm. Each list holds host-relative display strings."""

    target: Path
    relay_os: Path | None = None
    skill_links: list[Path] = field(default_factory=list)
    guides_remove: list[Path] = field(default_factory=list)
    guides_backup: list[Path] = field(default_factory=list)
    shim: Path | None = None
    gitignore: bool = False

    def is_empty(self) -> bool:
        return not (
            self.relay_os
            or self.skill_links
            or self.guides_remove
            or self.guides_backup
            or self.shim
            or self.gitignore
        )


def uninstall(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt (for scripted use).",
    ),
    purge: bool = typer.Option(
        False,
        "--purge",
        help=(
            "Also uninstall the global `relay-os` pip/pipx package — this removes "
            "`relay` for every repo on the machine, not just this one. Without it, "
            "the command prints the uninstall command for you to run."
        ),
    ),
) -> None:
    """Remove this repo's Relay footprint (and optionally the global package)."""
    try:
        relay_os = find_repo_root()
    except ConfigError as exc:
        _bail(str(exc))

    # `find_repo_root` returns either a `relay-os/` dir or a repo root that has a
    # `relay.toml` directly. Uninstall only knows how to undo the standard
    # init layout (a `relay-os/` subdir); refuse anything else loudly.
    if relay_os.name != "relay-os":
        _bail(
            f"{relay_os} doesn't look like a `relay init` layout (expected a "
            "`relay-os/` directory). Refusing to guess what to remove."
        )
    target = relay_os.parent

    plan = _build_plan(target, relay_os)
    if plan.is_empty() and not purge:
        typer.echo("Nothing to remove — no Relay footprint found in this repo.")
        return

    _print_plan(target, relay_os, plan, purge)

    if not yes:
        typer.echo("")
        if not typer.confirm("Remove the above?", default=False):
            typer.echo("Aborted — nothing was removed.")
            raise typer.Exit(0)

    typer.echo("")
    _execute_plan(plan)
    _handle_package(purge, relay_os)
    typer.echo("")
    typer.echo("Relay uninstalled. Thanks for trying it.")


def _build_plan(target: Path, relay_os: Path) -> _Plan:
    """Inspect the repo and record exactly what exists to remove. Reads only."""
    plan = _Plan(target=target)

    if relay_os.is_dir():
        plan.relay_os = relay_os

    for dirname in _AGENT_SKILL_DIRS:
        link = target / dirname / "skills" / "relay"
        if link.is_symlink():
            plan.skill_links.append(link)

    for name in _AGENT_GUIDE_FILES:
        path = target / name
        if not path.is_file():
            continue
        try:
            modified = path.read_text() != AGENT_GUIDE_TEMPLATE
        except OSError:
            modified = True
        if modified:
            plan.guides_backup.append(path)
        else:
            plan.guides_remove.append(path)

    shim = _relay_shim(relay_os)
    if shim is not None:
        plan.shim = shim

    plan.gitignore = _has_managed_gitignore(target)
    return plan


def _print_plan(target: Path, relay_os: Path, plan: _Plan, purge: bool) -> None:
    def rel(path: Path) -> str:
        try:
            return str(path.relative_to(target))
        except ValueError:
            return str(path)

    typer.echo(f"Uninstalling Relay from {target}:")
    if plan.relay_os:
        typer.echo(f"  - remove {rel(plan.relay_os)}/ (the whole Relay tree + vendored venv)")
    for link in plan.skill_links:
        typer.echo(f"  - unlink {rel(link)} (agent skill discovery)")
    for path in plan.guides_remove:
        typer.echo(f"  - remove {rel(path)} (unmodified Relay orientation guide)")
    for path in plan.guides_backup:
        typer.echo(
            f"  - back up {rel(path)} → {rel(path)}{_GUIDE_BACKUP_SUFFIX} "
            f"(you edited it; keeping a copy)"
        )
    if plan.gitignore:
        typer.echo(f"  - strip the relay-managed block from {rel(target / '.gitignore')}")
    if plan.shim:
        typer.echo(f"  - remove the `relay` shim at {plan.shim}")

    if purge:
        kind, _ = running_cli_location(relay_os)
        if kind == "vendored":
            typer.echo(
                "  - (--purge) the running `relay` is this repo's vendored copy, "
                "removed with relay-os/ — nothing else to uninstall"
            )
        else:
            typer.echo(f"  - (--purge) uninstall the global `{RELAY_PIPX_PACKAGE}` package")


def _execute_plan(plan: _Plan) -> None:
    if plan.relay_os:
        try:
            shutil.rmtree(plan.relay_os)
        except FileNotFoundError:
            pass
        except OSError as exc:
            _bail(f"Failed to remove {plan.relay_os}: {exc}")
        if plan.relay_os.exists():
            _bail(f"Failed to remove {plan.relay_os}: path still exists")
        typer.echo(f"Removed {plan.relay_os}/")

    for link in plan.skill_links:
        _remove_skill_link(link)

    for path in plan.guides_remove:
        try:
            path.unlink()
            typer.echo(f"Removed {path.name}")
        except OSError:
            pass
    for path in plan.guides_backup:
        backup = path.with_name(path.name + _GUIDE_BACKUP_SUFFIX)
        try:
            path.replace(backup)
            typer.echo(f"Backed up {path.name} → {backup.name}")
        except OSError:
            pass

    if plan.gitignore and remove_host_gitignore(plan.target):
        typer.echo("Stripped the relay-managed block from .gitignore")

    if plan.shim:
        try:
            plan.shim.unlink()
            typer.echo(f"Removed shim {plan.shim}")
        except OSError:
            pass


def _remove_skill_link(link: Path) -> None:
    """Unlink an agent skill symlink and prune the now-empty `skills/` and
    agent dir it lived in, leaving any user content alone."""
    try:
        link.unlink()
    except OSError:
        return
    typer.echo(f"Unlinked {link}")
    skills_dir = link.parent
    agent_dir = skills_dir.parent
    for d in (skills_dir, agent_dir):
        try:
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
        except OSError:
            break


def _handle_package(purge: bool, relay_os: Path) -> None:
    """Drop the global pip/pipx package on --purge, or print the command."""
    if not purge:
        typer.echo("")
        typer.echo(
            f"The global `{RELAY_PIPX_PACKAGE}` package is left installed. To "
            f"remove it for every repo on this machine, run one of:"
        )
        typer.echo(f"    pipx uninstall {RELAY_PIPX_PACKAGE}")
        typer.echo(f"    pip uninstall {RELAY_PIPX_PACKAGE}")
        typer.echo("(or re-run `relay uninstall --purge` from another Relay repo).")
        return

    kind, _ = running_cli_location(relay_os)
    if kind == "vendored":
        typer.echo(
            "Running `relay` is this repo's vendored copy; "
            "no global package to uninstall."
        )
        return

    if kind == "pipx":
        pipx = shutil.which("pipx")
        if pipx is None:
            typer.secho(
                f"Couldn't find pipx on PATH. Remove the global package by hand:\n"
                f"    pipx uninstall {RELAY_PIPX_PACKAGE}\n"
                f"(installed however you set Relay up — see {RELAY_REPO_URL}).",
                fg=typer.colors.YELLOW,
            )
            return
        typer.echo(f"Uninstalling global package (pipx uninstall {RELAY_PIPX_PACKAGE})…")
        result = subprocess.run(
            [pipx, "uninstall", RELAY_PIPX_PACKAGE],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            typer.echo(f"Uninstalled `{RELAY_PIPX_PACKAGE}` via pipx.")
            return
        typer.secho(
            f"pipx uninstall failed — remove it by hand:\n"
            f"    pip uninstall {RELAY_PIPX_PACKAGE}\n"
            f"{(result.stderr or result.stdout).strip()}",
            fg=typer.colors.YELLOW,
        )
        return

    typer.echo(
        f"Uninstalling global package ({sys.executable} -m pip uninstall -y "
        f"{RELAY_PIPX_PACKAGE})…"
    )
    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", RELAY_PIPX_PACKAGE],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        typer.echo(f"Uninstalled `{RELAY_PIPX_PACKAGE}` via pip.")
        return
    typer.secho(
        f"pip uninstall failed — remove it by hand:\n"
        f"    {sys.executable} -m pip uninstall {RELAY_PIPX_PACKAGE}\n"
        f"{(result.stderr or result.stdout).strip()}",
        fg=typer.colors.YELLOW,
    )


def _has_managed_gitignore(target: Path) -> bool:
    """True iff `<target>/.gitignore` carries a relay-managed block."""
    gi = target / ".gitignore"
    if not gi.is_file():
        return False
    try:
        return HOST_GITIGNORE_BEGIN in gi.read_text()
    except OSError:
        return False


def _relay_shim(relay_os: Path) -> Path | None:
    """The `~/.local/bin/relay` shim iff it's a symlink pointing back into this
    repo's `.relay/` (so we never remove an unrelated `relay` on PATH)."""
    shim = Path.home() / ".local" / "bin" / "relay"
    if not shim.is_symlink():
        return None
    dot_relay = (relay_os / ".relay").resolve()
    try:
        resolved = shim.resolve(strict=False)
    except OSError:
        return None
    if resolved == dot_relay or dot_relay in resolved.parents:
        return shim
    return None


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
