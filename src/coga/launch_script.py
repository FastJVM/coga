"""Deterministic ``ticket.py`` launch phase.

A directory-form ticket owns a deterministic half when ``ticket.py`` sits
beside ``ticket.md``.  The fixed name is the whole classifier: Coga does not
scan for plugins, import ticket code, or consult frontmatter to select a mode.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, NamedTuple

import typer

from coga import git
from coga.config import Config, build_launch_env, load_config
from coga.logfile import append_log, log_path
from coga.lifecycle import TERMINAL_STATUSES
from coga.notification import post, preflight_post
from coga.repl_supervisor import (
    ASSIST_AGENT_ENV,
    ASSIST_BRANCH_ENV,
    ASSIST_PR_ENV,
    EXPECTED_STEP_ENV,
    EXPECTED_TASK_ENV,
)
from coga.task_env import apply_task_env, host_repo_root
from coga.tasks import (
    BootstrapRef,
    TargetRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_target,
)
from coga.ticket import Ticket, TicketError


SCRIPT_ENTRY_POINT = "ticket.py"


@dataclass(frozen=True)
class ScriptPhaseResult:
    """The child exit and task state observed after one deterministic phase."""

    exit_code: int
    ticket: Ticket | None
    ran: bool = True
    cfg: Config | None = None
    ref: TargetRef | None = None


class ScriptChainResult(NamedTuple):
    """Result of consecutive deterministic steps before an agent handoff."""

    exit_code: int
    ticket: Ticket | None
    needs_agent: bool
    stop_reason: str | None
    cfg: Config | None = None
    ref: TargetRef | None = None


class ScriptPublicationError(RuntimeError):
    """A recorded-assist script could not stay inside its publication lease."""


def script_entry_point(ref: TargetRef) -> Path | None:
    """Return the target's fixed script entry point when it is a regular file.

    File-form tasks have no companion directory and therefore cannot carry a
    deterministic half.  Directory-form tasks and bootstrap tickets both use
    the one reserved sibling name; executable bits and other filenames do not
    participate in dispatch.
    """

    task_dir = ref.task_dir
    if task_dir is None:
        return None
    candidate = task_dir / SCRIPT_ENTRY_POINT
    return candidate if candidate.is_file() else None


def run_script_phase(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    *,
    stateless: bool,
    publish_aligned_branch: str | None = None,
    assist_agent: str | None = None,
    assist_pr_url: str | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
) -> ScriptPhaseResult:
    """Run one target-owned deterministic phase without composing a prompt.

    Secrets and task identity are preflighted before the stateful
    ``active -> in_progress`` transition.  The child receives no operands and
    runs from the host repository root under Coga's current Python
    interpreter.  The launcher, never this helper, decides whether an agent
    phase follows.
    """

    strict_assist = publish_aligned_branch is not None
    if strict_assist and (
        not assist_agent
        or not assist_pr_url
        or feature_publication_guard is None
    ):
        raise ScriptPublicationError(
            "recorded-assist script launch is missing its agent, PR, or "
            "publication guard"
        )

    entry = script_entry_point(ref)
    if entry is None:
        # Classification is a point-in-time observation. Activation, a prior
        # deterministic phase, or another checkout may have removed the fixed
        # entry before this phase began. Reclassify as agent-only instead of
        # turning the stale stat into a launch failure.
        return ScriptPhaseResult(
            exit_code=0,
            ticket=ticket,
            ran=False,
            cfg=cfg,
            ref=ref,
        )

    # Resolve every declared secret before publishing a started lifecycle.
    env = build_launch_env(cfg, ticket.secrets)
    if strict_assist:
        try:
            preflight_post(cfg)
        except typer.Exit as exc:
            raise ScriptPublicationError(
                "the recorded assist cannot run ticket.py until its live "
                "notification configuration is valid"
            ) from exc

    if not stateless and not isinstance(ref, TaskRef):
        raise ValueError(
            f"Stateful script phase requires a task target, got {ref.id_slug}."
        )

    if strict_assist and ticket.status != "in_progress":
        raise ScriptPublicationError(
            "recorded-assist lifecycle was not published before ticket.py"
        )

    if not stateless and ticket.status == "active":
        # Local import keeps the pure classifier importable by coga.validate;
        # coga.mark itself imports the validator for transition checks.
        from coga.mark import mark_in_progress

        current = ticket.current_step()
        step_note = (
            f" (step {ticket.step_index()}: {current['name']})"
            if current is not None
            else ""
        )
        mark_in_progress(
            cfg,
            ref,
            ticket,
            actor="system",
            log_message="started (active → in_progress) via coga launch",
            slack_text=(
                f"▶️ script started *{ref.id_slug}* "
                f"\"{ticket.title}\"{step_note}"
            ),
            echo=f"{ref.id_slug}: in_progress",
        )

    if not stateless:
        append_log(cfg, ref.id_slug, "system", "launched as a script (ticket.py)")
        # Commit the launch line before user code runs: an entry point may
        # switch branches, and a dirty tracked log would make git refuse it.
        log_synced = git.sync_log(
            cfg,
            message=f"Log: {ref.id_slug}",
            publish_if_remote_aligned=strict_assist,
            expected_feature_branch=publish_aligned_branch,
            allow_feature_fast_forward=not strict_assist,
            feature_publication_guard=feature_publication_guard,
        )
        if strict_assist and not log_synced:
            raise ScriptPublicationError(
                "the recorded PR branch moved or could not publish the "
                "pre-script audit record"
            )

    pre_sync_identity = (ticket.status, ticket.step, ticket.assignee)

    # The lifecycle and launch-log syncs above may fetch/rebase a control
    # checkout. Re-derive every input after that last moving boundary: a peer
    # may have replaced or removed ticket.py, changed coga.toml, edited the
    # ticket, or changed its secret declarations. A vanished entry point is a
    # fresh agent-only classification, not a failed execution of a stale path.
    cfg = load_config(cfg.repo_root)
    try:
        refreshed_ref = resolve_target(cfg, ref.id_slug)
    except TaskNotFoundError:
        return ScriptPhaseResult(
            exit_code=0,
            ticket=None,
            ran=False,
            cfg=cfg,
            ref=ref,
        )
    if refreshed_ref.id_slug != ref.id_slug:
        raise FileNotFoundError(
            f"Selected task {ref.id_slug!r} disappeared while preparing "
            "ticket.py."
        )
    ref = refreshed_ref
    ticket = read_ticket(ref)
    entry = script_entry_point(ref)
    if entry is None:
        return ScriptPhaseResult(
            exit_code=0,
            ticket=ticket,
            ran=False,
            cfg=cfg,
            ref=ref,
        )

    if not stateless and (
        ticket.status != "in_progress"
        or (ticket.status, ticket.step, ticket.assignee) != pre_sync_identity
    ):
        # The moving sync above is authoritative. A peer may have closed or
        # parked the task, advanced it to a configured agent after a human
        # assist, or handed it to a human. Do not execute code selected from the
        # stale pre-sync lifecycle; let the chain classify the fresh state.
        return ScriptPhaseResult(
            exit_code=0,
            ticket=ticket,
            ran=False,
            cfg=cfg,
            ref=ref,
        )

    result_publication: git.FeaturePublicationLease | None = None
    result_snapshot: git.FileMutationRollback | None = None
    if strict_assist:
        assert isinstance(ref, TaskRef)
        result_snapshot = _capture_script_result_state(cfg, ref)
        try:
            result_publication = git.feature_publication_lease(
                cfg,
                ref.path,
                publish_aligned_branch or "",
            )
            assert feature_publication_guard is not None
            feature_publication_guard(result_publication.remote_oid)
            _require_script_result_state_unchanged(result_snapshot, cfg, ref)
        except git.FeaturePublicationError as exc:
            raise ScriptPublicationError(
                "the recorded assist could not lease ticket.py's result "
                f"publication before execution: {exc}"
            ) from exc

    env = build_launch_env(cfg, ticket.secrets)
    env = apply_task_env(env, cfg, ref, ticket)
    # A normal ticket script must not inherit ownership witnesses from an outer
    # agent session. A strict human assist re-mints only the narrow task and PR
    # capability needed by in-script block/unblock operations. It deliberately
    # remains non-supervised, so it cannot signal an outer REPL's done marker.
    env.pop("COGA_SUPERVISED", None)
    env.pop(EXPECTED_TASK_ENV, None)
    env.pop(EXPECTED_STEP_ENV, None)
    if strict_assist:
        env[EXPECTED_TASK_ENV] = str(ref.path.resolve())
        env[EXPECTED_STEP_ENV] = ticket.step or ""
        env[ASSIST_AGENT_ENV] = assist_agent or ""
        env[ASSIST_BRANCH_ENV] = publish_aligned_branch or ""
        env[ASSIST_PR_ENV] = assist_pr_url or ""

    completed = subprocess.run(
        [sys.executable, str(entry)],
        cwd=host_repo_root(cfg),
        env=env,
        check=False,
    )
    exit_code = completed.returncode

    after: Ticket | None = None
    ticket_read_error: Exception | None = None
    if ref.ticket_path.exists():
        try:
            after = Ticket.read(ref.ticket_path)
        except (OSError, UnicodeError, TicketError) as exc:
            ticket_read_error = exc
    ticket_validation_error: Exception | None = None
    if strict_assist and after is not None:
        # Local import keeps this module importable by coga.validate, which
        # imports the fixed entry-point classifier above.
        from coga.validate import TaskValidationError, assert_task_valid

        try:
            assert_task_valid(cfg, ref, action="publish ticket.py result")
        except TaskValidationError as exc:
            ticket_validation_error = exc
    audit_append: bytes | None = None
    if not stateless:
        # The audit belongs to the launch, not to the continued existence or
        # parseability of ticket.md. Record it even when user code deleted or
        # malformed its own ticket, and never let that reread replace a
        # non-zero child result.
        audit_append = append_log(
            cfg,
            ref.id_slug,
            "system",
            f"script exited with code {exit_code}",
        )

    if strict_assist and not stateless:
        try:
            assert isinstance(ref, TaskRef)
            assert result_publication is not None
            assert result_snapshot is not None
            assert audit_append is not None
            _arm_script_result_state(result_snapshot, cfg, ref)
            invalid_detail: str | None = None
            if ticket_read_error is not None:
                invalid_detail = f"unreadable ticket result: {ticket_read_error}"
            elif after is None:
                invalid_detail = "removed ticket result"
            elif ticket_validation_error is not None:
                invalid_detail = f"invalid ticket result: {ticket_validation_error}"

            if invalid_detail is not None:
                # A nested strict lifecycle command may already have moved and
                # published the feature/control pair before ticket.py damaged
                # its ticket.  Lease the exact *current* published tip while
                # the invalid bytes still match our captured post-child
                # snapshot, then recover from that authoritative revision —
                # never from the stale pre-child snapshot.
                recovery_publication = git.feature_publication_lease(
                    cfg,
                    ref.path,
                    publish_aligned_branch or "",
                    allow_append_only_log=True,
                    allowed_dirty_paths=result_snapshot.generated,
                )
                assert feature_publication_guard is not None
                feature_publication_guard(recovery_publication.remote_oid)
                rollback_note = _restore_invalid_script_result(
                    result_snapshot,
                    cfg,
                    ref,
                    revision=recovery_publication.local_oid,
                )
                if rollback_note:
                    raise ScriptPublicationError(
                        "the recorded assist could not restore ticket.py's "
                        f"{invalid_detail}{rollback_note}"
                    )
                after = Ticket.read(ref.ticket_path)
                _publish_restored_script_failure(
                    cfg,
                    ref,
                    branch=publish_aligned_branch or "",
                    feature_publication_guard=feature_publication_guard,
                    publication=recovery_publication,
                )
                ticket_read_error = None
                if exit_code == 0:
                    raise ScriptPublicationError(
                        "the recorded assist restored and audited ticket.py's "
                        f"{invalid_detail}, but a zero exit cannot count as a "
                        "successful deterministic result"
                    )
            else:
                # A nested strict lifecycle command may already have published
                # the task and moved the exact branch/control pair. In that
                # case only the trailing exit audit remains dirty, so replace
                # the pre-child lease with a fresh append-only-log lease.
                # Direct ticket.py output stays dirty and deliberately falls
                # back to the pre-child lease plus its exact byte snapshot.
                try:
                    refreshed_publication = git.feature_publication_lease(
                        cfg,
                        ref.path,
                        publish_aligned_branch or "",
                        allow_append_only_log=True,
                    )
                except git.FeaturePublicationError:
                    publication = result_publication
                else:
                    publication = refreshed_publication
                assert feature_publication_guard is not None
                feature_publication_guard(publication.remote_oid)
                git.sync_task_state(
                    cfg,
                    ref.path,
                    message=f"Ticket: {ref.id_slug} — script result",
                    feature_publication=publication,
                    feature_publication_guard=feature_publication_guard,
                    generated_paths=result_snapshot.generated,
                )
        except git.FeaturePublicationError as exc:
            raise ScriptPublicationError(
                "the recorded assist could not publish ticket.py's result: "
                f"{exc}"
            ) from exc

    if exit_code != 0 and not stateless:
        observed = after or ticket
        current = observed.current_step()
        where = (
            f" at step {observed.step_index()} ({current['name']})"
            if current is not None
            else ""
        )
        try:
            post(
                cfg,
                f"💥 script failed on *{ref.id_slug}* "
                f"\"{observed.title}\": exit {exit_code}{where}",
                task_path=ref.path,
                owner=observed.owner or cfg.current_user,
                watchers=observed.watchers,
                # The deterministic failure and its exit code are already
                # durable; a notification outage must not replace that result.
                fatal=False,
                record_failure=not strict_assist,
            )
        except typer.Exit:
            if not strict_assist:
                raise
            # Configuration was preflighted before user code. If it changed
            # while ticket.py ran, keep the durable child exit authoritative.

    if exit_code == 0:
        if ticket_read_error is not None:
            raise ticket_read_error
        # User code and nested lifecycle syncs may change coga.toml or move the
        # checkout across a freshly integrated control tip. The caller uses
        # this result for handoff classification and agent setup, so return a
        # config, target, and ticket derived after the child boundary rather
        # than the objects captured before execution.
        cfg = load_config(cfg.repo_root)
        try:
            ref = resolve_target(cfg, ref.id_slug)
        except TaskNotFoundError:
            after = None
        else:
            after = read_ticket(ref)
        # A bootstrap script is a command implementation: preserve its stdout
        # for callers such as ``$(coga <verb>)`` by keeping framing on stderr.
        typer.echo(f"{ref.id_slug}: script ran successfully", err=stateless)

    return ScriptPhaseResult(
        exit_code=exit_code,
        ticket=after,
        cfg=cfg,
        ref=ref,
    )


def run_script_chain(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    ran_steps: set[str | None],
    *,
    publish_aligned_branch: str | None = None,
    assist_agent: str | None = None,
    assist_pr_url: str | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
) -> ScriptChainResult:
    """Run ``ticket.py`` once per consecutive step until agent work remains."""

    stateless = isinstance(ref, BootstrapRef)
    current = ticket
    phase_assist_agent = assist_agent
    while current.step not in ran_steps:
        step_key = current.step
        ran_steps.add(step_key)
        _echo_script_iteration(ref, current, stateless=stateless)

        before = current
        phase = run_script_phase(
            cfg,
            ref,
            before,
            stateless=stateless,
            publish_aligned_branch=publish_aligned_branch,
            assist_agent=phase_assist_agent,
            assist_pr_url=assist_pr_url,
            feature_publication_guard=feature_publication_guard,
        )
        cfg = phase.cfg or cfg
        ref = phase.ref or ref
        if not phase.ran:
            ran_steps.discard(step_key)
            return _classify_script_handoff(
                cfg,
                ref,
                phase.ticket,
                stateless=stateless,
                strict_assist=publish_aligned_branch is not None,
            )
        if phase.exit_code != 0:
            return ScriptChainResult(
                phase.exit_code,
                phase.ticket,
                False,
                None,
                cfg,
                ref,
            )

        after = phase.ticket
        if stateless:
            return ScriptChainResult(0, after, False, None, cfg, ref)
        if after is None:
            return ScriptChainResult(
                0,
                None,
                False,
                "Launch: task directory removed by script — nothing to chain",
                cfg,
                ref,
            )
        if after.status != "in_progress":
            if after.status in TERMINAL_STATUSES:
                reason = f"{ref.id_slug}: task is {after.status}"
            elif after.status == "paused":
                reason = f"{ref.id_slug}: task is paused"
            else:
                reason = f"{ref.id_slug}: task status is {after.status!r}"
            return ScriptChainResult(0, after, False, reason, cfg, ref)

        # An unchanged step is the completion-contract signal for row three:
        # deterministic preparation succeeded and the agent continues that
        # same open unit of work. A changed step gets its own deterministic
        # phase before any agent preflight or prompt composition, unless the
        # workflow handed control to a human or left the step unassigned.  The
        # deterministic chain must honor the same approval boundary as the
        # agent supervisor instead of running ticket.py on somebody else's
        # turn.
        if after.step == before.step:
            return ScriptChainResult(0, after, True, None, cfg, ref)
        if not after.assignee or after.assignee not in cfg.agents:
            who = after.assignee or "unassigned"
            return ScriptChainResult(
                0,
                after,
                False,
                f"{ref.id_slug}: next step hands off to {who}; "
                "returning to caller",
                cfg,
                ref,
            )
        if publish_aligned_branch is not None:
            # The override authorizes the human-owned phase only. Once a
            # deterministic bump hands control to a configured agent, every
            # immediately chained script phase must be attributed to that
            # durable assignee.
            phase_assist_agent = after.assignee
        current = after

    return ScriptChainResult(0, current, True, None, cfg, ref)


def _classify_script_handoff(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket | None,
    *,
    stateless: bool,
    strict_assist: bool,
) -> ScriptChainResult:
    """Classify fresh state after a formerly-scripted phase no longer runs."""
    if stateless:
        return ScriptChainResult(0, ticket, True, None, cfg, ref)
    if ticket is None:
        return ScriptChainResult(
            0,
            None,
            False,
            "Launch: task directory removed before script — nothing to chain",
            cfg,
            ref,
        )
    if ticket.status not in {"active", "in_progress"}:
        if ticket.status in TERMINAL_STATUSES:
            reason = f"{ref.id_slug}: task is {ticket.status}"
        elif ticket.status == "paused":
            reason = f"{ref.id_slug}: task is paused"
        else:
            reason = f"{ref.id_slug}: task status is {ticket.status!r}"
        return ScriptChainResult(0, ticket, False, reason, cfg, ref)
    if not ticket.assignee:
        return ScriptChainResult(
            0,
            ticket,
            False,
            f"{ref.id_slug}: next step is unassigned; returning to caller",
            cfg,
            ref,
        )
    if ticket.assignee not in cfg.agents and not strict_assist:
        return ScriptChainResult(
            0,
            ticket,
            False,
            f"{ref.id_slug}: next step hands off to {ticket.assignee}; "
            "returning to caller",
            cfg,
            ref,
        )
    return ScriptChainResult(0, ticket, True, None, cfg, ref)


def _task_file_bytes(ref: TaskRef) -> dict[Path, bytes]:
    """Capture regular task leaves without following a generated symlink."""
    return git.capture_task_file_bytes(
        ref.path,
        context="strict script result",
    )


def _capture_script_result_state(
    cfg: Config,
    ref: TaskRef,
) -> git.FileMutationRollback:
    """Capture the exact task tree and union log before strict user code runs."""
    audit = log_path(cfg)
    originals: dict[Path, bytes | None] = dict(_task_file_bytes(ref))
    originals[audit] = audit.read_bytes() if audit.is_file() else None
    return git.FileMutationRollback(
        originals=originals,
        union_paths=frozenset((audit,)),
    )


def _require_script_result_state_unchanged(
    snapshot: git.FileMutationRollback,
    cfg: Config,
    ref: TaskRef,
) -> None:
    """Refuse a lease-time local edit before ticket.py owns the transaction."""
    audit = log_path(cfg)
    current_task_paths = set(_task_file_bytes(ref))
    captured_task_paths = set(snapshot.originals) - {audit}
    if current_task_paths != captured_task_paths:
        raise git.FeaturePublicationError(
            "the task tree changed while leasing ticket.py result publication"
        )
    for path in snapshot.originals:
        snapshot.require_unchanged(path)


def _arm_script_result_state(
    snapshot: git.FileMutationRollback,
    cfg: Config,
    ref: TaskRef,
) -> None:
    """Arm exact post-child task/log bytes for one scoped strict commit."""
    audit = log_path(cfg)
    current = _task_file_bytes(ref)
    for path in set(current) - set(snapshot.originals):
        snapshot.originals[path] = None
    updates: dict[Path, bytes | None] = {
        path: current.get(path)
        for path in snapshot.originals
        if path != audit
    }
    updates[audit] = audit.read_bytes() if audit.is_file() else None
    snapshot.arm(updates)


def _restore_invalid_script_result(
    snapshot: git.FileMutationRollback,
    cfg: Config,
    ref: TaskRef,
    *,
    revision: str,
) -> str:
    """Restore invalid generated task bytes from a verified published tip.

    The audit log is deliberately left untouched: it already contains the
    child's exit record and, after a nested lifecycle command, the lifecycle
    audit now committed at ``revision``.  Rewinding the whole pre-child
    snapshot would remove that durable transition and make the next strict
    lease reject the stale checkout.
    """
    assert snapshot.generated is not None
    audit = log_path(cfg)
    authoritative = git.capture_revision_file_bytes(
        ref.path,
        revision,
        context="invalid script recovery",
    )
    generated = {
        path: data
        for path, data in snapshot.generated.items()
        if path != audit
    }
    paths = set(authoritative) | set(generated)
    recovery = git.FileMutationRollback(
        originals={path: authoritative.get(path) for path in paths},
        union_paths=frozenset(),
        generated={path: generated.get(path) for path in paths},
    )
    try:
        # Check the whole generated tree once before the first replacement so
        # a peer edit normally produces an all-or-nothing refusal.  ``restore``
        # repeats the byte CAS per path to cover a later race as well.
        for path in paths:
            recovery.require_unchanged(path)
    except git.FeaturePublicationError:
        refused = tuple(sorted(paths, key=str))
    else:
        refused = recovery.restore()
    if not refused:
        return ""
    names = ", ".join(str(path) for path in refused)
    return f"; concurrent edits were retained instead of overwritten at {names}"


def _publish_restored_script_failure(
    cfg: Config,
    ref: TaskRef,
    *,
    branch: str,
    feature_publication_guard: Callable[[str], None] | None,
    publication: git.FeaturePublicationLease | None = None,
) -> None:
    """Publish the restored valid task plus a malformed-child exit audit."""
    if feature_publication_guard is None:
        raise git.FeaturePublicationError(
            "restored script failure is missing its publication guard"
        )
    publication = publication or git.feature_publication_lease(
        cfg, ref.path, branch, allow_append_only_log=True
    )
    feature_publication_guard(publication.remote_oid)
    generated: dict[Path, bytes | None] = dict(_task_file_bytes(ref))
    audit = log_path(cfg)
    generated[audit] = audit.read_bytes() if audit.is_file() else None
    git.sync_task_state(
        cfg,
        ref.path,
        message=f"Ticket: {ref.id_slug} — invalid script result audited",
        feature_publication=publication,
        feature_publication_guard=feature_publication_guard,
        generated_paths=generated,
    )


def _echo_script_iteration(
    ref: TargetRef,
    ticket: Ticket,
    *,
    stateless: bool,
) -> None:
    if stateless:
        typer.echo(f"→ running {ref.id_slug} ticket.py", err=True)
        return
    current = ticket.current_step()
    if current is None:
        typer.echo(
            f"→ running {ref.id_slug} ticket.py "
            f"(status={ticket.status}, assignee={ticket.assignee or 'unassigned'})"
        )
        return
    typer.echo(
        f"→ entering step {ticket.step}: {current['name']} "
        f"(status={ticket.status}, assignee={ticket.assignee or 'unassigned'})"
    )


__all__ = [
    "SCRIPT_ENTRY_POINT",
    "ScriptChainResult",
    "ScriptPhaseResult",
    "ScriptPublicationError",
    "run_script_chain",
    "run_script_phase",
    "script_entry_point",
]
