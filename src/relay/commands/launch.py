"""`relay launch` — compose context and start work on a task."""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer

from relay.automerge import GhError, auto_bump_one
from relay.blackboard import blackboard_size_warning, format_bytes
from relay.compose import (
    PromptComposition,
    compose_prompt,
    compose_prompt_report,
    write_prompt_file,
)
from relay.config import Config, ConfigError, load_config
from relay.logfile import append_log, last_activity
from relay.scaffold import scaffold_task
from relay.slack import post
from relay.stream_render import is_stream_json_command, render_stream
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
    prompt_report: bool = typer.Option(
        False,
        "--prompt-report",
        help="Print composed prompt layers and approximate token counts, then exit without launching.",
    ),
    no_verify: bool = typer.Option(
        False,
        "--no-verify",
        help="Skip the pre-launch PR-merge freshness check.",
    ),
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

    if prompt_report and title is not None:
        _bail("--prompt-report cannot be used with a title argument.")

    if prompt_report:
        ticket = read_ticket(ref)
        if agent_override is not None and is_bootstrap:
            ticket.frontmatter["assignee"] = agent_override
        if ticket.mode == "script":
            _bail("mode=script tasks do not compose an agent prompt.")
        composition = compose_prompt_report(cfg, ref, ticket)
        typer.echo(_format_prompt_report(ref.id_slug, composition))
        warning = blackboard_size_warning(ref.path / "blackboard.md")
        if warning:
            typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW, err=True)
        return

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

    # Pre-launch freshness check: if this ticket's linked PR has merged,
    # auto-bump to done before spinning up an agent against stale state.
    # Bootstrap shims have no status / PR link — `_try_bump_one` no-ops
    # on them via the candidate filter, but skip for clarity. Same with
    # `--no-verify`.
    if not is_bootstrap and not no_verify and isinstance(ref, TaskRef):
        try:
            if auto_bump_one(cfg, ref):
                typer.echo(
                    f"Launch: {ref.id_slug} auto-bumped to done before launch — "
                    "nothing to do."
                )
                return
        except GhError as exc:
            typer.secho(
                f"Warning: skipping pre-launch freshness check: {exc}",
                fg=typer.colors.YELLOW,
                err=True,
            )
            typer.secho(
                "  Run `gh auth login` to enable PR-merge auto-bump on launch, "
                "or pass --no-verify to silence this.",
                fg=typer.colors.YELLOW,
                err=True,
            )

    ticket = read_ticket(ref)
    if agent_override is not None and is_bootstrap:
        ticket.frontmatter["assignee"] = agent_override

    typer.echo(
        f"Launch: task {ref.id_slug} "
        f"(status={ticket.status}, mode={ticket.mode}, assignee={ticket.assignee or 'unassigned'})"
    )

    # Announce ticket creation when the factory mode just scaffolded one.
    # `title is not None` was the factory-mode signal above; we re-derive
    # it here rather than threading another local because the post needs
    # the read ticket either way.
    if title is not None:
        typer.echo("Launch: posting scaffold notification")
        post(
            cfg,
            f"✨ {cfg.current_user} scaffolded *{ref.id_slug}* "
            f"\"{ticket.title}\" — "
            f"assignee {ticket.assignee or 'unassigned'}",
            task_path=ref.path,
            owner=ticket.owner or cfg.current_user,
        )
        typer.echo("Launch: scaffold notification posted")

    if not is_bootstrap and ticket.status not in _LAUNCHABLE_STATUSES:
        _bail(
            f"Task {ref.id_slug} is {ticket.status!r}. "
            f"Set status to 'draft' or 'active' before launching."
        )

    assignee = ticket.assignee
    if not assignee:
        _bail(f"Task {ref.id_slug} has no assignee")

    mode = ticket.mode

    # Soft-warn if the ticket is already active — status is the signal
    # that someone is already working on it. Bootstrap shims are stateless
    # re-entry points, so this check doesn't apply.
    if not is_bootstrap and ticket.status == "active":
        _warn_already_active(ref, ticket, mode)

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
    typer.echo(
        f"Launch: agent {launch_assignee} -> {agent.name} "
        f"(cli={agent.cli})"
    )

    # Verify CLI binary exists.
    agent_path = shutil.which(agent.cli)
    if agent_path is None:
        _bail(f"Agent CLI {agent.cli!r} not found in PATH.")
    typer.echo(f"Launch: found agent CLI at {agent_path}")

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
        typer.echo("Launch: activated draft task")
        typer.echo("Launch: posting activation notification")
        post(
            cfg,
            f"🚀 {cfg.current_user} activated *{ref.id_slug}* "
            f"\"{ticket.title}\" — assignee {assignee}"
            f"{_agent_override_note(agent_override, assignee)}",
            task_path=ref.path,
            owner=ticket.owner or cfg.current_user,
        )
        typer.echo("Launch: activation notification posted")

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

            typer.echo("Launch: composing prompt")
            prompt = compose_prompt(cfg, ref, ticket)
            prompt_file = write_prompt_file(prompt, ref)
            typer.echo(
                f"Launch: prompt written to {prompt_file} "
                f"({len(prompt)} chars)"
            )
            cmd = build_agent_command(agent, mode, prompt, prompt_file)
            typer.echo(
                f"Launch: command: "
                f"{_format_agent_command_for_console(cmd, prompt, prompt_file)}"
            )

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
                # Auto with stream-json: capture stdout, render events live.
                # Auto without streaming: inherit stdio and let claude buffer.
                if mode == "auto" and is_stream_json_command(cmd):
                    exit_code = _run_with_stream_render(cmd, env)
                else:
                    result = subprocess.run(cmd, env=env, check=False)
                    exit_code = result.returncode
            except FileNotFoundError:
                _bail(f"Failed to spawn agent: {agent.cli!r} not found.")
            finally:
                _cleanup_prompt()

            typer.echo(f"Launch: agent exited with code {exit_code}")
            if exit_code != 0:
                typer.secho(
                    f"Agent exited with code {exit_code}.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                sys.exit(exit_code)

            if is_bootstrap or ticket.skill:
                break

            typer.echo("Launch: reading task state after agent exit")
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


def _run_with_stream_render(cmd: list[str], env: dict[str, str]) -> int:
    """Run `cmd` capturing stdout and pretty-print stream-json events live.

    stderr is left attached to the parent terminal so claude's diagnostic
    output (auth errors, MCP startup, etc.) still surfaces.
    """
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        assert proc.stdout is not None
        render_stream(proc.stdout, sys.stdout)
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        raise
    return proc.wait()


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
        typer.echo(
            f"→ launching {ref.id_slug} "
            f"(status={ticket.status}, mode={ticket.mode}, assignee={ticket.assignee or 'unassigned'})"
        )
        return
    typer.echo(
        f"→ entering step {ticket.step}: {current['name']} "
        f"(status={ticket.status}, mode={ticket.mode}, assignee={ticket.assignee or 'unassigned'})"
    )


def _format_agent_command_for_console(
    cmd: list[str],
    prompt: str,
    prompt_file: Path,
) -> str:
    display = list(cmd)
    for idx, value in enumerate(display):
        if value == prompt:
            display[idx] = f"<prompt-text {len(prompt)} chars>"
        elif value == str(prompt_file):
            display[idx] = f"<prompt-file {prompt_file}>"
    return shlex.join(display)


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


def _format_prompt_report(id_slug: str, composition: PromptComposition) -> str:
    lines = [
        f"Prompt report for {id_slug}",
        "Approximate tokens use characters / 4; exact tokenizer parity is not assumed.",
        "",
        f"{'layer':<20} {'ref':<34} {'bytes':>10} {'approx_tokens':>14}",
        f"{'-' * 20} {'-' * 34} {'-' * 10} {'-' * 14}",
    ]
    for layer in composition.layers:
        ref = layer.ref or "-"
        if len(ref) > 34:
            ref = ref[:31] + "..."
        lines.append(
            f"{layer.layer:<20} {ref:<34} "
            f"{format_bytes(layer.byte_count):>10} {layer.approx_tokens:>14}"
        )
    lines.extend([
        "",
        f"Total composed prompt: {format_bytes(composition.byte_count)} "
        f"(~{composition.approx_tokens} tokens)",
    ])
    return "\n".join(lines)


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


def _warn_already_active(ref: TaskRef, ticket: Ticket, mode: str) -> None:
    """Status-is-signal soft warn: another worker may already be running.

    Interactive: prompt the human to continue. Auto/script: log a warning
    and proceed. No filesystem mutex — the failure mode (two divergent
    blackboard edits, two PR branches) is visible and recoverable.
    """
    assignee = ticket.assignee or "unassigned"
    last = last_activity(ref.path)
    when = _format_last_activity(last)
    line = (
        f"⚠ {ref.id_slug} is already active "
        f"(assignee: {assignee}, last log {when})"
    )
    if mode == "interactive" and sys.stdin.isatty():
        typer.secho(line, fg=typer.colors.YELLOW, err=True)
        if not typer.confirm("Continue anyway?", default=False):
            _bail("aborted")
        return
    typer.secho(f"{line} — proceeding ({mode} mode)", fg=typer.colors.YELLOW, err=True)


def _format_last_activity(last: datetime | None) -> str:
    if last is None:
        return "never"
    delta = datetime.now() - last
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
