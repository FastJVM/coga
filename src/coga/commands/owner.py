"""`coga owner <slug> <name>` — reassign a ticket's human of record.

`owner:` is the one ticket-to-person relationship the model carries: the
`owner` step role resolves to it, megalaunch and the dependency drain select
on it, and Slack mentions derive from it. It is not agent-editable, and a
hand edit skips validation, the audit line, and the guarded control sync —
which is how a ticket ends up with `owner:` naming someone who handed it off
months ago. This command is the one writer, shaped like a `coga.mark`
transition: prospective validation, locked write, audit line, exact-byte guarded sync.
No Slack post — like `mark paused`, a reassignment is routine local noise.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from coga import git
from coga.config import ConfigError, load_config
from coga.lifecycle import TERMINAL_STATUSES
from coga.logfile import append_log, retract_log_lines
from coga.paths import log_path
from coga.repl_supervisor import EXPECTED_TASK_ENV
from coga.tasks import TaskNotFoundError, resolve_task
from coga.ticket import Ticket
from coga.validate import TaskValidationError, assert_task_valid


def owner(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    name: str = typer.Argument(..., help="Coga name of the new owner."),
    assist_stopped: bool = typer.Option(
        False, "--assist-stopped",
        help="Confirm any assisting agent has stopped before reassigning an owner gate.",
    ),
) -> None:
    """Set `owner:` to NAME. Preserve status and step; an in-progress owner gate
    requires --assist-stopped. Terminal records cannot be reassigned."""
    name = name.strip()
    if not name:
        _bail("owner name cannot be empty")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    with git.state_lock(cfg):
        source = ref.ticket_path.read_bytes()
        ticket = Ticket.parse(source.decode("utf-8"))
        previous = ticket.owner
        if ticket.status in TERMINAL_STATUSES:
            _bail(
                f"Task {ref.id_slug} is {ticket.status!r}; a finished record keeps "
                "the owner it finished under."
            )
        expected_task = os.environ.get(EXPECTED_TASK_ENV)
        # The supervisor witnesses an absolute task path. The task metadata
        # also carries its path-qualified slug across feature-checkout changes;
        # use that only to refuse, never to authorize a mutation.
        own_session = (
            expected_task is not None
            and Path(expected_task).resolve() == ref.path.resolve()
        ) or os.environ.get("COGA_TASK_SLUG") == ref.id_slug
        if os.environ.get("COGA_SUPERVISED") and own_session:
            _bail(f"Stop this ticket's supervised session before reassigning {ref.id_slug}.")
        if ticket.launch_generation:
            _bail(f"Task {ref.id_slug} has an outstanding launch claim; stop the "
                  "session and recover the claim before reassignment.")
        if ticket.status == "in_progress":
            step = ticket.current_step()
            if step is None or step.get("assignee") != "owner":
                _bail(f"Task {ref.id_slug} is 'in_progress' on an agent step; "
                      f"stop the agent and run `coga mark paused {ref.id_slug}` first.")
            if not assist_stopped:
                _bail("An in-progress owner gate requires --assist-stopped: "
                      "stop any assisting agent first, then confirm from outside "
                      "its session. The ticket will remain in_progress.")
        if previous == name:
            _bail(f"Task {ref.id_slug} is already owned by {name!r}.")

        # Validate the prospective ticket before writing, so a refused
        # reassignment leaves nothing on disk to reconcile (the idiom
        # `coga/lifecycle` prescribes for every lifecycle writer).
        prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
        prospective.frontmatter["owner"] = name
        try:
            assert_task_valid(cfg, ref, action="owner", ticket_override=prospective)
        except TaskValidationError as exc:
            _bail(str(exc))

        # The lock serializes cooperating writers; compare bytes as well so an
        # edit made while prospective validation ran is never overwritten.
        if ref.ticket_path.read_bytes() != source:
            _bail("Ticket changed during owner validation; retry from current state.",
                  exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE)
        audit_path = log_path(cfg)
        audit_before = audit_path.read_bytes() if audit_path.exists() else b""
        written = git.write_ticket(cfg, prospective, ref.ticket_path)
        append_log(cfg, ref.id_slug, f"human:{cfg.current_user}",
                   f"owner {previous!r} → {name!r}")
        try:
            git.sync_task_state(
                cfg, ref.path,
                message=f"Ticket: {ref.id_slug} — owner {name}",
                expect={ref.ticket_path: source},
                strict=True,
            )
        except git.UncertainPublishError as exc:
            _bail(f"Owner publication is uncertain; reconcile with control before "
                  f"retrying: {exc}", exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE)
        except git.GitError as exc:
            # Undo only our bytes. A concurrent editor's newer ticket survives.
            if ref.ticket_path.read_bytes() == written:
                ref.ticket_path.write_bytes(source)
            retract_log_lines(cfg, ref.id_slug, audit_before)
            _bail(f"Owner publication failed; refresh from control before retrying: "
                  f"{exc}", exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE)
        typer.echo(f"{ref.id_slug}: owner {previous} → {name}")


def _bail(msg: str, *, exit_code: int = 2) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(exit_code)
