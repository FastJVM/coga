"""Recurring task templates under `relay-os/recurring/<name>/`."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from croniter import CroniterError, croniter

from relay.create import create_task
from relay.config import Config
from relay.paths import recurring_dir
from relay.period_state import write_snapshot
from relay.tasks import TaskRef, list_tasks, read_ticket


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_CRON_VALIDATION_BASE = datetime(2000, 1, 1)


class RecurringError(Exception):
    pass


@dataclass
class Template:
    """A recurring task — a ticket-format directory under `recurring/<name>/`.

    `ticket.md` carries the schedule and run body; `blackboard.md` persists
    across runs for forward state, including the `last_serviced_period`
    high-water mark. `log.md` is append-only human history.
    """

    path: Path  # the recurring task directory
    name: str
    frontmatter: dict[str, Any]
    body: str

    @classmethod
    def load(cls, path: Path) -> "Template":
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
        _validate_schedule(fm["schedule"])
        if "state_keys" in fm:
            state_keys = fm["state_keys"]
            if not isinstance(state_keys, list) or not all(
                isinstance(key, str) and key.strip() for key in state_keys
            ):
                raise RecurringError(
                    "`state_keys` must be a list of non-empty strings"
                )
        return cls(path=path, name=path.name, frontmatter=fm, body=match.group(2))

    @property
    def schedule(self) -> str:
        return self.frontmatter["schedule"]

    @property
    def blackboard_path(self) -> Path:
        """Persistent working state, composed into each run's prompt (layer 7).

        Kept small on purpose: the blackboard carries only forward state the
        next run actually reads, while append-only history lives in `log_path`
        (never composed).
        """
        return self.path / "blackboard.md"

    @property
    def log_path(self) -> Path:
        """Append-only period history (see `_record_run`).

        Never a prompt-composition layer, so it can grow without bloating any
        run's context.
        """
        return self.path / "log.md"


@dataclass
class CreateOutcome:
    """Result of creating one recurring template for a given firing.

    `created` is False when a task already exists for the template — the
    create is idempotent, so two `relay recurring` runs converge on the
    stable `tasks/recurring/<name>/` directory.
    """

    ref: TaskRef
    created: bool


# The cleanup template runs last in a bare sweep so its retro/cleanup pass acts
# on the period tickets the *same* sweep just produced. Dream is Relay's
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

    `relay recurring` materializes this for every template, then launches the
    `launchable` ones (`active`, plus an `in_progress` orphan it resumes —
    see `launchable`). `last_fire` is the scheduled firing this task covers —
    used to report "ready" vs "overdue" and to order launches.

    `ref` is `None` when the period was already serviced earlier and the task
    directory has since been removed. The template's `blackboard.md` carries
    the `last_serviced_period` high-water mark used for that decision.
    """

    template: str
    ref: TaskRef | None
    last_fire: datetime
    created: bool
    status: str

    @property
    def launchable(self) -> bool:
        # `active` → created-and-not-yet-run (created this scan or carried
        # over from one that never launched it).
        # `in_progress` → a *past* sweep died mid-run and left a recurring task
        # frozen. `relay recurring` is a foreground command — no daemon, no
        # concurrent sweep in normal use — so an `in_progress` recurring task at
        # scan time can only be a dead sweep's orphan, never a live session.
        # Relaunch it: `relay launch` resumes an `in_progress` ticket from its
        # current `step:` (it only flips status on an `active` launch). Worst
        # case a false relaunch redoes a step the human then catches — cheaper
        # than a liveness mechanism. The orphan need not be the *current*
        # period's — identity is the `recurring` directory plus the template
        # leaf slug, so a stale leftover is found and resumed too (and defers
        # the next period until it reaches done/paused: one live task per
        # template).
        # `done` → finished work, never re-run. `paused` → a human parked it.
        return self.status in {"active", "in_progress"}

    @property
    def resuming(self) -> bool:
        """A launchable orphan being resumed, not a fresh launch.

        True only for an `in_progress` period task — a dead sweep's orphan
        that `relay launch` will re-compose from its current `step:`. Drives
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
        return sorted(
            (t for t in self.tasks if t.launchable),
            key=lambda t: (t.is_cleanup, not t.resuming, t.last_fire),
        )


def scan_due(
    cfg: Config, now: datetime | None = None, *, allow_interactive: bool = True
) -> DueScan:
    """Scan every recurring template and get-or-create its current-period task.

    For each recurring task directory under `relay-os/recurring/` (skipping
    `_`-prefixed directories), this resolves the most recent scheduled firing,
    get-or-creates the task for that period, and records its status.
    Idempotent: a template whose current-period task already exists is a
    no-op. The caller (`relay recurring`) launches the `active` results
    sequentially.
    """
    now = now or datetime.now()
    root = recurring_dir(cfg)
    if not root.is_dir():
        return DueScan(tasks=[], errors=[])

    tasks: list[DueTask] = []
    errors: list[tuple[str, str]] = []
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
            template = Template.load(path)
        except RecurringError as exc:
            sys.stderr.write(f"[recurring] skipping {path.name}: {exc}\n")
            errors.append((path.name, str(exc)))
            continue

        last_fire = _last_firing(template.schedule, now)
        period_key = _period_key(template.schedule, last_fire)
        target_slug = _recurring_slug(template.name)

        # One live task per template. A live (active/in_progress) recurring
        # task for this template — even from a *prior* period — is resumed by
        # `create_template` below rather than superseded by a fresh period;
        # so the "already ran" skip only applies when nothing is live.
        #
        # The template's persistent blackboard carries the serviced-period
        # high-water mark. If it has already advanced through this period and
        # the task directory is gone, the period was handled — do not
        # re-create what already ran.
        if (
            _live_task_for_template(cfg, template.name) is None
            and _task_with_slug(cfg, target_slug) is None
            and _period_already_serviced(template, period_key)
        ):
            tasks.append(
                DueTask(
                    template=template.name,
                    ref=None,
                    last_fire=last_fire,
                    created=False,
                    status="done",
                )
            )
            continue

        try:
            outcome = create_template(
                cfg, template, now, allow_interactive=allow_interactive
            )
        except RecurringError as exc:
            # Don't let one bad template block the rest. Stderr keeps an
            # interactive `relay recurring` honest; the command also posts a
            # Slack summary so the failure is never silent.
            sys.stderr.write(f"[recurring] skipping {path.name}: {exc}\n")
            errors.append((path.name, str(exc)))
            continue

        ticket = read_ticket(outcome.ref)
        tasks.append(
            DueTask(
                template=template.name,
                ref=outcome.ref,
                last_fire=last_fire,
                created=outcome.created,
                status=ticket.status,
            )
        )
    return DueScan(tasks=tasks, errors=errors)


def create_named(
    cfg: Config, name: str, now: datetime | None = None
) -> CreateOutcome:
    """Create the named recurring task now, ignoring its schedule.

    `name` is the directory name under `relay-os/recurring/`. The task slug is
    the stable qualified `recurring/<name>`, so a manual `relay
    recurring launch <name>` and a bare `relay recurring` converge on one
    instantiated task directory.
    """
    now = now or datetime.now()
    path = recurring_dir(cfg) / name
    if not path.is_dir():
        raise RecurringError(f"no recurring task `recurring/{name}/`")
    template = Template.load(path)
    return create_template(cfg, template, now)


def create_template(
    cfg: Config,
    template: Template,
    now: datetime,
    *,
    allow_interactive: bool = True,
) -> CreateOutcome:
    """Create one recurring template for `now`'s firing. Idempotent."""
    effective_mode = _effective_mode(template, allow_interactive=allow_interactive)

    last_fire = _last_firing(template.schedule, now)
    period_key = _period_key(template.schedule, last_fire)
    target_slug = _recurring_slug(template.name)

    # One live task per template: an `active`/`in_progress` instance — current
    # period or a dead sweep's prior-period orphan — is *the* live run. Return
    # it (resume) instead of creating a competing new period. A stuck run
    # therefore defers the next period until it reaches `done`/`paused`; that
    # is deliberate — finish the in-flight run before piling another on.
    live = _live_task_for_template(cfg, template.name)
    if live is not None:
        return CreateOutcome(ref=live, created=False)

    existing = _task_with_slug(cfg, target_slug)
    if existing is not None:
        return CreateOutcome(ref=existing, created=False)

    outcome = _create_at_slug(
        cfg,
        template,
        target_slug=target_slug,
        effective_mode=effective_mode,
        title=_extract_title(template),
    )
    _advance_serviced_period(template, period_key, outcome, now)
    return outcome


# A `relay recurring --all` throwaway run is slugged `<name>-dbg-<timestamp>`
# (see `create_debug_run`), and any child task it spawns embeds that slug, so
# both carry the `-dbg-<digit>` infix. Requiring a digit after the marker spares
# ordinary hyphenated ticket names (e.g. `fix-dbg-output`) from matching.
_DEBUG_SLUG_RE = re.compile(r"-dbg-\d")


def is_debug_slug(slug: str) -> bool:
    """True if `slug` belongs to a `relay recurring --all` debug run (or its
    descendants). Debug runs are disposable scratch and must never reach Slack
    or the digest spool — only the task's own `log.md` records their events."""
    return bool(_DEBUG_SLUG_RE.search(slug))


def create_debug_run(
    cfg: Config,
    template: Template,
    now: datetime,
    *,
    allow_interactive: bool = True,
) -> CreateOutcome:
    """Create a throwaway debug run of one template — `relay recurring --all`.

    Unlike `create_template`, this ignores both the stable recurring task
    slug and the serviced-period high-water mark: it always creates a *fresh*
    task under a unique `<template>-dbg-<timestamp>` slug, so it never collides
    with — or mutates — the real run (which may already be `done`/
    `in_progress`/`paused`). The run is meant to be observed once and then
    deleted; it does not advance `last_serviced_period`.
    """
    effective_mode = _effective_mode(template, allow_interactive=allow_interactive)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    target_slug = f"{template.name}-dbg-{stamp}"
    return _create_at_slug(
        cfg,
        template,
        target_slug=target_slug,
        effective_mode=effective_mode,
        title=f"[debug] {_extract_title(template)}",
    )


def scan_debug(
    cfg: Config, now: datetime | None = None, *, allow_interactive: bool = True
) -> DueScan:
    """Create a fresh debug run for every recurring template.

    The debug counterpart of `scan_due`: it walks the same templates (skipping
    `_`-prefixed directories and `mode: auto`, with the same loud skips) but
    creates an isolated throwaway run per template instead of get-or-creating
    the current period's task. `relay recurring --all` launches the results.
    Real period state is left untouched.
    """
    now = now or datetime.now()
    root = recurring_dir(cfg)
    if not root.is_dir():
        return DueScan(tasks=[], errors=[])

    tasks: list[DueTask] = []
    errors: list[tuple[str, str]] = []
    for path in sorted(root.iterdir()):
        if path.name.startswith("_"):
            continue
        if not path.is_dir():
            continue
        try:
            template = Template.load(path)
            outcome = create_debug_run(
                cfg, template, now, allow_interactive=allow_interactive
            )
        except RecurringError as exc:
            sys.stderr.write(f"[recurring] skipping {path.name}: {exc}\n")
            errors.append((path.name, str(exc)))
            continue
        ticket = read_ticket(outcome.ref)
        tasks.append(
            DueTask(
                template=template.name,
                ref=outcome.ref,
                last_fire=now,
                created=True,
                status=ticket.status,
            )
        )
    return DueScan(tasks=tasks, errors=errors)


@dataclass
class TemplateStatus:
    """Read-only view of one recurring template and its current-period task.

    Produced by `list_templates`. Unlike `scan_due`/`scan_debug` it creates
    nothing and never touches git, so it is safe behind a pure `relay
    recurring list`. `instance` is the live (`active`/`in_progress`) task for
    this template if one exists — current period or a resumable prior-period
    orphan — else this period's task if it is already on disk, else `None`
    (due, not yet created). `error` is set for a template that failed to
    load (e.g. missing `schedule`), with the other fields left `None`.
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

    @property
    def due(self) -> bool:
        """No live/current instance covers the latest firing — a bare
        `relay recurring` would create and launch this template now."""
        return self.error is None and self.instance is None


def list_templates(cfg: Config, now: datetime | None = None) -> list[TemplateStatus]:
    """Read-only scan of every recurring template. Creates nothing.

    For each `recurring/<name>/` template (skipping `_`-prefixed entries) this
    resolves the schedule's last/next firing and the current period's task
    slug, then looks up whether a task for it already exists — without the
    get-or-create side effect `scan_due` carries. Powers `relay recurring
    list`, which must be inspectable like `relay status` (principle 6: a
    read-only view never mutates).
    """
    now = now or datetime.now()
    root = recurring_dir(cfg)
    out: list[TemplateStatus] = []
    if not root.is_dir():
        return out

    for path in sorted(root.iterdir()):
        if path.name.startswith("_") or not path.is_dir():
            continue
        try:
            template = Template.load(path)
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

        last_fire = _last_firing(template.schedule, now)
        next_fire = _next_firing(template.schedule, now)
        period_key = _period_key(template.schedule, last_fire)
        target_slug = _recurring_slug(template.name)
        instance = _live_task_for_template(cfg, template.name) or _task_with_slug(
            cfg, target_slug
        )
        instance_status: str | None = None
        if instance is not None:
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
            )
        )
    return out


def _effective_mode(template: Template, *, allow_interactive: bool = True) -> str:
    """Resolve a template's launch mode, enforcing the temporary auto ban.

    Temporary policy: refuse `mode: auto` recurring tasks. `claude -p` and
    `codex exec` buffer until completion, so scheduled runs would sit silently
    — worse than skipping. Lift when streaming lands. Templates can opt back in
    by setting `mode: script` (or `mode: interactive` if they can run from a
    TTY).
    """
    effective_mode = template.frontmatter.get("mode", "auto")
    if effective_mode == "auto":
        raise RecurringError(
            "mode=auto is temporarily disabled (auto runs produce no live "
            "console output). Set `mode: script` or `mode: interactive` "
            "to re-enable."
        )
    if effective_mode == "interactive" and not allow_interactive:
        raise RecurringError(
            "mode=interactive requires a TTY (stdin and stdout must both be "
            "terminals). Run `relay recurring --interactive` from a real shell, "
            "or change the template to mode: script."
        )
    return effective_mode


def _create_at_slug(
    cfg: Config,
    template: Template,
    *,
    target_slug: str,
    effective_mode: str,
    title: str,
) -> CreateOutcome:
    """Create one recurring task at an explicit slug. Shared by period and
    debug creating — the only differences are the slug and ledger handling,
    which the callers own."""
    # A recurring task is a machine-authored job: it creates straight to
    # `active` and is meant to run, not be triaged. So when the template
    # doesn't name an assignee, default to the repo's configured default
    # agent — not the human owner, which `relay launch` cannot resolve to
    # an agent type. Without this a workflow-less template like Dream (no
    # step to ever rewrite `assignee:`) creates unlaunchable.
    assignee = template.frontmatter.get("assignee")
    if not assignee:
        default_agent = cfg.default_agent()
        assignee = default_agent.name if default_agent else None

    # Every period task gets `relay/period-task` auto-attached so the run
    # learns where persistent state lives (the parent's blackboard, not
    # its own). The convention applies to every period task by definition —
    # an opt-out flag would just be a footgun — so always-append, idempotent.
    contexts = list(template.frontmatter.get("contexts") or [])
    if "relay/period-task" not in contexts:
        contexts.append("relay/period-task")

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
        mode=effective_mode,
        owner=template.frontmatter.get("owner"),
        assignee=assignee,
        watchers=list(template.frontmatter.get("watchers") or []),
        status="active",
        slug_override=target_slug,
        # Carry the template body verbatim so sections beyond `## Description`
        # (notably `## Script config`, which sets a script step's mode/sync)
        # reach the period task instead of being dropped at create time.
        body=template.body,
        created_by="system",
    )
    out_ref = _task_with_slug(cfg, ref["slug"])
    if out_ref is None:
        raise RecurringError(f"created task disappeared: {ref['slug']}")

    # If the template declares the blackboard keys it owns, snapshot their
    # current values into the period task. `relay mark done` later diffs this
    # baseline against the live parent blackboard to catch a run that finished
    # without advancing a declared key (a stale cursor → duplicate next firing).
    state_keys = template.frontmatter.get("state_keys") or []
    if state_keys:
        write_snapshot(
            out_ref.path, template.name, template.blackboard_path, list(state_keys)
        )

    return CreateOutcome(ref=out_ref, created=True)


# --- helpers ------------------------------------------------------------------


def _advance_serviced_period(
    template: Template, period_key: str, outcome: CreateOutcome, now: datetime
) -> None:
    current = read_last_serviced_period(template.blackboard_path)
    if current is not None and current >= period_key:
        return
    write_last_serviced_period(template.blackboard_path, period_key)
    _record_run(template, outcome, period_key, now)


def _record_run(
    template: Template, outcome: CreateOutcome, period_key: str, now: datetime
) -> None:
    """Append a period-history line to the template's persistent `log.md`.

    The load-bearing high-water mark lives in the template blackboard. The log
    remains append-only human history and is deliberately never composed into a
    run prompt.
    """
    log = template.log_path
    existing = log.read_text() if log.is_file() else ""
    # Make sure the appended line lands on its own line, even when the
    # existing log does not end with a newline.
    sep = "" if not existing or existing.endswith("\n") else "\n"
    stamp = now.strftime("%Y-%m-%d %H:%M")
    log.write_text(
        f"{existing}{sep}{stamp} [system] created "
        f"{outcome.ref.id_slug} for {period_key}\n"
    )


def _last_firing(cron: str, now: datetime) -> datetime:
    it = croniter(cron, now)
    return it.get_prev(datetime)


def _validate_schedule(schedule: Any) -> None:
    if not isinstance(schedule, str) or not schedule.strip():
        raise RecurringError("`schedule` must be a non-empty cron expression")
    try:
        croniter(schedule, _CRON_VALIDATION_BASE).get_prev(datetime)
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


_LAST_SERVICED_PERIOD_RE = re.compile(
    r"^last_serviced_period:\s*(?P<period>\S+)\s*$", re.MULTILINE
)


def _recurring_slug(template_name: str) -> str:
    return f"recurring/{template_name}"


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


def _period_already_serviced(template: Template, period_key: str) -> bool:
    last_serviced = read_last_serviced_period(template.blackboard_path)
    return last_serviced is not None and last_serviced >= period_key


def read_last_serviced_period(blackboard_path: Path) -> str | None:
    if not blackboard_path.is_file():
        return None
    return _read_last_serviced_period_text(blackboard_path.read_text())


def write_last_serviced_period(blackboard_path: Path, period_key: str) -> None:
    existing = blackboard_path.read_text() if blackboard_path.is_file() else ""
    blackboard_path.parent.mkdir(parents=True, exist_ok=True)
    blackboard_path.write_text(set_last_serviced_period_text(existing, period_key))


def merge_last_serviced_period_text(base_text: str, incoming_text: str) -> str:
    """Merge only the high-water line from `incoming_text` into `base_text`."""
    base_period = _read_last_serviced_period_text(base_text)
    incoming_period = _read_last_serviced_period_text(incoming_text)
    periods = [p for p in (base_period, incoming_period) if p is not None]
    if not periods:
        return base_text or incoming_text
    return set_last_serviced_period_text(base_text or incoming_text, max(periods))


def set_last_serviced_period_text(text: str, period_key: str) -> str:
    line = f"last_serviced_period: {period_key}"
    lines = text.splitlines()
    out: list[str] = []
    replaced = False
    for existing in lines:
        if _LAST_SERVICED_PERIOD_RE.match(existing):
            if not replaced:
                out.append(line)
                replaced = True
            continue
        out.append(existing)
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


def _read_last_serviced_period_text(text: str) -> str | None:
    match = _LAST_SERVICED_PERIOD_RE.search(text)
    if match is None:
        return None
    return match.group("period")


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
    "scan_debug",
    "create_named",
    "create_template",
    "create_debug_run",
    "is_debug_slug",
    "read_last_serviced_period",
    "write_last_serviced_period",
    "merge_last_serviced_period_text",
    "set_last_serviced_period_text",
    "RecurringError",
]
