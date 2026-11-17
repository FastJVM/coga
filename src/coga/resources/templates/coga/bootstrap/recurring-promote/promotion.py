"""Move a task into the recurring template catalog."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from coga.config import Config
from coga.git import GitError
from coga.delete_task import DeleteTaskError, run_delete_task
from coga.logfile import append_log
from coga.paths import recurring_dir, resolve_workflow_path
from coga.recurring import (
    RecurringError,
    Template,
    resolve_template_source,
    valid_template_name,
    validate_schedule,
)
from coga.taskfile import join_task_body, split_body
from coga.tasks import TaskRef, read_ticket
from coga.ticket import Ticket
from coga.workflow import Workflow, WorkflowError


class RetainedPromotionError(RecurringError):
    """Promotion changed local state that needs operator reconciliation."""


# A task's per-run fields, which a template must not carry. `status`/`step` are
# run state the scanner and workflow own. The generation fields identify
# the individual period and launch. `agent:` is *not* here: a template's main-agent
# choice is a real preference, so promotion keeps it and every period task
# inherits it (see `_TEMPLATE_PASSTHROUGH`). `skills:` is dropped too, but
# reported separately: it is deliberately never copied into a period task (see
# the `coga/recurring/templates` context), so leaving it on the template would look
# load-bearing while doing nothing.
_TASK_ONLY_FIELDS = (
    "status",
    "step",
    "period_generation",
    "launch_generation",
)

# What a template passes through to each period task, in render order. Mirrors
# the fields `_create_at_slug` reads back off the template.
_TEMPLATE_PASSTHROUGH = (
    "title",
    "workflow",
    "owner",
    "agent",
    "contexts",
    "secrets",
)

# A live run's step/blocker state has nowhere to go in a template, and dropping
# it silently would abandon an in-flight handoff. Refuse instead and let the
# human land the run first.
_PROMOTE_REFUSED_STATUSES = ("in_progress", "blocked")

_PROMOTED_BLACKBOARD = "\nThe cross-run state for this recurring task goes here.\n"


@dataclass
class PromoteOutcome:
    """Result of promoting one task into a recurring template."""

    name: str
    path: Path  # the new `coga/recurring/<name>/` directory
    source_slug: str
    source_path: Path
    dropped_skills: list[str]
    dropped_blackboard: bool
    attachments: list[Path]
    source_files: list[Path]


def promote_task(
    cfg: Config,
    ref: TaskRef,
    *,
    schedule: str,
    name: str | None = None,
    now: datetime | None = None,
) -> PromoteOutcome:
    """Move a task out of `tasks/` and into `recurring/<name>/` as a template.

    The authoring path for "this ticket should run every period": it does the
    task→template frontmatter transform, stamps the validated `schedule:`, and
    resets the blackboard to cross-run state (task scratch is one-run state and
    must not masquerade as a recurring cursor).

    Order is deliberate — the cron is validated and the destination checked
    *before* anything moves, and the written template is re-loaded through
    `Template.load` before the source task is removed. A bad schedule, an
    occupied name, or a template that fails to load leaves the source ticket
    untouched.
    """
    now = now or datetime.now()
    validate_schedule(schedule, now)

    ticket = read_ticket(ref)
    if ticket.status in _PROMOTE_REFUSED_STATUSES:
        raise RecurringError(
            f"{ref.id_slug} is {ticket.status!r} — a template cannot hold a live "
            f"run's step or blocker. Land the run first (`coga mark done "
            f"{ref.id_slug}`, or `coga unblock`), then promote."
        )

    template_name = name or ref.slug
    if not valid_template_name(template_name):
        raise RecurringError(
            f"invalid recurring template name {template_name!r} — it is a single "
            "directory name under `coga/recurring/` (letters, digits, `.`, `_`, "
            "`-`; no slashes, and `_` is reserved for parked templates). Pass "
            "`--name`."
        )
    dest = recurring_dir(cfg) / template_name
    source = resolve_template_source(cfg, template_name)
    if source.error:
        raise RecurringError(source.error)
    if dest.exists() or dest.is_symlink() or source.definition_dir is not None:
        raise RecurringError(
            f"`coga/recurring/{template_name}/` already exists — refusing to "
            f"overwrite it. Pass `--name` to pick another template name, or "
            f"remove the existing template first."
        )

    frontmatter, dropped_skills = _template_frontmatter(ticket, schedule)
    _validate_promoted_workflow(cfg, frontmatter)
    above, blackboard = split_body(ticket.body, blackboard_required=False)

    source_files = [ref.ticket_path] if ref.file_form else [
        path for path in ref.path.rglob("*") if path.is_symlink() or not path.is_dir()
    ]
    dest.mkdir(parents=True)
    try:
        # Directory-form attachments travel with the ticket — the promote is a
        # move, not a rewrite. The state snapshot is the one exception: it is a
        # period task's create-time baseline, not template state.
        if not ref.file_form:
            for sibling in sorted(ref.path.iterdir()):
                if sibling.name in ("ticket.md", ".state-snapshot.json"):
                    continue
                sibling_dest = dest / sibling.name
                if sibling.is_symlink():
                    sibling_dest.symlink_to(
                        sibling.readlink(),
                        target_is_directory=sibling.is_dir(),
                    )
                elif sibling.is_dir():
                    shutil.copytree(sibling, sibling_dest, symlinks=True)
                else:
                    shutil.copy2(sibling, sibling_dest)
        ticket_path = dest / "ticket.md"
        ticket_path.write_text(
            _render_template_text(frontmatter, join_task_body(above, _PROMOTED_BLACKBOARD)),
            encoding="utf-8", newline="\n",
        )
        Template.load(dest, now=now)
        attachments = [
            path.relative_to(dest)
            for path in dest.rglob("*")
            if path != ticket_path and (path.is_symlink() or not path.is_dir())
        ]
    except (RecurringError, OSError, UnicodeError) as exc:
        try:
            shutil.rmtree(dest)
        except OSError as cleanup:
            raise RetainedPromotionError(
                f"Promotion failed: {exc}. Could not clean up {dest}: {cleanup}. "
                f"The source remains at {ref.path}."
            ) from cleanup
        raise

    try:
        run_delete_task(cfg, ref)
    except (DeleteTaskError, OSError) as exc:
        raise RetainedPromotionError(
            f"Could not remove source {ref.path}: {exc}. "
            f"The verified template remains at {dest}. Inspect both paths."
        ) from exc

    try:
        append_log(
            cfg,
            ref.id_slug,
            "human",
            f"promoted to recurring template `recurring/{template_name}` "
            f"(schedule {schedule})",
        )
    except (GitError, OSError, ValueError) as exc:
        raise RetainedPromotionError(
            f"Could not record promotion from {ref.path} to {dest}: {exc}. "
            "The local move is retained. Reconcile it before publication."
        ) from exc

    return PromoteOutcome(
        name=template_name,
        path=dest,
        source_slug=ref.id_slug,
        source_path=ref.path,
        dropped_skills=dropped_skills,
        dropped_blackboard=bool((blackboard or "").strip()),
        attachments=attachments,
        source_files=source_files,
    )


def _template_frontmatter(
    ticket: Ticket, schedule: str
) -> tuple[dict[str, Any], list[str]]:
    """Transform task frontmatter into template frontmatter.

    Returns the new mapping (schedule first, then the documented passthrough
    fields, then any repo extension fields) and the dropped `skills:` refs.
    """
    fm: dict[str, Any] = {"schedule": schedule}
    for key in _TEMPLATE_PASSTHROUGH:
        if key not in ticket.frontmatter:
            continue
        value = ticket.frontmatter[key]
        if key == "workflow":
            # A launched task carries the frozen workflow snapshot; a template
            # names the workflow and lets the creator freeze it per period. An
            # absent workflow stays absent — the creator defaults to
            # `direct/body`.
            value = value.get("name") if isinstance(value, dict) else value
        if key == "contexts" and isinstance(value, list):
            # The creator auto-attaches `coga/period-task` to every period task;
            # a promoted former period task would otherwise carry it twice over.
            value = [c for c in value if c != "coga/period-task"]
        if value in (None, [], {}):
            continue
        fm[key] = value

    dropped_skills = [str(s) for s in (ticket.frontmatter.get("skills") or [])]
    handled = set(_TEMPLATE_PASSTHROUGH) | set(_TASK_ONLY_FIELDS) | {"skills"}
    for key, value in ticket.frontmatter.items():
        if key in handled or key in fm:
            continue
        fm[key] = value
    return fm, dropped_skills


def _render_template_text(frontmatter: dict[str, Any], body: str) -> str:
    """Render a template `ticket.md`. Deliberately not `Ticket.render`, which
    would push `schedule:` — not a canonical *task* key — below the extension
    marker."""
    fm_text = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip()
    return f"---\n{fm_text}\n---\n\n{body.lstrip(chr(10))}"


def _validate_promoted_workflow(
    cfg: Config, frontmatter: dict[str, Any]
) -> None:
    """Ensure the transformed template can resolve its per-period workflow."""
    workflow_name = frontmatter.get("workflow") or "direct/body"
    if not isinstance(workflow_name, str):
        raise RecurringError(
            "promoted template `workflow:` must be a workflow name"
        )
    try:
        Workflow.load(resolve_workflow_path(cfg, workflow_name))
    except WorkflowError as exc:
        raise RecurringError(
            f"cannot promote task with workflow {workflow_name!r}: {exc}"
        ) from exc
