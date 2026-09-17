"""Fixed, explicit registry for deterministic Coga recipes."""

from __future__ import annotations

import contextlib
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Protocol, TextIO, cast

import typer

from coga.autoclose import run_autoclose_recipe
from coga.blackboard import append_blackboard_report
from coga.blocker_reminders import run_blocker_reminders_recipe
from coga.branchsweep import run_branch_sweep_recipe
from coga.config import Config
from coga.delete_task import run_delete_task_recipe
from coga.dream_cleanup_orphan_markers import (
    run_cleanup_orphan_markers_recipe,
)
from coga.dream_validate_drift import run_validate_drift_recipe
from coga.open_pr import run_open_pr_recipe
from coga.recurring_autofix import run_autofix_analyze_recipe
from coga.recurring_runner import run_recurring_scan_recipe
from coga.skill_update import run_skill_update_recipe
from coga.task_env import blackboard_from_env
from coga.text import strip_ansi


class RecipeFn(Protocol):
    def __call__(self, cfg: Config, argv: list[str]) -> int: ...


RECIPES: dict[str, RecipeFn] = {
    "autoclose": run_autoclose_recipe,
    "blocker-reminders": run_blocker_reminders_recipe,
    "branch-sweep": run_branch_sweep_recipe,
    "validate-drift": run_validate_drift_recipe,
    "cleanup-orphan-markers": run_cleanup_orphan_markers_recipe,
    "recurring-scan": run_recurring_scan_recipe,
    "autofix-analyze": run_autofix_analyze_recipe,
    "skill-update": run_skill_update_recipe,
    "open-pr": run_open_pr_recipe,
    "delete-task": run_delete_task_recipe,
}

RECIPE_FAILURE_HEADING = "Recipe Failure"
# Matches the per-task budget the sweep's run record keeps for a blackboard
# (`recurring_autofix._MAX_BLACKBOARD_CHARS_PER_TASK`): a failure section
# longer than what the record can carry would only be truncated there.
FAILURE_DETAIL_CHARS = 4000


class UnknownRecipeError(ValueError):
    """A requested name is outside Coga's fixed recipe surface."""


class _StderrTail:
    """Pass writes through to the real stderr while keeping a bounded tail.

    Everything but `write` is delegated, so `isatty`, `fileno` and `encoding`
    still describe the underlying stream: a recipe that hands `sys.stderr` to a
    child process keeps its console, and click keeps its colour decision. A
    child's own stderr therefore bypasses the tail — the recipes wrap the
    subprocess output they care about into the exception or message they
    write themselves.
    """

    def __init__(self, stream: TextIO, limit: int = FAILURE_DETAIL_CHARS) -> None:
        self._stream = stream
        self._limit = limit
        self.tail = ""

    def write(self, text: str) -> int:
        written = self._stream.write(text)
        self.tail = (self.tail + text)[-self._limit :]
        return written

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name: str) -> object:
        return getattr(self._stream, name)


def run_recipe(cfg: Config, name: str, argv: list[str]) -> int:
    """Resolve ``name`` explicitly and forward ``argv`` without translation.

    Wrappers are called positionally, so a wrapper may add keyword-only
    parameters without affecting ``coga run``. Several use that to offer an
    optional ``result=`` out-parameter, filled in with what the run did while
    the return value stays the exit code this function reads.

    This is also the recipe layer's failure surface. The recurring sweep
    discards a `ticket.py` child's stderr and reads only the period task's
    blackboard into its run record, so a recipe that exited non-zero to stderr
    alone showed up there as a failed task with a blank blackboard and no
    reason. Every recipe crosses this function — `coga run`, and the shipped
    `ticket.py` shims — so the rule lives here once: when a recipe returns
    non-zero or lets an exception escape, the stderr it wrote (and the
    traceback, for an exception) is appended as a `## Recipe Failure` section
    to the blackboard `blackboard_from_env` resolves. Without a blackboard
    nothing extra happens — stderr already reached the console. A recipe may
    still write a richer report of its own; this is the floor, not a
    replacement. The exit code and the exception are never replaced by a
    failed write.
    """
    try:
        recipe = RECIPES[name]
    except KeyError as exc:
        known = ", ".join(sorted(RECIPES))
        raise UnknownRecipeError(
            f"unknown recipe {name!r}; known recipes: {known}"
        ) from exc
    tail = _StderrTail(sys.stderr)
    failure: tuple[int, str] | None = None
    try:
        with contextlib.redirect_stderr(cast(TextIO, tail)):
            try:
                code = recipe(cfg, list(argv))
            except (Exception, SystemExit) as exc:
                exit_code = _escaping_exit_code(exc)
                if exit_code is not None:
                    failure = (exit_code, "".join(traceback.format_exception(exc)))
                raise
        if code:
            failure = (code, "")
        return code
    finally:
        # Outside the redirect, so a write refusal or warning reaches the real
        # stderr rather than the tail it is reporting on.
        if failure is not None:
            _record_failure(cfg, name, failure[0], stderr=tail.tail, detail=failure[1])


def _escaping_exit_code(exc: BaseException) -> int | None:
    """The process exit an escaping exception produces, or None for a clean exit.

    `SystemExit` is how argparse refuses argv; `typer.Exit` is how a nested
    command refuses. Both can carry zero, which is a return, not a failure.
    Anything else the interpreter turns into a traceback and exit 1.
    """
    if isinstance(exc, SystemExit):
        code = exc.code
        if code is None or code == 0:
            return None
        return code if isinstance(code, int) else 1
    if isinstance(exc, typer.Exit):
        return exc.exit_code or None
    return 1


def _record_failure(
    cfg: Config, name: str, exit_code: int, *, stderr: str, detail: str
) -> None:
    if not os.environ.get("COGA_TASK_BLACKBOARD"):
        return
    root = getattr(cfg, "repo_root", None)
    if root is None:
        return
    blackboard = blackboard_from_env(root)
    if blackboard is None:
        return
    report = render_failure_section(
        name,
        exit_code,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        task_slug=os.environ.get("COGA_TASK_SLUG"),
        stderr=stderr,
        detail=detail,
    )
    try:
        append_blackboard_report(cfg, blackboard, report)
    except Exception as write_exc:  # never outrank the recipe's own failure
        sys.stderr.write(
            f"Warning: could not record the {name} failure on {blackboard}: "
            f"{write_exc}\n"
        )


def render_failure_section(
    name: str,
    exit_code: int,
    *,
    generated_at: str,
    task_slug: str | None,
    stderr: str,
    detail: str = "",
) -> str:
    """Render the `## Recipe Failure` section for one failed recipe run."""
    lines = [f"## {RECIPE_FAILURE_HEADING}", ""]
    lines.append(f"Recipe: `{name}`")
    lines.append(f"Exit: {exit_code}")
    if task_slug:
        lines.append(f"Task: `{task_slug}`")
    lines.append(f"Recorded: {generated_at}")
    lines.append("")
    parts = [strip_ansi(part).strip() for part in (stderr, detail)]
    body = "\n\n".join(part for part in parts if part)
    if len(body) > FAILURE_DETAIL_CHARS:
        body = "…" + body[-FAILURE_DETAIL_CHARS:]
    lines.append("```")
    lines.append(body or "no stderr output")
    lines.append("```")
    return "\n".join(lines) + "\n"
