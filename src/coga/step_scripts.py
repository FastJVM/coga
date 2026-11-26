"""Workflow-declared step scripts: `enter` at step start, `exit` on step change.

A workflow may name two skill refs at top level (`enter:` / `exit:`). The
kernel runs the `enter` skill's `run.py` before a launched step executes and
the `exit` skill's `run.py` after every lifecycle write that changes the step
(`coga bump`, `coga mark done|canceled`, `coga block`). The kernel stays
Git-free: it resolves the ref local-first, copies the skill into a tmp scope
(so a branch switch cannot change the code mid-run), and runs it with the
ticket and tmp environment and no secrets. All Git work lives in the scripts.
"""

from __future__ import annotations

import sys
from typing import Any

import typer

from coga import run_state
from coga.config import Config, ConfigError
from coga.launch_script import prepare_launch_hook, run_launch_hook
from coga.run_state import TmpScope
from coga.tasks import TaskRef
from coga.ticket import TicketError
from coga.workflow import WorkflowError, step_script


# A failed `exit` leaves this record in the ticket's durable data dir, so a
# supervising launch (or megalaunch) stops instead of starting the next step
# on an unpublished state. The next successful `exit` removes it.
EXIT_FAILED_FILE = "step-exit-failed"


class StepScriptError(Exception):
    """A step script could not be resolved or did not exit 0."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def step_script_ref(cfg: Config, workflow: Any, key: str) -> str | None:
    """The ticket workflow's `enter`/`exit` ref, or None when it names none."""
    try:
        return step_script(workflow, cfg, key)
    except WorkflowError as exc:
        raise StepScriptError(f"workflow `{key}`: {exc}", code=2) from exc


def run_step_script(
    cfg: Config, ref: TaskRef, workflow: Any, key: str,
    tmp_scope: TmpScope | None = None,
) -> bool:
    """Run the workflow's `key` script for `ref`; return whether one ran.

    Without a `tmp_scope` the run opens (and removes) its own scope, as a
    nested launch does. Raises `StepScriptError` on a resolution failure or a
    non-zero exit; the caller decides how loud to be.
    """
    if not isinstance(ref, TaskRef):
        return False
    skill = step_script_ref(cfg, workflow, key)
    if skill is None:
        return False
    if tmp_scope is None:
        with run_state.launch_tmp_scope(cfg, sweep=False) as scope:
            _run(cfg, ref, skill, key, scope)
    else:
        _run(cfg, ref, skill, key, tmp_scope)
    return True


def _run(cfg: Config, ref: TaskRef, skill: str, key: str, scope: TmpScope) -> None:
    try:
        script = prepare_launch_hook(cfg, skill, scope)
    except (ConfigError, OSError) as exc:
        raise StepScriptError(f"{key} script {skill!r}: {exc}") from exc
    try:
        code = run_launch_hook(cfg, ref, script, scope)
    except (OSError, TicketError, UnicodeError) as exc:
        raise StepScriptError(f"cannot run {key} script {skill!r}: {exc}") from exc
    if code != 0:
        raise StepScriptError(f"{key} script {skill!r} failed (exit {code})", code=code)


def run_enter_before_step(
    cfg: Config, ref: TaskRef, workflow: Any, tmp_scope: TmpScope | None,
) -> bool:
    """Run the `enter` script before a launched step executes.

    Returns whether a script ran, so the caller re-reads the ticket from the
    (possibly switched) checkout. Raises `StepScriptError` on failure; the
    step must not start.
    """
    return run_step_script(cfg, ref, workflow, "enter", tmp_scope)


def run_exit_after_transition(cfg: Config, ref: TaskRef, workflow: Any) -> int:
    """Run the `exit` script after a step-changing write; return an exit code.

    The lifecycle write already landed locally, so a failure is reported, not
    rolled back: the command exits non-zero and the checkout stays where the
    script stopped.
    """
    record = run_state.task_data_dir(cfg, ref) / EXIT_FAILED_FILE
    try:
        ran = run_step_script(cfg, ref, workflow, "exit")
    except StepScriptError as exc:
        message = (
            f"{ref.id_slug}: {exc}. The transition was written locally; the "
            "checkout was left where the script stopped. Fix it by hand."
        )
        typer.secho(message, fg=typer.colors.RED, err=True)
        try:
            run_state.ensure_task_data_dir(cfg, ref)
            record.write_text(message + "\n", encoding="utf-8")
        except OSError as error:
            typer.secho(f"{ref.id_slug}: cannot record the failure: {error}",
                        fg=typer.colors.RED, err=True)
        return exc.code or 1
    if ran:
        record.unlink(missing_ok=True)
    return 0


def exit_failure(cfg: Config, ref: Any) -> str | None:
    """The recorded failure of this ticket's last `exit` script, if any."""
    if not isinstance(ref, TaskRef):
        return None
    try:
        return (run_state.task_data_dir(cfg, ref) / EXIT_FAILED_FILE).read_text(
            encoding="utf-8"
        ).strip() or "exit script failed"
    except OSError:
        return None


def finish_transition(code: int) -> None:
    """Exit non-zero after the done marker when the `exit` script failed."""
    if code:
        sys.stdout.flush()
        sys.exit(code)


__all__ = [
    "EXIT_FAILED_FILE",
    "StepScriptError",
    "exit_failure",
    "finish_transition",
    "run_enter_before_step",
    "run_exit_after_transition",
    "run_step_script",
    "step_script_ref",
]
