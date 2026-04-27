"""Prompt composition — the core of `relay launch`."""

from __future__ import annotations

import re
import tempfile
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from relay.config import Config
from relay.paths import (
    context_path,
    repo_context_path,
    rules_path,
    skill_path,
    workflow_path,
)
from relay.tasks import TaskRef
from relay.ticket import Ticket
from relay.workflow import Workflow


_SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def compose_prompt(cfg: Config, task_ref: TaskRef, ticket: Ticket) -> str:
    """Assemble the composed prompt in spec order (§compose)."""
    parts: list[str] = []

    parts.append(f"# Relay task — {task_ref.id_slug}\n\n"
                 f"Title: {ticket.title}\nMode: {ticket.mode}\nStatus: {ticket.status}")

    # 1. Base prompt
    parts.append(_resource("prompt.md"))

    # 2. Mode-specific prompt
    if ticket.mode == "interactive":
        parts.append(_resource("prompt-interactive.md"))
    elif ticket.mode == "auto":
        parts.append(_resource("prompt-auto.md"))
    # script mode never gets composed; enforced by launch.py

    # 3. rules.md
    rules = rules_path(cfg)
    if rules.is_file():
        parts.append(_section("Global rules", rules.read_text()))

    # 4. repo context.md
    pctx = repo_context_path(cfg)
    if pctx.is_file():
        parts.append(_section("Repo context", pctx.read_text()))

    # 5. ticket-attached contexts
    for ref in ticket.contexts:
        cp = context_path(cfg, ref)
        if cp.is_file():
            parts.append(_section(f"Context — {ref}", cp.read_text()))

    # 6. inline `## Context` from ticket body
    inline_ctx = _extract_section(ticket.body, "Context")
    if inline_ctx:
        parts.append(_section("Task-specific context", inline_ctx))

    # 7. current workflow step (skill or inline instructions)
    parts.extend(_step_sections(cfg, ticket))

    # 8. blackboard
    bb = task_ref.path / "blackboard.md"
    if bb.is_file():
        parts.append(_section("Blackboard (current state)", bb.read_text()))

    # Trailing task description from ticket body
    desc = _extract_section(ticket.body, "Description")
    if desc:
        parts.append(_section("Task description", desc))

    return "\n\n---\n\n".join(p.strip() for p in parts if p.strip()) + "\n"


def write_prompt_file(prompt: str, task_ref: TaskRef, dest_dir: Path | None = None) -> Path:
    """Write the composed prompt to a temp file. Returns its path.

    Default location: /tmp/relay-<id>-<timestamp>.md per spec.
    """
    if dest_dir is None:
        dest_dir = Path(tempfile.gettempdir())
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    path = dest_dir / f"relay-{task_ref.id_slug}-{ts}.md"
    path.write_text(prompt)
    return path


# --- helpers ------------------------------------------------------------------


def _resource(name: str) -> str:
    return files("relay.resources").joinpath(name).read_text()


def _section(title: str, body: str) -> str:
    body = body.strip()
    return f"## {title}\n\n{body}"


def _extract_section(body: str, heading: str) -> str:
    """Extract the contents of `## <heading>` from a markdown body."""
    matches = list(_SECTION_HEADING_RE.finditer(body))
    for i, m in enumerate(matches):
        if m.group(1).strip().lower() == heading.lower():
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            return body[start:end].strip()
    return ""


def _step_sections(cfg: Config, ticket: Ticket) -> list[str]:
    current = ticket.current_step()
    if not current:
        return []

    name = current["name"]
    skill_ref = current.get("skill")

    if skill_ref:
        sp = skill_path(cfg, skill_ref)
        if sp.is_file():
            return [_section(
                f"Current step: {name} (skill: {skill_ref})",
                sp.read_text(),
            )]
        return [_section(
            f"Current step: {name} (skill: {skill_ref})",
            f"*Skill file not found at {sp}.*",
        )]

    # Inline: load workflow, pull the matching heading
    wf_name = (ticket.workflow or {}).get("name")
    if not wf_name:
        return []
    try:
        wf = Workflow.load(workflow_path(cfg, wf_name))
    except Exception:  # workflow may have been deleted after ticket was created
        return [_section(
            f"Current step: {name}",
            "*Workflow definition not found; using frozen snapshot only.*",
        )]
    inline = wf.inline_instructions.get(name)
    if inline:
        return [_section(f"Current step: {name}", inline)]
    return [_section(
        f"Current step: {name}",
        "*No instructions attached to this step.*",
    )]


__all__ = ["compose_prompt", "write_prompt_file"]
