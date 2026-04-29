"""Recurring task templates under `relay-os/recurring/*.md`."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from croniter import croniter

from relay.scaffold import scaffold_task
from relay.config import Config
from relay.paths import recurring_dir
from relay.tasks import TaskRef, list_tasks


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


class RecurringError(Exception):
    pass


@dataclass
class Template:
    path: Path
    name: str
    frontmatter: dict[str, Any]
    body: str

    @classmethod
    def load(cls, path: Path) -> "Template":
        text = path.read_text()
        match = _FM_RE.match(text)
        if not match:
            raise RecurringError(f"{path}: missing YAML frontmatter")
        fm = yaml.safe_load(match.group(1)) or {}
        if not isinstance(fm, dict):
            raise RecurringError(f"{path}: frontmatter must be a mapping")
        if "schedule" not in fm:
            raise RecurringError(f"{path}: `schedule` is required")
        return cls(path=path, name=path.stem, frontmatter=fm, body=match.group(2))

    @property
    def schedule(self) -> str:
        return self.frontmatter["schedule"]


def check_recurring(cfg: Config, now: datetime | None = None) -> list[TaskRef]:
    """Scan recurring templates and create any due tasks. Idempotent.

    Returns the newly-created TaskRefs.
    """
    now = now or datetime.now()
    root = recurring_dir(cfg)
    if not root.is_dir():
        return []

    created: list[TaskRef] = []
    for path in sorted(root.glob("*.md")):
        if path.name.startswith("_"):
            # Underscore-prefixed files are templates/scaffolds, not live recurring tasks.
            continue
        try:
            template = Template.load(path)
        except RecurringError as exc:
            # Don't let one bad template block the rest
            import sys
            sys.stderr.write(f"[recurring] skipping {path.name}: {exc}\n")
            continue

        last_fire = _last_firing(template.schedule, now)
        period_key = _period_key(template.schedule, last_fire)
        target_slug = f"{template.name}-{period_key}"

        if _task_with_slug_exists(cfg, target_slug):
            continue

        ref = scaffold_task(
            cfg=cfg,
            title=_extract_title(template),
            workflow_name=template.frontmatter.get("workflow"),
            contexts=list(template.frontmatter.get("contexts") or []),
            mode=template.frontmatter.get("mode", "auto"),
            owner=template.frontmatter.get("owner"),
            assignee=template.frontmatter.get("assignee"),
            watchers=list(template.frontmatter.get("watchers") or []),
            status=template.frontmatter.get("status") or cfg.default_status,
            slug_override=target_slug,
            description=_extract_description(template),
            created_by="system",
        )
        created.append(TaskRef(slug=ref["slug"], path=ref["path"]))
    return created


# --- helpers ------------------------------------------------------------------


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


def _task_with_slug_exists(cfg: Config, target_slug: str) -> bool:
    for ref in list_tasks(cfg):
        if ref.slug == target_slug:
            return True
    return False


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


__all__ = ["Template", "check_recurring", "RecurringError"]
