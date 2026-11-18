"""`coga recurring` — command heads for recurring scan, launch, and list."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from coga import git
from coga.config import ConfigError, load_config
from coga.paths import log_path
from coga.recurring import (
    RecurringError,
    promote_task,
)
from coga.recurring_runner import run_recurring_all_repos, run_recurring_named
from coga.runner import run_recipe
from coga.taskfile import TaskFileError
from coga.tasks import TaskNotFoundError, resolve_task
from coga.ticket import TicketError


app = typer.Typer(
    name="recurring",
    help="Scan recurring task templates and launch any that are due.",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Launch due agent tasks as a human-stepped run, leaving REPL "
        "liveness backstops unarmed. Ticket files are not modified.",
    ),
    all_root: Path | None = typer.Option(
        None,
        "--all",
        metavar="PATH",
        help="Discover every Coga repo below PATH and run each repo's due "
        "recurring sweep once, skipping `_`-prefixed trees and unconfigured "
        "repos. May be combined with --force.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force a real, full run of EVERY template: bypass the schedule "
        "and the already-serviced/done/paused status filter, then get-or-create "
        "and launch each template's real `recurring/<name>` task. Identical to a "
        "bare `coga recurring` (real Slack, git sync, "
        "serviced-period ledger advance) — just forced. A template that already "
        "ran this period is re-launched. A canceled period task is refused; "
        "delete it before starting a fresh run.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Agent type to use for agent-backed recurring tasks in this "
        "sweep. A template carrying `ticket.py` stays deterministic; ticket "
        "assignees are not rewritten.",
    ),
) -> None:
    """Run the registered recurring scanner recipe."""
    ctx.ensure_object(dict)["agent_override"] = agent
    if ctx.invoked_subcommand is not None:
        if all_root is not None or force:
            typer.secho(
                "--all and --force apply to recurring sweeps, not recurring "
                "subcommands.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)
        return

    if all_root is not None:
        code = run_recurring_all_repos(
            all_root,
            force=force,
            interactive=interactive,
            agent_override=agent,
        )
        if code:
            sys.exit(code)
        return

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    recipe_argv: list[str] = []
    if force:
        recipe_argv.append("--force")
    if interactive:
        recipe_argv.append("--interactive")
    if agent:
        recipe_argv.extend(("--agent", agent))
    code = run_recipe(cfg, "recurring-scan", recipe_argv)
    if code:
        raise typer.Exit(code)


@app.command("launch")
def launch(
    ctx: typer.Context,
    name: str = typer.Argument(
        ...,
        help="Recurring task name — the directory under coga/recurring/.",
    ),
    rerun: bool = typer.Option(
        False,
        "--rerun",
        help="Start a fresh run even if this period already finished. "
        "Human-paused and canceled runs stay parked.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Launch as a human-stepped run, leaving REPL liveness backstops "
        "unarmed. Ticket files are not modified.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Agent type to use for this agent-backed recurring launch. "
        "A template carrying `ticket.py` stays deterministic; the ticket "
        "assignee is not rewritten.",
    ),
) -> None:
    """Create a named recurring template now and launch it."""
    inherited_agent = (ctx.obj or {}).get("agent_override")
    if (
        agent is not None
        and inherited_agent is not None
        and agent != inherited_agent
    ):
        typer.secho(
            f"Conflicting recurring agent overrides: {inherited_agent!r} and "
            f"{agent!r}.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    agent_override = agent or inherited_agent

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    code = run_recurring_named(
        cfg, name, rerun=rerun, interactive=interactive, agent_override=agent_override
    )
    if code:
        sys.exit(code)


@app.command("promote")
def promote(
    ctx: typer.Context,
    task: str = typer.Argument(..., help="Task ID or id-slug to promote."),
    schedule: str = typer.Option(
        ...,
        "--schedule",
        help='5-field cron string the template fires on, e.g. "0 9 * * 1".',
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Recurring template directory name. Defaults to the task's slug.",
    ),
) -> None:
    """Move a task into `coga/recurring/<name>/` as a recurring template.

    The authoring path for "this ticket should run every period": the ticket
    body travels verbatim, task-only frontmatter is dropped, the validated
    `--schedule` is stamped on, and the blackboard is reset for cross-run
    state. Refuses rather than overwriting an existing template, and validates
    the cron before anything moves.
    """
    if (ctx.obj or {}).get("agent_override") is not None:
        typer.secho(
            "--agent is only supported when recurring launches work.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    source_path = ref.path
    try:
        outcome = promote_task(cfg, ref, schedule=schedule, name=name)
    except (RecurringError, TaskFileError, TicketError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    # One sync for the whole move: the task removal and the new template land
    # together, so no checkout ever sees the ticket in both places (or in
    # neither).
    try:
        git.publish(
            cfg,
            [source_path, outcome.path, log_path(cfg)],
            f"Recurring: promoted {outcome.source_slug} → recurring/{outcome.name}",
        )
    except git.GitError as exc:
        typer.secho(f"[git] sync failed: {exc}", fg=typer.colors.YELLOW, err=True)

    typer.echo(
        f"Promoted {outcome.source_slug} → recurring/{outcome.name} "
        f"({outcome.path}) on schedule {schedule!r}."
    )
    if outcome.dropped_skills:
        typer.secho(
            "Dropped ticket-level skills "
            f"{', '.join(outcome.dropped_skills)}: `skills:` is never copied "
            "into a period task. Put them on the template workflow's steps.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    if outcome.dropped_blackboard:
        typer.secho(
            "Dropped the task's blackboard: a template blackboard holds "
            "cross-run state, not one run's scratch. Recover it with `git show` "
            "if you need it.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    typer.echo("Run `coga validate --json` to check the new template.")


@app.command("list", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}, add_help_option=False)
def list_recurring(ctx: typer.Context) -> None:
    """List recurring templates and instantiated tasks."""
    from coga.launch import LaunchBail, launch as launch_target
    from coga.oscompat import process_exit_status

    if (ctx.obj or {}).get("agent_override") is not None:
        typer.secho(
            "--agent is only supported when recurring launches work.",
            fg=typer.colors.RED, err=True,
        )
        raise typer.Exit(2)
    policy_token = git.state_sweep_withheld.set(False)
    try:
        result = launch_target(
            "bootstrap/recurring-list", args=list(ctx.args), read_only=True,
        )
    except LaunchBail as exc:
        if exc.reason:
            typer.secho(exc.reason, fg=typer.colors.RED, err=True)
        raise typer.Exit(process_exit_status(exc.code)) from exc
    finally:
        # Read dispatch does not retain a failed writer transaction. Restore
        # the caller policy; recurring list already has no exit sweep.
        git.state_sweep_withheld.reset(policy_token)
    raise typer.Exit(process_exit_status(result.exit_code or 0))
