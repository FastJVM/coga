"""`coga project [seed]` — interview the human about a project, then create
an ordered set of draft tickets from the answers.

Thin launcher, mirroring `coga ticket`: it runs the `bootstrap/project` skill
in an interactive agent session. The four-question interview and the
review-before-create protocol live in the skill, not here, so they can't
drift from code. The agent creates the ordered drafts during the session via
`coga create` (each of which syncs itself); this command validates whatever
drafts the session produced and reports them before handing back.
"""

from __future__ import annotations

import os
import shutil
import sys

import typer

from coga.commands.launch import (
    _interactive_stdio_has_tty,
    spawn_agent_session,
)
from coga.compose import ComposeError
from coga.config import ConfigError, load_config
from coga.tasks import (
    TaskNotFoundError,
    list_tasks,
    read_ticket,
    resolve_bootstrap,
)
from coga.validate import format_task_issues, validate_task_dir


def project(
    seed: str | None = typer.Argument(
        None,
        help=(
            "Optional one-line project description, or a path/link to a vision "
            "doc to seed the interview. Omit to start from the first question."
        ),
    ),
    agent_override: str | None = typer.Option(
        None,
        "--agent",
        help="Agent nickname to run the planning interview.",
    ),
) -> None:
    """Interview about a project, then create an ordered set of draft tickets."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_bootstrap(cfg, "project")
    except TaskNotFoundError as exc:
        _bail(
            f"{exc}\nThe bootstrap/project ticket ships with the package — "
            "reinstall or update coga so the packaged launch target is present."
        )
    bootstrap_ticket = read_ticket(ref)

    launch_assignee = agent_override or bootstrap_ticket.assignee
    if not launch_assignee:
        _bail("No planning agent configured; pass --agent <nickname>.")

    if not _interactive_stdio_has_tty():
        _bail(
            "Cannot launch project planning: mode=interactive requires a TTY "
            "(stdin and stdout must both be terminals)."
        )

    try:
        agent = cfg.agent_type(launch_assignee)
    except ConfigError as exc:
        _bail(str(exc))

    if shutil.which(agent.cli) is None:
        _bail(f"Agent CLI {agent.cli!r} not found in PATH.")

    typer.echo(f"Project: planning with {launch_assignee} -> {agent.name}")
    before = {r.id_slug for r in list_tasks(cfg)}

    # Project planning routes through the same single-shot spawn as launch and
    # ticket authoring, but without the launch supervisor chain or Coga secret
    # injection: it plans work, it does not run task work.
    try:
        session = spawn_agent_session(
            cfg,
            ref,
            bootstrap_ticket,
            agent,
            "interactive",
            env=os.environ.copy(),
            actor=f"human:{cfg.current_user}",
            log_message=(
                "project planning launched "
                f"(assignee={launch_assignee}, agent={agent.name})"
            ),
            discussion=True,
            prompt_suffix=f"\n\n## Project seed\n\n{seed}\n" if seed else "",
            label="Project",
        )
    except ComposeError as exc:
        _bail(str(exc))
    except FileNotFoundError:
        _bail(f"Failed to spawn agent: {agent.cli!r} not found.")

    if session.exit_code != 0:
        typer.secho(
            f"Agent exited with code {session.exit_code}.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        sys.exit(session.exit_code)

    _report_new_drafts(cfg, before)


def _report_new_drafts(cfg, before: set[str]) -> None:
    """List the drafts the session created and fail loud on any schema break.

    Each `coga create` already synced itself during the session, so we don't
    re-sync here — we surface the new set and validate it while the human is
    still at the terminal and can fix breakage before launch.
    """
    new_refs = [r for r in list_tasks(cfg) if r.id_slug not in before]
    if not new_refs:
        typer.echo("Project: no draft tickets were created this session.")
        return

    typer.echo(f"Project: {len(new_refs)} draft ticket(s) created:")
    for ref in sorted(new_refs, key=lambda r: r.id_slug):
        typer.echo(f"  - {ref.id_slug}")

    errors_found = False
    for ref in new_refs:
        errors = [i for i in validate_task_dir(cfg, ref) if i.severity == "error"]
        if errors:
            errors_found = True
            typer.secho(
                f"Validation failed for {ref.id_slug}:\n"
                + format_task_issues(errors),
                fg=typer.colors.RED,
                err=True,
            )
    if errors_found:
        sys.exit(2)


def _bail(message: str) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=2)
