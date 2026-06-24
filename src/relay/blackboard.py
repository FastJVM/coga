"""Blackboard region helpers — render the default template and append to sections.

The blackboard is the region of a task's `ticket.md` below the
`<!-- relay:blackboard -->` fence (see `relay.taskfile`). These helpers operate
on that region only: they read it with `read_blackboard`, manipulate the
section text, and write it back with `replace_blackboard`, so the frontmatter
and body above the fence are never touched.
"""

from __future__ import annotations

import re
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from relay.taskfile import TaskFileError, read_blackboard, replace_blackboard


BLACKBOARD_WARN_BYTES = 32 * 1024


def render_blackboard(task_title: str) -> str:
    """Render the default blackboard template with task metadata filled in."""
    template = files("relay.resources").joinpath("blackboard.md").read_text()
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


def append_to_section(ticket_path: Path, heading: str, entry: str) -> None:
    """Append `entry` to the `## <heading>` section of the blackboard region.

    Reads and rewrites only the region below the fence; the body above stays
    byte-for-byte unchanged.
    """
    region = read_blackboard(ticket_path)
    replace_blackboard(ticket_path, append_to_section_text(region, heading, entry))


def append_blocker(task_dir: Path, actor: str, reason: str) -> None:
    """Write a timestamped blocker entry to the blackboard's Blockers section."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{ts}] [{actor}] {reason}"
    append_to_section(task_dir / "ticket.md", "Blockers", entry)


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
    "render_blackboard",
    "append_to_section_text",
    "append_to_section",
    "append_blocker",
    "format_bytes",
    "blackboard_size_warning",
]
