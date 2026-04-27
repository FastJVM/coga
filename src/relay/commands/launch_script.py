"""`relay launch` for `mode: script` — direct script execution, no agent."""

from __future__ import annotations

import os
import subprocess
import sys

import typer

from relay.config import Config
from relay.lock import LockHeldError, TaskLock
from relay.logfile import append_log
from relay.paths import skill_path
from relay.skill import Skill
from relay.slack import post_feed
from relay.tasks import TaskRef
from relay.ticket import Ticket


def run_script_mode(cfg: Config, ref: TaskRef, ticket: Ticket, *, force: bool = False) -> None:
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
    if not current.get("skill"):
        _bail(
            f"Step {current['name']!r} has no skill attached. "
            "Script mode requires a skill with a `script:` field."
        )

    skill_file = skill_path(cfg, current["skill"])
    if not skill_file.is_file():
        _bail(f"Skill file not found: {skill_file}")
    skill = Skill.load(skill_file)

    if not skill.script:
        _bail(
            f"Skill {skill.name!r} has no `script:` in frontmatter. "
            "Add a script reference to use script mode."
        )

    script_path = skill.dir / skill.script
    if not script_path.is_file():
        _bail(f"Script not found: {script_path}")

    # Acquire lock (script mode still single-worker).
    lock = TaskLock(ref.path)
    try:
        lock.acquire(holder=f"script:{skill.name}", force=force)
    except LockHeldError as exc:
        _bail(f"{exc}\nPass --force to break the lock.")

    env = os.environ.copy()
    env.update(cfg.secrets)

    # The repo root for relay-os/ inside a host repo is `repo/relay-os`; scripts
    # almost always want the host repo (its parent), so prefer that when present.
    cwd = cfg.repo_root.parent if cfg.repo_root.name == "relay-os" else cfg.repo_root

    append_log(
        ref.path,
        "system",
        f"launched in script mode (skill={skill.name}, script={skill.script})",
    )
    post_feed(
        cfg,
        f"{ref.id_slug} \"{ticket.title}\" — running {skill.script} (script mode)",
    )

    try:
        # Make script executable if needed — POC-friendly.
        if not os.access(script_path, os.X_OK):
            cmd = [sys.executable, str(script_path)] if script_path.suffix == ".py" else ["sh", str(script_path)]
        else:
            cmd = [str(script_path)]

        result = subprocess.run(cmd, env=env, cwd=cwd, check=False)
        exit_code = result.returncode
    finally:
        lock.release()

    append_log(ref.path, "system", f"script exited with code {exit_code}")

    if exit_code != 0:
        post_feed(
            cfg,
            f"{ref.id_slug} — script exited non-zero (code {exit_code}); "
            f"task stays at step {ticket.step}",
        )
        typer.secho(f"Script exited with {exit_code}.", fg=typer.colors.YELLOW, err=True)
        sys.exit(exit_code)

    typer.echo(f"{ref.id_slug}: script ran successfully")


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
