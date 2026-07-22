#!/usr/bin/env python3
"""`coga open-pr <slug>` — push the recorded feature branch and open (or ready) its PR.

Script entry point of the `bootstrap/open-pr` command ticket. `coga open-pr`
is a default alias for `coga launch bootstrap/open-pr <slug>`: a stateless
script launch whose trailing argument arrives as `COGA_ARG_1`. This seam
resolves the target task from the primary control checkout, runs the sibling
`recipe.py`, prints the PR URL, and exits non-zero on any `OpenPrError` —
nothing advances, and the open-pr step's `requires: pr` bump gate stays unmet.

The seam resolves the target task first, then applies its checkout gate. In the
legacy two-checkout layout the command runs from the primary control checkout,
which holds the authoritative ticket, and pushes the `## Dev` branch by name
from the separately recorded worktree — the separation that retires the
cross-worktree divergence trap. When `worktree:` records the primary checkout
itself, that checkout's feature branch holds the *live* ticket, so requiring
the control branch would make the recipe's recorded-branch check impossible to
satisfy; the command runs there instead and the recipe commits its `pr:` write
to that branch.

Proving that ownership needs care here. `coga open-pr` is itself a launch, and
`build_task_env` rewrites `COGA_TASK_*` for the launched target — inside this
script those name the `bootstrap/open-pr` command ticket, not the task being
published. The surviving witness is `COGA_EXPECTED_TASK`, which the *outer*
agent launch pins to its own task path and no nested launch rewrites. Matching
it against the resolved task is what separates a real session from an
independent fallback clone that would otherwise update its stale ticket copy.

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

from pathlib import Path  # noqa: E402

from coga.autoclose import parse_worktree_path  # noqa: E402
from coga.config import Config, ConfigError, load_config  # noqa: E402
from coga.git import is_linked_worktree  # noqa: E402
from coga.repl_supervisor import EXPECTED_TASK_ENV  # noqa: E402
from coga.taskfile import split_body  # noqa: E402
from coga.tasks import TaskNotFoundError, read_ticket, resolve_task  # noqa: E402

from recipe import OpenPrError, open_pr, same_git_checkout  # noqa: E402


def main() -> int:
    task = _target_task_arg()

    try:
        cfg = load_config()
    except ConfigError as exc:
        return _fail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        return _fail(str(exc))

    # read_ticket validates the ticket resolves before we touch git/gh.
    ticket = read_ticket(ref)
    _, blackboard = split_body(ticket.body)

    single_checkout, reason = _checkout_mode(
        cfg,
        recorded_worktree=parse_worktree_path(blackboard or ""),
        task_path=ref.path,
    )
    if reason is not None:
        return _fail(reason)

    try:
        url = open_pr(
            cfg,
            slug=ref.id_slug,
            blackboard_path=ref.ticket_path,
            single_checkout=single_checkout,
        )
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


def _checkout_mode(
    cfg: Config,
    *,
    recorded_worktree: str | None,
    task_path: Path,
) -> tuple[bool, str | None]:
    """Resolve the checkout gate: `(single_checkout, refusal)`.

    Keeps task resolution and blackboard writes on the control checkout, except
    for the one layout where that is impossible: with a single checkout the
    feature-branch ticket *is* the live task-state copy, so demanding the
    control branch would refuse every publish. `owns_live_ticket` is what keeps
    that exception honest — see this module's docstring for why the witness is
    `COGA_EXPECTED_TASK` rather than the `COGA_TASK_*` contract.

    Distinct or unproven checkouts retain the gate that prevents writes to a
    stale ticket copy.
    """
    same_checkout = bool(
        recorded_worktree
        and same_git_checkout(cfg.repo_root, recorded_worktree)
        and not is_linked_worktree(cfg.repo_root)
    )
    launched_task = os.environ.get(EXPECTED_TASK_ENV)
    owns_live_ticket = bool(
        launched_task and Path(launched_task).resolve() == task_path.resolve()
    )
    if same_checkout and owns_live_ticket:
        return True, None

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
        return False, None
    actual = branch or "<unknown>"
    if same_checkout:
        return False, (
            "`coga open-pr` cannot prove that this feature checkout owns the "
            "live ticket. Run it from the task's active `coga launch` session "
            "in the primary checkout, or return to the primary control "
            f"checkout on {cfg.git_control_branch!r}. This guard keeps an "
            "independent fallback clone from updating its stale ticket copy."
        )
    return False, (
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
