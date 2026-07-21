"""`coga delete` — remove a task directory from the working tree.

Thin entrypoint: resolve the task argument, then dispatch into the
`bootstrap/delete-task` skill, which performs the actual filesystem removal.
That skill is the single implementation of task deletion — it is equally
runnable as a script workflow step. Recovery is via `git restore`.
"""

from __future__ import annotations

import sys

import typer

from coga import git
from coga.config import ConfigError, load_config
from coga.delete_task import DeleteTaskError, run_delete_task_skill
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
        output = run_delete_task_skill(cfg, ref)
    except DeleteTaskError as exc:
        _bail(str(exc))
    if output:
        typer.echo(output, nl=False)

    # Sync the removal to the control branch, the git analogue of the Slack
    # broadcast every other state mutation posts. Without this, `coga delete`
    # leaves an uncommitted working-tree deletion — the one command that
    # bypassed the sync layer (create/mark/bump/block all call it). The task
    # dir is gone now, so anchor on its still-present parent for git-root
    # resolution while staging the deleted dir itself as the pathspec;
    # `sync_paths` already handles a removed path (it `git rm`s a missing
    # pathspec and drops it from the landed tree).
    git.sync_paths(
        cfg,
        ref.path.parent,
        [ref.path],
        message=f"Ticket: {ref.id_slug} — deleted",
        update_local_control_ref=not keep_control_checkout,
    )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
