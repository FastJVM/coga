#!/usr/bin/env python3
"""`coga open-pr <slug>` — push the recorded feature branch and open (or ready) its PR.

Script entry point of the `bootstrap/open-pr` command ticket. `coga open-pr`
is a default alias for `coga launch bootstrap/open-pr <slug>`: a stateless
script launch whose trailing argument arrives as `COGA_ARG_1`. This seam
resolves the target task from the primary control checkout, runs the sibling
`recipe.py`, prints the PR URL, and exits non-zero on any `OpenPrError` —
nothing advances, and the open-pr step's `requires: pr` bump gate stays unmet.

The command runs from the primary control checkout so it resolves and updates
the authoritative ticket. It operates on the `## Dev` feature branch **by
name**, pushing from the recorded worktree rather than the process's own
checkout. That separation retires the cross-worktree divergence trap.

Coga runs a command-ticket script as `python <ticket-dir>/run.py`, so
`sys.path[0]` is already this directory; the explicit insert below makes the
sibling import resolve the same way when a test loads this file via
`spec_from_file_location` (where `sys.path[0]` is not this directory).
"""

from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import typer  # noqa: E402

from coga.config import Config, ConfigError, load_config  # noqa: E402
from coga.tasks import TaskNotFoundError, read_ticket, resolve_task  # noqa: E402

from recipe import OpenPrError, open_pr  # noqa: E402


def main() -> int:
    task = _target_task_arg()

    try:
        cfg = load_config()
    except ConfigError as exc:
        return _fail(str(exc))

    reason = _control_checkout_refusal(cfg)
    if reason is not None:
        return _fail(reason)

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        return _fail(str(exc))

    # read_ticket validates the ticket resolves before we touch git/gh.
    read_ticket(ref)

    try:
        url = open_pr(cfg, slug=ref.id_slug, blackboard_path=ref.ticket_path)
    except OpenPrError as exc:
        return _fail(str(exc))

    typer.echo(url)
    return 0


def _target_task_arg() -> str:
    """The task ref from the launch arg channel, or a usage failure."""
    argc = int(os.environ.get("COGA_ARGC", "0") or "0")
    task = os.environ.get("COGA_ARG_1", "").strip()
    if argc != 1 or not task:
        typer.secho(
            "Usage: coga open-pr <task> (= coga launch bootstrap/open-pr "
            "<task>) — exactly one task ref is required; it arrives as "
            f"COGA_ARG_1 (got {argc} argument(s)).",
            fg=typer.colors.RED,
            err=True,
        )
        raise SystemExit(2)
    return task


def _control_checkout_refusal(cfg: Config) -> str | None:
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
    if branch == cfg.git_control_branch:
        return None
    actual = branch or "<unknown>"
    return (
        "`coga open-pr` must run from the primary control checkout on "
        f"{cfg.git_control_branch!r}, not branch {actual!r}. Return to the "
        "control checkout and rerun it; the command will still push the "
        "recorded feature branch by name."
    )


def _fail(msg: str) -> int:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
