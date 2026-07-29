"""Task metadata shared by agent and recipe execution."""

from __future__ import annotations

from pathlib import Path

from coga.config import Config
from coga.paths import log_path
from coga.tasks import TargetRef


def host_repo_root(cfg: Config) -> Path:
    """Return the host repository containing the configured Coga OS root."""
    return cfg.repo_root.parent if cfg.repo_root.name == "coga" else cfg.repo_root


def build_task_env(cfg: Config, ref: TargetRef) -> dict[str, str]:
    """Build the task metadata environment contract."""
    return {
        "COGA_TASK_SLUG": ref.id_slug,
        "COGA_TASK_DIR": str((ref.task_dir or ref.path.parent).resolve()),
        "COGA_TASK_TICKET": str(ref.ticket_path.resolve()),
        # The blackboard is the final region of the single ticket file.
        "COGA_TASK_BLACKBOARD": str(ref.ticket_path.resolve()),
        "COGA_TASK_LOG": str(log_path(cfg).resolve()),
        "COGA_COGA_OS_ROOT": str(cfg.repo_root.resolve()),
        "COGA_REPO_ROOT": str(host_repo_root(cfg).resolve()),
    }
