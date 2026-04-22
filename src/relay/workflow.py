"""Workflow definitions — parsed from markdown files under relay-os/workflows/."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class WorkflowError(Exception):
    """Raised on invalid workflow definitions."""


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    skill: str | None = None


@dataclass
class Workflow:
    name: str
    description: str
    steps: list[WorkflowStep] = field(default_factory=list)
    body: str = ""
    # step name -> markdown section body (used when step has no skill ref)
    inline_instructions: dict[str, str] = field(default_factory=dict)

    # --- io --------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "Workflow":
        if not path.is_file():
            raise WorkflowError(f"Workflow not found: {path}")
        text = path.read_text()
        match = _FM_RE.match(text)
        if not match:
            raise WorkflowError(f"{path} must begin with YAML frontmatter")
        fm_text, body = match.group(1), match.group(2)
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as exc:
            raise WorkflowError(f"{path}: invalid YAML frontmatter: {exc}") from exc
        if "name" not in fm:
            raise WorkflowError(f"{path}: missing `name` in frontmatter")
        if "steps" not in fm or not isinstance(fm["steps"], list) or not fm["steps"]:
            raise WorkflowError(f"{path}: `steps` must be a non-empty list")

        steps = [_parse_step(s, path) for s in fm["steps"]]
        inline = _parse_inline_sections(body, {s.name for s in steps})

        return cls(
            name=fm["name"],
            description=fm.get("description", ""),
            steps=steps,
            body=body,
            inline_instructions=inline,
        )

    # --- freezing --------------------------------------------------------------

    def freeze(self) -> dict[str, Any]:
        """Snapshot suitable for ticket frontmatter."""
        out: dict[str, Any] = {
            "name": self.name,
            "steps": [],
        }
        for step in self.steps:
            entry: dict[str, Any] = {"name": step.name}
            if step.skill:
                entry["skill"] = step.skill
            out["steps"].append(entry)
        return out


# --- helpers ------------------------------------------------------------------


def _parse_step(raw: Any, source: Path) -> WorkflowStep:
    if not isinstance(raw, dict) or "name" not in raw:
        raise WorkflowError(f"{source}: step must be a mapping with a `name` field, got {raw!r}")
    return WorkflowStep(name=raw["name"], skill=raw.get("skill"))


def _parse_inline_sections(body: str, step_names: set[str]) -> dict[str, str]:
    """Split the markdown body by `## <heading>` into sections keyed by heading text.

    Only returns sections whose heading matches a step name.
    """
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        return {}
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        if heading in step_names:
            sections[heading] = body[start:end].strip()
    return sections


__all__ = ["Workflow", "WorkflowStep", "WorkflowError"]
