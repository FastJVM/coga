"""ticket.md — YAML frontmatter + markdown body."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class TicketError(Exception):
    """Raised on malformed ticket files."""


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


@dataclass
class Ticket:
    frontmatter: dict[str, Any]
    body: str

    # --- parsing / rendering ---------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> "Ticket":
        match = _FM_RE.match(text)
        if not match:
            raise TicketError("ticket.md must begin with YAML frontmatter between --- lines")
        fm_text, body = match.group(1), match.group(2)
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as exc:
            raise TicketError(f"Invalid YAML frontmatter: {exc}") from exc
        if not isinstance(fm, dict):
            raise TicketError("Frontmatter must be a YAML mapping")
        return cls(frontmatter=fm, body=body)

    def render(self) -> str:
        fm = yaml.safe_dump(
            self.frontmatter,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).rstrip()
        body = self.body.lstrip("\n")
        return f"---\n{fm}\n---\n\n{body}" if body else f"---\n{fm}\n---\n"

    # --- io --------------------------------------------------------------------

    @classmethod
    def read(cls, path: Path) -> "Ticket":
        return cls.parse(path.read_text())

    def write(self, path: Path) -> None:
        path.write_text(self.render())

    # --- helpers ---------------------------------------------------------------

    @property
    def title(self) -> str:
        return self.frontmatter.get("title", "")

    @property
    def status(self) -> str:
        return self.frontmatter.get("status", "")

    @property
    def mode(self) -> str:
        return self.frontmatter.get("mode", "interactive")

    @property
    def owner(self) -> str | None:
        return self.frontmatter.get("owner")

    @property
    def assignee(self) -> str | None:
        return self.frontmatter.get("assignee")

    @property
    def contexts(self) -> list[str]:
        value = self.frontmatter.get("contexts") or []
        return list(value)

    @property
    def workflow(self) -> dict[str, Any] | None:
        return self.frontmatter.get("workflow")

    @property
    def step(self) -> str | None:
        return self.frontmatter.get("step")

    @property
    def skill(self) -> str | None:
        """Top-level skill ref for bootstrap tickets that aren't workflow-bound."""
        return self.frontmatter.get("skill")

    def step_index(self) -> int | None:
        """Return 1-indexed step number, or None if no workflow."""
        step = self.step
        if not step:
            return None
        # Format: "N (step-name)"
        match = re.match(r"(\d+)\s*\(", step)
        return int(match.group(1)) if match else None

    def current_step(self) -> dict[str, Any] | None:
        """Return the current workflow step dict, or None."""
        wf = self.workflow
        idx = self.step_index()
        if not wf or idx is None:
            return None
        steps = wf.get("steps", [])
        if 1 <= idx <= len(steps):
            return steps[idx - 1]
        return None


__all__ = ["Ticket", "TicketError"]
