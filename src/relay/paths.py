"""Canonical paths inside a Relay repo and inside a project's relay-os/."""

from __future__ import annotations

from pathlib import Path

from relay.config import Config


# --- company repo (where relay.toml lives) -------------------------------------


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


# --- per-project relay-os/ -----------------------------------------------------


def project_relay_dir(cfg: Config, project_name: str) -> Path:
    proj = cfg.project(project_name)
    if proj.path is None:
        raise ValueError(
            f"Project {project_name!r} has no path configured. "
            "Add it under [paths] in relay.local.toml."
        )
    return proj.path / "relay-os"


def project_tasks_dir(cfg: Config, project_name: str) -> Path:
    return project_relay_dir(cfg, project_name) / "tasks"


def project_context_path(cfg: Config, project_name: str) -> Path:
    return project_relay_dir(cfg, project_name) / "context.md"


def task_dir(cfg: Config, project_name: str, id_slug: str) -> Path:
    return project_tasks_dir(cfg, project_name) / id_slug


__all__ = [
    "rules_path",
    "workflow_path",
    "skill_path",
    "skill_dir",
    "context_path",
    "recurring_dir",
    "project_relay_dir",
    "project_tasks_dir",
    "project_context_path",
    "task_dir",
]
