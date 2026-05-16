"""Prompt composition — the core of `relay launch`."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
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
from relay.tasks import TargetRef
from relay.ticket import Ticket
from relay.workflow import Workflow


_SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class PromptLayer:
    """One included layer of a composed Relay prompt."""

    layer: str
    title: str
    text: str
    ref: str | None = None
    path: str | None = None
    raw: bool = False

    @property
    def rendered(self) -> str:
        if self.raw:
            return self.text
        return _section(self.title, self.text)

    @property
    def byte_count(self) -> int:
        return len(self.rendered.encode())

    @property
    def char_count(self) -> int:
        return len(self.rendered)

    @property
    def approx_tokens(self) -> int:
        return estimate_tokens(self.rendered)


@dataclass(frozen=True)
class PromptComposition:
    """Composed prompt plus layer metadata for prompt-scope reporting."""

    layers: list[PromptLayer]

    @property
    def prompt(self) -> str:
        return "\n\n---\n\n".join(
            layer.rendered.strip() for layer in self.layers if layer.rendered.strip()
        ) + "\n"

    @property
    def byte_count(self) -> int:
        return len(self.prompt.encode())

    @property
    def char_count(self) -> int:
        return len(self.prompt)

    @property
    def approx_tokens(self) -> int:
        return estimate_tokens(self.prompt)


def estimate_tokens(text: str) -> int:
    """Dependency-free approximation: about one token per four characters."""
    if not text:
        return 0
    return (len(text) + 3) // 4


def compose_prompt(cfg: Config, task_ref: TargetRef, ticket: Ticket) -> str:
    """Assemble the composed prompt in spec order (§compose)."""
    return compose_prompt_report(cfg, task_ref, ticket).prompt


def compose_prompt_report(
    cfg: Config,
    task_ref: TargetRef,
    ticket: Ticket,
) -> PromptComposition:
    """Assemble the prompt and keep per-layer measurement metadata."""
    layers: list[PromptLayer] = []

    header = f"# Relay task — {task_ref.id_slug}\n\nTitle: {ticket.title}\nMode: {ticket.mode}"
    if ticket.status:
        header += f"\nStatus: {ticket.status}"
    layers.append(PromptLayer("header", "Header", header, raw=True))

    # 1. Base prompt
    layers.append(PromptLayer(
        "base_prompt",
        "Relay base prompt",
        _resource("prompt.md"),
        ref="prompt.md",
    ))

    # 2. Mode-specific prompt
    if ticket.mode == "interactive":
        layers.append(PromptLayer(
            "mode_prompt",
            "Interactive mode",
            _resource("prompt-interactive.md"),
            ref="prompt-interactive.md",
        ))
    elif ticket.mode == "auto":
        layers.append(PromptLayer(
            "mode_prompt",
            "Auto mode",
            _resource("prompt-auto.md"),
            ref="prompt-auto.md",
        ))
    # script mode never gets composed; enforced by launch.py

    # 3. rules.md
    rules = rules_path(cfg)
    if rules.is_file():
        layers.append(PromptLayer(
            "global_rules",
            "Global rules",
            rules.read_text(),
            ref="rules.md",
            path=str(rules),
        ))

    # 4. repo context.md
    pctx = repo_context_path(cfg)
    if pctx.is_file():
        layers.append(PromptLayer(
            "repo_context",
            "Repo context",
            pctx.read_text(),
            ref="context.md",
            path=str(pctx),
        ))

    # 5. ticket-attached contexts
    for ref in ticket.contexts:
        cp = context_path(cfg, ref)
        if cp.is_file():
            layers.append(PromptLayer(
                "ticket_context",
                f"Context — {ref}",
                cp.read_text(),
                ref=ref,
                path=str(cp),
            ))

    # 6. inline `## Context` from ticket body
    inline_ctx = _extract_section(ticket.body, "Context")
    if inline_ctx:
        layers.append(PromptLayer(
            "task_context",
            "Task-specific context",
            inline_ctx,
            ref="ticket.md##Context",
            path=str(task_ref.path / "ticket.md"),
        ))

    # 7. ticket-level skills + current workflow step
    for skill_ref in ticket.skills:
        layers.extend(_skill_layers(cfg, skill_ref))
    layers.extend(_step_layers(cfg, ticket))

    # 8. blackboard
    bb = task_ref.path / "blackboard.md"
    if bb.is_file():
        layers.append(PromptLayer(
            "blackboard",
            "Blackboard (current state)",
            bb.read_text(),
            ref="blackboard.md",
            path=str(bb),
        ))

    # Trailing task description from ticket body
    desc = _extract_section(ticket.body, "Description")
    if desc:
        layers.append(PromptLayer(
            "task_description",
            "Task description",
            desc,
            ref="ticket.md##Description",
            path=str(task_ref.path / "ticket.md"),
        ))

    return PromptComposition(layers)


def write_prompt_file(prompt: str, task_ref: TargetRef, dest_dir: Path | None = None) -> Path:
    """Write the composed prompt to a temp file. Returns its path.

    Default location: /tmp/relay-<id>-<timestamp>.md per spec.
    """
    if dest_dir is None:
        dest_dir = Path(tempfile.gettempdir())
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    safe_slug = task_ref.id_slug.replace("/", "-")
    path = dest_dir / f"relay-{safe_slug}-{ts}.md"
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


def _skill_layers(cfg: Config, skill_ref: str) -> list[PromptLayer]:
    sp = skill_path(cfg, skill_ref)
    if sp.is_file():
        return [PromptLayer(
            "top_level_skill",
            f"Skill: {skill_ref}",
            sp.read_text(),
            ref=skill_ref,
            path=str(sp),
        )]
    return [PromptLayer(
        "top_level_skill",
        f"Skill: {skill_ref}",
        f"*Skill file not found at {sp}.*",
        ref=skill_ref,
        path=str(sp),
    )]


def _step_layers(cfg: Config, ticket: Ticket) -> list[PromptLayer]:
    current = ticket.current_step()
    if not current:
        return []

    name = current["name"]
    skill_refs = list(current.get("skills") or [])

    if skill_refs:
        out: list[PromptLayer] = []
        for skill_ref in skill_refs:
            sp = skill_path(cfg, skill_ref)
            if sp.is_file():
                out.append(PromptLayer(
                    "workflow_skill",
                    f"Current step: {name} (skill: {skill_ref})",
                    sp.read_text(),
                    ref=skill_ref,
                    path=str(sp),
                ))
            else:
                out.append(PromptLayer(
                    "workflow_skill",
                    f"Current step: {name} (skill: {skill_ref})",
                    f"*Skill file not found at {sp}.*",
                    ref=skill_ref,
                    path=str(sp),
                ))
        return out

    # Inline: load workflow, pull the matching heading
    wf_name = (ticket.workflow or {}).get("name")
    if not wf_name:
        return []
    try:
        wf = Workflow.load(workflow_path(cfg, wf_name))
    except Exception:  # workflow may have been deleted after ticket was created
        wp = workflow_path(cfg, wf_name)
        return [PromptLayer(
            "workflow_inline",
            f"Current step: {name}",
            "*Workflow definition not found; using frozen snapshot only.*",
            ref=wf_name,
            path=str(wp),
        )]
    inline = wf.inline_instructions.get(name)
    if inline:
        return [PromptLayer(
            "workflow_inline",
            f"Current step: {name}",
            inline,
            ref=wf_name,
            path=str(workflow_path(cfg, wf_name)),
        )]
    return [PromptLayer(
        "workflow_inline",
        f"Current step: {name}",
        "*No instructions attached to this step.*",
        ref=wf_name,
        path=str(workflow_path(cfg, wf_name)),
    )]


__all__ = [
    "PromptComposition",
    "PromptLayer",
    "compose_prompt",
    "compose_prompt_report",
    "estimate_tokens",
    "write_prompt_file",
]
