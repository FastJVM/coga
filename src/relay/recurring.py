"""Recurring task templates under `relay-os/recurring/*.md`."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from croniter import croniter

from relay.scaffold import scaffold_task
from relay.config import Config
from relay.paths import recurring_dir
from relay.tasks import TaskRef, list_tasks, read_ticket


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


class RecurringError(Exception):
    pass


@dataclass
class Template:
    """A recurring task — a ticket-format directory under `recurring/<name>/`.

    `ticket.md` carries the schedule and run body; `blackboard.md` persists
    across runs for forward state. `log.md` is the period ledger: `_record_run`
    appends a scaffolding line every time a new period task is created.
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
        return cls(path=path, name=path.name, frontmatter=fm, body=match.group(2))

    @property
    def schedule(self) -> str:
        return self.frontmatter["schedule"]

    @property
    def blackboard_path(self) -> Path:
        """Persistent working state, composed into each run's prompt (layer 7).

        Kept small on purpose: the period ledger and run records live in
        `log_path` (never composed), so the blackboard carries only the
        forward state the next run actually reads.
        """
        return self.path / "blackboard.md"

    @property
    def log_path(self) -> Path:
        """Append-only period ledger + run history (see `_record_run`).

        Never a prompt-composition layer, so it can grow without bloating any
        run's context. `scan_due` reads it to decide whether a period has
        already been handled even after the period task dir is gone.
        """
        return self.path / "log.md"


@dataclass
class ScaffoldOutcome:
    """Result of scaffolding one recurring template for a given firing.

    `created` is False when a task already exists for the period — the
    scaffold is idempotent, so two `relay recurring` runs in the same period
    converge on one task directory.
    """

    ref: TaskRef
    created: bool


@dataclass
class DueTask:
    """One recurring template's current-period task, after get-or-create.

    `relay recurring` materializes this for every template, then launches the
    `launchable` ones (`active`, plus an `in_progress` orphan it resumes —
    see `launchable`). `last_fire` is the scheduled firing this task covers —
    used to report "ready" vs "overdue" and to order launches.

    `ref` is `None` when the period was already scaffolded earlier this cycle
    and the task directory has since been removed (a later Dream run deletes
    done recurring period tickets via its retro pass; a human `relay delete` is
    the other case). The template's `log.md` is the period ledger — see
    `_period_already_scaffolded`.
    """

    template: str
    ref: TaskRef | None
    last_fire: datetime
    created: bool
    status: str

    @property
    def launchable(self) -> bool:
        # `active` → scaffolded-and-not-yet-run (created this scan or carried
        # over from one that never launched it).
        # `in_progress` → a *past* sweep died mid-run and left a recurring task
        # frozen. `relay recurring` is a foreground command — no daemon, no
        # concurrent sweep in normal use — so an `in_progress` recurring task at
        # scan time can only be a dead sweep's orphan, never a live session.
        # Relaunch it: `relay launch` resumes an `in_progress` ticket from its
        # current `step:` (it only flips status on an `active` launch). Worst
        # case a false relaunch redoes a step the human then catches — cheaper
        # than a liveness mechanism. The orphan need not be the *current*
        # period's — identity is the `recurring-<name>-` slug prefix, so a
        # stuck prior-period run is found and resumed too (and defers the next
        # period until it reaches done/paused: one live task per template).
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


@dataclass
class DueScan:
    """Outcome of scanning every recurring template for the current period."""

    tasks: list[DueTask]
    errors: list[tuple[str, str]]  # (template_filename, error_message)

    @property
    def due(self) -> list[DueTask]:
        """Launchable tasks: orphaned `in_progress` resumes first, then fresh
        launches, each group most-overdue first.

        Resuming a dead sweep's orphan before starting any fresh run is the
        "resume any in_progress first" rule — a stuck recurring task gets
        picked back up before the sweep spends effort scaffolding new work.
        """
        return sorted(
            (t for t in self.tasks if t.launchable),
            key=lambda t: (not t.resuming, t.last_fire),
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
            # Underscore-prefixed entries are templates/scaffolds, not live
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
        target_slug = _recurring_slug(template.name, period_key)

        # One live task per template. A live (active/in_progress) recurring
        # task for this template — even from a *prior* period — is resumed by
        # `scaffold_template` below rather than superseded by a fresh period;
        # so the "already ran" skip only applies when nothing is live.
        #
        # The template's persistent `log.md` is the period ledger. If it
        # records a scaffolding for this period and the task directory is gone
        # (a later Dream run deletes done recurring period tickets via its retro
        # pass; `relay delete` is the other case), the period was handled — do
        # not re-scaffold what already ran.
        if (
            _live_task_for_template(cfg, template.name) is None
            and _task_with_slug(cfg, target_slug) is None
            and _period_already_scaffolded(template, target_slug)
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
            outcome = scaffold_template(
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


def scaffold_named(
    cfg: Config, name: str, now: datetime | None = None
) -> ScaffoldOutcome:
    """Scaffold the named recurring task now, ignoring its schedule.

    `name` is the directory name under `relay-os/recurring/`. The task slug
    still uses the schedule-derived period key, so a manual `relay recurring
    launch <name>` and a bare `relay recurring` produce the same task
    directory for a given period.
    """
    now = now or datetime.now()
    path = recurring_dir(cfg) / name
    if not path.is_dir():
        raise RecurringError(f"no recurring task `recurring/{name}/`")
    template = Template.load(path)
    return scaffold_template(cfg, template, now)


def scaffold_template(
    cfg: Config,
    template: Template,
    now: datetime,
    *,
    allow_interactive: bool = True,
) -> ScaffoldOutcome:
    """Scaffold one recurring template for `now`'s firing. Idempotent."""
    effective_mode = _effective_mode(template, allow_interactive=allow_interactive)

    last_fire = _last_firing(template.schedule, now)
    period_key = _period_key(template.schedule, last_fire)
    target_slug = _recurring_slug(template.name, period_key)

    # One live task per template: an `active`/`in_progress` instance — current
    # period or a dead sweep's prior-period orphan — is *the* live run. Return
    # it (resume) instead of scaffolding a competing new period. A stuck run
    # therefore defers the next period until it reaches `done`/`paused`; that
    # is deliberate — finish the in-flight run before piling another on.
    live = _live_task_for_template(cfg, template.name)
    if live is not None:
        return ScaffoldOutcome(ref=live, created=False)

    existing = _task_with_slug(cfg, target_slug)
    if existing is not None:
        return ScaffoldOutcome(ref=existing, created=False)

    outcome = _scaffold_at_slug(
        cfg,
        template,
        target_slug=target_slug,
        effective_mode=effective_mode,
        title=_extract_title(template),
    )
    _record_run(template, outcome, now)
    return outcome


# A `relay recurring --all` throwaway run is slugged `<name>-dbg-<timestamp>`
# (see `scaffold_debug_run`), and any child task it spawns embeds that slug, so
# both carry the `-dbg-<digit>` infix. Requiring a digit after the marker spares
# ordinary hyphenated ticket names (e.g. `fix-dbg-output`) from matching.
_DEBUG_SLUG_RE = re.compile(r"-dbg-\d")


def is_debug_slug(slug: str) -> bool:
    """True if `slug` belongs to a `relay recurring --all` debug run (or its
    descendants). Debug runs are disposable scratch and must never reach Slack
    or the digest spool — only the task's own `log.md` records their events."""
    return bool(_DEBUG_SLUG_RE.search(slug))


def scaffold_debug_run(
    cfg: Config,
    template: Template,
    now: datetime,
    *,
    allow_interactive: bool = True,
) -> ScaffoldOutcome:
    """Scaffold a throwaway debug run of one template — `relay recurring --all`.

    Unlike `scaffold_template`, this ignores both the schedule-derived period
    slug and the period ledger: it always creates a *fresh* task under a unique
    `<template>-dbg-<timestamp>` slug, so it never collides with — or mutates —
    the real current-period task (which may already be `done`/`in_progress`/
    `paused`). The run is meant to be observed once and then deleted; it is not
    recorded in the template's period ledger.
    """
    effective_mode = _effective_mode(template, allow_interactive=allow_interactive)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    target_slug = f"{template.name}-dbg-{stamp}"
    return _scaffold_at_slug(
        cfg,
        template,
        target_slug=target_slug,
        effective_mode=effective_mode,
        title=f"[debug] {_extract_title(template)}",
    )


def scan_debug(
    cfg: Config, now: datetime | None = None, *, allow_interactive: bool = True
) -> DueScan:
    """Scaffold a fresh debug run for every recurring template.

    The debug counterpart of `scan_due`: it walks the same templates (skipping
    `_`-prefixed directories and `mode: auto`, with the same loud skips) but
    scaffolds an isolated throwaway run per template instead of get-or-creating
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
            outcome = scaffold_debug_run(
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


def _scaffold_at_slug(
    cfg: Config,
    template: Template,
    *,
    target_slug: str,
    effective_mode: str,
    title: str,
) -> ScaffoldOutcome:
    """Scaffold one recurring task at an explicit slug. Shared by period and
    debug scaffolding — the only differences are the slug and ledger handling,
    which the callers own."""
    # A recurring task is a machine-authored job: it scaffolds straight to
    # `active` and is meant to run, not be triaged. So when the template
    # doesn't name an assignee, default to the repo's configured default
    # agent — not the human owner, which `relay launch` cannot resolve to
    # an agent type. Without this a workflow-less template like Dream (no
    # step to ever rewrite `assignee:`) scaffolds unlaunchable.
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

    ref = scaffold_task(
        cfg=cfg,
        title=title,
        workflow_name=template.frontmatter.get("workflow"),
        contexts=contexts,
        mode=effective_mode,
        owner=template.frontmatter.get("owner"),
        assignee=assignee,
        watchers=list(template.frontmatter.get("watchers") or []),
        # Recurring tasks scaffold straight to `active`: they are
        # machine-authored ready jobs, and a workflow-less one (e.g. Dream)
        # could not otherwise be activated — `relay mark active` refuses
        # workflow-less tickets.
        status="active",
        slug_override=target_slug,
        # Carry the template body verbatim so sections beyond `## Description`
        # (notably `## Script config`, which sets a script step's mode/sync)
        # reach the period task instead of being dropped at scaffold time.
        body=template.body,
        created_by="system",
    )
    return ScaffoldOutcome(
        ref=TaskRef(slug=ref["slug"], path=ref["path"]), created=True
    )


# --- helpers ------------------------------------------------------------------


def _record_run(template: Template, outcome: ScaffoldOutcome, now: datetime) -> None:
    """Append a scaffolding line to the template's persistent `log.md`.

    The log is the period ledger: `scan_due` reads it to decide whether this
    period has already been handled, even after the period task has been
    deleted (a later Dream run's retro pass, or a human `relay delete`). The
    ledger lives in `log.md`, not `blackboard.md`, precisely because the log is
    never composed into a run's prompt — so the ledger can grow indefinitely
    without bloating context, and the blackboard stays small. Only a freshly
    created period task is recorded — re-scanning within the same period must
    not re-log.
    """
    if not outcome.created:
        return
    log = template.log_path
    existing = log.read_text() if log.is_file() else ""
    # Make sure the appended line lands on its own line, even when the
    # existing log does not end with a newline.
    sep = "" if not existing or existing.endswith("\n") else "\n"
    stamp = now.strftime("%Y-%m-%d %H:%M")
    log.write_text(f"{existing}{sep}{stamp} [system] scaffolded {outcome.ref.slug}\n")


def _last_firing(cron: str, now: datetime) -> datetime:
    it = croniter(cron, now)
    return it.get_prev(datetime)


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


# Every generated recurring task's slug carries this prefix. It is the
# identity marker: `_live_task_for_template` matches on `recurring-<name>-`,
# so a recurring task is recognizable (and a prior-period orphan resumable)
# regardless of which period suffix it ended up with. Debug runs
# (`scaffold_debug_run`) intentionally do NOT carry it — they are excluded
# from resume/dedup by `is_debug_slug`, and leaving them unprefixed keeps the
# `-dbg-` reaper's template extraction simple.
_RECURRING_PREFIX = "recurring-"


def _recurring_slug(template_name: str, period_key: str) -> str:
    return f"{_RECURRING_PREFIX}{template_name}-{period_key}"


def _task_with_slug(cfg: Config, target_slug: str) -> TaskRef | None:
    for ref in list_tasks(cfg):
        if ref.slug == target_slug:
            return ref
    return None


def _live_task_for_template(cfg: Config, template_name: str) -> TaskRef | None:
    """The template's single live (`active`/`in_progress`) recurring task.

    Identity is the slug prefix `recurring-<name>-`: any non-debug task under
    it is this template's instance, whatever period suffix it carries. That is
    what lets a *prior*-period orphan be found and resumed — the period-exact
    lookup it complements only ever sees the current period.

    Prefers an `in_progress` orphan (a dead sweep's frozen run, resumed from
    its step) over a never-launched `active`. Assumes a flat recurring
    namespace — no template name is a `-`-delimited prefix of another (e.g.
    `digest` vs `digest-weekly`); the shipped templates honor that, and
    `_reap_debug_orphans` makes the same assumption.
    """
    prefix = f"{_RECURRING_PREFIX}{template_name}-"
    live: TaskRef | None = None
    for ref in list_tasks(cfg):
        if not ref.slug.startswith(prefix) or is_debug_slug(ref.slug):
            continue
        status = read_ticket(ref).status
        if status == "in_progress":
            return ref
        if status == "active" and live is None:
            live = ref
    return live


def _period_already_scaffolded(template: Template, target_slug: str) -> bool:
    """Has this period's task ever been scaffolded?

    Reads the template's persistent `log.md`, which `_record_run` appends to
    each time a new period task is created. The log is the period ledger —
    consulted when the task directory itself is missing (a later Dream run's
    retro pass deletes done recurring period tickets; a human `relay delete`).

    For backward compatibility it also consults the legacy ledger location,
    `blackboard.md`: pre-migration templates recorded `scaffolded …` lines
    there, so a period handled before this change is still recognized.
    """
    needle = f"scaffolded {target_slug}"

    def _has_needle(path: Path) -> bool:
        if not path.is_file():
            return False
        return any(
            line.rstrip().endswith(needle) for line in path.read_text().splitlines()
        )

    return _has_needle(template.log_path) or _has_needle(template.blackboard_path)


def _extract_title(template: Template) -> str:
    if "title" in template.frontmatter:
        return template.frontmatter["title"]
    # Default to a humanized template name
    return template.name.replace("-", " ").replace("_", " ").strip().capitalize()


__all__ = [
    "Template",
    "ScaffoldOutcome",
    "DueTask",
    "DueScan",
    "scan_due",
    "scan_debug",
    "scaffold_named",
    "scaffold_template",
    "scaffold_debug_run",
    "is_debug_slug",
    "RecurringError",
]
