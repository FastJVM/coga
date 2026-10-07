"""Offer to install and log in an agent CLI (`claude`, `codex`).

Shared by interactive `coga init` (pick an agent before scaffolding) and
`coga build` (the onboarding launch, when its agent CLI is not on PATH), so a
new user never meets "Agent CLI not found in PATH" as their first step.
Callers decide interactivity; nothing here runs without a printed command and
an explicit yes, and nothing here edits `coga.toml`.

The installer is the vendor's package, never a `curl | sh` script: the brew
cask on macOS, else a global npm package when `npm` is on PATH, else the
manifest's install URL is printed. Install and login argv live in the
`coga.dependencies` manifest.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys

import typer

from coga.dependencies import AGENT_CLIS, DEPENDENCIES, PACKAGE_MANAGERS, Dependency


def _agent_dependency(name: str) -> Dependency | None:
    if name not in AGENT_CLIS:
        return None
    return next((dep for dep in DEPENDENCIES if dep.name == name), None)


def installer_argv(dep: Dependency) -> list[str] | None:
    """The command that installs `dep` on this machine, or None if none fits."""
    if sys.platform == "darwin" and "brew" in dep.packages and shutil.which("brew"):
        manager = "brew"
    elif "npm" in dep.packages and shutil.which("npm"):
        manager = "npm"
    else:
        return None
    return [*PACKAGE_MANAGERS[manager], *dep.packages[manager]]


def offer_agent_cli(name: str) -> bool:
    """Offer to install agent CLI `name`, then to log in; True when on PATH.

    An agent CLI already on PATH returns True without asking. One unknown to
    the manifest, or with no installer on this machine, gets its install URL
    (when known) and returns False. A declined, failed, or not-yet-on-PATH
    install returns False with the reason printed.
    """
    if shutil.which(name) is not None:
        return True
    dep = _agent_dependency(name)
    if dep is None:
        return False
    label = dep.purpose.split(" — ")[0]
    argv = installer_argv(dep)
    if argv is None:
        typer.secho(
            f"`{name}` ({label}) is not installed, and neither brew nor npm is "
            f"available to install it. Install it from {dep.install}, "
            "then re-run.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return False
    typer.echo(f"`{name}` ({label}) is not installed.")
    typer.echo(f"  Will run: {shlex.join(argv)}")
    if not typer.confirm("Install it now?", default=True):
        return False
    result = subprocess.run(argv, check=False)
    if result.returncode != 0:
        typer.secho(
            f"`{shlex.join(argv)}` failed (exit {result.returncode}). "
            f"Install it from {dep.install}, then re-run.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return False
    path = shutil.which(name)
    if path is None:
        typer.secho(
            f"Installed `{name}`, but it is not on PATH yet — open a new "
            "shell, then re-run.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return False
    _offer_login(dep, path)
    return True


def _offer_login(dep: Dependency, path: str) -> None:
    """Offer the manifest's login command for a freshly installed agent CLI."""
    if dep.login is None:
        return
    login = shlex.join([dep.name, *dep.login])
    hint = " (sign in, then exit it to continue)" if not dep.login else ""
    if typer.confirm(f"Run `{login}` now to log in{hint}?", default=True):
        subprocess.run([path, *dep.login], check=False)
