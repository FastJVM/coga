"""SKILL.md parser — YAML frontmatter + markdown body."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


@dataclass
class Skill:
    path: Path            # path to SKILL.md
    frontmatter: dict[str, Any]
    body: str

    @classmethod
    def load(cls, path: Path) -> "Skill":
        text = path.read_text()
        match = _FM_RE.match(text)
        if not match:
            raise ValueError(f"{path} must begin with YAML frontmatter")
        fm = yaml.safe_load(match.group(1)) or {}
        if not isinstance(fm, dict):
            raise ValueError(f"{path}: frontmatter must be a mapping")
        return cls(path=path, frontmatter=fm, body=match.group(2))

    @property
    def name(self) -> str:
        return self.frontmatter.get("name", self.path.parent.name)

    @property
    def script(self) -> str | None:
        return self.frontmatter.get("script")

    @property
    def dir(self) -> Path:
        return self.path.parent


__all__ = ["Skill"]
