"""Fixed, explicit registry for deterministic Coga recipes."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import traceback
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, TextIO, cast

import typer

from coga.blackboard import append_blackboard_report
from coga.config import Config, load_config
from coga.delete_task import run_delete_task_recipe
from coga.recurring_autofix import run_autofix_analyze_recipe
from coga.recurring_runner import run_recurring_scan_recipe
from coga.task_env import (
    SCRIPT_TASK_ENV,
    RootResolver,
    blackboard_from_env,
    is_script_task,
)
from coga.tasks import DuplicateTaskSlugError, TaskNotFoundError, resolve_task
from coga.text import strip_ansi


class RecipeFn(Protocol):
    def __call__(self, cfg: Config, argv: list[str]) -> int: ...


RECIPES: dict[str, RecipeFn] = {
    "recurring-scan": run_recurring_scan_recipe,
    "autofix-analyze": run_autofix_analyze_recipe,
    "delete-task": run_delete_task_recipe,
}

# Registered workers whose operating root is not the invoking config's: each
# owner supplies its resolver, as an edge worker passes its own to
# `run_reported`. An entry leaves with its job.
RECIPE_ROOTS: dict[str, RootResolver] = {
}

RECIPE_FAILURE_HEADING = "Recipe Failure"
# Matches the per-task budget the sweep's run record keeps for a blackboard
# (`recurring_autofix._MAX_BLACKBOARD_CHARS_PER_TASK`). Budget the whole
# section so a long diagnostic cannot evict its recipe/exit/task header.
FAILURE_REPORT_CHARS = 4000


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

    def __init__(self, stream: TextIO, limit: int = FAILURE_REPORT_CHARS) -> None:
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
    return run_reported(cfg, name, recipe, argv, root=RECIPE_ROOTS.get(name))


def run_reported(
    cfg: Config,
    name: str,
    recipe: RecipeFn,
    argv: list[str],
    *,
    root: RootResolver | None = None,
) -> int:
    """Run ``recipe`` under the `## Recipe Failure` floor that `run_recipe` gives.

    Shared by the registry and by ticket-owned `ticket.py` code that keeps its
    deterministic work at the edge instead of in `RECIPES`: ``name`` labels the
    failure section, and ``recipe`` need not be registered. ``root`` selects
    the Coga OS root the worker operates on from its argv (default: the
    invoking config's); the report goes only to a blackboard inside that root,
    and nowhere when it returns `None`.
    """
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
            _record_failure(
                cfg, name, argv, failure[0], root,
                stderr=tail.tail, detail=failure[1],
            )


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


def _invoking_root(cfg: Config, argv: list[str]) -> Path | None:
    return cfg.repo_root


def _record_failure(
    cfg: Config,
    name: str,
    argv: list[str],
    exit_code: int,
    resolver: RootResolver | None,
    *,
    stderr: str,
    detail: str,
) -> None:
    target = os.environ.get("COGA_TASK_BLACKBOARD")
    if not target:
        return
    try:
        root = (resolver or _invoking_root)(cfg, argv)
        blackboard = blackboard_from_env(root)
        if root is None or blackboard is None:
            return
        report = render_failure_section(
            name,
            exit_code,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            task_slug=os.environ.get("COGA_TASK_SLUG"),
            stderr=stderr,
            detail=detail,
        )
        # Use the root that owns the report, including when --cwd selects it.
        append_blackboard_report(replace(cfg, repo_root=root), blackboard, report)
    except Exception as write_exc:  # never outrank the recipe's own failure
        sys.stderr.write(
            f"Warning: could not record the {name} failure on {target}: "
            f"{write_exc}\n"
        )


def run_entry(
    name: str,
    worker: RecipeFn,
    argv: list[str],
    *,
    root: RootResolver | None = None,
    scheduled: bool = False,
    cfg: Config | None = None,
) -> int:
    """Run and report the worker, then bump a successful scheduled step."""
    cfg = cfg if cfg is not None else load_config()
    code = run_reported(cfg, name, worker, argv, root=root)
    if code or not scheduled:
        return code
    return _bump_script_task(cfg, name)


def _bump_script_task(cfg: Config, name: str) -> int:
    slug = os.environ.get("COGA_TASK_SLUG")
    if not os.environ.get(SCRIPT_TASK_ENV) or not slug:
        # Run by hand: no launched script step to complete.
        return 0
    try:
        ref = resolve_task(cfg, slug)
    except (TaskNotFoundError, DuplicateTaskSlugError) as exc:
        sys.stderr.write(f"{name}: cannot complete script task {slug!r}: {exc}\n")
        return 1
    if not is_script_task(ref):
        sys.stderr.write(
            f"{name}: {SCRIPT_TASK_ENV} does not name task {slug!r}; "
            "refusing to advance an inherited task\n"
        )
        return 1
    return _bump(slug)


def _bump(slug: str) -> int:
    # Complete the step through the CLI: calling a Typer command function
    # in-process would pass `OptionInfo` sentinels instead of real defaults.
    return subprocess.run(
        [sys.executable, "-m", "coga.cli", "bump", slug], check=False
    ).returncode


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
    # A fenced code block does not protect an own-line blackboard separator
    # (or a ## heading) from Coga's structural readers. Indentation does, and
    # also makes embedded Markdown fences harmless when a human reads it.
    body = "\n".join("    " + line for line in (body or "no stderr output").splitlines())
    header = "\n".join(lines) + "\n"
    available = FAILURE_REPORT_CHARS - len(header) - 1
    if len(body) > available:
        body = "    …" + body[-(available - 5):]
    return header + body + "\n"
