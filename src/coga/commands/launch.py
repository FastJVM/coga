"""`coga launch` — compose context and start work on a task.

Launching an `active` task moves it to `in_progress`. A draft / paused ticket
is activated inline first — typing `coga launch` is the readiness signal, so
launch performs the `coga mark active` step itself rather than refusing. (A
workflow-less or required-extension-incomplete ticket still can't be activated,
so those fail loud with the same remedy `mark active` gives.) An
already-`in_progress` ticket resumes without another status flip. Terminal
`done` / `canceled` tickets are refused and left untouched.

Human-owned steps remain unlaunchable by default. An explicit `--agent`
override starts one visible assist session without rewriting `assignee:`.

Bootstrap tickets are stateless re-entry points (no status, no log of state
changes) — launch is the only way to run a skill against one.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NamedTuple
from uuid import uuid4

import typer

from coga import usage as usage_tracking
from coga.agent_skills import refresh_agent_skill_view
from coga.autoclose import parse_branch_name, parse_pr_url, parse_worktree_path
from coga.blackboard import blackboard_size_warning, format_bytes, open_blockers
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
from coga import pr_assist
from coga.lifecycle import TERMINAL_STATUSES
from coga.logfile import append_log, log_path
from coga.mark import (
    BlackboardNeedsSynthesis,
    RequiredExtensionMissing,
    WorkflowMissing,
    format_blackboard_synthesis_refusal,
    mark_active,
    mark_blocked,
    mark_in_progress,
    prepare_active,
)
from coga.notification import preflight_post
from coga.paths import PackagedResourceMissing, read_packaged_resource
from coga.open_pr import same_git_checkout
from coga.repl_supervisor import (
    ASSIST_BRANCH_ENV,
    ASSIST_PR_ENV,
    EXPECTED_STEP_ENV,
    EXPECTED_TASK_ENV,
    AgentCliNotFound,
    run_with_done_marker,
)
from coga.task_env import apply_task_env
from coga.step_gate import gate_publishes_current_branch
from coga.taskfile import split_body
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
_ASSIST_ALIGNMENT_ATTEMPTS = 3


class _AssistPublicationRefused(ComposeError):
    """A retryable assist write was intentionally left out of the final sweep."""

    def __init__(self, message: str, *, post_session: bool = False):
        super().__init__(message)
        self.post_session = post_session


def launch(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>` ticket."),
    args: list[str] | None = typer.Argument(
        None,
        help="Trailing positional arguments for the launch target. They appear "
        "as an ordered Launch arguments block in the composed agent prompt.",
    ),
    agent_override: str | None = typer.Option(
        None,
        "--agent",
        help="Explicit agent override for this launch, including an assist on "
        "a human-owned step; never rewrites the ticket assignee.",
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
    launch_args: list[str] = list(args) if isinstance(args, (list, tuple)) else []

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_target(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    is_bootstrap = isinstance(ref, BootstrapRef)

    # A supported single-checkout assist may be behind its published PR branch.
    # Align before refreshing the agent-skill view or deriving any launch state:
    # the fetched commit can change coga.toml, the ticket, or a composed skill.
    # Reload and repeat after every fast-forward so publication authorization,
    # secrets, expected step, prompt, and command all come from the final tree.
    aligned_assist_branch: str | None = None
    aligned_assist_remote_oid: str | None = None
    if not prompt_report and agent_override is not None:
        for _ in range(_ASSIST_ALIGNMENT_ATTEMPTS):
            alignment_ticket = read_ticket(ref)
            candidate_assist_branch = (
                None
                if is_bootstrap
                else _recorded_single_checkout_assist_branch(cfg, alignment_ticket)
            )
            if (
                is_bootstrap
                or alignment_ticket.status
                not in {"draft", "active", "in_progress", "paused", "blocked"}
                or not _interactive_stdio_has_tty()
                or candidate_assist_branch is None
            ):
                break
            try:
                pr_head_oid = _verify_recorded_assist_pr_head(
                    cfg, alignment_ticket, candidate_assist_branch
                )
                moved, remote_oid = _align_recorded_assist_checkout(
                    cfg, alignment_ticket
                )
                if remote_oid != pr_head_oid:
                    raise git.FeaturePublicationError(
                        f"configured remote {cfg.git_remote!r} branch "
                        f"{candidate_assist_branch!r} is at {remote_oid}, but "
                        f"the recorded PR head is {pr_head_oid}"
                    )
            except git.GitError as exc:
                _bail(
                    f"Cannot launch {ref.id_slug}: could not verify and align "
                    f"the recorded assist checkout before composing the "
                    f"prompt: {exc}"
                )
            if not moved:
                aligned_assist_branch = candidate_assist_branch
                aligned_assist_remote_oid = remote_oid
                break
            try:
                cfg = load_config(cfg.repo_root)
                ref = resolve_target(cfg, task)
            except (ConfigError, TaskNotFoundError) as exc:
                _bail(str(exc))
            is_bootstrap = isinstance(ref, BootstrapRef)
        else:
            _bail(
                f"Cannot launch {ref.id_slug}: the recorded assist branch moved "
                f"during {_ASSIST_ALIGNMENT_ATTEMPTS} consecutive alignment "
                "attempts; retry once the PR branch is stable."
            )

    # Alignment may fast-forward coga.toml itself. Resolve an explicit override
    # only after that final tree is authoritative for the launch.
    if agent_override is not None:
        try:
            cfg.agent_type(agent_override)
        except ConfigError as exc:
            _bail(str(exc))

    _refresh_agent_skills_for_launch(cfg.repo_root)

    def _read(target: TaskRef | BootstrapRef) -> Ticket:
        """Read the ticket, applying the ephemeral `--agent` override."""
        t = read_ticket(target)
        if agent_override is not None and is_bootstrap:
            t.frontmatter["assignee"] = agent_override
        return t

    if prompt_report:
        ticket = _read(ref)
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
        f"assignee={ticket.assignee or 'unassigned'})",
    )

    # A terminal ticket is closed: launching it must not restart its frozen
    # workflow. Re-activating would re-seed `step: 1` without re-resolving
    # `assignee` (which still holds the final step's resolved human owner),
    # crashing the agent-type lookup and leaving the ticket wedged
    # (`active, step 1, assignee=<human>`). Refuse loud. Draft/paused still
    # activate inline below.
    if (
        not is_bootstrap
        and isinstance(ref, TaskRef)
        and ticket.status in TERMINAL_STATUSES
    ):
        _bail(
            f"Cannot launch {ref.id_slug}: it is {ticket.status}, a terminal "
            "status; nothing to launch. Launch a different ticket."
        )

    blocked_resume = False

    # A blocked ticket may be launched only by an explicit interactive human
    # act: the session's first job becomes resolving the open asks with the
    # human (the composed prompt gains a resolve-or-re-block preamble keyed
    # off the blackboard's open blockers), and the ticket reactivates inline
    # after preflights pass. Batch surfaces are unchanged — a TTY-less run has
    # no human to discuss with, so it keeps the hard refusal (checked here,
    # before any status mutation). `coga
    # megalaunch` never gets this far: its sweep classifies blocked tickets as
    # skipped-unresolved-blocker, and an explicit pick runs the same
    # activate-and-resume through the engine's own launch loop.
    if not is_bootstrap and isinstance(ref, TaskRef) and ticket.status == "blocked":
        if _interactive_stdio_has_tty():
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

    # Refuse unoverridden human handoffs up front: a human-owned
    # active/in-progress step should report the handoff directly, before any
    # status mutation. An explicit override is the on-demand assist path.
    if not is_bootstrap and ticket.status not in {"draft", "paused"}:
        _refuse_human_handoff_launch(cfg, ref, ticket, agent_override)

    assignee = ticket.assignee
    if not assignee:
        _bail(f"Task {ref.id_slug} has no assignee")
    human_assist = (
        not is_bootstrap
        and agent_override is not None
        and assignee not in cfg.agents
    )
    single_checkout_assist_branch = (
        _recorded_single_checkout_assist_branch(cfg, ticket)
        if human_assist and isinstance(ref, TaskRef)
        else None
    )
    if single_checkout_assist_branch is not None and (
        single_checkout_assist_branch != aligned_assist_branch
        or aligned_assist_remote_oid is None
    ):
        _bail(
            f"Cannot launch {ref.id_slug}: the recorded assist branch "
            "changed after alignment; retry once the PR branch is stable."
        )
    if single_checkout_assist_branch is not None:
        try:
            current_pr_head_oid = _verify_recorded_assist_pr_head(
                cfg, ticket, single_checkout_assist_branch
            )
        except git.FeaturePublicationError as exc:
            _bail(f"Cannot launch {ref.id_slug}: {exc}")
        if current_pr_head_oid != aligned_assist_remote_oid:
            _bail(
                f"Cannot launch {ref.id_slug}: recorded PR head moved from "
                f"{aligned_assist_remote_oid} to {current_pr_head_oid} after "
                "checkout alignment; retry once the PR branch is stable."
            )
    assist_publication = (
        git.FeaturePublicationLease(
            branch=single_checkout_assist_branch,
            local_oid=aligned_assist_remote_oid,
            remote_oid=aligned_assist_remote_oid,
        )
        if single_checkout_assist_branch is not None
        and aligned_assist_remote_oid is not None
        else None
    )
    assist_pr_guard = (
        _assist_pr_publication_guard(
            cfg,
            ref,
            single_checkout_assist_branch,
        )
        if isinstance(ref, TaskRef)
        and single_checkout_assist_branch is not None
        else None
    )
    try:
        # Typing `coga launch` *is* the readiness signal: a draft / paused ticket
        # is brought to `active` inline rather than refused with a "run
        # `coga mark active` first" hint. The flip to `in_progress` still happens
        # later (after the compose pre-flight), so this only does the `mark active`
        # half.
        if (
            not is_bootstrap
            and isinstance(ref, TaskRef)
            and ticket.status in {"draft", "paused"}
            and assist_publication is None
        ):
            _auto_activate(cfg, ref, ticket)

        _refuse_human_handoff_launch(cfg, ref, ticket, agent_override)

        if not _interactive_stdio_has_tty():
            _bail(
                f"Cannot launch {ref.id_slug!r}: an agent launch requires a TTY "
                "(stdin and stdout must both be terminals). Run from a real "
                "shell. Use a registered `coga run` recipe for deterministic "
                "unattended work."
            )

        launch_assignee = agent_override or assignee
        if human_assist:
            typer.echo(
                f"Launch: agent {agent_override} assisting on human-owned step "
                f"(assignee={assignee}; ticket assignment unchanged)"
            )

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
        except FileNotFoundError as exc:
            # A layer file that exists at resolve time but not at read time
            # (a concurrent checkout, a mid-sync working tree). Loud either
            # way, but name the path instead of dumping a traceback.
            _bail(missing_launch_file_message(exc))

        # Preflight and build the child env before mutating ticket state. A missing
        # declared secret is a launch refusal, not a started task.
        try:
            env = build_launch_env(cfg, ticket.secrets)
        except SecretError as exc:
            _bail(str(exc))

        # Strict assist state is published before its start notification. Catch
        # reproducible notification configuration errors while both branches
        # and the working tree still hold the pre-launch lifecycle state.
        if assist_publication is not None and ticket.status != "in_progress":
            try:
                preflight_post(cfg)
            except typer.Exit:
                _bail(
                    f"Cannot launch {ref.id_slug}: notification configuration "
                    "must be valid before assist lifecycle state is published."
                )

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

        if assist_publication is not None:
            try:
                current_pr_head_oid = _verify_recorded_assist_pr_head(
                    cfg, ticket, assist_publication.branch
                )
            except git.FeaturePublicationError as exc:
                _bail(
                    f"Cannot launch {ref.id_slug}: the recorded PR could not be "
                    f"re-verified before lifecycle publication. No agent was "
                    f"started: {exc}"
                )
            if current_pr_head_oid != assist_publication.remote_oid:
                _bail(
                    f"Cannot launch {ref.id_slug}: the recorded PR head moved "
                    "during launch preflight; retry so the prompt and lifecycle "
                    "state use the same tip. No agent was started."
                )
            try:
                fresh_publication = git.feature_publication_lease(
                    cfg,
                    ref.path,
                    assist_publication.branch,
                )
            except git.FeaturePublicationError as exc:
                _bail(
                    f"Cannot launch {ref.id_slug}: the recorded assist state "
                    "no longer matches the PR and control branches. No agent "
                    f"was started: {exc}"
                )
            if fresh_publication.remote_oid != current_pr_head_oid:
                _bail(
                    f"Cannot launch {ref.id_slug}: the recorded PR branch moved "
                    "while its control state was being verified. Retry so the "
                    "prompt and lifecycle state use one exact tip. No agent "
                    "was started."
                )
            assist_publication = fresh_publication

        if blocked_resume and isinstance(ref, TaskRef) and ticket.status == "blocked":
            if assist_publication is None:
                _auto_activate(cfg, ref, ticket)

        if (
            isinstance(ref, TaskRef)
            and ticket.status == "active"
            and assist_publication is None
        ):
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
            except git.FeaturePublicationError as exc:
                _bail(
                    "The recorded PR branch moved before lifecycle state could "
                    f"be published. No agent was started: {exc}"
                )
            except TaskValidationError as exc:
                _bail(str(exc))

        # Agent launches chain across consecutive agent-owned steps. After the
        # agent exits (via autoquit on
        # `coga bump` / `mark done` / `mark canceled` / `block`, or via
        # `/exit`), we re-read the
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
        if single_checkout_assist_branch is None:
            _refresh_launch_checkout(cfg)
        raise

    suppress_assist_refresh = False
    try:
        first_step = True
        while True:
            ticket = _read(ref)

            # Resolve the agent for THIS step from the ticket's current
            # assignee, so the supervisor can rotate claude <-> codex across
            # the workflow. The `--agent` override applies only to the first
            # step; chained steps follow the ticket. A human-owned first step
            # reaches here only through that explicit assist. Later human
            # handoffs stop in `_harness_stop_reason` before a relaunch.
            assist_session = (
                first_step
                and human_assist
                and ticket.assignee not in cfg.agents
            )
            publish_assist_branch = (
                single_checkout_assist_branch if assist_session else None
            )
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
            spawn_ticket = ticket
            before_spawn: Callable[[], None] | None = None
            if publish_assist_branch is not None:
                if not isinstance(ref, TaskRef) or assist_pr_guard is None:
                    _bail(
                        f"Cannot start {ref.id_slug}'s assist: its recorded "
                        "publication guard is unavailable."
                    )
                try:
                    spawn_ticket = _prospective_assist_ticket(cfg, ref, ticket)
                except ComposeError as exc:
                    _bail(str(exc))

                def publish_lifecycle() -> None:
                    _publish_assist_lifecycle_before_spawn(
                        cfg,
                        ref,
                        expected=ticket,
                        branch=publish_assist_branch,
                        launch_assignee=step_assignee or launch_assignee,
                        publication_guard=assist_pr_guard,
                    )

                before_spawn = publish_lifecycle
            step_env = dict(env)
            step_env[EXPECTED_TASK_ENV] = str(ref.path.resolve())
            step_env[EXPECTED_STEP_ENV] = spawn_ticket.step or ""

            try:
                session = spawn_agent_session(
                    cfg,
                    ref,
                    spawn_ticket,
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
                        _agent_args_prompt_suffix(launch_args)
                        + (_queue_prompt_suffix() if queue_guidance else "")
                    ),
                    idle_timeout=idle_timeout,
                    max_session=max_session,
                    label="Launch",
                    warn_blackboard=True,
                    # A proven recorded single-checkout assist runs on the PR
                    # branch itself. Commit the launch audit line before
                    # spawning so the clean-tree gate does not trip on Coga's
                    # own log.
                    commit_log=is_bootstrap or bool(publish_assist_branch),
                    # Publish generated assist state only from the recorded
                    # branch and an aligned configured remote.
                    publish_aligned_branch=publish_assist_branch,
                    feature_publication_guard=assist_pr_guard,
                    before_spawn=before_spawn,
                )
            except _AssistPublicationRefused as exc:
                suppress_assist_refresh = True
                if exc.post_session and blocked_resume:
                    try:
                        _reblock_unresolved_resume(
                            cfg,
                            ref,
                            step_assignee or launch_assignee,
                            feature_branch=publish_assist_branch,
                            feature_publication_guard=assist_pr_guard,
                        )
                    except _AssistPublicationRefused as reblock_exc:
                        _bail(
                            f"{exc} Automatic unresolved re-block also "
                            f"refused: {reblock_exc}",
                            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
                        )
                    blocked_resume = False
                _bail(
                    str(exc),
                    exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
                )
            except ComposeError as exc:
                _bail(str(exc))
            except AgentCliNotFound:
                _bail(f"Failed to spawn agent: {agent.cli!r} not found.")
            except FileNotFoundError as exc:
                _bail(missing_launch_file_message(exc))

            typer.echo(f"Launch: agent exited with code {session.exit_code}")
            if blocked_resume:
                try:
                    _reblock_unresolved_resume(
                        cfg,
                        ref,
                        step_assignee or launch_assignee,
                        feature_branch=publish_assist_branch,
                        feature_publication_guard=assist_pr_guard,
                    )
                except _AssistPublicationRefused as exc:
                    suppress_assist_refresh = True
                    _bail(
                        str(exc),
                        exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
                    )
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
        if not suppress_assist_refresh:
            refreshed = _refresh_launch_checkout(
                cfg,
                expected_assist_branch=single_checkout_assist_branch,
                feature_publication_guard=assist_pr_guard,
            )
            if single_checkout_assist_branch is not None and not refreshed:
                _bail(
                    "The recorded PR branch could not be safely refreshed "
                    "during assist teardown. Generated state remains dirty "
                    "for an explicit retry and the catch-all sweep has been "
                    "suppressed.",
                    exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
                )


# --- helpers ------------------------------------------------------------------


def _prospective_assist_ticket(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
) -> Ticket:
    """Return the lifecycle view composed for a child that has not started yet."""
    prospective = Ticket(
        frontmatter=dict(ticket.frontmatter),
        body=ticket.body,
    )
    if prospective.status in {"draft", "paused", "blocked"}:
        try:
            prepare_active(cfg, ref, prospective)
        except WorkflowMissing as exc:
            raise ComposeError(
                f"Cannot launch {ref.id_slug}: it is {ticket.status!r} and has "
                "no workflow, so there is nothing to activate or advance."
            ) from exc
        except WorkflowError as exc:
            raise ComposeError(
                f"Cannot launch {ref.id_slug}: its `workflow:` ref could not "
                f"be frozen — {exc}"
            ) from exc
        except RequiredExtensionMissing as exc:
            names = ", ".join(repr(field) for field in exc.fields)
            raise ComposeError(
                f"Cannot launch {ref.id_slug}: required extension field(s) "
                f"empty: {names}."
            ) from exc
        except BlackboardNeedsSynthesis as exc:
            raise ComposeError(
                format_blackboard_synthesis_refusal(
                    ref.id_slug,
                    action="launch",
                    reason=exc.reason,
                )
            ) from exc
    if prospective.status == "active":
        prospective.frontmatter["status"] = "in_progress"
    if prospective.status != "in_progress":
        raise ComposeError(
            f"Cannot launch {ref.id_slug}: assist lifecycle changed to "
            f"{prospective.status!r} before spawn."
        )
    return prospective


def _publish_assist_lifecycle_before_spawn(
    cfg: Config,
    ref: TaskRef,
    *,
    expected: Ticket,
    branch: str,
    launch_assignee: str,
    publication_guard: Callable[[str], None],
) -> None:
    """Publish lifecycle state at the last boundary before the child process."""
    current = read_ticket(ref)
    if current.render() != expected.render():
        raise _AssistPublicationRefused(
            "The ticket changed after assist composition. No agent was "
            "started; retry so the prompt and lifecycle state come from the "
            "same ticket revision."
        )
    try:
        publication = git.feature_publication_lease(cfg, ref.path, branch)
        publication_guard(publication.remote_oid)
    except git.FeaturePublicationError as exc:
        raise _AssistPublicationRefused(
            "The recorded PR or control state changed after assist "
            f"composition. No agent was started: {exc}"
        ) from exc

    if current.status == "in_progress":
        return

    snapshot = _snapshot_assist_state(cfg, ref)
    try:
        if current.status in {"draft", "paused", "blocked"}:
            mark_active(
                cfg,
                ref,
                current,
                actor=f"human:{cfg.current_user}",
                log_message=(
                    f"activated ({current.status} → active) — auto on launch"
                ),
                echo=f"{ref.id_slug}: active — auto on launch",
                sync_state=False,
            )
        if current.status != "active":
            raise git.FeaturePublicationError(
                f"assist lifecycle changed to {current.status!r} before spawn"
            )
        mark_in_progress(
            cfg,
            ref,
            current,
            actor=f"human:{cfg.current_user}",
            log_message="started (active → in_progress) via coga launch",
            slack_text=(
                f"▶️ {cfg.current_user} started *{ref.id_slug}* "
                f"\"{current.title}\" (assignee: {launch_assignee})"
            ),
            echo=f"{ref.id_slug}: in_progress",
            feature_publication=publication,
            feature_publication_guard=publication_guard,
            before_sync=snapshot.arm,
        )
    except BaseException as exc:
        rollback_note = _restore_assist_state(snapshot)
        if isinstance(
            exc,
            (
                BlackboardNeedsSynthesis,
                RequiredExtensionMissing,
                TaskValidationError,
                WorkflowError,
                WorkflowMissing,
                git.FeaturePublicationError,
            ),
        ):
            raise _AssistPublicationRefused(
                "The assist lifecycle could not be published at the final "
                f"spawn gate. No agent was started: {exc}{rollback_note}"
            ) from exc
        raise


def _snapshot_assist_state(
    cfg: Config, ref: TaskRef
) -> git.FileMutationRollback:
    """Capture the two files launch may mutate before a child actually starts."""
    paths = (ref.ticket_path, log_path(cfg))
    return git.FileMutationRollback.capture(
        paths,
        union_paths=(log_path(cfg),),
    )


def _restore_assist_state(snapshot: git.FileMutationRollback) -> str:
    """Conditionally restore refused assist state; report retained peer edits."""
    refused = snapshot.restore()
    if not refused:
        return ""
    names = ", ".join(str(path) for path in refused)
    return (
        "; concurrent edits were retained instead of being overwritten at "
        f"{names}"
    )


def _auto_activate(
    cfg: Config, ref: TaskRef, ticket: Ticket, *, sync_state: bool = True
) -> None:
    """Bring a draft / paused / resumable blocked ticket to `active` inline.

    `coga launch` used to refuse any status but `active`/`in_progress` and
    point the operator at `coga mark active`. Now launching *is* the
    readiness decision, so we run that activation here. The core `mark_active`
    mutates `ticket` in place — status → active, a bare-string `workflow:`
    frozen, and `step:` seeded — so the later `mark_in_progress` flip fires off
    the same object. (A terminal ticket never reaches here: launch refuses it
    earlier rather than restart closed work. A blocked ticket reaches
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
            sync_state=sync_state,
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
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    blocker: str | None,
    *,
    feature_branch: str | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
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
    feature_publication = None
    if feature_branch is not None:
        try:
            feature_publication = git.feature_publication_lease(
                cfg, ref.path, feature_branch
            )
        except git.FeaturePublicationError as exc:
            raise _AssistPublicationRefused(
                f"Could not return {ref.id_slug} to blocked on the recorded "
                f"assist branch after the unresolved session: {exc}"
            ) from exc
    rollback = (
        _snapshot_assist_state(cfg, ref)
        if feature_publication is not None
        else None
    )
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
            feature_publication=feature_publication,
            feature_publication_guard=feature_publication_guard,
            before_sync=rollback.arm if rollback is not None else None,
        )
    except git.FeaturePublicationError as exc:
        rollback_note = ""
        if rollback is not None:
            rollback_note = _restore_assist_state(rollback)
        message = (
            f"Could not publish {ref.id_slug}'s unresolved blocked state to "
            f"the recorded assist branch: {exc}{rollback_note}"
        )
        if feature_branch is not None:
            raise _AssistPublicationRefused(
                message,
                post_session=True,
            ) from exc
        _bail(message)
    except TaskValidationError as exc:
        rollback_note = ""
        if rollback is not None:
            rollback_note = _restore_assist_state(rollback)
        if feature_branch is not None:
            raise _AssistPublicationRefused(
                f"{exc}{rollback_note}",
                post_session=True,
            ) from exc
        _bail(f"{exc}{rollback_note}")


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


def _refresh_launch_checkout(
    cfg: Config,
    *,
    expected_assist_branch: str | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
) -> bool:
    """Pull the control branch's task state back into the launch checkout.

    Runs once on every exit path the supervisor sees, so the operator's
    checkout never stays stale until a manual pull. The git layer reports
    failures on stderr + the log and returns a safety result. Ordinary launches
    keep that advisory; a recorded assist treats False as a no-sweep retry so a
    retained audit/refresh write cannot be committed by the CLI catch-all. A
    proven recorded single-checkout assist also asks the refresh layer to keep
    generated state aligned with the feature remote, pinned to the branch the
    session started on. If the agent changed branches, teardown leaves that
    checkout alone. Unproven checkouts retain ordinary local-only behavior.
    """
    return git.refresh_coga_state_from_control(
        cfg,
        message="Refresh coga state after launch",
        publish_if_remote_aligned=expected_assist_branch is not None,
        expected_feature_branch=expected_assist_branch,
        feature_publication_guard=feature_publication_guard,
    )


def _recorded_single_checkout_assist_branch(
    cfg: Config, ticket: Ticket
) -> str | None:
    """The recorded PR branch when launch runs in its exact recorded checkout.

    Human ownership plus an explicit override authorizes the assist, but it
    does not prove that the checkout running `coga launch` owns the recorded
    branch. The current checkout must equal `worktree:`, be on `branch:`, and
    carry a recorded `pr:` link before launch may even attempt the live PR-head
    verification that authorizes publication. A different checkout, a missing
    `## Dev` field, or a different current branch returns None and retains
    ordinary local-only log handling. Linked worktrees and independent fallback
    clones are supported when they are themselves the exact recorded checkout.
    """
    if not cfg.git_enabled:
        return None
    _, blackboard = split_body(ticket.body)
    branch = parse_branch_name(blackboard or "")
    worktree = parse_worktree_path(blackboard or "")
    pr_url = parse_pr_url(blackboard or "")
    if not branch or not worktree or not pr_url:
        return None
    try:
        root = git._toplevel(cfg.repo_root)
        matches = bool(
            root is not None
            and same_git_checkout(cfg.repo_root, worktree)
            and git._current_branch(root) == branch
        )
        return branch if matches else None
    except git.GitError:
        return None


def _verify_recorded_assist_pr_head(
    cfg: Config, ticket: Ticket, branch: str
) -> str:
    """Compatibility seam around the shared PR-assist verifier."""
    return pr_assist.verify_recorded_assist_pr_head(cfg, ticket, branch)


def _assist_pr_publication_guard(
    cfg: Config,
    ref: TaskRef,
    branch: str,
) -> Callable[[str], None]:
    """Re-prove an open recorded PR immediately before a generated push."""

    def guard(expected_remote_oid: str) -> None:
        try:
            current = read_ticket(ref)
        except Exception as exc:
            raise git.FeaturePublicationError(
                "could not re-read the recorded assist ticket"
            ) from exc
        _, blackboard = split_body(current.body)
        recorded_branch = parse_branch_name(blackboard or "")
        if recorded_branch != branch:
            raise git.FeaturePublicationError(
                f"recorded assist branch changed from {branch!r} to "
                f"{recorded_branch!r}"
            )
        live_pr_oid = _verify_recorded_assist_pr_head(cfg, current, branch)
        if live_pr_oid != expected_remote_oid:
            raise git.FeaturePublicationError(
                f"recorded PR head moved from expected {expected_remote_oid} "
                f"to {live_pr_oid}"
            )

    return guard


def _align_recorded_assist_checkout(
    cfg: Config, ticket: Ticket
) -> tuple[bool, str]:
    """Fast-forward a verified recorded assist checkout before launch derivation.

    Returns whether HEAD moved plus the exact fetched remote OID. A
    merely-behind checkout with unrelated dirt, a missing remote branch, or an
    ahead/diverged tip raises instead of composing from stale files. The
    union-safe audit log is the sole permitted dirty path so a prior interrupted
    launch can recover on retry without losing its append.
    """
    _, blackboard = split_body(ticket.body)
    branch = parse_branch_name(blackboard or "")
    root = git._toplevel(cfg.repo_root)
    if root is None or not branch or not git._remote_configured(root, cfg.git_remote):
        raise git.GitError("the recorded assist checkout has no configured remote")
    before = git._run_git(root, "rev-parse", "HEAD").strip()
    log_rel = git._relative_to_root(root, log_path(cfg))
    publication = git._prepare_feature_branch_publication(
        root,
        cfg.git_remote,
        branch,
        preserve_union_rel=log_rel,
        require_single_push_url=True,
    )
    if not publication.aligned or publication.remote_oid is None:
        raise git.GitError(publication.detail)
    after = git._run_git(root, "rev-parse", "HEAD").strip()
    return before != after, publication.remote_oid


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
        prompt = read_packaged_resource("prompt-queue.md")
    except PackagedResourceMissing as exc:
        raise ComposeError(str(exc)) from exc
    return f"\n\n{prompt.strip()}\n"


def _agent_args_prompt_suffix(args: list[str]) -> str:
    """Render one launch invocation's positional args as prompt input.

    JSON preserves argument boundaries (including whitespace and newlines),
    and an indented code block cannot be closed by an argument containing a
    Markdown fence. This remains an ephemeral suffix rather than a durable
    compose layer because launch arguments are invocation state, not ticket
    state.
    """
    if not args:
        return ""
    encoded = json.dumps(args, ensure_ascii=False)
    return (
        "\n\n## Launch arguments\n\n"
        "The operator supplied these positional arguments to this launch, in "
        "order. Treat the JSON array as inputs to the launch target and "
        "preserve each value's boundary:\n\n"
        f"    {encoded}\n"
    )


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


def missing_launch_file_message(exc: FileNotFoundError) -> str:
    """Report a pre-spawn `FileNotFoundError` as the missing file it is.

    `spawn_agent_session` composes the prompt, writes it to disk, and appends
    the log *before* it spawns anything, so a `FileNotFoundError` escaping it
    is far more often a missing prompt layer than a missing agent CLI — and
    blaming the CLI sends the operator to debug a PATH that is fine. Name the
    path instead; `AgentCliNotFound` carries the genuine CLI case.
    """
    missing = exc.filename or "a file it needed"
    detail = exc.strerror or str(exc)
    return (
        f"Launch failed before the agent started: {missing} ({detail}). "
        "This is a file the launch had to read or write — a prompt layer "
        "(skill, context, ticket) or the prompt destination — not the agent "
        "CLI."
    )


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
    publish_aligned_branch: str | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
    before_spawn: Callable[[], None] | None = None,
    secrets_are_scoped: bool = True,
    stateless_identity: tuple[str, str] | None = None,
    include_blocker_preamble: bool = True,
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
    `include_blocker_preamble` is disabled only for guided authoring: the
    resolve-or-re-block directive belongs to task execution, while an authoring
    session must leave a blocked ticket and its open asks intact.
    The launch supervisor loop and step chaining deliberately stay outside.

    `commit_log` immediately commits the `log.md` launch append (via
    `sync_log`) instead of leaving it dirty. Stateless bootstrap launches use
    it because no later task-state sync will carry the log. An explicit assist
    on a human-owned step also uses it only after proving the launch checkout is
    the recorded primary PR worktree on the recorded branch.
    `publish_aligned_branch` is that assist's narrower publication rule: a
    merely-behind branch is fast-forwarded while preserving the pending
    union-log append, then pre-session and teardown log-only commits reach the
    feature remote only from an aligned tip on the exact recorded branch, so a
    branch switch or unrelated unpushed work never rides along. `coga ticket`
    leaves both publication arguments unset because its post-session record is
    committed by the shared teardown sync. `secrets_are_scoped` is False only
    when the caller passes an ambient environment instead of
    `build_launch_env`; that distinction keeps redaction from mistaking an
    unrelated same-named variable for a configured secret value.
    ``before_spawn`` runs after prompt, argv, and pre-session audit publication
    have all succeeded. The human-assist path uses that final boundary to
    publish lifecycle state immediately before entering the PTY supervisor.
    """
    # A nested launch inherits its parent's process environment. Re-derive the
    # task metadata at this last shared boundary so an agent identifies the
    # task it is actually running. `apply_task_env` copies first, so
    # caller-owned environments remain unchanged and unrelated parent values
    # still pass through — but it clears the whole task namespace before
    # rewriting it, so a variable this target does not export (a stateless
    # bootstrap ticket's absent `COGA_TASK_BLACKBOARD`) cannot survive by
    # inheritance.
    env = apply_task_env(env, cfg, ref)
    # Never inherit a parent assist capability into a nested ordinary launch.
    # Re-mint it only for the exact recorded branch/PR this spawn already
    # proved.
    env.pop(ASSIST_BRANCH_ENV, None)
    env.pop(ASSIST_PR_ENV, None)
    if publish_aligned_branch is not None:
        _, blackboard = split_body(ticket.body)
        assist_pr_url = parse_pr_url(blackboard or "")
        if not assist_pr_url:
            raise ComposeError(
                "recorded assist checkout has no `pr:` link under `## Dev`"
            )
        env[ASSIST_BRANCH_ENV] = publish_aligned_branch
        env[ASSIST_PR_ENV] = assist_pr_url

    if warn_blackboard:
        warning = blackboard_size_warning(ref.ticket_path)
        if warning:
            typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW, err=True)

    typer.echo(f"{label}: composing prompt")
    if include_blocker_preamble:
        prompt = compose_prompt(cfg, ref, ticket)
    else:
        prompt = compose_prompt(
            cfg,
            ref,
            ticket,
            include_blocker_preamble=False,
        )
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
    publish_session_log = False
    assist_log_refusal: str | None = None
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
            # Commit the launch line before spawning. A bootstrap target has no
            # later task-state sync to carry it; a human-step assist may share
            # the PR checkout whose clean-tree gate the agent is about to run.
            # Non-fatal on any git failure.
            log_synced = git.sync_log(
                cfg,
                message=f"Log: {ref.id_slug}",
                publish_if_remote_aligned=publish_aligned_branch is not None,
                expected_feature_branch=publish_aligned_branch,
                # A recorded assist was aligned before ticket/config/prompt
                # derivation. If its remote moves now, refuse to spawn instead
                # of fast-forwarding underneath already-composed state.
                allow_feature_fast_forward=publish_aligned_branch is None,
                feature_publication_guard=feature_publication_guard,
            )
            if publish_aligned_branch is not None and not log_synced:
                raise _AssistPublicationRefused(
                    "The recorded PR branch moved or could not be verified "
                    "after launch composition. No agent was started; retry "
                    "the launch so its prompt is composed from the new tip. "
                    "The launch audit append remains dirty and the catch-all "
                    "state sweep has been suppressed."
                )

        if name and sys.stdout.isatty():
            sys.stdout.write(f"\033]2;{name}\007")
            sys.stdout.flush()

        if before_spawn is not None:
            before_spawn()
        spawn_started = True
        # Agent CLIs (`claude`, `codex`) don't exit on their own. Run through a
        # PTY watcher so an agent that writes the session-done sentinel after
        # `coga bump` / `coga mark done` / `coga mark canceled` / `coga block`
        # releases the REPL.
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
        publish_session_log = _completed_publishing_gate(ticket, ref, outcome)
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
            # each step's record commits promptly. When a successful
            # artifact-gated bump just published an open PR branch, publish
            # this trailing commit there too so the local and PR tips stay in
            # lockstep. Non-fatal.
            if isinstance(cfg, Config):
                trailing_log_synced = git.sync_log(
                    cfg,
                    message=f"Log: {session_slug}",
                    publish_current_branch=publish_session_log,
                    publish_if_remote_aligned=publish_aligned_branch is not None,
                    expected_feature_branch=publish_aligned_branch,
                    feature_publication_guard=feature_publication_guard,
                )
                if (
                    publish_aligned_branch is not None
                    and not trailing_log_synced
                ):
                    assist_log_refusal = (
                        "The recorded PR branch changed or could not publish "
                        "the trailing assist audit record. The record remains "
                        "dirty for an explicit retry and the catch-all state "
                        "sweep has been suppressed."
                    )
        try:
            prompt_file.unlink()
        except FileNotFoundError:
            pass
        if assist_log_refusal is not None:
            raise _AssistPublicationRefused(
                assist_log_refusal,
                post_session=True,
            )


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


def _completed_publishing_gate(
    ticket: Ticket,
    ref: TaskRef | BootstrapRef,
    outcome,
) -> bool:
    """Whether this done-signalled session advanced off a publishing gate.

    The gated bump publishes its transition commit before it emits the done
    marker. Session usage is appended later, in this process's teardown. Read
    the durable ticket to prove the original gated step advanced before asking
    `sync_log` to publish that final feature-branch commit. Blocks, natural
    exits, crashes, and rewinds therefore keep the ordinary local-only feature
    log behavior.
    """
    if outcome.kind != "done" or not isinstance(ref, TaskRef):
        return False
    current = ticket.current_step()
    if not isinstance(current, dict) or not gate_publishes_current_branch(
        current.get("requires")
    ):
        return False
    before = ticket.step_index()
    if before is None or not ref.ticket_path.is_file():
        return False
    try:
        after = Ticket.read(ref.ticket_path).step_index()
    except Exception:
        # Teardown must never hide the agent's real outcome because a ticket was
        # concurrently removed or malformed after the session ended.
        return False
    return after is not None and after > before


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
        if after.status in TERMINAL_STATUSES:
            return f"{ref.id_slug}: task is {after.status}"
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
        or not assignee
        or assignee in cfg.agents
        or agent_override is not None
    ):
        return
    _bail(
        f"Cannot launch {ref.id_slug}: assignee {assignee!r} "
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


def _bail(msg: str, *, exit_code: int = 2) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(exit_code)
