"""Run locally scheduled and on-demand recurring work."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import typer

from coga.aliases import DEFAULT_ALIASES, validate_aliases
from coga.compose import LaunchContext
from coga.config import Config, ConfigError, ConfigParseError, load_config
from coga.launch import LaunchBail, interactive_stdio_has_tty
from coga.lifecycle import TERMINAL_STATUSES
from coga.logfile import append_log, task_log_lines
from coga.mark import PREPARE_ACTIVE_ERRORS, mark_active, mark_done, mark_in_progress, mark_paused
from coga.notification import notify
from coga.launch_script import script_entry_point
from coga.paths import RepoResourceUnreadable
from coga.workflow import WorkflowError
from coga.mark import RequiredExtensionMissing, WorkflowMissing, MainAgentUnavailable
from coga.period_state import SNAPSHOT_FILE, parse_keys
from coga.recurring import (
    _AGENT_NEEDS_TTY, _AGENT_NEEDS_TTY_LABEL, _declares_clone_scope,
    DueScan, DueTask, PAUSE_WATCHDOG, RecurringError, SWEEP_ACTOR, SWEEP_PAUSE_SUFFIX,
    WATCHDOG_ACTOR, assert_frozen_delegation, create_named,
    format_serviced_log, frozen_task_delegate, load_effective_template,
    resolve_agent_delegate, resolve_template_source, resumable_pause, recurring_dir,
    scan_clone_due, scan_due,
)
from coga.recurring_activity import RepoActivity, check_activity
from coga.recurring_autofix import (
    RunRecord, TaskOutcome, blackboard_for_ref, outcome_for_ref, run_autofix,
    scan_lines_for_record,
)
from coga.recurring_clone import run_clone_template
from coga.repl_supervisor import _TIMEOUT_EXIT_CODE
from coga.session_limits import resolve_idle_timeout, resolve_max_session
from coga.taskfile import TaskFileError, read_blackboard, split_body
from coga.tasks import TaskRef, read_ticket
from coga.ticket import Ticket, TicketError
from coga.validate import TaskValidationError
from coga.workspace_discovery import discover_coga_repos


_RECURRING_IDLE_TIMEOUT_SECONDS = 900.0


def recurring_owner_refusal(cfg: Config) -> str | None:
    """Why this operator may not launch recurring here, or None if they may.

    Recurring sweeps mutate shared period state (the created period task and
    the repo-global serviced-period ledger) and then launch real
    work, so two *different* operators sweeping the same repo from their own
    clones race each other. The committed `owner` in `coga.toml` picks one of
    them: every clone reads the same name, and only the operator whose
    machine-local `user` matches it may launch.

    A **policy gate, not a lock.** Same-machine overlap is already prevented by
    the sweep being sequential and foreground; the owner running two clones of
    their own can still race, and this does not try to stop them. `--force` is
    gated too — a deliberate takeover is a committed `owner` change, not a
    flag. A repo with no `owner` set behaves exactly as before.
    """
    return _recurring_owner_refusal(cfg, cfg.owner)



def _recurring_owner_refusal(cfg: Config, owner: str) -> str | None:
    """Apply the owner policy using an explicitly resolved committed value."""
    if not owner or cfg.current_user == owner:
        return None
    who = (
        f"this checkout runs as {cfg.current_user!r}"
        if cfg.current_user
        else "this checkout has no `user` set in coga.local.toml"
    )
    return (
        f"Recurring launches in this repo belong to {owner!r} "
        f"(`owner` in coga.toml); {who}. Recurring is gated to one operator so "
        "two clones cannot sweep the same repo at once — ask them to run it, "
        "or change the committed `owner` to take it over."
    )



def _repo_label(coga_os: Path, root: Path) -> str:
    host_repo = coga_os.parent
    try:
        relative = host_repo.relative_to(root)
    except ValueError:
        return str(host_repo)
    return host_repo.name if relative == Path(".") else str(relative)



def _task_outcome(
    cfg: Config,
    template: str,
    ref: TaskRef | None,
    *,
    kind: str | None = None,
    result: str = "",
    exit_code: int | None = None,
    template_damage: str | None = None,
    detail: str = "",
) -> TaskOutcome:
    """Classify one period task's run for the record.

    A launched task has no exit code worth reading in the ordinary case — the
    supervisor tears the session down on a lifecycle transition — so the
    ticket's status after the run *is* the outcome, and its blackboard is what
    the run had to say. `_stop_if_unfinished_after_launch` has already parked an
    unfinished run, which is what makes `paused` legible here.

    `template_damage` is the one thing status cannot express: a run that closed
    its own step cleanly *and* overwrote the template it was composed from. It
    overrides an otherwise-clean result so the sweep counts it as a problem.
    """
    status = outcome_for_ref(cfg, ref)
    if not result:
        # Status first, `kind` only to explain it. `kind == "script"` says the
        # deterministic phase ended the launch — including the ordinary success
        # where it closed the step itself — so reading it as a failure would
        # report every healthy `ticket.py` template as unfinished.
        if status in TERMINAL_STATUSES:
            result = "completed"
            if kind == "timeout":
                detail = (
                    "late teardown: done signal not observed before liveness stop; "
                    f"ticket is {status}"
                )
        elif kind == "timeout":
            result = "timed-out"
            detail = (
                "liveness watchdog tore the session down before it signalled done"
            )
        elif status is None:
            result = "completed"
            detail = "task directory was removed during the run"
        elif status == "blocked":
            result = "unfinished"
            detail = (
                "the deterministic `ticket.py` phase recorded a blocker"
                if kind == "script"
                else "the agent blocked on a human answer"
            )
        elif kind == "script":
            result = "unfinished"
            detail = (
                "the deterministic `ticket.py` phase stopped before the step closed"
            )
        elif kind == "agent-refused":
            result = "unfinished"
            detail = "the sweep refused the period's agent phase before spawn"
        else:
            result = "unfinished"
            detail = (
                "the run exited without a terminal transition; the sweep parked it"
            )
    if template_damage:
        # Overrides even a clean `completed`: the run finished its own work and
        # destroyed the instructions for the next one. That is the failure this
        # check exists for, so it must not be reportable as success.
        result = "damaged-template"
        detail = f"{detail}; {template_damage}" if detail else template_damage
    return TaskOutcome(
        template=template,
        slug=ref.id_slug if ref else template,
        result=result,
        exit_code=exit_code,
        final_status=status,
        detail=detail,
        blackboard=blackboard_for_ref(ref),
    )



def _record_outcome(record: RunRecord, outcome: TaskOutcome) -> None:
    """Record one run and surface template damage without the analyst.

    `COGA_AUTOFIX=0` deliberately disables run-log rendering and analysis, but
    damage to the next firing's instructions cannot become silent with it. The
    structured outcome still feeds the analyst when enabled; stderr is the
    unconditional correction-loop signal.
    """
    record.add(outcome)
    if outcome.result != "damaged-template":
        return
    typer.secho(
        f"Recurring template {outcome.template!r} was damaged by "
        f"{outcome.slug}: {outcome.detail}\n"
        "Repair the template from git history before another firing.",
        fg=typer.colors.RED,
        err=True,
    )



def _run_clone_scoped(
    cfg: Config,
    record: RunRecord,
    *,
    force: bool = False,
    inactive_since: str | None = None,
    only: str | None = None,
) -> bool:
    """Run every due `scope: clone` template in this clone; True on any problem.

    Clone-scoped templates create no period task or runner publication: each
    due template's `ticket.py` runs directly, may publish its own state under
    the scheduling contract, and this clone's ledger under `.coga/`
    records the serviced period (`recurring_clone`). Runs after the shared
    launches so a branch pass sees the tickets this sweep just closed. A
    failure is recorded for autofix and retried by the next sweep.
    """
    scan = scan_clone_due(
        cfg, force=force, inactive_since=inactive_since, only=only
    )
    record.scan_errors.extend(scan.errors)
    if scan.inactivity_skips:
        record.note(
            "clone-scoped templates skipped while the repo is inactive: "
            + ", ".join(scan.inactivity_skips)
        )
    for name in scan.serviced:
        record.scan_lines.append(f"recurring/{name} (clone): ran this period here")
    if not scan.due:
        return bool(scan.errors)
    typer.echo(
        f"\nRunning {len(scan.due)} clone-scoped template(s) in this clone...\n"
    )
    problem = bool(scan.errors)
    for due in scan.due:
        name = due.template.name
        script = due.template.script_entry_point
        assert script is not None  # `Template.load` requires it for clone scope
        typer.secho(
            f"recurring/{name} (clone, period {due.period_key})",
            fg=typer.colors.CYAN,
        )
        try:
            result = run_clone_template(
                cfg,
                name,
                script,
                due.period_key,
                secrets=due.template.frontmatter.get("secrets"),
            )
        except Exception as exc:  # one template must not stop the rest
            problem = True
            typer.secho(
                f"recurring/{name} (clone) could not run: {exc}",
                fg=typer.colors.RED,
                err=True,
            )
            _record_outcome(
                record,
                TaskOutcome(
                    template=name,
                    slug=f"recurring/{name}",
                    result="failed",
                    detail=f"clone-scoped run could not start: {exc}",
                ),
            )
            continue
        if result.exit_code:
            problem = True
            typer.secho(
                f"recurring/{name} (clone) exited {result.exit_code}; this "
                f"clone retries it next sweep. Log: {result.log_path}",
                fg=typer.colors.RED,
                err=True,
            )
        _record_outcome(
            record,
            TaskOutcome(
                template=name,
                slug=f"recurring/{name}",
                result="failed" if result.exit_code else "completed",
                exit_code=result.exit_code,
                detail=f"clone-scoped run for period {result.period}",
                blackboard=result.output,
            ),
        )
    return problem



@dataclass(frozen=True)
class DelegatedRunResult:
    """Exit status plus the delegated supervisor's termination class."""

    exit_code: int
    kind: str | None



def _template_description(cfg: Config, template: str) -> str | None:
    """A recurring template's body above its blackboard fence, or None.

    That region is the template's *instructions*: `create_template` copies it
    into every period task, so it is what the next firing composes as its own
    prompt. A firing legitimately rewrites its template's blackboard — that is
    where cross-run state lives — but never the region above the fence.

    None means "nothing to compare": the file is unreadable, or it carries no
    single fence, so the body and the blackboard cannot be told apart. Callers
    read None-before as "no baseline" and None-after as damage.
    """
    # Compare the *selected definition*. For a package-backed job the repo
    # parent is a state-only carrier: its above-fence region (the reserved
    # marker) is compared too, so a firing that writes prose above the
    # carrier's fence is still damage while ordinary state updates are not.
    src = resolve_template_source(cfg, template)
    definition = src.ticket_path or (recurring_dir(cfg) / template / "ticket.md")
    paths = [definition]
    state = src.state_dir / "ticket.md"
    if state != definition and (state.exists() or state.is_symlink()):
        paths.append(state)
    regions: list[str] = []
    for path in paths:
        try:
            above, _ = split_body(Ticket.read(path).body)
        except (OSError, UnicodeError, TicketError, TaskFileError):
            # `UnicodeError` alongside the rest, as the four sibling
            # `Ticket.read` call sites in this module do: `read_text` raises
            # `UnicodeDecodeError` on a non-UTF-8 file, and a corrupt template
            # must not abort the sweep with a traceback from a check that only
            # observes.
            return None
        regions.append(above)
    return "\n".join(regions)



def _template_damage(before: str | None, after: str | None) -> str | None:
    """Return how a firing damaged its own recurring template, or None.

    The failure this exists for: a run told to "replace the `## Run Summary`
    section" resolved that section by plain-text search, wrote from there to end
    of file, and pasted its own notes over the template's instructions and its
    blackboard fence. The run still reached `done`, so the sweep called it
    `completed` and reported `problems: 0` — nothing had ever looked at the
    template file. Compare the bytes instead of trusting the lifecycle status.
    """
    if before is None:
        # No baseline — a template that was already fence-less or unreadable
        # before this firing is `coga validate`'s finding, not this run's.
        return None
    if after is None:
        return (
            "the firing left its recurring template without exactly one "
            "readable blackboard fence — it now has none, or more than one — "
            "so its Description is no longer separable from the run's own "
            "notes; the next firing would compose this run's output as its "
            "instructions. Check which case it is before repairing: a run "
            "whose notes quote the fence on its own line duplicates it, which "
            "is a different repair from one that overwrote it"
        )
    if after != before:
        return (
            "the firing rewrote its recurring template's Description (the "
            "region above the blackboard fence); a firing may only write below "
            "the fence. Confirm against git history before restoring anything: "
            "both reads come from the live working tree, so a run that left the "
            "checkout on another branch, or that fast-forwarded repo state "
            "mid-run, can surface a legitimate edit here"
        )
    return None



def _damage_since(cfg: Config, template: str, before: str | None) -> str | None:
    """`_template_damage` against the template's bytes as they are right now.

    Every call site is the same pair — the baseline captured before dispatch,
    re-read after the run — so it is spelled once here rather than five times.
    """
    return _template_damage(before, _template_description(cfg, template))



def _valid_agent_override(cfg: Config, agent_override: str | None) -> bool:
    """Fail loud on an unknown recurring agent, even when no task is due."""
    if agent_override is None:
        return True
    try:
        cfg.agent_type(agent_override)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return False
    return True



def _recurring_launch_context(interactive: bool) -> LaunchContext:
    """Map this recurring invocation onto its composed session-conduct layer.

    Every runner-owned spelling — the bare sweep, `--force`, `coga run
    recurring-scan`, a named `recurring launch <name>`, an ordinary period
    task's agent phase, and a delegated stateless bootstrap session — is a
    queue: nobody is necessarily watching, so an agent that asks and waits
    hangs the sweep until a liveness timeout fails the task. `--interactive`
    is the operator stepping through by hand, which is a genuinely attended
    session. The entry point already knows which it is, so no ticket field,
    config option, or user-facing session-mode knob is involved.
    """
    return "attended" if interactive else "recurring"



def _firing_label(last_fire: datetime, now: datetime) -> str:
    """Human label for a scheduled firing — 'ready' or 'overdue Nd'."""
    delta = now - last_fire
    stamp = last_fire.strftime("%a %H:%M")
    if delta.total_seconds() < 86400:
        return f"ready ({stamp})"
    return f"overdue {delta.days}d ({stamp})"



def _watchdog_row_detail(task: DueTask) -> str:
    """Scan-row text for a watchdog-paused period (console and run record)."""
    assert task.ref is not None
    if task.launch_refusal:
        return f"watchdog timeout; coga launch {task.ref.id_slug}"
    return "watchdog timeout; resuming"



def _open_asks_row_detail(task: DueTask) -> str:
    """Scan-row text for a sweep-paused period still waiting on its asks."""
    assert task.ref is not None
    return f"paused; open asks — coga unblock {task.ref.id_slug}"



def _print_table(scan: DueScan, *, force: bool = False) -> None:
    """Print a one-line-per-template scan summary."""
    if not (
        scan.tasks
        or scan.errors
        or scan.admission_skips
        or scan.inactivity_skips
        or scan.agent_refusals
    ):
        return

    now = datetime.now()
    typer.echo(f"Recurring scan — {now:%Y-%m-%d %H:%M}\n")
    for task in scan.tasks:
        when = _firing_label(task.last_fire, now)
        if task.ref is None:
            # The period was created earlier this cycle and the task
            # was removed afterwards (a later Dream retro pass or `coga delete`).
            action = typer.style(
                "skip (ran this period)", fg=typer.colors.BRIGHT_BLACK
            )
        elif task.period_contradiction:
            action = typer.style(
                f"error ({task.period_contradiction})", fg=typer.colors.RED
            )
        elif task.watchdog_paused and (task.launch_refusal or not force):
            # A watchdog pause stays loud even while a bare sweep retries it.
            action = typer.style(
                f"needs attention ({_watchdog_row_detail(task)})",
                fg=typer.colors.RED,
            )
        elif task.resuming:
            # An orphaned `in_progress` period task from a dead sweep, or a
            # sweep-paused run — relaunch resumes its current step rather than
            # starting a fresh run.
            action = typer.style("→ resume", fg=typer.colors.YELLOW)
        elif task.launchable or (force and not task.launch_refusal):
            action = typer.style("→ launch", fg=typer.colors.GREEN)
        elif task.sweep_paused:
            action = typer.style(
                f"skip ({_open_asks_row_detail(task)})",
                fg=typer.colors.BRIGHT_BLACK,
            )
        else:
            action = typer.style(
                f"skip ({task.status})", fg=typer.colors.BRIGHT_BLACK
            )
        typer.echo(f"  {task.template:<20} {when:<26} {action}")

    for task, reason in scan.admission_skips:
        when = _firing_label(task.last_fire, now)
        skipped = typer.style(f"skip ({reason})", fg=typer.colors.BRIGHT_BLACK)
        typer.echo(f"  {task.template:<20} {when:<26} {skipped}")

    for name, last_fire in scan.inactivity_skips:
        when = "-" if last_fire is None else _firing_label(last_fire, now)
        skipped = typer.style(f"skip ({scan.inactivity_reason})", fg=typer.colors.BRIGHT_BLACK)
        typer.echo(f"  {name:<20} {when:<26} {skipped}")

    for name, last_fire, _reason in scan.agent_refusals:
        when = _firing_label(last_fire, now)
        skipped = typer.style(
            f"skip ({scan.agent_refusal_label})", fg=typer.colors.YELLOW
        )
        typer.echo(f"  {name:<20} {when:<26} {skipped}")

    for name, msg in scan.errors:
        bad = typer.style(f"skip (error: {msg})", fg=typer.colors.RED)
        typer.echo(f"  {name:<20} {'':<26} {bad}")



def _resume_named_pause(cfg: Config, ref: TaskRef) -> int | None:
    """Reactivate a non-human-paused period before a named launch.

    The named counterpart of the sweep's `DueTask.resumes_pause`: a watchdog
    pause, or a sweep pause whose asks are resolved, is resumed from its
    recorded step. A human pause is left for `_launch_created` to report. An
    agent-backed resume needs an agent-capable terminal, so refuse before
    reactivating rather than leave the period active with nothing to run it.
    Returns an exit code to stop with, or None to continue to the launch.
    """
    try:
        ticket = read_ticket(ref)
    except TicketError:
        return None  # `_launch_created` reports the unreadable ticket.
    if ticket.status != "paused":
        return None
    try:
        origin = resumable_pause(cfg, ref)
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return 2
    if not origin:
        return None
    if script_entry_point(ref, ticket, cfg=cfg) is None:
        if not interactive_stdio_has_tty():
            typer.secho(
                f"cannot resume {ref.id_slug}: {_AGENT_NEEDS_TTY}",
                fg=typer.colors.RED,
                err=True,
            )
            return 2
    try:
        _resume_paused_period(cfg, ref, watchdog=origin == PAUSE_WATCHDOG)
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return 2
    return None



def _record_unlaunched_creates(scan: DueScan, record: RunRecord) -> None:
    """Flag every period this sweep created but never launched.

    A create refused at admission because control changed it, or skipped by a
    launch-loop path that records only a note, leaves no outcome behind. The
    sweep would otherwise report `problems: 0` over lost work, so absence of an
    outcome is the signal, as with admitted watchdog recoveries above.
    """
    ran = {outcome.slug for outcome in record.outcomes}
    unlaunched = [
        (
            task.ref.id_slug,
            task.period_contradiction or "no launch outcome was recorded",
        )
        for task in scan.tasks
        if task.ref is not None
        and (task.created or task.replaced_done)
        and task.ref.id_slug not in ran
    ]
    for slug, reason in unlaunched:
        detail = f"created this sweep but never launched ({reason})"
        typer.secho(f"{slug}: {detail}", fg=typer.colors.RED, err=True)
        record.scan_problems.append((slug, detail))



def _resume_paused_period(cfg: Config, ref: TaskRef, *, watchdog: bool) -> None:
    """Reactivate a non-human-paused period so launch resumes its saved step.

    Only for a pause `recurring._pause_origins` attributed to the sweep or the
    watchdog; a human pause is never reactivated here. `coga launch` then
    re-composes the period from its retained `step:` and blackboard.
    """
    cause = "watchdog-paused" if watchdog else "sweep-paused"
    try:
        mark_active(
            cfg,
            ref,
            read_ticket(ref),
            actor=SWEEP_ACTOR,
            log_message=f"activated (paused → active) to resume a {cause} run",
            echo=f"{ref.id_slug}: active (resuming {cause} run)",
        )
    except (
        TicketError,
        WorkflowMissing,
        WorkflowError,
        MainAgentUnavailable,
        RepoResourceUnreadable,
        RequiredExtensionMissing,
        TaskValidationError,
    ) as exc:
        raise RecurringError(
            f"cannot resume {cause} period {ref.id_slug}: {exc}"
        ) from exc



def _record_forced_period_locally(cfg: Config, task: DueTask) -> None:
    if task.ref is None or not task.period_key:
        return

    template = load_effective_template(cfg, task.template)
    blackboard_text = (
        read_blackboard(template.state_path, blackboard_required=False)
        if template.state_path.is_file()
        else ""
    )
    state_keys = list(template.frontmatter.get("state_keys") or [])
    if state_keys:
        _write_snapshot_from_text(
            task.ref.path,
            template.name,
            blackboard_text,
            state_keys,
        )

    _append_forced_reused_log(
        cfg, _recurring_ref(template.name), task.ref.id_slug, task.period_key
    )



def _write_snapshot_from_text(
    task_dir: Path, parent: str, blackboard_text: str, state_keys: list[str]
) -> None:
    keys = parse_keys(blackboard_text, list(state_keys))
    payload = {"parent": parent, "keys": keys}
    (task_dir / SNAPSHOT_FILE).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")



def _recurring_ref(template_name: str) -> str:
    """The log tag for a template — `recurring/<name>`."""
    return f"recurring/{template_name}"



def _append_forced_reused_log(
    cfg: Config, template_ref: str, task_id_slug: str, period_key: str
) -> None:
    """Record a forced reuse in the repo-global ledger, idempotently.

    Skipped when the same line is already present, so repeated `--force` runs
    inside one period leave one record rather than one per invocation.
    """
    needle = format_serviced_log("reused", task_id_slug, period_key)
    if any(needle in line for line in task_log_lines(cfg, template_ref)):
        return
    append_log(cfg, template_ref, "system", needle)



def _refuse_non_owner(cfg: Config) -> bool:
    refusal = recurring_owner_refusal(cfg)
    if refusal is None:
        return False
    typer.secho(refusal, fg=typer.colors.RED, err=True)
    return True


def run_recurring_all_repos(
    scan_root: Path, *, force: bool = False, interactive: bool = False,
    agent_override: str | None = None,
) -> int:
    """Run the single-repo command in each discovered checkout."""
    root = scan_root.expanduser().resolve()
    if not root.is_dir():
        typer.secho(f"{root} is not a directory.", fg=typer.colors.RED, err=True)
        return 2
    repos = discover_coga_repos(root)
    if not repos:
        typer.echo(f"No Coga repos found under {root}.")
        return 1
    typer.echo(f"Found {len(repos)} Coga repo(s) under {root}.")
    failed: list[str] = []
    unconfigured = 0
    not_owner = 0
    swept = 0
    for index, repo in enumerate(repos, 1):
        label = _repo_label(repo, root)
        try:
            cfg = load_config(repo)
            validate_aliases({**DEFAULT_ALIASES, **cfg.aliases})
        except ConfigParseError as exc:
            typer.echo(f"{label}: {exc}", err=True)
            failed.append(label)
            continue
        except ConfigError:
            unconfigured += 1
            continue
        if _refuse_non_owner(cfg):
            not_owner += 1
            continue
        typer.echo(f"\n[{index}/{len(repos)}] {label}")
        try:
            status = _run_repo_recurring(
                repo, force=force, interactive=interactive,
                agent_override=agent_override, clone_only=False,
            )
        except OSError as exc:
            typer.echo(f"{label}: {exc}", err=True)
            status = 1
        if status:
            failed.append(label)
            typer.echo(f"{label} — recurring exited {status}", err=True)
        else:
            swept += 1
    typer.echo(f"Swept {swept} of {len(repos)} Coga repo(s).")
    if unconfigured:
        typer.echo(f"Skipped {unconfigured} unconfigured repos.")
    if not_owner:
        typer.echo(f"Skipped {not_owner} repo(s) owned by another operator.")
    if failed:
        typer.echo(f"Recurring failed in {', '.join(failed)}.", err=True)
    return int(bool(failed))


def _run_repo_recurring(
    repo: Path, *, force: bool, interactive: bool,
    agent_override: str | None, clone_only: bool,
) -> int:
    argv = [sys.executable, "-m", "coga.cli", "run", "recurring-scan"]
    if force:
        argv.append("--force")
    if interactive:
        argv.append("--interactive")
    if agent_override:
        argv.extend(("--agent", agent_override))
    if clone_only:
        argv.append("--clone-only")
    return subprocess.run(argv, cwd=repo, check=False).returncode


def run_recurring_scan_recipe(cfg: Config, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="coga run recurring-scan")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--agent")
    parser.add_argument("--clone-only", action="store_true")
    args = parser.parse_args(argv)
    return run_recurring_scan(
        cfg, force=args.force, interactive=args.interactive,
        agent_override=args.agent, clone_only=args.clone_only,
    )


def _publish_scan_notes(cfg: Config, scan: DueScan) -> None:
    for task in scan.tasks:
        if task.ref is not None and task.replaced_done:
            typer.echo(f"Replaced completed {task.ref.id_slug}")
        elif task.ref is not None and task.created:
            typer.echo(f"Created {task.ref.id_slug}")
    skipped = scan.errors + [(name, reason) for name, _, reason in scan.agent_refusals]
    if skipped:
        bullets = "\n".join(f"• {name}: {reason}" for name, reason in skipped)
        notify(
            cfg, f"⚠️ recurring scan skipped {len(skipped)} template(s)\n{bullets}",
            kind="recurring-error", important=True, fatal=False,
        )


def run_recurring_scan(
    cfg: Config, *, force: bool = False, interactive: bool = False,
    agent_override: str | None = None, clone_only: bool = False,
) -> int:
    """Read due work and execute it sequentially in this checkout."""
    if _refuse_non_owner(cfg) or not _valid_agent_override(cfg, agent_override):
        return 2
    today = datetime.now().date()
    activity = RepoActivity() if force else check_activity(cfg, today)
    if activity.error:
        typer.echo(f"Recurring activity unavailable: {activity.error}", err=True)
    record = RunRecord(
        started=datetime.now(), repo=cfg.repo_root.name, force=force,
        interactive=interactive, agent_override=agent_override,
    )
    agent_refusal = None if interactive_stdio_has_tty() else _AGENT_NEEDS_TTY
    failure = 0
    try:
        if not clone_only:
            scan = scan_due(
                cfg, force=force, allow_interactive=agent_refusal is None,
                inactive_since=activity.inactive_since,
                agent_unavailable_reason=agent_refusal,
                agent_unavailable_label=_AGENT_NEEDS_TTY_LABEL,
            )
            _publish_scan_notes(cfg, scan)
            _print_table(scan, force=force)
            record.scan_lines.extend(scan_lines_for_record(scan, force=force))
            record.scan_errors.extend(scan.errors)
            record.scan_problems.extend(scan.sync_problems)
            due = scan.forced if force else scan.due
            for task in due:
                if task.ref is None:
                    continue
                try:
                    if force:
                        _prepare_forced_launch(cfg, task)
                    elif task.resumes_pause:
                        _resume_paused_period(cfg, task.ref, watchdog=task.watchdog_paused)
                    code = _launch_created(
                        cfg, task.ref, interactive=interactive, agent_override=agent_override,
                        record=record, template=task.template, agent_spawn_refusal=agent_refusal,
                        scheduled=True,
                    )
                    failure = failure or code
                except (RecurringError, TicketError, TaskValidationError, OSError, *PREPARE_ACTIVE_ERRORS) as exc:
                    typer.echo(f"{task.ref.id_slug}: {exc}", err=True)
                    _record_outcome(
                        record, _task_outcome(cfg, task.template, task.ref, result="failed", detail=str(exc)),
                    )
                    failure = failure or 2
            _record_unlaunched_creates(scan, record)
        clone_problem = _run_clone_scoped(cfg, record, force=force, inactive_since=activity.inactive_since)
        return failure or (2 if record.scan_problems or clone_problem else 0)
    finally:
        if not activity.inactive or record.outcomes:
            run_autofix(cfg, record, agent_override=agent_override)


def _prepare_forced_launch(cfg: Config, task: DueTask) -> None:
    ref = task.ref
    if ref is None:
        return
    ticket = read_ticket(ref)
    if ticket.status in {"blocked", "canceled"}:
        raise RecurringError(f"Cannot force-run {ref.id_slug} while it is {ticket.status}")
    if ticket.status not in {"active", "in_progress"}:
        mark_active(
            cfg, ref, ticket, actor=f"human:{cfg.current_user}",
            log_message=f"activated ({ticket.status} → active) for forced recurring run",
            echo=f"{ref.id_slug}: active (forced recurring run)",
        )
        _record_forced_period_locally(cfg, task)


def _stop_if_unfinished_after_launch(cfg: Config, ref: TaskRef, *, timed_out: bool) -> None:
    if not ref.ticket_path.is_file():
        return
    ticket = read_ticket(ref)
    if ticket.status not in {"active", "in_progress"}:
        return
    suffix = "liveness watchdog: REPL timed out before signalling done" if timed_out else SWEEP_PAUSE_SUFFIX
    mark_paused(
        cfg, ref, ticket, actor=WATCHDOG_ACTOR if timed_out else SWEEP_ACTOR,
        log_message=f"paused ({ticket.status} → paused) — {suffix}",
        slack_text=f"⏱️ *{ref.id_slug}* timed out — {suffix}" if timed_out else None,
        echo=f"{ref.id_slug}: paused — {suffix}",
    )


def _run_delegated_task(
    cfg: Config, ref: TaskRef, *, agent_override: str | None = None,
    idle_timeout: float | None = None, max_session: float | None = None,
    launch_context: LaunchContext = "recurring", continue_after_timeout: bool,
    activate_if_needed: bool = False,
) -> DelegatedRunResult:
    from coga.launch import launch_with_before_spawn

    try:
        ticket = read_ticket(ref)
        delegate = frozen_task_delegate(ref, ticket)
        if delegate is None:
            raise RecurringError(f"{ref.id_slug} has no frozen delegate")
        resolve_agent_delegate(cfg, delegate)
        assert_frozen_delegation(ref, ticket, require_step=False)
        if ticket.status not in {"active", "in_progress"} and not (
            activate_if_needed and ticket.status in {"draft", "paused"}
        ):
            raise RecurringError(f"{ref.id_slug} is {ticket.status}; cannot start its delegate")

        def start_period() -> None:
            if ticket.status in {"draft", "paused"}:
                mark_active(cfg, ref, ticket, actor="system", log_message="activated delegated period")
            assert_frozen_delegation(ref, ticket)
            if ticket.status == "active":
                mark_in_progress(cfg, ref, ticket, actor="system", log_message=f"started delegate {delegate}")

        result = launch_with_before_spawn(
            delegate, agent_override=agent_override, idle_timeout=idle_timeout,
            max_session=max_session, return_timeout=True, launch_context=launch_context,
            before_spawn=start_period,
        )
        cfg = load_config(cfg.repo_root)
        if result.kind == "timeout":
            if continue_after_timeout:
                _stop_if_unfinished_after_launch(cfg, ref, timed_out=True)
                return DelegatedRunResult(0, "timeout")
            return DelegatedRunResult(result.exit_code or _TIMEOUT_EXIT_CODE, result.kind)
        if result.kind != "done" or result.exit_code:
            typer.echo(
                f"{delegate} ended without its done signal ({result.kind or 'unknown'}). "
                f"{ref.id_slug} remains in progress.",
                err=True,
            )
            return DelegatedRunResult(2, result.kind or "unknown")
        if ref.ticket_path.is_file():
            current = read_ticket(ref)
            if current.status == "in_progress":
                assert_frozen_delegation(ref, current)
                mark_done(
                    cfg, ref, current, actor="system", log_message=f"task done (via {delegate})",
                    slack_text=f"🎉 {ref.id_slug} finished via {delegate}",
                )
        return DelegatedRunResult(0, "done")
    except LaunchBail as exc:
        typer.echo(exc.reason or str(exc), err=True)
        return DelegatedRunResult(exc.code, "refused")
    except (ConfigError, RecurringError, TicketError, TaskValidationError, *PREPARE_ACTIVE_ERRORS) as exc:
        typer.echo(str(exc), err=True)
        return DelegatedRunResult(2, "refused")


def _launch_created(
    cfg: Config, ref: TaskRef, *, interactive: bool, agent_override: str | None,
    record: RunRecord, template: str, agent_spawn_refusal: str | None = None,
    scheduled: bool = False,
) -> int:
    ticket = read_ticket(ref)
    if ticket.status not in {"active", "in_progress"}:
        typer.echo(f"{ref.id_slug}: {ticket.status}; not launching")
        return 2 if ticket.status == "canceled" else 0
    before = _template_description(cfg, template)
    idle_timeout = resolve_idle_timeout(cfg, default=None if interactive else _RECURRING_IDLE_TIMEOUT_SECONDS)
    max_session = resolve_max_session(cfg)
    kind = None
    detail = ""
    try:
        if frozen_task_delegate(ref, ticket):
            if agent_spawn_refusal:
                raise RecurringError(agent_spawn_refusal)
            result = _run_delegated_task(
                cfg, ref, agent_override=agent_override, idle_timeout=idle_timeout,
                max_session=max_session, launch_context=_recurring_launch_context(interactive),
                continue_after_timeout=scheduled,
            )
        else:
            from coga.launch import launch_recurring_period

            result = launch_recurring_period(
                ref.id_slug, agent_override=agent_override, idle_timeout=idle_timeout,
                max_session=max_session, launch_context=_recurring_launch_context(interactive),
                agent_spawn_refusal=agent_spawn_refusal,
            )
        kind, code = result.kind, result.exit_code
        if scheduled and (not code or kind == "timeout"):
            _stop_if_unfinished_after_launch(cfg, ref, timed_out=kind == "timeout")
            if kind == "timeout":
                code = 0
    except LaunchBail as exc:
        code, detail = exc.code, exc.reason
        if detail:
            typer.echo(detail, err=True)
    _record_outcome(
        record,
        _task_outcome(
            cfg, template, ref, kind=kind, result="failed" if code and kind != "timeout" else "",
            exit_code=code or None, template_damage=_damage_since(cfg, template, before),
            detail=detail,
        ),
    )
    return code


def run_recurring_named(
    cfg: Config, name: str, *, rerun: bool = False, interactive: bool = False,
    agent_override: str | None = None,
) -> int:
    """Run a named template on demand, with the current checkout's state."""
    if _refuse_non_owner(cfg) or not _valid_agent_override(cfg, agent_override):
        return 2
    record = RunRecord(
        started=datetime.now(), repo=cfg.repo_root.name, on_demand=name,
        interactive=interactive, agent_override=agent_override,
    )
    try:
        source = resolve_template_source(cfg, name)
        if source.definition_dir is not None and _declares_clone_scope(source.definition_dir):
            return 2 if _run_clone_scoped(cfg, record, only=name) else 0
        outcome = create_named(cfg, name, rerun=rerun)
        ref = outcome.ref
        if outcome.created:
            typer.echo(f"Created {ref.id_slug}")
        else:
            typer.echo(f"{ref.id_slug} already created for this period")
            resumed = _resume_named_pause(cfg, ref)
            if resumed is not None:
                return resumed
        return _launch_created(
            cfg, ref, interactive=interactive, agent_override=agent_override,
            record=record, template=name,
        )
    except RecurringError as exc:
        typer.echo(str(exc), err=True)
        return 2
    finally:
        if record.outcomes or record.scan_errors:
            run_autofix(cfg, record, agent_override=agent_override)
