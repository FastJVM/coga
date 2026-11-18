"""Show report policy, owned by this command ticket."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.rule import Rule

from coga.config import Config, ConfigError, load_config
from coga.logfile import task_log_lines
from coga.tasks import BootstrapRef, TaskNotFoundError, read_ticket, resolve_target
from coga.ticket import TicketError
from coga.views import operator_cell


def render_show(cfg: Config, task: str, console: Console | None = None) -> None:
    """Print a task's contents — its single-file ticket (frontmatter + body +
    blackboard) and, for a real task, its history reconstructed from the
    repo-global log.

    Raises `TaskNotFoundError` when the target cannot be resolved; the caller
    translates that to `sys.exit(2)`.
    """
    ref = resolve_target(cfg, task)

    if console is None:
        console = Console()

    # The single-file ticket.md carries frontmatter + body + blackboard.
    console.print(Rule(f"{ref.id_slug}/ticket.md"))
    console.print()
    ticket_path = ref.ticket_path
    if not ticket_path.is_file():
        console.print("[dim](no ticket.md)[/dim]")
    else:
        from rich.markdown import Markdown

        text = ticket_path.read_text(encoding="utf-8")
        console.print(Markdown(text) if text.strip() else "[dim](empty)[/dim]")

    # Bootstrap tickets are stateless: no log history to reconstruct.
    if isinstance(ref, BootstrapRef):
        return

    # The operator is derived, not stored, so the rendered ticket above cannot
    # show it. Print it explicitly — and label it — so `coga show` still answers
    # "whose turn is this?" without anyone looking for a field that no longer
    # exists.
    try:
        shown_ticket = read_ticket(ref)
    except TicketError:
        pass
    else:
        console.print()
        console.print(
            f"operator: {operator_cell(cfg, ref, shown_ticket)} "
            "[dim](derived from the current workflow step — not stored)[/dim]"
        )

    console.print()
    console.print(Rule(f"{ref.id_slug} — log (from coga/log.md)"))
    console.print()
    lines = task_log_lines(cfg, ref.id_slug)
    if not lines:
        console.print("[dim](no log entries)[/dim]")
    else:
        for line in lines:
            console.print(line)


app = typer.Typer(add_completion=False)


@app.command()
def show(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>`."),
) -> None:
    """Print a task's contents — its single-file ticket (frontmatter + body +
    blackboard) and, for a real task, its history reconstructed from the
    repo-global log."""
    try:
        cfg = load_config(require_user=False)
    except ConfigError as exc:
        _bail(str(exc))

    try:
        render_show(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)


if __name__ == "__main__":
    app(prog_name="coga show")
