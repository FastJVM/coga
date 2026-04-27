"""Canonical paths inside a Relay repo's `relay-os/`."""

from __future__ import annotations

from pathlib import Path

from relay.config import Config


def rules_path(cfg: Config) -> Path:
    return cfg.repo_root / "rules.md"


def workflow_path(cfg: Config, name: str) -> Path:
    return cfg.repo_root / "workflows" / f"{name}.md"


def skill_path(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "skills" / ref / "SKILL.md"


def skill_dir(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "skills" / ref


def context_path(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "contexts" / ref / "SKILL.md"


def recurring_dir(cfg: Config) -> Path:
    return cfg.repo_root / "recurring"


def repo_context_path(cfg: Config) -> Path:
    return cfg.repo_root / "context.md"


def tasks_dir(cfg: Config) -> Path:
    return cfg.repo_root / "tasks"


def task_dir(cfg: Config, id_slug: str) -> Path:
    return tasks_dir(cfg) / id_slug


__all__ = [
    "rules_path",
    "workflow_path",
    "skill_path",
    "skill_dir",
    "context_path",
    "recurring_dir",
    "repo_context_path",
    "tasks_dir",
    "task_dir",
]
