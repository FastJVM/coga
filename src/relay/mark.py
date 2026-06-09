"""Status transitions — the shared core of `relay mark` and `relay automerge`.

These finalizers mutate ticket frontmatter, append a `log.md` line, echo the
local outcome, and post to Slack. The CLI commands and the auto-merge scanner
all reuse the same helpers so the on-disk shape stays identical regardless
of who triggered the transition.

`advance_step` lives in `relay.bump` — that's the workflow plane.
"""

from __future__ import annotations

import typer

from relay import git
from relay.config import Config
from relay.logfile import append_log
from relay.paths import workflow_path
from relay.slack import notify, post
from relay.tasks import TaskRef
from relay.ticket import Ticket
from relay.validate import assert_task_valid
from relay.workflow import Workflow


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
) -> None:
    """Flip a ticket to `done`: write frontmatter, log, notify.

    `done` is a batchable event, so it routes through `slack.notify`: spooled
    into the daily digest when that ticket is installed, else posted live as
    `slack_text` (image and all). `digest_detail` is the one-liner shown under
    this ticket in the digest.

    `echo` is the stdout line printed before the notify (so the local outcome
    is visible even if a live post crashes). Pass `None` to suppress — used by
    quiet auto-bump paths such as launch-time freshness checks.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action="mark done")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
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
    )
    git.sync_task_state(cfg, ref.path, message=f"Ticket: {ref.id_slug} — done")


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
    `relay bump`, so activating one would strand it. The workflow may be a
    bare string ref (frozen on the first `relay bump`) or an already-frozen
    dict — only `null`/missing is refused.
    """


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
    so the activated ticket is launch-ready — `relay launch` composes the
    current step's skill from the frozen workflow. That covers two cases: a
    fresh draft (never stepped) and a re-activated `done` ticket whose `step:`
    was cleared by `mark done` — re-activation restarts the frozen workflow
    from the top. No-op for the workflow dict of an `active`/`paused` ticket
    that already carries a step. Raises `WorkflowError` if a string ref names
    no known workflow.

    Precondition: `_has_workflow(ticket)` is true, so `ticket.workflow` is a
    non-empty string or dict by the time we read its steps.
    """
    wf = ticket.workflow
    if isinstance(wf, str):
        wf_def = Workflow.load(workflow_path(cfg, wf))
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


def mark_active(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    digest_detail: str,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `active`: write frontmatter, log, notify.

    Refuses to activate a workflow-less ticket. A bare-string `workflow:`
    ref is frozen into its snapshot here so the activated ticket is
    launch-ready. Also refuses if any `required = true` extension field is
    empty. The approval is a batchable event — spooled into the digest when
    installed, else posted live (see `slack.notify`).
    """
    if not _has_workflow(ticket):
        raise WorkflowMissing()
    _freeze_workflow_ref(cfg, ticket)

    missing = _missing_required_extensions(cfg, ticket)
    if missing:
        raise RequiredExtensionMissing(missing)

    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "active"
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action="mark active")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    notify(
        cfg,
        slack_text,
        kind="active",
        detail=digest_detail,
        ticket=ref.id_slug,
        owner=owner,
        watchers=ticket.watchers,
        task_path=ref.path,
    )
    git.sync_task_state(cfg, ref.path, message=f"Ticket: {ref.id_slug} — active")


def mark_in_progress(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `in_progress`: write frontmatter, log, optionally post."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action="mark in_progress")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        post(cfg, slack_text, task_path=ref.path, owner=owner, watchers=ticket.watchers)
    git.sync_task_state(cfg, ref.path, message=f"Ticket: {ref.id_slug} — in_progress")


def mark_paused(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    digest_detail: str,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `paused`: write frontmatter, log, notify (batchable)."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "paused"
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action="mark paused")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    notify(
        cfg,
        slack_text,
        kind="paused",
        detail=digest_detail,
        ticket=ref.id_slug,
        owner=owner,
        watchers=ticket.watchers,
        task_path=ref.path,
    )
    git.sync_task_state(cfg, ref.path, message=f"Ticket: {ref.id_slug} — paused")


__all__ = [
    "mark_active",
    "mark_in_progress",
    "mark_paused",
    "mark_done",
    "RequiredExtensionMissing",
    "WorkflowMissing",
]
