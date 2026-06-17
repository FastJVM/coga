"""`relay launch` — compose context and start work on a task.

Launching an `active` task moves it to `in_progress`. A draft / paused / done
ticket is activated inline first — typing `relay launch` is the readiness
signal, so launch performs the `relay mark active` step itself rather than
refusing. (A workflow-less or required-extension-incomplete ticket still
can't be activated, so those fail loud with the same remedy `mark active`
gives.) An already-`in_progress` ticket resumes without another status flip.

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
    ComposeError,
    PromptComposition,
    compose_prompt,
    compose_prompt_report,
    write_prompt_file,
)
from relay.config import (
    Config,
    ConfigError,
    SecretError,
    load_config,
    select_launch_secrets,
)
from relay.logfile import append_log
from relay.mark import (
    RequiredExtensionMissing,
    WorkflowMissing,
    mark_active,
    mark_in_progress,
)
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
from relay.workflow import WorkflowError


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
    idle_timeout: float | None = typer.Option(
        None,
        "--idle-timeout",
        help="Tear down a stalled interactive REPL after this many seconds with "
        "no output or input (it never signalled done). Off by default — an "
        "attended launch waits indefinitely. `relay recurring` sets it so one "
        "stuck agent can't block the sweep.",
    ),
    max_session: float | None = typer.Option(
        None,
        "--max-session",
        help="Tear down an interactive REPL after this many seconds of wall-clock, "
        "even while it is still producing output (the runaway-loop case idle "
        "timeout misses). Off by default. `relay recurring` sets it from "
        "`[launch].max_session` so a busy-but-wedged agent can't block the sweep.",
    ),
    return_timeout: bool = typer.Option(
        False,
        "--return-timeout",
        hidden=True,
        help="Internal: return 'timeout' instead of exiting with the timeout code.",
    ),
) -> str | None:
    """Compose context, start work on a task.

    Returns the termination *kind* of the last interactive REPL the supervisor
    tore down when `return_timeout` is true — `"timeout"` when a liveness limit
    fired — or None for any other ending (clean done, chain completion,
    non-interactive launch). `relay recurring` uses this internal path to record
    a timed-out sweep launch honestly instead of mistaking it for a human pause;
    public CLI timeouts exit with the supervisor's non-zero timeout code.
    """
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
        try:
            composition = compose_prompt_report(
                cfg, ref, ticket, mode_override=mode_override
            )
        except ComposeError as exc:
            _bail(str(exc))
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

    # Typing `relay launch` *is* the readiness signal: a draft / paused /
    # done ticket is brought to `active` inline rather than refused with a
    # "run `relay mark active` first" hint. The flip to `in_progress` still
    # happens later (after the compose pre-flight), so this only does the
    # `mark active` half. Done before the script-mode dispatch so both
    # interactive and script launches start from an activated, stepped ticket.
    if (
        not is_bootstrap
        and isinstance(ref, TaskRef)
        and ticket.status not in {"active", "in_progress"}
    ):
        _auto_activate(cfg, ref, ticket)

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

    # Pre-flight the permission-skip policy for the first step's agent so a
    # skip_permissions = "auto" agent with no configured argv fails loud here
    # — before the in_progress flip and "started" broadcast, like the compose
    # pre-flight below. The per-step loop re-resolves the policy for rotated
    # agents.
    try:
        _skip_permissions_argv_for_launch(agent, mode, ref)
    except ConfigError as exc:
        _bail(str(exc))

    # Fail loud BEFORE flipping status: if a referenced context or skill is
    # missing, the composed prompt would drop a layer the human expected the
    # agent to have. Refuse to start — and don't flip the ticket to
    # in_progress or post a "started" broadcast for a task that never runs.
    # The per-step loop below re-composes; this is a cheap pre-flight (file
    # reads only) so the flip and notification post are never reached on a bad ref.
    try:
        compose_prompt(cfg, ref, ticket, mode_override=mode_override)
    except ComposeError as exc:
        _bail(str(exc))

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
                    f"\"{ticket.title}\" (assignee: {launch_assignee})"
                ),
                echo=f"{ref.id_slug}: in_progress",
            )
        except TaskValidationError as exc:
            _bail(str(exc))

    # Inject secrets as env vars, scoped to what the ticket declares. This is
    # the only place `relay launch` (agent mode) hands secrets to the spawned
    # process; a ticket's declared secret that resolves to an unset env var
    # fails loud here, before any agent starts.
    env = os.environ.copy()
    try:
        env.update(select_launch_secrets(cfg, ticket.secrets))
    except SecretError as exc:
        _bail(str(exc))

    # Interactive launches chain across consecutive agent-owned steps the
    # same way auto mode does. After the agent exits (via autoquit on
    # `relay bump` / `mark done` / `panic`, or via `/exit`), we re-read the
    # ticket and either relaunch the next step's agent as a fresh process —
    # rotating the CLI when the step hands off to a different agent (e.g.
    # claude -> codex for peer review) — or stop and return control to the
    # caller. Every bump produces a brand-new agent process with a freshly
    # composed prompt; context flows through the durable files (blackboard,
    # ticket, artifacts), never a carried-over REPL session. The supervisor
    # only stops at human handoffs and terminal states — `_harness_stop_reason`
    # decides. `RELAY_SUPERVISED=1` tells `relay bump` it's running under a
    # launch supervisor so its chaining hint can fire.
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

    first_step = True
    try:
        while True:
            ticket = _read(ref)

            # Resolve the agent for THIS step from the ticket's current
            # assignee, so the supervisor can rotate claude <-> codex across
            # the workflow. The `--agent` override applies only to the first
            # step; chained steps follow the ticket. A step whose assignee is
            # a human never reaches here — `_harness_stop_reason` returns
            # control to the caller before we'd relaunch.
            step_assignee = (
                (agent_override or ticket.assignee) if first_step else ticket.assignee
            )
            first_step = False
            try:
                agent = cfg.agent_type(step_assignee) if step_assignee else None
                if agent is None:
                    raise ConfigError(f"Task {ref.id_slug} has no assignee")
            except ConfigError as exc:
                # Defensive: a non-agent assignee should have stopped the
                # chain at the previous bump. If we somehow reach here, stop
                # rather than crash.
                typer.echo(f"{ref.id_slug}: {exc}; stopping")
                break
            # Re-check the CLI every step — catches the case where the chain
            # rotates to an agent (e.g. codex) whose CLI isn't on PATH. Stop
            # cleanly and hand back to the human rather than panicking.
            if shutil.which(agent.cli) is None:
                typer.secho(
                    f"{ref.id_slug}: next step needs agent {step_assignee!r} "
                    f"but its CLI {agent.cli!r} is not on PATH — stopping. "
                    f"Install it, then `relay launch {ref.id_slug}` to continue.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                break
            typer.echo(
                f"Launch: step agent {step_assignee} -> {agent.name} "
                f"(cli={agent.cli})"
            )

            _echo_launch_iteration(ref, ticket)

            # Compose & write prompt fresh for this step.
            warning = blackboard_size_warning(ref.path / "blackboard.md")
            if warning:
                typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW, err=True)

            typer.echo("Launch: composing prompt")
            try:
                prompt = compose_prompt(cfg, ref, ticket, mode_override=mode_override)
            except ComposeError as exc:
                _bail(str(exc))
            prompt_file = write_prompt_file(prompt, ref)
            typer.echo(
                f"Launch: prompt written to {prompt_file} "
                f"({len(prompt)} chars)"
            )
            # Re-resolve the permission-skip policy for THIS step's agent and
            # the ticket's current mode — supervised chains rotate agents
            # (claude <-> codex), and each agent carries its own local policy.
            try:
                skip_permissions_argv = _skip_permissions_argv_for_launch(
                    agent, mode_override or ticket.mode, ref
                )
            except ConfigError as exc:
                _bail(str(exc))
            cmd = build_agent_command(
                agent,
                mode,
                prompt,
                name=ticket.title or "",
                discussion=_is_discussion_bootstrap(ref),
                skip_permissions_argv=skip_permissions_argv,
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
                    step_assignee or launch_assignee,
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
                    # writes the session-done sentinel file after `relay mark
                    # done` / `relay panic` releases the REPL — and `relay
                    # recurring --interactive` can move to the next task
                    # without the human typing `/exit`. The sentinel path is
                    # advertised via `relay.repl_supervisor.SENTINEL_ENV`.
                    outcome = run_with_done_marker(
                        cmd,
                        env,
                        session_id=str(ref.path.resolve()),
                        idle_timeout=idle_timeout,
                        max_session=max_session,
                    )
                    exit_code = outcome.exit_code
                    termination_kind = outcome.kind
                else:
                    result = subprocess.run(cmd, env=env, check=False)
                    exit_code = result.returncode
                    termination_kind = "natural"
            except FileNotFoundError:
                _bail(f"Failed to spawn agent: {agent.cli!r} not found.")
            finally:
                _cleanup_prompt()

            typer.echo(f"Launch: agent exited with code {exit_code}")
            if termination_kind == "timeout":
                # A liveness limit (idle / max-session) tore the REPL down — the
                # agent never signalled done. Don't chain to the next step.
                # Recurring's in-process caller asks for the kind so it can
                # record the timeout and continue its sweep; public CLI callers
                # get the supervisor's non-zero timeout exit.
                typer.secho(
                    f"Agent timed out (no progress past the liveness limit) — "
                    f"exit {exit_code}.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                if return_timeout:
                    return "timeout"
                sys.exit(exit_code)
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

            # Bootstrap shims are stateless single-shot launches — they have no
            # workflow to chain across, so stop after the one run. A normal
            # workflow ticket that happens to declare ticket-level `skills:`
            # MUST still chain; gating on `ticket.skills` here (a rename
            # artifact of the old singular skill-shim field) silently broke that.
            if is_bootstrap:
                typer.echo(
                    f"Launch: {ref.id_slug} is a bootstrap shim — not chaining"
                )
                break

            typer.echo("Launch: reading task state after agent exit")
            updated_ticket = read_ticket(ref)
            stop_reason = _harness_stop_reason(ref, ticket, updated_ticket, cfg)
            if stop_reason is not None:
                typer.echo(stop_reason)
                break
    finally:
        _cleanup()


# --- helpers ------------------------------------------------------------------


def _auto_activate(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Bring a draft / paused / done ticket to `active` inline.

    `relay launch` used to refuse any status but `active`/`in_progress` and
    point the operator at `relay mark active`. Now launching *is* the
    readiness decision, so we run that activation here. The core `mark_active`
    mutates `ticket` in place — status → active, a bare-string `workflow:`
    frozen, and `step:` seeded (re-seeded to step 1 for a re-activated `done`
    ticket whose step was cleared by `mark done`) — so the later
    `mark_in_progress` flip fires off the same object.

    Fails loud, leaving the ticket untouched, when activation can't legally
    happen: the ticket has no workflow to advance, its `workflow:` ref can't
    be frozen, or a `required` extension field is empty. These mirror the
    `relay mark active` errors so the remedy is the same.
    """
    prior = ticket.status
    suffix = " — auto on launch"
    try:
        mark_active(
            cfg,
            ref,
            ticket,
            actor=f"human:{cfg.current_user}",
            log_message=f"activated ({prior} → active){suffix}",
            echo=f"{ref.id_slug}: active{suffix}",
        )
    except WorkflowMissing:
        _bail(
            f"Cannot launch {ref.id_slug}: it is {prior!r} and has no workflow, "
            "so there is nothing to activate or advance. Set `workflow: <name>` "
            "in `ticket.md` (see relay-os/workflows/) or run "
            f"`relay ticket {ref.id_slug}` to fill it in, then retry."
        )
    except WorkflowError as exc:
        _bail(
            f"Cannot launch {ref.id_slug}: its `workflow:` ref could not be "
            f"frozen — {exc}"
        )
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        _bail(
            f"Cannot launch {ref.id_slug}: required extension field(s) empty: "
            f"{names}. Fill them in `ticket.md` then retry."
        )
    except TaskValidationError as exc:
        _bail(str(exc))


def build_agent_command(
    agent,
    mode: str,
    prompt: str,
    *,
    name: str = "",
    discussion: bool = False,
    skip_permissions_argv: tuple[str, ...] = (),
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

    `skip_permissions_argv` (the agent's machine-local permission-skip argv,
    threaded by `_skip_permissions_argv_for_launch` only when its policy
    applies) is inserted after the name argv and before the mode-specific
    argv/prompt payload — `claude -n <title> <skip-argv> -p <prompt>`,
    `codex <skip-argv> exec <prompt>`.

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
        return [agent.cli, *name_args, *skip_permissions_argv, prompt]
    return [
        agent.cli,
        *name_args,
        *skip_permissions_argv,
        *shlex.split(agent.auto),
        prompt,
    ]


def _skip_permissions_argv_for_launch(
    agent, mode: str, ref: TaskRef | BootstrapRef
) -> tuple[str, ...]:
    """Resolve the permission-skip argv for one agent spawn, or `()`.

    The policy is machine-local per-agent config (`relay.local.toml`
    `[agents.<name>] skip_permissions = "auto"`) and applies only to normal
    task tickets running in effective `mode: auto`. Bootstrap/discussion
    shims and interactive/script launches always get `()` — today's
    behavior. Called per step so supervised chains re-evaluate the policy
    for whichever agent the current step rotated to.

    Fails loud (ConfigError) when the policy applies but the agent has no
    `skip_permissions_argv` configured — never silently fall back to the
    normal permission mode the operator opted out of.
    """
    if mode != "auto" or not isinstance(ref, TaskRef):
        return ()
    if agent.skip_permissions != "auto":
        return ()
    if not agent.skip_permissions_argv:
        raise ConfigError(
            f"Agent {agent.name!r} has skip_permissions = \"auto\" but no "
            "skip_permissions_argv in relay.local.toml. Set it (e.g. "
            f"`[agents.{agent.name}] skip_permissions_argv = \"...\"`) or "
            "remove the skip_permissions policy."
        )
    return agent.skip_permissions_argv


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


def _harness_stop_reason(
    ref: TaskRef, before: Ticket, after: Ticket, cfg: Config
) -> str | None:
    if after.status != "in_progress":
        if after.status == "done":
            return f"{ref.id_slug}: task is done"
        if after.status == "paused":
            return f"{ref.id_slug}: task is paused"
        return f"{ref.id_slug}: task status is {after.status!r}"

    # A workflow-less task has no step machinery — the whole ticket is the one
    # unit of work, and the supervisor only ever chains *across workflow steps*.
    # Reaching here means the agent exited (often after emitting the session-done
    # marker) without `relay mark done`, so it is still in_progress. There is
    # nothing to advance to; stop and return to the caller. This is distinct from
    # the no-progress case below — don't report it as "still on no workflow
    # step", which reads as a failed step advance.
    if not isinstance(after.workflow, dict):
        return (
            f"{ref.id_slug}: no workflow to chain — task is still in_progress "
            "(agent exited without `relay mark done`); stopping"
        )

    if (after.step, after.status) == (before.step, before.status):
        return f"{ref.id_slug}: still on {after.step}; stopping"

    current = after.current_step()
    if current is None:
        return f"{ref.id_slug}: no current workflow step; stopping"

    # The supervisor chains across agent steps — including agent rotations
    # (e.g. claude -> codex for peer review), relaunching the next step's
    # agent as a fresh process. It only returns control to the caller when
    # the next step hands off to a HUMAN (an assignee that is not a configured
    # agent type) or is unassigned. The discriminator is human-vs-agent, NOT
    # "did the nickname change" — a skill-less agent step is still the agent's
    # turn and chains. (Same-agent steps were always chained; this also covers
    # the cross-agent hop the single-agent loop used to stop at.)
    if not after.assignee or after.assignee not in cfg.agents:
        who = after.assignee or "unassigned"
        return f"{ref.id_slug}: next step hands off to {who}; returning to caller"

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
