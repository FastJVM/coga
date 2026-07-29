"""Task metadata shared by agent and recipe execution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from coga.config import Config, ConfigError, find_repo_root
from coga.paths import log_path
from coga.tasks import BootstrapRef, TargetRef

# Every variable `build_task_env` owns. The namespace is cleared before it is
# rewritten (see `apply_task_env`) so no member can survive by inheritance.
TASK_ENV_KEYS = (
    "COGA_TASK_SLUG",
    "COGA_TASK_DIR",
    "COGA_TASK_TICKET",
    "COGA_TASK_BLACKBOARD",
    "COGA_TASK_LOG",
    "COGA_COGA_OS_ROOT",
    "COGA_REPO_ROOT",
)


def host_repo_root(cfg: Config) -> Path:
    """Return the host repository containing the configured Coga OS root."""
    return cfg.repo_root.parent if cfg.repo_root.name == "coga" else cfg.repo_root


def build_task_env(cfg: Config, ref: TargetRef) -> dict[str, str]:
    """Build the task metadata environment contract.

    `COGA_TASK_BLACKBOARD` is emitted only for a task under `coga/tasks/`.
    A bootstrap ticket is stateless — no status, no workflow, no blackboard —
    and its `ticket.md` is normally a *packaged* resource, so handing that path
    to a report writer makes it append run reports into a file that ships in
    the wheel (a repo-local `coga/bootstrap/<name>/ticket.md` override is
    corrupted the same way). Stateless targets get no blackboard; recipes
    already fall back to stdout when the variable is absent.
    """
    env = {
        "COGA_TASK_SLUG": ref.id_slug,
        "COGA_TASK_DIR": str((ref.task_dir or ref.path.parent).resolve()),
        "COGA_TASK_TICKET": str(ref.ticket_path.resolve()),
        "COGA_TASK_LOG": str(log_path(cfg).resolve()),
        "COGA_COGA_OS_ROOT": str(cfg.repo_root.resolve()),
        "COGA_REPO_ROOT": str(host_repo_root(cfg).resolve()),
    }
    if not isinstance(ref, BootstrapRef):
        # The blackboard is the final region of the single ticket file.
        env["COGA_TASK_BLACKBOARD"] = str(ref.ticket_path.resolve())
    return env


def apply_task_env(env: dict[str, str], cfg: Config, ref: TargetRef) -> dict[str, str]:
    """Return a copy of `env` with the task metadata namespace rewritten for `ref`.

    Clearing the namespace first is what makes the contract absolute: a
    stateless bootstrap target emits no `COGA_TASK_BLACKBOARD`, and a plain
    `update` would leave an outer session's inherited value in place — which is
    exactly the packaged-resource path this refuses to hand out.
    """
    updated = dict(env)
    for key in TASK_ENV_KEYS:
        updated.pop(key, None)
    updated.update(build_task_env(cfg, ref))
    return updated


def discover_coga_os_root(cwd: Path | None) -> Path | None:
    """The Coga OS root a recipe run from `cwd` operates on, or `None`.

    `None` means "cannot tell" — there is no `coga.toml` to discover, as in a
    unit test driving a recipe against a bare tmp dir. Callers hand the result
    to `blackboard_from_env`, which fails closed rather than guessing that an
    inherited blackboard belongs to the target.
    """
    try:
        return find_repo_root(cwd)
    except ConfigError:
        return None


def blackboard_from_env(coga_os_root: Path | None) -> Path | None:
    """The blackboard a recipe should append its report to, or `None`.

    `None` means "write the report to stdout" — the caller's existing
    no-blackboard path. Beyond the variable simply being unset, two shapes are
    refused, because a recipe can inherit a stale value from an outer process
    (a bootstrap session predating this contract, a test harness):

    - A path outside a `tasks/` tree: there the inherited ticket path is a
      packaged resource rather than a task blackboard.
    - A path outside the discovered root's `tasks/` tree: the report belongs to
      the repo the recipe is *operating on*, and a blackboard in another
      checkout is by definition not this run's. That is the shape a `pytest`
      run inside `coga launch` produces — the recipe validates a fixture repo
      under `/tmp` while the inherited blackboard points at the live outer
      ticket, which satisfies the `tasks/` check on its own.
    - A path whose target root cannot be discovered: without a root there is no
      safe containment judgment, so the report falls back to stdout.

    Defence in depth for the same class as `build_task_env`'s bootstrap
    carve-out, on the reading side. The autouse env guard in
    `tests/conftest.py` is the other half; neither is meant to be the only one.
    """
    value = os.environ.get("COGA_TASK_BLACKBOARD")
    if not value:
        return None
    path = Path(value)
    resolved = path.resolve()
    if "tasks" not in resolved.parts[:-1]:
        _refuse_blackboard(path, "outside a tasks/ tree")
        return None
    if coga_os_root is None:
        _refuse_blackboard(
            path, "because the target Coga root could not be discovered"
        )
        return None
    tasks_root = (coga_os_root / "tasks").resolve()
    if not resolved.is_relative_to(tasks_root):
        _refuse_blackboard(path, f"outside {tasks_root}")
        return None
    return path


def _refuse_blackboard(path: Path, reason: str) -> None:
    print(
        f"Warning: ignoring COGA_TASK_BLACKBOARD {reason}: "
        f"{path} — writing the report to stdout instead.",
        file=sys.stderr,
    )
