"""`relay launch` — compose context and start work on a task.

Launching an `active` task moves it to `in_progress`. Drafts must be
activated via `relay mark active <slug>` first; paused / done tickets must be
marked back to `active` before they can be launched.

Bootstrap shims are stateless re-entry points (no status, no log of state
changes) — launch is the only way to run a skill against one.
"""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import sys
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
from relay.config import ConfigError, load_config
from relay.logfile import append_log
from relay.mark import mark_in_progress
from relay.stream_render import (
    RunSummary,
    format_run_summary_log,
    is_stream_json_command,
    render_stream,
)
from relay.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_target,
)
from relay.ticket import Ticket


def launch(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>` shim."),
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

    # Pre-launch freshness check: if this ticket's linked PR has merged,
    # auto-bump to done before spinning up an agent against stale state.
    # Bootstrap shims have no status / PR link — `auto_bump_one` no-ops
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
        f"(status={ticket.status if not is_bootstrap else 'n/a'}, mode={ticket.mode}, "
        f"assignee={ticket.assignee or 'unassigned'})"
    )

    if not is_bootstrap:
        if ticket.status == "draft":
            _bail(
                f"Task {ref.id_slug} is draft. "
                f"Run `relay mark active {ref.id_slug}` first."
            )
        if ticket.status not in {"active", "in_progress"}:
            _bail(
                f"Task {ref.id_slug} is {ticket.status!r}. "
                f"Run `relay mark active {ref.id_slug}` to relaunch."
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
    typer.echo(
        f"Launch: agent {launch_assignee} -> {agent.name} "
        f"(cli={agent.cli})"
    )

    # Verify CLI binary exists.
    agent_path = shutil.which(agent.cli)
    if agent_path is None:
        _bail(f"Agent CLI {agent.cli!r} not found in PATH.")
    typer.echo(f"Launch: found agent CLI at {agent_path}")

    if isinstance(ref, TaskRef) and ticket.status == "active":
        mark_in_progress(
            cfg,
            ref,
            ticket,
            actor=f"human:{cfg.current_user}",
            log_message="started (active → in_progress) via relay launch",
            slack_text=(
                f"▶️ {cfg.current_user} started *{ref.id_slug}* "
                f"\"{ticket.title}\" — assignee {launch_assignee}"
            ),
            echo=f"{ref.id_slug}: in_progress",
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

            run_summary: RunSummary | None = None
            try:
                # Interactive: inherit stdio (human sits with agent).
                # Auto with stream-json: capture stdout, render events live.
                # Auto without streaming: inherit stdio and let claude buffer.
                if mode == "auto" and is_stream_json_command(cmd):
                    exit_code, run_summary = _run_with_stream_render(cmd, env)
                else:
                    result = subprocess.run(cmd, env=env, check=False)
                    exit_code = result.returncode
            except FileNotFoundError:
                _bail(f"Failed to spawn agent: {agent.cli!r} not found.")
            finally:
                _cleanup_prompt()

            # Token accounting: only the stream-json path can attribute usage
            # to this task. Interactive launches inherit stdio so we never
            # see the result event; skip silently rather than log a guess.
            if run_summary is not None and not is_bootstrap:
                append_log(
                    ref.path,
                    f"agent:{launch_assignee}",
                    format_run_summary_log(run_summary),
                )

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


def _run_with_stream_render(
    cmd: list[str], env: dict[str, str]
) -> tuple[int, RunSummary | None]:
    """Run `cmd` capturing stdout and pretty-print stream-json events live.

    Returns `(exit_code, run_summary)`. `run_summary` is `None` if the agent
    exited without emitting a `result` event (e.g. crash, signal).

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
    summary: RunSummary | None = None
    try:
        assert proc.stdout is not None
        summary = render_stream(proc.stdout, sys.stdout)
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        raise
    return proc.wait(), summary


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
    if after.status != "in_progress":
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


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
