"""`coga delete` — remove a task directory from the working tree.

Thin entrypoint: resolve the task argument, then call `coga.delete_task`, the
single implementation of task deletion — equally reachable as the registered
`delete-task` recipe. What this command adds on top is the control-branch
sync. Recovery is via `git restore`.
"""

from __future__ import annotations

import sys

import typer

from coga import git
from coga.paths import log_path
from coga.config import ConfigError, load_config
from coga.delete_task import DeleteTaskError, run_delete_task
from coga.tasks import TaskNotFoundError, resolve_task


def delete(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    keep_control_checkout: bool = typer.Option(
        False,
        "--keep-control-checkout",
        help=(
            "From a linked worktree, push the deletion without fast-forwarding "
            "another checkout that holds the control branch. Used by Retro."
        ),
    ),
) -> None:
    """Remove a task directory. Recovery is via `git restore`."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    if keep_control_checkout and not git.is_linked_worktree(ref.path):
        _bail(
            "--keep-control-checkout requires a linked git worktree; refusing "
            "to delete from the primary checkout"
        )

    try:
        output = run_delete_task(cfg, ref)
    except DeleteTaskError as exc:
        _bail(str(exc))
    if output:
        typer.echo(output, nl=False)

    # Sync the removal to the control branch, the git analogue of the Slack
    # broadcast every other state mutation posts. Without this, `coga delete`
    # leaves an uncommitted working-tree deletion — the one command that
    # bypassed the sync layer (create/mark/bump/block all call it). The task
    # dir is gone now; `publish` lands the deletion from the working tree's
    # `git status`, and `fast_forward=False` is Retro's isolated delete: leave
    # the operator's control checkout untouched after the remote landing.
    try:
        git.publish(
            cfg,
            [ref.path, log_path(cfg)],
            f"Ticket: {ref.id_slug} — deleted",
            fast_forward=not keep_control_checkout,
        )
    except git.GitError as exc:
        typer.secho(f"[git] sync failed: {exc}", fg=typer.colors.YELLOW, err=True)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
