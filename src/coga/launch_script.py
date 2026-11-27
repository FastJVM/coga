"""Deterministic ``ticket.py`` launch phase.

A directory-form ticket owns a deterministic half when ``ticket.py`` sits
beside ``ticket.md``.  The fixed name is the whole classifier: Coga does not
scan for plugins, import ticket code, or consult frontmatter to select a mode.
"""

from __future__ import annotations

import subprocess
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Sequence

import typer

from coga.bump import OperatorResolutionError, effective_step_role, resolve_operator
from coga.config import (
    Config,
    ConfigError,
    build_launch_env,
    find_repo_root,
    load_config,
    step_script_env,
)
from coga.logfile import append_log
from coga.lifecycle import TERMINAL_STATUSES
from coga.paths import bootstrap_skill_dir, resolve_workflow_path, skill_dir
from coga.workflow import Workflow
from coga.notification import post
from coga.repl_supervisor import (
    EXPECTED_AGENT_ENV,
    EXPECTED_STEP_ENV,
    EXPECTED_TASK_ENV,
    SENTINEL_ENV,
)
from coga.run_state import (
    DATA_DIR_ENV,
    TASK_DATA_DIR_ENV,
    TmpScope,
    apply_tmp_env,
    ensure_task_data_dir,
)
from coga.task_env import TASK_ENV_KEYS, SCRIPT_TASK_ENV, apply_task_env, host_repo_root
from coga.process_relay import run_foreground_child
from coga.tasks import (
    BootstrapRef,
    TargetRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_target,
)
from coga.ticket import Ticket, TicketError


SCRIPT_ENTRY_POINT = "ticket.py"


@dataclass(frozen=True)
class ScriptPhaseResult:
    """The child exit and task state observed after one deterministic phase."""

    exit_code: int
    ticket: Ticket | None
    ran: bool = True
    cfg: Config | None = None
    ref: TargetRef | None = None


class ScriptChainResult(NamedTuple):
    """Result of consecutive deterministic steps before an agent handoff."""

    exit_code: int
    ticket: Ticket | None
    needs_agent: bool
    stop_reason: str | None
    cfg: Config | None = None
    ref: TargetRef | None = None


def resolve_step_script(cfg: Config, run: str) -> Path:
    """Resolve and check the selected skill's script."""
    if any(part in {"", ".", ".."} for part in run.split("/")) or "\\" in run or ":" in run:
        raise ConfigError(f"Invalid workflow script ref {run!r}")
    local = skill_dir(cfg, run)
    directory = local if local.exists() or local.is_symlink() else bootstrap_skill_dir(cfg, run)
    candidate = directory / "run.py"
    try:
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        with candidate.open("rb"):
            pass
    except OSError as exc:
        raise FileNotFoundError(f"Cannot read workflow script {candidate}: {exc}") from exc
    return candidate


def script_entry_point(
    ref: TargetRef, ticket: Ticket | None = None, *, cfg: Config | None = None,
) -> Path | None:
    """Resolve the current workflow script, falling back to the ticket script."""
    if ticket is not None and isinstance(ref, TaskRef):
        step = ticket.current_step()
        if cfg is None:
            cfg = load_config(find_repo_root(ref.ticket_path.parent), require_user=False)
        if step is None and ticket.status in {"draft", "paused"}:
            workflow = ticket.workflow
            if isinstance(workflow, str):
                workflow = Workflow.load(resolve_workflow_path(cfg, workflow)).freeze()
            if isinstance(workflow, dict) and workflow.get("steps"):
                steps = workflow["steps"]
                step = steps[0]
                index = 1
            else:
                index = None
        else:
            workflow = ticket.workflow
            index = ticket.step_index()
        if isinstance(step, dict) and step.get("run") is not None:
            run = step["run"]
            if not isinstance(run, str) or not run.strip():
                raise ConfigError(f"{ref.id_slug}: workflow run must be a skill ref")
            if effective_step_role(workflow["steps"], index) == "owner":
                raise ConfigError(f"{ref.id_slug}: an owner step cannot declare run")
            return resolve_step_script(cfg, run)

    task_dir = ref.task_dir
    if task_dir is None:
        return None
    candidate = task_dir / SCRIPT_ENTRY_POINT
    return candidate if candidate.is_file() else None


def _normalize_exit_code(returncode: int) -> int:
    """Map a signal-killed child's POSIX ``-N`` to the shell's ``128 + N``.

    Non-negative codes pass through unchanged.
    """

    return 128 - returncode if returncode < 0 else returncode


def run_script_phase(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    *,
    stateless: bool,
    read_only: bool = False,
    args: Sequence[str] = (),
    failure_important: bool = False,
    tmp_scope: TmpScope | None = None,
) -> ScriptPhaseResult:
    """Execute one deterministic phase with the current ticket environment.

    `tmp_scope` is the caller's open launch tmp scope; with it the phase gets
    the repo-local TMPDIR and an existing task data directory. Read-only
    dispatch gets the temp redirection but no durable data variables.
    """
    if read_only and (not stateless or not isinstance(ref, BootstrapRef)):
        raise ValueError("Read-only dispatch requires a stateless bootstrap script.")
    if not stateless and ticket.status == "blocked":
        raise ValueError(f"{ref.id_slug}: answer with `coga unblock --answer` before running a script")

    entry = script_entry_point(ref, ticket, cfg=cfg)
    if entry is None:
        if read_only:
            raise FileNotFoundError(f"Read-only script entry disappeared: {ref.id_slug}/ticket.py")
        if stateless:
            raise FileNotFoundError(f"Classified bootstrap script disappeared: {ref.id_slug}/ticket.py")
        # Classification is a point-in-time observation. Activation, a prior
        # deterministic phase, or another checkout may have removed the fixed
        # entry before this phase began. Reclassify as agent-only instead of
        # turning the stale stat into a launch failure.
        return ScriptPhaseResult(
            exit_code=0,
            ticket=ticket,
            ran=False,
            cfg=cfg,
            ref=ref,
        )

    env = build_launch_env(cfg, ticket.secrets)

    if not stateless and not isinstance(ref, TaskRef):
        raise ValueError(
            f"Stateful script phase requires a task target, got {ref.id_slug}."
        )
    if args and not stateless:
        # Launch refuses this before any effect; reaching here is a caller bug.
        raise ValueError(
            f"Stateful script phase for {ref.id_slug} takes no launch arguments."
        )

    if not stateless and ticket.status == "active":
        # Local import keeps the pure classifier importable by coga.validate;
        # coga.mark itself imports the validator for transition checks.
        from coga.mark import mark_in_progress

        current = ticket.current_step()
        step_note = (
            f" (step {ticket.step_index()}: {current['name']})"
            if current is not None
            else ""
        )
        mark_in_progress(
            cfg,
            ref,
            ticket,
            actor="system",
            log_message="started (active → in_progress) via coga launch",
            slack_text=(
                f"▶️ script started *{ref.id_slug}* "
                f"\"{ticket.title}\"{step_note}"
            ),
            echo=f"{ref.id_slug}: in_progress",
        )

    if not stateless:
        append_log(cfg, ref.id_slug, "system", f"launched as a script ({entry.name})")

    env.pop("COGA_SCRIPT_HELP", None)
    env = apply_task_env(env, cfg, ref, ticket)
    env.pop("COGA_SUPERVISED", None)
    env[SENTINEL_ENV] = ""
    env.pop(EXPECTED_TASK_ENV, None)
    env.pop(EXPECTED_STEP_ENV, None)
    env.pop(EXPECTED_AGENT_ENV, None)
    env[SCRIPT_TASK_ENV] = str(ref.path.resolve())
    if read_only:
        env.pop(DATA_DIR_ENV, None)
        env.pop(TASK_DATA_DIR_ENV, None)
    elif tmp_scope is not None:
        ensure_task_data_dir(cfg, ref)
    env = apply_tmp_env(env, tmp_scope)

    if stateless and not read_only:
        exit_code, _ = run_foreground_child(
            [sys.executable, str(entry), *args], cwd=host_repo_root(cfg),
            env=env, defer_interrupt=True,
        )
    else:
        completed = subprocess.run(
            [sys.executable, str(entry), *args], cwd=host_repo_root(cfg),
            env=env, check=False,
        )
        # Normalize before any return so every consumer (the shell, the
        # audit line, the failure notice, LaunchBail) sees one status.
        exit_code = _normalize_exit_code(completed.returncode)

    if read_only:
        # No teardown reload, lifecycle inspection, notification or agent fallback.
        return ScriptPhaseResult(exit_code=exit_code, ticket=ticket, cfg=cfg, ref=ref)

    after: Ticket | None = None
    ticket_read_error: Exception | None = None
    if ref.ticket_path.exists():
        try:
            after = Ticket.read(ref.ticket_path)
        except (OSError, UnicodeError, TicketError) as exc:
            ticket_read_error = exc
    if not stateless:
        # The audit belongs to the launch, not to the continued existence or
        # parseability of ticket.md. Record it even when user code deleted or
        # malformed its own ticket, and never let that reread replace a
        # non-zero child result.
        append_log(
            cfg,
            ref.id_slug,
            "system",
            f"script exited with code {exit_code}",
        )

    if exit_code != 0 and not stateless:
        observed = after or ticket
        current = observed.current_step()
        where = (
            f" at step {observed.step_index()} ({current['name']})"
            if current is not None
            else ""
        )
        post(
            cfg,
            f"💥 script failed on *{ref.id_slug}* "
            f"\"{observed.title}\": exit {exit_code}{where}",
            task_path=ref.path,
            owner=observed.owner or cfg.current_user,
            important=failure_important,
            # The deterministic failure and its exit code are already
            # durable; a notification outage must not replace that result.
            fatal=False,
        )

    if exit_code == 0:
        if ticket_read_error is not None:
            raise ticket_read_error
        # User code may change project configuration or select another branch. The caller uses
        # this result for handoff classification and agent setup, so return a
        # config, target, and ticket derived after the child boundary rather
        # than the objects captured before execution.
        cfg = load_config(cfg.repo_root)
        try:
            ref = resolve_target(cfg, ref.id_slug)
        except TaskNotFoundError:
            after = None
        else:
            after = read_ticket(ref)
        # A bootstrap script is a command implementation: preserve its stdout
        # for callers such as ``$(coga <verb>)`` by keeping framing on stderr.
        typer.echo(f"{ref.id_slug}: script ran successfully", err=stateless)

    return ScriptPhaseResult(
        exit_code=exit_code,
        ticket=after,
        cfg=cfg,
        ref=ref,
    )


def run_script_chain(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    ran_steps: set[str | None],
    *,
    args: Sequence[str] = (),
    failure_important: bool = False,
    tmp_scope: TmpScope | None = None,
) -> ScriptChainResult:
    """Run consecutive deterministic steps until a human or agent takes over."""
    stateless = isinstance(ref, BootstrapRef)
    current = ticket
    while current.step not in ran_steps:
        step_key = current.step
        ran_steps.add(step_key)
        _echo_script_iteration(cfg, ref, current, stateless=stateless)

        before = current
        # Enter only a step this chain will run as a script; an agent step
        # is entered by the supervisor right before its session starts.
        if not stateless and script_entry_point(ref, before, cfg=cfg) is not None:
            entered = _enter_step(cfg, ref, before, tmp_scope)
            if isinstance(entered, ScriptChainResult):
                return entered
            before = entered
        phase = run_script_phase(
            cfg,
            ref,
            before,
            stateless=stateless,
            args=args,
            failure_important=failure_important,
            tmp_scope=tmp_scope,
        )
        cfg = phase.cfg or cfg
        ref = phase.ref or ref
        if not phase.ran:
            ran_steps.discard(step_key)
            return _classify_script_handoff(
                cfg,
                ref,
                phase.ticket,
                stateless=stateless,
                )
        if phase.exit_code != 0:
            return ScriptChainResult(
                phase.exit_code,
                phase.ticket,
                False,
                None,
                cfg,
                ref,
            )

        after = phase.ticket
        if stateless:
            return ScriptChainResult(0, after, False, None, cfg, ref)
        from coga.step_scripts import exit_failure

        if (failure := exit_failure(cfg, ref)) is not None:
            return ScriptChainResult(
                1, after, False, f"{failure} Stopping before the next step", cfg, ref,
            )
        if after is None:
            return ScriptChainResult(
                0,
                None,
                False,
                "Launch: task directory removed by script — nothing to chain",
                cfg,
                ref,
            )
        if after.status != "in_progress":
            if after.status in TERMINAL_STATUSES:
                reason = f"{ref.id_slug}: task is {after.status}"
            elif after.status == "paused":
                reason = f"{ref.id_slug}: task is paused"
            else:
                reason = f"{ref.id_slug}: task status is {after.status!r}"
            return ScriptChainResult(0, after, False, reason, cfg, ref)

        # An unchanged step is the completion-contract signal for row three:
        # deterministic preparation succeeded and the agent continues that
        # same open unit of work. A changed step gets its own deterministic
        # phase before any agent preflight or prompt composition, unless the
        # workflow handed control to the owner. The deterministic chain must
        # honor the same approval boundary as the agent supervisor instead of
        # running ticket.py on somebody else's turn.
        if after.step == before.step:
            return ScriptChainResult(0, after, True, None, cfg, ref)
        try:
            operator = resolve_operator(cfg, ref, after)
        except OperatorResolutionError as exc:
            return ScriptChainResult(
                0, after, False, f"{ref.id_slug}: {exc}; stopping", cfg, ref
            )
        if operator is None or operator.is_human:
            who = "nobody" if operator is None else operator.name
            return ScriptChainResult(
                0,
                after,
                False,
                f"{ref.id_slug}: next step hands off to {who}; "
                "returning to caller",
                cfg,
                ref,
            )
        current = after

    return ScriptChainResult(0, current, True, None, cfg, ref)


def _enter_step(
    cfg: Config, ref: TargetRef, ticket: Ticket, tmp_scope: TmpScope | None,
) -> "Ticket | ScriptChainResult":
    """Run the workflow's `enter` script before one script phase.

    Returns the ticket re-read from the checkout the script left, or a failed
    chain result naming the failure.
    """
    from coga.step_scripts import StepScriptError, run_enter_before_step

    try:
        ran = run_enter_before_step(cfg, ref, ticket.workflow, tmp_scope)
    except StepScriptError as exc:
        typer.secho(
            f"Cannot start {ref.id_slug} step {ticket.step}: {exc}; the step "
            "did not run.",
            fg=typer.colors.RED, err=True,
        )
        return ScriptChainResult(exc.code or 1, ticket, False, None, cfg, ref)
    if not ran:
        return ticket
    return read_ticket(ref)


def _classify_script_handoff(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket | None,
    *,
    stateless: bool,
) -> ScriptChainResult:
    """Classify fresh state after a formerly-scripted phase no longer runs."""
    if stateless:
        return ScriptChainResult(0, ticket, True, None, cfg, ref)
    if ticket is None:
        return ScriptChainResult(
            0,
            None,
            False,
            "Launch: task directory removed before script — nothing to chain",
            cfg,
            ref,
        )
    if ticket.status not in {"active", "in_progress"}:
        if ticket.status in TERMINAL_STATUSES:
            reason = f"{ref.id_slug}: task is {ticket.status}"
        elif ticket.status == "paused":
            reason = f"{ref.id_slug}: task is paused"
        else:
            reason = f"{ref.id_slug}: task status is {ticket.status!r}"
        return ScriptChainResult(0, ticket, False, reason, cfg, ref)
    try:
        operator = resolve_operator(cfg, ref, ticket)
    except OperatorResolutionError as exc:
        return ScriptChainResult(
            0, ticket, False, f"{ref.id_slug}: {exc}; stopping", cfg, ref
        )
    if operator is None:
        return ScriptChainResult(
            0,
            ticket,
            False,
            f"{ref.id_slug}: next step has no operator; returning to caller",
            cfg,
            ref,
        )
    if operator.is_human:
        return ScriptChainResult(
            0,
            ticket,
            False,
            f"{ref.id_slug}: next step hands off to {operator.name}; "
            "returning to caller",
            cfg,
            ref,
        )
    return ScriptChainResult(0, ticket, True, None, cfg, ref)


def _echo_script_iteration(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    *,
    stateless: bool,
) -> None:
    if stateless:
        typer.echo(f"→ running {ref.id_slug} ticket.py", err=True)
        return
    current = ticket.current_step()
    try:
        operator = resolve_operator(
            cfg, ref, ticket, allow_prospective_default=True
        )
        who = operator.name if operator is not None else "none"
    except OperatorResolutionError:
        who = "unresolved"
    if current is None:
        typer.echo(
            f"→ running {ref.id_slug} ticket.py "
            f"(status={ticket.status}, operator={who})"
        )
        return
    typer.echo(
        f"→ entering step {ticket.step}: {current['name']} "
        f"(status={ticket.status}, operator={who})"
    )


LAUNCH_HOOK_DIR = "launch-hook"


def prepare_launch_hook(cfg: Config, hook_ref: str, tmp_scope: TmpScope) -> Path:
    """Copy a step script's skill into the launch tmp scope; return its run.py.

    The skill is resolved local-first like a step's `run:` and copied, so a
    script that switches branches keeps running the code it started with even
    if the switch changes or removes a local override.
    """
    import shutil

    source = resolve_step_script(cfg, hook_ref).parent
    target = tmp_scope.path / LAUNCH_HOOK_DIR / hook_ref
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return target / "run.py"


def run_launch_hook(cfg: Config, ref: TaskRef, script: Path, tmp_scope: TmpScope) -> int:
    """Run one workflow step script (`enter` / `exit`) as a subprocess.

    Git-free: the kernel only supplies the ticket and tmp environment and
    returns the child's exit status. The script gets no secrets.
    """
    ticket = read_ticket(ref)
    env = apply_task_env(step_script_env(ticket.secrets), cfg, ref, ticket)
    for key in ("COGA_SUPERVISED", SENTINEL_ENV, EXPECTED_TASK_ENV,
                EXPECTED_STEP_ENV, EXPECTED_AGENT_ENV, "COGA_SCRIPT_HELP"):
        env.pop(key, None)
    env = apply_tmp_env(env, tmp_scope)
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=host_repo_root(cfg),
        env=env, check=False,
    )
    return _normalize_exit_code(completed.returncode)


__all__ = [
    "SCRIPT_ENTRY_POINT",
    "prepare_launch_hook",
    "run_launch_hook",
    "ScriptChainResult",
    "ScriptPhaseResult",
    "run_script_chain",
    "run_script_phase",
    "script_entry_point",
]


def run_bootstrap_script_help(task: str, args: Sequence[str]) -> int | None:
    """Run only a bootstrap script parser, before ordinary launch setup.

    Valid workspaces resolve local overrides. Invalid/absent configuration
    uses package definitions and never starts an agent as a help fallback.
    """
    from coga.paths import packaged_template_path
    from coga.tasks import BootstrapRef, resolve_bootstrap

    name = task.removeprefix("bootstrap/")
    cwd = Path.cwd()
    try:
        root = find_repo_root()
    except ConfigError:
        root = None
    if root is not None:
        cwd = root.parent if root.name == "coga" else root
        try:
            cfg = load_config(root, require_user=False)
        except (ConfigError, tomllib.TOMLDecodeError):
            ref = BootstrapRef(name, packaged_template_path("bootstrap", name))
        else:
            try:
                ref = resolve_bootstrap(cfg, name)
            except TaskNotFoundError:
                # Unknown target or broken override (`BootstrapOverrideError`):
                # ordinary launch reports it with its usual message.
                return None
    else:
        ref = BootstrapRef(name, packaged_template_path("bootstrap", name))
    entry = script_entry_point(ref)
    if entry is None:
        return None
    env = os.environ.copy()
    for key in (*TASK_ENV_KEYS, "COGA_SUPERVISED", SENTINEL_ENV,
                EXPECTED_TASK_ENV, EXPECTED_STEP_ENV, EXPECTED_AGENT_ENV):
        env.pop(key, None)
    env["COGA_SCRIPT_HELP"] = "1"
    if os.name == "nt":
        env["PYTHONIOENCODING"] = "utf-8"
    code, _ = run_foreground_child(
        [sys.executable, str(entry), *args], cwd=cwd, env=env,
        defer_interrupt=True,
    )
    return code
