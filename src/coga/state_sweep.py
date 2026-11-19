"""The end-of-invocation state sweep, shared by the CLI and edge entrypoints.

This module owns the publication mechanism only: whether an earlier step in
this process withheld or relayed the sweep, reloading the target root's config
at the publication boundary, and the guarded `git.sync_coga_state`. Which
invocations are admitted to sweep at all (argv rules, `--help`, exit 75,
`recurring --all`) stays with each caller.
"""

from __future__ import annotations

from pathlib import Path

import typer

from coga import git
from coga.config import ConfigError, load_config


def sweep_suppressed() -> bool:
    """Whether this process must not run its end-of-invocation sweep.

    A process that relayed a run into the control worktree leaves the sweep to
    that child. A withheld sweep protects local state a command deliberately
    preserved after a refusal; say so, since that state stays unpublished.
    """
    if git.control_relay_started.get():
        return True
    if git.state_sweep_withheld.get():
        typer.secho(
            "[git] state sweep withheld: the command refused before changing "
            "state, or preserved local changes after a refused or failed "
            "publication or checkout return.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return True
    return False


def sweep_root(root: Path) -> None:
    """Publish eligible state under the Coga OS root ``root``; never raises
    for a Git or config failure, so it cannot mask the caller's own result.

    The invocation may have edited `coga.toml` or moved the context tree;
    reload at the publication boundary rather than sweeping a stale root.
    """
    try:
        live_cfg = load_config(root, require_user=False)
    except ConfigError as exc:
        typer.secho(
            f"[git] current config is invalid (state sweep skipped): {exc}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return
    git.sync_coga_state(live_cfg)
