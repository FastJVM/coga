"""Prompt composition — the core of `coga launch`."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from coga.config import Config
from coga.paths import (
    context_resolution_paths,
    repo_context_path,
    resolve_context_path,
    resolve_skill_path,
    resolve_workflow_path,
    skill_resolution_paths,
)
from coga.taskfile import split_body
from coga.tasks import BootstrapRef, TargetRef
from coga.ticket import Ticket
from coga.workflow import Workflow


class ComposeError(RuntimeError):
    """A referenced context or skill could not be resolved at compose time.

    Raised rather than silently dropping the layer: a missing context/skill
    means the launched agent would run without knowledge the human expected
    it to have, producing confidently wrong output. `coga launch` catches
    this and refuses to start the task. `coga validate` catches the same
    condition statically.
    """


_SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class PromptLayer:
    """One included layer of a composed Coga prompt."""

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


def compose_prompt(
    cfg: Config,
    task_ref: TargetRef,
    ticket: Ticket,
    *,
    autonomy_override: str | None = None,
) -> str:
    """Assemble the composed prompt in spec order (§compose)."""
    return compose_prompt_report(
        cfg, task_ref, ticket, autonomy_override=autonomy_override
    ).prompt


def compose_prompt_report(
    cfg: Config,
    task_ref: TargetRef,
    ticket: Ticket,
    *,
    autonomy_override: str | None = None,
) -> PromptComposition:
    """Assemble the prompt and keep per-layer measurement metadata.

    `autonomy_override`, when set, replaces the ticket's `autonomy:` for the
    header and the autonomy-specific prompt block — a per-launch debug override
    that never touches the ticket file.
    """
    layers: list[PromptLayer] = []
    autonomy = autonomy_override or ticket.autonomy

    # Split the single-file ticket body at the blackboard fence: the body above
    # feeds the Description / inline-Context layers, the region below is the
    # blackboard layer. Bootstrap tickets legitimately carry no fence, so they are
    # parsed leniently (blackboard is then None and the blackboard layer is
    # omitted); a normal task ticket missing the fence fails loud.
    body_above, blackboard_text = split_body(
        ticket.body, blackboard_required=not isinstance(task_ref, BootstrapRef)
    )

    header = (
        f"# Coga task — {task_ref.id_slug}\n\n"
        f"Title: {ticket.title}\n"
        f"Task directory: {_task_path_for_prompt(cfg, task_ref)}\n"
        f"Autonomy: {autonomy}"
    )
    if ticket.status:
        header += f"\nStatus: {ticket.status}"
    layers.append(PromptLayer("header", "Header", header, raw=True))

    # 1. Base prompt
    layers.append(PromptLayer(
        "base_prompt",
        "Coga base prompt",
        _resource("prompt.md"),
        ref="prompt.md",
    ))

    # 2. Autonomy-specific prompt
    if autonomy == "interactive":
        layers.append(PromptLayer(
            "mode_prompt",
            "Interactive mode",
            _resource("prompt-interactive.md"),
            ref="prompt-interactive.md",
        ))
    elif autonomy == "auto":
        layers.append(PromptLayer(
            "mode_prompt",
            "Auto mode",
            _resource("prompt-auto.md"),
            ref="prompt-auto.md",
        ))
    # A script task is never composed; enforced by launch.py's dispatch.

    # 3. repo context.md
    pctx = repo_context_path(cfg)
    if pctx.is_file():
        layers.append(PromptLayer(
            "repo_context",
            "Repo context",
            pctx.read_text(),
            ref="context.md",
            path=str(pctx),
        ))

    # 4. ticket-attached contexts
    for ref in ticket.contexts:
        cp = resolve_context_path(cfg, ref)
        if cp is None:
            checked = _checked_context_paths(cfg, ref)
            raise ComposeError(
                f"Task {task_ref.id_slug!r} references context {ref!r}, but no "
                f"context file exists for it. Checked: {checked}. Create one of "
                f"those files or remove {ref!r} from the ticket's `contexts:` list."
            )
        layers.append(PromptLayer(
            "ticket_context",
            f"Context — {ref}",
            cp.read_text(),
            ref=ref,
            path=str(cp),
        ))

    # 5. inline `## Context` from ticket body
    inline_ctx = _extract_section(body_above, "Context")
    if inline_ctx:
        layers.append(PromptLayer(
            "task_context",
            "Task-specific context",
            inline_ctx,
            ref="ticket.md##Context",
            path=str(task_ref.ticket_path),
        ))

    # 6. ticket-level skills + current workflow step
    for skill_ref in ticket.skills:
        layers.extend(_skill_layers(cfg, skill_ref, slug=task_ref.id_slug))
    layers.extend(_step_layers(cfg, ticket, slug=task_ref.id_slug))

    # 7. blackboard (the single-file region below the fence)
    if blackboard_text and blackboard_text.strip():
        layers.append(PromptLayer(
            "blackboard",
            "Blackboard (current state)",
            blackboard_text,
            ref="ticket.md##blackboard",
            path=str(task_ref.ticket_path),
        ))

    # Trailing task description from ticket body
    desc = _extract_section(body_above, "Description")
    if desc:
        layers.append(PromptLayer(
            "task_description",
            "Task description",
            desc,
            ref="ticket.md##Description",
            path=str(task_ref.ticket_path),
        ))

    return PromptComposition(layers)


def write_prompt_file(prompt: str, task_ref: TargetRef, dest_dir: Path | None = None) -> Path:
    """Write the composed prompt to a temp file. Returns its path.

    Default location: /tmp/coga-<id>-<timestamp>.md per spec.
    """
    if dest_dir is None:
        dest_dir = Path(tempfile.gettempdir())
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    safe_slug = task_ref.id_slug.replace("/", "-")
    path = dest_dir / f"coga-{safe_slug}-{ts}.md"
    path.write_text(prompt)
    return path


# --- helpers ------------------------------------------------------------------


def _resource(name: str) -> str:
    return files("coga.resources").joinpath(name).read_text()


def _task_path_for_prompt(cfg: Config, task_ref: TargetRef) -> str:
    path = task_ref.path.resolve(strict=False)
    try:
        rel = path.relative_to(cfg.repo_root.resolve(strict=False))
    except ValueError:
        return str(path)
    return str(Path(cfg.repo_root.name) / rel)


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


def _skill_layers(cfg: Config, skill_ref: str, *, slug: str) -> list[PromptLayer]:
    sp = resolve_skill_path(cfg, skill_ref)
    if sp is None:
        raise ComposeError(_missing_skill_message(cfg, skill_ref, slug))
    return [PromptLayer(
        "top_level_skill",
        f"Skill: {skill_ref}",
        sp.read_text(),
        ref=skill_ref,
        path=str(sp),
    )]


def _step_layers(cfg: Config, ticket: Ticket, *, slug: str) -> list[PromptLayer]:
    current = ticket.current_step()
    if not current:
        return []

    name = current["name"]
    skill_refs = list(current.get("skills") or [])

    if skill_refs:
        out: list[PromptLayer] = []
        for skill_ref in skill_refs:
            sp = resolve_skill_path(cfg, skill_ref)
            if sp is None:
                raise ComposeError(_missing_skill_message(cfg, skill_ref, slug))
            out.append(PromptLayer(
                "workflow_skill",
                f"Current step: {name} (skill: {skill_ref})",
                sp.read_text(),
                ref=skill_ref,
                path=str(sp),
            ))
        return out

    # Inline: load workflow, pull the matching heading
    wf_name = (ticket.workflow or {}).get("name")
    if not wf_name:
        return []
    try:
        wf = Workflow.load(resolve_workflow_path(cfg, wf_name))
    except Exception:  # workflow may have been deleted after ticket was created
        wp = resolve_workflow_path(cfg, wf_name)
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
            path=str(resolve_workflow_path(cfg, wf_name)),
        )]
    return [PromptLayer(
        "workflow_inline",
        f"Current step: {name}",
        "*No instructions attached to this step.*",
        ref=wf_name,
        path=str(resolve_workflow_path(cfg, wf_name)),
    )]


def _checked_skill_paths(cfg: Config, skill_ref: str) -> str:
    return ", ".join(str(path) for path in skill_resolution_paths(cfg, skill_ref))


def _checked_context_paths(cfg: Config, ref: str) -> str:
    return ", ".join(str(path) for path in context_resolution_paths(cfg, ref))


def _missing_skill_message(cfg: Config, skill_ref: str, slug: str) -> str:
    checked = _checked_skill_paths(cfg, skill_ref)
    return (
        f"Task {slug!r} references skill {skill_ref!r}, but no skill file exists "
        f"for it. Checked: {checked}. Create one of those files or remove "
        f"{skill_ref!r} from the workflow step / ticket `skills:` list."
    )


__all__ = [
    "ComposeError",
    "PromptComposition",
    "PromptLayer",
    "compose_prompt",
    "compose_prompt_report",
    "estimate_tokens",
    "write_prompt_file",
]
