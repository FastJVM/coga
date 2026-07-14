"""`coga launch` script dispatch — direct script execution, no agent."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

import typer

from coga.bump import (
    AssigneeResolutionError,
    advance_step,
    resolve_step_assignee,
)
from coga.compose import _extract_section
from coga.config import Config, SecretError, build_launch_env
from coga.logfile import append_log
from coga.mark import StrandedProductCode, mark_done, mark_in_progress
from coga.paths import log_path, resolve_skill_path, skill_resolution_paths
from coga.skill import Skill
from coga.notification import post
from coga.taskfile import split_body
from coga.tasks import TargetRef
from coga.ticket import Ticket
from coga.validate import TaskValidationError


def is_script_launch(cfg: Config, ticket: Ticket) -> bool:
    """True when this launch runs a script instead of spawning an agent.

    Deduced from context, never declared: the current workflow step is a
    script step (`current_step_is_script`), or the ticket carries its own
    `script:` entry (`inline` or a sibling file). Neither → an agent launch.
    """
    return current_step_is_script(cfg, ticket) or bool(ticket.script)


def current_step_is_script(cfg: Config, ticket: Ticket) -> bool:
    """True when the ticket's *current workflow step* is a script step.

    A step runs as a script when it has exactly one skill and that skill's
    SKILL.md declares a `script:` entry — the same rule `_resolve_script` uses to
    pick the step-skill script. This is what lets a workflow interleave a
    deterministic script step (e.g. `code/open-pr`) with agent steps: the
    launch supervisor consults this per step and runs the script itself rather
    than spawning an agent.
    """
    step = ticket.current_step()
    if step is None:
        return False
    skills_refs = list(step.get("skills") or [])
    if len(skills_refs) != 1:
        return False
    sp = resolve_skill_path(cfg, skills_refs[0])
    if sp is None:
        return False
    return bool(Skill.load(sp).script)


def script_repo_root(cfg: Config) -> Path:
    """Working directory for a script run.

    The repo root for `coga/` inside a host repo is `repo/coga`;
    scripts almost always want the host repo (its parent), so prefer that
    when present.
    """
    return cfg.repo_root.parent if cfg.repo_root.name == "coga" else cfg.repo_root


def build_script_env(
    cfg: Config, ref: TargetRef, skill: Skill | None = None
) -> dict[str, str]:
    """The script task/skill metadata environment contract.

    Callers: `coga launch` (a step-skill script or a ticket-owned script) and
    `coga delete`, which runs the `bootstrap/delete-task` skill directly against
    a resolved target task. Keeping it shared means the `COGA_*` variable names
    cannot drift between the dispatch paths. `COGA_SKILL_*` is set only when a
    skill backs the script — a ticket-owned script has no skill, so those vars
    are omitted.
    """
    env = {
        "COGA_TASK_SLUG": ref.id_slug,
        "COGA_TASK_DIR": str((ref.task_dir or ref.path.parent).resolve()),
        "COGA_TASK_TICKET": str((ref.ticket_path).resolve()),
        # Single-file format: the blackboard is the region below the fence in
        # ticket.md, so COGA_TASK_BLACKBOARD and COGA_TASK_TICKET point at the
        # same file. A worker that appends notes to the end still lands them in
        # the blackboard region (it is the last region). COGA_TASK_LOG is the
        # repo-global audit log; workers read it but never write it directly.
        "COGA_TASK_BLACKBOARD": str((ref.ticket_path).resolve()),
        "COGA_TASK_LOG": str(log_path(cfg).resolve()),
        "COGA_COGA_OS_ROOT": str(cfg.repo_root.resolve()),
        "COGA_REPO_ROOT": str(script_repo_root(cfg).resolve()),
    }
    if skill is not None:
        env["COGA_SKILL_NAME"] = skill.name
        env["COGA_SKILL_DIR"] = str(skill.dir.resolve())
    return env


def build_script_command(script_path: Path) -> list[str]:
    """argv for running a skill script.

    Python skill scripts always run under the active Coga interpreter so they
    can import the installed package. Other executable scripts keep their
    shebang behavior; non-executable scripts fall back to `sh`.
    """
    if script_path.suffix == ".py":
        return [sys.executable, str(script_path)]
    if os.access(script_path, os.X_OK):
        return [str(script_path)]
    return ["sh", str(script_path)]


def run_script_mode(
    cfg: Config, ref: TargetRef, ticket: Ticket, *, stateless: bool = False
) -> None:
    """Execute the task's script — a step skill's, or the ticket's own.

    Dispatch (see `is_script_launch`):
    - The current step has a single skill whose SKILL.md declares `script:` →
      run that skill's script.
    - Otherwise the ticket declares `script:` → run the ticket's own script,
      either `inline` (the fenced block in the body's `## Script` section) or a
      sibling file in the task directory.

    The script runs with secrets from coga.local.toml as env vars. Working
    directory = the host repo (parent of coga/), or repo_root if coga.toml
    lives at the top level. Non-zero exit: task stays at current step; a Slack
    FYI is posted.

    `stateless=True` is for package-backed bootstrap script targets such as
    `bootstrap/recurring-scan`: resolve and run the same script shape, but skip
    task lifecycle writes because there is no task.
    """
    skill, cmd, log_label, cleanup = _resolve_script(cfg, ref, ticket)

    # Preflight and build the child env before mutating ticket state. A missing
    # declared secret is a launch refusal, not a started script task.
    try:
        env = build_launch_env(cfg, ticket.secrets)
    except SecretError as exc:
        cleanup()
        _bail(str(exc))

    if not stateless and ticket.status == "active":
        cur = ticket.current_step()
        step_note = f" (step {ticket.step_index()}: {cur['name']})" if cur else ""
        try:
            mark_in_progress(
                cfg,
                ref,
                ticket,
                actor="system",
                log_message="started (active → in_progress) via coga launch",
                slack_text=(
                    f"▶️ script started *{ref.id_slug}* "
                    f"\"{ticket.title}\"{step_note}"
                ),
                echo=f"{ref.id_slug}: in_progress",
            )
        except TaskValidationError as exc:
            cleanup()
            _bail(str(exc))

    # Same secret chokepoint as agent-mode `coga launch`: a script task still
    # receives its scoped secrets here (folded in, not dropped).
    env.update(build_script_env(cfg, ref, skill))
    cwd = script_repo_root(cfg)

    if not stateless:
        append_log(cfg, ref.id_slug, "system", f"launched as a script ({log_label})")

    try:
        result = subprocess.run(cmd, env=env, cwd=cwd, check=False)
    finally:
        cleanup()
    exit_code = result.returncode

    # A script may legitimately delete its own task — the `bootstrap/delete-task`
    # skill run as a script step does exactly that. The task still exists iff its
    # ticket file is on disk (file- or directory-form), so key the post-run
    # bookkeeping off that rather than the directory.
    if not stateless and ref.ticket_path.exists():
        append_log(cfg, ref.id_slug, "system", f"script exited with code {exit_code}")

    if exit_code != 0:
        if stateless:
            typer.secho(
                f"Script exited with {exit_code}.", fg=typer.colors.YELLOW, err=True
            )
            sys.exit(exit_code)
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
    if stateless:
        return

    # A script has no agent to run `coga bump` / `coga mark done`, so the
    # launcher applies the same completion contract itself: advance to the next
    # step, or finish the task when the script completed the final step (or the
    # task has no workflow). Without this the task ran its script and then sat in
    # `in_progress` forever, stalling the recurring scan on the next due task.
    # Skip when the script deleted its own task (the `bootstrap/delete-task`
    # self-delete case) — there is nothing left to advance.
    #
    # RE-READ the ticket first. In the single-file format the script likely just
    # appended to the blackboard region of this same `ticket.md` (via
    # `COGA_TASK_BLACKBOARD`). The status/step write below renders a `Ticket`
    # back to disk, and a `Ticket` held since before the script ran carries a
    # stale `body` — writing it would clobber the script's append. A fresh read
    # picks up the script's blackboard edit; the frontmatter the writers mutate
    # (status / step) is unchanged by the script, so nothing is lost.
    if ref.ticket_path.exists():
        _advance_after_script(cfg, ref, Ticket.read(ref.ticket_path))


def _resolve_script(
    cfg: Config, ref: TargetRef, ticket: Ticket
) -> tuple[Skill | None, list[str], str, "Callable[[], None]"]:
    """Resolve the concrete script to run and how to launch it.

    Returns `(skill_or_none, argv, log_label, cleanup)`. `skill` is set only for
    a step-skill script (None for a ticket-owned script). `cleanup` removes any
    temp file written for an inline script; it is a no-op otherwise and is safe
    to call exactly once after the run (or on any early bail).
    """
    step = ticket.current_step()
    if step is not None:
        skills_refs = list(step.get("skills") or [])
        if len(skills_refs) == 1:
            sp = resolve_skill_path(cfg, skills_refs[0])
            if sp is not None and Skill.load(sp).script:
                return _resolve_skill_script(cfg, skills_refs[0])

    # No step skill carries a script — fall back to the ticket's own `script:`.
    if not ticket.script:
        _bail(
            f"Task {ref.id_slug} has no script to run: neither the current "
            "workflow step's skill nor the ticket declares a `script:`."
        )
    return _resolve_ticket_script(ref, ticket)


def _resolve_skill_script(
    cfg: Config, skill_ref: str
) -> tuple[Skill, list[str], str, "Callable[[], None]"]:
    skill_file = resolve_skill_path(cfg, skill_ref)
    if skill_file is None:
        checked = ", ".join(str(path) for path in skill_resolution_paths(cfg, skill_ref))
        _bail(f"Skill file not found for {skill_ref!r}. Checked: {checked}")
    skill = Skill.load(skill_file)
    if not skill.script:
        _bail(
            f"Skill {skill.name!r} has no `script:` in frontmatter. "
            "Add a script reference to run it as a script."
        )
    script_path = skill.dir / skill.script
    if not script_path.is_file():
        _bail(f"Script not found: {script_path}")
    return (
        skill,
        build_script_command(script_path),
        f"skill={skill.name}, script={skill.script}",
        lambda: None,
    )


def _resolve_ticket_script(
    ref: TargetRef, ticket: Ticket
) -> tuple[None, list[str], str, "Callable[[], None]"]:
    """Resolve the ticket's own `script:` — an inline block or a sibling file."""
    spec = ticket.script
    if spec == "inline":
        return _resolve_inline_script(ref, ticket)

    # A `script: <filename>` entry names a sibling file; that needs directory
    # form (a self-contained file-form task has nowhere to put siblings).
    if ref.task_dir is None:
        _bail(
            f"Task {ref.id_slug} declares `script: {spec}` but is in single-file "
            "form, which has no companion directory to hold the script file. "
            "Convert it to directory form (tasks/<slug>/ticket.md) so the script "
            "can live beside it."
        )
    script_path = ref.task_dir / spec
    if not script_path.is_file():
        _bail(f"Ticket script not found: {script_path}")
    return (
        None,
        build_script_command(script_path),
        f"ticket-script={spec}",
        lambda: None,
    )


_FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)\n```", re.DOTALL)


def _resolve_inline_script(
    ref: TargetRef, ticket: Ticket
) -> tuple[None, list[str], str, "Callable[[], None]"]:
    """Run the fenced code block in the body's `## Script` section.

    The body above the blackboard fence carries the `## Script` section; we pull
    its first ```` ```<lang> ```` block, write it to a temp file, and run it via
    the interpreter named by `<lang>` (default `bash`). `python`/`py` route
    through the current interpreter; everything else is treated as a shell.
    """
    body_above, _ = split_body(ticket.body, blackboard_required=False)
    section = _extract_section(body_above, "Script")
    if not section:
        _bail(
            f"Task {ref.id_slug} declares `script: inline` but its body has no "
            "`## Script` section."
        )
    match = _FENCE_RE.search(section)
    if match is None:
        _bail(
            f"Task {ref.id_slug} `## Script` section has no fenced code block to "
            "run."
        )
    lang = (match.group(1) or "").strip().lower() or "bash"
    code = match.group(2)

    if lang in ("python", "py"):
        suffix, interpreter = ".py", [sys.executable]
    else:
        # Everything else runs as a shell script. `sh` honors an `sh` fence;
        # `bash` (and the default) use bash.
        suffix, interpreter = ".sh", ["sh" if lang == "sh" else "bash"]

    fd, tmp_name = tempfile.mkstemp(
        prefix=f"coga-script-{ref.id_slug.replace('/', '-')}-", suffix=suffix
    )
    tmp = Path(tmp_name)
    with os.fdopen(fd, "w") as fh:
        fh.write(code if code.endswith("\n") else code + "\n")

    def _cleanup() -> None:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass

    return (
        None,
        [*interpreter, str(tmp)],
        f"inline-script ({lang})",
        _cleanup,
    )


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
            log_message="completed (final script step ran) via coga launch",
            slack_text=(
                f"✅ script completed *{ref.id_slug}* \"{ticket.title}\""
            ),
            digest_detail="→ done (script)",
            echo=f"{ref.id_slug}: done",
        )
    except StrandedProductCode as exc:
        # No `_NO_PR_WORKFLOWS` member runs as a script today, so this is
        # currently unreachable — but the guard set is meant to grow. Surface
        # the strand loudly (as the interactive `mark done` does) instead of
        # letting it escape as a traceback from an unattended script launch.
        listed = "\n".join(f"    {p}" for p in exc.paths)
        _bail(
            f"Cannot finish {ref.id_slug}: its {exc.workflow_name} workflow has "
            f"no push/PR step, but this checkout committed tracked product code "
            f"not on the control branch:\n{listed}\n"
            f"Move it to a code/* workflow so it opens a PR."
        )
    except TaskValidationError as exc:
        _bail(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
