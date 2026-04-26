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

from relay.commands.common import not_implemented
from relay.compose import compose_prompt, write_prompt_file
from relay.config import Config, ConfigError, load_config
from relay.lock import LockHeldError, TaskLock
from relay.logfile import append_log
from relay.slack import post_feed
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def launch(
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
    force: bool = typer.Option(False, "--force", help="Break a stale lock."),
) -> None:
    """Compose context, start work on a task."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)

    if ticket.status != "active":
        _bail(
            f"Task {ref.id_slug} is {ticket.status!r}. "
            f"Set status to 'active' before launching."
        )

    assignee = ticket.assignee
    if not assignee:
        _bail(f"Task {ref.id_slug} has no assignee")

    mode = ticket.mode

    if mode == "script":
        from relay.commands.launch_script import run_script_mode
        run_script_mode(cfg, ref, ticket)
        return

    if mode not in ("interactive", "auto"):
        _bail(f"Unknown mode: {mode!r}")

    # Resolve agent for this assignee (under current user's config).
    try:
        agent = cfg.agent_type_for(cfg.current_user, assignee)
    except ConfigError as exc:
        _bail(str(exc))

    # Verify CLI binary exists.
    if shutil.which(agent.cli) is None:
        _bail(f"Agent CLI {agent.cli!r} not found in PATH.")

    # Acquire lock.
    lock = TaskLock(ref.path)
    try:
        lock.acquire(holder=assignee, force=force)
    except LockHeldError as exc:
        _bail(
            f"{exc}\nPass --force to break the lock (e.g. after a crashed session)."
        )

    # Compose & write prompt.
    prompt = compose_prompt(cfg, ref, ticket)
    prompt_file = write_prompt_file(prompt, ref)

    cmd = build_agent_command(agent, mode, prompt, prompt_file)

    # Inject secrets as env vars.
    env = os.environ.copy()
    env.update(cfg.secrets)

    # Log + notify.
    append_log(
        ref.path,
        f"human:{cfg.current_user}",
        f"launched in {mode} mode (assignee={assignee}, agent={agent.name})",
    )
    post_feed(
        cfg,
        f"{cfg.current_user}'s {assignee} started work on "
        f"{ref.id_slug} \"{ticket.title}\" ({mode})",
    )

    # Install a signal-safe cleanup.
    def _cleanup() -> None:
        lock.release()
        try:
            prompt_file.unlink()
        except FileNotFoundError:
            pass

    def _on_signal(signum, frame):  # type: ignore[no-untyped-def]
        _cleanup()
        sys.exit(128 + signum)

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    try:
        # Interactive: inherit stdio (human sits with agent).
        # Auto: capture nothing, let agent print to our stdout.
        result = subprocess.run(cmd, env=env, check=False)
        exit_code = result.returncode
    except FileNotFoundError:
        _cleanup()
        _bail(f"Failed to spawn agent: {agent.cli!r} not found.")
    finally:
        _cleanup()

    if exit_code != 0:
        typer.secho(f"Agent exited with code {exit_code}.", fg=typer.colors.YELLOW, err=True)
        sys.exit(exit_code)


# --- helpers ------------------------------------------------------------------


def build_agent_command(agent, mode: str, prompt: str, prompt_file: Path) -> list[str]:
    """Build the argv for spawning the agent.

    Heuristic: if the configured flag contains "file", pass the prompt-file
    path as the trailing argument; otherwise pass the full prompt text.
    """
    flag_str = agent.interactive if mode == "interactive" else agent.auto
    payload = str(prompt_file) if _flag_takes_file(flag_str) else prompt
    return [agent.cli, *shlex.split(flag_str), payload]


def _flag_takes_file(flag: str) -> bool:
    return "file" in flag.lower()


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
