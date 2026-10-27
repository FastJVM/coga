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
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, NamedTuple, TypeVar
from uuid import uuid4

from typer import Exit as NotificationExit

from coga import usage as usage_tracking
from coga.agent_cli_setup import offer_agent_cli
from coga.aliases import ONBOARDING_TASK
from coga.agent_skills import refresh_agent_skill_view
from coga.autoclose import parse_branch_name, parse_pr_url, parse_worktree_path
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
    CheckoutNotice,
    PromptComposition,
    compose_prompt,
    compose_prompt_report,
    write_prompt_file,
)
from coga.oscompat import lock_fd
from coga.config import (
    build_launch_env,
    Config,
    ConfigError,
    parse_inline_secrets,
    SecretError,
    load_config,
)
from coga.dependencies import agent_cli_missing_message
from coga.github_preflight import check_git_auth, check_git_remote
from coga import checkouts
from coga import git
from coga import pr_assist
from coga.checkout_policy import select_checkout_policy
from coga.lifecycle import TERMINAL_STATUSES
from coga.launch_script import run_script_chain, script_entry_point
from coga.logfile import append_log, log_path
from coga.paths import RESOURCE_NAMES, RepoResourceUnreadable
from coga.mark import (
    MainAgentUnavailable,
    BlackboardNeedsSynthesis,
    RequiredExtensionMissing,
    WorkflowMissing,
    format_blackboard_synthesis_refusal,
    mark_active,
    mark_blocked,
    mark_in_progress,
    prepare_active,
)
from coga.notification import preflight_post
from coga.open_pr import same_git_checkout
from coga.repl_supervisor import (
    ASSIST_AGENT_ENV,
    ASSIST_BRANCH_ENV,
    ASSIST_PR_ENV,
    CHECKOUT_RETURN_ENV,
    AgentCliNotFound,
    ReplOutcome,
    build_supervised_step_env,
    run_with_done_marker,
    unsignalled_advance_warning,
)
from coga.recurring import PeriodLease, local_period_lease, same_period_lease
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
    PENDING_LAUNCH_GENERATION_PREFIX,
    Ticket,
    TicketError,
    admitted_launch_generation,
    pending_launch_generation,
    released_launch_generation,
)
from coga.validate import TaskValidationError
from coga.workflow import WorkflowError


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
_ASSIST_ALIGNMENT_ATTEMPTS = 3
_T = TypeVar("_T")

WINDOWS_AGENT_SESSION_MESSAGE = (
    "agent sessions are not supported on native Windows yet; see "
    "v1/14-interactive-coga-launch-on-native-windows."
)


def agent_sessions_supported() -> bool:
    return os.name != "nt"


def require_agent_sessions() -> None:
    """Refuse an agent entry before writes, including the CLI exit sweep."""
    if not agent_sessions_supported():
        _bail(WINDOWS_AGENT_SESSION_MESSAGE, exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE)


def _preflight_platform_target(task: str, *, prompt_report: bool) -> None:
    """Only a locally visible script can admit work on native Windows.

    This read-only classifier precedes checkout preparation, recurring
    catch-up, chat receipts and draft creation. Missing/stale targets cannot
    justify moving the checkout to discover whether they need an agent.
    The normal path reclassifies after every sync as before.
    """
    if prompt_report or agent_sessions_supported():
        return
    try:
        cfg = load_config()
        ref = resolve_target(cfg, task)
    except (ConfigError, TaskNotFoundError):
        require_agent_sessions()
        return
    if script_entry_point(ref) is None:
        require_agent_sessions()


_CHECKOUT_GUARD_SCOPE: ContextVar[ExitStack | None] = ContextVar(
    "checkout_guard_scope", default=None
)
# The live direct chat this process guards, for its runtime checkout notice.
_CHAT_SESSION: ContextVar[checkouts.ChatSession | None] = ContextVar(
    "chat_session", default=None
)


@contextmanager
def checkout_guard_scope() -> Iterator[None]:
    """Keep launch's checkout guard through the CLI's final state sweep."""
    with ExitStack() as stack:
        token = _CHECKOUT_GUARD_SCOPE.set(stack)
        try:
            yield
        finally:
            _CHECKOUT_GUARD_SCOPE.reset(token)


@contextmanager
def _orientation_checkout_guard(cfg: Config) -> Iterator[None]:
    """Refuse a second direct chat before it can publish or move this checkout.

    Unlike the short publication lock, this nonblocking lock spans the whole
    command. It is keyed by Git toplevel, so nested Coga roots share it while
    separate checkouts do not. The kernel releases it on process exit; the
    file is deliberately never unlinked (which would permit two lock inodes).
    Once held, a companion receipt names this live session and its one
    reserved branch name, which `coga run prepare-checkout` must match.
    """
    if not cfg.git_enabled:
        yield
        return
    try:
        root = git.toplevel(cfg.repo_root)
    except git.GitError as exc:
        _bail(
            f"Cannot guard this chat's checkout: {exc}. No work was started.",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    if root is None:
        yield
        return
    try:
        lock_file, _ = checkouts.orientation_lock_paths(root)
        lock_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR, 0o600)
    except OSError as exc:
        _bail(
            f"Cannot guard this chat's checkout: {exc}. No work was started.",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    try:
        try:
            lock_fd(fd, blocking=False)
        except BlockingIOError:
            _bail(
                "Cannot launch bootstrap/orient: another chat is using this "
                f"checkout ({root}). Finish that chat or use a separate "
                "checkout. No work was started and the checkout was not changed.",
                exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
            )
        except OSError as exc:
            _bail(
                f"Cannot guard this chat's checkout: {exc}. No work was started.",
                exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
            )
        try:
            session = checkouts.install_chat_session(cfg, root)
        except (OSError, git.GitError) as exc:
            _bail(
                f"Cannot record this chat's session: {exc}. No work was started.",
                exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
            )
        token = _CHAT_SESSION.set(session)
        try:
            yield
        finally:
            try:
                _CHAT_SESSION.reset(token)
            except ValueError:  # released from the CLI's outer sweep scope
                _CHAT_SESSION.set(None)
            checkouts.clear_chat_session(cfg, session)
    finally:
        os.close(fd)


class _RecomposeAfterLaunchPublication(RuntimeError):
    """A caller-owned start publication completed; rebuild before spawning."""


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
) -> LaunchResult:
    """Launch with ordinary Python defaults, returning a result or LaunchBail.

    Queue callers use the specialized recurring/delegation entry points below.
    No command-line parser objects or process exits cross this boundary.
    """
    _preflight_platform_target(task, prompt_report=prompt_report)
    with ExitStack() as local_scope:
        if task == "bootstrap/orient" and not prompt_report:
            try:
                cfg = load_config()
            except ConfigError as exc:
                _bail(str(exc))
            # CLI dispatch owns cleanup through its exit sweep. Direct Python
            # callers have no outer sweep, so their guard ends with this call.
            scope = _CHECKOUT_GUARD_SCOPE.get() or local_scope
            scope.enter_context(_orientation_checkout_guard(cfg))
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
            before_recompose=None,
            before_final_spawn=None,
            require_agent_target=False,
            record_launch=True,
            recurring_authorized=False,
        )



class RecurringPeriodLaunchResult(NamedTuple):
    """One ordinary launch with its child generation and publication class."""

    kind: str | None
    period_lease: PeriodLease | None
    require_period_publication: bool


@_launch_error_boundary()
def launch_recurring_period(
    task: str,
    *,
    expected_period_lease: PeriodLease,
    control_remote_expected: bool,
    agent_override: str | None,
    prompt_report: bool,
    idle_timeout: float | None,
    max_session: float | None,
    return_timeout: bool,
    script_failure_important: bool,
    launch_context: LaunchContext,
    agent_spawn_refusal: str | None = None,
) -> RecurringPeriodLaunchResult:
    """Launch one period after the recurring runner admitted the sweep.

    This is an in-process capability, not a Typer option. ``coga recurring``
    performs the full admission pass at its outer boundary. A prior child can
    run long enough for another checkout to pause, finish, or replace a later
    period, though, so this seam refreshes and rechecks that one period before
    entering shared launch logic. The caller supplies the exact ticket/audit
    generation admitted before any prior child ran. ``control_remote_expected``
    freezes whether that outer admission saw a configured remote: an admitted
    remote-less checkout uses local control state, while a remote that later
    disappears remains a failed verification. A lost refresh fails closed; a
    period that became closed, parked, or replaced returns
    ``"skipped"`` without starting work. The result also carries the exact
    refreshed generation admitted before a deterministic child, or the exact
    generation recaptured immediately before the last agent spawn. The sweep
    can therefore compare-and-set any unfinished-child pause without touching
    a replacement that arrived while either kind of child was running.
    ``agent_spawn_refusal`` is the runner's hard execution boundary for a
    headless or temporary-worktree sweep. A frozen ``ticket.py`` may be a
    hybrid deterministic/agent phase; when it leaves agent work open, shared
    launch returns before every agent setup or spawn and lets the runner park
    that exact period.
    """
    if not _refresh_recurring_period_before_launch(
        task,
        expected_period_lease,
        control_remote_expected=control_remote_expected,
    ):
        return RecurringPeriodLaunchResult("skipped", None, False)

    publication_cfg, publication_ref = _exact_recurring_period_for_launch(
        task, boundary="publication preflight"
    )
    require_period_publication = _preflight_push_auth(
        publication_cfg,
        publication_ref,
        is_bootstrap=False,
    )

    # The refresh above proved this exact generation immediately before shared
    # launch setup. A pure ticket.py child has no agent-spawn callback, so keep
    # that admitted lease as its teardown witness. Agent-backed launches verify
    # the same generation and replace only its exact ticket bytes at the tighter
    # boundary immediately before every actual spawn.
    launched_period_lease = expected_period_lease

    def capture_launched_period_lease(expected_ticket: Ticket) -> None:
        """Freeze the exact composed period immediately before agent spawn."""
        nonlocal launched_period_lease
        current_cfg, current_ref = _exact_recurring_period_for_launch(
            task, boundary="agent spawn"
        )
        current_period_lease = local_period_lease(current_cfg, current_ref)
        if current_period_lease.generation != expected_period_lease.generation:
            _bail(
                f"{task} belongs to a different period generation at agent "
                "spawn; not launching."
            )
        try:
            if current_period_lease.ticket_bytes is None:
                raise TicketError("period ticket disappeared")
            current_ticket = Ticket.parse(
                current_period_lease.ticket_bytes.decode()
            )
        except (UnicodeError, TicketError) as exc:
            _bail(f"Cannot launch {task}: invalid period state at agent spawn: {exc}")
        if current_ticket.status != "in_progress":
            _bail(
                f"Cannot launch {task}: period became {current_ticket.status!r} "
                "before agent spawn. No work was started."
            )
        if current_ticket != expected_ticket:
            _bail(
                f"Cannot launch {task}: period state changed after prompt "
                "composition. No work was started."
            )
        launched_period_lease = current_period_lease

    result = _launch(
        task,
        args=None,
        agent_override=agent_override,
        prompt_report=prompt_report,
        idle_timeout=idle_timeout,
        max_session=max_session,
        return_timeout=return_timeout,
        script_failure_important=script_failure_important,
        launch_context=launch_context,
        before_recompose=None,
        before_final_spawn=capture_launched_period_lease,
        require_agent_target=False,
        record_launch=True,
        recurring_authorized=True,
        agent_spawn_refusal=agent_spawn_refusal,
    )
    if git.state_sweep_withheld.get():
        # The checkout return refused (already reported) and preserved dirt
        # the sweep must not publish or disturb: stop it through the
        # retained-state exit instead of pausing this period and moving on.
        raise LaunchBail(git.RETRY_WITHOUT_SWEEP_EXIT_CODE)
    return RecurringPeriodLaunchResult(
        result.kind,
        launched_period_lease,
        require_period_publication,
    )


def _exact_recurring_period_for_launch(
    task: str, *, boundary: str
) -> tuple[Config, TaskRef]:
    """Resolve one canonical period ref without permitting prefix fallback."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))
    ref = next(
        (candidate for candidate in list_tasks(cfg) if candidate.id_slug == task),
        None,
    )
    if ref is None or ref.directory != "recurring":
        _bail(
            f"Cannot launch {task}: its exact recurring period disappeared "
            f"before {boundary}. No work was started."
        )
    return cfg, ref


def _refresh_recurring_period_before_launch(
    task: str,
    expected_period_lease: PeriodLease,
    *,
    control_remote_expected: bool,
) -> bool:
    """Refresh and re-admit the exact period generation selected by a sweep."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    from coga.recurring_runner import (
        _control_remote_present_at_admission,
        _refuse_non_control_branch,
        _refuse_non_owner,
    )

    if _refuse_non_control_branch(cfg) or _refuse_non_owner(cfg):
        raise LaunchBail(2)
    remote_present_now = _control_remote_present_at_admission(cfg)
    if not control_remote_expected and not remote_present_now:
        # This sweep was admitted in the supported local-only Git class. The
        # branch/owner gates above and exact ticket lease below remain active;
        # there is simply no distinct control destination to refresh from.
        refreshed = True
    elif not remote_present_now:
        # The remote this sweep was admitted against has vanished: a refresh
        # that cannot fetch is not a verified per-child refresh.
        refreshed = False
    else:
        refreshed = git.refresh(cfg)
    if refreshed is False:
        _bail(
            f"Cannot launch {task}: the latest control state could not be "
            "verified after the preceding recurring child. No work was started."
        )
    try:
        cfg = load_config(cfg.repo_root)
    except ConfigError as exc:
        _bail(str(exc))
    ref = next(
        (candidate for candidate in list_tasks(cfg) if candidate.id_slug == task),
        None,
    )
    if ref is None:
        _report(
            f"{task} no longer exists on control; not launching.",
            fg='yellow',
        )
        return False
    if ref.directory != "recurring":
        _bail(
            f"Internal recurring launch expected exact period ref {task!r}, "
            f"but found it in {ref.directory!r}."
        )
    if _refuse_non_control_branch(cfg) or _refuse_non_owner(cfg):
        raise LaunchBail(2)
    current_period_lease = local_period_lease(cfg, ref)
    if not same_period_lease(current_period_lease, expected_period_lease):
        _report(
            f"{ref.id_slug} belongs to a different ticket/period generation "
            "on control; not launching.",
            fg='yellow',
        )
        return False
    try:
        if current_period_lease.ticket_bytes is None:
            raise TicketError("period ticket disappeared")
        ticket = Ticket.parse(current_period_lease.ticket_bytes.decode())
    except (UnicodeError, TicketError) as exc:
        _bail(str(exc))
    if ticket.status not in {"active", "in_progress"}:
        _report(
            f"{ref.id_slug} became {ticket.status} on control; not launching.",
            fg='yellow',
        )
        return False
    return True


@_launch_error_boundary()
def launch_with_before_spawn(
    task: str,
    *,
    agent_override: str | None,
    idle_timeout: float | None,
    max_session: float | None,
    return_timeout: bool,
    script_failure_important: bool = False,
    launch_context: LaunchContext,
    before_spawn: Callable[[], None],
    revalidate_before_spawn: Callable[[Ticket], None] | None = None,
) -> LaunchResult:
    """Publish caller state after preflight, then re-derive and spawn once.

    Recurring delegation uses this typed in-process seam to publish its period
    task's `in_progress` state only after target resolution, TTY/CLI checks,
    prompt composition, secret preflights, and argv construction have all
    succeeded. Publication can move the control checkout, so that first pass
    makes its launch audit durable, runs the callback, and deliberately stops
    before spawn; a second shared launch pass reloads config and target state,
    repeats every preflight, re-composes without duplicating that audit, and
    then starts the bootstrap agent. A separate final callback can lease
    caller-owned state again immediately before the PTY spawn. The CLI surface
    remains callback-free.
    """
    try:
        return _launch(
            task,
            args=None,
            agent_override=agent_override,
            prompt_report=False,
            idle_timeout=idle_timeout,
            max_session=max_session,
            return_timeout=return_timeout,
            script_failure_important=script_failure_important,
            launch_context=launch_context,
            before_recompose=before_spawn,
            before_final_spawn=None,
            require_agent_target=True,
            record_launch=True,
            recurring_authorized=False,
        )
    except _RecomposeAfterLaunchPublication:
        return _launch(
            task,
            args=None,
            agent_override=agent_override,
            prompt_report=False,
            idle_timeout=idle_timeout,
            max_session=max_session,
            return_timeout=return_timeout,
            script_failure_important=script_failure_important,
            launch_context=launch_context,
            before_recompose=None,
            before_final_spawn=revalidate_before_spawn,
            require_agent_target=True,
            record_launch=False,
            recurring_authorized=False,
        )


def _reconcile_released_launch_admission(
    cfg: Config,
    ticket_path: Path,
    *,
    expected_ticket_bytes: bytes,
) -> bytes:
    """Turn one local ``released:`` witness into a durable admitted claim.

    A post-gate admission failure cannot restore ``pending:``: the child was
    already able to execute, even though the supervisor then terminated it.
    Megalaunch therefore retains ``released:<uuid>`` only in its checkout.
    An explicit ordinary launch calls this boundary before recovery. It accepts
    control only when the whole remote ticket is either the matching pending
    revision (publication definitely failed) or the matching plain revision
    (an ambiguous push actually landed), then publishes the plain UUID with
    that exact control copy as its `expect`. Every failure restores the local
    ``released:`` witness so a later retry remains recognizable, and the sweep
    never publishes a released witness on its own.
    """
    with git.state_lock(cfg):
        try:
            current_bytes = ticket_path.read_bytes()
        except OSError as exc:
            raise git.GitError(
                f"could not read released launch admission: {exc}"
            ) from exc
        if current_bytes != expected_ticket_bytes:
            raise git.StateRegressionError(
                "released launch admission changed before reconciliation"
            )
        try:
            released_ticket = Ticket.parse(current_bytes.decode("utf-8"))
        except (UnicodeDecodeError, TicketError) as exc:
            raise git.GitError(
                f"released launch admission is unreadable: {exc}"
            ) from exc
        generation = released_ticket.launch_generation
        if not released_launch_generation(generation):
            raise git.StateRegressionError(
                "launch admission is no longer awaiting released-state "
                "reconciliation"
            )
        assert generation is not None
        if not cfg.git_enabled:
            raise git.GitError(
                "released launch admission requires Git sync to reconcile its "
                "pending control revision"
            )

        root = git.toplevel(ticket_path)
        if root is None:
            raise git.GitError("released launch admission requires a Git checkout")
        if not git.remote_configured(root, cfg.git_remote):
            raise git.GitError(
                f"remote {cfg.git_remote!r} is unavailable for released "
                "launch-admission reconciliation"
            )
        if not git.control_branch_present(
            root, cfg.git_control_branch, cfg.git_remote
        ):
            raise git.GitError(git.control_branch_mismatch_message(cfg, root))

        admitted_ticket = Ticket(
            frontmatter=dict(released_ticket.frontmatter),
            body=released_ticket.body,
        )
        admitted_ticket.frontmatter["launch_generation"] = (
            admitted_launch_generation(generation)
        )
        admitted_bytes = admitted_ticket.render().encode("utf-8")
        pending_ticket = Ticket(
            frontmatter=dict(released_ticket.frontmatter),
            body=released_ticket.body,
        )
        pending_ticket.frontmatter["launch_generation"] = (
            f"{PENDING_LAUNCH_GENERATION_PREFIX}"
            f"{admitted_launch_generation(generation)}"
        )
        pending_bytes = pending_ticket.render().encode("utf-8")

        base = git.fetch_control(cfg, root)
        rel = git.relative_to_root(root, ticket_path)
        control_bytes = git.tree_bytes(root, base, rel)
        if control_bytes not in {pending_bytes, admitted_bytes}:
            raise git.StateRegressionError(
                f"{rel}: control ticket changed before released "
                "launch-admission reconciliation"
            )
        # The fetch is a network wait; an edit made during it must not be
        # overwritten by the admitted rendering of the older witness.
        if ticket_path.read_bytes() != current_bytes:
            raise git.StateRegressionError(
                "released launch admission changed during reconciliation"
            )

        try:
            admitted_ticket.write(ticket_path)
            git.publish(
                cfg,
                [ticket_path],
                "Ticket: reconcile released launch admission",
                expect={ticket_path: control_bytes},
            )
        except (git.GitError, OSError) as exc:
            # Put the witness back: it is what makes the next attempt
            # recognizable, whether the publish was refused or unknown.
            ticket_path.write_bytes(current_bytes)
            if isinstance(exc, OSError):
                raise git.GitError(
                    f"could not record reconciled launch admission: {exc}"
                ) from exc
            raise
        return admitted_bytes


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
    before_recompose: Callable[[], None] | None,
    before_final_spawn: Callable[[Ticket], None] | None,
    require_agent_target: bool,
    record_launch: bool,
    recurring_authorized: bool,
    agent_spawn_refusal: str | None = None,
) -> LaunchResult:
    """Run the fixed launch phases; each may finish without starting an agent."""
    if agent_spawn_refusal is None:
        _preflight_platform_target(task, prompt_report=prompt_report)
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
        before_recompose=before_recompose,
        before_final_spawn=before_final_spawn,
        require_agent_target=require_agent_target,
        record_launch=record_launch,
        recurring_authorized=recurring_authorized,
        agent_spawn_refusal=agent_spawn_refusal,
    )
    for prepare in (
        invocation._prepare_target,
        invocation._align_and_classify,
        invocation._run_initial_script,
        invocation._prepare_agent,
    ):
        result = prepare()
        if result is not None:
            return result
    return invocation._supervise_steps()


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
        before_recompose: Callable[[], None] | None,
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
        self.before_recompose = before_recompose
        self.before_final_spawn = before_final_spawn
        self.require_agent_target = require_agent_target
        self.record_launch = record_launch
        self.recurring_authorized = recurring_authorized
        self.agent_spawn_refusal = agent_spawn_refusal
        self.script_retained_state = False
        self.kept_checkout_reason: str | None = None

    def _prepare_target(self) -> LaunchResult | None:
        """Resolve and admit the current target, including delegated periods."""
        self.launch_args = list(self.args or [])

        try:
            self.cfg = load_config()
        except ConfigError as exc:
            _bail(str(exc))

        direct_recurring_prefix = (
            not self.recurring_authorized
            and not self.prompt_report
            and self.task.startswith("recurring/")
        )

        def authorize_direct_recurring(current_cfg: Config) -> Config:
            """Gate and refresh one public period launch before state lookup."""
            from coga.recurring_runner import (
                _control_remote_present_at_admission,
                _refuse_non_control_branch,
                _refuse_non_owner,
                _sync_control_checkout_ahead,
            )

            if _refuse_non_control_branch(current_cfg) or _refuse_non_owner(current_cfg):
                raise LaunchBail(2)
            try:
                remote_present_at_admission = _control_remote_present_at_admission(
                    current_cfg
                )
            except git.GitError as exc:
                _bail(
                    f"Cannot launch {self.task}: control-state verification failed: "
                    f"{exc}. No work was started.",
                    exit_code=git.STALE_CONTROL_EXIT_CODE,
                )
            catchup = _sync_control_checkout_ahead(
                current_cfg, announce_failure=False
            )
            if not catchup.fresh and current_cfg.git_enabled:
                try:
                    control_checkout = git.toplevel(current_cfg.repo_root)
                    remote_present_now = _control_remote_present_at_admission(
                        current_cfg
                    )
                except git.GitError as exc:
                    _bail(
                        f"Cannot launch {self.task}: control-state verification failed: "
                        f"{exc}. No work was started.",
                        exit_code=git.STALE_CONTROL_EXIT_CODE,
                    )
                if control_checkout is not None and (
                    remote_present_at_admission or remote_present_now
                ):
                    _bail(
                        f"Cannot launch {self.task}: could not confirm this checkout "
                        f"includes the latest {current_cfg.git_remote}/"
                        f"{current_cfg.git_control_branch}: {catchup.reason}. "
                        "No work was started.",
                        exit_code=git.STALE_CONTROL_EXIT_CODE,
                    )
            try:
                refreshed_cfg = load_config(current_cfg.repo_root)
            except ConfigError as exc:
                _bail(str(exc))
            if _refuse_non_control_branch(refreshed_cfg) or _refuse_non_owner(
                refreshed_cfg
            ):
                raise LaunchBail(2)
            return refreshed_cfg

        # An explicit recurring ref may exist only on the remote control tip. Gate
        # and catch up from its namespace before resolving it locally; resolving
        # first made a safely materialized remote period look nonexistent.
        if direct_recurring_prefix:
            self.cfg = authorize_direct_recurring(self.cfg)

        # An ordinary ticket launch runs from a clean, current control checkout
        # (`coga/checkouts`). Resolution and the recorded-checkout test below only
        # classify; every authoritative read happens after `enter`.
        self.boundary = _CheckoutBoundary()
        may_normalize = not self.prompt_report and not self.recurring_authorized

        # Chat/orientation must compose from current control too, including its
        # repo-local bootstrap override. Other bootstrap commands may deliberately
        # operate on a PR branch; delegated sessions keep their caller's boundary.
        if may_normalize and not self.require_agent_target and self.task == "bootstrap/orient":
            self.cfg = self.boundary.enter(self.cfg, self.task)

        try:
            self.ref = resolve_target(self.cfg, self.task)
        except TaskNotFoundError as exc:
            # A ticket created on control after this checkout's branch point is
            # absent from a stale tree: normalize once, then resolve again.
            missing: TaskNotFoundError | None = exc
            if (
                may_normalize
                and not direct_recurring_prefix
                and not self.task.startswith("bootstrap/")
            ):
                self.cfg = self.boundary.enter(self.cfg, self.task)
                if self.boundary.armed:
                    try:
                        self.ref = resolve_target(self.cfg, self.task)
                        missing = None
                    except TaskNotFoundError as retry_exc:
                        missing = retry_exc
            if missing is not None:
                # `coga build` rewrites to `launch coga-build`; the ticket is
                # absent when init classified the repo as filled, or when it was
                # removed later, and the bare resolver miss gives no hint why.
                if self.task == ONBOARDING_TASK and not any(
                    t.id_slug.startswith(self.task) for t in list_tasks(self.cfg)
                ):
                    _bail(f"{missing}\n{_onboarding_missing_message()}")
                _bail(str(missing))

        if may_normalize and isinstance(self.ref, TaskRef) and not self.boundary.entered:
            if self.ref.directory == "recurring":
                pass  # its own admission gates below require control
            else:
                exemption = _checkout_exemption(self.cfg, self.ref)
                if exemption is not None:
                    self.kept_checkout_reason = exemption
                    _report(
                        f"Launch: keeping this checkout for {self.ref.id_slug}: {exemption}"
                    )
                else:
                    selected_slug = self.ref.id_slug
                    self.cfg = self.boundary.enter(self.cfg, selected_slug)
                    if self.boundary.armed:
                        try:
                            self.ref = resolve_target(self.cfg, selected_slug)
                        except TaskNotFoundError:
                            _bail(
                                f"Cannot launch {selected_slug}: it no longer "
                                f"exists on {self.cfg.git_remote}/"
                                f"{self.cfg.git_control_branch}. No work was started."
                            )
                        if self.ref.id_slug != selected_slug:
                            _bail(
                                f"Selected task {selected_slug!r} disappeared on "
                                "control; refusing to launch the different prefix "
                                f"match {self.ref.id_slug!r}."
                            )

        if (
            isinstance(self.ref, TaskRef)
            and self.ref.directory == "recurring"
            and not self.prompt_report
            and not self.recurring_authorized
            and not direct_recurring_prefix
        ):
            # A bare/prefix task spelling can resolve into the recurring namespace
            # only after lookup. Preserve that compatibility, then re-resolve its
            # canonical slug from the refreshed checkout exactly as the explicit
            # fast path above does.
            recurring_slug = self.ref.id_slug
            self.cfg = authorize_direct_recurring(self.cfg)
            try:
                self.refreshed_ref = resolve_target(self.cfg, recurring_slug)
            except TaskNotFoundError as exc:
                _bail(str(exc))
            if (
                not isinstance(self.refreshed_ref, TaskRef)
                or self.refreshed_ref.directory != "recurring"
                or self.refreshed_ref.id_slug != recurring_slug
            ):
                _bail(
                    f"Selected recurring task {recurring_slug!r} disappeared "
                    "during control catch-up; refusing to launch a different "
                    f"prefix match {self.refreshed_ref.id_slug!r}."
                )
            self.ref = self.refreshed_ref

        # A materialized recurring delegation is an immutable dispatch snapshot,
        # not prose for an agent wrapper. Route it before ordinary task setup so a
        # direct `coga launch recurring/<name>` and every recurring runner entry
        # point perform the same one-hop bootstrap launch. The local imports avoid
        # a module cycle: recurring_runner itself uses this module's bootstrap
        # launch seam.
        if (
            not self.prompt_report
            and isinstance(self.ref, TaskRef)
            and self.ref.directory == "recurring"
        ):
            self.boundary.admit(self.cfg)

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
                        before_recompose=None,
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
                # The period's own return half (armed by `admit` above): the
                # delegated bootstrap session is exempt from normalization, but
                # the recurring period that dispatched it is not. A refusal sets
                # the withheld flag, which `launch_recurring_period` turns into
                # the retained-state exit.
                self.boundary.settle(self.cfg, subject=f"{self.ref.id_slug}'s delegated run")
                if self.return_timeout:
                    return LaunchResult(delegated.kind, delegated.exit_code)
                if delegated.exit_code:
                    raise LaunchBail(delegated.exit_code)
                return LaunchResult()

        self.resolved_target_slug = self.ref.id_slug
        self.is_bootstrap = isinstance(self.ref, BootstrapRef)
        self.script_steps_run: set[str | None] = set()
        return None

    def _align_and_classify(self) -> LaunchResult | None:
        """Align a recorded assist, then classify its current ticket and script."""

        # A recorded single-checkout assist may be behind its published PR branch.
        # Align before refreshing the agent-skill view or deriving any launch state:
        # the fetched commit can change coga.toml, the ticket, or a composed skill.
        # Reload and repeat after every fast-forward so secrets, expected step,
        # prompt, and command all come from the final tree.
        aligned_assist_branch: str | None = None
        aligned_assist_remote_oid: str | None = None
        self.aligned_assist_pr_url: str | None = None

        if not self.prompt_report and self.agent_override is not None:
            for _ in range(_ASSIST_ALIGNMENT_ATTEMPTS):
                alignment_ticket = read_ticket(self.ref)
                # Same resolution the classification below uses: activation
                # freezes the snapshot, seeds step 1, and selects a main agent,
                # so a draft must be aligned against the routing it will
                # actually launch with, not the routing it is parked with.
                alignment_operator: Operator | None = None
                if not self.is_bootstrap and isinstance(self.ref, TaskRef):
                    alignment_operator, _ = _prospective_activation_identity(
                        self.cfg, self.ref, alignment_ticket
                    )
                alignment_is_human_assist = (
                    alignment_operator is not None
                    and alignment_operator.is_human
                )
                if (
                    alignment_is_human_assist
                    and alignment_ticket.status
                    in {"draft", "active", "in_progress", "paused", "blocked"}
                    and not _interactive_stdio_has_tty()
                ):
                    _refuse_tty_launch(self.ref)
                candidate_assist_branch = (
                    None
                    if not alignment_is_human_assist
                    else _recorded_single_checkout_assist_branch(
                        self.cfg, alignment_ticket
                    )
                )
                if (
                    self.is_bootstrap
                    or alignment_ticket.status
                    not in {"draft", "active", "in_progress", "paused", "blocked"}
                    or candidate_assist_branch is None
                ):
                    break
                try:
                    if candidate_assist_branch == self.cfg.git_control_branch:
                        raise git.GitError(
                            f"recorded assist branch {candidate_assist_branch!r} "
                            "has the same name as the configured control branch"
                        )
                    pr_head_oid = _verify_recorded_assist_pr_head(
                        self.cfg, alignment_ticket, candidate_assist_branch
                    )
                    moved, remote_oid = _align_recorded_assist_checkout(
                        self.cfg, alignment_ticket
                    )
                    if remote_oid != pr_head_oid:
                        raise git.GitError(
                            f"configured remote {self.cfg.git_remote!r} branch "
                            f"{candidate_assist_branch!r} is at {remote_oid}, but "
                            f"the recorded PR head is {pr_head_oid}"
                        )
                except git.GitError as exc:
                    _bail(
                        f"Cannot launch {self.ref.id_slug}: could not verify and align "
                        f"the recorded assist checkout before composing the "
                        f"prompt: {exc}"
                    )
                if not moved:
                    _, alignment_blackboard = split_body(alignment_ticket.body)
                    aligned_assist_branch = candidate_assist_branch
                    aligned_assist_remote_oid = remote_oid
                    self.aligned_assist_pr_url = parse_pr_url(
                        alignment_blackboard or ""
                    )
                    break
                try:
                    self.cfg = load_config(self.cfg.repo_root)
                    self.ref = resolve_target(self.cfg, self.resolved_target_slug)
                    if self.ref.id_slug != self.resolved_target_slug:
                        raise TaskNotFoundError(
                            f"Selected task {self.resolved_target_slug!r} disappeared "
                            "during assist alignment; refusing to launch the "
                            f"different prefix match {self.ref.id_slug!r}."
                        )
                except (ConfigError, TaskNotFoundError) as exc:
                    _bail(str(exc))
                self.is_bootstrap = isinstance(self.ref, BootstrapRef)
            else:
                _bail(
                    f"Cannot launch {self.ref.id_slug}: the recorded assist branch "
                    f"moved during {_ASSIST_ALIGNMENT_ATTEMPTS} consecutive "
                    "alignment attempts; retry once the PR branch is stable."
                )


        # Classify only after recorded-assist alignment. Prompt reporting remains
        # non-executing; for an agent-only report, refresh the agent skill view here
        # and keep every deterministic launch free of that agent-only preflight.
        self.entry = script_entry_point(self.ref)
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

        self.ticket = self._read(self.ref)

        if (
            isinstance(self.ref, TaskRef)
            and released_launch_generation(self.ticket.launch_generation)
        ):
            try:
                released_bytes = self.ref.ticket_path.read_bytes()
                admitted_bytes = _reconcile_released_launch_admission(
                    self.cfg,
                    self.ref.ticket_path,
                    expected_ticket_bytes=released_bytes,
                )
                self.ticket = Ticket.parse(admitted_bytes.decode("utf-8"))
            except (OSError, UnicodeError, TicketError, git.GitError) as exc:
                _bail(
                    f"Cannot launch {self.ref.id_slug}: its released megalaunch "
                    "admission could not be reconciled with control. The "
                    f"recoverable local witness was retained; fix Git and retry: "
                    f"{exc}",
                    exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
                )
            _report(
                f"Reconciled released megalaunch admission for {self.ref.id_slug}."
            )

        if (
            isinstance(self.ref, TaskRef)
            and pending_launch_generation(self.ticket.launch_generation)
        ):
            _bail(
                f"Cannot launch {self.ref.id_slug}: megalaunch admission "
                f"{self.ticket.launch_generation!r} is still pending. Its held child "
                "must be released or the pending claim reconciled before another "
                "session can start."
            )

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
        self.blocked_resume_step: str | None = None
        self.blocked_resume_ticket_bytes: bytes | None = None

        # A blocked ticket may be launched only by an explicit interactive human
        # act: the session's first job becomes resolving the open asks with the
        # human (the composed prompt gains a resolve-or-re-block preamble keyed
        # off the blackboard's open blockers), and the ticket reactivates inline
        # after preflights pass. Batch surfaces are unchanged — a TTY-less run has
        # no human to discuss with, so it keeps the hard refusal (checked here,
        # before any status mutation). `coga
        # megalaunch` never gets this far: its sweep classifies blocked tickets as
        # skipped-unresolved-blocker, and an explicit pick runs the same
        # activate-and-resume through the engine's own launch loop.
        if not self.is_bootstrap and isinstance(self.ref, TaskRef) and self.ticket.status == "blocked":
            if _interactive_stdio_has_tty():
                if not open_blockers(self.ref.ticket_path):
                    _bail(
                        f"Cannot launch {self.ref.id_slug}: it is blocked but has no "
                        "open blocker asks to resolve. Record a blocker with "
                        f"`coga block --task {self.ref.id_slug} --reason \"...\"` or "
                        "repair the task state before launching."
                    )
                self.blocked_resume = True
                self.blocked_resume_step = self.ticket.step
                self.blocked_resume_ticket_bytes = self.ref.ticket_path.read_bytes()
                _report(
                    f"Launch: {self.ref.id_slug} is blocked — resuming "
                    "interactively; the session's first job is to resolve or "
                    "re-block the open asks."
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
        self.single_checkout_assist_branch = (
            _recorded_single_checkout_assist_branch(self.cfg, self.ticket)
            if self.human_assist and isinstance(self.ref, TaskRef)
            else None
        )
        if aligned_assist_branch is not None and (
            self.single_checkout_assist_branch != aligned_assist_branch
            or aligned_assist_remote_oid is None
            or self.aligned_assist_pr_url is None
        ):
            _bail(
                f"Cannot launch {self.ref.id_slug}: the recorded assist checkout, "
                "branch, or PR changed after alignment; retry from the recorded "
                "checkout once the PR is stable."
            )
        if self.single_checkout_assist_branch is not None:
            try:
                current_pr_head_oid = _verify_recorded_assist_pr_head(
                    self.cfg,
                    self.ticket,
                    self.single_checkout_assist_branch,
                    expected_pr_url=self.aligned_assist_pr_url,
                )
            except git.GitError as exc:
                _bail(f"Cannot launch {self.ref.id_slug}: {exc}")
            if current_pr_head_oid != aligned_assist_remote_oid:
                _bail(
                    f"Cannot launch {self.ref.id_slug}: recorded PR head moved from "
                    f"{aligned_assist_remote_oid} to {current_pr_head_oid} after "
                    "checkout alignment; retry once the PR branch is stable."
                )
        return None

    def _run_initial_script(self) -> LaunchResult | None:
        """Run deterministic work before any agent-only preparation."""

        # Run the deterministic half before every agent-only preflight. Blocked
        # tickets pay only their attended/open-ask gate first. A recorded human
        # assist is additionally wrapped in the same strict lifecycle, PR, audit,
        # and child-capability transaction as its agent process.
        if self.entry is not None:
            self.script_outcome = None
            try:
                if self.single_checkout_assist_branch is not None:
                    if (
                        not isinstance(self.ref, TaskRef)
                        or self.agent_override is None
                        or self.aligned_assist_pr_url is None
                    ):
                        _bail(
                            f"Cannot launch {self.ref.id_slug}: recorded script assist "
                            "is missing its task, agent, or PR."
                        )
                    # The selected assist agent is part of the child identity, so
                    # validate the name here. CLI lookup, skill refresh, prompt
                    # composition, and the remaining agent preflights stay deferred
                    # until ticket.py actually leaves agent work open.
                    try:
                        self.cfg.agent_type(self.agent_override)
                    except ConfigError as exc:
                        _bail(str(exc))
                    build_launch_env(self.cfg, self.ticket.secrets)
                    try:
                        preflight_post(self.cfg)
                    except NotificationExit:
                        _bail(
                            f"Cannot launch {self.ref.id_slug}: notification "
                            "configuration must be valid before assist "
                            "lifecycle state or script audit is published."
                        )
                    _preflight_push_auth(self.cfg, self.ref, is_bootstrap=False)
                    if self.ticket.status in {"draft", "paused", "blocked"}:
                        _auto_activate(self.cfg, self.ref, self.ticket)
                    if self.ticket.status == "active":
                        _start_session(self.cfg, self.ref, self.ticket, launch_agent=self.agent_override)
                    self.ticket = self._read(self.ref)
                elif (
                    not self.is_bootstrap
                    and isinstance(self.ref, TaskRef)
                    and self.ticket.status in {"draft", "paused", "blocked"}
                ):
                    # Secret resolution belongs before the activation write. The
                    # script helper repeats it after any moving sync so the child
                    # receives the final ticket's declarations.
                    build_launch_env(self.cfg, self.ticket.secrets)
                    _auto_activate(self.cfg, self.ref, self.ticket)

                self.script_outcome = run_script_chain(
                    self.cfg,
                    self.ref,
                    self.ticket,
                    self.script_steps_run,
                    assist_branch=self.single_checkout_assist_branch,
                    assist_agent=(
                        self.agent_override
                        if self.single_checkout_assist_branch is not None
                        else None
                    ),
                    assist_pr_url=self.aligned_assist_pr_url,
                    failure_important=self.script_failure_important,
                    between_phases=(
                        self.settle_between_phases if self.boundary.armed else None
                    ),
                    args=self.launch_args if self.is_bootstrap else (),
                )
                self.cfg = self.script_outcome.cfg or self.cfg
                self.ref = self.script_outcome.ref or self.ref
                self.is_bootstrap = isinstance(self.ref, BootstrapRef)
                if self.script_outcome.ticket is not None:
                    self.ticket = self.script_outcome.ticket
                self.entry = script_entry_point(self.ref)

                # An unresolved blocked resume may continue to an agent only while
                # ticket.py left the original step open. Failure, pause, closure,
                # deletion, or advancement ends the deterministic path and must put
                # the original ask back in the blocked queue first.
                should_reblock_after_script = bool(
                    self.blocked_resume
                    and (
                        self.script_outcome.exit_code != 0
                        or not self.script_outcome.needs_agent
                        or self.script_outcome.ticket is None
                        or self.script_outcome.ticket.step != self.blocked_resume_step
                    )
                )
                stop_blocked_resume = (
                    self.reblock_after_script()
                    if should_reblock_after_script
                    else False
                )

                if self.script_outcome.exit_code != 0:
                    if (
                        self.is_bootstrap
                        and self.script_outcome.exit_code
                        == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
                    ):
                        # The command script deliberately retained local state
                        # (for example a nested launch whose checkout return
                        # refused). Leave it untouched: no teardown refresh,
                        # no end-of-command sweep, and the same exit.
                        self.script_retained_state = True
                        git.state_sweep_withheld.set(True)
                    _exit_failed_script(self.script_outcome.exit_code)

                if not self.script_outcome.needs_agent or stop_blocked_resume:
                    if self.script_outcome.stop_reason:
                        _report(self.script_outcome.stop_reason, err=self.is_bootstrap)
                    elif stop_blocked_resume:
                        _report(
                            f"{self.ref.id_slug}: unresolved blocker restored; "
                            "returning to caller"
                        )
                    self.refresh_after_script()
                    return LaunchResult('script' if self.return_timeout else None)

                if self.script_outcome.ticket is None:
                    _bail(
                        f"Cannot continue {self.ref.id_slug}: ticket.py left no "
                        "ticket state for an agent handoff."
                    )
                if self.agent_spawn_refusal is not None:
                    if self.blocked_resume:
                        self.reblock_after_script()
                    _report(
                        f"Cannot continue {self.ref.id_slug}: ticket.py left "
                        f"{_script_step_label(self.ticket)} open, but "
                        f"{self.agent_spawn_refusal} The deterministic work was kept; "
                        "no agent was started.",
                        fg='yellow',
                        err=True,
                    )
                    self.refresh_after_script()
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
                if self.blocked_resume:
                    self.reblock_after_script()
                self.refresh_after_script()
                _bail(str(exc))
            except BaseException:
                if self.blocked_resume:
                    self.reblock_after_script()
                self.refresh_after_script()
                raise

        # Everything below is agent-only. A headless or temporary-worktree runner
        # supplies a hard refusal even for a period whose frozen ticket.py vanished
        # after scan admission; no reconciliation race may turn that period into an
        # agent launch in the disposable checkout.
        if self.agent_spawn_refusal is not None:
            if self.blocked_resume:
                self.reblock_after_script()
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

        if not self.prompt_report:
            require_agent_sessions()

        # Deterministic completion, failure, and handoff paths have already
        # returned without consulting agent config, materializing skills,
        # composing a prompt, or probing the CLI binary.
        def agent_only_setup_call(action: Callable[[], _T]) -> _T:
            """Keep a resumed blocker owned through every agent-only preflight."""
            try:
                return action()
            except BaseException:
                if self.blocked_resume:
                    self.reblock_after_script()
                raise

        if self.agent_override is not None:
            try:
                agent_only_setup_call(
                    lambda: self.cfg.agent_type(self.agent_override)
                )
            except ConfigError as exc:
                _bail(str(exc))
        agent_only_setup_call(
            lambda: _refresh_agent_skills_for_launch(self.cfg.repo_root)
        )

        try:
            self.operator = _target_operator(self.cfg, self.ref, self.ticket)
        except OperatorResolutionError as exc:
            if self.blocked_resume:
                self.reblock_after_script()
            _bail(f"Cannot launch {self.ref.id_slug}: {exc}")
            return LaunchResult()
        if self.operator is None:
            if self.blocked_resume:
                self.reblock_after_script()
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

        try:
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

            if not _interactive_stdio_has_tty():
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

            # Verify CLI binary exists. `coga build` is a new user's first launch,
            # so it offers the install and login (the TTY is proven above) rather
            # than failing on a missing agent CLI.
            agent_path = shutil.which(self.agent.cli)
            if (
                agent_path is None
                and self.ref.id_slug == ONBOARDING_TASK
                and offer_agent_cli(self.agent.cli)
            ):
                agent_path = shutil.which(self.agent.cli)
            if agent_path is None:
                _bail(agent_cli_missing_message(self.agent.cli))
            _report(f"Launch: found agent CLI at {agent_path}")

            # Fail loud BEFORE any status is written: if a referenced context or
            # skill is missing, the composed prompt would drop a layer the human
            # expected the agent to have. Refuse to start — and don't write the
            # activation, flip the ticket to in_progress, or post a "started"
            # broadcast for a task that never runs.
            # The per-step loop below re-composes; this is a cheap pre-flight (file
            # reads only) so the flip and notification post are never reached on a bad ref.
            try:
                compose_prompt(self.cfg, self.ref, self.ticket, launch_context=self.launch_context)
            except ComposeError as exc:
                _bail(str(exc))
            except FileNotFoundError as exc:
                # A layer file that exists at resolve time but not at read time
                # (a concurrent checkout, a mid-sync working tree). Loud either
                # way, but name the path instead of dumping a traceback.
                _bail(missing_launch_file_message(exc))

            # Preflight and build the child env before mutating ticket state. A missing
            # declared secret is a launch refusal, not a started task.
            try:
                self.env = build_launch_env(self.cfg, self.ticket.secrets)
            except SecretError as exc:
                _bail(str(exc))

            # Refuse to start an agent session when git push access is broken. Coga
            # drives the whole session through git/gh (branch push, `gh pr create`,
            # every `coga bump` syncs ticket state), so a dead remote means an
            # often-long run guaranteed to fail at ship time. Fail loud at the door
            # rather than discover it at PR time — same as the other pre-flip
            # preflights above. Pre-flip, so a refused launch never posts a "started"
            # broadcast or flips status.
            _preflight_push_auth(self.cfg, self.ref, is_bootstrap=self.is_bootstrap)

            # Every refusing preflight has passed, so the activation staged in
            # memory above is now safe to write. Nothing between the prepare guard
            # and here re-reads the ticket from disk, so `ticket` is still the
            # object that was prepared — keep it that way, or the deferred write
            # will publish a ticket the preflights never saw.
            if auto_activate_prior is not None and isinstance(self.ref, TaskRef):
                _commit_auto_activate(
                    self.cfg, self.ref, self.ticket, prior=auto_activate_prior
                )

            if self.blocked_resume and isinstance(self.ref, TaskRef) and self.ticket.status == "blocked":
                _auto_activate(self.cfg, self.ref, self.ticket)

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
        except BaseException:
            if self.blocked_resume:
                self.reblock_after_script()
            self.return_checkout()
            raise
        return None

    def _supervise_steps(self) -> LaunchResult:
        """Supervise successive steps and always reconcile the checkout on exit."""

        ended_by_script = False
        try:
            first_step = True
            consecutive_agent_override = False
            while True:
                self.ticket = self._read(self.ref)
                is_first_step = first_step

                if self.entry is not None and self.ticket.step not in self.script_steps_run:
                    try:
                        self.script_outcome = run_script_chain(
                            self.cfg,
                            self.ref,
                            self.ticket,
                            self.script_steps_run,
                            assist_branch=self.single_checkout_assist_branch,
                            assist_agent=(
                                self.launch_agent
                                if self.single_checkout_assist_branch is not None
                                else None
                            ),
                            assist_pr_url=self.aligned_assist_pr_url,
                            failure_important=self.script_failure_important,
                            between_phases=(
                                self.settle_between_phases if self.boundary.armed else None
                            ),
                        )
                    except (SecretError, TaskValidationError, FileNotFoundError) as exc:
                        _bail(str(exc))
                    self.cfg = self.script_outcome.cfg or self.cfg
                    self.ref = self.script_outcome.ref or self.ref
                    self.is_bootstrap = isinstance(self.ref, BootstrapRef)
                    self.entry = script_entry_point(self.ref)
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
                # The explicit override expires for routing as soon as ticket.py
                # hands control to a configured agent, but the launch still runs
                # in the one aligned recorded-PR checkout, so every step of an
                # assist keeps naming the assisting agent in its audit lines.
                assist_branch = self.single_checkout_assist_branch
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
                # rotates to an agent (e.g. codex) whose CLI isn't on PATH. Stop
                # cleanly and hand back to the human rather than blocking.
                if shutil.which(self.agent.cli) is None:
                    message = (
                        f"{self.ref.id_slug}: next step needs agent {step_agent!r} "
                        f"but {agent_cli_missing_message(self.agent.cli)}"
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
                session_before_recompose = (
                    self.before_recompose if is_first_step else None
                )
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
                checkout_notice: CheckoutNotice | None = None
                composed_prompt: str | None = None
                record_launch = self.record_launch
                if self._manages_branch_checkout():
                    spawn_ticket, composed_prompt = self._prepare_step_checkout(
                        spawn_ticket, actor=actor, log_message=log_message
                    )
                    self.ticket = spawn_ticket
                    record_launch = False
                else:
                    checkout_notice = self._unmanaged_checkout_notice()

                step_env = build_supervised_step_env(
                    self.env,
                    task_path=self.ref.path,
                    step=spawn_ticket.step,
                    agent=step_agent or self.launch_agent,
                )
                if self.boundary.armed:
                    step_env[CHECKOUT_RETURN_ENV] = "1"

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
                        # Publish the launch line before the agent starts: a
                        # bootstrap target has no later task-state sync to carry
                        # it. A managed branch checkout already published it on
                        # control, before preparation switched.
                        commit_log=True,
                        assist_branch=assist_branch,
                        assist_agent=(
                            (step_agent or self.launch_agent)
                            if assist_branch is not None
                            else None
                        ),
                        before_recompose=session_before_recompose,
                        before_spawn=freeze_state_before_session,
                        record_launch=record_launch,
                        composed_prompt=composed_prompt,
                        checkout_notice=checkout_notice,
                    )
                except ComposeError as exc:
                    _bail(str(exc))
                except AgentCliNotFound:
                    _bail(f"Failed to spawn agent: {self.agent.cli!r} not found.")
                except FileNotFoundError as exc:
                    _bail(missing_launch_file_message(exc))

                _report(f"Launch: agent exited with code {session.exit_code}")
                supervisor_reblocked = False
                if self.blocked_resume:
                    self.blocked_resume = False
                    bytes_before_reblock = _diagnostic_ticket_bytes(self.ref)
                    _reblock_unresolved_resume(self.cfg, self.ref, step_agent or self.launch_agent)
                    # A supervisor-owned reblock is not an agent's change; give up
                    # the diagnostic for this session rather than misattribute it.
                    supervisor_reblocked = (
                        _diagnostic_ticket_bytes(self.ref) != bytes_before_reblock
                    )
                # Return the checkout after every started session (usage already
                # published by the spawn), before deciding whether to chain. A
                # refusal keeps this session's own result below and stops chaining.
                checkout_returned = self.boundary.settle(
                    self.cfg, subject=f"{self.ref.id_slug}'s session"
                )
                target_removed = False
                if checkout_returned and self.boundary.armed:
                    self.cfg, returned_ref = self.boundary.reload(self.cfg, self.ref)
                    checkout_returned = not self.boundary.stopped
                    if returned_ref is None:
                        target_removed = True
                    else:
                        self.ref = returned_ref
                # Advisory only: observe refreshed state before the result
                # branches below, and skip when that state is unavailable.
                if (
                    checkout_returned
                    and not target_removed
                    and not supervisor_reblocked
                    and isinstance(self.ref, TaskRef)
                ):
                    _warn_unsignalled_advance(
                        self.ref,
                        state_before_session,
                        done_signalled=session.done_signalled,
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

                if not checkout_returned:
                    break
                if target_removed:
                    _report(
                        f"Launch: {self.ref.id_slug} no longer exists on control — "
                        "nothing to chain"
                    )
                    break

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
        finally:
            # A blocked resume stays responsible for its original unanswered ask
            # until an agent session records a resolution.  ticket.py can end the
            # deterministic path before the ordinary post-session cleanup (failure,
            # pause, close, or a step handoff), so cover every remaining
            # exit here.  The helper is a no-op once the ask was resolved.
            if self.blocked_resume:
                self.blocked_resume = False
                _reblock_unresolved_resume(
                    self.cfg,
                    self.ref,
                    self.agent_override or self.launch_agent,
                    resume_step=self.blocked_resume_step,
                )

            # On every exit path — clean chain completion, `LaunchBail` on a
            # non-zero/timeout agent, or an exception — pull the run's published
            # state back into the checkout the operator launched from, so the
            # `coga status` they run next in this terminal shows the world the
            # run just created. A normalized launch returns the checkout to a
            # clean control branch instead (a no-op after a settled session).
            self.return_checkout()

        return LaunchResult('script' if self.return_timeout and ended_by_script else None)

    def _manages_branch_checkout(self) -> bool:
        """Whether this step's checkout is prepared here (`coga/checkouts`).

        Only an ordinary task launch whose boundary entered and armed on
        control. Recurring, delegated and caller-guarded launches keep their
        own admission and spawn transactions; a recorded checkout, bootstrap
        command and prompt report are exempt; megalaunch never comes here.
        """
        return (
            isinstance(self.ref, TaskRef)
            and not self.is_bootstrap
            and not self.prompt_report
            and self.ref.directory != "recurring"
            and self.boundary.entered
            and self.boundary.armed
            and not self.boundary.stopped
            and not self.recurring_authorized
            and not self.require_agent_target
            and self.before_recompose is None
            and self.before_final_spawn is None
            and self.single_checkout_assist_branch is None
            and self.launch_context == "attended"
        )

    def _prepare_step_checkout(
        self, ticket: Ticket, *, actor: str, log_message: str
    ) -> tuple[Ticket, str]:
        """Plan and link on control, compose, audit, then switch and project.

        The `launched` audit line is appended and published only after
        planning and composition on control succeeded, so a refused
        preparation leaves no launch record; the switch-time checks were
        already run once while planning. Returns the authoritative ticket and
        the prompt composed from control state; the spawn must use both
        unchanged. A refusal reports where the checkout stands and stops the
        launch without a sweep or a return over state it did not start.
        """
        assert isinstance(self.ref, TaskRef)
        policy = select_checkout_policy(self.cfg, ticket)
        _report(f"Launch: checkout policy {policy.kind} — {policy.reason}")

        def compose(
            plan: checkouts.TicketCheckoutPlan,
        ) -> tuple[Ticket, CheckoutNotice, str]:
            assert isinstance(self.ref, TaskRef)
            current = self._read(self.ref)
            notice = checkouts.ticket_notice(self.cfg, plan)
            try:
                prompt = compose_prompt(
                    self.cfg, self.ref, current,
                    launch_context=self.launch_context, checkout=notice,
                )
            except ComposeError as exc:
                _bail(str(exc))
            return current, notice, prompt

        try:
            plan = checkouts.plan_ticket_checkout(self.cfg, self.ref, ticket, policy)
            current, notice, prompt = compose(plan)
            if self.record_launch:
                append_log(self.cfg, self.ref.id_slug, actor, log_message)
                git.sync_log(self.cfg, message=f"Log: {self.ref.id_slug}")
                confirmed = checkouts.confirm_ticket_checkout(
                    self.cfg, self.ref, ticket, plan
                )
                if confirmed.ticket_bytes != plan.ticket_bytes:
                    # Control's ticket gained notes meanwhile: compose from it.
                    current, notice, prompt = compose(confirmed)
                plan = confirmed
            checkouts.enter_ticket_checkout(self.cfg, self.ref, plan)
        except (checkouts.CheckoutPreparationError, git.GitError, OSError) as exc:
            switched = getattr(exc, "switched", False)
            self.boundary.stopped = True
            git.state_sweep_withheld.set(True)
            where = (
                "This checkout was left where preparation stopped, with every "
                "change preserved; launch did not return or sweep it."
                if switched
                else "No agent was started; nothing was swept or discarded."
            )
            _bail(
                f"Cannot launch {self.ref.id_slug}: {exc}\n{where} See "
                "coga/checkouts/launch-boundary for recovery.",
                exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
            )
        _report(f"Launch: checkout {plan.action} — {notice.summary}")
        return current, prompt

    def _unmanaged_checkout_notice(self) -> CheckoutNotice | None:
        """A truthful notice for a launch that prepared no branch, or None."""
        if self.prompt_report:
            return None
        if self.is_bootstrap:
            if self.ref.id_slug != "bootstrap/orient" or not self.boundary.entered:
                return None
            return checkouts.chat_notice(
                self.cfg, _CHAT_SESSION.get(), armed=self.boundary.armed,
                reason=self.boundary.exempt_reason or "",
            )
        if self.kept_checkout_reason is not None:
            return CheckoutNotice(
                summary=(
                    "Launch kept this checkout and did not prepare or switch it: "
                    f"{self.kept_checkout_reason}."
                ),
                return_owner=(
                    "Launch does not return this checkout; follow coga/checkouts "
                    "for the end of the step."
                ),
            )
        if self.boundary.entered and not self.boundary.armed:
            return CheckoutNotice(
                summary=(
                    "Launch did not prepare a branch or claim freshness against "
                    f"control: {self.boundary.exempt_reason or 'Git is unavailable'}."
                ),
                return_owner="Nothing returns this checkout automatically.",
            )
        return None

    def _read(self, target: TaskRef | BootstrapRef) -> Ticket:
        """Read the ticket from disk.

        Deliberately unmodified: an `--agent` override is ephemeral and is
        applied where the worker is chosen, never by editing a ticket — not even
        the in-memory copy, which composition and the routing derivation both
        read.
        """
        return read_ticket(target)


    def return_checkout(self) -> None:
        """Teardown: return a normalized checkout, else today's refresh."""
        if self.boundary.armed:
            self.boundary.settle(self.cfg, subject=f"{self.ref.id_slug}'s launch")
        else:
            _refresh_launch_checkout(self.cfg)


    def refresh_after_script(self) -> None:
        if self.script_retained_state:
            return
        self.return_checkout()


    def settle_between_phases(
        self,
        phase_cfg: Config, phase_ref: TargetRef
    ) -> tuple[Config, TargetRef | None] | None:
        """Return the checkout after one ticket.py phase, then re-read."""
        if not self.boundary.settle(phase_cfg, subject=f"{phase_ref.id_slug}'s script"):
            return None
        refreshed_cfg, refreshed_ref = self.boundary.reload(phase_cfg, phase_ref)
        if self.boundary.stopped:
            return None
        return refreshed_cfg, refreshed_ref


    def reblock_after_script(self) -> bool:
        """Return a still-unanswered resumed blocker to its durable queue."""
        if not self.blocked_resume:
            return False
        self.blocked_resume = False
        return _reblock_unresolved_resume(
            self.cfg,
            self.ref,
            self.agent_override or _operator_display(self.cfg, self.ref, self.ticket),
            resume_step=self.blocked_resume_step,
            fallback_ticket_bytes=self.blocked_resume_ticket_bytes,
        )




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
    if not agent_sessions_supported():
        _bail(
            f"Cannot continue {ref.id_slug}: ticket.py left {step_label} open; "
            f"{WINDOWS_AGENT_SESSION_MESSAGE} The deterministic work was kept."
        )
    if not _interactive_stdio_has_tty():
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
            f"for agent {worker!r}, but {agent_cli_missing_message(agent.cli)} "
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


def _prospective_assist_ticket(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
) -> Ticket:
    """Return the lifecycle view composed for a child that has not started yet."""
    prospective = Ticket(
        frontmatter=dict(ticket.frontmatter),
        body=ticket.body,
    )
    if prospective.status in {"draft", "paused", "blocked"}:
        try:
            prepare_active(cfg, ref, prospective)
        except WorkflowMissing as exc:
            raise ComposeError(
                f"Cannot launch {ref.id_slug}: it is {ticket.status!r} and has "
                "no workflow, so there is nothing to activate or advance."
            ) from exc
        except WorkflowError as exc:
            raise ComposeError(
                f"Cannot launch {ref.id_slug}: its `workflow:` ref could not "
                f"be frozen — {exc}"
            ) from exc
        except RequiredExtensionMissing as exc:
            names = ", ".join(repr(field) for field in exc.fields)
            raise ComposeError(
                f"Cannot launch {ref.id_slug}: required extension field(s) "
                f"empty: {names}."
            ) from exc
        except BlackboardNeedsSynthesis as exc:
            raise ComposeError(
                format_blackboard_synthesis_refusal(
                    ref.id_slug,
                    action="launch",
                    reason=exc.reason,
                )
            ) from exc
        except RepoResourceUnreadable as exc:
            raise ComposeError(f"Cannot launch {ref.id_slug}: {exc}") from exc
        except MainAgentUnavailable as exc:
            raise ComposeError(
                f"Cannot launch {ref.id_slug}: {exc}"
            ) from exc
    if prospective.status == "active":
        prospective.frontmatter["status"] = "in_progress"
    if prospective.status != "in_progress":
        raise ComposeError(
            f"Cannot launch {ref.id_slug}: assist lifecycle changed to "
            f"{prospective.status!r} before spawn."
        )
    return prospective


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

    This assumes nothing rewrote `ref.ticket_path` while the preflights ran:
    the in-memory ticket is written over whatever is on disk, unguarded. Coga
    is a single-writer, locally operated tool and tickets are not edited
    concurrently with a launch of the same ticket; the blocked-resume gate in
    `_launch` makes the same assumption across the same preflights. The strict
    assist path is the exception and guards its publication explicitly — see
    `coga-dev/internals`.
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


def _diagnostic_ticket_bytes(ref: TargetRef) -> bytes | None:
    try:
        return ref.ticket_path.read_bytes()
    except OSError:
        return None


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


def _reblock_unresolved_resume(
    cfg: Config,
    ref: TaskRef | BootstrapRef,
    blocker: str | None,
    *,
    resume_step: str | None = None,
    fallback_ticket_bytes: bytes | None = None,
) -> bool:
    """Return an unresolved blocked-ticket resume to the blocked queue.

    A resumed blocked launch is allowed to become `in_progress` so the same
    session can discuss, run `coga unblock`, and continue to `coga bump`. If
    that session exits before recording the answer, keep the unresolved ask
    visible to `status --blocked`, `unblock --all`, and blocker reminders.

    ``resume_step`` is supplied by the deterministic path.  A ticket script
    can pause or close the ticket before launch regains control; an unanswered
    ask still wins, so restore the original live step when the transition
    cleared it and put the ticket back in the blocked queue.  Agent-session
    callers omit it and retain the established in-progress-only cleanup.
    Restoring a position restores the routing *inputs*; the operator is derived
    from them, never copied from the session that ran.

    Returns whether an open ask remains durably parked as ``blocked``.
    """
    if not isinstance(ref, TaskRef):
        return False
    current_bytes = ref.ticket_path.read_bytes() if ref.ticket_path.is_file() else None
    restored_fallback = False
    try:
        if current_bytes is None:
            raise TicketError("ticket.py removed ticket.md")
        ticket = Ticket.parse(current_bytes.decode("utf-8"))
        _, blackboard = split_body(ticket.body)
        blockers = [
            item
            for item in parse_blockers_text(blackboard or "")
            if not item.resolved
        ]
    except (OSError, UnicodeError, TaskFileError, TicketError):
        if fallback_ticket_bytes is None:
            return False
        ticket = Ticket.parse(fallback_ticket_bytes.decode("utf-8"))
        _, blackboard = split_body(ticket.body)
        blockers = [
            item
            for item in parse_blockers_text(blackboard or "")
            if not item.resolved
        ]
        # A failed deterministic child owns its invalid or missing ticket
        # result. Fall back to the exact pre-resume ticket so the original ask
        # stays queue-visible, then preserve the child's exit code upstream.
        ref.ticket_path.parent.mkdir(parents=True, exist_ok=True)
        git.write_ticket(cfg, ticket, ref.ticket_path)
        restored_fallback = True
    if not blockers:
        return False
    if ticket.status == "blocked" and not restored_fallback:
        return True
    if ticket.status != "in_progress" and resume_step is None:
        return False
    if resume_step is not None and ticket.step is None:
        # A terminal deterministic transition can clear ``step``. Restore the
        # original position and let routing be derived from it again: there is no
        # copied assignment to restore, so an unresolved ask can no longer be
        # attributed to whichever agent a later step would have used.
        ticket.frontmatter["step"] = resume_step

    owner = ticket.owner or cfg.current_user
    detail = "; ".join(b.reason for b in blockers)
    try:
        mark_blocked(
            cfg,
            ref,
            ticket,
            actor="system",
            log_message=(
                "blocked: unresolved blocker still open after resumed launch exited"
            ),
            slack_text=(
                f"🛑 {blocker or cfg.current_user} still blocked "
                f"*{ref.id_slug}* \"{ticket.title}\": {detail}"
            ),
            echo=(
                f"{ref.id_slug}: blocked (unresolved blocker still open; "
                f"owner {owner} needs to answer)"
            ),
        )
    except TaskValidationError as exc:
        _bail(str(exc))
    return True


def _preflight_push_auth(
    cfg: Config, ref: TaskRef | BootstrapRef, *, is_bootstrap: bool
) -> bool:
    """Refuse to launch when git push access to the configured remote is broken.

    Coga runs the whole session through git/gh, so a dead remote means a run
    guaranteed to fail at ship time; catch it at the door. The probe is the
    same non-interactive `git push --dry-run` `coga validate --check-github`
    uses (so a logged-out HTTPS remote fails fast, not on a prompt).

    Self-skips when there is nothing to push to or no sync configured:
    bootstrap tickets (stateless, no PR), `[git].enabled = false`, and any
    checkout where the configured remote does not resolve (not a git repo / no
    remote) — which is also why the non-git launch test fixtures are
    unaffected. Only a *configured, reachable-but-unauthenticated* remote bails.
    Returns whether the period has a configured remote whose later lifecycle
    publications must therefore keep failing closed if transport disappears.
    """
    if is_bootstrap or not cfg.git_enabled:
        return False
    if not check_git_remote(cfg.git_remote).ok:
        # No git repo / remote unconfigured → the sync layer soft-no-ops, so
        # there is no push to gate.
        return False
    auth = check_git_auth(cfg.git_remote)
    if not auth.ok:
        _bail(
            f"Cannot launch {ref.id_slug}: git push access to "
            f"{cfg.git_remote!r} is unavailable, and coga drives the session "
            "through git/gh (branch push, `gh pr create`, `coga bump` ticket "
            f"sync) — it would fail at ship time. {auth.detail} "
            "Fix auth and retry, or set `[git].enabled = false` to run without "
            "git sync."
        )
    return True


def _refresh_launch_checkout(cfg: Config) -> bool:
    """Bring the launch checkout level with control after a session.

    Runs once on every exit path the supervisor sees, so a control checkout
    never stays stale until a manual pull; a feature-branch checkout is left
    as it is (stale-by-design for other checkouts' tickets). The git layer
    reports failures on stderr + the log and returns the result.
    """
    return git.refresh(cfg)


def settle_delegated_period(cfg: Config, ref: TaskRef) -> bool:
    """Return the checkout after a recurring runner's direct delegated run.

    The sweep and the named recurring path call `_run_delegated_task`
    themselves rather than through `_launch`, so they arm and settle the
    period's return half here. False means the return refused: the sweep is
    withheld and the caller must stop with the retained-state exit.
    """
    boundary = _CheckoutBoundary()
    boundary.admit(cfg)
    return boundary.settle(cfg, subject=f"{ref.id_slug}'s delegated run")


class _CheckoutBoundary:
    """One ordinary launch's checkout normalization (`coga/checkouts`).

    `enter` publishes routine pending Coga state, then brings the invoking
    checkout to a clean, fetched control branch before any authoritative
    ticket read. `admit` arms only the return half for a recurring period,
    whose own gates already required control. `settle` repeats the same
    publish-then-prepare after every started agent session or deterministic
    phase and at teardown. Only state whose publication failed, or that is
    not Coga state, blocks. The first refusal or failure stops every later
    mutation for this launch, withholds the end-of-command sweep, and ends
    chaining; it never rewrites the session's own result.
    """

    def __init__(self) -> None:
        self.entered = False
        self.armed = False
        self.stopped = False
        self._remote_expected = False
        self._destination: tuple[object, ...] | None = None
        self._contexts_root: Path | None = None
        self.exempt_reason: str | None = None

    def enter(self, cfg: Config, target: str) -> Config:
        self.entered = True
        git.sync_coga_state(cfg, message="Sync coga state before launch")
        outcome = git.prepare_control_checkout(cfg)
        if outcome.kind == "exempt":
            self.exempt_reason = outcome.reason
            return cfg
        if outcome.kind != "prepared":
            _bail(
                _checkout_refusal_message(cfg, outcome, f"Cannot launch {target}")
                + "\nNo work was started.",
                exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
            )
        self.armed = True
        self._remote_expected = True
        self._destination = _git_destination(cfg)
        try:
            refreshed = load_config(cfg.repo_root)
        except ConfigError as exc:
            _bail(str(exc), exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE)
        if _git_destination(refreshed) != self._destination:
            _bail(
                f"Cannot launch {target}: coga.toml on "
                f"{cfg.git_remote}/{cfg.git_control_branch} changes the Git "
                "destination; retry so one configuration governs the launch. "
                "No work was started.",
                exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
            )
        self._contexts_root = refreshed.contexts_root
        return refreshed

    def admit(self, cfg: Config) -> None:
        if self.armed or not cfg.git_enabled:
            return
        try:
            root = git.toplevel(cfg.repo_root)
            self._remote_expected = bool(
                root is not None and git.remote_configured(root, cfg.git_remote)
            )
        except git.GitError:
            return
        if root is None:
            return
        self.armed = True
        self._destination = _git_destination(cfg)
        self._contexts_root = cfg.contexts_root

    def settle(self, cfg: Config, *, subject: str) -> bool:
        """Return the checkout; False means stop chaining (already reported)."""
        if not self.armed:
            return True
        if self.stopped:
            return False
        try:
            refreshed = load_config(cfg.repo_root)
        except ConfigError as exc:
            self._stop(f"config reload before checkout return failed: {exc}")
            return False
        if _git_destination(refreshed) != self._destination:
            self._stop("coga.toml changed the Git destination during the launch")
            return False
        # ticket.py reloads config before its return callback. Keep the root
        # captured at admission/the preceding return, not the callback's
        # already-refreshed view of a relocation.
        previous_contexts_root = self._contexts_root or cfg.contexts_root
        cfg = refreshed
        # The end-of-command sweep, run before the switch rather than after
        # it: routine state a session or ticket.py wrote without publishing
        # lands now, and only what publication could not land blocks.
        git.sync_coga_state(
            cfg, message="Sync coga state before checkout return",
            previous_contexts_root=previous_contexts_root,
        )
        outcome = git.prepare_control_checkout(
            cfg, require_remote_control=self._remote_expected,
            previous_contexts_root=previous_contexts_root,
        )
        if outcome.kind in {"prepared", "exempt"}:
            self._contexts_root = cfg.contexts_root
            return True
        self.stopped = True
        git.state_sweep_withheld.set(True)
        _report(
            _checkout_refusal_message(
                cfg, outcome, f"Checkout return after {subject} did not complete"
            )
            + "\nThe remaining changes were preserved and not published; the "
            "session's own result stands. Not chaining further.",
            fg='red',
            bold=True,
            err=True,
        )
        return False

    def reload(self, cfg: Config, ref: TargetRef) -> tuple[Config, TargetRef | None]:
        """Fresh config and the exact same target after a settled boundary.

        `None` means the target is gone from control; a changed Git
        destination stops the launch rather than cleaning under a second
        configuration.
        """
        try:
            refreshed = load_config(cfg.repo_root)
        except ConfigError as exc:
            self._stop(f"config reload failed: {exc}")
            return cfg, ref
        if _git_destination(refreshed) != self._destination:
            self._stop("coga.toml changed the Git destination during the launch")
            return cfg, ref
        self._contexts_root = refreshed.contexts_root
        try:
            current = resolve_target(refreshed, ref.id_slug)
        except TaskNotFoundError:
            return refreshed, None
        if current.id_slug != ref.id_slug:
            return refreshed, None
        return refreshed, current

    def _stop(self, reason: str) -> None:
        self.stopped = True
        git.state_sweep_withheld.set(True)
        _report(
            f"Launch stopped chaining: {reason}; retry the launch.",
            fg='red',
            err=True,
        )


def _git_destination(cfg: Config) -> tuple[object, ...]:
    return (cfg.git_enabled, cfg.git_remote, cfg.git_control_branch, cfg.repo_root)


def _checkout_refusal_message(
    cfg: Config, outcome: git.CheckoutPreparation, prefix: str
) -> str:
    what = (
        "stopped part-way"
        if outcome.kind == "failed"
        else "refused to change the checkout"
    )
    lines = [
        f"{prefix}: bringing this checkout to a clean {cfg.git_control_branch!r} "
        f"at {cfg.git_remote}/{cfg.git_control_branch} {what}: {outcome.reason}"
    ]
    lines.extend(f"  - {item}" for item in outcome.blocking)
    lines.append(
        "Before changing this checkout, identify its branch's ticket and check "
        f"the ticket on current {cfg.git_remote}/{cfg.git_control_branch} and "
        "the PR's merge status. Inspect uncommitted changes separately; a "
        "merged PR does not prove those edits are finished. Do not automatically "
        "stash or discard them. Follow coga/checkouts/launch-boundary's "
        "checkout recovery procedure."
    )
    return "\n".join(lines)


def _checkout_exemption(cfg: Config, ref: TaskRef) -> str | None:
    """Why an ordinary ticket launch keeps its checkout, else None.

    The one exemption: the invoking checkout is the ticket's recorded
    `worktree:` and HEAD is its recorded `branch:` — the verified recorded
    human-assist route (which owns its own refusals, such as a
    control-named branch) or a sandbox clone. The invoking bytes are
    read first; a `## Dev` record published after the branch point is read
    from the last fetched control copy. A local released megalaunch witness is
    likewise left to its own reconciliation. Classification only: nothing
    composes from these bytes.
    """
    if not cfg.git_enabled:
        return None
    try:
        root = git.toplevel(cfg.repo_root)
        if root is None:
            return None
        head_branch = git.symbolic_head(root)
        if head_branch is None:
            return None
        copies: list[bytes | None] = [ref.ticket_path.read_bytes()]
        revision = git.known_control_revision(cfg, root)
        if revision is not None:
            copies.append(
                git.tree_bytes(root, revision, git.relative_to_root(root, ref.ticket_path))
            )
    except (git.GitError, OSError):
        return None
    for index, data in enumerate(copies):
        try:
            ticket = Ticket.parse(data.decode("utf-8")) if data is not None else None
        except (UnicodeDecodeError, TicketError):
            ticket = None
        if ticket is None:
            continue
        if index == 0 and released_launch_generation(ticket.launch_generation):
            # Megalaunch's local-only released witness: its own
            # reconciliation transaction owns this checkout's state.
            return "it holds a released megalaunch admission to reconcile"
        try:
            _, blackboard = split_body(ticket.body)
        except TaskFileError:
            continue
        branch = parse_branch_name(blackboard or "")
        worktree = parse_worktree_path(blackboard or "")
        if (
            branch == head_branch
            and worktree
            and same_git_checkout(cfg.repo_root, worktree)
        ):
            return f"it runs in its recorded checkout on {branch!r}"
    return None


def _recorded_single_checkout_assist_branch(
    cfg: Config, ticket: Ticket
) -> str | None:
    """The recorded PR branch when launch runs in its exact recorded checkout.

    Human ownership plus an explicit override authorizes the assist, but it
    does not prove that the checkout running `coga launch` owns the recorded
    branch. The current checkout must equal `worktree:`, be on `branch:`, and
    carry a recorded `pr:` link before launch may even attempt the live PR-head
    verification that authorizes publication. A different checkout, a missing
    `## Dev` field, or a different current branch returns None and retains
    ordinary local-only log handling. Linked worktrees and independent fallback
    clones are supported when they are themselves the exact recorded checkout.
    """
    if not cfg.git_enabled:
        return None
    _, blackboard = split_body(ticket.body)
    branch = parse_branch_name(blackboard or "")
    worktree = parse_worktree_path(blackboard or "")
    pr_url = parse_pr_url(blackboard or "")
    if not branch or not worktree or not pr_url:
        return None
    try:
        root = git.toplevel(cfg.repo_root)
        matches = bool(
            root is not None
            and same_git_checkout(cfg.repo_root, worktree)
            and git.current_branch(root) == branch
        )
        return branch if matches else None
    except git.GitError:
        return None


def _verify_recorded_assist_pr_head(
    cfg: Config,
    ticket: Ticket,
    branch: str,
    *,
    expected_pr_url: str | None = None,
) -> str:
    """Compatibility seam around the shared PR-assist verifier."""
    return pr_assist.verify_recorded_assist_pr_head(
        cfg,
        ticket,
        branch,
        expected_pr_url=expected_pr_url,
    )


def _align_recorded_assist_checkout(
    cfg: Config, ticket: Ticket
) -> tuple[bool, str]:
    """Fast-forward a verified recorded assist checkout before launch derivation.

    Returns whether HEAD moved plus the exact fetched remote OID. Only files
    under the Coga roots (`git.coga_root_paths`) may be dirty; a merely-behind
    checkout with other dirt, a missing remote branch, or an ahead/diverged
    tip raises instead of composing from stale files.
    """
    _, blackboard = split_body(ticket.body)
    branch = parse_branch_name(blackboard or "")
    root = git.toplevel(cfg.repo_root)
    if root is None or not branch or not git.remote_configured(root, cfg.git_remote):
        raise git.GitError("the recorded assist checkout has no configured remote")
    before = git.run_git(root, "rev-parse", "HEAD").strip()
    remote_ref = f"refs/remotes/{cfg.git_remote}/{branch}"
    git.run_git(
        root, "fetch", "--quiet", cfg.git_remote, f"+refs/heads/{branch}:{remote_ref}"
    )
    remote_oid = git.run_git(root, "rev-parse", remote_ref).strip()
    if before == remote_oid:
        return False, remote_oid
    ancestry = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", before, remote_oid],
        capture_output=True,
        check=False,
    )
    if ancestry.returncode != 0:
        raise git.GitError(
            f"local {branch!r} is ahead of or diverged from "
            f"{cfg.git_remote}/{branch}; reconcile it (`git pull --rebase`) first"
        )
    excludes = [
        f":(exclude){git.relative_to_root(root, path)}"
        for path in git.coga_root_paths(cfg)
    ]
    dirt = git.run_git(root, "status", "--porcelain", "--", ".", *excludes).strip()
    if dirt:
        raise git.GitError(
            f"the recorded assist checkout has uncommitted changes beyond "
            f"Coga state; commit or stash them before launching:\n{dirt}"
        )
    git.run_git(root, "merge", "--ff-only", "--quiet", remote_oid)
    return True, remote_oid


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
    pointer = (
        f"Read the file {prompt_file} in full before doing anything else — "
        "its contents are your complete composed Coga prompt, too large to "
        "pass as a command-line argument. Follow it exactly as if it had "
        "been given to you as this message."
    )
    return f"{pointer}\n\n{marker_line}\n" if marker_line else pointer


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
    launch_args = shlex.split(agent.launch_args)
    discussion_template = _discussion_template(agent) if discussion else ""
    if discussion_template:
        tokens = [
            tok.replace("{prompt}", prompt)
            for tok in shlex.split(discussion_template)
        ]
        return [agent.cli, *launch_args, *tokens]
    name_args: list[str] = []
    if name and agent.name_flag:
        name_args = [*shlex.split(agent.name_flag), name]
    session_id_args: list[str] = []
    if session_id and agent.session_id_flag:
        session_id_args = [*shlex.split(agent.session_id_flag), session_id]
    return [
        agent.cli,
        *launch_args,
        *name_args,
        *session_id_args,
        prompt,
    ]


class AgentSessionResult(NamedTuple):
    exit_code: int
    termination_kind: str
    termination_reason: str | None = None
    # Whether the supervisor observed a matching done signal, independent of
    # `termination_kind` (a signal followed by a crash is still a `crash`).
    # False also means "no sentinel channel"; see `ReplOutcome`.
    done_signalled: bool = False


def missing_launch_file_message(exc: FileNotFoundError) -> str:
    """Report a pre-spawn `FileNotFoundError` as the missing file it is.

    `spawn_agent_session` composes the prompt and writes it to disk before its
    executable boundary (ordinary launches also append their audit there), so
    a `FileNotFoundError` escaping it is far more often a missing prompt layer
    than a missing agent CLI — and blaming the CLI sends the operator to debug
    a PATH that is fine. Name the path instead; `AgentCliNotFound` carries the
    genuine CLI case.
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
    assist_branch: str | None = None,
    assist_agent: str | None = None,
    before_recompose: Callable[[], None] | None = None,
    validate_before_spawn: Callable[[], None] | None = None,
    before_spawn: Callable[[], None] | None = None,
    validate_after_spawn: Callable[[], None] | None = None,
    after_spawn_release: Callable[[], None] | None = None,
    record_launch: bool = True,
    record_launch_on_spawn: bool = False,
    secrets_are_scoped: bool = True,
    stateless_identity: tuple[str, str] | None = None,
    include_blocker_preamble: bool = True,
    composed_prompt: str | None = None,
    checkout_notice: CheckoutNotice | None = None,
) -> AgentSessionResult:
    """Spawn one agent process once.

    This is the shared single-shot body beneath `coga launch`'s supervisor
    chain: compose prompt, write prompt file, build argv, log, spawn under the
    PTY watcher for interactive REPLs, and remove the temp prompt file.

    Per-caller differences are arguments here, not forked command code:
    `env` carries the secrets policy (`coga launch` passes a launch env;
    authoring passes the ambient process env with no Coga secret injection),
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
    `composed_prompt` carries a prompt a caller already materialized at its
    own preflight boundary. The spawn uses those exact bytes instead of
    recomposing after intervening lifecycle publication. `checkout_notice`
    is the caller's observed checkout result for a prompt composed here.
    The launch supervisor loop and step chaining deliberately stay outside.

    `commit_log` immediately publishes the `log.md` launch append (via
    `sync_log`) instead of leaving it for the end-of-command sweep. The
    ordinary launch path always sets it: stateless bootstrap launches have no
    later task-state sync to carry the log, and a code step's start check
    requires a clean tree before the agent branches. `coga ticket` sets it
    too, so an attended authoring session does not hold a dirty log open.
    `assist_branch` and
    `assist_agent` name an explicit assist on a human-owned step running in
    the recorded single-checkout PR worktree: the
    child inherits them so its in-session lifecycle commands attribute audit
    lines to the assisting agent rather than the human ticket owner. `coga
    ticket` leaves them unset. `secrets_are_scoped` is False only
    when the caller passes an ambient environment instead of
    `build_launch_env`; that distinction keeps redaction from mistaking an
    unrelated same-named variable for a configured secret value.
    ``before_recompose`` runs after prompt, argv, and pre-session audit
    publication. Once it returns, this preflight pass exits through a private
    signal so the caller can reload and re-compose from state those publications
    may have moved. The recomposed pass sets ``record_launch=False`` because the
    first pass already made that audit durable. ``validate_before_spawn`` is a
    guard-only boundary before the launch audit. ``before_spawn`` remains the
    final publication boundary immediately before the PTY supervisor: human
    assists publish lifecycle there, while recurring delegation revalidates its
    period lease. ``validate_after_spawn`` is the narrower executable-admission
    guard: it runs after the supervisor creates its child but while a private
    pipe still holds that child before exec. ``record_launch_on_spawn`` defers
    the audit append into that same gate. A guarded deferred audit is bracketed
    by two calls to ``validate_after_spawn``: the second exact proof runs after
    the append and immediately before release. The append, proof, and supervisor
    pipe release share Git's local `state_lock`, so another Coga command in
    this checkout cannot publish the provisional line while that proof is in
    flight. ``after_spawn_release`` runs after that pipe release but before the
    lock is dropped. A Git-backed megalaunch uses it to admit its visible
    pending claim only after the held child can execute.
    Refusal removes only this invocation's append. A pipe-release failure
    invokes the same compensation inside the lock and clears the
    session-started flag before the held child is killed. Such an audit cannot
    also request immediate Git publication, because a published append cannot
    be transactionally retracted if that final proof or release refuses.
    """
    # A nested launch inherits its parent's process environment. Re-derive the
    # task metadata at this last shared boundary so an agent identifies the
    # task it is actually running. `apply_task_env` copies first, so
    # caller-owned environments remain unchanged and unrelated parent values
    # still pass through — but it clears the whole task namespace before
    # rewriting it, so a variable this target does not export (a stateless
    # bootstrap ticket's absent `COGA_TASK_BLACKBOARD`) cannot survive by
    # inheritance.
    require_agent_sessions()
    env = apply_task_env(env, cfg, ref, ticket)
    # Never inherit a parent assist capability into a nested ordinary launch.
    # Re-mint it only for the exact recorded branch/PR this spawn already
    # proved.
    env.pop(ASSIST_AGENT_ENV, None)
    env.pop(ASSIST_BRANCH_ENV, None)
    env.pop(ASSIST_PR_ENV, None)
    if assist_branch is not None:
        if not assist_agent:
            raise ComposeError(
                "recorded assist checkout has no effective launch agent"
            )
        _, blackboard = split_body(ticket.body)
        assist_pr_url = parse_pr_url(blackboard or "")
        if not assist_pr_url:
            raise ComposeError(
                "recorded assist checkout has no `pr:` link under `## Dev`"
            )
        env[ASSIST_AGENT_ENV] = assist_agent
        env[ASSIST_BRANCH_ENV] = assist_branch
        env[ASSIST_PR_ENV] = assist_pr_url

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
            checkout=checkout_notice,
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
    prompt_arg = _argv_prompt(prompt, prompt_file, marker_line)
    if prompt_arg is not prompt:
        _report(
            f"{label}: prompt exceeds the {_MAX_PROMPT_ARG_BYTES}-byte "
            f"single-argument limit — the agent will read it from "
            f"{prompt_file}"
        )

    usage_provider = usage_tracking.parser_key_for_cli(agent.cli)
    usage_session_id = (
        str(uuid4()) if agent.session_id_flag else None
    )
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
    provisional_audit: tuple[bytes | None, bytes] | None = None
    outcome_status: usage_tracking.OutcomeStatus = "unknown"
    outcome: ReplOutcome | None = None

    try:
        if (
            record_launch
            and record_launch_on_spawn
            and commit_log
        ):
            raise ValueError(
                "a guarded spawn-time launch audit cannot be published before "
                "its post-append validation"
            )
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

        deferred_launch_audit = record_launch and record_launch_on_spawn

        def record_and_publish_launch_audit() -> bytes:
            audit_append = append_log(cfg, ref.id_slug, actor, log_message)
            if commit_log:
                # A bootstrap target has no later task-state sync to carry its
                # launch line. When audit recording is spawn-gated, this
                # publication remains inside that gate too.
                git.sync_log(cfg, message=f"Log: {ref.id_slug}")
            return audit_append

        if record_launch and not deferred_launch_audit:
            record_and_publish_launch_audit()

        if before_recompose is not None:
            before_recompose()
            raise _RecomposeAfterLaunchPublication()

        if name and sys.stdout.isatty():
            sys.stdout.write(f"\033]2;{name}\007")
            sys.stdout.flush()

        if before_spawn is not None:
            before_spawn()

        gated_spawn_admission = (
            validate_after_spawn is not None
            or deferred_launch_audit
            or after_spawn_release is not None
        )
        if not gated_spawn_admission:
            spawn_started = True

        def admit_spawned_child() -> None:
            nonlocal provisional_audit, spawn_started
            if validate_after_spawn is not None:
                validate_after_spawn()
            if deferred_launch_audit:
                audit_path = log_path(cfg)
                before = audit_path.read_bytes() if audit_path.is_file() else None
                audit_append = record_and_publish_launch_audit()
                provisional_audit = (before, audit_append)
                if validate_after_spawn is not None:
                    try:
                        # The append is visible to same-checkout editors and
                        # publishers, so the proof that authorizes exec must
                        # follow it rather than merely precede it.
                        validate_after_spawn()
                    except BaseException as exc:
                        provisional_audit = None
                        if not _retract_log_append(cfg, before, audit_append):
                            raise RuntimeError(
                                f"{exc}; could not remove refused launch audit "
                                f"from {audit_path}"
                            ) from exc
                        raise
            spawn_started = True

        def rollback_spawn_admission() -> None:
            """Retract callback effects when the held child was not released."""
            nonlocal provisional_audit, spawn_started
            spawn_started = False
            if provisional_audit is None:
                return
            before, audit_append = provisional_audit
            provisional_audit = None
            if not _retract_log_append(cfg, before, audit_append):
                raise RuntimeError(
                    "could not remove unreleased launch audit from "
                    f"{log_path(cfg)}"
                )

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
            after_spawn=admit_spawned_child if gated_spawn_admission else None,
            spawn_release_guard=(
                (lambda: git.state_lock(cfg))
                if deferred_launch_audit or after_spawn_release is not None
                else None
            ),
            after_spawn_release=after_spawn_release,
            on_spawn_admission_failure=(
                rollback_spawn_admission if gated_spawn_admission else None
            ),
        )
        outcome_status = _session_outcome_status(outcome)
        return AgentSessionResult(
            outcome.exit_code,
            outcome.kind,
            outcome.reason,
            outcome.done_signalled,
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
            # The usage record lands in `log.md` *past* the agent's final
            # `bump`/`mark` sync, so publish exactly the log now via its
            # union-safe path; it also carries this launch's own log line. A
            # supervised chain reaches this finally per step, so each step's
            # record publishes promptly. Non-fatal.
            if isinstance(cfg, Config):
                log_published = git.sync_log(cfg, message=f"Log: {session_slug}")
                if log_published is None and cfg.git_enabled:
                    _report(
                        f"Session {session_slug} ended; log publication was not "
                        f"confirmed. The local log is retained at {log_path(cfg)}. "
                        "See the [git] diagnostic above before retrying publication.",
                        fg='yellow', bold=True, err=True,
                    )
        try:
            prompt_file.unlink()
        except FileNotFoundError:
            pass


def _terminal_status_probe(
    cfg: Config, ref: TaskRef | BootstrapRef, ticket: Ticket,
) -> Callable[[], str | None] | None:
    """Observe this ticket's terminal state without fetching or scanning tasks.

    With Git publication enabled, only the local remote-tracking control ref
    is proof: a lifecycle command writes its working copy *before* notifying
    and publishing, and another worktree may hold the completed copy. Without
    a configured remote, watch the exact local file. Cache unchanged blobs /
    file stats, poll at most once a second, and allow five seconds of stable
    terminal state for the ordinary sentinel path to finish first.
    """
    if isinstance(ref, BootstrapRef):
        return None

    generation = ticket.frontmatter.get("period_generation")
    initialized = False
    root: Path | None = None
    control_path: str | None = None
    cached_key: object = None
    cached_status: str | None = None
    next_poll = 0.0
    terminal_since: float | None = None

    def probe() -> str | None:
        nonlocal initialized, root, control_path, cached_key, cached_status
        nonlocal next_poll, terminal_since
        now = time.monotonic()
        if now < next_poll:
            return None
        next_poll = now + 1.0
        try:
            if not initialized:
                if getattr(cfg, "git_enabled", False):
                    root = git.toplevel(cfg.repo_root)
                    if root is not None and git.remote_configured(root, cfg.git_remote):
                        rel = git.relative_to_root(root, ref.ticket_path)
                        control_path = (
                            f"refs/remotes/{cfg.git_remote}/{cfg.git_control_branch}:{rel}"
                        )
                initialized = True
            if control_path is not None and root is not None:
                key = git.run_git(root, "rev-parse", "--verify", control_path).strip()
                text = (
                    git.run_git(root, "cat-file", "blob", key)
                    if key != cached_key else None
                )
            else:
                stat = ref.ticket_path.stat()
                key = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
                text = (
                    ref.ticket_path.read_text(encoding="utf-8")
                    if key != cached_key else None
                )
            if text is not None:
                current = Ticket.parse(text)
                status = current.status
                cached_status = (
                    status if isinstance(status, str) and status in TERMINAL_STATUSES
                    and current.frontmatter.get("period_generation") == generation
                    else None
                )
                cached_key = key
        except (OSError, UnicodeError, TicketError, git.GitError):
            # Missing/unreadable/malformed state is not evidence of completion.
            # Retry next poll; the sentinel and liveness limits remain armed.
            cached_key = None
            cached_status = None
        if cached_status is None:
            terminal_since = None
        elif terminal_since is None:
            terminal_since = now
        elif now - terminal_since >= 5.0:
            return cached_status
        return None

    return probe


def _retract_log_append(cfg: Config, before: bytes | None, appended: bytes) -> bool:
    from coga.logfile import retract_log_append
    return retract_log_append(cfg, before, appended)


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

    if (after.step, after.status) == (before.step, before.status):
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


def _interactive_stdio_has_tty() -> bool:
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
    try:
        result = refresh_agent_skill_view(coga_os)
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
