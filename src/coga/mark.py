"""Status transitions — the shared core of `coga mark` and lifecycle callers.

These finalizers mutate ticket frontmatter, append a repo-global `log.md`
line (tagged by task ref), and echo
the local outcome. Terminal outcomes post live to Slack as they happen;
routine active/paused transitions are intentionally local-only noise. The CLI
commands and the auto-merge scanner all reuse the same helpers so the on-disk
shape stays identical regardless of who triggered the transition.

`advance_step` lives in `coga.bump` — that's the workflow plane.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from coga import git
from coga.blackboard import prelaunch_blackboard_synthesis_reason
from coga.bump import OperatorResolutionError, resolve_main_agent, resolve_operator
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
from coga.notification import notify, post
from coga.tasks import TaskRef
from coga.ticket import Ticket
from coga.validate import assert_task_valid
from coga.workflow import Workflow, WorkflowError

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
    stranded = stranded_product_paths(cfg, ref.path)
    if stranded:
        raise StrandedProductCode(name or "direct/body", stranded)


def stranded_product_paths(cfg: Config, anchor_path: Path) -> list[str]:
    """Tracked non-Coga paths this checkout committed that the control branch lacks.

    The detection half of the `direct/body` stranding guard (the 2026-07-06
    DaCapo incident). A merge-base (three-dot) `--name-only` diff of HEAD
    against the control branch, restricted to paths outside the Coga OS-state
    subtree (and a relocated `[layout] contexts` root), so an independently
    advanced control branch is not mistaken for stranded work and a HEAD level
    with control is a fast `[]`. Only tracked, committed files appear.

    Fail-open: `[]` when git is disabled, this is not a git repo, the control
    branch is absent, or any probe fails — a guard that cannot inspect git must
    not block a local `mark done` (the on-disk markdown is the source of truth).
    """
    if not cfg.git_enabled:
        return []
    try:
        root = git.toplevel(anchor_path)
        if root is None:
            return []
        base = _local_control_base(cfg, root)
        if base is None:
            return []
        if git.run_git(root, "rev-parse", "HEAD").strip() == base:
            return []
        excludes = [
            f":(exclude){git.relative_to_root(root, path)}"
            for path in {cfg.repo_root, cfg.contexts_root}
        ]
        # `-z` (NUL-delimited, no path quoting) so a product file with
        # non-ASCII characters is named verbatim in the `mark done` error.
        out = git.run_git(
            root, "diff", "-z", "--name-only", f"{base}...HEAD", "--", ".", *excludes
        )
        return [path for path in out.split("\x00") if path]
    except git.GitError:
        return []


def _local_control_base(cfg: Config, root: Path) -> str | None:
    for ref in (
        f"refs/heads/{cfg.git_control_branch}",
        f"refs/remotes/{cfg.git_remote}/{cfg.git_control_branch}",
    ):
        try:
            return git.run_git(root, "rev-parse", "--verify", "-q", ref).strip()
        except git.GitError:
            continue
    return None


def mark_done(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    image_url: str | None = None,
    echo: str | None = None,
    force: bool = False,
    strict: bool = False,
) -> None:
    """Flip a ticket to `done`: write frontmatter, log, notify.

    `done` is the routine outcome Slack still needs, so it routes through
    `notification.notify`, which posts `slack_text` live (image and all).

    `echo` is the stdout line printed before the notify (so the local outcome
    is visible even if a live post crashes). Pass `None` to suppress — used by
    quiet auto-bump paths such as launch-time freshness checks.

    A `direct/body` ticket that committed tracked product code off the control
    branch is refused with `StrandedProductCode` (the code would strand); pass
    `force=True` to override. See `_assert_no_stranded_product_code`.

    `strict=True` (a recurring delegator publishing a child's result) makes
    the git publication transactional: refusals and transport failures
    propagate, and completion is published before it is announced, so a stale
    or unverified child result has no visible lifecycle side effect.
    """
    if not force:
        _assert_no_stranded_product_code(cfg, ref, ticket)
    owner = ticket.owner or cfg.current_user
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
    git.write_ticket(cfg, ticket, ref.ticket_path)
    append_log(cfg, ref.id_slug, actor, log_message)
    snapshot = read_snapshot(ref.path)

    def announce() -> None:
        notify(
            cfg,
            slack_text,
            kind="done",
            owner=owner,
            task_path=ref.path,
            image_url=image_url,
            # The ticket is already `done` on disk; an undeliverable broadcast
            # is reported but never aborts the transition.
            fatal=False,
        )

    def sync_state() -> None:
        paths = [ref.path, log_path(cfg)]
        # The parent template's working state (high-water / state keys) lives
        # in the blackboard region of its single-file ticket.md, so publish it
        # with the period task.
        if snapshot is not None:
            parent_ticket = parent_ticket_path(cfg, snapshot)
            if parent_ticket.parent.is_dir():
                paths.append(parent_ticket)
        _publish(cfg, ref, paths, f"Ticket: {ref.id_slug} — done", strict=strict)

    # A strict caller waits until the transition is durable before announcing;
    # the ordinary path announces before syncing.
    if strict:
        sync_state()
    if echo is not None:
        typer.echo(echo)
    announce()
    if not strict:
        sync_state()
    _warn_if_state_not_advanced(cfg, ref, ticket, owner, snapshot)


def _publish(
    cfg: Config, ref: TaskRef, paths: list[Path], message: str, *, strict: bool
) -> None:
    """One task-state publication; non-fatal unless `strict`."""
    try:
        git.publish(cfg, paths, message)
    except git.StateRegressionError as exc:
        sys.stderr.write(f"[git] sync refused: {exc}. Message was: {message}\n")
        if strict:
            raise
    except git.GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        append_log(cfg, ref.id_slug, "git", f"sync failed: {exc}")
        if strict:
            raise


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
    image_url: str | None = None,
    echo: str | None = None,
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
    git.write_ticket(cfg, ticket, ref.ticket_path)
    append_log(
        cfg,
        ref.id_slug,
        actor,
        f"canceled ({prior_status} → canceled): {reason}",
    )
    if echo is not None:
        typer.echo(echo)
    notify(
        cfg,
        slack_text,
        kind="canceled",
        owner=owner,
        task_path=ref.path,
        image_url=image_url,
        fatal=False,
    )
    git.sync_task_state(cfg, ref.path, message=f"Ticket: {ref.id_slug} — canceled")


def _warn_if_state_not_advanced(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    owner: str,
    snapshot: StateSnapshot | None,
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
            important=True,
        )
    except Exception as exc:  # advisory broadcast — never break completion
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


class MainAgentUnavailable(RuntimeError):
    """Raised when activation cannot settle this ticket's main agent.

    Either the ticket names an agent that configuration no longer declares, or
    it names none and no `[agents.*]` table exists to default to. Both are
    routing inputs a human fixes; activation refuses rather than substituting a
    different agent behind the operator's back.
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
    of an `active`/`paused` ticket that already carries a step.

    Seeding a step writes no assignment: who holds step 1 is derived from the
    frozen role every time it is read (`coga.bump.resolve_operator`), so a
    stored nickname can no longer disagree with the snapshot's own role the way
    it once could. Raises `WorkflowError` if a string ref names no known
    workflow — every activation caller already renders that.

    Precondition: `_has_workflow(ticket)` is true, so `ticket.workflow` is a
    non-empty string or dict by the time we read its steps.
    """
    wf = ticket.workflow
    if isinstance(wf, str):
        wf_def = Workflow.load(resolve_workflow_path(cfg, wf))
        ticket.frontmatter["workflow"] = wf_def.freeze()
    if not ticket.step:
        frozen = ticket.workflow or {}
        steps = frozen.get("steps") or []
        if steps:
            ticket.frontmatter["step"] = f"1 ({steps[0]['name']})"


def _select_main_agent(cfg: Config, ticket: Ticket) -> None:
    """Freeze this ticket's main agent, if it has not chosen one already.

    Activation is the moment approved work first needs an agent, so it is where
    an omitted choice becomes a concrete, stable identity: the configured
    default is resolved once and persisted in `agent:`. Everything afterwards —
    pause/resume, peer review, unblock, terminal transitions — retains it, so
    reordering `[agents.*]` between launches changes only *future* activations
    and can never turn a ticket's `main -> peer -> main` rotation into
    `main -> peer -> peer`.

    An explicit choice is never replaced, only validated. Removing a selected
    agent from configuration is an error to fix, not permission to substitute
    another one. Peers stay live configuration and are deliberately not frozen
    here.
    """
    try:
        ticket.frontmatter["agent"] = resolve_main_agent(
            cfg, ticket.agent, allow_prospective_default=True
        )
    except OperatorResolutionError as exc:
        raise MainAgentUnavailable(str(exc)) from exc


def _assert_operator_resolves(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Refuse activation whose prepared step has no derivable operator.

    Activation is the last cheap boundary before a ticket becomes launchable, so
    a role token this machine cannot resolve — an ambiguous `other-agent`, an
    `owner` step on a ticket with no owner — fails here rather than surfacing
    later as a launch refusing a step its own snapshot declares. It runs on the
    prospective ticket, so a refusal leaves the stored bytes untouched.
    """
    try:
        resolve_operator(cfg, ref, ticket)
    except OperatorResolutionError as exc:
        raise WorkflowError(str(exc)) from exc


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

    Main-agent selection lives here rather than in `mark_active` so it is part
    of the *prospective* preparation and commits only with the successful
    transition. A preparation that fails afterwards — a missing required
    extension, a refused publication — leaves the ticket's bytes untouched, so
    a newly chosen agent is never written to a real ticket by a failed attempt.
    """
    prior_status = ticket.status
    if prior_status == "canceled":
        raise CancellationError("a canceled ticket cannot be reactivated")
    _refuse_unsynthesized_draft_blackboard(ref, prior_status)

    if not _has_workflow(ticket):
        raise WorkflowMissing()
    _freeze_workflow_ref(cfg, ticket)
    _select_main_agent(cfg, ticket)
    _assert_operator_resolves(cfg, ref, ticket)

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
    strict: bool = False,
) -> None:
    """Flip a ticket to `active`: write frontmatter and log.

    Refuses to activate a workflow-less ticket. A bare-string `workflow:`
    ref is frozen into its snapshot here so the activated ticket is
    launch-ready. Also refuses if any `required = true` extension field is
    empty. Activation is intentionally silent in Slack; the task log and git
    sync remain the audit trail. `strict=True` propagates a refused or failed
    publication (megalaunch's deferred activation).
    """
    prepare_active(cfg, ref, ticket)
    git.write_ticket(cfg, ticket, ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark active")
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    if sync_state:
        _publish(
            cfg, ref, [ref.path, log_path(cfg)],
            f"Ticket: {ref.id_slug} — active", strict=strict,
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
    strict: bool = False,
) -> None:
    """Flip a ticket to `in_progress`: write, sync, then optionally post.

    `strict=True` (megalaunch's claim) publishes before any output or
    notification and propagates a refused or failed publication, so a claim
    that did not land has no visible side effect.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "in_progress"
    git.write_ticket(cfg, ticket, ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark in_progress")
    append_log(cfg, ref.id_slug, actor, log_message)

    def sync_state() -> None:
        _publish(
            cfg, ref, [ref.path, log_path(cfg)],
            f"Ticket: {ref.id_slug} — in_progress", strict=strict,
        )

    if strict:
        sync_state()
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        post(cfg, slack_text, task_path=ref.path, owner=owner, fatal=False)
    if not strict:
        sync_state()


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
) -> None:
    """Flip a ticket to `blocked` without changing its workflow step."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "blocked"
    ticket.frontmatter.pop("launch_generation", None)
    git.write_ticket(cfg, ticket, ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark blocked")
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(
        cfg,
        slack_text,
        task_path=ref.path,
        owner=owner,
        image_url=image_url,
        # `coga block` ends the session: a Slack outage must not keep the
        # blocked ticket's agent REPL alive to its idle timeout.
        fatal=False,
    )
    git.sync_task_state(cfg, ref.path, message=f"Ticket: {ref.id_slug} — blocked")


def mark_paused(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    echo: str | None = None,
    strict: bool = False,
) -> None:
    """Flip a ticket to `paused`: write frontmatter and log.

    Most pauses are silent on Slack (a human `mark paused`, the interactive
    recurring-cleanup path): they pass no `slack_text` and nothing is
    broadcast. The one broadcasting caller is the recurring liveness watchdog,
    which pauses a wedged run and needs the team to see it — a recurring run
    that timed out is a `recurring-error`, so when `slack_text` is given the
    pause routes through `notification.notify`, posted live to important.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "paused"
    ticket.frontmatter.pop("launch_generation", None)
    git.write_ticket(cfg, ticket, ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark paused")
    append_log(cfg, ref.id_slug, actor, log_message)

    def sync_state() -> None:
        _publish(
            cfg, ref, [ref.path, log_path(cfg)],
            f"Ticket: {ref.id_slug} — paused", strict=strict,
        )

    if strict:
        sync_state()
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        notify(
            cfg,
            slack_text,
            kind="recurring-error",
            owner=owner,
            task_path=ref.path,
            important=True,
            fatal=False,
        )
    if not strict:
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
    "MainAgentUnavailable",
    "StrandedProductCode",
    "stranded_product_paths",
]
