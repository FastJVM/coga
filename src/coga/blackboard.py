"""Blackboard region helpers — render the default template and edit sections.

The blackboard is the region of a task's `ticket.md` below the
`<!-- coga:blackboard -->` fence (see `coga.taskfile`). These helpers operate
on that region only: they read it with `read_blackboard`, manipulate the
section text, and write it back with `replace_blackboard`, so the frontmatter
and body above the fence are never touched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from coga.taskfile import (
    TaskFileError,
    fence_count,
    read_blackboard,
    replace_blackboard,
)


BLACKBOARD_WARN_BYTES = 32 * 1024
PRODUCTION_NOTES_HEADING = "Production notes"
PRELAUNCH_AUTHORING_HEADINGS = (
    "Evaluator review",
    "Ticket authoring notes",
    "Proposals",
)
PRELAUNCH_SYNTHESIS_TEXT_CHARS = 600
BLOCKER_TS_FORMAT = "%Y-%m-%d %H:%M"


def render_blackboard(task_title: str) -> str:
    """Render the default blackboard template with task metadata filled in."""
    template = files("coga.resources").joinpath("blackboard.md").read_text()
    return template.replace("{task_title}", task_title)


_SECTION_RE = re.compile(r"^(## .+?)$", re.MULTILINE)


def append_to_section_text(text: str, heading: str, entry: str) -> str:
    """Return `text` with `entry` appended to the `## <heading>` section.

    Pure text transform on the blackboard region. If the section isn't found, a
    new section is appended at the end.
    """
    entry = entry.rstrip() + "\n"
    target = f"## {heading}"

    matches = list(_SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        if m.group(1).strip() == target:
            # End of this section = start of next section, or EOF.
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            # Trim trailing "---" separator between sections so the entry sits inside the section.
            body_until_end = text[:end]
            trimmed = body_until_end.rstrip()
            separator_start = trimmed.rfind("---")
            if separator_start > m.end() and trimmed[separator_start:].strip() == "---":
                insertion = trimmed[:separator_start].rstrip() + "\n\n" + entry + "\n"
                return insertion + "\n---\n\n" + text[end:]
            return trimmed + "\n\n" + entry + text[end:]

    # Section not found — append a new one.
    tail = "" if text.endswith("\n") else "\n"
    return text + f"{tail}\n---\n\n## {heading}\n\n{entry}"


def _normalize_section_heading(heading: str) -> str:
    stripped = heading.strip()
    if stripped.startswith("## "):
        return stripped
    return f"## {stripped}"


def _has_section(text: str, heading: str) -> bool:
    target = _normalize_section_heading(heading)
    return any(
        match.group(1).strip() == target for match in _SECTION_RE.finditer(text)
    )


def _section_headings(text: str) -> list[str]:
    headings: list[str] = []
    for match in _SECTION_RE.finditer(text):
        headings.append(match.group(1).removeprefix("## ").strip())
    return headings


def _is_stock_blackboard(text: str) -> bool:
    stock = files("coga.resources").joinpath("blackboard.md").read_text()
    return text.strip() in {"", stock.strip()}


def prelaunch_blackboard_synthesis_reason_text(text: str) -> str | None:
    """Return why a draft blackboard must be synthesized before launch.

    A draft ticket's stock placeholder is empty authoring space. A
    `## Production notes` section is an explicit operator signal that the
    remaining blackboard content is intentional launch/handoff material.
    """
    if _has_section(text, PRODUCTION_NOTES_HEADING):
        return None
    if _is_stock_blackboard(text):
        return None

    headings = [
        heading
        for heading in _section_headings(text)
        if heading in PRELAUNCH_AUTHORING_HEADINGS
    ]
    if headings:
        return "authoring section(s): " + ", ".join(f"## {h}" for h in headings)

    size = len(text.strip())
    if size >= PRELAUNCH_SYNTHESIS_TEXT_CHARS:
        return f"non-placeholder blackboard is {size} characters"
    return None


def append_to_section(ticket_path: Path, heading: str, entry: str) -> None:
    """Append `entry` to the `## <heading>` section of the blackboard region.

    Reads and rewrites only the region below the fence; the body above stays
    byte-for-byte unchanged.
    """
    region = read_blackboard(ticket_path)
    replace_blackboard(ticket_path, append_to_section_text(region, heading, entry))


def prelaunch_blackboard_synthesis_reason(
    ticket_path: Path,
    *,
    blackboard_required: bool = True,
) -> str | None:
    """Return why a ticket blackboard must be synthesized before first launch."""
    if (
        not blackboard_required
        and fence_count(ticket_path.read_text(encoding="utf-8")) == 0
    ):
        return None
    region = read_blackboard(ticket_path, blackboard_required=blackboard_required)
    return prelaunch_blackboard_synthesis_reason_text(region)


@dataclass(frozen=True)
class Blocker:
    """One unresolved or resolved blocker recorded in a task blackboard."""

    id: str
    created_at: datetime | None
    actor: str
    reason: str
    resolved: bool = False
    resolved_at: datetime | None = None
    answer: str | None = None


_CHECKBOX_BLOCKER_RE = re.compile(
    r"^- \[(?P<mark>[ xX])\]\s+"
    r"\[(?P<ts>[^\]]+)\]\s+"
    r"\[(?P<actor>[^\]]+)\]\s+"
    r"id=(?P<id>\S+)\s+"
    r"(?P<reason>.*)$"
)
_LEGACY_BLOCKER_RE = re.compile(
    r"^- \[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]\s+"
    r"\[(?P<actor>[^\]]+)\]\s+"
    r"(?P<reason>.*)$"
)
_RESOLVED_LINE_RE = re.compile(
    r"^\s+resolved:\s+\[(?P<ts>[^\]]+)\]\s+\[(?P<actor>[^\]]+)\]\s+(?P<answer>.*)$"
)


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, BLOCKER_TS_FORMAT)
    except ValueError:
        return None


def _blocker_id(now: datetime) -> str:
    return now.strftime("%Y%m%dT%H%M%S")


def append_blocker(ticket_path: Path, actor: str, reason: str) -> Blocker:
    """Write a timestamped blocker entry to the blackboard's Blockers section.

    `ticket_path` is the task's `ticket.md` (file-form: the `.md` file itself;
    directory-form: `<dir>/ticket.md`)."""
    now = datetime.now()
    ts = now.strftime(BLOCKER_TS_FORMAT)
    blocker_id = _blocker_id(now)
    entry = f"- [ ] [{ts}] [{actor}] id={blocker_id} {reason}"
    append_to_section(ticket_path, "Blockers", entry)
    return Blocker(
        id=blocker_id,
        created_at=now.replace(second=0, microsecond=0),
        actor=actor,
        reason=reason,
    )


def parse_blockers_text(text: str) -> list[Blocker]:
    """Parse blockers from a blackboard region.

    New entries use checkbox lines with a stable id. Historical panic entries
    had no checkbox or id; treat them as open until an unblock rewrite marks
    them resolved.
    """
    lines = text.splitlines()
    blockers: list[Blocker] = []
    pending_index: int | None = None
    legacy_counter = 0
    for line in lines:
        checkbox = _CHECKBOX_BLOCKER_RE.match(line)
        if checkbox:
            created_at = _parse_ts(checkbox.group("ts"))
            blockers.append(
                Blocker(
                    id=checkbox.group("id"),
                    created_at=created_at,
                    actor=checkbox.group("actor"),
                    reason=checkbox.group("reason").strip(),
                    resolved=checkbox.group("mark").lower() == "x",
                )
            )
            pending_index = len(blockers) - 1
            continue

        legacy = _LEGACY_BLOCKER_RE.match(line)
        if legacy:
            legacy_counter += 1
            created_at = _parse_ts(legacy.group("ts"))
            blockers.append(
                Blocker(
                    id=f"legacy-{legacy_counter}",
                    created_at=created_at,
                    actor=legacy.group("actor"),
                    reason=legacy.group("reason").strip(),
                    resolved=False,
                )
            )
            pending_index = len(blockers) - 1
            continue

        resolved = _RESOLVED_LINE_RE.match(line)
        if resolved and pending_index is not None:
            blocker = blockers[pending_index]
            blockers[pending_index] = Blocker(
                id=blocker.id,
                created_at=blocker.created_at,
                actor=blocker.actor,
                reason=blocker.reason,
                resolved=True,
                resolved_at=_parse_ts(resolved.group("ts")),
                answer=resolved.group("answer").strip(),
            )
    return blockers


def read_blockers(ticket_path: Path) -> list[Blocker]:
    """Read every blocker from a task's blackboard region."""
    return parse_blockers_text(read_blackboard(ticket_path))


def open_blockers(ticket_path: Path) -> list[Blocker]:
    """Read unresolved blockers from a task's blackboard region."""
    return [b for b in read_blockers(ticket_path) if not b.resolved]


def resolve_open_blockers(ticket_path: Path, actor: str, answer: str) -> list[Blocker]:
    """Mark every currently open blocker resolved and append the answer.

    A blocked ticket may carry multiple asks. `coga unblock` answers all open
    asks in one transition so status and blackboard cannot disagree.
    """
    now = datetime.now()
    ts = now.strftime(BLOCKER_TS_FORMAT)
    region = read_blackboard(ticket_path)
    lines = region.splitlines()
    blockers_before = parse_blockers_text(region)
    if not [b for b in blockers_before if not b.resolved]:
        return []

    resolved_lines: list[str] = []
    legacy_counter = 0
    for line in lines:
        checkbox = _CHECKBOX_BLOCKER_RE.match(line)
        if checkbox:
            if checkbox.group("mark").lower() == "x":
                resolved_lines.append(line)
            else:
                resolved_lines.append(line.replace("- [ ]", "- [x]", 1))
                resolved_lines.append(f"  resolved: [{ts}] [{actor}] {answer}")
            continue
        legacy = _LEGACY_BLOCKER_RE.match(line)
        if legacy:
            legacy_counter += 1
            resolved_lines.append(
                "- [x] "
                f"[{legacy.group('ts')}] "
                f"[{legacy.group('actor')}] "
                f"id=legacy-{legacy_counter} "
                f"{legacy.group('reason').strip()}"
            )
            resolved_lines.append(f"  resolved: [{ts}] [{actor}] {answer}")
            continue
        resolved_lines.append(line)

    trailing = "\n" if region.endswith("\n") else ""
    replace_blackboard(ticket_path, "\n".join(resolved_lines) + trailing)
    return [b for b in read_blockers(ticket_path) if b.resolved and b.answer == answer]


def format_bytes(size: int) -> str:
    """Human-friendly binary size."""
    if size < 1024:
        return f"{size} B"
    return f"{size / 1024:.1f} KiB"


def blackboard_size_warning(
    ticket_path: Path,
    *,
    max_bytes: int = BLACKBOARD_WARN_BYTES,
) -> str | None:
    """Return a warning if the ticket's blackboard region is large enough to
    bloat prompts.

    Measures only the region below the fence — the part compose includes in
    launch prompts — not the whole `ticket.md`.
    """
    try:
        region = read_blackboard(ticket_path)
    except (FileNotFoundError, TaskFileError):
        return None
    size = len(region.encode())
    if size <= max_bytes:
        return None
    return (
        f"blackboard region is {format_bytes(size)} "
        f"(warning threshold {format_bytes(max_bytes)}); it is included in "
        "launch prompts. Consider summarizing old notes."
    )


__all__ = [
    "BLACKBOARD_WARN_BYTES",
    "PRODUCTION_NOTES_HEADING",
    "PRELAUNCH_AUTHORING_HEADINGS",
    "PRELAUNCH_SYNTHESIS_TEXT_CHARS",
    "render_blackboard",
    "Blocker",
    "append_to_section_text",
    "prelaunch_blackboard_synthesis_reason_text",
    "append_to_section",
    "prelaunch_blackboard_synthesis_reason",
    "append_blocker",
    "parse_blockers_text",
    "read_blockers",
    "open_blockers",
    "resolve_open_blockers",
    "format_bytes",
    "blackboard_size_warning",
]
