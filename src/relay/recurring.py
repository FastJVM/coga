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
    across runs (a recurring task records last-run state there so the next
    run can pick up where this one left off); `log.md` is the append-only
    run history.
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
        """Persistent blackboard — recurring runs store last-run state here."""
        return self.path / "blackboard.md"

    @property
    def log_path(self) -> Path:
        """Append-only run history for this recurring task."""
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
    ones that are still `active`. `last_fire` is the scheduled firing this
    task covers — used to report "ready" vs "overdue" and to order launches.
    """

    template: str
    ref: TaskRef
    last_fire: datetime
    created: bool
    status: str

    @property
    def launchable(self) -> bool:
        # `active` means scaffolded-and-not-yet-run: either created this scan
        # or carried over from an earlier scan that never launched it.
        # `in_progress`/`paused`/`done` are already handled — never relaunch.
        return self.status == "active"


@dataclass
class DueScan:
    """Outcome of scanning every recurring template for the current period."""

    tasks: list[DueTask]
    errors: list[tuple[str, str]]  # (template_filename, error_message)

    @property
    def due(self) -> list[DueTask]:
        """Launchable tasks, most-overdue first."""
        return sorted(
            (t for t in self.tasks if t.launchable), key=lambda t: t.last_fire
        )


def scan_due(cfg: Config, now: datetime | None = None) -> DueScan:
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
            outcome = scaffold_template(cfg, template, now)
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
                last_fire=_last_firing(template.schedule, now),
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
    cfg: Config, template: Template, now: datetime
) -> ScaffoldOutcome:
    """Scaffold one recurring template for `now`'s firing. Idempotent."""
    effective_mode = template.frontmatter.get("mode", "auto")

    last_fire = _last_firing(template.schedule, now)
    period_key = _period_key(template.schedule, last_fire)
    target_slug = f"{template.name}-{period_key}"

    existing = _task_with_slug(cfg, target_slug)
    if existing is not None:
        return ScaffoldOutcome(ref=existing, created=False)

    blocking = _blocking_prior_run(cfg, template.name, target_slug)
    if blocking is not None:
        ref, status = blocking
        raise RecurringError(
            f"previous run {ref.slug} is {status}; finish or delete it before "
            f"scaffolding {target_slug}"
        )

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

    ref = scaffold_task(
        cfg=cfg,
        title=_extract_title(template),
        workflow_name=template.frontmatter.get("workflow"),
        contexts=list(template.frontmatter.get("contexts") or []),
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
        description=_extract_description(template),
        created_by="system",
    )
    outcome = ScaffoldOutcome(
        ref=TaskRef(slug=ref["slug"], path=ref["path"]), created=True
    )
    _record_run(template, outcome, now)
    return outcome


# --- helpers ------------------------------------------------------------------


def _record_run(template: Template, outcome: ScaffoldOutcome, now: datetime) -> None:
    """Append a line to the recurring task's own `log.md` when it scaffolds a
    period task.

    The recurring directory is the task's durable home: `log.md` is the run
    history across periods, and `blackboard.md` is the persistent state a run
    reads and updates for the next one. Only a freshly created period task is
    recorded — re-scanning within the same period must not re-log.
    """
    if not outcome.created:
        return
    log = template.log_path
    existing = log.read_text() if log.is_file() else ""
    stamp = now.strftime("%Y-%m-%d %H:%M")
    log.write_text(f"{existing}[{stamp}] scaffolded {outcome.ref.slug}\n")


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


def _task_with_slug(cfg: Config, target_slug: str) -> TaskRef | None:
    for ref in list_tasks(cfg):
        if ref.slug == target_slug:
            return ref
    return None


def _blocking_prior_run(
    cfg: Config, template_name: str, target_slug: str
) -> tuple[TaskRef, str] | None:
    """Return an unfinished older period task for this template, if any."""
    template_names = _template_names(cfg)
    for ref in list_tasks(cfg):
        if ref.slug == target_slug:
            continue
        if _template_for_slug(ref.slug, template_names) != template_name:
            continue
        ticket = read_ticket(ref)
        if ticket.status != "done":
            return ref, ticket.status
    return None


def _template_names(cfg: Config) -> list[str]:
    root = recurring_dir(cfg)
    if not root.is_dir():
        return []
    return sorted(
        (
            path.name
            for path in root.iterdir()
            if path.is_dir() and not path.name.startswith("_")
        ),
        key=len,
        reverse=True,
    )


def _template_for_slug(slug: str, template_names: list[str]) -> str | None:
    for name in template_names:
        if slug.startswith(f"{name}-"):
            return name
    return None


def _extract_description(template: Template) -> str:
    # Mirrors the logic in compose._extract_section but keeps this module standalone.
    body = template.body
    m = re.search(r"(?m)^##\s+Description\s*$", body)
    if not m:
        return ""
    after = body[m.end():]
    next_heading = re.search(r"(?m)^##\s+", after)
    return (after[:next_heading.start()] if next_heading else after).strip()


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
    "scaffold_named",
    "scaffold_template",
    "RecurringError",
]
