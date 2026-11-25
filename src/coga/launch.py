"""`coga launch` — run a ticket's deterministic and/or agent phases.

Launching an `active` task moves it to `in_progress`. A draft / paused ticket
is activated inline first — typing `coga launch` is the readiness signal, so
launch performs the `coga mark active` step itself rather than refusing. (A
workflow-less or required-extension-incomplete ticket still can't be activated,
so those fail loud with the same remedy `mark active` gives.) An
already-`in_progress` ticket resumes without another status flip. Terminal
`done` / `canceled` tickets are refused and left untouched.

Human-owned steps remain unlaunchable by default. An explicit `--agent`
override starts one visible assist session without rewriting `assignee:`.

Bootstrap tickets are stateless re-entry points (no status, no log of state
changes). A reserved ``ticket.py`` sibling runs directly; otherwise launch
composes and starts the agent.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
import tomllib
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Mapping, NamedTuple

from uuid import UUID, uuid4

from typer import Exit as NotificationExit

from coga import usage as usage_tracking
from coga.aliases import ONBOARDING_TASK
from coga.agent_skills import refresh_agent_skill_view
from coga.bump import (
    Operator,
    OperatorResolutionError,
    resolve_main_agent,
    resolve_operator,
)
from coga.blackboard import (
    blackboard_size_warning,
    format_bytes,
    open_blockers,
    parse_blockers_text,
)
from coga.compose import (
    ComposeError,
    LaunchContext,
    PromptComposition,
    ResolvedPromptLayers,
    compose_prompt,
    compose_prompt_report,
    resolve_prompt_layers,
    write_prompt_file,
)
from coga import oscompat
from coga.config import (
    build_launch_env,
    Config,
    AgentType,
    ConfigError,
    parse_inline_secrets,
    SecretError,
    load_config,
)
from coga.dependencies import agent_cli_missing_message
from coga.lifecycle import TERMINAL_STATUSES
from coga.launch_script import (
    prepare_launch_hook,
    run_launch_hook,
    run_script_chain,
    run_script_phase,
    script_entry_point,
)
from coga.logfile import append_log
from coga.paths import RESOURCE_NAMES, RepoResourceUnreadable
from coga.mark import (
    MainAgentUnavailable,
    BlackboardNeedsSynthesis,
    RequiredExtensionMissing,
    WorkflowMissing,
    format_blackboard_synthesis_refusal,
    mark_active,
    mark_in_progress,
    prepare_active,
)
from coga.notification import post, preflight_post
from coga.repl_supervisor import (
    ASSIST_AGENT_ENV,
    AgentCliNotFound,
    ReplOutcome,
    build_supervised_step_env,
    run_with_done_marker,
    unsignalled_advance_warning,
)
from coga import run_state
from coga.task_env import apply_task_env
from coga.taskfile import TaskFileError, split_body, uncomposed_sections_warning
from coga.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    TargetRef,
    list_tasks,
    read_ticket,
    resolve_target,
)
from coga.ticket import (
    Ticket,
    TicketError,
)
from coga.validate import TaskValidationError, assert_task_valid
from coga.workflow import GIT_MODES, WorkflowError, git_mode


class LaunchResult(NamedTuple):
    """A completed launch's termination kind and actual child exit code."""

    kind: str | None = None
    exit_code: int = 0


@contextmanager
def _launch_error_boundary() -> Iterator[None]:
    """Translate signals and exit-shaped failures after internal cleanup."""
    try:
        yield
    except (SystemExit, NotificationExit) as exc:
        code = exc.code if isinstance(exc, SystemExit) else exc.exit_code
        status = code if isinstance(code, int) else (0 if code is None else 1)
        raise LaunchBail(status, code if isinstance(code, str) else "") from exc


def _plain_report(message: str, *, fg: str | None = None, err: bool = False,
                  bold: bool = False) -> None:
    print(message, file=sys.stderr if err else sys.stdout)


_REPORTER: ContextVar[Callable[..., None]] = ContextVar("launch_reporter", default=_plain_report)


@contextmanager
def launch_reporting(reporter: Callable[..., None]) -> Iterator[None]:
    """Select presentation for this call without making results depend on it."""
    token = _REPORTER.set(reporter)
    try:
        yield
    finally:
        _REPORTER.reset(token)


def _report(message: str, *, fg: str | None = None, err: bool = False,
            bold: bool = False) -> None:
    _REPORTER.get()(message, fg=fg, err=err, bold=bold)


DISCUSSION_BOOTSTRAP_TICKETS = frozenset({"bootstrap/orient", "bootstrap/ticket"})
DEFAULT_DISCUSSION_TEMPLATES = {
    "claude": "--append-system-prompt {prompt}",
    "codex": "-c developer_instructions={prompt}",
}
def _onboarding_missing_message() -> str:
    """Explain a `coga build` miss without claiming why the ticket is gone."""
    return (
        f"The {ONBOARDING_TASK!r} onboarding ticket is not in this repo, so "
        "`coga build` has nothing to launch. `coga init` seeds it only on an "
        "empty repo (no project content beyond a stock README, LICENSE, "
        "or .gitattributes), so it was either skipped at init or removed "
        'since. Author tasks with `coga ticket "<title>"` instead.'
    )


@_launch_error_boundary()
def launch(
    task: str,
    args: list[str] | None = None,
    agent_override: str | None = None,
    prompt_report: bool = False,
    idle_timeout: float | None = None,
    max_session: float | None = None,
    return_timeout: bool = False,
    script_failure_important: bool = False,
    read_only: bool = False,
) -> LaunchResult:
    """Launch with ordinary Python defaults, returning a result or LaunchBail.

    Queue callers use the specialized recurring/delegation entry points below.
    No command-line parser objects or process exits cross this boundary.
    """
    if read_only:
        if (
            agent_override is not None or prompt_report or idle_timeout is not None
            or max_session is not None or return_timeout or script_failure_important
        ):
            _bail("--read-only cannot be combined with agent, report or REPL options.")
        try:
            cfg = load_config(require_user=False)
            ref = resolve_target(cfg, task)
            if not isinstance(ref, BootstrapRef) or script_entry_point(ref) is None:
                _bail("--read-only requires a bootstrap target with an exact ticket.py entry.")
            ticket = read_ticket(ref)
            # Read-only dispatch may create only its own tmp area: it never
            # sweeps other launches' state or creates the durable layout.
            with run_state.launch_tmp_scope(cfg, sweep=False) as scope:
                result = run_script_phase(
                    cfg, ref, ticket, stateless=True, read_only=True, args=args or (),
                    tmp_scope=scope,
                )
        except (ConfigError, tomllib.TOMLDecodeError, TaskNotFoundError, TicketError, SecretError, OSError) as exc:
            _bail(str(exc))
        return LaunchResult(kind="script", exit_code=result.exit_code)
    from coga.argv import help_requested
    from coga.launch_script import run_bootstrap_script_help

    if task.startswith("bootstrap/") and help_requested(args or ()):
        code = run_bootstrap_script_help(task, args or ())
        if code is not None:
            return LaunchResult(exit_code=code)
    return _launch(
        task,
        args=args,
        agent_override=agent_override,
        prompt_report=prompt_report,
        idle_timeout=idle_timeout,
        max_session=max_session,
        return_timeout=return_timeout,
        script_failure_important=script_failure_important,
        # The public CLI spelling is always attended: a human typed it and is
        # in the REPL. Queue conduct is selected by the in-process seams
        # below, never by a flag an ordinary launch could pass.
        launch_context="attended",
        before_final_spawn=None,
        require_agent_target=False,
        record_launch=True,
        recurring_authorized=False,
    )



@_launch_error_boundary()
def launch_recurring_period(
    task: str, *, agent_override: str | None, idle_timeout: float | None,
    max_session: float | None, launch_context: LaunchContext,
    agent_spawn_refusal: str | None = None,
) -> LaunchResult:
    """Launch one locally admitted recurring period."""
    return _launch(
        task, args=None, agent_override=agent_override, prompt_report=False,
        idle_timeout=idle_timeout, max_session=max_session, return_timeout=True,
        script_failure_important=True, launch_context=launch_context,
        before_final_spawn=None, require_agent_target=False,
        record_launch=True, recurring_authorized=True,
        agent_spawn_refusal=agent_spawn_refusal,
    )


@_launch_error_boundary()
def launch_with_before_spawn(
    task: str, *, agent_override: str | None, idle_timeout: float | None,
    max_session: float | None, return_timeout: bool, launch_context: LaunchContext,
    before_spawn: Callable[[], None],
) -> LaunchResult:
    """Start delegated period bookkeeping just before spawning its agent."""
    return _launch(
        task, args=None, agent_override=agent_override, prompt_report=False,
        idle_timeout=idle_timeout, max_session=max_session, return_timeout=return_timeout,
        script_failure_important=False, launch_context=launch_context,
        before_final_spawn=lambda _: before_spawn(), require_agent_target=True,
        record_launch=True, recurring_authorized=False,
    )


def _launch(
    task: str,
    *,
    args: list[str] | None,
    agent_override: str | None,
    prompt_report: bool,
    idle_timeout: float | None,
    max_session: float | None,
    return_timeout: bool,
    script_failure_important: bool,
    launch_context: LaunchContext,
    before_final_spawn: Callable[[Ticket], None] | None,
    require_agent_target: bool,
    record_launch: bool,
    recurring_authorized: bool,
    agent_spawn_refusal: str | None = None,
) -> LaunchResult:
    """Run the fixed launch phases; each may finish without starting an agent."""
    invocation = _LaunchInvocation(
        task=task,
        args=args,
        agent_override=agent_override,
        prompt_report=prompt_report,
        idle_timeout=idle_timeout,
        max_session=max_session,
        return_timeout=return_timeout,
        script_failure_important=script_failure_important,
        launch_context=launch_context,
        before_final_spawn=before_final_spawn,
        require_agent_target=require_agent_target,
        record_launch=record_launch,
        recurring_authorized=recurring_authorized,
        agent_spawn_refusal=agent_spawn_refusal,
    )
    result = invocation._prepare_target()
    if result is not None:
        # Admission finished the launch (including a delegated period, which
        # ran its own `_launch` with its own scope).
        return result
    with ExitStack() as stack:
        # One tmp scope covers the whole supervised step chain. A prompt
        # report executes nothing, so it creates no run state.
        if not invocation.prompt_report:
            invocation.tmp_scope = stack.enter_context(
                run_state.launch_tmp_scope(invocation.cfg)
            )
        # The workflow's launch Git mode may wrap the whole launch in a hook.
        # The guard is entered (inside the tmp scope, so `$TMPDIR` outlives
        # it) before `enter` runs, so `exit` runs on every later path.
        guard = invocation._launch_hook_guard()
        if guard is not None:
            stack.enter_context(guard)
            guard.enter()
        for prepare in (
            invocation._classify_target,
            invocation._run_initial_script,
            invocation._prepare_agent,
        ):
            result = prepare()
            if result is not None:
                break
        else:
            result = invocation._supervise_steps()
        if guard is not None:
            guard.result = result
    return result


_HOOK_INTERRUPT_CODE = 130


def _exception_exit_code(exc: BaseException) -> int:
    """The exit status an unwinding exception will become at the boundary."""
    if isinstance(exc, LaunchBail):
        return exc.code
    if isinstance(exc, SystemExit):
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 1)
    if isinstance(exc, NotificationExit):
        return exc.exit_code
    if isinstance(exc, KeyboardInterrupt):
        return _HOOK_INTERRUPT_CODE
    return 1


class _LaunchHookGuard:
    """Run a workflow Git mode's hook around one launch.

    `enter` runs before classification; `exit` runs once `enter` has started,
    on every later path (normal end, handoff, failure, timeout, bail,
    interrupt). The guard observes both the returned `LaunchResult` and an
    unwinding exception, and keeps the first non-zero code: an exit-hook
    failure only makes an otherwise successful launch fail. The kernel knows
    only the hook's script and phases; all Git work lives in the edge script.
    """

    def __init__(self, invocation: "_LaunchInvocation", mode: str, script: Path) -> None:
        self.invocation = invocation
        self.mode = mode
        self.script = script
        self.started = False
        self.result: LaunchResult | None = None

    def __enter__(self) -> "_LaunchHookGuard":
        return self

    def enter(self) -> None:
        inv = self.invocation
        assert inv.tmp_scope is not None and isinstance(inv.ref, TaskRef)
        self.started = True
        code = run_launch_hook(inv.cfg, inv.ref, self.script, "enter", inv.tmp_scope)
        if code != 0:
            _bail(
                f"Cannot launch {inv.ref.id_slug}: its `git: {self.mode}` enter "
                f"hook failed (exit {code}); no lifecycle state was written.",
                exit_code=code,
            )
        # The hook may have switched the checkout: resolve config, target and
        # mode again so classification reads the copy now on disk.
        try:
            inv.cfg = load_config()
            inv.ref = resolve_target(inv.cfg, inv.task)
        except (ConfigError, TaskNotFoundError) as exc:
            _bail(str(exc))
        try:
            live_mode = git_mode(read_ticket(inv.ref).workflow, inv.cfg)
        except (OSError, UnicodeError, TicketError, WorkflowError) as exc:
            _bail(f"Cannot launch {inv.ref.id_slug}: {exc}")
        if live_mode != self.mode:
            _bail(
                f"Cannot launch {inv.ref.id_slug}: the copy that selected the "
                f"launch Git mode declares `git: {self.mode}`, but the live copy "
                f"after the hook declares `git: {live_mode}`. Reconcile the two "
                "copies, then launch again."
            )

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        if not self.started:
            return False
        inv = self.invocation
        assert inv.tmp_scope is not None
        try:
            code = run_launch_hook(inv.cfg, inv.ref, self.script, "exit", inv.tmp_scope)
        except KeyboardInterrupt:
            code = _HOOK_INTERRUPT_CODE
        except OSError as exc:
            _report(f"Launch: cannot run the `git: {self.mode}` exit hook: {exc}",
                    fg='red', err=True)
            code = 1
        if code == 0:
            return False
        message = (
            f"Launch: `git: {self.mode}` exit hook failed (exit {code}); the "
            "checkout was left where the hook stopped. Fix it by hand."
        )
        if exc is not None:
            original = _exception_exit_code(exc)
            if original != 0:
                _report(f"{message} The launch had already failed (exit {original}).",
                        fg='red', err=True)
                return False
            raise LaunchBail(code, message) from exc
        if self.result is not None and self.result.exit_code != 0:
            _report(
                f"{message} The launch had already failed "
                f"(exit {self.result.exit_code}).",
                fg='red', err=True,
            )
            return False
        raise LaunchBail(code, message)


class _LaunchInvocation:
    """Mutable state of one launch, shared by its fixed phases and cleanup.

    Preparation establishes cfg/ref/boundary; classification establishes ticket,
    routing and blocker state. Later phases refresh those same fields after
    moving syncs. The instance is never shared between launches.
    """

    def __init__(
        self,
        task: str,
        *,
        args: list[str] | None,
        agent_override: str | None,
        prompt_report: bool,
        idle_timeout: float | None,
        max_session: float | None,
        return_timeout: bool,
        script_failure_important: bool,
        launch_context: LaunchContext,
        before_final_spawn: Callable[[Ticket], None] | None,
        require_agent_target: bool,
        record_launch: bool,
        recurring_authorized: bool,
        agent_spawn_refusal: str | None = None,
    ) -> None:
        self.task = task
        self.args = args
        self.agent_override = agent_override
        self.prompt_report = prompt_report
        self.idle_timeout = idle_timeout
        self.max_session = max_session
        self.return_timeout = return_timeout
        self.script_failure_important = script_failure_important
        self.launch_context = launch_context
        # File-backed prompt layers resolved by the entry preflight and handed
        # to the first step's one composition (see `_launch`).
        self.resolved_layers: ResolvedPromptLayers | None = None
        self.before_final_spawn = before_final_spawn
        self.require_agent_target = require_agent_target
        self.record_launch = record_launch
        self.recurring_authorized = recurring_authorized
        self.agent_spawn_refusal = agent_spawn_refusal
        self.tmp_scope: run_state.TmpScope | None = None

    def _prepare_target(self) -> LaunchResult | None:
        """Resolve and admit the current target, including delegated periods."""
        self.launch_args = list(self.args or [])

        try:
            self.cfg = load_config()
        except ConfigError as exc:
            _bail(str(exc))

        try:
            self.ref = resolve_target(self.cfg, self.task)
        except TaskNotFoundError as exc:
            if self.task == ONBOARDING_TASK and not any(
                t.id_slug.startswith(self.task) for t in list_tasks(self.cfg)
            ):
                _bail(f"{exc}\n{_onboarding_missing_message()}")
            _bail(str(exc))

        if (
            isinstance(self.ref, TaskRef)
            and self.ref.directory == "recurring"
            and not self.prompt_report
            and not self.recurring_authorized
        ):
            from coga.recurring_runner import recurring_owner_refusal

            refusal = recurring_owner_refusal(self.cfg)
            if refusal is not None:
                _bail(refusal)

        if isinstance(self.ref, TaskRef):
            frozen_ticket = read_ticket(self.ref)
            if "delegate" in frozen_ticket.frontmatter:
                if self.agent_spawn_refusal is not None:
                    _report(
                        f"Cannot continue {self.ref.id_slug}: its delegated phase needs "
                        f"an agent, but {self.agent_spawn_refusal} No agent was started.",
                        fg='yellow',
                        err=True,
                    )
                    return LaunchResult('agent-refused' if self.return_timeout else None)
                if self.launch_args:
                    _bail(
                        f"Cannot pass trailing arguments to delegated period "
                        f"{self.ref.id_slug}; its frozen target owns a fixed command."
                    )
                if self.prompt_report:
                    from coga.recurring import (
                        RecurringError,
                        assert_frozen_delegation,
                        frozen_task_delegate,
                        resolve_agent_delegate,
                    )

                    try:
                        delegate = frozen_task_delegate(self.ref, frozen_ticket)
                        if delegate is None:
                            raise RecurringError(
                                f"delegating recurring task {self.ref.id_slug} is "
                                "missing its frozen target"
                            )
                        resolve_agent_delegate(self.cfg, delegate)
                        assert_frozen_delegation(
                            self.ref, frozen_ticket, require_step=False
                        )
                    except RecurringError as exc:
                        _bail(str(exc))
                    return _launch(
                        delegate,
                        args=None,
                        agent_override=self.agent_override,
                        prompt_report=True,
                        idle_timeout=self.idle_timeout,
                        max_session=self.max_session,
                        return_timeout=self.return_timeout,
                        script_failure_important=self.script_failure_important,
                        launch_context=self.launch_context,
                        before_final_spawn=None,
                        require_agent_target=False,
                        record_launch=True,
                        recurring_authorized=False,
                    )

                from coga.recurring_runner import _run_delegated_task

                delegated = _run_delegated_task(
                    self.cfg,
                    self.ref,
                    agent_override=self.agent_override,
                    idle_timeout=self.idle_timeout,
                    max_session=self.max_session,
                    launch_context=self.launch_context,
                    continue_after_timeout=False,
                    activate_if_needed=True,
                )
                if self.return_timeout:
                    return LaunchResult(delegated.kind, delegated.exit_code)
                if delegated.exit_code:
                    raise LaunchBail(delegated.exit_code)
                return LaunchResult()

        self.resolved_target_slug = self.ref.id_slug
        self.is_bootstrap = isinstance(self.ref, BootstrapRef)
        self.script_steps_run: set[str | None] = set()
        return None

    def _launch_hook_guard(self) -> "_LaunchHookGuard | None":
        """Select the launch-boundary hook for the ticket's frozen Git mode.

        `main` (also an omitted field) selects no hook. A prompt report runs
        nothing; bootstrap targets have no workflow; delegated periods have
        already returned from `_prepare_target`.
        """
        if self.prompt_report or not isinstance(self.ref, TaskRef):
            return None
        try:
            workflow = read_ticket(self.ref).workflow
        except (OSError, UnicodeError, TicketError):
            # Classification reports the unreadable ticket.
            return None
        try:
            mode = git_mode(workflow, self.cfg)
        except WorkflowError as exc:
            if isinstance(workflow, str):
                # A draft's unloadable reference fails at activation, as today.
                return None
            _bail(f"Cannot launch {self.ref.id_slug}: {exc}")
        hook_ref = GIT_MODES[mode]
        if hook_ref is None:
            return None
        if self.ref.directory == "recurring":
            _bail(
                f"Cannot launch {self.ref.id_slug}: a recurring period cannot use "
                f"`git: {mode}`; recurring work runs with `git: main`."
            )
        assert self.tmp_scope is not None
        try:
            script = prepare_launch_hook(self.cfg, hook_ref, self.tmp_scope)
        except (ConfigError, OSError) as exc:
            _bail(f"Cannot launch {self.ref.id_slug}: `git: {mode}` hook: {exc}")
        return _LaunchHookGuard(self, mode, script)

    def _classify_target(self) -> LaunchResult | None:
        """Read and classify the ticket in this checkout."""
        self.source_ticket_bytes = self.ref.ticket_path.read_bytes()
        self.ticket = Ticket.parse(self.source_ticket_bytes.decode("utf-8"))
        try:
            self.entry = script_entry_point(self.ref, self.ticket, cfg=self.cfg)
        except (OSError, ValueError, ConfigError, WorkflowError) as exc:
            _bail(str(exc))
        if self.require_agent_target and self.entry is not None:
            _bail(
                f"Cannot launch {self.ref.id_slug} through the agent-only in-process "
                "delegation seam: the target carries ticket.py."
            )
        if self.entry is not None and not self.is_bootstrap and self.launch_args:
            # Only a stateless command ticket takes operands. Refuse before any
            # secret, activation, lifecycle, or log effect: arguments to a
            # stateful script would be hidden mutable input (coga/extension-model).
            _bail(
                f"Cannot pass trailing arguments to {self.ref.id_slug}: its "
                "ticket.py has lifecycle state, and a stateful script takes no "
                "launch arguments. Record the input in the ticket instead."
            )
        if self.entry is not None and self.prompt_report:
            _bail(
                f"Cannot report an agent prompt for {self.ref.id_slug}: ticket.py runs "
                "before composition and may complete the step. --prompt-report "
                "does not execute ticket code."
            )

        if self.prompt_report:
            if self.agent_override is not None:
                try:
                    self.cfg.agent_type(self.agent_override)
                except ConfigError as exc:
                    _bail(str(exc))
            _refresh_agent_skills_for_launch(self.cfg.repo_root)
            self.ticket = self._read(self.ref)
            try:
                composition = compose_prompt_report(
                    self.cfg, self.ref, self.ticket, launch_context=self.launch_context
                )
            except ComposeError as exc:
                _bail(str(exc))
            _report(_format_prompt_report(self.ref.id_slug, composition))
            warning = blackboard_size_warning(self.ref.ticket_path)
            if warning:
                _report(f"Warning: {warning}", fg='yellow', err=True)
            warning = uncomposed_sections_warning(self.ref.ticket_path)
            if warning:
                _report(f"Warning: {warning}", fg='yellow', err=True)
            return LaunchResult()

        _report(
            f"Launch: task {self.ref.id_slug} "
            f"(status={self.ticket.status if not self.is_bootstrap else 'n/a'}, "
            f"operator={_operator_display(self.cfg, self.ref, self.ticket)})",
            err=self.is_bootstrap and self.entry is not None,
        )

        # A terminal ticket is closed: launching it must not restart its frozen
        # workflow. Re-activating would re-seed `step: 1` and quietly reopen
        # finished work. Refuse loud. Draft/paused still activate inline below.
        if (
            not self.is_bootstrap
            and isinstance(self.ref, TaskRef)
            and self.ticket.status in TERMINAL_STATUSES
        ):
            _bail(
                f"Cannot launch {self.ref.id_slug}: it is {self.ticket.status}, a terminal "
                "status; nothing to launch. Launch a different ticket."
            )

        self.blocked_resume = False
        if not self.is_bootstrap and isinstance(self.ref, TaskRef) and self.ticket.status == "blocked":
            if self.entry is not None:
                _bail(
                    f"Cannot launch {self.ref.id_slug}: its script is blocked. "
                    f"Answer with `coga unblock {self.ref.id_slug} --answer ...`."
                )
            if interactive_stdio_has_tty():
                if not open_blockers(self.ref.ticket_path):
                    _bail(
                        f"Cannot launch {self.ref.id_slug}: it is blocked but has no "
                        "open blocker asks to resolve. Record a blocker with "
                        f"`coga block --task {self.ref.id_slug} --reason \"...\"` or "
                        "repair the task state before launching."
                    )
                self.blocked_resume = True
                _report(
                    f"Launch: {self.ref.id_slug} is blocked — resuming "
                    "interactively to resolve the open asks."
                )
            else:
                _bail(
                    f"Cannot launch {self.ref.id_slug}: it is blocked, and only an "
                    f"interactive launch from a TTY can resume it to resolve the "
                    f"blocker in-session. Run `coga status --blocked` to read the "
                    f"open ask, then `coga unblock {self.ref.id_slug} --answer \"...\"` "
                    f"to resume."
                )

        if not self.is_bootstrap and isinstance(self.ref, TaskRef):
            # Activation can change every routing input, so classify the recorded
            # assist from the prepared activation rather than the parked ticket.
            self.operator, self.current_step = _prospective_activation_identity(self.cfg, self.ref, self.ticket)
        else:
            try:
                self.operator = _target_operator(self.cfg, self.ref, self.ticket)
            except OperatorResolutionError as exc:
                # A script command ticket runs no agent, so it must not require
                # one. If its ticket.py vanishes before running, the agent
                # handoff re-derives the operator and refuses then.
                if not (self.is_bootstrap and self.entry is not None):
                    _bail(f"Cannot launch {self.ref.id_slug}: {exc}")
                    return LaunchResult()
                self.operator = None
            self.current_step = self.ticket.current_step()
        # A strict human assist: an explicit override running one visible session on
        # a step the workflow hands to a human. Decided by the step's *role*, so an
        # explicitly declared agent step is never mistaken for a handoff, and a
        # human whose nickname matches an agent type is never mistaken for an agent.
        self.human_assist = (
            not self.is_bootstrap
            and self.agent_override is not None
            and self.operator is not None
            and self.operator.is_human
        )
        return None

    def _run_initial_script(self) -> LaunchResult | None:
        """Run deterministic work before any agent-only preparation."""

        if self.entry is not None:
            try:
                if isinstance(self.ref, TaskRef):
                    _refuse_human_handoff_launch(self.cfg, self.ref, self.ticket, self.agent_override)
                    if self.ticket.status in {"draft", "paused"}:
                        build_launch_env(self.cfg, self.ticket.secrets)
                        _auto_activate(self.cfg, self.ref, self.ticket)

                self.script_outcome = run_script_chain(
                    self.cfg,
                    self.ref,
                    self.ticket,
                    self.script_steps_run,
                    args=self.launch_args if self.is_bootstrap else (),
                    failure_important=self.script_failure_important,
                    tmp_scope=self.tmp_scope,
                )
                self.cfg = self.script_outcome.cfg or self.cfg
                self.ref = self.script_outcome.ref or self.ref
                self.is_bootstrap = isinstance(self.ref, BootstrapRef)
                if self.script_outcome.ticket is not None:
                    self.ticket = self.script_outcome.ticket
                if self.script_outcome.exit_code != 0:
                    _exit_failed_script(self.script_outcome.exit_code)

                if not self.script_outcome.needs_agent:
                    if self.script_outcome.stop_reason:
                        _report(self.script_outcome.stop_reason, err=self.is_bootstrap)
                    return LaunchResult('script' if self.return_timeout else None)

                if self.script_outcome.ticket is None:
                    _bail(
                        f"Cannot continue {self.ref.id_slug}: ticket.py left no "
                        "ticket state for an agent handoff."
                    )
                if self.agent_spawn_refusal is not None:
                    _report(
                        f"Cannot continue {self.ref.id_slug}: ticket.py left "
                        f"{_script_step_label(self.ticket)} open, but "
                        f"{self.agent_spawn_refusal} The deterministic work was kept; "
                        "no agent was started.",
                        fg='yellow',
                        err=True,
                    )
                    return LaunchResult('script' if self.return_timeout else None)
                try:
                    post_script_operator = _target_operator(self.cfg, self.ref, self.ticket)
                except OperatorResolutionError as exc:
                    post_script_operator = None
                    script_operator_error: str | None = str(exc)
                else:
                    script_operator_error = None
                # An explicit override authorizes the human-owned step it was
                # requested for. Once ticket.py advances the workflow to an agent
                # step, that step's derived operator owns the actual spawn and the
                # assist override stops participating in routing.
                handoff_override = (
                    None
                    if self.human_assist
                    and post_script_operator is not None
                    and post_script_operator.is_agent
                    else self.agent_override
                )
                if script_operator_error is not None and handoff_override is None:
                    _bail(
                        f"Cannot continue {self.ref.id_slug}: ticket.py left work open, "
                        f"but its operator cannot be derived "
                        f"({script_operator_error})."
                    )
                _require_agent_after_script(
                    self.cfg,
                    self.ref,
                    self.ticket,
                    handoff_override,
                )
                self.agent_override = handoff_override
                self.human_assist = bool(
                    self.agent_override is not None
                    and post_script_operator is not None
                    and post_script_operator.is_human
                )
            except (SecretError, TaskValidationError, FileNotFoundError) as exc:
                _bail(str(exc))

        # Everything below is agent-only. A headless or temporary-worktree runner
        # supplies a hard refusal even for a period whose frozen ticket.py vanished
        # after scan admission; no reconciliation race may turn that period into an
        # agent launch in the disposable checkout.
        if self.agent_spawn_refusal is not None:
            _report(
                f"Cannot continue {self.ref.id_slug}: its open work needs an agent, "
                f"but {self.agent_spawn_refusal} No agent was started.",
                fg='yellow',
                err=True,
            )
            return LaunchResult('agent-refused' if self.return_timeout else None)
        return None

    def _prepare_agent(self) -> LaunchResult | None:
        """Preflight the selected agent before committing lifecycle changes."""

        # Deterministic completion, failure, and handoff paths have already
        # returned without consulting agent config, materializing skills,
        # composing a prompt, or probing the CLI binary.
        if self.agent_override is not None:
            try:
                self.cfg.agent_type(self.agent_override)
            except ConfigError as exc:
                _bail(str(exc))
        _refresh_agent_skills_for_launch(self.cfg.repo_root)

        try:
            self.operator = _target_operator(self.cfg, self.ref, self.ticket)
        except OperatorResolutionError as exc:
            _bail(f"Cannot launch {self.ref.id_slug}: {exc}")
            return LaunchResult()
        if self.operator is None:
            _bail(
                f"Cannot launch {self.ref.id_slug}: it has no current step, so there is "
                "no operator to route to."
            )
            return LaunchResult()

        # Carried across the prepare/commit split below, so the deferred audit line
        # can still name the real transition once `ticket.status` reads `active`.
        # Initialized here because the commit gate is reached on paths where the
        # prepare guard never fires.
        auto_activate_prior: str | None = None
        # Typing `coga launch` *is* the readiness signal: a draft / paused ticket
        # is brought to `active` inline rather than refused with a "run
        # `coga mark active` first" hint. Only the *in-memory* half runs here,
        # so the composed prompt sees the activated ticket; the durable write is
        # deferred past every refusing preflight to `_commit_auto_activate`
        # below, immediately before the `in_progress` flip. A refused launch
        # must not leave a ticket on disk claiming a session started.
        if (
            not self.is_bootstrap
            and isinstance(self.ref, TaskRef)
            and self.ticket.status in {"draft", "paused"}
        ):
            auto_activate_prior = self.ticket.status
            _prepare_auto_activate(self.cfg, self.ref, self.ticket)
            # Activation freezes the snapshot, seeds step 1, and selects a main
            # agent. Re-derive routing from that prepared state for CLI
            # preflight, audit, and override continuation, before committing any
            # lifecycle state.
            try:
                self.operator = _target_operator(self.cfg, self.ref, self.ticket)
            except OperatorResolutionError as exc:
                _bail(f"Cannot launch {self.ref.id_slug}: {exc}")
                return LaunchResult()
            if self.operator is None:
                _bail(
                    f"Cannot launch {self.ref.id_slug}: activation left it with no "
                    "current step to route."
                )
                return LaunchResult()
            self.current_step = self.ticket.current_step()
            self.human_assist = bool(
                self.agent_override is not None and self.operator.is_human
            )

        _refuse_human_handoff_launch(self.cfg, self.ref, self.ticket, self.agent_override)

        if not interactive_stdio_has_tty():
            _refuse_tty_launch(self.ref)

        self.launch_agent = self.agent_override or self.operator.name
        if self.human_assist:
            _report(
                f"Launch: agent {self.agent_override} assisting on owner-held step "
                f"(operator={self.operator.name}; ticket routing unchanged)"
            )
        elif self.agent_override is not None and self.agent_override != self.operator.name:
            _report(
                f"Launch: agent {self.agent_override} overriding this session only "
                f"(operator={self.operator.name}; ticket routing unchanged)"
            )

        # Resolve the agent type from whoever is actually going to run.
        try:
            self.agent = self.cfg.agent_type(self.launch_agent)
        except ConfigError as exc:
            _bail(str(exc))
        _report(
            f"Launch: agent {self.launch_agent} -> {self.agent.name} "
            f"(cli={self.agent.cli})"
        )

        try:
            prepared = prepare_agent_launch(
                self.cfg, self.ref, self.ticket, self.launch_agent,
                launch_context=self.launch_context,
                defer_prompt=True,
                discussion=_is_discussion_bootstrap(self.ref),
                kickoff=_bootstrap_kickoff(self.ref),
            )
        except AgentPreparationError as exc:
            _bail(str(exc))
        self.agent, self.env = prepared.agent, prepared.env
        self.resolved_layers = prepared.resolved_layers
        _report(f"Launch: found agent CLI at {prepared.cli_path}")

        if auto_activate_prior is not None and isinstance(self.ref, TaskRef):
            _commit_auto_activate(self.cfg, self.ref, self.ticket, prior=auto_activate_prior)

        if isinstance(self.ref, TaskRef) and self.ticket.status == "active":
            _start_session(self.cfg, self.ref, self.ticket, launch_agent=self.launch_agent)

        # Agent launches chain across consecutive agent-owned steps. After the
        # agent exits (via autoquit on
        # `coga bump` / `mark done` / `mark canceled` / `block`, or via
        # `/exit`), we re-read the
        # ticket and either relaunch the next step's agent as a fresh process —
        # rotating the CLI when the step hands off to a different agent (e.g.
        # claude -> codex for peer review) — or stop and return control to the
        # caller. Every bump produces a brand-new agent process with a freshly
        # composed prompt; context flows through the durable files (blackboard,
        # ticket, artifacts), never a carried-over REPL session. The supervisor
        # only stops at human handoffs and terminal states — `_harness_stop_reason`
        # decides. Each step's launch environment is minted below with the
        # supervised flag plus the exact task/step ownership witnesses.

        def _on_signal(signum, frame):  # type: ignore[no-untyped-def]
            # Signals must bypass libraries' recoverable Exception handlers.
            # The public boundary translates this after internal cleanup.
            raise SystemExit(128 + signum)

        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
        return None

    def _supervise_steps(self) -> LaunchResult:
        """Supervise successive steps in the current checkout."""

        ended_by_script = False
        first_step = True
        consecutive_agent_override = False
        while True:
            self.ticket = self._read(self.ref)
            is_first_step = first_step
            try:
                self.entry = script_entry_point(self.ref, self.ticket, cfg=self.cfg)
            except (OSError, ValueError, ConfigError, WorkflowError) as exc:
                _bail(str(exc))

            if self.entry is not None and self.ticket.step not in self.script_steps_run:
                try:
                    self.script_outcome = run_script_chain(
                        self.cfg,
                        self.ref,
                        self.ticket,
                        self.script_steps_run,
                        failure_important=self.script_failure_important,
                        tmp_scope=self.tmp_scope,
                    )
                except (SecretError, TaskValidationError, FileNotFoundError) as exc:
                    _bail(str(exc))
                self.cfg = self.script_outcome.cfg or self.cfg
                self.ref = self.script_outcome.ref or self.ref
                self.is_bootstrap = isinstance(self.ref, BootstrapRef)
                if self.script_outcome.exit_code != 0:
                    _exit_failed_script(self.script_outcome.exit_code)
                if not self.script_outcome.needs_agent:
                    if self.script_outcome.stop_reason:
                        _report(self.script_outcome.stop_reason)
                    ended_by_script = True
                    break
                if self.script_outcome.ticket is None:
                    _bail(
                        f"Cannot continue {self.ref.id_slug}: ticket.py left no "
                        "ticket state for an agent handoff."
                    )
                self.ticket = self.script_outcome.ticket
                _require_agent_after_script(
                    self.cfg,
                    self.ref,
                    self.ticket,
                    self.agent_override if first_step else None,
                )

            # A prior agent or deterministic phase may have changed both the
            # ticket's secret declarations and coga.toml. Mint this step's env
            # from the freshly re-read config/ticket instead of carrying the
            # first step's secret scope across the handoff.
            try:
                self.env = build_launch_env(self.cfg, self.ticket.secrets)
            except SecretError as exc:
                _bail(str(exc))

            # Resolve the agent for THIS step from the step's derived operator,
            # so the supervisor can rotate main <-> peer across the workflow. A
            # one-off `--agent` override follows directly consecutive steps that
            # *explicitly declare* the `agent` role, so a same-agent workflow
            # stays on the explicitly selected CLI. An omitted role, an owner
            # step, or `other-agent` ends that continuation permanently for this
            # launch; later steps follow the ticket's own routing. An inherited
            # agent role can execute, but does not widen the override contract.
            # An owner-held first step reaches here only through an explicit
            # assist, whose override never propagates. Later human handoffs
            # stop in `_harness_stop_reason` before a relaunch.
            #
            self.current_step = self.ticket.current_step()
            current_role = _explicit_step_role(self.current_step)
            try:
                step_operator = _target_operator(self.cfg, self.ref, self.ticket)
            except OperatorResolutionError as exc:
                # A routing input became invalid mid-chain (an agent removed
                # from config, an edited snapshot). Stop cleanly and hand back
                # to the human rather than guessing a worker.
                _report(f"{self.ref.id_slug}: {exc}; stopping")
                break
            if first_step:
                step_agent = self.agent_override or (
                    step_operator.name if step_operator is not None else None
                )
                consecutive_agent_override = bool(
                    self.agent_override
                    and not self.human_assist
                    and current_role == "agent"
                )
            elif consecutive_agent_override and current_role == "agent":
                step_agent = self.agent_override
            else:
                consecutive_agent_override = False
                step_agent = (
                    step_operator.name if step_operator is not None else None
                )
            first_step = False
            try:
                self.agent = self.cfg.agent_type(step_agent) if step_agent else None
                if self.agent is None:
                    raise ConfigError(
                        f"Task {self.ref.id_slug} has no agent to route this step to"
                    )
            except ConfigError as exc:
                # Defensive: an owner-held step should have stopped the chain at
                # the previous bump. If we somehow reach here, stop rather than
                # crash.
                _report(f"{self.ref.id_slug}: {exc}; stopping")
                break
            # Re-check the CLI every step — catches the case where the chain
            # rotates to an agent (e.g. codex) whose CLI won't resolve. Stop
            # cleanly and hand back to the human rather than blocking.
            if shutil.which(self.agent.cli) is None:
                message = (
                    f"{self.ref.id_slug}: next step needs agent {step_agent!r} "
                    f"but {agent_cli_missing_message(self.agent.name, self.agent.cli)}"
                )
                if self.is_bootstrap and self.return_timeout:
                    _bail(f"{message} No agent was started.")
                _report(
                    f"{message} Stopping; then run `coga launch "
                    f"{self.ref.id_slug}` to continue.",
                    fg='yellow',
                    err=True,
                )
                break
            _report(
                f"Launch: step agent {step_agent} -> {self.agent.name} "
                f"(cli={self.agent.cli})"
            )

            _echo_launch_iteration(self.cfg, self.ref, self.ticket)
            spawn_ticket = self.ticket
            # Delegation uses this only for its stateless single bootstrap
            # session. An ordinary recurring period can chain agent-owned
            # workflow steps, so refresh its teardown witness before every
            # spawned child and retain the last generation actually launched.
            session_before_spawn: Callable[[], None] | None = None
            if self.before_final_spawn is not None and (
                is_first_step or self.recurring_authorized
            ):

                def invoke_final_spawn_guard(
                    callback: Callable[[Ticket], None] = self.before_final_spawn,
                    expected_ticket: Ticket = spawn_ticket,
                ) -> None:
                    callback(expected_ticket)

                session_before_spawn = invoke_final_spawn_guard

            # Freeze the pre-session `(status, step)` at the last boundary
            # before the PTY spawn, after every start-state write (including an
            # assist's lifecycle publication in the caller's guard), so the
            # session's own activation can never read as an agent change.
            state_before_session: tuple[str | None, str | None] | None = None

            def freeze_state_before_session(
                guard: Callable[[], None] | None = session_before_spawn,
                spawn_ref: TargetRef = self.ref,
            ) -> None:
                nonlocal state_before_session
                if guard is not None:
                    guard()
                state_before_session = _diagnostic_ticket_state(spawn_ref)

            log_message = _launch_log_message(
                _operator_display(self.cfg, self.ref, self.ticket),
                step_agent or self.launch_agent,
                self.agent.name,
            )
            actor = f"human:{self.cfg.current_user}"
            resolved_layers = self.resolved_layers if is_first_step else None
            step_env = build_supervised_step_env(
                self.env,
                task_path=self.ref.path,
                step=spawn_ticket.step,
                agent=step_agent or self.launch_agent,
            )
            if self.tmp_scope is not None:
                run_state.ensure_task_data_dir(self.cfg, self.ref)
                step_env = run_state.apply_tmp_env(step_env, self.tmp_scope)

            try:
                session = spawn_agent_session(
                    self.cfg,
                    self.ref,
                    spawn_ticket,
                    self.agent,
                    env=step_env,
                    actor=actor,
                    log_message=log_message,
                    name=self.ticket.title or "",
                    discussion=_is_discussion_bootstrap(self.ref),
                    kickoff=_bootstrap_kickoff(self.ref),
                    prompt_suffix=_agent_args_prompt_suffix(self.launch_args),
                    launch_context=self.launch_context,
                    idle_timeout=self.idle_timeout,
                    max_session=self.max_session,
                    label="Launch",
                    warn_blackboard=True,
                    assist_agent=step_agent if is_first_step and self.human_assist else None,
                    before_spawn=freeze_state_before_session,
                    record_launch=self.record_launch,
                    resolved_layers=resolved_layers,
                )
            except ComposeError as exc:
                _bail(str(exc))
            except AgentCliNotFound:
                _bail(
                    "Failed to spawn agent: "
                    f"{agent_cli_missing_message(self.agent.name, self.agent.cli)}"
                )
            except FileNotFoundError as exc:
                _bail(missing_launch_file_message(exc))

            _report(f"Launch: agent exited with code {session.exit_code}")
            if isinstance(self.ref, TaskRef):
                _warn_unsignalled_advance(
                    self.ref, state_before_session, done_signalled=session.done_signalled,
                )
            if session.termination_kind == "timeout":
                # A liveness limit (idle / max-session) tore the REPL down — the
                # agent never signalled done. Don't chain to the next step.
                # Recurring's in-process caller asks for the kind so it can
                # record the timeout and continue its sweep; public CLI callers
                # get the supervisor's non-zero timeout exit.
                timeout_reason = (
                    session.termination_reason
                    or "liveness limit reached without a done signal"
                )
                _report(
                    f"Agent timed out: {timeout_reason} — exit "
                    f"{session.exit_code}.",
                    fg='yellow',
                    err=True,
                )
                if self.return_timeout:
                    return LaunchResult("timeout", session.exit_code)
                raise LaunchBail(session.exit_code)
            if session.exit_code != 0:
                _report(
                    f"Agent exited with code {session.exit_code}.",
                    fg='yellow',
                    err=True,
                )
                if self.return_timeout and self.is_bootstrap:
                    return LaunchResult(session.termination_kind, session.exit_code)
                raise LaunchBail(session.exit_code)

            if self.return_timeout and self.is_bootstrap:
                return LaunchResult(session.termination_kind, session.exit_code)

            # An agent may delete its own task directory as a final action —
            # e.g. a Dream run retiring itself once its findings are durable.
            # A missing ticket.md is a clean terminal state, not a chain step.
            if not self.ref.ticket_path.exists():
                _report(
                    "Launch: task directory removed by agent — nothing to chain"
                )
                break

            # Bootstrap tickets are stateless single-shot launches — they have no
            # workflow to chain across, so stop after the one run. A normal
            # workflow ticket that happens to declare ticket-level `skills:`
            # MUST still chain; gating on `ticket.skills` here (a rename
            # artifact of the old singular skill-shim field) silently broke that.
            if self.is_bootstrap:
                _report(
                    f"Launch: {self.ref.id_slug} is a bootstrap ticket — not chaining"
                )
                break

            _report("Launch: reading task state after agent exit")
            updated_ticket = read_ticket(self.ref)
            stop_reason = _harness_stop_reason(
                self.ref,
                self.ticket,
                updated_ticket,
                self.cfg,
                chain_agent_override=(
                    self.agent_override if consecutive_agent_override else None
                ),
            )
            if stop_reason is not None:
                _report(stop_reason)
                break
        return LaunchResult('script' if self.return_timeout and ended_by_script else None)

    def _read(self, target: TaskRef | BootstrapRef) -> Ticket:
        """Read the ticket from disk.

        Deliberately unmodified: an `--agent` override is ephemeral and is
        applied where the worker is chosen, never by editing a ticket — not even
        the in-memory copy, which composition and the routing derivation both
        read.
        """
        return read_ticket(target)



# --- helpers ------------------------------------------------------------------


def _script_step_label(ticket: Ticket) -> str:
    current = ticket.current_step()
    if current is None:
        return "the workflow-less task"
    return f"step {ticket.step_index()} ({current['name']})"


def _require_agent_after_script(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    agent_override: str | None,
) -> None:
    """Fail loud when ``ticket.py`` left work open but no agent can take it."""

    step_label = _script_step_label(ticket)
    if not interactive_stdio_has_tty():
        _bail(
            f"Cannot continue {ref.id_slug}: ticket.py left {step_label} open, "
            "but its agent phase requires a TTY (stdin and stdout must both "
            "be terminals). The deterministic work was kept; rerun from a "
            "real shell to continue."
        )

    worker = agent_override
    if worker is None:
        try:
            operator = _target_operator(cfg, ref, ticket)
        except OperatorResolutionError as exc:
            _bail(
                f"Cannot continue {ref.id_slug}: ticket.py left {step_label} "
                f"open, but its operator cannot be derived ({exc}). The "
                "deterministic work was kept."
            )
            return
        if operator is None or operator.is_human:
            who = "nobody" if operator is None else f"the owner ({operator.name})"
            _bail(
                f"Cannot continue {ref.id_slug}: ticket.py left {step_label} "
                f"open, but it hands off to {who} rather than an agent. The "
                "deterministic work was kept."
            )
            return
        worker = operator.name
    try:
        agent = cfg.agent_type(worker)
    except ConfigError as exc:
        _bail(
            f"Cannot continue {ref.id_slug}: ticket.py left {step_label} open, "
            f"but {worker!r} cannot run an agent ({exc}). The "
            "deterministic work was kept."
        )
    if shutil.which(agent.cli) is None:
        _bail(
            f"Cannot continue {ref.id_slug}: ticket.py left {step_label} open "
            f"for agent {worker!r}, but {agent_cli_missing_message(agent.name, agent.cli)} "
            "The deterministic work was kept."
        )


def _exit_failed_script(exit_code: int) -> None:
    _report(
        f"Script exited with {exit_code}.",
        fg='yellow',
        err=True,
    )
    raise LaunchBail(exit_code)


def _target_operator(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
) -> Operator | None:
    """The operator a launch should route to, for any launch target.

    A `BootstrapRef` is stateless: it has no workflow and no lifecycle, so its
    operator is simply its own explicit main-agent choice, or the configured
    default. Ordinary tasks derive theirs from the frozen workflow step.

    Raises `OperatorResolutionError`; callers turn that into a refusal *before*
    dispatch rather than guessing an agent.
    """
    if isinstance(ref, BootstrapRef):
        return Operator(
            "agent",
            resolve_main_agent(
                cfg,
                ticket.agent,
                task_label=ref.id_slug,
                allow_prospective_default=True,
            ),
        )
    return resolve_operator(cfg, ref, ticket, allow_prospective_default=True)


def _operator_display(cfg: Config, ref: TargetRef, ticket: Ticket) -> str:
    """A never-raising operator label for a launch banner."""
    try:
        operator = _target_operator(cfg, ref, ticket)
    except OperatorResolutionError:
        return "unresolved"
    return operator.name if operator is not None else "none"


def _explicit_step_role(step: dict | None) -> str | None:
    """The role a step *declares*, or None when it omits one.

    An omitted role still routes — it inherits the nearest preceding
    declaration — but an inherited `agent` role deliberately does not extend a
    `--agent` override's propagation, which is scoped to explicitly declared
    agent steps.
    """
    return step.get("assignee") if isinstance(step, dict) else None


def _prospective_activation_identity(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
) -> tuple[Operator | None, dict | None]:
    """The operator and step a draft/paused ticket would have once activated.

    Activation freezes a bare workflow ref, seeds step 1, and selects a main
    agent — all three change how routing resolves, so classifying a recorded
    human assist from the *unactivated* draft gets both transitions wrong:
    human→agent needlessly enters strict assist handling, and agent→human misses
    it entirely. `coga/workflows` requires launch to choose the agent and
    check human handoffs from the prepared activation, so resolve it here,
    before that classification.

    This runs on a copy and writes nothing. Activation and resolution refusals
    are deliberately swallowed: the real `_prepare_auto_activate` (or the assist
    publisher) still runs later and owns the operator-facing error, so this must
    not change which message a refused launch produces or when it appears.
    """
    def _current() -> tuple[Operator | None, dict | None]:
        try:
            return _target_operator(cfg, ref, ticket), ticket.current_step()
        except OperatorResolutionError:
            return None, ticket.current_step()

    if ticket.status not in {"draft", "paused"}:
        return _current()
    prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    try:
        prepare_active(cfg, ref, prospective)
        return (
            _target_operator(cfg, ref, prospective),
            prospective.current_step(),
        )
    except Exception:
        return _current()


def _start_session(
    cfg: Config, ref: TaskRef, ticket: Ticket, *, launch_agent: str
) -> None:
    """Flip an `active` ticket to `in_progress` for the session about to start."""
    try:
        mark_in_progress(
            cfg,
            ref,
            ticket,
            actor=f"human:{cfg.current_user}",
            log_message="started (active → in_progress) via coga launch",
            slack_text=(
                f"▶️ {cfg.current_user} started *{ref.id_slug}* "
                f"\"{ticket.title}\" (agent: {launch_agent})"
            ),
            echo=f"{ref.id_slug}: in_progress",
        )
    except TaskValidationError as exc:
        _bail(str(exc))


_AUTO_ACTIVATE_SUFFIX = " — auto on launch"


def _prepare_auto_activate(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Bring a draft / paused / resumable blocked ticket to `active` in memory.

    `coga launch` used to refuse any status but `active`/`in_progress` and
    point the operator at `coga mark active`. Now launching *is* the readiness
    decision, so we run that activation here. This is the pure half: it mutates
    `ticket` in place — status → active, a bare-string `workflow:` frozen, and
    `step:` seeded — so the later `mark_in_progress` flip fires off the same
    object, but it writes nothing durable. `_commit_auto_activate` writes.

    Splitting the two is the point: everything that can *refuse* a launch runs
    between them, so a refused launch leaves no ticket on disk claiming a
    session started. (A terminal ticket never reaches here: launch refuses it
    earlier rather than restart closed work. A blocked ticket reaches here only
    after the launch preflights have passed.)

    Fails loud, leaving the ticket untouched, when activation can't legally
    happen: the ticket has no workflow to advance, its `workflow:` ref can't
    be frozen, a `required` extension field is empty, or a draft still carries
    unsynthesized authoring notes. These mirror the `coga mark active` errors
    so the remedy is the same. `TaskValidationError` is *not* handled here —
    it comes from the post-write `assert_task_valid` in the commit half.
    """
    prior = ticket.status
    try:
        prepare_active(cfg, ref, ticket)
    except WorkflowMissing:
        _bail(
            f"Cannot launch {ref.id_slug}: it is {prior!r} and has no workflow, "
            "so there is nothing to activate or advance. Set `workflow: <name>` "
            "in `ticket.md` (see coga/workflows/) or run "
            f"`coga ticket {ref.id_slug}` to fill it in, then retry."
        )
    except WorkflowError as exc:
        _bail(
            f"Cannot launch {ref.id_slug}: its `workflow:` ref could not be "
            f"frozen — {exc}"
        )
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        _bail(
            f"Cannot launch {ref.id_slug}: required extension field(s) empty: "
            f"{names}. Fill them in `ticket.md` then retry."
        )
    except BlackboardNeedsSynthesis as exc:
        _bail(
            format_blackboard_synthesis_refusal(
                ref.id_slug, action="launch", reason=exc.reason
            )
        )
    except RepoResourceUnreadable as exc:
        _bail(f"Cannot launch {ref.id_slug}: {exc}")
    except MainAgentUnavailable as exc:
        _bail(f"Cannot launch {ref.id_slug}: {exc}")


def _commit_auto_activate(
    cfg: Config, ref: TaskRef, ticket: Ticket, *, prior: str
) -> None:
    """Write the activation `_prepare_auto_activate` already staged in memory.

    `prior` is the status the ticket held *before* the prepare half mutated it;
    the caller must carry it across, because `ticket.status` reads `active` by
    the time we get here and the audit line names the real transition.

    `mark_active` re-runs `prepare_active` on the already-prepared ticket. That
    is deliberately idempotent: the canceled check and the unsynthesized-draft
    refusal both key off `prior_status`, which is now `active`, so neither
    fires twice; `_freeze_workflow_ref` is a documented no-op on a frozen
    workflow dict that already carries a step; and the extension check and the
    status assignment are pure re-reads. Keep it that way — the split relies on
    the second run being free of side effects the first already had.

    Outside ordinary grouped startup, this assumes nothing rewrote
    `ref.ticket_path` while the preflights ran:
    the in-memory ticket is written over whatever is on disk, unguarded. Coga
    is a single-writer, locally operated tool and tickets are not edited
    concurrently with a launch of the same ticket; the blocked-resume gate in
    `_launch` makes the same assumption across the same preflights. The strict
    assist path guards its publication explicitly. Ordinary managed startup
    uses `_publish_startup` instead, with captured source bytes and a guarded
    task-plus-log transaction — see `coga-dev/internals/state-publication`.
    """
    try:
        mark_active(
            cfg,
            ref,
            ticket,
            actor=f"human:{cfg.current_user}",
            log_message=f"activated ({prior} → active){_AUTO_ACTIVATE_SUFFIX}",
            echo=f"{ref.id_slug}: active{_AUTO_ACTIVATE_SUFFIX}",
        )
    except TaskValidationError as exc:
        _bail(str(exc))


def _auto_activate(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Prepare and durably write an activation in one step.

    For callers that have no refusing preflight to run in between — the script
    path, whose `ticket.py` run genuinely *is* work starting, and the
    blocked-resume gate, which already sits below every preflight.
    """
    prior = ticket.status
    _prepare_auto_activate(cfg, ref, ticket)
    _commit_auto_activate(cfg, ref, ticket, prior=prior)


def _diagnostic_ticket_state(
    ref: TargetRef,
) -> tuple[str | None, str | None] | None:
    """Best-effort `(status, step)` for the unsignalled-advance diagnostic.

    None when the ticket is missing or unreadable: the diagnostic is advisory
    and must never change a launch's result, so expected read, parse, and
    validation failures mean "no observation" rather than an error.
    """
    try:
        ticket = read_ticket(ref)
    except (OSError, UnicodeError, TaskFileError, TicketError):
        return None
    return ticket.status, ticket.step


def _warn_unsignalled_advance(
    ref: TargetRef,
    before: tuple[str | None, str | None] | None,
    *,
    done_signalled: bool,
) -> None:
    """Print the yellow advisory when the ticket moved without a done signal."""
    if before is None:
        return
    warning = unsignalled_advance_warning(
        ref.id_slug,
        before,
        _diagnostic_ticket_state(ref),
        done_signalled=done_signalled,
    )
    if warning:
        _report(warning, fg='yellow', err=True)


def _agent_args_prompt_suffix(args: list[str]) -> str:
    """Render one launch invocation's positional args as prompt input.

    JSON preserves argument boundaries (including whitespace and newlines),
    and an indented code block cannot be closed by an argument containing a
    Markdown fence. This remains an ephemeral suffix rather than a durable
    compose layer because launch arguments are invocation state, not ticket
    state.
    """
    if not args:
        return ""
    encoded = json.dumps(args, ensure_ascii=False)
    return (
        "\n\n## Launch arguments\n\n"
        "The operator supplied these positional arguments to this launch, in "
        "order. Treat the JSON array as inputs to the launch target and "
        "preserve each value's boundary:\n\n"
        f"    {encoded}\n"
    )


# Linux caps a single execve() argument at MAX_ARG_STRLEN (32 pages =
# 131072 bytes). A composed prompt at or over it makes the PTY child's
# execvp fail with E2BIG before the agent ever starts. Stay under with
# headroom for a discussion template's text wrapped around `{prompt}`.
_MAX_PROMPT_ARG_BYTES = 120_000


def _argv_prompt(
    prompt: str, prompt_file: Path, marker_line: str = ""
) -> str:
    """The prompt as it rides argv: verbatim, or a file pointer when oversized.

    The prompt file is already on disk (written before the argv is built) and
    is only removed after the session ends, so the pointer stays valid for the
    agent's whole run. Same content, one indirection — the alternative is a
    guaranteed E2BIG exec failure. The pointer repeats the launch marker line
    so usage capture can still find it in the transcript's own message.
    """
    if len(prompt.encode()) <= _MAX_PROMPT_ARG_BYTES:
        return prompt
    return _prompt_pointer(prompt_file, marker_line)


def _prompt_pointer(
    prompt_file: Path, marker_line: str = "", *, separator: str = "\n"
) -> str:
    """The file-pointer message, repeating the launch marker on its own line.

    A Windows .cmd/.bat agent cannot receive raw CR/LF intact, so its pointer
    uses U+2028 LINE SEPARATOR instead. ``str.splitlines`` (usage capture's
    exact-line marker match) treats both as line boundaries.
    """
    pointer = (
        f"Read the file {prompt_file} in full before doing anything else — "
        "its contents are your complete composed Coga prompt, too large to "
        "pass as a command-line argument. Follow it exactly as if it had "
        "been given to you as this message."
    )
    if not marker_line:
        return pointer
    return f"{pointer}{separator}{separator}{marker_line}{separator}"


_BATCH_POINTER_SEPARATOR = "\u2028"


class AgentCommandRefused(ComposeError):
    """The final agent command cannot be represented on native Windows."""


def _plan_windows_agent_command(
    agent,
    *,
    env: Mapping[str, str],
    prompt: str | None,
    prompt_file: Path,
    marker_line: str,
    name: str = "",
    discussion: bool = False,
    session_id: str | None = None,
    kickoff: str | None = None,
):
    """Plan the Windows argv (full prompt or pointer) from serialized size."""
    from coga import repl_supervisor_nt

    def parts_for(prompt_arg: str) -> list[tuple[str, str]]:
        parts = _agent_command_parts(
            agent, prompt_arg, name=name, discussion=discussion,
            session_id=session_id,
        )
        if kickoff:
            parts.append((kickoff, "kickoff"))
        return parts

    try:
        return repl_supervisor_nt.plan_agent_command(
            parts_for,
            prompt=prompt,
            pointer_for=lambda batch: _prompt_pointer(
                prompt_file,
                marker_line,
                separator=_BATCH_POINTER_SEPARATOR if batch else "\n",
            ),
            env=env,
        )
    except repl_supervisor_nt.CommandRefused as exc:
        raise AgentCommandRefused(
            f"Cannot start agent {agent.name}: {exc}"
        ) from exc


def agent_command_refusal(
    agent,
    *,
    env: Mapping[str, str],
    ref: TargetRef,
    name: str = "",
    discussion: bool = False,
    kickoff: str | None = None,
) -> str | None:
    """Windows preflight: why this agent's command cannot be built, else None.

    Plans the pointer form, the smallest command a launch can use, before
    activation, draft creation or queue admission. The placeholder prompt
    path and marker have the real ones' width. A missing CLI is left to the
    caller's own CLI check. POSIX always returns None.
    """
    if os.name != "nt":
        return None
    placeholder = Path(oscompat.system_tmpdir()) / (
        f"coga-{ref.id_slug.replace('/', '-')}-XXXXXXXX.md"
    )
    try:
        _plan_windows_agent_command(
            agent,
            env=env,
            prompt=None,
            prompt_file=placeholder,
            marker_line=usage_tracking.launch_marker_line(str(UUID(int=0))),
            name=name,
            discussion=discussion,
            session_id=str(UUID(int=0)) if agent.session_id_flag else None,
            kickoff=kickoff,
        )
    except AgentCliNotFound:
        return None
    except AgentCommandRefused as exc:
        return str(exc)
    return None


def require_representable_agent_command(agent, **kwargs) -> None:
    """``agent_command_refusal`` as an exit-2 refusal with the sweep withheld."""
    refusal = agent_command_refusal(agent, **kwargs)
    if refusal is not None:
        _bail(refusal)


class AgentPreparationError(Exception):
    """Readiness refusal before a caller publishes startup state."""

    def __init__(self, reason: str, *, command_refused: bool = False) -> None:
        super().__init__(reason)
        self.command_refused = command_refused


class PreparedAgentLaunch(NamedTuple):
    """One fresh readiness pass; never retained across publication/reload."""

    agent: AgentType
    prompt: str | None
    env: dict[str, str]
    cli_path: str
    resolved_layers: ResolvedPromptLayers | None


def prepare_agent_launch(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    launch_agent: str,
    *,
    launch_context: LaunchContext = "attended",
    discussion: bool = False,
    kickoff: str | None = None,
    defer_prompt: bool = False,
    env_transform: Callable[[dict[str, str]], dict[str, str]] | None = None,
) -> PreparedAgentLaunch:
    """Validate CLI, prompt layers, secrets and command without repo writes.

    Ordinary launch defers rendering until it has the final ticket and checkout
    notice. Queue callers retain the prompt rendered during readiness.

    Callers own prospective lifecycle, admission and publication. Secret
    resolution may call an external provider; the result is not cached.
    ``env_transform`` maps the launch env to the env the caller will spawn
    with (megalaunch's supervised step identity); the command check and the
    returned ``env`` both use its result.
    """
    try:
        agent = cfg.agent_type(launch_agent)
        cli_path = shutil.which(agent.cli)
        if cli_path is None:
            raise AgentPreparationError(agent_cli_missing_message(agent.name, agent.cli))
        prompt = None
        resolved_layers = None
        if defer_prompt:
            resolved_layers = resolve_prompt_layers(
                cfg, ref, ticket, launch_context=launch_context
            )
        else:
            prompt = compose_prompt(cfg, ref, ticket, launch_context=launch_context)
        env = build_launch_env(cfg, ticket.secrets)
        if env_transform is not None:
            env = env_transform(env)
    except FileNotFoundError as exc:
        raise AgentPreparationError(missing_launch_file_message(exc)) from exc
    except (ConfigError, ComposeError, SecretError) as exc:
        raise AgentPreparationError(str(exc)) from exc
    refusal = agent_command_refusal(
        agent, env=env, ref=ref, name=ticket.title or "",
        discussion=discussion, kickoff=kickoff,
    )
    if refusal is not None:
        raise AgentPreparationError(refusal, command_refused=True)
    return PreparedAgentLaunch(agent, prompt, env, cli_path, resolved_layers)


def build_agent_command(
    agent,
    prompt: str,
    *,
    name: str = "",
    discussion: bool = False,
    session_id: str | None = None,
) -> list[str]:
    """Build the argv for spawning the agent.

    Default shape: `<cli> <launch_args...> <prompt>` — agent opens its REPL
    with the prompt as the first user message. The agent's `launch_args`
    tokens (shlex-split, empty by default) follow `<cli>` in both this and
    the discussion shape, so launch-mode flags such as Codex's `--no-daemon`
    apply to every interactive spawn.

    When the agent declares `name_flag` and a non-empty `name` is passed,
    `<name_flag> <name>` is inserted right after the CLI so the spawned
    session carries the ticket title in its picker / window title. Skipped
    in `discussion` mode so the human's first ask names the session.

    `session_id` uses the agent's `session_id_flag`, when configured, to pin a
    transcript id.

    `discussion=True` (used for human discussion sessions like `coga chat`
    and `coga ticket`) routes the prompt through the agent's
    `discussion = "..."` template in `coga.toml` so it lands as
    system/developer context instead of as the first user message. The agent
    opens with no user message, letting the human's first ask set the session
    title. Uses configured `agent.discussion`, then built-in templates for
    known `claude` / `codex` CLIs, then falls back to positional.
    """
    return [
        token
        for token, _ in _agent_command_parts(
            agent, prompt, name=name, discussion=discussion,
            session_id=session_id,
        )
    ]


def _agent_command_parts(
    agent,
    prompt: str,
    *,
    name: str = "",
    discussion: bool = False,
    session_id: str | None = None,
) -> list[tuple[str, str]]:
    """``build_agent_command``'s argv with each token's role.

    Roles name an argument in a refusal without printing its value.
    """
    cli = [(agent.cli, "agent CLI")]
    launch_args = [(tok, "launch option") for tok in shlex.split(agent.launch_args)]
    discussion_template = _discussion_template(agent) if discussion else ""
    if discussion_template:
        tokens = [
            (tok.replace("{prompt}", prompt), "discussion token")
            for tok in shlex.split(discussion_template)
        ]
        return [*cli, *launch_args, *tokens]
    name_args: list[tuple[str, str]] = []
    if name and agent.name_flag:
        name_args = [(tok, "title") for tok in [*shlex.split(agent.name_flag), name]]
    session_id_args: list[tuple[str, str]] = []
    if session_id and agent.session_id_flag:
        session_id_args = [
            (tok, "session ID")
            for tok in [*shlex.split(agent.session_id_flag), session_id]
        ]
    return [
        *cli,
        *launch_args,
        *name_args,
        *session_id_args,
        (prompt, "prompt"),
    ]


class AgentSessionResult(NamedTuple):
    exit_code: int
    termination_kind: str
    termination_reason: str | None = None
    # Whether the supervisor observed a matching done signal, independent of
    # `termination_kind` (a signal followed by a crash is still a `crash`).
    # False also means "no sentinel channel"; see `ReplOutcome`.
    done_signalled: bool = False
    exec_failed: bool = False


def missing_launch_file_message(exc: FileNotFoundError) -> str:
    """Report a pre-spawn `FileNotFoundError` as the missing file it is.

    `spawn_agent_session` composes the prompt and writes it to disk before its
    executable boundary (ordinary launches also append their audit there), so
    a `FileNotFoundError` escaping it is far more often a missing prompt layer
    than a missing agent CLI — and blaming the CLI sends the operator to debug
    a `cli` setting that is fine. Name the path instead; `AgentCliNotFound`
    carries the genuine CLI case.
    """
    missing = exc.filename or "a file it needed"
    detail = exc.strerror or str(exc)
    return (
        f"Launch failed before the agent started: {missing} ({detail}). "
        "This is a file the launch had to read or write — a prompt layer "
        "(skill, context, ticket) or the prompt destination — not the agent "
        "CLI."
    )


def spawn_agent_session(
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    ticket: Ticket,
    agent,
    *,
    env,
    actor: str,
    log_message: str,
    name: str = "",
    discussion: bool = False,
    kickoff: str | None = None,
    prompt_suffix: str = "",
    launch_context: LaunchContext = "attended",
    idle_timeout: float | None = None,
    max_session: float | None = None,
    label: str = "Launch",
    warn_blackboard: bool = False,
    commit_log: bool = False,
    assist_agent: str | None = None,
    validate_before_spawn: Callable[[], None] | None = None,
    before_spawn: Callable[[], None] | None = None,
    record_launch: bool = True,
    secrets_are_scoped: bool = True,
    stateless_identity: tuple[str, str] | None = None,
    include_blocker_preamble: bool = True,
    composed_prompt: str | None = None,
    resolved_layers: ResolvedPromptLayers | None = None,
) -> AgentSessionResult:
    """Spawn one agent process once.

    This is the shared single-shot body beneath `coga launch`'s supervisor
    chain: compose prompt, write prompt file, build argv, log, spawn under the
    PTY watcher for interactive REPLs, and remove the temp prompt file.

    Per-caller differences are arguments here, not forked command code:
    `env` carries the secrets policy (`coga launch` passes a launch env;
    authoring passes a scrubbed process env with no Coga secret injection),
    `discussion` selects discussion-prompt argv, and `kickoff` appends an
    optional first user turn such as the `coga ticket` greet-first "Begin".
    `stateless_identity` lets an authoring surface compose against a real task
    while recording the agent interaction under its bootstrap identity and
    title, with no workflow step. `launch_context` selects the one composed
    session-conduct layer and defaults to `"attended"`, so a caller that is
    not draining a queue gets the ask-a-present-human contract; `prompt_suffix`
    is left for genuinely appended invocation input such as
    `## Launch arguments`, never for conduct.
    `include_blocker_preamble` is disabled only for guided authoring: the
    resolve-or-re-block directive belongs to task execution, while an authoring
    session must leave a blocked ticket and its open asks intact.
    `composed_prompt` and `resolved_layers` carry already prepared prompt
    inputs. `assist_agent` gives lifecycle commands their audit attribution.
    """
    # A nested launch inherits its parent's process environment. Re-derive the
    # task metadata at this last shared boundary so an agent identifies the
    # task it is actually running. `apply_task_env` copies first, so
    # caller-owned environments remain unchanged and unrelated parent values
    # still pass through — but it clears the whole task namespace before
    # rewriting it, so a variable this target does not export (a stateless
    # bootstrap ticket's absent `COGA_TASK_BLACKBOARD`) cannot survive by
    # inheritance.
    env = apply_task_env(env, cfg, ref, ticket)
    if assist_agent is not None:
        env[ASSIST_AGENT_ENV] = assist_agent

    if warn_blackboard:
        warning = blackboard_size_warning(ref.ticket_path)
        if warning:
            _report(f"Warning: {warning}", fg='yellow', err=True)
        warning = uncomposed_sections_warning(ref.ticket_path)
        if warning:
            _report(f"Warning: {warning}", fg='yellow', err=True)

    if composed_prompt is None:
        _report(f"{label}: composing prompt")
        prompt = compose_prompt(
            cfg,
            ref,
            ticket,
            include_blocker_preamble=include_blocker_preamble,
            launch_context=launch_context,
            resolved=resolved_layers,
        )
    else:
        _report(f"{label}: using preflighted prompt")
        prompt = composed_prompt
    if prompt_suffix:
        prompt = f"{prompt}{prompt_suffix}"
    # A per-launch marker, last so everything before it stays a stable prompt
    # cache prefix. Usage capture uses it to pick this launch's transcript
    # when concurrent sessions share the cwd.
    launch_marker = str(uuid4())
    marker_line = usage_tracking.launch_marker_line(launch_marker)
    prompt = prompt.rstrip("\n") + f"\n\n{marker_line}\n"
    prompt_file = write_prompt_file(prompt, ref)
    _report(
        f"{label}: prompt written to {prompt_file} "
        f"({len(prompt)} chars)"
    )
    usage_session_id = (
        str(uuid4()) if agent.session_id_flag else None
    )
    windows_plan = None
    if os.name == "nt":
        # Windows budgets the complete serialized command, not one argument:
        # plan after every token (title, session id, kickoff) is known.
        try:
            windows_plan = _plan_windows_agent_command(
                agent,
                env=env,
                prompt=prompt,
                prompt_file=prompt_file,
                marker_line=marker_line,
                name=name,
                discussion=discussion,
                session_id=usage_session_id,
                kickoff=kickoff,
            )
        except BaseException:
            prompt_file.unlink(missing_ok=True)
            raise
        prompt_arg = windows_plan.prompt_arg
        if windows_plan.prompt_in_file:
            _report(
                f"{label}: the Windows command line cannot carry the prompt "
                f"— the agent will read it from {prompt_file}"
            )
    else:
        prompt_arg = _argv_prompt(prompt, prompt_file, marker_line)
        if prompt_arg is not prompt:
            _report(
                f"{label}: prompt exceeds the {_MAX_PROMPT_ARG_BYTES}-byte "
                f"single-argument limit — the agent will read it from "
                f"{prompt_file}"
            )

    usage_provider = usage_tracking.parser_key_for_cli(agent.cli)
    usage_pre_existing = usage_tracking.snapshot_session_files(usage_provider)
    usage_secret_values = _configured_secret_values(
        ticket, env, secrets_are_scoped=secrets_are_scoped
    )
    excluded_user_texts = tuple(
        dict.fromkeys(text for text in (prompt, prompt_arg, kickoff) if text)
    )
    usage_cwd = Path.cwd().resolve()
    usage_window_start = datetime.now(timezone.utc)
    spawn_started = False
    outcome_status: usage_tracking.OutcomeStatus = "unknown"
    outcome: ReplOutcome | None = None

    try:
        if windows_plan is not None:
            cmd = list(windows_plan.argv)
        else:
            cmd = build_agent_command(
                agent,
                prompt_arg,
                name=name,
                discussion=discussion,
                session_id=usage_session_id,
            )
            if kickoff:
                cmd.append(kickoff)
        _report(
            f"{label}: command: "
            f"{_format_agent_command_for_console(cmd, prompt)}"
        )

        if validate_before_spawn is not None:
            validate_before_spawn()

        if record_launch:
            append_log(cfg, ref.id_slug, actor, log_message)

        if name and sys.stdout.isatty():
            sys.stdout.write(f"\033]2;{name}\007")
            sys.stdout.flush()

        if before_spawn is not None:
            before_spawn()

        spawn_started = True
        # Agent CLIs (`claude`, `codex`) don't exit on their own. Run through a
        # PTY watcher so an agent that writes the session-done sentinel after
        # `coga bump` / `coga mark done` / `coga mark canceled` / `coga block`
        # releases the REPL.
        # Scope the sentinel by the task's `id_slug`, the identifier `bump` /
        # `mark` / `block` write. It must be the slug, not `ref.path.resolve()`:
        # a path-scoped marker only matches when the agent's `coga bump` ran
        # from the same checkout — a bump from a peer agent's separate clone
        # (or any other checkout of the repo) writes a different path, the
        # poll never matches, and the REPL hangs. The slug is the same from
        # any checkout, so teardown fires regardless of the bump's cwd.
        outcome = run_with_done_marker(
            cmd,
            env,
            session_id=ref.id_slug,
            terminal_status=(
                _terminal_status_probe(cfg, ref, ticket)
                if stateless_identity is None else None
            ),
            idle_timeout=idle_timeout,
            max_session=max_session,
        )
        outcome_status = _session_outcome_status(outcome)
        return AgentSessionResult(
            outcome.exit_code,
            outcome.kind,
            outcome.reason,
            outcome.done_signalled,
            outcome.exec_failed,
        )
    except KeyboardInterrupt:
        outcome_status = "interrupted"
        raise
    except FileNotFoundError:
        spawn_started = False
        raise
    except BaseException:
        outcome_status = "failed"
        raise
    finally:
        usage_window_end = datetime.now(timezone.utc)
        if spawn_started:
            stateless_session = stateless_identity is not None or isinstance(
                ref, BootstrapRef
            )
            session_slug = (
                stateless_identity[0] if stateless_identity else ref.id_slug
            )
            session_title = (
                stateless_identity[1]
                if stateless_identity
                else ticket.title or ""
            )
            usage_tracking.capture_session(
                cfg=cfg,
                title=session_title,
                slug=session_slug,
                step=None if stateless_session else _current_step_name(ticket),
                agent=agent.name,
                cli=agent.cli,
                cwd=usage_cwd,
                session_id=usage_session_id,
                pre_existing=usage_pre_existing,
                window_start=usage_window_start,
                window_end=usage_window_end,
                excluded_user_texts=excluded_user_texts,
                secret_values=usage_secret_values,
                outcome_status=outcome_status,
                exit_code=outcome.exit_code if outcome is not None else None,
                exit_kind=outcome.kind if outcome is not None else None,
                launch_marker=launch_marker,
            )
        try:
            prompt_file.unlink()
        except FileNotFoundError:
            pass


def _terminal_status_probe(
    cfg: Config, ref: TaskRef | BootstrapRef, ticket: Ticket,
) -> Callable[[], str | None] | None:
    """Observe terminal state in the local ticket if a sentinel is missed."""
    if isinstance(ref, BootstrapRef):
        return None

    cached_key: tuple[int, int, int] | None = None
    cached_status: str | None = None
    armed = False
    next_poll = 0.0
    terminal_since: float | None = None

    def probe() -> str | None:
        nonlocal cached_key, cached_status, armed, next_poll, terminal_since
        now = time.monotonic()
        if now < next_poll:
            return None
        next_poll = now + 1.0
        try:
            stat = ref.ticket_path.stat()
            key = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
            if key != cached_key:
                current = Ticket.read(ref.ticket_path)
                status = current.status
                cached_status = status if isinstance(status, str) and status in TERMINAL_STATUSES else None
                cached_key = key
        except (OSError, TicketError, UnicodeError):
            cached_key = cached_status = None
        if cached_status is None:
            armed, terminal_since = True, None
        elif armed:
            # A ticket terminal since launch is not this session's transition.
            if terminal_since is None:
                terminal_since = now
            elif now - terminal_since >= 5.0:
                return cached_status
        return None

    return probe


def _is_discussion_bootstrap(ref: TaskRef | BootstrapRef) -> bool:
    return isinstance(ref, BootstrapRef) and ref.id_slug in DISCUSSION_BOOTSTRAP_TICKETS


def _bootstrap_kickoff(ref: TaskRef | BootstrapRef) -> str | None:
    if isinstance(ref, BootstrapRef) and ref.id_slug == "bootstrap/ticket":
        return "Begin"
    return None


def _configured_secret_values(
    ticket: Ticket,
    env: dict[str, str],
    *,
    secrets_are_scoped: bool,
) -> tuple[str, ...] | None:
    """Return exact configured values, or None when safe redaction is unknown."""
    try:
        declared = parse_inline_secrets(ticket.secrets)
    except SecretError:
        return None
    values: list[str] = []
    for name, ref in declared:
        if secrets_are_scoped:
            value = env.get(name)
        elif ref.startswith("env:"):
            value = env.get(ref[len("env:") :])
        else:
            # Ambient authoring sessions deliberately do not resolve op://
            # references. A same-named process variable is not proof of the
            # configured value, so suppress activity content rather than risk
            # committing an unredacted secret.
            return None
        if value is None:
            return None
        values.append(value)
    return tuple(values)


def _session_outcome_status(outcome) -> usage_tracking.OutcomeStatus:
    if outcome.kind == "timeout":
        return "timed_out"
    # Codex can die by SIGINT on a fast double Ctrl-C; that is an interrupt.
    if outcome.kind == "crash" and outcome.exit_code == 128 + signal.SIGINT:
        return "interrupted"
    if outcome.kind == "crash" or outcome.exit_code != 0:
        return "failed"
    return "completed"


def _current_step_name(ticket: Ticket) -> str | None:
    current = ticket.current_step()
    if isinstance(current, dict):
        name = current.get("name")
        if isinstance(name, str):
            return name
    return None


def _discussion_template(agent) -> str:
    if agent.discussion:
        return agent.discussion
    return DEFAULT_DISCUSSION_TEMPLATES.get(Path(agent.cli).name, "")


def _echo_launch_iteration(
    cfg: Config, ref: TaskRef | BootstrapRef, ticket: Ticket
) -> None:
    current = ticket.current_step()
    operator = _operator_display(cfg, ref, ticket)
    if current is None:
        _report(
            f"→ launching {ref.id_slug} "
            f"(status={ticket.status}, operator={operator})"
        )
        return
    _report(
        f"→ entering step {ticket.step}: {current['name']} "
        f"(status={ticket.status}, operator={operator})"
    )


def _format_agent_command_for_console(cmd: list[str], prompt: str) -> str:
    display = [
        f"<prompt-text {len(prompt)} chars>" if value == prompt else value
        for value in cmd
    ]
    return shlex.join(display)


def _harness_stop_reason(
    ref: TaskRef,
    before: Ticket,
    after: Ticket,
    cfg: Config,
    *,
    chain_agent_override: str | None = None,
) -> str | None:
    if after.status != "in_progress":
        if after.status in TERMINAL_STATUSES:
            return f"{ref.id_slug}: task is {after.status}"
        if after.status == "paused":
            return f"{ref.id_slug}: task is paused"
        return f"{ref.id_slug}: task status is {after.status!r}"

    # A workflow-less task has no step machinery — the whole ticket is the one
    # unit of work, and the supervisor only ever chains *across workflow steps*.
    # Reaching here means the agent exited (often after emitting the session-done
    # marker) without `coga mark done`, so it is still in_progress. There is
    # nothing to advance to; stop and return to the caller. This is distinct from
    # the no-progress case below — don't report it as "still on no workflow
    # step", which reads as a failed step advance.
    if not isinstance(after.workflow, dict):
        return (
            f"{ref.id_slug}: no workflow to chain — task is still in_progress "
            "(agent exited without `coga mark done`); stopping"
        )

    if after.step == before.step:
        return f"{ref.id_slug}: still on {after.step}; stopping"

    current = after.current_step()
    if current is None:
        return f"{ref.id_slug}: no current workflow step; stopping"

    # The supervisor chains across agent steps — including main <-> peer
    # rotations, relaunching the next step's agent as a fresh process. It only
    # returns control to the caller when the next step hands off to the OWNER.
    # The discriminator is the step's role, NOT "did the nickname change" — a
    # skill-less agent step is still the agent's turn and chains.
    if (
        chain_agent_override is not None
        and _explicit_step_role(current) == "agent"
        and chain_agent_override in cfg.agents
    ):
        return None
    try:
        operator = _target_operator(cfg, ref, after)
    except OperatorResolutionError as exc:
        return f"{ref.id_slug}: cannot derive the next operator ({exc}); stopping"
    if operator is None:
        return f"{ref.id_slug}: no current operator; returning to caller"
    if operator.is_human:
        return (
            f"{ref.id_slug}: next step hands off to {operator.name}; "
            "returning to caller"
        )

    return None


def _format_prompt_report(id_slug: str, composition: PromptComposition) -> str:
    lines = [
        f"Prompt report for {id_slug}",
        "Approximate tokens use characters / 4; exact tokenizer parity is not assumed.",
        "",
        f"{'layer':<20} {'ref':<34} {'bytes':>10} {'approx_tokens':>14}",
        f"{'-' * 20} {'-' * 34} {'-' * 10} {'-' * 14}",
    ]
    for layer in composition.layers:
        ref = layer.ref or "-"
        if len(ref) > 34:
            ref = ref[:31] + "..."
        lines.append(
            f"{layer.layer:<20} {ref:<34} "
            f"{format_bytes(layer.byte_count):>10} {layer.approx_tokens:>14}"
        )
    lines.extend([
        "",
        f"Total composed prompt: {format_bytes(composition.byte_count)} "
        f"(~{composition.approx_tokens} tokens)",
    ])
    # Fixed layers read packaged text unless the repo overrides it under
    # `<coga root>/resources/`; the override is the layer's `path`.
    overrides = [
        layer for layer in composition.layers
        if layer.ref in RESOURCE_NAMES and layer.path
    ]
    if overrides:
        lines.extend(["", "Repo resource overrides:"])
        lines.extend(
            f"  {layer.layer}: {layer.ref} <- {layer.path}" for layer in overrides
        )
    return "\n".join(lines)


def _launch_log_message(
    operator: str,
    launch_agent: str,
    agent_name: str,
) -> str:
    """Audit line for one spawn.

    Names the *actual* worker. When an ephemeral override makes that differ from
    the configured operator, record both, so the launch record stays a faithful
    account of who ran while the ticket keeps its unchanged routing.
    """
    if launch_agent == operator:
        return f"launched (operator={operator}, agent={agent_name})"
    return (
        f"launched "
        f"(operator={operator}, launch_agent={launch_agent}, agent={agent_name})"
    )


def _refuse_human_handoff_launch(
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    ticket: Ticket,
    agent_override: str | None,
) -> None:
    """Refuse to run an agent on a step the workflow hands to a human.

    Keyed on the step's *role*, not on whether the derived name happens to be
    missing from `[agents.*]`: a human whose nickname matches an agent type must
    still be a handoff. An explicit `--agent` override is the one authorized way
    past this, and it assists that single human step without changing routing.
    """
    if isinstance(ref, BootstrapRef) or agent_override is not None:
        return
    try:
        operator = _target_operator(cfg, ref, ticket)
    except OperatorResolutionError as exc:
        _bail(f"Cannot launch {ref.id_slug}: {exc}")
        return
    if operator is None or not operator.is_human:
        return
    _bail(
        f"Cannot launch {ref.id_slug}: its current step hands off to the owner "
        f"({operator.name}), not to an agent. Advance the workflow to an agent "
        f"step, or pass `--agent <type>` to run one explicit assisting session "
        "on this human step."
    )


def interactive_stdio_has_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _refuse_tty_launch(
    ref: TaskRef | BootstrapRef,
    *,
    exit_code: int = 2,
) -> None:
    _bail(
        f"Cannot launch {ref.id_slug!r}: an agent launch requires a TTY "
        "(stdin and stdout must both be terminals). Run from a real "
        "shell. A directory-form ticket can instead own deterministic "
        "unattended work in the exact sibling `ticket.py`.",
        exit_code=exit_code,
    )


def _refresh_agent_skills_for_launch(coga_os: Path) -> None:
    from coga.paths import LocalOverrideError

    try:
        result = refresh_agent_skill_view(coga_os)
    except LocalOverrideError as exc:
        raise LaunchBail(2, str(exc)) from exc
    except OSError as exc:
        _report(
            f"Warning: could not refresh agent skill view: {exc}",
            fg='yellow',
            err=True,
        )
        return
    if result.skipped:
        skipped = ", ".join(result.skipped[:5])
        suffix = "…" if len(result.skipped) > 5 else ""
        _report(
            f"Warning: skipped {len(result.skipped)} agent skill link(s): {skipped}{suffix}",
            fg='yellow',
            err=True,
        )


class LaunchBail(RuntimeError):
    """A launch refusal that keeps its message beside the exit code.

    A caller that catches the exit in-process (the recurring sweep) records
    `reason`, so a refusal before `ticket.py` runs is not a bare exit code
    beside a blank blackboard.
    """

    def __init__(self, code: int, reason: str = "") -> None:
        super().__init__(reason or f"Launch ended with exit {code}")
        self.code = code
        self.reason = reason


def _bail(msg: str, *, exit_code: int = 2) -> None:
    raise LaunchBail(exit_code, msg)
