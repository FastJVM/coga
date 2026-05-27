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

from relay.agent_skills import refresh_agent_skill_view
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
from relay.repl_supervisor import run_with_done_marker
from relay.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_target,
)
from relay.ticket import Ticket
from relay.validate import TaskValidationError


DISCUSSION_BOOTSTRAP_SHIMS = frozenset({"bootstrap/orient", "bootstrap/ticket"})
DEFAULT_DISCUSSION_TEMPLATES = {
    "claude": "--append-system-prompt {prompt}",
    "codex": "-c developer_instructions={prompt}",
}


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
    mode_override: str | None = typer.Option(
        None,
        "--mode",
        help="Run in this mode for this launch only (interactive or auto), "
        "overriding the ticket's `mode:`. For debugging — the ticket file is "
        "not modified.",
    ),
) -> None:
    """Compose context, start work on a task."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))
    _refresh_agent_skills_for_launch(cfg.repo_root)

    try:
        ref = resolve_target(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    is_bootstrap = isinstance(ref, BootstrapRef)
    if agent_override is not None:
        try:
            cfg.agent_type(agent_override)
        except ConfigError as exc:
            _bail(str(exc))

    if mode_override is not None and mode_override not in ("interactive", "auto"):
        _bail("--mode must be 'interactive' or 'auto'")

    def _read(target: TaskRef | BootstrapRef) -> Ticket:
        """Read the ticket, applying the ephemeral `--agent` override.

        `--mode` is deliberately NOT written into `frontmatter` here: the
        same ticket object is handed to `mark_in_progress`, which persists
        it. The mode override is threaded separately to `compose_prompt` and
        `build_agent_command` so the ticket file is never touched.
        """
        t = read_ticket(target)
        if mode_override is not None and t.mode == "script":
            _bail(
                "--mode override is not supported for script-mode tasks "
                "(they compose no agent prompt)."
            )
        if agent_override is not None and is_bootstrap:
            t.frontmatter["assignee"] = agent_override
        return t

    if prompt_report:
        ticket = _read(ref)
        if ticket.mode == "script":
            _bail("mode=script tasks do not compose an agent prompt.")
        composition = compose_prompt_report(
            cfg, ref, ticket, mode_override=mode_override
        )
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

    ticket = _read(ref)

    typer.echo(
        f"Launch: task {ref.id_slug} "
        f"(status={ticket.status if not is_bootstrap else 'n/a'}, mode={ticket.mode}, "
        f"assignee={ticket.assignee or 'unassigned'})"
    )
    if mode_override is not None:
        typer.secho(
            f"Launch: mode overridden to {mode_override!r} for this run "
            "— ticket file unchanged",
            fg=typer.colors.YELLOW,
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

    mode = mode_override or ticket.mode

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

    if mode == "auto":
        # Temporary policy. `claude -p` and `codex exec` buffer stdout until
        # the run completes, so auto launches produce no live console output
        # for the operator. Until relay grows a streaming consumer for the
        # agent's structured output, we refuse rather than let runs sit
        # silently. Re-enable when streaming lands.
        _bail(
            f"Cannot launch {ref.id_slug!r}: mode=auto is temporarily disabled. "
            "Auto runs produce no live console output (claude -p and codex exec "
            "buffer until completion), so unattended runs are unobservable. "
            "Edit the ticket to mode: interactive (and run from a TTY), or "
            "mode: script if the work fits a single script entry point."
        )

    if mode == "interactive" and not _interactive_stdio_has_tty():
        _bail(
            f"Cannot launch {ref.id_slug!r}: mode=interactive requires a TTY "
            "(stdin and stdout must both be terminals). Run from a real "
            "shell, or change the ticket to mode: script."
        )

    launch_assignee = agent_override or assignee

    # Resolve the agent type — the ticket's assignee names it directly.
    try:
        agent = cfg.agent_type(launch_assignee)
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
        try:
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
        except TaskValidationError as exc:
            _bail(str(exc))

    # Inject secrets as env vars.
    env = os.environ.copy()
    env.update(cfg.secrets)

    # Interactive launches chain across consecutive agent-owned steps the
    # same way auto mode does. After the agent exits (via autoquit on
    # `relay bump` / `mark done` / `panic`, or via `/exit`), we re-read the
    # ticket and either spawn a fresh REPL for the next step or stop and
    # return control to the caller. `_harness_stop_reason` decides.
    # `RELAY_SUPERVISED=1` tells `relay bump` it's running under a launch
    # supervisor so its chaining hint can fire.
    env["RELAY_SUPERVISED"] = "1"

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
            ticket = _read(ref)
            _echo_launch_iteration(ref, ticket)

            # Compose & write prompt fresh for this step.
            warning = blackboard_size_warning(ref.path / "blackboard.md")
            if warning:
                typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW, err=True)

            typer.echo("Launch: composing prompt")
            prompt = compose_prompt(cfg, ref, ticket, mode_override=mode_override)
            prompt_file = write_prompt_file(prompt, ref)
            typer.echo(
                f"Launch: prompt written to {prompt_file} "
                f"({len(prompt)} chars)"
            )
            cmd = build_agent_command(
                agent,
                mode,
                prompt,
                name=ticket.title or "",
                discussion=_is_discussion_bootstrap(ref),
            )
            typer.echo(
                f"Launch: command: "
                f"{_format_agent_command_for_console(cmd, prompt)}"
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

            if mode == "interactive" and ticket.title and sys.stdout.isatty():
                sys.stdout.write(f"\033]2;{ticket.title}\007")
                sys.stdout.flush()

            try:
                if mode == "interactive":
                    # Interactive REPLs (`claude`, `codex`) don't exit on
                    # their own. Run through a PTY watcher so an agent that
                    # emits the session-done marker after `relay mark done`
                    # / `relay panic` releases the REPL — and `relay
                    # recurring --interactive` can move to the next task
                    # without the human typing `/exit`. The marker string
                    # is `relay.repl_supervisor.DONE_MARKER`.
                    exit_code = run_with_done_marker(cmd, env)
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

            # An agent may delete its own task directory as a final action —
            # e.g. a Dream run retiring itself once its findings are durable.
            # A missing ticket.md is a clean terminal state, not a chain step.
            if not (ref.path / "ticket.md").exists():
                typer.echo(
                    "Launch: task directory removed by agent — nothing to chain"
                )
                break

            if is_bootstrap or ticket.skills:
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


def build_agent_command(
    agent, mode: str, prompt: str, *, name: str = "", discussion: bool = False
) -> list[str]:
    """Build the argv for spawning the agent.

    Interactive: `<cli> <prompt>` — agent opens its REPL with the prompt as
    the first user message. Auto: `<cli> <auto-flag(s)> <prompt>` — prefix
    flags put the CLI in headless mode (e.g. `-p` for claude, `exec` for
    codex).

    When the agent declares `name_flag` and a non-empty `name` is passed,
    `<name_flag> <name>` is inserted right after the CLI so the spawned
    session carries the ticket title in its picker / window title. Skipped
    in `discussion` mode so the human's first ask names the session.

    `discussion=True` (used for human discussion sessions like `relay chat`
    and `relay ticket`) routes the prompt through the agent's
    `discussion = "..."` template in `relay.toml` so it lands as
    system/developer context instead of as the first user message. The agent
    opens with no user message, letting the human's first ask set the session
    title. Uses configured `agent.discussion`, then built-in templates for
    known `claude` / `codex` CLIs, then falls back to positional.
    """
    discussion_template = _discussion_template(agent) if discussion else ""
    if discussion_template and mode == "interactive":
        tokens = [
            tok.replace("{prompt}", prompt)
            for tok in shlex.split(discussion_template)
        ]
        return [agent.cli, *tokens]
    name_args: list[str] = []
    if name and agent.name_flag:
        name_args = [*shlex.split(agent.name_flag), name]
    if mode == "interactive":
        return [agent.cli, *name_args, prompt]
    return [agent.cli, *name_args, *shlex.split(agent.auto), prompt]


def _is_discussion_bootstrap(ref: TaskRef | BootstrapRef) -> bool:
    return isinstance(ref, BootstrapRef) and ref.id_slug in DISCUSSION_BOOTSTRAP_SHIMS


def _discussion_template(agent) -> str:
    if agent.discussion:
        return agent.discussion
    return DEFAULT_DISCUSSION_TEMPLATES.get(Path(agent.cli).name, "")


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


def _format_agent_command_for_console(cmd: list[str], prompt: str) -> str:
    display = [
        f"<prompt-text {len(prompt)} chars>" if value == prompt else value
        for value in cmd
    ]
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

    if not current.get("skills"):
        return f"{ref.id_slug}: next step has no skills — handoff to human"

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


def _refresh_agent_skills_for_launch(relay_os: Path) -> None:
    try:
        result = refresh_agent_skill_view(relay_os)
    except OSError as exc:
        typer.secho(
            f"Warning: could not refresh agent skill view: {exc}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return
    if result.skipped:
        skipped = ", ".join(result.skipped[:5])
        suffix = "…" if len(result.skipped) > 5 else ""
        typer.secho(
            f"Warning: skipped {len(result.skipped)} agent skill link(s): {skipped}{suffix}",
            fg=typer.colors.YELLOW,
            err=True,
        )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
