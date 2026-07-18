"""Shared execution of the bundled task-deletion skill."""

from __future__ import annotations

import os
import subprocess

from coga.commands.launch_script import (
    build_script_command,
    build_task_env,
    script_repo_root,
)
from coga.config import Config
from coga.paths import resolve_skill_path, skill_resolution_paths
from coga.skill import Skill
from coga.tasks import TaskRef


class DeleteTaskError(RuntimeError):
    """The bundled task-deletion skill could not remove its target."""


def run_delete_task_skill(cfg: Config, ref: TaskRef) -> str:
    """Run the single task-deletion implementation and return its stdout.

    Callers own synchronization. `coga delete` lands the removal immediately;
    recurring replacement recreates the task at the same path and syncs that
    replacement as one state transition.
    """
    skill_file = resolve_skill_path(cfg, "bootstrap/delete-task")
    if skill_file is None:
        checked = ", ".join(
            str(p)
            for p in skill_resolution_paths(cfg, "bootstrap/delete-task")
        )
        raise DeleteTaskError(
            "Delete skill 'bootstrap/delete-task' not found. "
            f"Checked: {checked}. Reinstall or update coga so the packaged "
            "bundled skills are present."
        )
    skill = Skill.load(skill_file)
    if not skill.script:
        raise DeleteTaskError(
            f"Delete skill {skill.name!r} has no `script:` in frontmatter."
        )
    script_path = skill.dir / skill.script
    if not script_path.is_file():
        raise DeleteTaskError(f"Delete skill script not found: {script_path}")

    env = os.environ.copy()
    env.update(build_task_env(cfg, ref, skill))
    result = subprocess.run(
        build_script_command(script_path),
        env=env,
        cwd=script_repo_root(cfg),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"script exited with {result.returncode}"
        raise DeleteTaskError(detail)
    return result.stdout
