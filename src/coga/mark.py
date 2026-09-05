"""Status transitions — the shared core of `coga mark` and lifecycle callers.

These finalizers mutate ticket frontmatter, append a repo-global `log.md`
line (tagged by task ref), and echo
the local outcome. Terminal outcomes still enter Slack through the digest path;
routine active/paused transitions are intentionally local-only noise. The CLI
commands and the auto-merge scanner all reuse the same helpers so the on-disk
shape stays identical regardless of who triggered the transition.

`advance_step` lives in `coga.bump` — that's the workflow plane.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer

from coga import git
from coga.blackboard import prelaunch_blackboard_synthesis_reason
from coga.config import Config
from coga.lifecycle import CANCELABLE_STATUSES
from coga.logfile import append_log
from coga.paths import log_path, resolve_workflow_path
from coga.period_state import (
    StateSnapshot,
    parent_ticket_path,
    read_snapshot,
    stale_keys,
)
from coga.notification import digest_spool_path, notify, post
from coga.tasks import TaskRef
from coga.ticket import Ticket
from coga.validate import assert_task_valid
from coga.workflow import Workflow

# Workflows with no push/PR step: finishing one with committed product code
# strands that code off the control branch. Kept as a set so the guard can grow
# to other bodyless flows without touching the call site.
_NO_PR_WORKFLOWS = {"direct/body"}


class StrandedProductCode(RuntimeError):
    """Raised when a `direct/body` ticket is finished with committed product
    code that will not reach the control branch (the workflow has no push/PR
    step). The CLI renders the offending paths and points at a `code/*`
    workflow; `--force` overrides.
    """

    def __init__(self, workflow_name: str, paths: list[str]):
        self.workflow_name = workflow_name
        self.paths = paths
        super().__init__(
            f"{workflow_name} task committed {len(paths)} tracked product "
            "file(s) not on the control branch"
        )


def _workflow_name(ticket: Ticket) -> str | None:
    """The ticket's workflow name, whether frozen (dict) or a bare-string ref."""
    wf = ticket.workflow
    if isinstance(wf, dict):
        name = wf.get("name")
        return str(name) if name else None
    if isinstance(wf, str):
        return wf.strip() or None
    return None


def _assert_no_stranded_product_code(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Refuse to finish a no-PR-workflow ticket that committed product code.

    A `direct/body` (or other push/PR-less) workflow lands only Coga OS state on
    the control branch; any tracked product code the agent committed rides a
    throwaway branch or detached checkout that never reaches `main` and dangles
    when that checkout is removed. Detect it before the `done` write and raise
    so the CLI can steer the ticket to a `code/*` workflow (or `--force` past
    it).
    """
    name = _workflow_name(ticket)
    if name not in _NO_PR_WORKFLOWS:
        return
    stranded = git.stranded_product_paths(cfg, ref.path)
    if stranded:
        raise StrandedProductCode(name or "direct/body", stranded)


def _state_guard(cfg: Config, ref: TaskRef) -> Callable[[str], None]:
    """The regression guard every transition below hands to its git sync.

    A transition's sync overlays this ticket wholesale onto the control tip, so
    a checkout holding a stale copy — one that went stale while an agent worked,
    or while the `autoclose-merged` sweep closed the ticket from the primary
    checkout — would otherwise bury the newer state. The guard re-checks the
    control copy on every landing attempt, including the base refetched after a
    non-fast-forward retry, and refuses rather than overwriting terminal or
    further-advanced state.

    The refusal is loud but non-fatal, and deliberately lands *after* the local
    ticket write: the transition the human asked for stays on disk, git declines
    to publish it, and the checkout is left visibly behind control (`coga
    status` flags it via `stale_coga_task_rels`). Moving the write behind a
    fetch would put the network on every status transition.
    """
    return git.ticket_state_guard(cfg, ref.ticket_path)


def _prepare_outcome_spool(
    cfg: Config,
    mutation_snapshot: git.FileMutationRollback | None,
) -> Path | None:
    """Resolve/migrate the digest spool and arm a strict expected creation."""
    spool_path = digest_spool_path(cfg)
    if mutation_snapshot is None or spool_path is None:
        return spool_path
    if spool_path not in mutation_snapshot.originals:
        raise git.FeaturePublicationError(
            f"strict outcome snapshot does not cover digest spool {spool_path}"
        )
    original = mutation_snapshot.originals[spool_path]
    current = spool_path.read_bytes()
    if current == original:
        mutation_snapshot.require_unchanged(spool_path)
    elif original is None:
        # Legacy migration created the new spool after the command acquired
        # its lease; the pre-lease snapshot explicitly covered that absence.
        mutation_snapshot.arm({spool_path: current})
    else:
        raise git.FeaturePublicationError(
            f"digest spool changed before strict outcome publication: {spool_path}"
        )
    return spool_path


def mark_done(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    digest_detail: str,
    image_url: str | None = None,
    echo: str | None = None,
    force: bool = False,
    publish_current_branch: bool = False,
    feature_publication: git.FeaturePublicationLease | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
    mutation_snapshot: git.FileMutationRollback | None = None,
    after_sync: Callable[[], None] | None = None,
    state_guard: Callable[[str], None] | None = None,
    strict_state_guard: bool = False,
    strict_state_sync: bool = False,
) -> None:
    """Flip a ticket to `done`: write frontmatter, log, notify.

    `done` is the routine outcome Slack still needs, so it routes through
    `notification.notify`: spooled into the daily digest when that ticket is
    installed, else posted live as `slack_text` (image and all).
    `digest_detail` is the one-liner shown under this ticket in the digest.

    `echo` is the stdout line printed before the notify (so the local outcome
    is visible even if a live post crashes). Pass `None` to suppress — used by
    quiet auto-bump paths such as launch-time freshness checks.

    A `direct/body` ticket that committed tracked product code off the control
    branch is refused with `StrandedProductCode` (the code would strand); pass
    `force=True` to override. See `_assert_no_stranded_product_code`.

    A completion gate may set `publish_current_branch=True` so the terminal
    task-state commit is also published to the current feature branch. A
    recorded-assist caller supplies ``feature_publication`` plus an armed
    ``mutation_snapshot`` to publish the terminal ticket, audit, and any
    digest-spool append as one strict feature/control transition. A recurring
    delegator instead supplies an exact ``state_guard`` with
    ``strict_state_guard=True`` and ``strict_state_sync=True``: guard and Git
    transport failures then propagate, and completion is published before it
    is announced, so a stale or unverified child result has no visible
    lifecycle side effect.
    """
    if not force:
        _assert_no_stranded_product_code(cfg, ref, ticket)
    owner = ticket.owner or cfg.current_user
    spool_path = _prepare_outcome_spool(cfg, mutation_snapshot)
    # Validate the prospective close before committing it, the way
    # `mark canceled` already does. An `other-agent` step that cannot resolve
    # against this machine's `[agents.*]` is a config fact rather than
    # something this write caused, so validating afterwards would leave a
    # ticket marked done on disk with no audit entry and no sync — on the very
    # tickets an operator is only trying to close.
    prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    prospective.frontmatter["status"] = "done"
    prospective.frontmatter.pop("step", None)
    prospective.frontmatter.pop("launch_generation", None)
    assert_task_valid(cfg, ref, action="mark done", ticket_override=prospective)
    ticket.frontmatter = prospective.frontmatter
    ticket_bytes = git.write_ticket_under_barrier(
        cfg,
        ticket,
        ref.ticket_path,
        mutation_snapshot=mutation_snapshot,
    )
    audit_append = append_log(cfg, ref.id_slug, actor, log_message)
    if mutation_snapshot is not None:
        mutation_snapshot.arm_append(log_path(cfg), audit_append)

    notification_spooled = False

    def announce() -> None:
        nonlocal notification_spooled
        notify(
            cfg,
            slack_text,
            kind="done",
            detail=digest_detail,
            ticket=ref.id_slug,
            owner=owner,
            watchers=ticket.watchers,
            task_path=ref.path,
            image_url=image_url,
            # The ticket is already `done` on disk; an undeliverable broadcast
            # is reported but never aborts the transition.
            fatal=False,
            record_failure=feature_publication is None,
        )
        if spool_path is not None:
            notification_spooled = True
            if mutation_snapshot is not None:
                mutation_snapshot.arm({spool_path: spool_path.read_bytes()})

    # A digest event is local union-safe state, so strict publication includes
    # it in the same exact generated commit. A live notification waits until
    # the feature/control transition is durable.
    if spool_path is not None and (
        feature_publication is not None or strict_state_sync
    ):
        if mutation_snapshot is None:
            raise git.FeaturePublicationError(
                "strict done publication is missing its mutation snapshot"
            )
        mutation_snapshot.require_unchanged(spool_path)
        announce()
    snapshot = read_snapshot(ref.path)

    def sync_state() -> None:
        _sync_done_state(
            cfg,
            ref,
            snapshot,
            publish_current_branch=publish_current_branch,
            feature_publication=feature_publication,
            feature_publication_guard=feature_publication_guard,
            mutation_snapshot=mutation_snapshot,
            after_sync=after_sync,
            state_guard=state_guard,
            raise_state_regression=strict_state_guard,
            raise_git_error=strict_state_sync,
            spool_path=(
                spool_path
                if notification_spooled
                and (feature_publication is not None or strict_state_sync)
                else None
            ),
        )

    if feature_publication is not None or strict_state_guard or strict_state_sync:
        sync_state()
        if (
            strict_state_guard
            and not strict_state_sync
            and feature_publication is None
            and after_sync is not None
        ):
            after_sync()
        if echo is not None:
            typer.echo(echo)
        if not notification_spooled:
            announce()
    else:
        if echo is not None:
            typer.echo(echo)
        announce()
        sync_state()
    _warn_if_state_not_advanced(
        cfg,
        ref,
        ticket,
        owner,
        snapshot,
        record_failure=feature_publication is None,
    )


class CancellationError(RuntimeError):
    """A requested transition would violate cancellation semantics."""


def mark_canceled(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    reason: str,
    slack_text: str,
    digest_detail: str,
    image_url: str | None = None,
    echo: str | None = None,
    feature_publication: git.FeaturePublicationLease | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
    mutation_snapshot: git.FileMutationRollback | None = None,
    after_sync: Callable[[], None] | None = None,
) -> None:
    """Flip any non-terminal ticket to ``canceled`` and record why.

    The reason is required in this shared layer, not only by Typer, so an
    internal caller cannot create an illegible cancellation. Cancellation
    clears ``step:`` like completion but deliberately leaves the body and
    blackboard untouched; an unresolved blocker therefore remains historical
    context while the ticket itself becomes terminal.
    """
    reason = reason.strip()
    if not reason:
        raise CancellationError("cancellation reason cannot be empty")
    if ticket.status not in CANCELABLE_STATUSES:
        raise CancellationError(
            f"status {ticket.status!r} cannot transition to 'canceled'"
        )

    prior_status = ticket.status
    owner = ticket.owner or cfg.current_user
    spool_path = _prepare_outcome_spool(cfg, mutation_snapshot)
    prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    prospective.frontmatter["status"] = "canceled"
    prospective.frontmatter.pop("step", None)
    prospective.frontmatter.pop("launch_generation", None)
    assert_task_valid(
        cfg,
        ref,
        action="mark canceled",
        ticket_override=prospective,
    )
    ticket.frontmatter = prospective.frontmatter
    ticket_bytes = git.write_ticket_under_barrier(
        cfg,
        ticket,
        ref.ticket_path,
        mutation_snapshot=mutation_snapshot,
    )
    audit_append = append_log(
        cfg,
        ref.id_slug,
        actor,
        f"canceled ({prior_status} → canceled): {reason}",
    )
    if mutation_snapshot is not None:
        mutation_snapshot.arm_append(log_path(cfg), audit_append)

    notification_spooled = False

    def announce() -> None:
        nonlocal notification_spooled
        notify(
            cfg,
            slack_text,
            kind="canceled",
            detail=digest_detail,
            ticket=ref.id_slug,
            owner=owner,
            watchers=ticket.watchers,
            task_path=ref.path,
            image_url=image_url,
            fatal=False,
            record_failure=feature_publication is None,
        )
        if spool_path is not None:
            notification_spooled = True
            if mutation_snapshot is not None:
                mutation_snapshot.arm({spool_path: spool_path.read_bytes()})

    if feature_publication is not None and spool_path is not None:
        if mutation_snapshot is None:
            raise git.FeaturePublicationError(
                "strict canceled publication is missing its mutation snapshot"
            )
        mutation_snapshot.require_unchanged(spool_path)
        announce()

    def sync_state() -> None:
        strict_spool = (
            spool_path
            if notification_spooled and feature_publication is not None
            else None
        )
        git.sync_task_state(
            cfg,
            ref.path,
            message=f"Ticket: {ref.id_slug} — canceled",
            guard=_state_guard(cfg, ref),
            feature_publication=feature_publication,
            feature_publication_guard=feature_publication_guard,
            after_strict_publication=after_sync,
            generated_paths=(
                mutation_snapshot.generated
                if mutation_snapshot is not None
                else None
            ),
            extra_paths=([strict_spool] if strict_spool is not None else []),
            land_union_files_to_control=strict_spool is not None,
        )

    if feature_publication is not None:
        sync_state()
        if echo is not None:
            typer.echo(echo)
        if not notification_spooled:
            announce()
    else:
        if echo is not None:
            typer.echo(echo)
        announce()
        # Preserve cancellation's established immediate union landing for the
        # digest spool on ordinary branches.
        git.sync_paths(
            cfg,
            ref.path,
            [ref.path, *([spool_path] if spool_path is not None else [])],
            message=f"Ticket: {ref.id_slug} — canceled",
            land_union_files_to_control=True,
            guard=_state_guard(cfg, ref),
        )


def _sync_done_state(
    cfg: Config,
    ref: TaskRef,
    snapshot: StateSnapshot | None,
    *,
    publish_current_branch: bool = False,
    feature_publication: git.FeaturePublicationLease | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
    mutation_snapshot: git.FileMutationRollback | None = None,
    after_sync: Callable[[], None] | None = None,
    state_guard: Callable[[str], None] | None = None,
    raise_state_regression: bool = False,
    raise_git_error: bool = False,
    spool_path: Path | None = None,
) -> None:
    message = f"Ticket: {ref.id_slug} — done"
    guard = state_guard or _state_guard(cfg, ref)
    if feature_publication is None:
        publish_kwargs = (
            {"publish_current_branch": True} if publish_current_branch else {}
        )
        strict_state_kwargs = (
            {
                "after_strict_publication": after_sync,
                "generated_paths": (
                    mutation_snapshot.generated
                    if mutation_snapshot is not None
                    else None
                ),
            }
            if raise_git_error
            else {}
        )
        if snapshot is None:
            spool_sync_kwargs = (
                {
                    "extra_paths": [spool_path],
                    "land_union_files_to_control": True,
                }
                if spool_path is not None
                else {}
            )
            git.sync_task_state(
                cfg,
                ref.path,
                message=message,
                guard=guard,
                **spool_sync_kwargs,
                **strict_state_kwargs,
                **(
                    {"raise_state_regression": True}
                    if raise_state_regression
                    else {}
                ),
                **({"raise_git_error": True} if raise_git_error else {}),
                **publish_kwargs,
            )
            return
        paths = [ref.path]
        parent_ticket = parent_ticket_path(cfg, snapshot)
        if parent_ticket.parent.is_dir():
            paths.append(parent_ticket)
        if spool_path is not None:
            paths.append(spool_path)
        spool_sync_kwargs = (
            {"land_union_files_to_control": True}
            if spool_path is not None
            else {}
        )
        git.sync_paths(
            cfg,
            ref.path,
            paths,
            message=message,
            guard=guard,
            **spool_sync_kwargs,
            **strict_state_kwargs,
            **(
                {"raise_state_regression": True}
                if raise_state_regression
                else {}
            ),
            **({"raise_git_error": True} if raise_git_error else {}),
            **publish_kwargs,
        )
        return

    extra_paths: list[Path] = []
    # The parent template's working state (high-water / state keys) lives in the
    # blackboard region of its single-file ticket.md, so sync that file.
    if snapshot is not None:
        parent_ticket = parent_ticket_path(cfg, snapshot)
        if (
            parent_ticket.parent.is_dir()
            and mutation_snapshot is not None
            and parent_ticket in mutation_snapshot.originals
        ):
            extra_paths.append(parent_ticket)
    if spool_path is not None:
        extra_paths.append(spool_path)
    git.sync_task_state(
        cfg,
        ref.path,
        message=message,
        guard=guard,
        publish_current_branch=publish_current_branch,
        feature_publication=feature_publication,
        feature_publication_guard=feature_publication_guard,
        after_strict_publication=after_sync,
        generated_paths=(
            mutation_snapshot.generated
            if mutation_snapshot is not None
            else None
        ),
        extra_paths=extra_paths,
        land_union_files_to_control=spool_path is not None,
        **(
            {"raise_state_regression": True}
            if raise_state_regression
            else {}
        ),
        **({"raise_git_error": True} if raise_git_error else {}),
    )


def _warn_if_state_not_advanced(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    owner: str,
    snapshot: StateSnapshot | None,
    *,
    record_failure: bool = True,
) -> None:
    """Flag a period task that completed without advancing its declared state.

    A recurring task can declare the blackboard keys it owns (`state_keys:`);
    the creator snapshots their values into the period task. If a declared
    key still equals that snapshot when the run finishes, the run did the work
    but never recorded its high-water mark — the next firing will redo the same
    range. Warn locally and broadcast an important alert.

    No-op for any task without a snapshot — i.e. every non-recurring task. This
    is advisory only: it runs after the transition has already committed, and a
    failed broadcast must never turn a successful `mark done` into an error.
    """
    if snapshot is None:
        return
    stale = stale_keys(cfg, snapshot)
    if not stale:
        return

    keys = ", ".join(stale)
    typer.echo(
        f"⚠ declared state key(s) {keys} did not advance this run. The parent "
        f"recurring task's blackboard still holds the value this period started "
        f"with, so the next firing will redo the same range. Record state before "
        f"finishing (or record an explicit skip)."
    )

    try:
        post(
            cfg,
            f"⚠ {ref.id_slug} finished without advancing declared state "
            f"({keys}) — next run may duplicate work.",
            task_path=ref.path,
            owner=owner,
            watchers=ticket.watchers,
            important=True,
            record_failure=record_failure,
        )
    except Exception as exc:  # advisory broadcast — never break completion
        import sys

        sys.stderr.write(f"[period-state] FYI broadcast failed: {exc}\n")


class RequiredExtensionMissing(RuntimeError):
    """Raised when `mark active` is called on a ticket with required-but-empty
    extension fields. The caller renders a per-field error message for the
    user.
    """

    def __init__(self, fields: list[str]):
        self.fields = fields
        super().__init__(
            f"ticket missing values for required extension fields: {fields}"
        )


class WorkflowMissing(RuntimeError):
    """Raised when `mark active` is called on a ticket with no workflow.

    A workflow-less ticket has no steps and can never be advanced by
    `coga bump`, so activating one would strand it. The workflow may be a
    bare string ref (frozen on the first `coga bump`) or an already-frozen
    dict — only `null`/missing is refused.
    """


class BlackboardNeedsSynthesis(RuntimeError):
    """Raised when a draft blackboard still carries pre-launch authoring notes."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def format_blackboard_synthesis_refusal(
    id_slug: str, *, action: str, reason: str
) -> str:
    """Render the operator-facing first-launch blackboard refusal."""
    return (
        f"Cannot {action} {id_slug}: the blackboard has pre-launch notes "
        f"({reason}). Merge the important parts into `## Description` / "
        "`## Context` before launch. If this blackboard content is "
        "intentionally part of the run, keep the durable launch notes under "
        "`## Production notes`, then retry."
    )


def _has_workflow(ticket: Ticket) -> bool:
    """True when the ticket carries a workflow `mark active` can accept.

    Accepts both a bare string ref (hand-authored, frozen here on activate)
    and an already-frozen workflow dict. Rejects `null`, missing, and empty
    values.
    """
    wf = ticket.workflow
    if isinstance(wf, str):
        return bool(wf.strip())
    if isinstance(wf, dict):
        return bool(wf)
    return False


def _freeze_workflow_ref(cfg: Config, ticket: Ticket) -> None:
    """Freeze a bare-string `workflow:` ref and ensure the ticket has a step.

    Hand-authored / guided-authored draft tickets carry `workflow:` as a
    plain workflow name. Activation is when that becomes real: we freeze the
    snapshot. We also seed `step: 1` whenever the ticket has no current step,
    so a fresh draft is launch-ready — `coga launch` composes the current
    step's skill from the frozen workflow. It is a no-op for the workflow dict
    of an `active`/`paused` ticket that already carries a step. Raises
    `WorkflowError` if a string ref names no known workflow.

    Precondition: `_has_workflow(ticket)` is true, so `ticket.workflow` is a
    non-empty string or dict by the time we read its steps.
    """
    wf = ticket.workflow
    if isinstance(wf, str):
        wf_def = Workflow.load(resolve_workflow_path(cfg, wf))
        ticket.frontmatter["workflow"] = wf_def.freeze()
    if not ticket.step:
        steps = (ticket.workflow or {}).get("steps") or []
        if steps:
            ticket.frontmatter["step"] = f"1 ({steps[0]['name']})"


def _missing_required_extensions(cfg: Config, ticket: Ticket) -> list[str]:
    """Return names of `required = true` extension fields that are absent or
    empty on this ticket."""
    missing: list[str] = []
    for name, spec in cfg.ticket_fields.items():
        if not spec.required:
            continue
        value = ticket.frontmatter.get(name, "")
        if not isinstance(value, str) or not value.strip():
            missing.append(name)
    return missing


def _refuse_unsynthesized_draft_blackboard(
    ref: TaskRef, prior_status: str | None
) -> None:
    """Refuse the first launch boundary when authoring notes remain."""
    if prior_status != "draft":
        return
    reason = prelaunch_blackboard_synthesis_reason(
        ref.ticket_path,
        blackboard_required=False,
    )
    if reason is not None:
        raise BlackboardNeedsSynthesis(reason)


def prepare_active(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
) -> None:
    """Validate and mutate ``ticket`` to active without writing durable state.

    Launch uses this pure preparation boundary to compose a prospective prompt
    before an assist's final publication gate. ``mark_active`` remains the
    durable wrapper that writes, audits, and optionally syncs the result.
    """
    prior_status = ticket.status
    if prior_status == "canceled":
        raise CancellationError("a canceled ticket cannot be reactivated")
    _refuse_unsynthesized_draft_blackboard(ref, prior_status)

    if not _has_workflow(ticket):
        raise WorkflowMissing()
    _freeze_workflow_ref(cfg, ticket)

    missing = _missing_required_extensions(cfg, ticket)
    if missing:
        raise RequiredExtensionMissing(missing)

    ticket.frontmatter["status"] = "active"
    # An active task has no live megalaunch claim. The next megalaunch writes
    # a fresh generation atomically with its `in_progress` transition.
    ticket.frontmatter.pop("launch_generation", None)


def mark_active(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    echo: str | None = None,
    sync_state: bool = True,
    mutation_snapshot: git.FileMutationRollback | None = None,
) -> None:
    """Flip a ticket to `active`: write frontmatter and log.

    Refuses to activate a workflow-less ticket. A bare-string `workflow:`
    ref is frozen into its snapshot here so the activated ticket is
    launch-ready. Also refuses if any `required = true` extension field is
    empty. Activation is intentionally silent in Slack; the task log and git
    sync remain the audit trail.
    """
    prior_status = ticket.status
    prepare_active(cfg, ref, ticket)
    ticket_bytes = git.write_ticket_under_barrier(
        cfg,
        ticket,
        ref.ticket_path,
        mutation_snapshot=mutation_snapshot,
    )
    assert_task_valid(cfg, ref, action="mark active")
    audit_append = append_log(cfg, ref.id_slug, actor, log_message)
    if mutation_snapshot is not None:
        # Include the generated audit append in the exact publication snapshot.
        mutation_snapshot.arm_append(log_path(cfg), audit_append)
    if echo is not None:
        typer.echo(echo)
    if sync_state:
        git.sync_task_state(
            cfg,
            ref.path,
            message=f"Ticket: {ref.id_slug} — active",
            guard=_state_guard(cfg, ref),
        )


def mark_in_progress(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    echo: str | None = None,
    publish_current_branch: bool = False,
    expected_current_branch: str | None = None,
    expected_current_branch_oid: str | None = None,
    expected_remote_branch_oid: str | None = None,
    feature_publication: git.FeaturePublicationLease | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
    mutation_snapshot: git.FileMutationRollback | None = None,
    after_sync: Callable[[], None] | None = None,
    state_guard: Callable[[str], None] | None = None,
    strict_state_guard: bool = False,
    strict_state_sync: bool = False,
) -> None:
    """Flip a ticket to `in_progress`: write, sync, then optionally post.

    ``after_sync`` observes the exact boundary after durable publication and
    before output or notification work that may still interrupt the caller.
    ``strict_state_guard`` makes a supplied exact guard transactional;
    ``strict_state_sync`` also makes Git publication transactional: an
    unaccepted local commit is unwound and an ambiguous push is reconciled by
    exact remote candidate before rollback. Either strict form publishes
    before start output/notification.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "in_progress"
    ticket_bytes = git.write_ticket_under_barrier(
        cfg,
        ticket,
        ref.ticket_path,
        mutation_snapshot=mutation_snapshot,
    )
    assert_task_valid(cfg, ref, action="mark in_progress")
    audit_append = append_log(cfg, ref.id_slug, actor, log_message)
    if mutation_snapshot is not None:
        # Re-arm after the audit append so strict sync consumes both writes.
        mutation_snapshot.arm_append(log_path(cfg), audit_append)

    def sync_state() -> None:
        if feature_publication is None:
            strict_state_kwargs = (
                {
                    "after_strict_publication": after_sync,
                    "generated_paths": (
                        mutation_snapshot.generated
                        if mutation_snapshot is not None
                        else None
                    ),
                }
                if strict_state_sync
                else {}
            )
            git.sync_task_state(
                cfg,
                ref.path,
                message=f"Ticket: {ref.id_slug} — in_progress",
                guard=state_guard or _state_guard(cfg, ref),
                **strict_state_kwargs,
                **(
                    {"raise_state_regression": True}
                    if strict_state_guard
                    else {}
                ),
                **({"raise_git_error": True} if strict_state_sync else {}),
            )
            return
        git.sync_task_state(
            cfg,
            ref.path,
            message=f"Ticket: {ref.id_slug} — in_progress",
            guard=state_guard or _state_guard(cfg, ref),
            publish_current_branch=publish_current_branch,
            expected_current_branch=expected_current_branch,
            expected_current_branch_oid=expected_current_branch_oid,
            expected_remote_branch_oid=expected_remote_branch_oid,
            feature_publication=feature_publication,
            feature_publication_guard=feature_publication_guard,
            after_strict_publication=after_sync,
            generated_paths=(
                mutation_snapshot.generated
                if mutation_snapshot is not None
                else None
            ),
            **(
                {"raise_state_regression": True}
                if strict_state_guard
                else {}
            ),
            **({"raise_git_error": True} if strict_state_sync else {}),
        )

    # A strict assist publication must succeed before announcing a started
    # session. Preserve the existing notification-before-sync ordering for
    # ordinary launches and other callers.
    if feature_publication is not None or strict_state_guard or strict_state_sync:
        sync_state()
        if (
            strict_state_guard
            and not strict_state_sync
            and feature_publication is None
            and after_sync is not None
        ):
            after_sync()
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        post(
            cfg,
            slack_text,
            task_path=ref.path,
            owner=owner,
            watchers=ticket.watchers,
            fatal=False,
            # Strict lifecycle state already consumed its exact feature lease.
            # Keep a delivery failure on stderr instead of appending an
            # unleased audit line that would dirty the checkout before spawn.
            record_failure=feature_publication is None,
        )
    if (
        feature_publication is None
        and not strict_state_guard
        and not strict_state_sync
    ):
        sync_state()
        if after_sync is not None:
            after_sync()


def mark_blocked(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    image_url: str | None = None,
    echo: str | None = None,
    feature_publication: git.FeaturePublicationLease | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
    mutation_snapshot: git.FileMutationRollback | None = None,
    after_sync: Callable[[], None] | None = None,
    state_guard: Callable[[str], None] | None = None,
) -> None:
    """Flip a ticket to `blocked` without changing its workflow step."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "blocked"
    ticket.frontmatter.pop("launch_generation", None)
    ticket_bytes = git.write_ticket_under_barrier(
        cfg,
        ticket,
        ref.ticket_path,
        mutation_snapshot=mutation_snapshot,
    )
    assert_task_valid(cfg, ref, action="mark blocked")
    audit_append = append_log(cfg, ref.id_slug, actor, log_message)
    if mutation_snapshot is not None:
        # Re-arm with the generated blocker audit line included.
        mutation_snapshot.arm_append(log_path(cfg), audit_append)

    def sync_state() -> None:
        git.sync_task_state(
            cfg,
            ref.path,
            message=f"Ticket: {ref.id_slug} — blocked",
            guard=state_guard or _state_guard(cfg, ref),
            feature_publication=feature_publication,
            feature_publication_guard=feature_publication_guard,
            after_strict_publication=after_sync,
            generated_paths=(
                mutation_snapshot.generated
                if mutation_snapshot is not None
                else None
            ),
        )

    # A resumed single-checkout assist must republish `blocked` before telling
    # the owner the unresolved ask is safely parked. Ordinary block calls keep
    # their established echo/notification-before-sync ordering.
    if feature_publication is not None:
        sync_state()
    if echo is not None:
        typer.echo(echo)
    post(
        cfg,
        slack_text,
        task_path=ref.path,
        owner=owner,
        watchers=ticket.watchers,
        image_url=image_url,
        # `coga block` ends the session: a Slack outage must not keep the
        # blocked ticket's agent REPL alive to its idle timeout.
        fatal=False,
        # The strict state push above consumed this assist lease. A new Slack
        # failure line cannot safely enter the generic CLI sweep afterwards.
        record_failure=feature_publication is None,
    )
    if feature_publication is None:
        sync_state()


def mark_paused(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    digest_detail: str | None = None,
    echo: str | None = None,
    feature_publication: git.FeaturePublicationLease | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
    mutation_snapshot: git.FileMutationRollback | None = None,
    after_sync: Callable[[], None] | None = None,
    state_guard: Callable[[str], None] | None = None,
    strict_state_guard: bool = False,
    strict_state_sync: bool = False,
) -> None:
    """Flip a ticket to `paused`: write frontmatter and log.

    Most pauses are silent on Slack (a human `mark paused`, the interactive
    recurring-cleanup path): they pass neither `slack_text` nor `digest_detail`
    and nothing is broadcast. The one broadcasting caller is the recurring
    liveness watchdog, which pauses a wedged run and needs the team to see it —
    a recurring run that timed out is a `recurring-error`, so when `slack_text`
    is given the pause routes through `notification.notify` (digest-spooled when the
    ticket is installed, else posted live to important); `digest_detail` is its
    one-liner.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "paused"
    ticket.frontmatter.pop("launch_generation", None)
    ticket_bytes = git.write_ticket_under_barrier(
        cfg,
        ticket,
        ref.ticket_path,
        mutation_snapshot=mutation_snapshot,
    )
    assert_task_valid(cfg, ref, action="mark paused")
    audit_append = append_log(cfg, ref.id_slug, actor, log_message)
    if mutation_snapshot is not None:
        mutation_snapshot.arm_append(log_path(cfg), audit_append)

    def sync_state() -> None:
        git.sync_task_state(
            cfg,
            ref.path,
            message=f"Ticket: {ref.id_slug} — paused",
            guard=state_guard or _state_guard(cfg, ref),
            feature_publication=feature_publication,
            feature_publication_guard=feature_publication_guard,
            after_strict_publication=after_sync,
            generated_paths=(
                mutation_snapshot.generated
                if mutation_snapshot is not None
                else None
            ),
            **(
                {"raise_state_regression": True}
                if strict_state_guard
                else {}
            ),
            **({"raise_git_error": True} if strict_state_sync else {}),
        )

    if feature_publication is not None or strict_state_guard or strict_state_sync:
        sync_state()
        if (
            strict_state_guard
            and not strict_state_sync
            and feature_publication is None
            and after_sync is not None
        ):
            after_sync()
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        notify(
            cfg,
            slack_text,
            kind="recurring-error",
            detail=digest_detail or slack_text,
            ticket=ref.id_slug,
            owner=owner,
            watchers=ticket.watchers,
            task_path=ref.path,
            important=True,
            fatal=False,
            record_failure=feature_publication is None,
        )
    if (
        feature_publication is None
        and not strict_state_guard
        and not strict_state_sync
    ):
        sync_state()


__all__ = [
    "mark_active",
    "prepare_active",
    "mark_in_progress",
    "mark_blocked",
    "mark_paused",
    "mark_done",
    "mark_canceled",
    "CancellationError",
    "RequiredExtensionMissing",
    "WorkflowMissing",
    "StrandedProductCode",
]
