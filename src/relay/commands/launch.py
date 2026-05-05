"""`relay launch` — compose context and start work on a task."""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import typer

from relay.blackboard import blackboard_size_warning
from relay.compose import compose_prompt, write_prompt_file
from relay.config import Config, ConfigError, load_config
from relay.lock import LockHeldError, TaskLock
from relay.logfile import append_log
from relay.scaffold import scaffold_task
from relay.slack import post
from relay.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_target,
    resolve_task,
)
from relay.ticket import Ticket

_LAUNCHABLE_STATUSES = {"draft", "active"}


def launch(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>` shim."),
    title: str = typer.Argument(
        None,
        help="With a bootstrap shim, scaffold a new draft task with this title and launch on it.",
    ),
    agent_override: str | None = typer.Option(
        None,
        "--agent",
        help="Agent nickname to use for this launch instead of the ticket/shim assignee.",
    ),
    force: bool = typer.Option(False, "--force", help="Break a stale lock."),
) -> None:
    """Compose context, start work on a task."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_target(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    is_bootstrap = isinstance(ref, BootstrapRef)
    if agent_override is not None:
        try:
            cfg.agent_type_for(cfg.current_user, agent_override)
        except ConfigError as exc:
            _bail(str(exc))

    # Factory mode: bootstrap shim + title → scaffold a new draft task
    # seeded from the shim's frontmatter, then launch on the new task.
    if title is not None:
        if not is_bootstrap:
            _bail("Title arg is only valid when launching a `bootstrap/<name>` shim.")
        try:
            ref = _scaffold_from_shim(cfg, ref, title, assignee_override=agent_override)
        except (ConfigError, ValueError) as exc:
            _bail(str(exc))
        is_bootstrap = False

    ticket = read_ticket(ref)
    if agent_override is not None and is_bootstrap:
        ticket.frontmatter["assignee"] = agent_override

    # Announce ticket creation when the factory mode just scaffolded one.
    # `title is not None` was the factory-mode signal above; we re-derive
    # it here rather than threading another local because the post needs
    # the read ticket either way.
    if title is not None:
        post(
            cfg,
            f"✨ {cfg.current_user} scaffolded *{ref.id_slug}* "
            f"\"{ticket.title}\" — "
            f"assignee {ticket.assignee or 'unassigned'}",
            task_path=ref.path,
            owner=ticket.owner or cfg.current_user,
        )

    if not is_bootstrap and ticket.status not in _LAUNCHABLE_STATUSES:
        _bail(
            f"Task {ref.id_slug} is {ticket.status!r}. "
            f"Set status to 'draft' or 'active' before launching."
        )

    assignee = ticket.assignee
    if not assignee:
        _bail(f"Task {ref.id_slug} has no assignee")

    mode = ticket.mode

    if mode == "script":
        if agent_override is not None:
            _bail("--agent is only supported for interactive/auto launches.")
        if is_bootstrap:
            _bail("Bootstrap tickets only support interactive/auto modes.")
        from relay.commands.launch_script import run_script_mode
        run_script_mode(cfg, ref, ticket)
        return

    if mode not in ("interactive", "auto"):
        _bail(f"Unknown mode: {mode!r}")

    if mode == "interactive" and not _interactive_stdio_has_tty():
        _bail(
            f"Cannot launch {ref.id_slug!r}: mode=interactive requires a TTY "
            "(stdin and stdout must both be terminals). Run from a real "
            "shell, or change the ticket to mode: auto / mode: script."
        )

    launch_assignee = agent_override or assignee

    # Resolve agent for this launch assignee (under current user's config).
    try:
        agent = cfg.agent_type_for(cfg.current_user, launch_assignee)
    except ConfigError as exc:
        _bail(str(exc))

    # Verify CLI binary exists.
    if shutil.which(agent.cli) is None:
        _bail(f"Agent CLI {agent.cli!r} not found in PATH.")

    # Acquire lock for normal tasks. Bootstrap shims are stateless re-entry
    # points — concurrent launches are fine, no lock to release.
    lock = None if is_bootstrap else TaskLock(ref.path)
    if lock is not None:
        try:
            lock.acquire(holder=launch_assignee, force=force)
        except LockHeldError as exc:
            _bail(
                f"{exc}\nPass --force to break the lock (e.g. after a crashed session)."
            )

    # Launching is the approval gesture: a draft becomes active.
    # Skip for tickets carrying a top-level skill ref (bootstrap-style):
    # the bootstrap skill leaves the new task as `draft` so the human's
    # *next* launch is what approves the real work (spec L611).
    if not is_bootstrap and not ticket.skill and ticket.status == "draft":
        ticket.frontmatter["status"] = "active"
        ticket.write(ref.path / "ticket.md")
        append_log(
            ref.path,
            f"human:{cfg.current_user}",
            "activated (draft → active)",
        )
        post(
            cfg,
            f"🚀 {cfg.current_user} activated *{ref.id_slug}* "
            f"\"{ticket.title}\" — assignee {assignee}"
            f"{_agent_override_note(agent_override, assignee)}",
            task_path=ref.path,
            owner=ticket.owner or cfg.current_user,
        )

    # Inject secrets as env vars.
    env = os.environ.copy()
    env.update(cfg.secrets)

    # Install a signal-safe cleanup.
    prompt_file: Path | None = None

    def _cleanup_prompt() -> None:
        nonlocal prompt_file
        if prompt_file is None:
            return
        try:
            prompt_file.unlink()
        except FileNotFoundError:
            pass
        prompt_file = None

    def _cleanup() -> None:
        if lock is not None:
            lock.release()
        _cleanup_prompt()

    def _on_signal(signum, frame):  # type: ignore[no-untyped-def]
        _cleanup()
        sys.exit(128 + signum)

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    try:
        while True:
            ticket = read_ticket(ref)
            if agent_override is not None and is_bootstrap:
                ticket.frontmatter["assignee"] = agent_override
            _echo_launch_iteration(ref, ticket)

            # Compose & write prompt fresh for this step.
            warning = blackboard_size_warning(ref.path / "blackboard.md")
            if warning:
                typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW, err=True)

            prompt = compose_prompt(cfg, ref, ticket)
            prompt_file = write_prompt_file(prompt, ref)
            cmd = build_agent_command(agent, mode, prompt, prompt_file)

            append_log(
                ref.path,
                f"human:{cfg.current_user}",
                _launch_log_message(
                    mode,
                    ticket.assignee or assignee,
                    launch_assignee,
                    agent.name,
                ),
            )

            try:
                # Interactive: inherit stdio (human sits with agent).
                # Auto: capture nothing, let agent print to our stdout.
                result = subprocess.run(cmd, env=env, check=False)
                exit_code = result.returncode
            except FileNotFoundError:
                _bail(f"Failed to spawn agent: {agent.cli!r} not found.")
            finally:
                _cleanup_prompt()

            if exit_code != 0:
                typer.secho(
                    f"Agent exited with code {exit_code}.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                sys.exit(exit_code)

            if is_bootstrap or ticket.skill:
                break

            updated_ticket = read_ticket(ref)
            stop_reason = _harness_stop_reason(ref, ticket, updated_ticket)
            if stop_reason is not None:
                typer.echo(stop_reason)
                break
    finally:
        _cleanup()


# --- helpers ------------------------------------------------------------------


def _scaffold_from_shim(
    cfg: Config,
    shim: BootstrapRef,
    title: str,
    *,
    assignee_override: str | None = None,
) -> TaskRef:
    """Scaffold a new draft task seeded from a bootstrap shim's frontmatter.

    The shim ticket carries the `mode`, `assignee`, and `skill` ref the new
    task should inherit; the agent will fill in workflow/contexts/description
    during its first launch.
    """
    shim_ticket = read_ticket(shim)
    result = scaffold_task(
        cfg=cfg,
        title=title,
        workflow_name=None,
        contexts=[],
        mode=shim_ticket.mode,
        owner=cfg.current_user,
        assignee=assignee_override or shim_ticket.assignee,
        watchers=[],
        status="draft",
        skill=shim_ticket.skill,
        created_by=f"bootstrap:{shim.name}",
    )
    return resolve_task(cfg, result["slug"])


def build_agent_command(agent, mode: str, prompt: str, prompt_file: Path) -> list[str]:
    """Build the argv for spawning the agent.

    Heuristic: if the configured flag contains "file", pass the prompt-file
    path as the trailing argument; otherwise pass the full prompt text.
    """
    flag_str = agent.interactive if mode == "interactive" else agent.auto
    takes_file = _flag_takes_file(flag_str)
    payload = str(prompt_file) if takes_file else prompt
    cmd = [agent.cli, *shlex.split(flag_str), payload]
    # Interactive launches: kick the agent off so it starts working on the
    # composed context immediately instead of sitting at an empty REPL prompt.
    # Only when the agent takes the prompt as a file — otherwise the prompt
    # itself was already passed positionally as the user turn.
    if mode == "interactive" and takes_file:
        cmd.append("Make it so.")
    return cmd


def _flag_takes_file(flag: str) -> bool:
    return "file" in flag.lower()


def _echo_launch_iteration(ref: TaskRef | BootstrapRef, ticket: Ticket) -> None:
    current = ticket.current_step()
    if current is None:
        typer.echo(f"→ launching {ref.id_slug}")
        return
    typer.echo(f"→ entering step {ticket.step}: {current['name']}")


def _harness_stop_reason(ref: TaskRef, before: Ticket, after: Ticket) -> str | None:
    if after.status != "active":
        if after.status == "done":
            return f"{ref.id_slug}: task is done"
        if after.status == "paused":
            return f"{ref.id_slug}: task is paused"
        return f"{ref.id_slug}: task status is {after.status!r}"

    if (after.step, after.status) == (before.step, before.status):
        current = after.step or "no workflow step"
        return f"{ref.id_slug}: still on {current}; stopping"

    current = after.current_step()
    if current is None:
        return f"{ref.id_slug}: no current workflow step; stopping"

    if not current.get("skill"):
        return f"{ref.id_slug}: next step has no skill — handoff to human"

    if after.assignee != before.assignee:
        return f"{ref.id_slug}: next step assignee changed: {before.assignee} → {after.assignee}"

    return None


def _agent_override_note(agent_override: str | None, assignee: str) -> str:
    if agent_override is None or agent_override == assignee:
        return ""
    return f" (launched with {agent_override})"


def _launch_log_message(
    mode: str,
    assignee: str,
    launch_assignee: str,
    agent_name: str,
) -> str:
    if launch_assignee == assignee:
        return f"launched in {mode} mode (assignee={assignee}, agent={agent_name})"
    return (
        f"launched in {mode} mode "
        f"(assignee={assignee}, launch_assignee={launch_assignee}, agent={agent_name})"
    )


def _interactive_stdio_has_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
