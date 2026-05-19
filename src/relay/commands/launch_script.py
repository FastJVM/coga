"""`relay launch` for `mode: script` — direct script execution, no agent."""

from __future__ import annotations

import os
import subprocess
import sys

import typer

from relay.config import Config
from relay.logfile import append_log
from relay.mark import mark_in_progress
from relay.paths import resolve_skill_path, skill_resolution_paths
from relay.skill import Skill
from relay.slack import post
from relay.tasks import TaskRef
from relay.ticket import Ticket
from relay.validate import TaskValidationError


def run_script_mode(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Execute the script attached to the current workflow step.

    - The current step must have `skill:` set.
    - The skill's SKILL.md frontmatter must have `script: <filename>`.
    - The script runs with secrets from relay.local.toml as env vars.
    - Working directory = the host repo (parent of relay-os/), or repo_root if
      relay.toml lives at the top level.
    - Non-zero exit: task stays at current step; a Slack FYI is posted.
    """
    current = ticket.current_step()
    if not current:
        _bail(f"Task {ref.id_slug} has no current workflow step.")
    skills_refs = list(current.get("skills") or [])
    if not skills_refs:
        _bail(
            f"Step {current['name']!r} has no skills attached. "
            "Script mode requires exactly one skill with a `script:` field."
        )
    if len(skills_refs) > 1:
        _bail(
            f"Step {current['name']!r} has multiple skills; script mode requires "
            f"exactly one skill (got {skills_refs!r})."
        )

    skill_ref = skills_refs[0]
    skill_file = resolve_skill_path(cfg, skill_ref)
    if skill_file is None:
        checked = ", ".join(str(path) for path in skill_resolution_paths(cfg, skill_ref))
        _bail(f"Skill file not found for {skill_ref!r}. Checked: {checked}")
    skill = Skill.load(skill_file)

    if not skill.script:
        _bail(
            f"Skill {skill.name!r} has no `script:` in frontmatter. "
            "Add a script reference to use script mode."
        )

    script_path = skill.dir / skill.script
    if not script_path.is_file():
        _bail(f"Script not found: {script_path}")

    if ticket.status == "active":
        try:
            mark_in_progress(
                cfg,
                ref,
                ticket,
                actor="system",
                log_message="started (active → in_progress) via relay launch",
                slack_text=(
                    f"▶️ script started on *{ref.id_slug}* \"{ticket.title}\" "
                    f"— step {ticket.step}"
                ),
                echo=f"{ref.id_slug}: in_progress",
            )
        except TaskValidationError as exc:
            _bail(str(exc))

    env = os.environ.copy()
    env.update(cfg.secrets)

    # The repo root for relay-os/ inside a host repo is `repo/relay-os`; scripts
    # almost always want the host repo (its parent), so prefer that when present.
    cwd = cfg.repo_root.parent if cfg.repo_root.name == "relay-os" else cfg.repo_root
    env.update(
        {
            "RELAY_TASK_SLUG": ref.id_slug,
            "RELAY_TASK_DIR": str(ref.path.resolve()),
            "RELAY_TASK_TICKET": str((ref.path / "ticket.md").resolve()),
            "RELAY_TASK_BLACKBOARD": str((ref.path / "blackboard.md").resolve()),
            "RELAY_TASK_LOG": str((ref.path / "log.md").resolve()),
            "RELAY_RELAY_OS_ROOT": str(cfg.repo_root.resolve()),
            "RELAY_REPO_ROOT": str(cwd.resolve()),
            "RELAY_SKILL_NAME": skill.name,
            "RELAY_SKILL_DIR": str(skill.dir.resolve()),
        }
    )

    append_log(
        ref.path,
        "system",
        f"launched in script mode (skill={skill.name}, script={skill.script})",
    )

    # Make script executable if needed — POC-friendly.
    if not os.access(script_path, os.X_OK):
        cmd = [sys.executable, str(script_path)] if script_path.suffix == ".py" else ["sh", str(script_path)]
    else:
        cmd = [str(script_path)]

    result = subprocess.run(cmd, env=env, cwd=cwd, check=False)
    exit_code = result.returncode

    append_log(ref.path, "system", f"script exited with code {exit_code}")

    if exit_code != 0:
        post(
            cfg,
            f"💥 script failed on *{ref.id_slug}* \"{ticket.title}\" "
            f"— exit {exit_code}, stuck at step {ticket.step}",
            task_path=ref.path,
        )
        typer.secho(f"Script exited with {exit_code}.", fg=typer.colors.YELLOW, err=True)
        sys.exit(exit_code)

    typer.echo(f"{ref.id_slug}: script ran successfully")


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
