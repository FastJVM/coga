"""`relay worktree <create|remove|list>` — manage per-task feature worktrees.

A dev task's code work happens in a dedicated git worktree at
`<git-toplevel>/worktree/<slug>` on its own branch, kept out of the
control-plane checkout so concurrent tasks never collide on one working tree.
See the `dev/code` context for the convention.
"""

from __future__ import annotations

from pathlib import Path

import typer

from relay import git
from relay.git import GitError

app = typer.Typer(
    name="worktree",
    help="Manage per-task feature worktrees (<git-toplevel>/worktree/<slug>).",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("create")
def create(
    slug: str = typer.Argument(
        ..., help="Task slug; the worktree lands at <toplevel>/worktree/<slug>."
    ),
    base: str = typer.Option(
        "HEAD", "--base", help="Start-point for the new branch (default: HEAD)."
    ),
    branch: str | None = typer.Option(
        None, "--branch", help="Branch name to create (default: the slug)."
    ),
) -> None:
    """Create the feature worktree + branch for SLUG."""
    try:
        path, br = git.create_worktree(Path.cwd(), slug, base=base, branch=branch)
    except GitError as exc:
        typer.echo(f"relay worktree: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo(f"worktree: {path}")
    typer.echo(f"branch: {br}")


@app.command("remove")
def remove(
    slug: str = typer.Argument(..., help="Task slug whose worktree to remove."),
) -> None:
    """Remove SLUG's feature worktree — refuses if it has uncommitted work."""
    try:
        removed = git.remove_worktree(Path.cwd(), slug)
    except GitError as exc:
        typer.echo(
            f"relay worktree: refusing to remove — {exc}\n"
            "The worktree has uncommitted or untracked work. Commit, stash, or "
            "remove it by hand; relay never passes `--force`.",
            err=True,
        )
        raise typer.Exit(1)
    typer.echo(
        f"removed worktree for {slug}"
        if removed
        else f"no worktree for {slug} — nothing to remove"
    )


@app.command("list")
def list_() -> None:
    """List the repo's git worktrees."""
    try:
        typer.echo(git.list_worktrees_text(Path.cwd()), nl=False)
    except GitError as exc:
        typer.echo(f"relay worktree: {exc}", err=True)
        raise typer.Exit(1)
