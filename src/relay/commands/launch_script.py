"""`relay launch` for `mode: script` — direct script execution, no agent."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer

from relay.bump import (
    AssigneeResolutionError,
    advance_step,
    resolve_step_assignee,
)
from relay.config import Config, SecretError, select_launch_secrets
from relay.logfile import append_log
from relay.mark import mark_done, mark_in_progress
from relay.paths import resolve_skill_path, skill_resolution_paths
from relay.skill import Skill
from relay.notification import post
from relay.tasks import TaskRef
from relay.ticket import Ticket
from relay.validate import TaskValidationError


def script_repo_root(cfg: Config) -> Path:
    """Working directory for a script run.

    The repo root for `relay-os/` inside a host repo is `repo/relay-os`;
    scripts almost always want the host repo (its parent), so prefer that
    when present.
    """
    return cfg.repo_root.parent if cfg.repo_root.name == "relay-os" else cfg.repo_root


def build_script_env(cfg: Config, ref: TaskRef, skill: Skill) -> dict[str, str]:
    """The `mode: script` task/skill metadata environment contract.

    One definition, two callers: `relay launch` (script mode) and `relay
    delete`, which runs the `bootstrap/delete-task` skill directly against a
    resolved target task. Keeping it shared means the `RELAY_*` variable names
    cannot drift between the two dispatch paths.
    """
    return {
        "RELAY_TASK_SLUG": ref.id_slug,
        "RELAY_TASK_DIR": str(ref.path.resolve()),
        "RELAY_TASK_TICKET": str((ref.path / "ticket.md").resolve()),
        "RELAY_TASK_BLACKBOARD": str((ref.path / "blackboard.md").resolve()),
        "RELAY_TASK_LOG": str((ref.path / "log.md").resolve()),
        "RELAY_RELAY_OS_ROOT": str(cfg.repo_root.resolve()),
        "RELAY_REPO_ROOT": str(script_repo_root(cfg).resolve()),
        "RELAY_SKILL_NAME": skill.name,
        "RELAY_SKILL_DIR": str(skill.dir.resolve()),
    }


def build_script_command(script_path: Path) -> list[str]:
    """argv for running a skill script — honor the executable bit, else
    interpret by suffix. POC-friendly: a non-executable `.py` still runs."""
    if os.access(script_path, os.X_OK):
        return [str(script_path)]
    if script_path.suffix == ".py":
        return [sys.executable, str(script_path)]
    return ["sh", str(script_path)]


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
        cur = ticket.current_step()
        step_note = f" (step {ticket.step_index()}: {cur['name']})" if cur else ""
        try:
            mark_in_progress(
                cfg,
                ref,
                ticket,
                actor="system",
                log_message="started (active → in_progress) via relay launch",
                slack_text=(
                    f"▶️ script started *{ref.id_slug}* "
                    f"\"{ticket.title}\"{step_note}"
                ),
                echo=f"{ref.id_slug}: in_progress",
            )
        except TaskValidationError as exc:
            _bail(str(exc))

    # Same secret chokepoint as agent-mode `relay launch`: script-mode tasks
    # still receive their secrets here (folded in, not dropped), scoped to the
    # ticket's `secrets:` declaration and failing loud on an unset env var.
    env = os.environ.copy()
    try:
        env.update(select_launch_secrets(cfg, ticket.secrets))
    except SecretError as exc:
        _bail(str(exc))
    env.update(build_script_env(cfg, ref, skill))
    cwd = script_repo_root(cfg)

    append_log(
        ref.path,
        "system",
        f"launched in script mode (skill={skill.name}, script={skill.script})",
    )

    cmd = build_script_command(script_path)

    result = subprocess.run(cmd, env=env, cwd=cwd, check=False)
    exit_code = result.returncode

    # A script may legitimately delete its own task directory — the
    # `bootstrap/delete-task` skill run as a `mode: script` step does exactly
    # that. Only record the exit when the directory is still there.
    if ref.path.is_dir():
        append_log(ref.path, "system", f"script exited with code {exit_code}")

    if exit_code != 0:
        cur = ticket.current_step()
        where = f" at step {ticket.step_index()} ({cur['name']})" if cur else ""
        post(
            cfg,
            f"💥 script failed on *{ref.id_slug}* "
            f"\"{ticket.title}\": exit {exit_code}{where}",
            task_path=ref.path,
            owner=ticket.owner or cfg.current_user,
            watchers=ticket.watchers,
        )
        typer.secho(f"Script exited with {exit_code}.", fg=typer.colors.YELLOW, err=True)
        sys.exit(exit_code)

    typer.echo(f"{ref.id_slug}: script ran successfully")

    # A `mode: script` step has no agent to run `relay bump` / `relay mark
    # done`, so the launcher applies the same completion contract itself:
    # advance to the next step, or finish the task when the script completed the
    # final step (or the task has no workflow). Without this the task ran its
    # script and then sat in `in_progress` forever, stalling the recurring scan
    # on the next due task. Skip when the script deleted its own directory (the
    # `bootstrap/delete-task` self-delete case) — there is nothing left to
    # advance.
    if ref.path.is_dir():
        _advance_after_script(cfg, ref, ticket)


def _advance_after_script(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Bump to the next workflow step, or mark the task done after its last."""
    wf = ticket.workflow
    steps = wf.get("steps") if isinstance(wf, dict) else None

    if not steps:
        _mark_script_done(cfg, ref, ticket)
        return

    total = len(steps)
    current_idx = ticket.step_index() or 0
    if current_idx >= total:
        _mark_script_done(cfg, ref, ticket)
        return

    next_step = current_idx + 1
    new_step = steps[next_step - 1]
    new_step_name = new_step["name"]
    prev_step_name = (
        steps[current_idx - 1]["name"] if current_idx >= 1 else f"step {current_idx}"
    )

    role = new_step.get("assignee")
    new_assignee: str | None = None
    if role is not None:
        try:
            resolved = resolve_step_assignee(cfg, ticket, role)
        except AssigneeResolutionError as exc:
            _bail(str(exc))
        if resolved != ticket.assignee:
            new_assignee = resolved
    handoff = f" → assigned to {new_assignee}" if new_assignee else ""

    try:
        advance_step(
            cfg, ref, ticket,
            next_step=next_step,
            new_step_name=new_step_name,
            actor="system",
            log_message=(
                f"advanced to step {next_step} ({new_step_name}){handoff} "
                "after script step"
            ),
            slack_text=(
                f"👉 script advanced *{ref.id_slug}* \"{ticket.title}\": "
                f"{prev_step_name} → {new_step_name} "
                f"(step {next_step}/{total}){handoff}"
            ),
            digest_detail=(
                f"script advanced: {prev_step_name} → {new_step_name} "
                f"(step {next_step}/{total}){handoff}"
            ),
            new_assignee=new_assignee,
            echo=f"{ref.id_slug}: step {next_step} ({new_step_name}){handoff}",
        )
    except TaskValidationError as exc:
        _bail(str(exc))


def _mark_script_done(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    try:
        mark_done(
            cfg, ref, ticket,
            actor="system",
            log_message="completed (final script step ran) via relay launch",
            slack_text=(
                f"✅ script completed *{ref.id_slug}* \"{ticket.title}\""
            ),
            digest_detail="→ done (script)",
            echo=f"{ref.id_slug}: done",
        )
    except TaskValidationError as exc:
        _bail(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
