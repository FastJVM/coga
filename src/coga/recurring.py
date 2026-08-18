"""Recurring task templates under `coga/recurring/<name>/`."""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml
from croniter import CroniterError, croniter

from coga.create import create_task
from coga.config import Config
from coga.delete_task import DeleteTaskError, run_delete_task
from coga.logfile import (
    append_log,
    iter_log_messages,
    iter_log_messages_reverse,
)
from coga.paths import recurring_dir, resolve_workflow_path
from coga.period_state import write_snapshot
from coga.taskfile import (
    join_task_body,
    split_body,
)
from coga.tasks import TaskRef, list_tasks, read_ticket
from coga.ticket import Ticket
from coga.validate import TaskValidationError
from coga.workflow import Workflow, WorkflowError


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
class RecurringError(Exception):
    pass


@dataclass
class Template:
    """A recurring task — a ticket-format directory under `recurring/<name>/`.

    `ticket.md` carries the schedule and run body; its blackboard region
    (below the fence) persists across runs for task-specific forward state.
    The serviced-period high-water mark lives in the append-only repo-global
    `coga/log.md`, tagged `recurring/<name>`.
    """

    path: Path  # the recurring task directory
    name: str
    frontmatter: dict[str, Any]
    body: str

    @classmethod
    def load(cls, path: Path, *, now: datetime | None = None) -> "Template":
        ticket = path / "ticket.md"
        if not ticket.is_file():
            raise RecurringError("missing ticket.md")
        match = _FM_RE.match(ticket.read_text())
        if not match:
            raise RecurringError("ticket.md missing YAML frontmatter")
        fm = yaml.safe_load(match.group(1)) or {}
        if not isinstance(fm, dict):
            raise RecurringError("frontmatter must be a mapping")
        if "schedule" not in fm:
            raise RecurringError("`schedule` is required")
        _validate_schedule(fm["schedule"], now or datetime.now())
        if "state_keys" in fm:
            state_keys = fm["state_keys"]
            if not isinstance(state_keys, list) or not all(
                isinstance(key, str) and key.strip() for key in state_keys
            ):
                raise RecurringError(
                    "`state_keys` must be a list of non-empty strings"
                )
        if "recipe" in fm:
            recipe = fm["recipe"]
            if not isinstance(recipe, str) or not recipe.strip():
                raise RecurringError("`recipe` must be a non-empty string")
            from coga.runner import RECIPES

            if recipe not in RECIPES:
                known = ", ".join(sorted(RECIPES))
                raise RecurringError(
                    f"unknown recipe {recipe!r}; known recipes: {known}"
                )
        return cls(path=path, name=path.name, frontmatter=fm, body=match.group(2))

    @property
    def schedule(self) -> str:
        return self.frontmatter["schedule"]

    @property
    def recipe(self) -> str | None:
        value = self.frontmatter.get("recipe")
        return value if isinstance(value, str) else None

    @property
    def ticket_path(self) -> Path:
        """The template's single-file `ticket.md`.

        Its blackboard region (below the `<!-- coga:blackboard -->` fence)
        holds task-specific working state composed into each run's prompt.
        The serviced-period ledger lives in the repo-global log (see
        `_record_run`), which is never composed.
        """
        return self.path / "ticket.md"


@dataclass
class CreateOutcome:
    """Result of creating one recurring template for a given firing.

    `created` is False when a task already exists for the template — the
    create is idempotent, so two `coga recurring` runs converge on the
    stable `tasks/recurring/<name>/` directory. `replaced_done` identifies a
    prior-period completed task that was deleted before this fresh creation.
    """

    ref: TaskRef
    created: bool
    replaced_done: bool = False


# The cleanup template runs last in a bare sweep so its retro/cleanup pass acts
# on the period tickets the *same* sweep just produced. Dream is Coga's
# recurring janitor: its Phase-4 retro pass is the sole deleter of `done`
# recurring period tickets, so if it launched before the templates it reaps
# (alphabetical order put it mid-rotation), the sweep's own freshly-`done`
# tickets weren't cleaned up until the *next* Dream run — cleanup lagged a full
# sweep. Hardcoding the name here keeps the ordering legible at the cost of
# making Dream load-bearing in the engine; see `DueScan.due`.
_CLEANUP_TEMPLATE = "dream"


@dataclass
class DueTask:
    """One recurring template's current-period task, after get-or-create.

    `coga recurring` materializes this for every template, then launches the
    `launchable` ones (`active`, plus an `in_progress` orphan it resumes —
    see `launchable`). `last_fire` is the scheduled firing this task covers —
    used to report "ready" vs "overdue" and to order launches.

    `ref` is `None` when the period was already serviced earlier and the task
    directory has since been removed. The repo-global log carries the
    serviced-period high-water mark used for that decision.
    """

    template: str
    ref: TaskRef | None
    last_fire: datetime
    created: bool
    status: str
    recipe: str | None = None
    period_key: str = ""
    replaced_done: bool = False

    @property
    def launchable(self) -> bool:
        # `active` → created-and-not-yet-run (created this scan or carried
        # over from one that never launched it).
        # `in_progress` → a *past* sweep died mid-run and left a recurring task
        # frozen. `coga recurring` is a foreground command — no daemon, no
        # concurrent sweep in normal use — so an `in_progress` recurring task at
        # scan time can only be a dead sweep's orphan, never a live session.
        # Relaunch it: `coga launch` resumes an `in_progress` ticket from its
        # current `step:` (it only flips status on an `active` launch). Worst
        # case a false relaunch redoes a step the human then catches — cheaper
        # than a liveness mechanism. The orphan need not be the *current*
        # period's — identity is the `recurring` directory plus the template
        # leaf slug, so a stale leftover is found and resumed too (and defers
        # the next period until it reaches a closed/paused state: one live task per
        # template).
        # `done` → finished work, never re-run normally. `canceled` →
        # intentionally abandoned and never reactivated. `paused` → a human
        # parked it.
        return self.status in {"active", "in_progress"}

    @property
    def resuming(self) -> bool:
        """A launchable orphan being resumed, not a fresh launch.

        True only for an `in_progress` period task — a dead sweep's orphan
        that `coga launch` will re-compose from its current `step:`. Drives
        the "→ resume" vs "→ launch" distinction in the scan table.
        """
        return self.launchable and self.status == "in_progress"

    @property
    def is_cleanup(self) -> bool:
        """True for the cleanup template (Dream), which `DueScan.due` orders
        last so its retro pass sees this sweep's freshly-`done` period tickets.
        """
        return self.template == _CLEANUP_TEMPLATE


@dataclass
class DueScan:
    """Outcome of scanning every recurring template for the current period."""

    tasks: list[DueTask]
    errors: list[tuple[str, str]]  # (template_filename, error_message)

    @property
    def due(self) -> list[DueTask]:
        """Launchable tasks in launch order: non-cleanup templates first, the
        cleanup template (Dream) last; within each group, orphaned `in_progress`
        resumes first, then fresh launches, each most-overdue first.

        The sort key is layered. `is_cleanup` leads so Dream lands at the end of
        the sweep — its retro pass then reaps the period tickets the *same*
        sweep just drove to `done`, instead of trailing them by a full sweep.
        Underneath that, resuming a dead sweep's orphan before any fresh run is
        the "resume any in_progress first" rule — a stuck recurring task gets
        picked back up before the sweep spends effort creating new work.
        (A resuming Dream orphan still sorts last: cleanup-after-the-rest wins
        over resume-first for the janitor itself, which is what we want.)
        """
        return _order_for_launch(t for t in self.tasks if t.launchable)

    @property
    def forced(self) -> list[DueTask]:
        """Every materialized template task in launch order — for `coga
        recurring --force`.

        Unlike `due`, this does **not** filter to launchable status: a `done`,
        `canceled`, or `paused` period task is still included. The force runner
        reactivates done/paused tasks but refuses canceled tasks; they
        must be deleted before a fresh run. The same Dream-last / resume-first
        ordering as `due` applies.
        """
        return _order_for_launch(t for t in self.tasks if t.ref is not None)


def _order_for_launch(tasks: Iterable[DueTask]) -> list[DueTask]:
    """Sort tasks into sweep launch order: Dream last, orphan-resumes before
    fresh launches, each group most-overdue first."""
    return sorted(
        tasks, key=lambda t: (t.is_cleanup, not t.resuming, t.last_fire)
    )


def scan_due(
    cfg: Config,
    now: datetime | None = None,
    *,
    allow_interactive: bool = True,
    force: bool = False,
) -> DueScan:
    """Scan every recurring template and get-or-create its current-period task.

    For each recurring task directory under `coga/recurring/` (skipping
    `_`-prefixed directories), this resolves the most recent scheduled firing,
    get-or-creates the task for that period, and records its status.
    Idempotent: a template whose current-period task already exists is a
    no-op. The caller (`coga recurring`) launches the `active` results
    sequentially.

    `force` (the `coga recurring --force` knob) bypasses the
    "period already serviced this period" skip, so every template's real
    `recurring/<name>` task is get-or-created and surfaced for launch even when
    it already ran — `coga launch` re-activates a finished one. It does not
    invent a separate scratch task; `--force` is a real run, not a sandbox.
    """
    now = now or datetime.now()
    root = recurring_dir(cfg)
    if not root.is_dir():
        return DueScan(tasks=[], errors=[])

    tasks: list[DueTask] = []
    errors: list[tuple[str, str]] = []
    # One log pass for every template in this scan, then kept current in-place
    # as creates record their periods. Bounding it to the templates on disk
    # lets the read stop at the log's tail instead of walking the whole file
    # once per sweep. Malformed records stay attached to the template they
    # belong to so one bad high-water mark cannot hide itself as "already
    # serviced" or prevent healthy templates from running.
    ledger = read_serviced_ledger(cfg, _template_refs(root))
    serviced = ledger.periods
    for path in sorted(root.iterdir()):
        if path.name.startswith("_"):
            # Underscore-prefixed entries are templates/creates, not live
            # recurring tasks.
            continue
        if not path.is_dir():
            if path.suffix == ".md":
                # A recurring task is now a ticket-format directory, not a
                # single file. Flag a leftover `<name>.md` loudly so the
                # migration to `<name>/ticket.md` is not silently skipped.
                msg = (
                    "legacy single-file recurring template — recurring tasks "
                    "are now directories (recurring/<name>/ticket.md)"
                )
                sys.stderr.write(f"[recurring] skipping {path.name}: {msg}\n")
                errors.append((path.name, msg))
            continue
        try:
            template = Template.load(path, now=now)
        except RecurringError as exc:
            sys.stderr.write(f"[recurring] skipping {path.name}: {exc}\n")
            errors.append((path.name, str(exc)))
            continue

        ledger_error = ledger.errors.get(_recurring_slug(template.name))
        if ledger_error is not None:
            sys.stderr.write(
                f"[recurring] skipping {path.name}: {ledger_error}\n"
            )
            errors.append((path.name, ledger_error))
            continue

        last_fire = _last_firing(template.schedule, now)
        period_key = _period_key(template.schedule, last_fire)
        target_slug = _recurring_slug(template.name)

        # One live task per template. A live (active/in_progress) recurring
        # task for this template — even from a *prior* period — is resumed by
        # `create_template` below rather than superseded by a fresh period;
        # so the "already ran" skip only applies when nothing is live.
        #
        # The repo-global log carries the serviced-period high-water mark. If
        # it has advanced through this period and the task directory is gone,
        # the period was handled — do not re-create what already ran. `--force`
        # overrides this and re-runs every template for real.
        if (
            not force
            and _live_task_for_template(cfg, template.name) is None
            and _task_with_slug(cfg, target_slug) is None
            and _period_already_serviced(cfg, template, period_key, serviced)
        ):
            tasks.append(
                DueTask(
                    template=template.name,
                    ref=None,
                    last_fire=last_fire,
                    recipe=template.recipe,
                    period_key=period_key,
                    created=False,
                    status="done",
                )
            )
            continue

        try:
            outcome = create_template(
                cfg,
                template,
                now,
                allow_agent=allow_interactive,
                # Forced scans defer every status/period mutation until the
                # sequential launch loop actually reaches that template.
                replace_done=not force,
                serviced=serviced,
            )
            ticket = read_ticket(outcome.ref)
        except RecurringError as exc:
            # Don't let one bad template block the rest. Stderr keeps an
            # interactive `coga recurring` honest; the command also posts a
            # Slack summary so the failure is never silent.
            sys.stderr.write(f"[recurring] skipping {path.name}: {exc}\n")
            errors.append((path.name, str(exc)))
            continue

        tasks.append(
            DueTask(
                template=template.name,
                ref=outcome.ref,
                last_fire=last_fire,
                recipe=template.recipe,
                period_key=period_key,
                created=outcome.created,
                status=ticket.status,
                replaced_done=outcome.replaced_done,
            )
        )
    return DueScan(tasks=tasks, errors=errors)


def create_named(
    cfg: Config, name: str, now: datetime | None = None
) -> CreateOutcome:
    """Create the named recurring task now, ignoring its schedule.

    `name` is the directory name under `coga/recurring/`. The task slug is
    the stable qualified `recurring/<name>`, so a manual `coga
    recurring launch <name>` and a bare `coga recurring` converge on one
    instantiated task directory.
    """
    now = now or datetime.now()
    path = recurring_dir(cfg) / name
    if not path.is_dir():
        raise RecurringError(f"no recurring task `recurring/{name}/`")
    template = Template.load(path, now=now)
    return create_template(cfg, template, now)


def create_template(
    cfg: Config,
    template: Template,
    now: datetime,
    *,
    allow_agent: bool = True,
    replace_done: bool = True,
    serviced: dict[str, str] | None = None,
) -> CreateOutcome:
    """Create one recurring template for `now`'s firing. Idempotent.

    `serviced` is the caller's prefetched valid-period map when it is walking
    every template; None reads and validates this template's ledger state.
    """
    last_fire = _last_firing(template.schedule, now)
    period_key = _period_key(template.schedule, last_fire)
    target_slug = _recurring_slug(template.name)
    if serviced is None:
        ledger = read_serviced_ledger(cfg, [target_slug])
        ledger_error = ledger.errors.get(target_slug)
        if ledger_error is not None:
            raise RecurringError(ledger_error)
        serviced = ledger.periods

    # One live task per template: an `active`/`in_progress` instance — current
    # period or a dead sweep's prior-period orphan — is *the* live run. Return
    # it (resume) instead of creating a competing new period. A stuck run
    # therefore defers the next period until it reaches a terminal/paused state; that
    # is deliberate — finish the in-flight run before piling another on.
    #
    # The TTY check is evaluated *after* the resume short-circuits: resuming an
    # existing task must not be blocked by it (only a fresh create launches a
    # would-be agent run that the check guards against).
    live = _live_task_for_template(cfg, template.name)
    if live is not None:
        return CreateOutcome(ref=live, created=False)

    existing = _task_with_slug(cfg, target_slug)
    if existing is not None:
        ticket = read_ticket(existing)
        if (
            replace_done
            and ticket.status == "done"
            and not _period_already_serviced(cfg, template, period_key, serviced)
        ):
            # A completed task is terminal. If Dream did not reap it, delete
            # that prior-period artifact through the canonical deletion path,
            # then create a genuinely fresh task from the current template.
            if not allow_agent and not template.recipe:
                raise RecurringError(
                    "an agent run requires a TTY (stdin and stdout must both be "
                    "terminals). Run `coga recurring --interactive` from a real "
                    "shell, or give the template a registered recipe for "
                    "unattended runs."
                )
            try:
                run_delete_task(existing)
            except DeleteTaskError as exc:
                raise RecurringError(
                    f"could not delete stale done task {target_slug}: {exc}"
                ) from exc
            outcome = _create_at_slug(
                cfg,
                template,
                target_slug=target_slug,
                title=_extract_title(template),
            )
            outcome.replaced_done = True
            append_log(
                cfg,
                target_slug,
                "system",
                f"deleted completed prior-period task before {period_key}",
            )
            _advance_serviced_period(
                cfg, template, period_key, outcome, now, serviced
            )
            return outcome
        return CreateOutcome(ref=existing, created=False)

    if not allow_agent and not template.recipe:
        raise RecurringError(
            "an agent run requires a TTY (stdin and stdout must both be "
            "terminals). Run `coga recurring --interactive` from a real shell, "
            "or give the template a registered `recipe:`."
        )
    outcome = _create_at_slug(
        cfg,
        template,
        target_slug=target_slug,
        title=_extract_title(template),
    )
    _advance_serviced_period(cfg, template, period_key, outcome, now, serviced)
    return outcome


@dataclass
class TemplateStatus:
    """Read-only view of one recurring template and its current-period task.

    Produced by `list_templates`. Unlike `scan_due` it creates
    nothing and never touches git, so it is safe behind a pure `coga
    recurring list`. `instance` is the live (`active`/`in_progress`) task for
    this template if one exists — current period or a resumable prior-period
    orphan — else the task at the stable slug if one is already on disk, else
    `None` (due, not yet created). `stale_done` marks an `instance` that is a
    prior-period `done` leftover Dream never reaped: the next sweep deletes it
    and creates this period's task fresh, so it is reported as due rather than
    as serviced. `serviced` marks a template with no task on disk whose
    serviced-period ledger already covers the current period — the run
    happened and Dream reaped the task dir, so it is *not* due (the sweep
    would skip it as "ran this period"). `error` is set for a template that
    failed to load (e.g. missing `schedule`), with the other fields left
    `None`.
    """

    name: str
    schedule: str | None
    last_fire: datetime | None
    next_fire: datetime | None
    period_key: str | None
    target_slug: str | None
    instance: TaskRef | None
    instance_status: str | None
    error: str | None = None
    stale_done: bool = False
    serviced: bool = False

    @property
    def due(self) -> bool:
        """No live/current instance covers the latest firing — a bare
        `coga recurring` would create and launch this template now.

        A stale prior-period `done` instance counts as due: the next sweep
        deletes it and creates this period's task fresh. A template with no
        task but a serviced high-water mark does not: the sweep skips it, so
        `list` must agree instead of over-reporting dueness."""
        return self.error is None and (
            self.stale_done or (self.instance is None and not self.serviced)
        )


def list_templates(cfg: Config, now: datetime | None = None) -> list[TemplateStatus]:
    """Read-only scan of every recurring template. Creates nothing.

    For each `recurring/<name>/` template (skipping `_`-prefixed entries) this
    resolves the schedule's last/next firing and the current period's task
    slug, then looks up whether a task for it already exists — without the
    get-or-create side effect `scan_due` carries. Powers `coga recurring
    list`, which must be inspectable like `coga status` (principle 6: a
    read-only view never mutates).
    """
    now = now or datetime.now()
    root = recurring_dir(cfg)
    out: list[TemplateStatus] = []
    if not root.is_dir():
        return out
    ledger = read_serviced_ledger(cfg, _template_refs(root))
    serviced = ledger.periods

    for path in sorted(root.iterdir()):
        if path.name.startswith("_") or not path.is_dir():
            continue
        try:
            template = Template.load(path, now=now)
        except RecurringError as exc:
            out.append(
                TemplateStatus(
                    name=path.name,
                    schedule=None,
                    last_fire=None,
                    next_fire=None,
                    period_key=None,
                    target_slug=None,
                    instance=None,
                    instance_status=None,
                    error=str(exc),
                )
            )
            continue

        ledger_error = ledger.errors.get(_recurring_slug(template.name))
        if ledger_error is not None:
            out.append(
                TemplateStatus(
                    name=template.name,
                    schedule=None,
                    last_fire=None,
                    next_fire=None,
                    period_key=None,
                    target_slug=None,
                    instance=None,
                    instance_status=None,
                    error=ledger_error,
                )
            )
            continue

        last_fire = _last_firing(template.schedule, now)
        next_fire = _next_firing(template.schedule, now)
        period_key = _period_key(template.schedule, last_fire)
        target_slug = _recurring_slug(template.name)
        instance = _live_task_for_template(cfg, template.name)
        instance_status: str | None = None
        stale_done = False
        period_handled = False
        if instance is None:
            candidate = _task_with_slug(cfg, target_slug)
            if candidate is None:
                # No task on disk at all — the period still counts as handled
                # when the log records this template servicing it (the run
                # happened and Dream reaped the task dir).
                period_handled = _period_already_serviced(
                    cfg, template, period_key, serviced
                )
            if candidate is not None:
                try:
                    instance_status = read_ticket(candidate).status
                except Exception:  # half-written / unreadable ticket
                    instance_status = "unknown"
                instance = candidate
                # A prior-period `done` task will be replaced by scan_due;
                # it is not evidence that the current period has run.
                # Surface it as stale instead of letting "done" read as
                # serviced.
                stale_done = instance_status == "done" and not (
                    _period_already_serviced(cfg, template, period_key, serviced)
                )
        if instance is not None and instance_status is None:
            try:
                instance_status = read_ticket(instance).status
            except Exception:  # half-written / unreadable ticket — report unknown
                instance_status = "unknown"
        out.append(
            TemplateStatus(
                name=template.name,
                schedule=template.schedule,
                last_fire=last_fire,
                next_fire=next_fire,
                period_key=period_key,
                target_slug=target_slug,
                instance=instance,
                instance_status=instance_status,
                error=None,
                stale_done=stale_done,
                serviced=period_handled,
            )
        )
    return out


# --- promote ------------------------------------------------------------------

# A task's per-run fields, which a template must not carry. `status`/`step` are
# run state the scanner and workflow own; `slug` identifies a *task*, while a
# template is identified by its directory name; `human`/`agent` are task-launch
# fields the creator re-derives for every period task. `skills:` is dropped too,
# but reported separately: it is deliberately never copied into a period task
# (see the `coga/recurring` context), so leaving it on the template would look
# load-bearing while doing nothing.
_TASK_ONLY_FIELDS = ("slug", "status", "step", "human", "agent")

# What a template passes through to each period task, in render order. Mirrors
# the fields `_create_at_slug` reads back off the template.
_TEMPLATE_PASSTHROUGH = (
    "title",
    "workflow",
    "owner",
    "assignee",
    "watchers",
    "contexts",
    "secrets",
)

# A live run's step/blocker state has nowhere to go in a template, and dropping
# it silently would abandon an in-flight handoff. Refuse instead and let the
# human land the run first.
_PROMOTE_REFUSED_STATUSES = ("in_progress", "blocked")

# One `coga/recurring/` directory component — the same slug-ish shape a task
# directory has. The template name becomes both the directory and the period
# task's `recurring/<name>` slug, so it must not need escaping.
_TEMPLATE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

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
    _validate_schedule(schedule, now)

    ticket = read_ticket(ref)
    if ticket.status in _PROMOTE_REFUSED_STATUSES:
        raise RecurringError(
            f"{ref.id_slug} is {ticket.status!r} — a template cannot hold a live "
            f"run's step or blocker. Land the run first (`coga mark done "
            f"{ref.id_slug}`, or `coga unblock`), then promote."
        )

    template_name = name or ref.slug
    if not _TEMPLATE_NAME_RE.match(template_name):
        raise RecurringError(
            f"invalid recurring template name {template_name!r} — it is a single "
            "directory name under `coga/recurring/` (letters, digits, `.`, `_`, "
            "`-`; no slashes, and `_` is reserved for parked templates). Pass "
            "`--name`."
        )
    dest = recurring_dir(cfg) / template_name
    if dest.exists():
        raise RecurringError(
            f"`coga/recurring/{template_name}/` already exists — refusing to "
            f"overwrite it. Pass `--name` to pick another template name, or "
            f"remove the existing template first."
        )

    frontmatter, dropped_skills = _template_frontmatter(ticket, schedule)
    _validate_promoted_workflow(cfg, frontmatter)
    above, blackboard = split_body(ticket.body, blackboard_required=False)

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
            _render_template_text(frontmatter, join_task_body(above, _PROMOTED_BLACKBOARD))
        )
        Template.load(dest, now=now)
    except (RecurringError, OSError):
        shutil.rmtree(dest, ignore_errors=True)
        raise

    if ref.file_form:
        ref.path.unlink()
    else:
        shutil.rmtree(ref.path)

    append_log(
        cfg,
        ref.id_slug,
        "human",
        f"promoted to recurring template `recurring/{template_name}` "
        f"(schedule {schedule})",
    )

    return PromoteOutcome(
        name=template_name,
        path=dest,
        source_slug=ref.id_slug,
        source_path=ref.path,
        dropped_skills=dropped_skills,
        dropped_blackboard=bool((blackboard or "").strip()),
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


def _create_at_slug(
    cfg: Config,
    template: Template,
    *,
    target_slug: str,
    title: str,
) -> CreateOutcome:
    """Create one recurring task at an explicit slug. Shared by period and
    debug creating — the only differences are the slug and ledger handling,
    which the callers own."""
    # A recurring task is a machine-authored job: it creates straight to
    # `active` and is meant to run, not be triaged. So when the template
    # doesn't name an assignee, default to the repo's configured default
    # agent — not the human owner, which `coga launch` cannot resolve to
    # an agent type. Without this a workflow-less template like Dream (no
    # step to ever rewrite `assignee:`) creates unlaunchable.
    assignee = template.frontmatter.get("assignee")
    if not assignee:
        default_agent = cfg.default_agent()
        assignee = default_agent.name if default_agent else None

    # Every period task gets `coga/period-task` auto-attached so the run
    # learns where persistent state lives (the parent's blackboard, not
    # its own). The convention applies to every period task by definition —
    # an opt-out flag would just be a footgun — so always-append, idempotent.
    contexts = list(template.frontmatter.get("contexts") or [])
    if "coga/period-task" not in contexts:
        contexts.append("coga/period-task")

    try:
        ref = create_task(
            cfg=cfg,
            title=title,
            # Recurring tasks create straight to `active`, and every task past
            # `draft` carries a workflow. A template that declares its own (e.g.
            # digest) keeps it; a workflow-less one (e.g. Dream, whose process is
            # its body's ordered phases) runs through the one-step `direct/body`
            # workflow so it is activatable, bumpable, and valid like any task.
            workflow_name=template.frontmatter.get("workflow") or "direct/body",
            contexts=contexts,
            owner=template.frontmatter.get("owner"),
            assignee=assignee,
            watchers=list(template.frontmatter.get("watchers") or []),
            status="active",
            slug_override=target_slug,
            secrets=template.frontmatter.get("secrets"),
            # Carry the template body verbatim so sections beyond `## Description`
            # reach the period task instead of being dropped at create time.
            body=template.body,
            # Recurring period tasks stay directory-form: they may carry a
            # `.state-snapshot.json` sibling (state-key tracking), and the sweep's
            # cross-branch sync addresses them as a directory.
            force_directory=True,
            created_by="system",
        )
    except (TaskValidationError, ValueError) as exc:
        # create_task fails with TaskValidationError post-write and plain
        # ValueError pre-write (unknown contexts, slug collision, ...); both
        # must become RecurringError so scan_due skips and reports this
        # template instead of aborting the whole sweep.
        raise RecurringError(str(exc)) from exc
    out_ref = _task_with_slug(cfg, ref["slug"])
    if out_ref is None:
        raise RecurringError(f"created task disappeared: {ref['slug']}")

    # If the template declares the blackboard keys it owns, snapshot their
    # current values into the period task. `coga mark done` later diffs this
    # baseline against the live parent blackboard to catch a run that finished
    # without advancing a declared key (a stale cursor → duplicate next firing).
    _write_state_snapshot(template, out_ref)

    return CreateOutcome(ref=out_ref, created=True)


# --- helpers ------------------------------------------------------------------


def _advance_serviced_period(
    cfg: Config,
    template: Template,
    period_key: str,
    outcome: CreateOutcome,
    now: datetime,
    serviced: dict[str, str] | None = None,
) -> None:
    """Record that this template serviced `period_key`.

    The log line *is* the ledger — there is no separate mark to keep in step
    with it. Re-recording an already-serviced period is skipped so the log does
    not accumulate a duplicate line per invocation.
    """
    if _period_already_serviced(cfg, template, period_key, serviced):
        return
    _record_run(cfg, template, outcome, period_key)
    if serviced is not None:
        serviced[_recurring_slug(template.name)] = period_key


def _write_state_snapshot(template: Template, ref: TaskRef) -> None:
    state_keys = template.frontmatter.get("state_keys") or []
    if state_keys:
        write_snapshot(
            ref.path, template.name, template.ticket_path, list(state_keys)
        )


def _record_run(
    cfg: Config, template: Template, outcome: CreateOutcome, period_key: str
) -> None:
    """Append this template's serviced-period line to the repo-global log.

    This line is the load-bearing dedup record, not just history: `coga
    recurring` reads it back through `serviced_periods` to decide whether a
    period has already run. It is tagged `recurring/<name>` and lands in the
    global log, which is never composed into a run prompt.
    """
    verb = "created" if outcome.created else "reused"
    append_log(
        cfg,
        _recurring_slug(template.name),
        "system",
        format_serviced_log(verb, outcome.ref.id_slug, period_key),
    )


def firing_stamp(when: datetime | None) -> str:
    """Compact firing label for template tables (`Mon 06-15 09:00`).

    Shared by `coga recurring list` and the `coga status` templates footer.
    """
    if when is None:
        return "-"
    return when.strftime("%a %m-%d %H:%M")


def _last_firing(cron: str, now: datetime) -> datetime:
    it = croniter(cron, now)
    return it.get_prev(datetime)


def _validate_schedule(schedule: Any, now: datetime) -> None:
    if not isinstance(schedule, str) or not schedule.strip():
        raise RecurringError("`schedule` must be a non-empty cron expression")
    field_count = len(schedule.split())
    if field_count != 5:
        raise RecurringError(
            "`schedule` is not a valid cron expression: expected exactly "
            f"5 fields, got {field_count}"
        )
    try:
        croniter(schedule, now).get_prev(datetime)
    except CroniterError as exc:
        raise RecurringError(
            f"`schedule` is not a valid cron expression: {exc}"
        ) from exc


def _next_firing(cron: str, now: datetime) -> datetime:
    it = croniter(cron, now)
    return it.get_next(datetime)


def _period_key(cron: str, fire_time: datetime) -> str:
    """Heuristic bucket for a cron schedule's firing."""
    parts = cron.split()
    if len(parts) != 5:
        return fire_time.strftime("%Y%m%dT%H%M")
    minute, hour, dom, month, dow = parts

    # Hourly (minute fixed, hour *) → YYYY-MM-DD-HH
    if hour == "*":
        return fire_time.strftime("%Y-%m-%d-%H")
    # Daily (dow and dom *) → YYYY-MM-DD
    if dow == "*" and dom == "*":
        return fire_time.strftime("%Y-%m-%d")
    # Weekly (dow specific, dom *) → YYYY-WW (ISO week)
    if dow != "*" and dom == "*":
        iso_year, iso_week, _ = fire_time.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    # Monthly (dom specific, dow *) → YYYY-MM
    if dom != "*" and dow == "*":
        return fire_time.strftime("%Y-%m")
    return fire_time.strftime("%Y%m%dT%H%M")


# --- the serviced-period ledger ----------------------------------------------
#
# "Has this period already run?" is answered from the repo-global append-only
# log, not from a mark in the template blackboard. The blackboard is shared
# free text, so any co-writer that rewrites a region of it can destroy a mark
# living there — the digest recipe did exactly that, and every `coga recurring`
# then re-fired an already-serviced period and reposted the digest. An appended
# line cannot be clobbered that way, it outlives the period task (Dream reaps
# those), and it is union-merged across checkouts.
#
# Because dedup now depends on this wording, the format has one writer and one
# reader, both here. Changing it breaks `test_recurring.py`'s format pin rather
# than silently disabling dedup.
SERVICED_LOG_VERBS = ("created", "reused")
_SERVICED_LOG_RE = re.compile(
    rf"^(?:{'|'.join(SERVICED_LOG_VERBS)})\s+\S+\s+for(?:\s+(?P<period>.*))?$"
)
_PERIOD_KEY_EXPECTATION = (
    "expected YYYY-MM, YYYY-Www, YYYY-MM-DD, YYYY-MM-DD-HH, or "
    "YYYYMMDDTHHMM with valid calendar values"
)


@dataclass
class ServicedPeriodLedger:
    """Valid high-water marks plus malformed records, keyed by template ref."""

    periods: dict[str, str]
    errors: dict[str, str]


def _period_key_position(period_key: str) -> datetime:
    """Normalize every period-key shape emitted by `_period_key` for ordering."""
    try:
        match = re.fullmatch(r"(\d{4})-(\d{2})", period_key)
        if match is not None:
            return datetime(int(match.group(1)), int(match.group(2)), 1)

        match = re.fullmatch(r"(\d{4})-W(\d{2})", period_key)
        if match is not None:
            return datetime.fromisocalendar(
                int(match.group(1)), int(match.group(2)), 1
            )

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", period_key):
            return datetime.strptime(period_key, "%Y-%m-%d")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{2}", period_key):
            return datetime.strptime(period_key, "%Y-%m-%d-%H")
        if re.fullmatch(r"\d{8}T\d{4}", period_key):
            return datetime.strptime(period_key, "%Y%m%dT%H%M")
    except ValueError as exc:
        raise ValueError(
            f"invalid period key {period_key!r}; {_PERIOD_KEY_EXPECTATION}"
        ) from exc
    raise ValueError(
        f"invalid period key {period_key!r}; {_PERIOD_KEY_EXPECTATION}"
    )


def period_key_at_least(period_key: str, other: str) -> bool:
    """Compare two serviced-period keys by calendar position, not spelling."""
    return _period_key_position(period_key) >= _period_key_position(other)


class _LedgerAccumulator:
    """Fold log entries into high-water marks, in either file direction.

    Shared by the whole-log forward read and the bounded tail read so both
    agree on what counts as a ledger line, what counts as malformed, and which
    of two records for one template wins.
    """

    def __init__(self) -> None:
        self.periods: dict[str, str] = {}
        self.errors: dict[str, str] = {}
        self._positions: dict[str, tuple[datetime, str]] = {}

    def add(self, ref: str, message: str) -> None:
        if not ref.startswith("recurring/"):
            return
        match = _SERVICED_LOG_RE.match(message)
        if match is None:
            return
        period = (match.group("period") or "").strip()
        try:
            position = _period_key_position(period)
        except ValueError:
            error = (
                f"invalid serviced period {period!r} for {ref} in coga/log.md; "
                f"{_PERIOD_KEY_EXPECTATION}"
            )
            current_error = self.errors.get(ref)
            if current_error is None or error < current_error:
                self.errors[ref] = error
            return
        candidate = (position, period)
        current = self._positions.get(ref)
        if current is None or candidate > current:
            self.periods[ref] = period
            self._positions[ref] = candidate

    def ledger(self) -> ServicedPeriodLedger:
        return ServicedPeriodLedger(periods=self.periods, errors=self.errors)


def parse_serviced_period_entries(
    entries: Iterable[tuple[str, str]],
) -> ServicedPeriodLedger:
    """Parse log `(ref, message)` entries into typed high-water marks.

    A malformed ledger-looking line is retained as a per-template error rather
    than ignored or compared as text. Valid records still accumulate for other
    templates so scan and status can isolate the bad state to its owner.
    """
    accumulator = _LedgerAccumulator()
    for ref, message in entries:
        accumulator.add(ref, message)
    return accumulator.ledger()


def format_serviced_log(verb: str, task_ref: str, period_key: str) -> str:
    """The one spelling of a serviced-period log message."""
    if verb not in SERVICED_LOG_VERBS:
        raise ValueError(f"unknown serviced-period verb {verb!r}")
    _period_key_position(period_key)
    return f"{verb} {task_ref} for {period_key}"


# How far past "every template resolved" the tail read keeps going before it
# stops. `log.md` is `merge=union`, so two checkouts appending in the same
# period leave their blocks concatenated in whichever order the merge picked —
# a template's newest record can sit *above* an older one. Reverse order is
# therefore a good recency heuristic, not a guarantee, and a bare "stop at the
# first hit" would re-introduce the under-reporting this ticket exists to kill.
# A merge block is a sweep's worth of lines; this window covers many of them
# while still reading a fixed tail rather than the unbounded file.
_LEDGER_TAIL_SLACK_LINES = 500


def read_serviced_ledger(
    cfg: Config, refs: Iterable[str] | None = None
) -> ServicedPeriodLedger:
    """Read serviced-period state while preserving per-template errors.

    `refs` is the finite set of `recurring/<name>` refs the caller actually
    needs — every template in a scan, or the single one a create is deciding.
    Given it, the log is read **backwards** and abandoned once each ref has
    resolved, so the answer costs a tail read instead of a full pass over the
    one file Coga lets grow without bound. `None` keeps the whole-log forward
    read for callers that must reconstruct every template's state.

    Two consequences of the bounded read, both deliberate. A ref with no record
    at all never resolves, so a template's first firing still walks the whole
    log — the same cost as before, once. And a malformed record older than a
    valid one for the same template is no longer reached, so a template heals
    itself by servicing a period instead of staying wedged behind ancient bad
    state; a malformed record *newer* than the valid one is still surfaced,
    because the reverse scan meets it first and records its error before the
    older valid record resolves the ref.
    """
    if refs is None:
        return parse_serviced_period_entries(iter_log_messages(cfg))
    wanted = set(refs)
    if not wanted:
        return ServicedPeriodLedger(periods={}, errors={})
    accumulator = _LedgerAccumulator()
    pending = set(wanted)
    slack = _LEDGER_TAIL_SLACK_LINES
    for ref, message in iter_log_messages_reverse(cfg):
        # Only the requested templates accumulate — a ref the caller did not
        # ask about must not answer for one it did, and its malformed records
        # are not this caller's error to raise.
        if ref in wanted:
            accumulator.add(ref, message)
            if ref in accumulator.periods:
                # Resolved means "has a valid high-water mark". A malformed
                # record alone leaves the ref pending, so an older good one is
                # still found.
                pending.discard(ref)
        # Slack counts every line scanned, not just ledger ones: the window is
        # sized against a merge block's worth of log, whatever it contains.
        if not pending:
            slack -= 1
            if slack <= 0:
                break
    return accumulator.ledger()


def serviced_periods(
    cfg: Config, refs: Iterable[str] | None = None
) -> dict[str, str]:
    """Map each `recurring/<name>` ref to the newest period it has serviced.

    One pass over the log for every requested template at once; scanning per
    template would re-read the one file Coga lets grow without bound. Pass
    `refs` to bound that pass to the log's tail — see `read_serviced_ledger`.

    The latest calendar period is kept rather than the last line seen:
    `log.md` is `merge=union`, so concurrent appends from two checkouts can
    leave the file unsorted. Malformed ledger state raises instead of returning
    a partial map; scan/status use `read_serviced_ledger` to attach each error
    to its template while continuing past it.
    """
    ledger = read_serviced_ledger(cfg, refs)
    if ledger.errors:
        first_ref = sorted(ledger.errors)[0]
        raise RecurringError(ledger.errors[first_ref])
    return ledger.periods


def _recurring_slug(template_name: str) -> str:
    return f"recurring/{template_name}"


def _template_refs(root: Path) -> list[str]:
    """Every live template's log ref, from directory names alone.

    Cheap enough to run before `Template.load`, which is what lets a scan bound
    its ledger read to the templates it is about to walk.
    """
    return [
        _recurring_slug(path.name)
        for path in sorted(root.iterdir())
        if path.is_dir() and not path.name.startswith("_")
    ]


def _task_with_slug(cfg: Config, target_slug: str) -> TaskRef | None:
    for ref in list_tasks(cfg):
        if ref.id_slug == target_slug:
            return ref
    return None


def _live_task_for_template(cfg: Config, template_name: str) -> TaskRef | None:
    """The template's single live (`active`/`in_progress`) recurring task.

    Identity is the qualified slug `recurring/<name>`. That is what lets
    a stale leftover be found and resumed.

    Prefers an `in_progress` orphan (a dead sweep's frozen run, resumed from
    its step) over a never-launched `active`.
    """
    live: TaskRef | None = None
    for ref in list_tasks(cfg):
        if ref.directory != "recurring" or ref.slug != template_name:
            continue
        status = read_ticket(ref).status
        if status == "in_progress":
            return ref
        if status == "active" and live is None:
            live = ref
    return live


def _period_already_serviced(
    cfg: Config, template: Template, period_key: str, serviced: dict[str, str] | None
) -> bool:
    """Has this template already serviced `period_key`?

    `serviced` is a prefetched `serviced_periods` map when the caller is
    walking every template; None makes this read the log itself.
    """
    if serviced is None:
        serviced = serviced_periods(cfg, [_recurring_slug(template.name)])
    last = serviced.get(_recurring_slug(template.name))
    if last is None:
        return False
    try:
        return period_key_at_least(last, period_key)
    except ValueError as exc:
        raise RecurringError(
            f"invalid serviced-period comparison for "
            f"{_recurring_slug(template.name)}: {exc}"
        ) from exc


def _extract_title(template: Template) -> str:
    if "title" in template.frontmatter:
        return template.frontmatter["title"]
    # Default to a humanized template name
    return template.name.replace("-", " ").replace("_", " ").strip().capitalize()


__all__ = [
    "Template",
    "CreateOutcome",
    "DueTask",
    "DueScan",
    "scan_due",
    "create_named",
    "create_template",
    "PromoteOutcome",
    "promote_task",
    "serviced_periods",
    "read_serviced_ledger",
    "parse_serviced_period_entries",
    "period_key_at_least",
    "ServicedPeriodLedger",
    "format_serviced_log",
    "SERVICED_LOG_VERBS",
    "RecurringError",
]
