"""Canonical paths inside a Coga repo's `coga-os/`."""

from __future__ import annotations

from pathlib import Path

from coga.config import Config


def workflow_path(cfg: Config, name: str) -> Path:
    return cfg.repo_root / "workflows" / f"{name}.md"


def bootstrap_workflow_path(cfg: Config, name: str) -> Path:
    return cfg.repo_root / "bootstrap" / "workflows" / f"{name}.md"


def resolve_workflow_path(cfg: Config, name: str) -> Path:
    """Resolve a workflow ref from local workflows first, then bundled bootstrap.

    Mirrors `resolve_skill_path` / `resolve_context_path`: a repo's own
    `workflows/<name>.md` overrides a package-backed
    `bootstrap/workflows/<name>.md`. Unlike those resolvers this returns a
    `Path` rather than `None` when neither exists — it falls back to the local
    path so a caller's `Workflow.load(...)` raises a not-found error naming the
    conventional `workflows/` location.
    """
    local = workflow_path(cfg, name)
    if local.is_file():
        return local
    bundled = bootstrap_workflow_path(cfg, name)
    if bundled.is_file():
        return bundled
    return local


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


def log_path(cfg: Config) -> Path:
    """The repo-global append-only audit log (`coga-os/log.md`).

    One file per repo, never a prompt-composition layer, marked `merge=union`
    via `coga-os/.gitattributes` so concurrent appends across branches merge
    cleanly. Each line is tagged with its task ref; see `coga.logfile`.
    """
    return cfg.repo_root / "log.md"


def tasks_dir(cfg: Config) -> Path:
    return cfg.repo_root / "tasks"


def bootstrap_dir(cfg: Config) -> Path:
    return cfg.repo_root / "bootstrap"


def bootstrap_path(cfg: Config, name: str) -> Path:
    return bootstrap_dir(cfg) / name


__all__ = [
    "workflow_path",
    "bootstrap_workflow_path",
    "resolve_workflow_path",
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
    "log_path",
    "tasks_dir",
    "bootstrap_dir",
    "bootstrap_path",
]
