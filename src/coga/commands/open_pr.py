"""`coga open-pr` — push the recorded feature branch and open (or ready) its PR.

A thin wrapper over the `open_pr()` recipe in `coga.open_pr`, the way `coga
delete` wraps its bootstrap skill: the recipe carries the deterministic logic
(read `branch:` / `worktree:` from `## Dev`, confirm the worktree is on that
branch, clean, ahead of and not stale relative to the base, push, open/ready the
PR, write `pr:` back) and this command is the CLI seam.

The command itself runs from the primary control checkout so it resolves and
updates the authoritative ticket. It operates on the `## Dev` feature branch
**by name**, pushing from the recorded worktree rather than the process's own
checkout. That separation retires the cross-worktree divergence trap.

`open-pr` is an ordinary agent step in `code/*` workflows: the agent runs this
command, then `coga bump`. The bump refuses to advance until `pr:` is recorded
(the step's `requires: pr` gate), so a skipped `coga open-pr` is caught
structurally — the exit code is not the gate, the recorded artifact is.
"""

from __future__ import annotations

import subprocess
import sys

import typer

from coga.config import Config, ConfigError, load_config
from coga.open_pr import OpenPrError, open_pr
from coga.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def open_pr_command(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
) -> None:
    """Push the recorded `## Dev` branch and open (or ready) its PR."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    _require_control_checkout(cfg)

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    # read_ticket validates the ticket resolves before we touch git/gh.
    read_ticket(ref)

    try:
        url = open_pr(cfg, slug=ref.id_slug, blackboard_path=ref.ticket_path)
    except OpenPrError as exc:
        _bail(str(exc))

    typer.echo(url)


def _require_control_checkout(cfg: Config) -> None:
    """Keep task resolution and blackboard writes on the control checkout."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(cfg.repo_root),
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    branch = result.stdout.strip() if result.returncode == 0 else ""
    if branch != cfg.git_control_branch:
        actual = branch or "<unknown>"
        _bail(
            "`coga open-pr` must run from the primary control checkout on "
            f"{cfg.git_control_branch!r}, not branch {actual!r}. Return to the "
            "control checkout and rerun it; the command will still push the "
            "recorded feature branch by name."
        )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
