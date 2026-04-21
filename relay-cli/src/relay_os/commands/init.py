"""relay init — scaffold a project's ``relay-os/`` directory.

Takes one argument: the project name (must match a ``[projects.<name>]``
entry in ``relay.toml``). Inside the path declared for that project in
``relay.local.toml`` ``[paths]``, creates:

- ``relay-os/``
- ``relay-os/context.md`` (empty project base context)
- ``relay-os/counter`` (initialized to ``1``)
- ``relay-os/tasks/``

Idempotent: existing files and directories are left alone. Running twice
is safe.

Bootstrapping a fresh Relay repo itself (creating ``relay.toml`` and the
knowledge-tree directories) is out of scope for this command. Users
clone the Relay repo, fill in ``relay.toml`` / ``relay.local.toml``, and
then run ``relay init <project>`` for each project they're working on.
"""

from __future__ import annotations

from pathlib import Path

import click

from ..config import ConfigError, RelayConfig


@click.command()
@click.argument("project")
def init(project: str) -> None:
    """Scaffold PROJECT's relay-os/ directory."""
    try:
        cfg = RelayConfig.load()
    except ConfigError as e:
        raise click.ClickException(str(e))

    if cfg.project(project) is None:
        valid = sorted(cfg.shared.projects.keys())
        raise click.ClickException(
            f"no project named {project!r} in relay.toml. "
            f"Valid projects: {valid}"
        )

    project_path = cfg.project_path(project)
    if project_path is None:
        raise click.ClickException(
            f"project {project!r} has no path in relay.local.toml [paths]. "
            f'Add an entry like: {project} = "./projects/{project}"'
        )

    project_path.mkdir(parents=True, exist_ok=True)
    relay_dir = project_path / "relay-os"

    created: list[str] = []
    skipped: list[str] = []

    _mkdir_if_missing(relay_dir, project_path, created, skipped)
    _mkdir_if_missing(relay_dir / "tasks", project_path, created, skipped)

    context = relay_dir / "context.md"
    if context.exists():
        skipped.append(str(context.relative_to(project_path)))
    else:
        context.write_text(_project_context_stub(project))
        created.append(str(context.relative_to(project_path)))

    counter = relay_dir / "counter"
    if counter.exists():
        skipped.append(str(counter.relative_to(project_path)))
    else:
        counter.write_text("1\n")
        created.append(str(counter.relative_to(project_path)))

    _print_summary(project_path, created, skipped)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------


def _mkdir_if_missing(
    path: Path, base: Path, created: list[str], skipped: list[str]
) -> None:
    rel = f"{path.relative_to(base)}/"
    if path.exists():
        skipped.append(rel)
    else:
        path.mkdir(parents=True, exist_ok=True)
        created.append(rel)


def _project_context_stub(name: str) -> str:
    return (
        f"# {name}\n"
        "\n"
        "Project-level context. Every task in this project inherits this as\n"
        "its first context block. Add what's always true about this project:\n"
        "what it is, how it's deployed, who owns what, gotchas.\n"
    )


def _print_summary(base: Path, created: list[str], skipped: list[str]) -> None:
    click.echo(f"Initialized Relay at {base}")
    for item in created:
        click.echo(f"  created:  {item}")
    for item in skipped:
        click.echo(f"  skipped:  {item} (exists)")
    if not created:
        click.echo("  (nothing to do — already initialized)")
