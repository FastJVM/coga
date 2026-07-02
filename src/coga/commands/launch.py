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
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4

import typer

from coga import usage as usage_tracking
from coga.agent_skills import refresh_agent_skill_view
from coga.blackboard import blackboard_size_warning, format_bytes, open_blockers
from coga.commands.launch_script import is_script_launch
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
    SecretError,
    load_config,
)
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
from coga.repl_supervisor import run_with_done_marker
from coga.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_target,
)
from coga.ticket import Ticket
from coga.validate import TaskValidationError
from coga.workflow import WorkflowError


DISCUSSION_BOOTSTRAP_TICKETS = frozenset({"bootstrap/orient", "bootstrap/ticket"})
DEFAULT_DISCUSSION_TEMPLATES = {
    "claude": "--append-system-prompt {prompt}",
    "codex": "-c developer_instructions={prompt}",
}


def launch(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>` ticket."),
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
    autonomy_override: str | None = typer.Option(
        None,
        "--autonomy",
        help="Run with this autonomy for this launch only (interactive or auto), "
        "overriding the ticket's `autonomy:`. For debugging — the ticket file is "
        "not modified.",
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
) -> str | None:
    """Compose context, start work on a task.

    Returns the termination *kind* of the last interactive REPL the supervisor
    tore down when `return_timeout` is true — `"timeout"` when a liveness limit
    fired — or None for any other ending (clean done, chain completion,
    non-interactive launch). `coga recurring` uses this internal path to record
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

    if autonomy_override is not None and autonomy_override not in ("interactive", "auto"):
        _bail("--autonomy must be 'interactive' or 'auto'")

    def _read(target: TaskRef | BootstrapRef) -> Ticket:
        """Read the ticket, applying the ephemeral `--agent` override.

        `--mode` is deliberately NOT written into `frontmatter` here: the
        same ticket object is handed to `mark_in_progress`, which persists
        it. The mode override is threaded separately to `compose_prompt` and
        `build_agent_command` so the ticket file is never touched.
        """
        t = read_ticket(target)
        if autonomy_override is not None and is_script_launch(cfg, t):
            _bail(
                "--autonomy-override is not supported for script tasks "
                "(they compose no agent prompt)."
            )
        if agent_override is not None and is_bootstrap:
            t.frontmatter["assignee"] = agent_override
        return t

    if prompt_report:
        ticket = _read(ref)
        if is_script_launch(cfg, ticket):
            _bail("script tasks do not compose an agent prompt.")
        try:
            composition = compose_prompt_report(
                cfg, ref, ticket, autonomy_override=autonomy_override
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
        f"(status={ticket.status if not is_bootstrap else 'n/a'}, autonomy={ticket.autonomy}, "
        f"assignee={ticket.assignee or 'unassigned'})"
    )
    if autonomy_override is not None:
        typer.secho(
            f"Launch: autonomy overridden to {autonomy_override!r} for this run "
            "— ticket file unchanged",
            fg=typer.colors.YELLOW,
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
    # script step, an auto launch, or a TTY-less run has no human to discuss
    # with, so those keep the hard refusal (checked here, before any status
    # mutation). `coga megalaunch` never gets this far: it classifies blocked
    # tickets as skipped-unresolved-blocker before launching.
    if not is_bootstrap and isinstance(ref, TaskRef) and ticket.status == "blocked":
        effective_autonomy = autonomy_override or ticket.autonomy
        if (
            effective_autonomy == "interactive"
            and not is_script_launch(cfg, ticket)
            and _interactive_stdio_has_tty()
        ):
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

    # Per-launch `git worktree` isolation (`[launch].worktree`). When on, the
    # whole supervised session — launch-owned status writes, every step's
    # compose, spawn, in-session `coga bump`/`mark`, and usage sync — runs
    # against a private detached worktree instead of the shared primary checkout.
    # `base_cfg` is kept for teardown; `cfg`/`ref` are re-rooted into the
    # worktree so reads, spawns, and syncs all target it. Bootstrap tickets,
    # script launches, and non-git checkouts are unaffected.
    base_cfg = cfg
    worktree_path: Path | None = None
    spawn_cwd: Path | None = None
    script_launch = is_script_launch(cfg, ticket)
    if (
        cfg.launch_worktree
        and isinstance(ref, TaskRef)
        and not is_bootstrap
        and not script_launch
    ):
        cfg, ref, worktree_path = _enter_launch_worktree(base_cfg, ref, task)
        if worktree_path is not None:
            spawn_cwd = worktree_path
            ticket = _read(ref)
            script_launch = is_script_launch(cfg, ticket)

    try:
        # Typing `coga launch` *is* the readiness signal: a draft / paused ticket
        # is brought to `active` inline rather than refused with a "run
        # `coga mark active` first" hint. The flip to `in_progress` still happens
        # later (after the compose pre-flight), so this only does the `mark active`
        # half. Done before the script-mode dispatch so both interactive and script
        # launches start from an activated, stepped ticket.
        if (
            not is_bootstrap
            and isinstance(ref, TaskRef)
            and ticket.status in {"draft", "paused"}
        ):
            _auto_activate(cfg, ref, ticket)

        assignee = ticket.assignee
        if not assignee:
            _bail(f"Task {ref.id_slug} has no assignee")

        # Script vs. agent is deduced, not declared: a step whose skill carries a
        # `script:` (or a no-skill step / workflow-less task with the ticket's own
        # `script:`) runs as a script, with no agent and no composed prompt.
        if script_launch:
            if agent_override is not None:
                _bail(
                    "--agent is only supported for agent (interactive/auto) launches."
                )
            if is_bootstrap:
                _bail("Bootstrap tickets only support interactive/auto launches.")
            from coga.commands.launch_script import run_script_mode
            run_script_mode(cfg, ref, ticket)
            return

        autonomy = autonomy_override or ticket.autonomy

        if autonomy not in ("interactive", "auto"):
            _bail(f"Unknown autonomy: {autonomy!r}")

        if autonomy == "auto":
            # Temporary policy. `claude -p` and `codex exec` buffer stdout until
            # the run completes, so auto launches produce no live console output
            # for the operator. Until coga grows a streaming consumer for the
            # agent's structured output, we refuse rather than let runs sit
            # silently. Re-enable when streaming lands.
            _bail(
                f"Cannot launch {ref.id_slug!r}: autonomy=auto is temporarily disabled. "
                "Auto runs produce no live console output (claude -p and codex exec "
                "buffer until completion), so unattended runs are unobservable. "
                "Set the ticket to autonomy: interactive (and run from a TTY), or "
                "give it a script if the work fits a single script entry point."
            )

        if autonomy == "interactive" and not _interactive_stdio_has_tty():
            _bail(
                f"Cannot launch {ref.id_slug!r}: autonomy=interactive requires a TTY "
                "(stdin and stdout must both be terminals). Run from a real "
                "shell, or give the ticket a script entry point."
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
            _skip_permissions_argv_for_launch(agent, autonomy, ref)
        except ConfigError as exc:
            _bail(str(exc))

        # Fail loud BEFORE flipping status: if a referenced context or skill is
        # missing, the composed prompt would drop a layer the human expected the
        # agent to have. Refuse to start — and don't flip the ticket to
        # in_progress or post a "started" broadcast for a task that never runs.
        # The per-step loop below re-composes; this is a cheap pre-flight (file
        # reads only) so the flip and notification post are never reached on a bad ref.
        try:
            compose_prompt(cfg, ref, ticket, autonomy_override=autonomy_override)
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

        # Interactive launches chain across consecutive agent-owned steps the
        # same way auto mode does. After the agent exits (via autoquit on
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
    except BaseException:
        if worktree_path is not None:
            _cleanup_launch_worktree(base_cfg, cfg, worktree_path)
        raise

    try:
        first_step = True
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
            # cleanly and hand back to the human rather than blocking.
            if shutil.which(agent.cli) is None:
                typer.secho(
                    f"{ref.id_slug}: next step needs agent {step_assignee!r} "
                    f"but its CLI {agent.cli!r} is not on PATH — stopping. "
                    f"Install it, then `coga launch {ref.id_slug}` to continue.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                break
            typer.echo(
                f"Launch: step agent {step_assignee} -> {agent.name} "
                f"(cli={agent.cli})"
            )

            _echo_launch_iteration(ref, ticket)

            # Re-resolve the permission-skip policy for THIS step's agent and
            # the ticket's current mode — supervised chains rotate agents
            # (claude <-> codex), and each agent carries its own local policy.
            try:
                skip_permissions_argv = _skip_permissions_argv_for_launch(
                    agent, autonomy_override or ticket.autonomy, ref
                )
            except ConfigError as exc:
                _bail(str(exc))

            try:
                session = spawn_agent_session(
                    cfg,
                    ref,
                    ticket,
                    agent,
                    autonomy,
                    env=env,
                    actor=f"human:{cfg.current_user}",
                    log_message=_launch_log_message(
                        autonomy,
                        ticket.assignee or assignee,
                        step_assignee or launch_assignee,
                        agent.name,
                    ),
                    autonomy_override=autonomy_override,
                    name=ticket.title or "",
                    discussion=_is_discussion_bootstrap(ref),
                    kickoff=_bootstrap_kickoff(ref),
                    skip_permissions_argv=skip_permissions_argv,
                    idle_timeout=idle_timeout,
                    max_session=max_session,
                    label="Launch",
                    warn_blackboard=True,
                    capture_usage=not is_bootstrap,
                    commit_log=is_bootstrap,
                    cwd=spawn_cwd,
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
                typer.secho(
                    f"Agent timed out (no progress past the liveness limit) — "
                    f"exit {session.exit_code}.",
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
        # Tear down the per-launch worktree on every exit path — clean chain
        # completion, `sys.exit` on a non-zero/timeout agent, or an exception.
        # Driven from `base_cfg` (the primary root); `cfg` now points into the
        # worktree, and git refuses to remove the worktree it is invoked from.
        if worktree_path is not None:
            _cleanup_launch_worktree(base_cfg, cfg, worktree_path)


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


def _enter_launch_worktree(
    cfg: Config, ref: TaskRef, task: str
) -> tuple[Config, TaskRef, Path | None]:
    """Create a per-launch worktree and re-root config/ref into it.

    Returns `(cfg, ref, worktree_path)` re-rooted into a fresh detached worktree
    (keyed by a unique id so a relaunch of a still-running ticket can't collide),
    or the unchanged `(cfg, ref, None)` when there is no git repo to isolate
    within — a non-git checkout has no shared-index race to close. Reaps
    crash-orphaned worktrees first. A genuine `git worktree add` failure is a
    launch refusal, not a silent fall back to the shared checkout: the operator
    opted into isolation, and quietly reintroducing the race would defeat it.
    """
    git.reap_orphan_launch_worktrees(cfg)
    try:
        worktree_path = git.add_launch_worktree(cfg, uuid4().hex)
    except git.GitError as exc:
        _bail(
            f"Cannot launch {ref.id_slug}: [launch].worktree is on but creating "
            f"an isolation worktree failed — {exc}. Fix the git state and retry, "
            "or set [launch].worktree = false to run in the shared checkout."
        )
    if worktree_path is None:
        return cfg, ref, None
    typer.echo(f"Launch: isolating session in worktree {worktree_path}")
    try:
        worktree_repo_root = git.repo_root_in_worktree(cfg, worktree_path)
        _copy_task_state_into_worktree(cfg.repo_root, ref.path, worktree_repo_root)
        _mirror_local_config_into_worktree(cfg.repo_root, worktree_repo_root)
        worktree_cfg = load_config(repo_root=worktree_repo_root)
        worktree_ref = resolve_target(worktree_cfg, task)
    except BaseException:
        # Re-rooting failed after the worktree was created — tear it down so a
        # failed setup never leaks a checkout, then re-raise. (The caller's
        # `finally` only covers a worktree it was handed back.)
        git.remove_launch_worktree(cfg, worktree_path)
        raise
    if not isinstance(worktree_ref, TaskRef):
        # Defensive: a TaskRef in the primary checkout must resolve to a TaskRef
        # in the worktree too (identical tree). If it somehow doesn't, drop the
        # worktree and run unisolated rather than crash the launch.
        git.remove_launch_worktree(cfg, worktree_path)
        return cfg, ref, None
    return worktree_cfg, worktree_ref, worktree_path


def _copy_task_state_into_worktree(
    source_root: Path, source_path: Path, worktree_root: Path
) -> None:
    """Seed the isolated checkout with the live task file/dir from the caller."""
    rel = source_path.relative_to(source_root)
    target = worktree_root / rel
    if source_path.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source_path, target)
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)


def _mirror_local_config_into_worktree(source_root: Path, worktree_root: Path) -> None:
    """Expose ignored machine-local config inside a fresh git worktree."""
    source = source_root / "coga.local.toml"
    if not source.is_file():
        return
    target = worktree_root / "coga.local.toml"
    try:
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(source)
    except OSError:
        shutil.copy2(source, target)


def _cleanup_launch_worktree(
    base_cfg: Config, worktree_cfg: Config, worktree_path: Path
) -> None:
    """Remove a launch worktree only after recoverable Coga state is clean."""
    git.sync_coga_state(worktree_cfg)
    try:
        dirty = git.launch_worktree_has_dirty_coga_state(base_cfg, worktree_path)
    except git.GitError as exc:
        typer.secho(
            f"Launch: leaving isolation worktree {worktree_path} for recovery; "
            f"could not inspect Coga state ({exc}).",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return
    if dirty:
        typer.secho(
            f"Launch: leaving isolation worktree {worktree_path} for recovery; "
            "unsynced Coga state remains.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return
    git.remove_launch_worktree(base_cfg, worktree_path)


def build_agent_command(
    agent,
    mode: str,
    prompt: str,
    *,
    name: str = "",
    discussion: bool = False,
    skip_permissions_argv: tuple[str, ...] = (),
    session_id: str | None = None,
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

    `session_id` uses the agent's `session_id_flag`, when configured, to pin a
    transcript id. `skip_permissions_argv` (the agent's machine-local
    permission-skip argv, threaded by `_skip_permissions_argv_for_launch` only
    when its policy applies) is inserted after the name/session argv and before
    the mode-specific argv/prompt payload — `claude -n <title> --session-id
    <uuid> <skip-argv> -p <prompt>`, `codex <skip-argv> exec <prompt>`.

    `discussion=True` (used for human discussion sessions like `coga chat`
    and `coga ticket`) routes the prompt through the agent's
    `discussion = "..."` template in `coga.toml` so it lands as
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
    session_id_args: list[str] = []
    if session_id and agent.session_id_flag:
        session_id_args = [*shlex.split(agent.session_id_flag), session_id]
    if mode == "interactive":
        return [
            agent.cli,
            *name_args,
            *session_id_args,
            *skip_permissions_argv,
            prompt,
        ]
    return [
        agent.cli,
        *name_args,
        *session_id_args,
        *skip_permissions_argv,
        *shlex.split(agent.auto),
        prompt,
    ]


class AgentSessionResult(NamedTuple):
    exit_code: int
    termination_kind: str


def spawn_agent_session(
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    ticket: Ticket,
    agent,
    mode: str,
    *,
    env,
    actor: str,
    log_message: str,
    autonomy_override: str | None = None,
    name: str = "",
    discussion: bool = False,
    kickoff: str | None = None,
    skip_permissions_argv: tuple[str, ...] = (),
    prompt_suffix: str = "",
    idle_timeout: float | None = None,
    max_session: float | None = None,
    label: str = "Launch",
    warn_blackboard: bool = False,
    capture_usage: bool = False,
    commit_log: bool = False,
    cwd: Path | None = None,
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
    The launch supervisor loop and step chaining deliberately stay outside.

    `commit_log` immediately commits the `log.md` launch append (via
    `sync_log`) instead of leaving it dirty. Callers set it only when no later
    sync will carry the log: a stateless bootstrap-ticket launch has no
    subsequent bump/`sync_paths`, so without this its append blocks the next
    `git pull` at the checkout gate (the append is committed before the REPL
    starts, so even an in-session `git pull` is unblocked). `coga ticket`
    leaves it False — its post-session `sync_paths` folds the log in instead.

    `cwd`, when set, is the working directory the agent subprocess runs in — the
    per-launch `git worktree` under `[launch].worktree` isolation. It also keys
    usage capture (the agent CLI stores its transcript under a hash of its cwd),
    so it must match where the agent actually ran. None (the default) runs in
    the launch process's own cwd — today's shared-checkout behaviour.
    """
    if warn_blackboard:
        warning = blackboard_size_warning(ref.ticket_path)
        if warning:
            typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW, err=True)

    typer.echo(f"{label}: composing prompt")
    prompt = compose_prompt(cfg, ref, ticket, autonomy_override=autonomy_override)
    if prompt_suffix:
        prompt = f"{prompt}{prompt_suffix}"
    prompt_file = write_prompt_file(prompt, ref)
    typer.echo(
        f"{label}: prompt written to {prompt_file} "
        f"({len(prompt)} chars)"
    )

    # Single-file format: usage records live in the `## Usage` section of the
    # ticket's blackboard region, so the usage "blackboard" is the ticket itself.
    usage_blackboard = ref.ticket_path
    should_capture_usage = (
        capture_usage
        and mode in {"interactive", "auto"}
        and isinstance(ref, TaskRef)
        and usage_blackboard.is_file()
    )
    usage_provider = usage_tracking.parser_key_for_cli(agent.cli)
    usage_session_id = (
        str(uuid4()) if should_capture_usage and agent.session_id_flag else None
    )
    usage_pre_existing = (
        usage_tracking.snapshot_session_files(usage_provider)
        if should_capture_usage else set()
    )
    usage_cwd = (cwd or Path.cwd()).resolve()
    usage_window_start = datetime.now(timezone.utc)
    spawn_started = False

    try:
        cmd = build_agent_command(
            agent,
            mode,
            prompt,
            name=name,
            discussion=discussion,
            skip_permissions_argv=skip_permissions_argv,
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

        if mode == "interactive" and name and sys.stdout.isatty():
            sys.stdout.write(f"\033]2;{name}\007")
            sys.stdout.flush()

        if mode == "interactive":
            # Interactive REPLs (`claude`, `codex`) don't exit on their own.
            # Run through a PTY watcher so an agent that writes the session-done
            # sentinel after `coga mark done` / `coga block` releases the REPL.
            spawn_started = True
            outcome = run_with_done_marker(
                cmd,
                env,
                session_id=str(ref.path.resolve()),
                idle_timeout=idle_timeout,
                max_session=max_session,
                cwd=cwd,
            )
            return AgentSessionResult(outcome.exit_code, outcome.kind)

        spawn_started = True
        result = subprocess.run(
            cmd, env=env, check=False, cwd=str(cwd) if cwd is not None else None
        )
        return AgentSessionResult(result.returncode, "natural")
    except FileNotFoundError:
        spawn_started = False
        raise
    finally:
        usage_window_end = datetime.now(timezone.utc)
        if should_capture_usage and spawn_started:
            usage_tracking.capture_session(
                blackboard=usage_blackboard,
                title=ticket.title or "",
                slug=ref.id_slug,
                step=_current_step_name(ticket),
                agent=agent.name,
                cli=agent.cli,
                cwd=usage_cwd,
                session_id=usage_session_id,
                pre_existing=usage_pre_existing,
                window_start=usage_window_start,
                window_end=usage_window_end,
            )
            # The `## Usage` record is appended *past* the agent's final
            # `bump`/`mark` sync, so without this it lingers uncommitted on the
            # working tree forever. Commit it (and anything else dirty under
            # `coga/`) now. A supervised chain reaches this finally per step but
            # the CLI-dispatch sweep only once at the end of the whole launch, so
            # this is what commits each step's usage promptly. Non-fatal.
            git.sync_coga_state(cfg)
        try:
            prompt_file.unlink()
        except FileNotFoundError:
            pass


def _skip_permissions_argv_for_launch(
    agent, mode: str, ref: TaskRef | BootstrapRef
) -> tuple[str, ...]:
    """Resolve the permission-skip argv for one agent spawn, or `()`.

    The policy is machine-local per-agent config (`coga.local.toml`
    `[agents.<name>] skip_permissions = "auto"`) and applies only to normal
    task tickets running in effective `mode: auto`. Bootstrap/discussion
    tickets and interactive/script launches always get `()` — today's
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
            "skip_permissions_argv in coga.local.toml. Set it (e.g. "
            f"`[agents.{agent.name}] skip_permissions_argv = \"...\"`) or "
            "remove the skip_permissions policy."
        )
    return agent.skip_permissions_argv


def _is_discussion_bootstrap(ref: TaskRef | BootstrapRef) -> bool:
    return isinstance(ref, BootstrapRef) and ref.id_slug in DISCUSSION_BOOTSTRAP_TICKETS


def _bootstrap_kickoff(ref: TaskRef | BootstrapRef) -> str | None:
    if isinstance(ref, BootstrapRef) and ref.id_slug == "bootstrap/ticket":
        return "Begin"
    return None


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
            f"(status={ticket.status}, mode={ticket.autonomy}, assignee={ticket.assignee or 'unassigned'})"
        )
        return
    typer.echo(
        f"→ entering step {ticket.step}: {current['name']} "
        f"(status={ticket.status}, mode={ticket.autonomy}, assignee={ticket.assignee or 'unassigned'})"
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
