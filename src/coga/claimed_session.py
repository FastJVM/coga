"""Co-versioned claim, release, admission and exact activation transactions.

The pending seal and held-child barrier must agree with ordinary launch
recovery. Callers select work; this module alone constructs admission proofs.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from uuid import uuid4

from coga import git
from coga.blackboard import (
    Blocker,
    open_blockers,
    resolve_blockers_text,
    update_blackboard_under_barrier,
)
from coga.launch import (
    AgentSessionResult,
    agent_command_refusal,
    missing_launch_file_message,
    spawn_agent_session,
)
from coga.compose import ComposeError, compose_prompt
from coga.config import AgentType, Config, ConfigError, SecretError, build_launch_env
from coga.dependencies import agent_cli_missing_message
from coga.github_preflight import check_git_auth, check_git_remote
from coga.logfile import retract_log_lines
from coga.mark import (
    PREPARE_ACTIVE_ERRORS as _PREPARE_ACTIVE_ERRORS,
    mark_active,
    mark_in_progress,
)
from coga.paths import log_path
from coga.repl_supervisor import build_supervised_step_env, SENTINEL_ENV
from coga.task_env import apply_task_env
from coga.taskfile import TaskFileError
from coga.tasks import TaskRef
from coga.ticket import (
    PENDING_LAUNCH_GENERATION_PREFIX,
    Ticket,
    TicketError,
    admitted_launch_generation,
    pending_launch_generation,
    released_generation_from_pending,
    released_launch_generation,
)
from coga.validate import TaskValidationError


@dataclass(frozen=True)
class ActivationRefusal:
    error: Exception
    retained: bool = False


@dataclass(frozen=True)
class ClaimedSessionResult:
    before: Ticket | None = None
    session: AgentSessionResult | None = None
    refusal: str | None = None
    released: bool = False
    retained: bool = False
    # The refused activation itself, so the caller classifies it exactly as
    # its own prepare half does (an unlaunchable workflow is not a failure).
    activation_error: Exception | None = None


class _LaunchClaimRefused(Exception):
    """The published megalaunch claim stopped matching before PTY spawn."""


@dataclass(frozen=True)
class _PreparedAgentLaunch:
    """Fallible launch inputs materialized before lifecycle writes."""

    ticket: Ticket
    source_ticket_bytes: bytes
    agent: AgentType
    env: dict[str, str]
    prompt: str


def activate_claimed_ticket(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    log_message: str | None = None,
    prepared: Ticket | None = None,
    source_bytes: bytes | None = None,
    blocker_resolution: tuple[str, dict[Blocker, str]] | None = None,
) -> ActivationRefusal | None:
    """Commit a picked or dependency-drained ticket to `active`.

    Mirrors `coga launch`'s inline auto-activation, but returns a loud result
    instead of exiting the process — one bad task must not kill the sweep.
    `mark_active` mutates `ticket` in place (status, frozen workflow, seeded
    step), so the caller's launch loop continues off the same object.

    The durable half. A deferred picker launch supplies the exact prospective
    ticket its preflight saw plus the source bytes that preflight read.
    `mark_active` therefore sees an already-prepared `active` ticket (so it
    cannot freeze a changed workflow definition) and the write is refused
    before it happens if a peer changed the ticket meanwhile. A dependency
    drain also supplies an actor and answers by blocker record: after
    activation validates and writes, its blocker update joins the same exact
    control publication. Thus
    the next launch claim builds on resolved bytes rather than a local-only
    edit. A refused or failed publication restores the source bytes; an
    unknown one keeps the local write for reconciliation.
    """
    prior = ticket.status
    written: bytes | None = None
    strict_activation = (
        cfg.git_enabled and prepared is not None and source_bytes is not None
    )
    if blocker_resolution is not None and (prepared is None or source_bytes is None):
        return ActivationRefusal(git.GitError('dependency resolution requires an exact activation snapshot'))
    if prepared is not None:
        ticket.frontmatter = dict(prepared.frontmatter)
        ticket.body = prepared.body
    with git.state_lock(cfg):
        log_before = snapshot_log_bytes(cfg)
        try:
            with git.state_lock(cfg):
                if source_bytes is not None and snapshot_ticket_bytes(ref) != source_bytes:
                    return ActivationRefusal(git.GitError('ticket changed before deferred activation; retry'))
                mark_active(
                    cfg,
                    ref,
                    ticket,
                    actor="megalaunch",
                    log_message=(
                        log_message
                        or f"activated ({prior} → active) — explicit megalaunch pick"
                    ),
                    echo=None,
                    sync_state=not strict_activation and blocker_resolution is None,
                )
                written = ticket.render().encode("utf-8")
                if blocker_resolution is not None:
                    actor, answers = blocker_resolution
                    try:
                        resolved = update_blackboard_under_barrier(
                            cfg, ref.ticket_path,
                            lambda region: resolve_blockers_text(region, actor, answers),
                            expected_bytes=ticket.render().encode("utf-8"),
                        )
                    except (OSError, UnicodeError, TaskFileError) as exc:
                        raise git.GitError(
                            f"could not resolve dependency blocker: {exc}"
                        ) from exc
                    written = resolved
                    if resolved is None or open_blockers(ref.ticket_path):
                        raise git.GitError(
                            "dependency blocker changed before its guarded resolution"
                        )
                if strict_activation:
                    git.sync_task_state(
                        cfg,
                        ref.path,
                        message=f"Ticket: {ref.id_slug} — active",
                        expect={ref.ticket_path: source_bytes},
                        strict=True,
                    )
        except git.UncertainPublishError as exc:
            return ActivationRefusal(git.GitError(
                "activation publication outcome is uncertain; generated "
                f"local state retained for reconciliation — {exc}"
            ), retained=True)
        except (*_PREPARE_ACTIVE_ERRORS, TaskValidationError, git.GitError) as exc:
            retained = False
            if isinstance(exc, (TaskValidationError, git.GitError)) and strict_activation:
                if not restore_owned_ticket(
                    cfg, ref, source_bytes, log_before=log_before,
                    expected_bytes=written or ticket.render().encode("utf-8"),
                ):
                    retained = True
                    exc = git.GitError(
                        f"activation publication failed and local ticket changed; "
                        f"state retained for reconciliation — {exc}"
                    )
            return ActivationRefusal(exc, retained=retained)
    return None


def snapshot_ticket_bytes(ref: TaskRef) -> bytes | None:
    try:
        return ref.ticket_path.read_bytes()
    except (FileNotFoundError, IsADirectoryError):
        return None


def snapshot_log_bytes(cfg: Config) -> bytes | None:
    path = log_path(cfg)
    return path.read_bytes() if path.is_file() else None


def restore_owned_ticket(
    cfg: Config, ref: TaskRef, data: bytes | None, *, log_before: bytes | None = None,
    expected_bytes: bytes,
) -> bool:
    """Undo a lifecycle write whose publication was definitely refused.

    The ticket goes back to its pre-write bytes and the audit lines that
    write appended are retracted, so nothing on disk claims a transition
    control never accepted.
    """
    with git.state_lock(cfg):
        try:
            if snapshot_ticket_bytes(ref) != expected_bytes:
                return False
        except OSError:
            return False
        if data is None:
            ref.ticket_path.unlink(missing_ok=True)
        else:
            ref.ticket_path.write_bytes(data)
        retract_log_lines(cfg, ref.id_slug, log_before)
        return True


def _revalidate_launch_claim_before_spawn(
    cfg: Config,
    ref: TaskRef,
    *,
    expected_started_bytes: bytes,
) -> None:
    """Re-prove one exact local/control claim at the actual PTY boundary.

    Strict claim publication closes the race between preflight and the first
    control push, and a published generation is not automatically reclaimable
    by another megalaunch. Still reread the local ticket and every effective
    control push destination from a private fetch immediately before
    ``run_with_done_marker`` so arbitrary peer edits after publication cannot
    reach spawn. Exact ticket bytes bind the proof to the preflighted prompt as
    well as the generation.

    Refusal deliberately leaves the pending ``in_progress`` claim untouched.
    Ordinary ``coga launch`` refuses that visible held-child state; only the
    post-release admission callback turns it into a plain generation that can
    be recovered explicitly.
    """
    def require_local_claim() -> None:
        try:
            local_bytes = ref.ticket_path.read_bytes()
        except OSError as exc:
            raise _LaunchClaimRefused(
                f"launch claim could not be read before agent spawn: {exc}"
            ) from exc
        if local_bytes != expected_started_bytes:
            raise _LaunchClaimRefused(
                "launch claim changed locally before agent spawn"
            )

    require_local_claim()
    if not cfg.git_enabled:
        return

    try:
        root = git.toplevel(ref.path)
        if root is None:
            raise git.GitError(
                "strict launch-claim verification requires a Git checkout"
            )
        base = git.fetch_control(cfg, root)
        control_bytes = git.tree_bytes(
            root, base, git.relative_to_root(root, ref.ticket_path)
        )
        if control_bytes != expected_started_bytes:
            raise _LaunchClaimRefused(
                "launch claim changed on control before agent spawn"
            )
    except git.GitError as exc:
        raise _LaunchClaimRefused(
            f"launch claim could not be verified before agent spawn: {exc}"
        ) from exc
    # Fetching control may take long enough for a local ordinary launch to
    # update the blackboard. Keep the last filesystem action before returning
    # to the PTY call an exact local reread too.
    require_local_claim()


def _admit_launch_claim_after_release(
    cfg: Config,
    ref: TaskRef,
    *,
    expected_started_bytes: bytes,
) -> None:
    """Publish pending-to-admitted only after the held child is released.

    The supervisor calls this while retaining the same-checkout publication
    barrier that covered the final remote proof and gate write. Cross-checkout
    publishers see the visible ``pending:`` claim and refuse every replacement;
    this exact one-field transition is the sole exception. Once it lands, the
    child can already execute, so ordinary lifecycle changes may proceed.
    """
    if not cfg.git_enabled:
        return
    try:
        current_bytes = ref.ticket_path.read_bytes()
    except OSError as exc:
        raise _LaunchClaimRefused(
            f"pending launch claim could not be read after child release: {exc}"
        ) from exc
    if current_bytes != expected_started_bytes:
        raise _LaunchClaimRefused(
            "pending launch claim changed locally during child release"
        )
    try:
        ticket = Ticket.parse(current_bytes.decode("utf-8"))
    except (UnicodeDecodeError, TicketError) as exc:
        raise _LaunchClaimRefused(
            f"pending launch claim became unreadable after child release: {exc}"
        ) from exc
    generation = ticket.launch_generation
    if not pending_launch_generation(generation):
        raise _LaunchClaimRefused(
            "launch claim was not pending after child release"
        )
    assert generation is not None

    admitted_generation = admitted_launch_generation(generation)
    released_ticket = Ticket(
        frontmatter=dict(ticket.frontmatter),
        body=ticket.body,
    )
    released_ticket.frontmatter["launch_generation"] = (
        released_generation_from_pending(generation)
    )
    try:
        # Record release before attempting its remote publication. If that
        # publication fails, this local-only form is the durable capability
        # that lets an explicit ordinary launch safely reconcile and recover.
        released_ticket.write(ref.ticket_path)
    except OSError as exc:
        raise _LaunchClaimRefused(
            "released launch admission could not be recorded locally; "
            f"manual reconciliation is required: {exc}"
        ) from exc

    try:
        ticket.frontmatter["launch_generation"] = admitted_generation
        ticket.write(ref.ticket_path)
        # The supervisor already holds `state_lock` through this callback;
        # `publish` re-enters it. `expect` pins the pending control copy the
        # seal accepts this exact prefix-stripped transition against.
        git.publish(
            cfg,
            [ref.ticket_path, log_path(cfg)],
            f"Ticket: {ref.id_slug} — launch admitted",
            expect={ref.ticket_path: current_bytes},
        )
    except (git.GitError, OSError, ValueError) as exc:
        # Whether the publish was refused, failed, or is unknown, the local
        # `released:` witness is what lets `coga launch` reconcile it.
        try:
            released_ticket.write(ref.ticket_path)
            detail = ""
        except OSError as restore_exc:
            detail = f"; released witness could not be restored: {restore_exc}"
        if isinstance(exc, git.StateRegressionError):
            raise _LaunchClaimRefused(
                "launch admission could not be published; admitted child was "
                "terminated and released local state was retained for "
                f"`coga launch {ref.id_slug}` reconciliation: {exc}{detail}"
            ) from exc
        if isinstance(exc, git.GitError):
            raise _LaunchClaimRefused(
                "launch-admission publication outcome is uncertain; admitted "
                "child was terminated and released local state was retained for "
                f"`coga launch {ref.id_slug}` reconciliation — {exc}{detail}"
            ) from exc
        raise _LaunchClaimRefused(
            f"launch admission could not be recorded: {exc}{detail}"
        ) from exc


def _preflight_agent_launch(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    launch_agent: str | None,
    *,
    source_ticket_bytes: bytes | None = None,
) -> _PreparedAgentLaunch | str:
    try:
        agent = cfg.agent_type(launch_agent or "")
    except ConfigError as exc:
        return str(exc)
    # A not-yet-activated pick arrives as its prospective `active` view. Keep
    # the launch boundary strict so malformed or concurrently changed states
    # cannot reach the agent spawn path.
    if ticket.status not in {"active", "in_progress"}:
        return f"status is {ticket.status}; expected active or in_progress"
    # An admitted (plain) generation from an earlier session is replaced by
    # this launch's new claim: whether that session still runs is the human's
    # to coordinate. Concurrent claimers still race through the strict
    # compare-and-set start publication and the pre-spawn claim proof.
    if ticket.status == "in_progress" and ticket.launch_generation is not None:
        if pending_launch_generation(ticket.launch_generation):
            return (
                "ticket already carries a pending megalaunch admission; its "
                "held child must be released or the claim reconciled before "
                "another session can start"
            )
        if released_launch_generation(ticket.launch_generation):
            return (
                "ticket carries a released megalaunch admission awaiting "
                f"reconciliation — run `coga launch {ref.id_slug}` to recover"
            )
    if shutil.which(agent.cli) is None:
        return agent_cli_missing_message(agent.name, agent.cli)
    expected_source_bytes = (
        ticket.render().encode("utf-8")
        if source_ticket_bytes is None
        else source_ticket_bytes
    )
    launch_ticket = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    if launch_ticket.status == "active":
        launch_ticket.frontmatter["status"] = "in_progress"
    generation = str(uuid4())
    launch_ticket.frontmatter["launch_generation"] = (
        f"{PENDING_LAUNCH_GENERATION_PREFIX}{generation}"
        if cfg.git_enabled
        else generation
    )
    try:
        prompt = compose_prompt(
            cfg, ref, launch_ticket, launch_context="megalaunch"
        )
        launch_env = apply_task_env(build_launch_env(cfg, launch_ticket.secrets), cfg, ref, launch_ticket)
        launch_env.pop(SENTINEL_ENV, None)
        env = build_supervised_step_env(
            launch_env,
            task_path=ref.path,
            step=launch_ticket.step,
            agent=launch_agent,
        )
    except FileNotFoundError as exc:
        return missing_launch_file_message(exc)
    except (ConfigError, ComposeError, SecretError) as exc:
        return str(exc)
    command_refusal = agent_command_refusal(
        agent, env=env, ref=ref, name=launch_ticket.title or ""
    )
    if command_refusal is not None:
        return command_refusal
    if cfg.git_enabled and check_git_remote(cfg.git_remote).ok:
        auth = check_git_auth(cfg.git_remote)
        if not auth.ok:
            return f"git push access unavailable: {auth.detail}"
    return _PreparedAgentLaunch(
        ticket=launch_ticket,
        source_ticket_bytes=expected_source_bytes,
        agent=agent,
        env=env,
        prompt=prompt,
    )


def run_claimed_agent_session(
    cfg: Config, ref: TaskRef, *, source_bytes: bytes,
    prospective_ticket: Ticket, agent_name: str,
    activation: Ticket | None = None,
    idle_timeout: float | None = None, max_session: float | None = None,
) -> ClaimedSessionResult:
    """Prepare and publish an exact claim, then release and admit its child.

    No caller-supplied proof, release callback or generation crosses this API.
    A human step is refused even under an agent override.
    """
    from coga.bump import resolve_operator, OperatorResolutionError

    ticket = Ticket.parse(source_bytes.decode("utf-8"))
    expected_view = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    if activation is not None:
        from coga.mark import prepare_active
        try:
            prepare_active(cfg, ref, expected_view)
        except _PREPARE_ACTIVE_ERRORS as exc:
            return ClaimedSessionResult(refusal=str(exc), activation_error=exc)
    if expected_view.render() != prospective_ticket.render():
        return ClaimedSessionResult(refusal="prospective ticket does not match source routing")
    try:
        operator = resolve_operator(cfg, ref, expected_view)
    except OperatorResolutionError as exc:
        return ClaimedSessionResult(refusal=str(exc))
    if operator is None or operator.is_human:
        return ClaimedSessionResult(refusal="current step is not agent-owned")
    prepared_launch = _preflight_agent_launch(
        cfg,
        ref,
        prospective_ticket,
        agent_name,
        source_ticket_bytes=(prospective_ticket.render().encode("utf-8") if activation is not None else source_bytes),
    )
    if isinstance(prepared_launch, str):
        return ClaimedSessionResult(refusal=prepared_launch)

    if activation is not None:
        failure = activate_claimed_ticket(
            cfg,
            ref,
            ticket,
            prepared=activation,
            source_bytes=source_bytes,
        )
        if failure is not None:
            return ClaimedSessionResult(
                refusal=str(failure.error), retained=failure.retained,
                activation_error=failure.error,
            )

    # Activation sync can spend long enough fetching/publishing for a peer
    # to edit or complete the ticket. Bind the following start write to the
    # exact active bytes that the preflight saw; never overlay that peer
    # revision with this loop's stale in-memory ticket. The same guard also
    # closes the preflight window for an already-active sweep candidate.
    with git.state_lock(cfg):
        prior_start_status = ticket.status
        start_bytes = snapshot_ticket_bytes(ref)
        log_before = snapshot_log_bytes(cfg)
        if start_bytes != prepared_launch.source_ticket_bytes:
            return ClaimedSessionResult(
                refusal="ticket changed after launch preflight; retry",
            )
        try:
            mark_in_progress(
                cfg,
                ref,
                prepared_launch.ticket,
                actor="megalaunch",
                log_message=(
                    "started (active → in_progress) via coga megalaunch"
                    if prior_start_status == "active"
                    else "claimed in_progress resume via coga megalaunch"
                    + (
                        f" (replaced earlier claim {ticket.launch_generation})"
                        if ticket.launch_generation is not None
                        else ""
                    )
                ),
                echo=None,
                strict=cfg.git_enabled,
            )
        except TaskValidationError as exc:
            restored = restore_owned_ticket(
                cfg, ref, start_bytes, log_before=log_before,
                expected_bytes=prepared_launch.ticket.render().encode("utf-8"),
            )
            return ClaimedSessionResult(refusal=str(exc), retained=not restored)
        except git.UncertainPublishError as exc:
            # Unknown: keep the pending claim on disk as the legible evidence
            # for reconciliation.
            return ClaimedSessionResult(
                refusal="launch claim publication outcome is uncertain; generated "
                f"local state retained for reconciliation — {exc}",
                retained=True,
            )
        except git.GitError as exc:
            # Definitely not on control: another checkout won the claim, this
            # one is stale, or the push never got through. Put the pre-write
            # bytes back.
            restored = restore_owned_ticket(
                cfg, ref, start_bytes, log_before=log_before,
                expected_bytes=prepared_launch.ticket.render().encode("utf-8"),
            )
            return ClaimedSessionResult(
                refusal=f"launch claim publication refused: {exc}; retry",
                retained=not restored,
            )
    # `mark_in_progress` includes synchronous Git publication. A peer can
    # replace, complete, or claim the ticket while that network boundary
    # is in flight, after our pre-write CAS has already succeeded. Spawn
    # only if the live file is still the exact claimed revision whose
    # prompt, environment, and agent were materialized above.
    try:
        post_start_ticket_bytes = ref.ticket_path.read_bytes()
    except FileNotFoundError:
        post_start_ticket_bytes = None
    expected_started_bytes = prepared_launch.ticket.render().encode("utf-8")
    if post_start_ticket_bytes != expected_started_bytes:
        return ClaimedSessionResult(
            refusal="ticket changed during start publication; current state "
            "retained for safe resume; retry", retained=True,
        )

    def revalidate_launch_claim() -> None:
        _revalidate_launch_claim_before_spawn(
            cfg,
            ref,
            expected_started_bytes=expected_started_bytes,
        )

    released = False

    def admit_released_launch_claim() -> None:
        nonlocal released
        released = True
        _admit_launch_claim_after_release(
            cfg,
            ref,
            expected_started_bytes=expected_started_bytes,
        )

    before = prepared_launch.ticket
    try:
        agent = prepared_launch.agent
        # A normal interactive launch: the REPL streams to the console
        # under the PTY watcher, and the done-sentinel (`coga bump` /
        # `mark done` / `mark canceled` / `block`) releases it — never
        # headless `-p`, which
        # buffers all output until the run ends.
        session = spawn_agent_session(
            cfg,
            ref,
            before,
            agent,
            env=prepared_launch.env,
            actor="megalaunch",
            log_message="launched via coga megalaunch",
            name=before.title or "",
            idle_timeout=idle_timeout,
            max_session=max_session,
            launch_context="megalaunch",
            label="Megalaunch",
            warn_blackboard=True,
            composed_prompt=prepared_launch.prompt,
            validate_before_spawn=revalidate_launch_claim,
            validate_after_spawn=revalidate_launch_claim,
            after_spawn_release=(
                admit_released_launch_claim if cfg.git_enabled else None
            ),
            record_launch_on_spawn=True,
        )
    except _LaunchClaimRefused as exc:
        return ClaimedSessionResult(
            refusal=f"{exc}; current state retained for safe resume; retry",
            released=released, retained=True,
        )
    except (ComposeError, ConfigError, SecretError) as exc:
        return ClaimedSessionResult(refusal=str(exc), retained=True)
    except git.GitError as exc:
        return ClaimedSessionResult(
            refusal=f"launch admission publication barrier unavailable: {exc}",
            released=released, retained=True,
        )
    except FileNotFoundError:
        return ClaimedSessionResult(refusal=agent_cli_missing_message(agent.name, agent.cli), retained=True)

    return ClaimedSessionResult(before=before, session=session, released=True)
