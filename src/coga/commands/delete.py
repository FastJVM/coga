"""`coga delete` — remove a task directory from the working tree.

Thin entrypoint: resolve the task argument, then dispatch into the
`bootstrap/delete-task` skill, which performs the actual filesystem removal.
That skill is the single implementation of task deletion — it is equally
runnable as a script workflow step. Recovery is via `git restore`.
"""

from __future__ import annotations

import os
import subprocess
import sys

import typer

from coga import git
from coga.commands.launch_script import (
    build_script_command,
    build_script_env,
    script_repo_root,
)
from coga.config import ConfigError, load_config
from coga.paths import resolve_skill_path, skill_resolution_paths
from coga.skill import Skill
from coga.tasks import TaskNotFoundError, resolve_task

DELETE_SKILL_REF = "bootstrap/delete-task"


def delete(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
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

    skill_file = resolve_skill_path(cfg, DELETE_SKILL_REF)
    if skill_file is None:
        checked = ", ".join(str(p) for p in skill_resolution_paths(cfg, DELETE_SKILL_REF))
        _bail(
            f"Delete skill {DELETE_SKILL_REF!r} not found. Checked: {checked}. "
            "Reinstall or update coga so the packaged bundled skills are present."
        )
    skill = Skill.load(skill_file)
    if not skill.script:
        _bail(f"Delete skill {skill.name!r} has no `script:` in frontmatter.")
    script_path = skill.dir / skill.script
    if not script_path.is_file():
        _bail(f"Delete skill script not found: {script_path}")

    # Run the skill's script directly with the `COGA_*` env contract, pointed
    # at the resolved target task. No secrets: deleting a task directory needs
    # none, and secrets flow through the `coga launch` chokepoint only.
    env = os.environ.copy()
    env.update(build_script_env(cfg, ref, skill))

    result = subprocess.run(
        build_script_command(script_path),
        env=env,
        cwd=script_repo_root(cfg),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        typer.echo(result.stdout, nl=False)
    if result.returncode != 0:
        if result.stderr:
            typer.secho(result.stderr, fg=typer.colors.RED, err=True, nl=False)
        sys.exit(result.returncode)

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
    )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
