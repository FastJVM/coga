"""Fixed, explicit registry for deterministic Coga recipes."""

from __future__ import annotations

from typing import Protocol

from coga.autoclose import run_autoclose_recipe
from coga.blocker_reminders import run_blocker_reminders_recipe
from coga.branchsweep import run_branch_sweep_recipe
from coga.commands.digest import run_digest_recipe
from coga.config import Config
from coga.dream_cleanup_orphan_markers import (
    run_cleanup_orphan_markers_recipe,
)
from coga.dream_validate_drift import run_validate_drift_recipe
from coga.recurring_runner import run_recurring_scan_recipe
from coga.skill_update import run_skill_update_recipe


class RecipeFn(Protocol):
    def __call__(self, cfg: Config, argv: list[str]) -> int: ...


RECIPES: dict[str, RecipeFn] = {
    "autoclose": run_autoclose_recipe,
    "digest": run_digest_recipe,
    "blocker-reminders": run_blocker_reminders_recipe,
    "branch-sweep": run_branch_sweep_recipe,
    "validate-drift": run_validate_drift_recipe,
    "cleanup-orphan-markers": run_cleanup_orphan_markers_recipe,
    "recurring-scan": run_recurring_scan_recipe,
    "skill-update": run_skill_update_recipe,
}


class UnknownRecipeError(ValueError):
    """A requested name is outside Coga's fixed recipe surface."""


def run_recipe(cfg: Config, name: str, argv: list[str]) -> int:
    """Resolve ``name`` explicitly and forward ``argv`` without translation."""
    try:
        recipe = RECIPES[name]
    except KeyError as exc:
        known = ", ".join(sorted(RECIPES))
        raise UnknownRecipeError(
            f"unknown recipe {name!r}; known recipes: {known}"
        ) from exc
    return recipe(cfg, list(argv))
