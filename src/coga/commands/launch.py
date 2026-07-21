"""`coga launch` — compose context and start work on a task.

Launching an `active` task moves it to `in_progress`. A draft / paused ticket
is activated inline first — typing `coga launch` is the readiness signal, so
launch performs the `coga mark active` step itself rather than refusing. (A
workflow-less or required-extension-incomplete ticket still can't be activated,
so those fail loud with the same remedy `mark active` gives.) An
already-`in_progress` ticket resumes without another status flip. A `done`
ticket is refused and left untouched.

Bootstrap tickets are stateless re-entry points (no status, no log of state
changes) — launch is the only way to run a skill against one.
"""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4

import typer

from coga import usage as usage_tracking
from coga.agent_skills import refresh_agent_skill_view
from coga.blackboard import blackboard_size_warning, format_bytes, open_blockers
from coga.commands.launch_script import (
    build_task_env,
    current_step_is_script,
    is_script_launch,
)
from coga.compose import (
    ComposeError,
    PromptComposition,
    compose_prompt,
    compose_prompt_report,
    write_prompt_file,
)
from coga.config import (
    build_launch_env,
    Config,
    ConfigError,
    parse_inline_secrets,
    SecretError,
    load_config,
)
from coga.dependencies import agent_cli_missing_message
from coga.github_preflight import check_git_auth, check_git_remote
from coga import git
from coga.logfile import append_log
from coga.mark import (
    BlackboardNeedsSynthesis,
    RequiredExtensionMissing,
    WorkflowMissing,
    format_blackboard_synthesis_refusal,
    mark_active,
    mark_blocked,
    mark_in_progress,
)
from coga.repl_supervisor import (
    EXPECTED_STEP_ENV,
    EXPECTED_TASK_ENV,
    run_with_done_marker,
)
from coga.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_target,
)
from coga.ticket import Ticket
from coga.validate import TaskValidationError
from coga.version_skew import warn_if_installed_predates_source
from coga.workflow import WorkflowError


DISCUSSION_BOOTSTRAP_TICKETS = frozenset({"bootstrap/orient", "bootstrap/ticket"})
DEFAULT_DISCUSSION_TEMPLATES = {
    "claude": "--append-system-prompt {prompt}",
    "codex": "-c developer_instructions={prompt}",
}


def launch(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>` ticket."),
    args: list[str] | None = typer.Argument(
        None,
        help="Trailing arguments for a script launch, injected into the "
        "script's environment as COGA_ARG_1..N plus COGA_ARGC. An agent "
        "launch given trailing args fails loud (nothing consumes them).",
    ),
    agent_override: str | None = typer.Option(
        None,
        "--agent",
        help="Agent nickname to use for this launch instead of the ticket assignee.",
    ),
    prompt_report: bool = typer.Option(
        False,
        "--prompt-report",
        help="Print composed prompt layers and approximate token counts, then exit without launching.",
    ),
    idle_timeout: float | None = typer.Option(
        None,
        "--idle-timeout",
        help="Tear down a stalled interactive REPL after this many seconds with "
        "no output or input (it never signalled done). Off by default — an "
        "attended launch waits indefinitely. `coga recurring` sets it so one "
        "stuck agent can't block the sweep.",
    ),
    max_session: float | None = typer.Option(
        None,
        "--max-session",
        help="Tear down an interactive REPL after this many seconds of wall-clock, "
        "even while it is still producing output (the runaway-loop case idle "
        "timeout misses). Off by default. `coga recurring` sets it from "
        "`[launch].max_session` so a busy-but-wedged agent can't block the sweep.",
    ),
    return_timeout: bool = typer.Option(
        False,
        "--return-timeout",
        hidden=True,
        help="Internal: return 'timeout' instead of exiting with the timeout code.",
    ),
    queue_guidance: bool = typer.Option(
        False,
        "--queue-guidance",
        hidden=True,
        help="Internal: append the sequential-queue execution guidance "
        "(prompt-queue.md) to each composed agent prompt. `coga recurring` "
        "sets it for automatic sweeps so an agent announces its plan and "
        "continues — ending in `coga block` for owner decisions — instead of "
        "pausing the queue on a conversational ask.",
    ),
) -> str | None:
    """Compose context, start work on a task.

    Returns the termination *kind* of the last interactive REPL the supervisor
    tore down when `return_timeout` is true — `"timeout"` when a liveness limit
    fired — or None for any other ending (clean done, chain completion,
    non-interactive launch). `coga recurring` uses this internal path to record
    a timed-out sweep launch honestly instead of mistaking it for a human pause;
    public CLI timeouts exit with the supervisor's non-zero timeout code.
    """
    # In-process callers (recurring, retire) invoke this Typer command function
    # directly without passing every parameter, so an omitted `args` arrives as
    # Typer's ArgumentInfo sentinel rather than None. Normalize once up front.
    script_args: list[str] = list(args) if isinstance(args, (list, tuple)) else []

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

    def _read(target: TaskRef | BootstrapRef) -> Ticket:
        """Read the ticket, applying the ephemeral `--agent` override."""
        t = read_ticket(target)
        if agent_override is not None and is_bootstrap:
            t.frontmatter["assignee"] = agent_override
        return t

    if prompt_report:
        ticket = _read(ref)
        if is_script_launch(cfg, ticket):
            _bail("script tasks do not compose an agent prompt.")
        try:
            composition = compose_prompt_report(
                cfg, ref, ticket
            )
        except ComposeError as exc:
            _bail(str(exc))
        typer.echo(_format_prompt_report(ref.id_slug, composition))
        warning = blackboard_size_warning(ref.ticket_path)
        if warning:
            typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW, err=True)
        return

    ticket = _read(ref)

    typer.echo(
        f"Launch: task {ref.id_slug} "
        f"(status={ticket.status if not is_bootstrap else 'n/a'}, "
        f"assignee={ticket.assignee or 'unassigned'})"
    )

    # A `done` ticket is finished: launching it must not restart its frozen
    # workflow. Re-activating would re-seed `step: 1` without re-resolving
    # `assignee` (which still holds the final step's resolved human owner),
    # crashing the agent-type lookup and leaving the ticket wedged
    # (`active, step 1, assignee=<human>`). Refuse loud; reopening a finished
    # ticket is a deliberate workflow decision outside launch. Draft/paused
    # still activate inline below.
    if not is_bootstrap and isinstance(ref, TaskRef) and ticket.status == "done":
        _bail(
            f"Cannot launch {ref.id_slug}: it is done; nothing to launch. "
            "Reopen it deliberately before launching again, or launch a "
            "different ticket."
        )

    blocked_resume = False

    # A blocked ticket may be launched only by an explicit interactive human
    # act: the session's first job becomes resolving the open asks with the
    # human (the composed prompt gains a resolve-or-re-block preamble keyed
    # off the blackboard's open blockers), and the ticket reactivates inline
    # after preflights pass. Batch surfaces are unchanged — a
    # script step or TTY-less run has no human to discuss with, so those keep
    # the hard refusal (checked here, before any status mutation). `coga
    # megalaunch` never gets this far: its sweep classifies blocked tickets as
    # skipped-unresolved-blocker, and an explicit pick runs the same
    # activate-and-resume through the engine's own launch loop.
    if not is_bootstrap and isinstance(ref, TaskRef) and ticket.status == "blocked":
        if not is_script_launch(cfg, ticket) and _interactive_stdio_has_tty():
            if not open_blockers(ref.ticket_path):
                _bail(
                    f"Cannot launch {ref.id_slug}: it is blocked but has no "
                    "open blocker asks to resolve. Record a blocker with "
                    f"`coga block --task {ref.id_slug} --reason \"...\"` or "
                    "repair the task state before launching."
                )
            blocked_resume = True
            typer.echo(
                f"Launch: {ref.id_slug} is blocked — resuming interactively; "
                "the session's first job is to resolve or re-block the open asks."
            )
        else:
            _bail(
                f"Cannot launch {ref.id_slug}: it is blocked, and only an "
                f"interactive launch from a TTY can resume it to resolve the "
                f"blocker in-session. Run `coga status --blocked` to read the "
                f"open ask, then `coga unblock {ref.id_slug} --answer \"...\"` "
                f"to resume."
            )

    # Refuse human handoffs up front: a human-owned active/in-progress step
    # should report the handoff directly, before any status mutation.
    if not is_bootstrap and ticket.status not in {"draft", "paused"}:
        _refuse_human_handoff_launch(cfg, ref, ticket, agent_override)

    # A script launch — the current step has one script-backed skill or the
    # ticket carries its own `script:` — runs with no agent through
    # run_script_mode.
    run_current_as_script = is_script_launch(cfg, ticket)

    try:
        # Typing `coga launch` *is* the readiness signal: a draft / paused ticket
        # is brought to `active` inline rather than refused with a "run
        # `coga mark active` first" hint. The flip to `in_progress` still happens
        # later (after the compose pre-flight), so this only does the `mark active`
        # half. Done before the script-vs-agent dispatch so both agent and
        # script launches start from an activated, stepped ticket.
        if (
            not is_bootstrap
            and isinstance(ref, TaskRef)
            and ticket.status in {"draft", "paused"}
        ):
            _auto_activate(cfg, ref, ticket)
            # Activation freezes a bare-string workflow and seeds step 1. A
            # hand-authored draft can therefore become script-backed here even
            # though the pre-activation deduction above could not see a current
            # step. Recompute before choosing the script or agent path.
            run_current_as_script = is_script_launch(cfg, ticket)

        assignee = ticket.assignee
        if not assignee:
            _bail(f"Task {ref.id_slug} has no assignee")

        # A script launch — the ticket's own `script:`, or a current step whose
        # single skill is script-backed (e.g. code/open-pr) — runs with no agent
        # and no composed prompt, through the same run_script_mode path.
        # Handling it here — before the agent-only TTY / CLI / git-auth setup —
        # is what lets a relaunch land straight on the script step without a
        # terminal. The supervisor loop below runs the same path for a script
        # step reached mid-chain; on exit 0 the step advances, on non-zero it
        # does not.
        if run_current_as_script:
            if agent_override is not None:
                _bail("--agent is only supported for agent launches.")
            from coga.commands.launch_script import run_script_mode
            run_script_mode(
                cfg, ref, ticket, stateless=is_bootstrap, args=script_args
            )
            # A failed script sys.exits inside run_script_mode; that path is
            # refreshed by the BaseException handler below, so this fires
            # exactly once per script launch.
            _refresh_launch_checkout(cfg)
            return

        # Trailing args are a script-launch channel (COGA_ARG_1..N). An agent
        # launch has nothing that consumes them — composing them into the
        # prompt is deliberately deferred — so dropping them silently would be
        # a fail-quiet wrong answer. Refuse before any TTY/CLI/auth setup.
        if script_args:
            listed = " ".join(script_args)
            _bail(
                f"Cannot launch {ref.id_slug} with trailing arguments "
                f"({listed!r}): launch arguments are only supported for "
                "script launches, where they are injected as COGA_ARG_1..N. "
                "An agent launch does not consume them. Remove the arguments, "
                "or target a script-backed ticket."
            )

        _refuse_human_handoff_launch(cfg, ref, ticket, agent_override)

        if not _interactive_stdio_has_tty():
            _bail(
                f"Cannot launch {ref.id_slug!r}: an agent launch requires a TTY "
                "(stdin and stdout must both be terminals). Run from a real "
                "shell, or give the task a script (a `script:` entry or a "
                "script-backed workflow step) for deterministic unattended work."
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
            _bail(agent_cli_missing_message(agent.cli))
        typer.echo(f"Launch: found agent CLI at {agent_path}")

        # Fail loud BEFORE flipping status: if a referenced context or skill is
        # missing, the composed prompt would drop a layer the human expected the
        # agent to have. Refuse to start — and don't flip the ticket to
        # in_progress or post a "started" broadcast for a task that never runs.
        # The per-step loop below re-composes; this is a cheap pre-flight (file
        # reads only) so the flip and notification post are never reached on a bad ref.
        try:
            compose_prompt(cfg, ref, ticket)
        except ComposeError as exc:
            _bail(str(exc))

        # Preflight and build the child env before mutating ticket state. A missing
        # declared secret is a launch refusal, not a started task.
        try:
            env = build_launch_env(cfg, ticket.secrets)
        except SecretError as exc:
            _bail(str(exc))

        # Refuse to start an agent session when git push access is broken. Coga
        # drives the whole session through git/gh (branch push, `gh pr create`,
        # every `coga bump` syncs ticket state), so a dead remote means an
        # often-long run guaranteed to fail at ship time. Fail loud at the door
        # rather than discover it at PR time — same as the other pre-flip
        # preflights above. Pre-flip, so a refused launch never posts a "started"
        # broadcast or flips status.
        _preflight_push_auth(cfg, ref, is_bootstrap=is_bootstrap)

        # All fail-loud preflights have passed — the session is going to run. A
        # stale installed binary launching agent work is the costliest place for
        # version skew to hide (it can burn a whole session running bugs already
        # fixed in source), so surface it here, before the status flip and spawn.
        # Warn-only, and a silent no-op outside a coga source checkout.
        warn_if_installed_predates_source(cfg.repo_root)

        if blocked_resume and isinstance(ref, TaskRef) and ticket.status == "blocked":
            _auto_activate(cfg, ref, ticket)

        if isinstance(ref, TaskRef) and ticket.status == "active":
            try:
                mark_in_progress(
                    cfg,
                    ref,
                    ticket,
                    actor=f"human:{cfg.current_user}",
                    log_message="started (active → in_progress) via coga launch",
                    slack_text=(
                        f"▶️ {cfg.current_user} started *{ref.id_slug}* "
                        f"\"{ticket.title}\" (assignee: {launch_assignee})"
                    ),
                    echo=f"{ref.id_slug}: in_progress",
                )
            except TaskValidationError as exc:
                _bail(str(exc))

        # Agent launches chain across consecutive agent-owned steps. After the
        # agent exits (via autoquit on
        # `coga bump` / `mark done` / `block`, or via `/exit`), we re-read the
        # ticket and either relaunch the next step's agent as a fresh process —
        # rotating the CLI when the step hands off to a different agent (e.g.
        # claude -> codex for peer review) — or stop and return control to the
        # caller. Every bump produces a brand-new agent process with a freshly
        # composed prompt; context flows through the durable files (blackboard,
        # ticket, artifacts), never a carried-over REPL session. The supervisor
        # only stops at human handoffs and terminal states — `_harness_stop_reason`
        # decides. `COGA_SUPERVISED=1` tells `coga bump` it's running under a
        # launch supervisor so its chaining hint can fire.
        env["COGA_SUPERVISED"] = "1"

        def _on_signal(signum, frame):  # type: ignore[no-untyped-def]
            sys.exit(128 + signum)

        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
    except BaseException as exc:
        # Setup can exit after state was already published (the auto-activate
        # or in_progress flip, a failed script step) — pull that state back
        # into the launch checkout before surfacing the exit. The one
        # exception: a *bootstrap* script (coga-owned, so the exit-code
        # contract is ours) that refused because the control checkout is
        # stale/diverged (`git.STALE_CONTROL_EXIT_CODE`) published nothing,
        # and the refresh's ff-merge is guaranteed to fail against the same
        # divergence — it would only re-dump the conflict the script already
        # reported. A user ticket script exiting with the same number keeps
        # the unconditional refresh.
        if not (
            is_bootstrap
            and isinstance(exc, SystemExit)
            and exc.code == git.STALE_CONTROL_EXIT_CODE
        ):
            _refresh_launch_checkout(cfg)
        raise

    try:
        first_step = True
        while True:
            ticket = _read(ref)

            # A workflow step whose single skill declares a `script:` runs as a
            # deterministic script even mid-way through an agent workflow — the
            # same run_script_mode path used above, dispatched per step. The launcher,
            # not an agent, executes it and advances only on exit 0, so
            # `code/open-pr` reached mid-chain (peer-review → open-pr) cannot
            # complete without producing a real PR.
            if not is_bootstrap and current_step_is_script(cfg, ticket):
                from coga.commands.launch_script import run_script_mode

                _echo_launch_iteration(ref, ticket)
                before = ticket
                # Advances the step on success; on failure posts and sys.exit.
                run_script_mode(cfg, ref, ticket)
                ticket = read_ticket(ref)
                stop_reason = _harness_stop_reason(ref, before, ticket, cfg)
                if stop_reason is not None:
                    typer.echo(stop_reason)
                    break
                continue

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
            # cleanly and hand back to the human rather than blocking.
            if shutil.which(agent.cli) is None:
                typer.secho(
                    f"{ref.id_slug}: next step needs agent {step_assignee!r} "
                    f"but {agent_cli_missing_message(agent.cli)} Stopping; "
                    f"then run `coga launch {ref.id_slug}` to continue.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                break
            typer.echo(
                f"Launch: step agent {step_assignee} -> {agent.name} "
                f"(cli={agent.cli})"
            )

            _echo_launch_iteration(ref, ticket)
            step_env = dict(env)
            step_env[EXPECTED_TASK_ENV] = str(ref.path.resolve())
            step_env[EXPECTED_STEP_ENV] = ticket.step or ""

            try:
                session = spawn_agent_session(
                    cfg,
                    ref,
                    ticket,
                    agent,
                    env=step_env,
                    actor=f"human:{cfg.current_user}",
                    log_message=_launch_log_message(
                        ticket.assignee or assignee,
                        step_assignee or launch_assignee,
                        agent.name,
                    ),
                    name=ticket.title or "",
                    discussion=_is_discussion_bootstrap(ref),
                    kickoff=_bootstrap_kickoff(ref),
                    prompt_suffix=(
                        _queue_prompt_suffix() if queue_guidance else ""
                    ),
                    idle_timeout=idle_timeout,
                    max_session=max_session,
                    label="Launch",
                    warn_blackboard=True,
                    commit_log=is_bootstrap,
                )
            except ComposeError as exc:
                _bail(str(exc))
            except FileNotFoundError:
                _bail(f"Failed to spawn agent: {agent.cli!r} not found.")

            typer.echo(f"Launch: agent exited with code {session.exit_code}")
            if blocked_resume:
                _reblock_unresolved_resume(cfg, ref, step_assignee or launch_assignee)
                blocked_resume = False
            if session.termination_kind == "timeout":
                # A liveness limit (idle / max-session) tore the REPL down — the
                # agent never signalled done. Don't chain to the next step.
                # Recurring's in-process caller asks for the kind so it can
                # record the timeout and continue its sweep; public CLI callers
                # get the supervisor's non-zero timeout exit.
                timeout_reason = (
                    session.termination_reason
                    or "liveness limit reached without a done signal"
                )
                typer.secho(
                    f"Agent timed out: {timeout_reason} — exit "
                    f"{session.exit_code}.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                if return_timeout:
                    return "timeout"
                sys.exit(session.exit_code)
            if session.exit_code != 0:
                typer.secho(
                    f"Agent exited with code {session.exit_code}.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                sys.exit(session.exit_code)

            # An agent may delete its own task directory as a final action —
            # e.g. a Dream run retiring itself once its findings are durable.
            # A missing ticket.md is a clean terminal state, not a chain step.
            if not ref.ticket_path.exists():
                typer.echo(
                    "Launch: task directory removed by agent — nothing to chain"
                )
                break

            # Bootstrap tickets are stateless single-shot launches — they have no
            # workflow to chain across, so stop after the one run. A normal
            # workflow ticket that happens to declare ticket-level `skills:`
            # MUST still chain; gating on `ticket.skills` here (a rename
            # artifact of the old singular skill-shim field) silently broke that.
            if is_bootstrap:
                typer.echo(
                    f"Launch: {ref.id_slug} is a bootstrap ticket — not chaining"
                )
                break

            typer.echo("Launch: reading task state after agent exit")
            updated_ticket = read_ticket(ref)
            stop_reason = _harness_stop_reason(ref, ticket, updated_ticket, cfg)
            if stop_reason is not None:
                typer.echo(stop_reason)
                break
    finally:
        # On every exit path — clean chain completion, `sys.exit` on a
        # non-zero/timeout agent, or an exception — pull the run's published
        # state back into the checkout the operator launched from, so the
        # `coga status` they run next in this terminal shows the world the
        # run just created.
        _refresh_launch_checkout(cfg)


# --- helpers ------------------------------------------------------------------


def _auto_activate(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Bring a draft / paused / resumable blocked ticket to `active` inline.

    `coga launch` used to refuse any status but `active`/`in_progress` and
    point the operator at `coga mark active`. Now launching *is* the
    readiness decision, so we run that activation here. The core `mark_active`
    mutates `ticket` in place — status → active, a bare-string `workflow:`
    frozen, and `step:` seeded — so the later `mark_in_progress` flip fires off
    the same object. (A `done` ticket never reaches here: launch refuses it
    earlier rather than restart a finished workflow. A blocked ticket reaches
    here only after the launch preflights have passed.)

    Fails loud, leaving the ticket untouched, when activation can't legally
    happen: the ticket has no workflow to advance, its `workflow:` ref can't
    be frozen, or a `required` extension field is empty. These mirror the
    `coga mark active` errors so the remedy is the same.
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
            "in `ticket.md` (see coga/workflows/) or run "
            f"`coga ticket {ref.id_slug}` to fill it in, then retry."
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
    except BlackboardNeedsSynthesis as exc:
        _bail(
            format_blackboard_synthesis_refusal(
                ref.id_slug, action="launch", reason=exc.reason
            )
        )
    except TaskValidationError as exc:
        _bail(str(exc))


def _reblock_unresolved_resume(
    cfg: Config, ref: TaskRef | BootstrapRef, blocker: str | None
) -> None:
    """Return an unresolved blocked-ticket resume to the blocked queue.

    A resumed blocked launch is allowed to become `in_progress` so the same
    session can discuss, run `coga unblock`, and continue to `coga bump`. If
    that session exits before recording the answer, keep the unresolved ask
    visible to `status --blocked`, `unblock --all`, and blocker reminders.
    """
    if not isinstance(ref, TaskRef) or not ref.ticket_path.exists():
        return
    blockers = open_blockers(ref.ticket_path)
    if not blockers:
        return
    ticket = read_ticket(ref)
    if ticket.status != "in_progress":
        return

    owner = ticket.owner or cfg.current_user
    detail = "; ".join(b.reason for b in blockers)
    try:
        mark_blocked(
            cfg,
            ref,
            ticket,
            actor="system",
            log_message=(
                "blocked: unresolved blocker still open after resumed launch exited"
            ),
            slack_text=(
                f"🛑 {blocker or cfg.current_user} still blocked "
                f"*{ref.id_slug}* \"{ticket.title}\": {detail}"
            ),
            echo=(
                f"{ref.id_slug}: blocked (unresolved blocker still open; "
                f"owner {owner} needs to answer)"
            ),
        )
    except TaskValidationError as exc:
        _bail(str(exc))


def _preflight_push_auth(
    cfg: Config, ref: TaskRef | BootstrapRef, *, is_bootstrap: bool
) -> None:
    """Refuse to launch when git push access to the configured remote is broken.

    Coga runs the whole session through git/gh, so a dead remote means a run
    guaranteed to fail at ship time; catch it at the door. The probe is the
    same non-interactive `git push --dry-run` `coga validate --check-github`
    uses (so a logged-out HTTPS remote fails fast, not on a prompt).

    Self-skips when there is nothing to push to or no sync configured:
    bootstrap tickets (stateless, no PR), `[git].enabled = false`, and any
    checkout where the configured remote does not resolve (not a git repo / no
    remote) — which is also why the non-git launch test fixtures are
    unaffected. Only a *configured, reachable-but-unauthenticated* remote bails.
    """
    if is_bootstrap or not cfg.git_enabled:
        return
    if not check_git_remote(cfg.git_remote).ok:
        # No git repo / remote unconfigured → the sync layer soft-no-ops, so
        # there is no push to gate.
        return
    auth = check_git_auth(cfg.git_remote)
    if not auth.ok:
        _bail(
            f"Cannot launch {ref.id_slug}: git push access to "
            f"{cfg.git_remote!r} is unavailable, and coga drives the session "
            "through git/gh (branch push, `gh pr create`, `coga bump` ticket "
            f"sync) — it would fail at ship time. {auth.detail} "
            "Fix auth and retry, or set `[git].enabled = false` to run without "
            "git sync."
        )


def _refresh_launch_checkout(cfg: Config) -> None:
    """Pull the control branch's task state back into the launch checkout.

    Runs once on every exit path the supervisor sees, so the operator's
    checkout never stays stale until a manual pull. Non-fatal by
    construction: `refresh_coga_state_from_control` surfaces git failures on
    stderr + the log and never raises, so a refresh miss cannot mask the
    launch's real outcome.
    """
    git.refresh_coga_state_from_control(
        cfg, message="Refresh coga state after launch"
    )


def _queue_prompt_suffix() -> str:
    """Package-backed execution guidance for sequential automatic queues.

    The `coga recurring` counterpart of megalaunch's `prompt-megalaunch.md`:
    an automatic sweep's REPL has a TTY (so work streams live), but nobody is
    necessarily watching — an agent that pauses on a conversational ask hangs
    the queue until a liveness timeout fails the task. The guidance says to
    announce the plan and continue, and to end in `coga block` when a decision
    genuinely needs the owner.
    """
    try:
        prompt = files("coga.resources").joinpath("prompt-queue.md").read_text()
    except OSError as exc:
        raise ComposeError(
            "Queue execution prompt is missing from the installed Coga "
            "package: prompt-queue.md"
        ) from exc
    return f"\n\n{prompt.strip()}\n"


# Linux caps a single execve() argument at MAX_ARG_STRLEN (32 pages =
# 131072 bytes). A composed prompt at or over it makes the PTY child's
# execvp fail with E2BIG before the agent ever starts. Stay under with
# headroom for a discussion template's text wrapped around `{prompt}`.
_MAX_PROMPT_ARG_BYTES = 120_000


def _argv_prompt(prompt: str, prompt_file: Path) -> str:
    """The prompt as it rides argv: verbatim, or a file pointer when oversized.

    The prompt file is already on disk (written before the argv is built) and
    is only removed after the session ends, so the pointer stays valid for the
    agent's whole run. Same content, one indirection — the alternative is a
    guaranteed E2BIG exec failure.
    """
    if len(prompt.encode()) <= _MAX_PROMPT_ARG_BYTES:
        return prompt
    return (
        f"Read the file {prompt_file} in full before doing anything else — "
        "its contents are your complete composed Coga prompt, too large to "
        "pass as a command-line argument. Follow it exactly as if it had "
        "been given to you as this message."
    )


def build_agent_command(
    agent,
    prompt: str,
    *,
    name: str = "",
    discussion: bool = False,
    session_id: str | None = None,
) -> list[str]:
    """Build the argv for spawning the agent.

    Default shape: `<cli> <prompt>` — agent opens its REPL with the prompt as
    the first user message.

    When the agent declares `name_flag` and a non-empty `name` is passed,
    `<name_flag> <name>` is inserted right after the CLI so the spawned
    session carries the ticket title in its picker / window title. Skipped
    in `discussion` mode so the human's first ask names the session.

    `session_id` uses the agent's `session_id_flag`, when configured, to pin a
    transcript id.

    `discussion=True` (used for human discussion sessions like `coga chat`
    and `coga ticket`) routes the prompt through the agent's
    `discussion = "..."` template in `coga.toml` so it lands as
    system/developer context instead of as the first user message. The agent
    opens with no user message, letting the human's first ask set the session
    title. Uses configured `agent.discussion`, then built-in templates for
    known `claude` / `codex` CLIs, then falls back to positional.
    """
    discussion_template = _discussion_template(agent) if discussion else ""
    if discussion_template:
        tokens = [
            tok.replace("{prompt}", prompt)
            for tok in shlex.split(discussion_template)
        ]
        return [agent.cli, *tokens]
    name_args: list[str] = []
    if name and agent.name_flag:
        name_args = [*shlex.split(agent.name_flag), name]
    session_id_args: list[str] = []
    if session_id and agent.session_id_flag:
        session_id_args = [*shlex.split(agent.session_id_flag), session_id]
    return [
        agent.cli,
        *name_args,
        *session_id_args,
        prompt,
    ]


class AgentSessionResult(NamedTuple):
    exit_code: int
    termination_kind: str
    termination_reason: str | None = None


def spawn_agent_session(
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    ticket: Ticket,
    agent,
    *,
    env,
    actor: str,
    log_message: str,
    name: str = "",
    discussion: bool = False,
    kickoff: str | None = None,
    prompt_suffix: str = "",
    idle_timeout: float | None = None,
    max_session: float | None = None,
    label: str = "Launch",
    warn_blackboard: bool = False,
    commit_log: bool = False,
    secrets_are_scoped: bool = True,
    stateless_identity: tuple[str, str] | None = None,
) -> AgentSessionResult:
    """Spawn one agent process once.

    This is the shared single-shot body beneath `coga launch`'s supervisor
    chain: compose prompt, write prompt file, build argv, log, spawn under the
    PTY watcher for interactive REPLs, and remove the temp prompt file.

    Per-caller differences are arguments here, not forked command code:
    `env` carries the secrets policy (`coga launch` passes a launch env;
    authoring passes the ambient process env with no Coga secret injection),
    `discussion` selects discussion-prompt argv, and `kickoff` appends an
    optional first user turn such as the `coga ticket` greet-first "Begin".
    `stateless_identity` lets an authoring surface compose against a real task
    while recording the agent interaction under its bootstrap identity and
    title, with no workflow step.
    The launch supervisor loop and step chaining deliberately stay outside.

    `commit_log` immediately commits the `log.md` launch append (via
    `sync_log`) instead of leaving it dirty. Callers set it only when no later
    sync will carry the log: a stateless bootstrap-ticket launch has no
    subsequent bump/`sync_paths`, so without this its append blocks the next
    `git pull` at the checkout gate (the append is committed before the REPL
    starts, so even an in-session `git pull` is unblocked). `coga ticket`
    leaves it False because its post-session record is committed by the shared
    teardown sync. `secrets_are_scoped` is False only when the caller passes an
    ambient environment instead of `build_launch_env`; that distinction keeps
    redaction from mistaking an unrelated same-named variable for a configured
    secret value.
    """
    # A nested launch inherits its parent's process environment. Re-derive the
    # task metadata at this last shared boundary so an agent started by a
    # bootstrap script identifies the task it is actually running, not the
    # outer bootstrap ticket. Copy first so caller-owned environments remain
    # unchanged; unrelated parent values still pass through.
    env = dict(env)
    env.pop("COGA_SKILL_NAME", None)
    env.pop("COGA_SKILL_DIR", None)
    env.update(build_task_env(cfg, ref))

    if warn_blackboard:
        warning = blackboard_size_warning(ref.ticket_path)
        if warning:
            typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW, err=True)

    typer.echo(f"{label}: composing prompt")
    prompt = compose_prompt(cfg, ref, ticket)
    if prompt_suffix:
        prompt = f"{prompt}{prompt_suffix}"
    prompt_file = write_prompt_file(prompt, ref)
    typer.echo(
        f"{label}: prompt written to {prompt_file} "
        f"({len(prompt)} chars)"
    )
    prompt_arg = _argv_prompt(prompt, prompt_file)
    if prompt_arg is not prompt:
        typer.echo(
            f"{label}: prompt exceeds the {_MAX_PROMPT_ARG_BYTES}-byte "
            f"single-argument limit — the agent will read it from "
            f"{prompt_file}"
        )

    usage_provider = usage_tracking.parser_key_for_cli(agent.cli)
    usage_session_id = (
        str(uuid4()) if agent.session_id_flag else None
    )
    usage_pre_existing = usage_tracking.snapshot_session_files(usage_provider)
    usage_secret_values = _configured_secret_values(
        ticket, env, secrets_are_scoped=secrets_are_scoped
    )
    excluded_user_texts = tuple(
        dict.fromkeys(text for text in (prompt, prompt_arg, kickoff) if text)
    )
    usage_cwd = Path.cwd().resolve()
    usage_window_start = datetime.now(timezone.utc)
    spawn_started = False
    outcome_status: usage_tracking.OutcomeStatus = "unknown"

    try:
        cmd = build_agent_command(
            agent,
            prompt_arg,
            name=name,
            discussion=discussion,
            session_id=usage_session_id,
        )
        if kickoff:
            cmd.append(kickoff)
        typer.echo(
            f"{label}: command: "
            f"{_format_agent_command_for_console(cmd, prompt)}"
        )

        append_log(cfg, ref.id_slug, actor, log_message)
        if commit_log:
            # Commit the launch line now so it never lingers uncommitted in the
            # working tree. A bootstrap-ticket launch has no later sync to carry
            # the log, so without this its append blocks the next `git pull` at
            # the checkout gate (merge=union only saves committed content).
            # Non-fatal on any git failure.
            git.sync_log(cfg, message=f"Log: {ref.id_slug}")

        if name and sys.stdout.isatty():
            sys.stdout.write(f"\033]2;{name}\007")
            sys.stdout.flush()

        spawn_started = True
        # Agent CLIs (`claude`, `codex`) don't exit on their own. Run through a
        # PTY watcher so an agent that writes the session-done sentinel after
        # `coga bump` / `coga mark done` / `coga block` releases the REPL.
        # Scope the sentinel by the task's `id_slug`, the identifier `bump` /
        # `mark` / `block` write. It must be the slug, not `ref.path.resolve()`:
        # a path-scoped marker only matches when the agent's `coga bump` ran
        # from the same checkout — a bump from a peer agent's separate clone
        # (or any other checkout of the repo) writes a different path, the
        # poll never matches, and the REPL hangs. The slug is the same from
        # any checkout, so teardown fires regardless of the bump's cwd.
        outcome = run_with_done_marker(
            cmd,
            env,
            session_id=ref.id_slug,
            idle_timeout=idle_timeout,
            max_session=max_session,
        )
        outcome_status = _session_outcome_status(outcome)
        return AgentSessionResult(outcome.exit_code, outcome.kind, outcome.reason)
    except KeyboardInterrupt:
        outcome_status = "interrupted"
        raise
    except FileNotFoundError:
        spawn_started = False
        raise
    except BaseException:
        outcome_status = "failed"
        raise
    finally:
        usage_window_end = datetime.now(timezone.utc)
        if spawn_started:
            stateless_session = stateless_identity is not None or isinstance(
                ref, BootstrapRef
            )
            session_slug = (
                stateless_identity[0] if stateless_identity else ref.id_slug
            )
            session_title = (
                stateless_identity[1]
                if stateless_identity
                else ticket.title or ""
            )
            usage_tracking.capture_session(
                cfg=cfg,
                title=session_title,
                slug=session_slug,
                step=None if stateless_session else _current_step_name(ticket),
                agent=agent.name,
                cli=agent.cli,
                cwd=usage_cwd,
                session_id=usage_session_id,
                pre_existing=usage_pre_existing,
                window_start=usage_window_start,
                window_end=usage_window_end,
                excluded_user_texts=excluded_user_texts,
                secret_values=usage_secret_values,
                outcome_status=outcome_status,
            )
            # The usage record lands in `log.md` *past* the agent's final
            # `bump`/`mark` sync, so without this it lingers uncommitted (and,
            # dirty, blocks the next `git pull` at the checkout gate —
            # merge=union only saves committed content). Commit exactly the
            # log via its union-safe path; it also carries this launch's own
            # log line. A supervised chain reaches this finally per step, so
            # each step's record commits promptly. Non-fatal.
            if isinstance(cfg, Config):
                git.sync_log(cfg, message=f"Log: {session_slug}")
        try:
            prompt_file.unlink()
        except FileNotFoundError:
            pass


def _is_discussion_bootstrap(ref: TaskRef | BootstrapRef) -> bool:
    return isinstance(ref, BootstrapRef) and ref.id_slug in DISCUSSION_BOOTSTRAP_TICKETS


def _bootstrap_kickoff(ref: TaskRef | BootstrapRef) -> str | None:
    if isinstance(ref, BootstrapRef) and ref.id_slug == "bootstrap/ticket":
        return "Begin"
    return None


def _configured_secret_values(
    ticket: Ticket,
    env: dict[str, str],
    *,
    secrets_are_scoped: bool,
) -> tuple[str, ...] | None:
    """Return exact configured values, or None when safe redaction is unknown."""
    try:
        declared = parse_inline_secrets(ticket.secrets)
    except SecretError:
        return None
    values: list[str] = []
    for name, ref in declared:
        if secrets_are_scoped:
            value = env.get(name)
        elif ref.startswith("env:"):
            value = env.get(ref[len("env:") :])
        else:
            # Ambient authoring sessions deliberately do not resolve op://
            # references. A same-named process variable is not proof of the
            # configured value, so suppress activity content rather than risk
            # committing an unredacted secret.
            return None
        if value is None:
            return None
        values.append(value)
    return tuple(values)


def _session_outcome_status(outcome) -> usage_tracking.OutcomeStatus:
    if outcome.kind == "timeout":
        return "timed_out"
    if outcome.kind == "crash" or outcome.exit_code != 0:
        return "failed"
    return "completed"


def _current_step_name(ticket: Ticket) -> str | None:
    current = ticket.current_step()
    if isinstance(current, dict):
        name = current.get("name")
        if isinstance(name, str):
            return name
    return None


def _discussion_template(agent) -> str:
    if agent.discussion:
        return agent.discussion
    return DEFAULT_DISCUSSION_TEMPLATES.get(Path(agent.cli).name, "")


def _echo_launch_iteration(ref: TaskRef | BootstrapRef, ticket: Ticket) -> None:
    current = ticket.current_step()
    if current is None:
        typer.echo(
            f"→ launching {ref.id_slug} "
            f"(status={ticket.status}, assignee={ticket.assignee or 'unassigned'})"
        )
        return
    typer.echo(
        f"→ entering step {ticket.step}: {current['name']} "
        f"(status={ticket.status}, assignee={ticket.assignee or 'unassigned'})"
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
    # marker) without `coga mark done`, so it is still in_progress. There is
    # nothing to advance to; stop and return to the caller. This is distinct from
    # the no-progress case below — don't report it as "still on no workflow
    # step", which reads as a failed step advance.
    if not isinstance(after.workflow, dict):
        return (
            f"{ref.id_slug}: no workflow to chain — task is still in_progress "
            "(agent exited without `coga mark done`); stopping"
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
    assignee: str,
    launch_assignee: str,
    agent_name: str,
) -> str:
    if launch_assignee == assignee:
        return f"launched (assignee={assignee}, agent={agent_name})"
    return (
        f"launched "
        f"(assignee={assignee}, launch_assignee={launch_assignee}, agent={agent_name})"
    )


def _refuse_human_handoff_launch(
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    ticket: Ticket,
    agent_override: str | None,
) -> None:
    assignee = ticket.assignee
    if (
        isinstance(ref, BootstrapRef)
        or is_script_launch(cfg, ticket)
        or not assignee
        or assignee in cfg.agents
    ):
        return
    override = (
        f" with --agent {agent_override!r}" if agent_override is not None else ""
    )
    _bail(
        f"Cannot launch {ref.id_slug}{override}: assignee {assignee!r} "
        "is not a configured agent type. This is a human handoff; "
        "reassign the task to an agent type before launching an agent."
    )


def _interactive_stdio_has_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _refresh_agent_skills_for_launch(coga_os: Path) -> None:
    try:
        result = refresh_agent_skill_view(coga_os)
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
