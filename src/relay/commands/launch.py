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
_LAUNCHABLE_STATUSES = {"draft", "active"}


def launch(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>` shim."),
    title: str = typer.Argument(
        None,
        help="With a bootstrap shim, scaffold a new draft task with this title and launch on it.",
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

    # Factory mode: bootstrap shim + title → scaffold a new draft task
    # seeded from the shim's frontmatter, then launch on the new task.
    if title is not None:
        if not is_bootstrap:
            _bail("Title arg is only valid when launching a `bootstrap/<name>` shim.")
        try:
            ref = _scaffold_from_shim(cfg, ref, title)
        except (ConfigError, ValueError) as exc:
            _bail(str(exc))
        is_bootstrap = False

    ticket = read_ticket(ref)

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
        if is_bootstrap:
            _bail("Bootstrap tickets only support interactive/auto modes.")
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

    # Acquire lock for normal tasks. Bootstrap shims are stateless re-entry
    # points — concurrent launches are fine, no lock to release.
    lock = None if is_bootstrap else TaskLock(ref.path)
    if lock is not None:
        try:
            lock.acquire(holder=assignee, force=force)
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
    post(
        cfg,
        f"{cfg.current_user}'s {assignee} started work on "
        f"{ref.id_slug} \"{ticket.title}\" ({mode})",
    )

    # Install a signal-safe cleanup.
    def _cleanup() -> None:
        if lock is not None:
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


def _scaffold_from_shim(cfg: Config, shim: BootstrapRef, title: str) -> TaskRef:
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
        assignee=shim_ticket.assignee,
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


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
