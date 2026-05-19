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


def bootstrap_skill_path(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "bootstrap" / "skills" / ref / "SKILL.md"


def bootstrap_skill_dir(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "bootstrap" / "skills" / ref


def resolve_skill_path(cfg: Config, ref: str) -> Path | None:
    """Resolve a skill ref from local skills first, then bundled bootstrap skills."""
    local = skill_path(cfg, ref)
    if local.is_file():
        return local
    bundled = bootstrap_skill_path(cfg, ref)
    if bundled.is_file():
        return bundled
    return None


def skill_resolution_paths(cfg: Config, ref: str) -> tuple[Path, Path]:
    return (skill_path(cfg, ref), bootstrap_skill_path(cfg, ref))


def context_path(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "contexts" / ref / "SKILL.md"


def context_dir(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "contexts" / ref


def bootstrap_context_path(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "bootstrap" / "contexts" / ref / "SKILL.md"


def bootstrap_context_dir(cfg: Config, ref: str) -> Path:
    return cfg.repo_root / "bootstrap" / "contexts" / ref


def resolve_context_path(cfg: Config, ref: str) -> Path | None:
    """Resolve a context ref from local contexts first, then bundled bootstrap contexts."""
    local = context_path(cfg, ref)
    if local.is_file():
        return local
    bundled = bootstrap_context_path(cfg, ref)
    if bundled.is_file():
        return bundled
    return None


def context_resolution_paths(cfg: Config, ref: str) -> tuple[Path, Path]:
    return (context_path(cfg, ref), bootstrap_context_path(cfg, ref))


def recurring_dir(cfg: Config) -> Path:
    return cfg.repo_root / "recurring"


def repo_context_path(cfg: Config) -> Path:
    return cfg.repo_root / "context.md"


def tasks_dir(cfg: Config) -> Path:
    return cfg.repo_root / "tasks"


def task_dir(cfg: Config, id_slug: str) -> Path:
    return tasks_dir(cfg) / id_slug


def bootstrap_dir(cfg: Config) -> Path:
    return cfg.repo_root / "bootstrap"


def bootstrap_path(cfg: Config, name: str) -> Path:
    return bootstrap_dir(cfg) / name


__all__ = [
    "rules_path",
    "workflow_path",
    "skill_path",
    "skill_dir",
    "bootstrap_skill_path",
    "bootstrap_skill_dir",
    "resolve_skill_path",
    "skill_resolution_paths",
    "context_path",
    "context_dir",
    "bootstrap_context_path",
    "bootstrap_context_dir",
    "resolve_context_path",
    "context_resolution_paths",
    "recurring_dir",
    "repo_context_path",
    "tasks_dir",
    "task_dir",
    "bootstrap_dir",
    "bootstrap_path",
]
