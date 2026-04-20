"""relay init — scaffold a new Relay repo or project.

Two modes:

* ``relay init`` — in the current directory, drop the shared knowledge
  tree (``skills/``, ``contexts/``, ``workflows/``, ``recurring/``,
  ``scripts/``), the config files, ``rules.md``, and the three protocol
  files. This is the second thing a user runs after installing the CLI.

* ``relay init --project <name>`` — inside a Relay repo, scaffold the
  per-project ``relay-os/`` directory (``context.md``, ``counter``,
  ``tasks/``) at the path declared for ``<name>`` in
  ``relay.local.toml``.

Both modes are idempotent: existing files are left alone.
"""

from __future__ import annotations

from importlib.resources import files as resource_files
from pathlib import Path

import click

from ..config import ConfigError, RelayConfig


REPO_DIRS = ("skills", "contexts", "workflows", "recurring", "scripts")

REPO_TEMPLATES = (
    ("relay.toml", "relay.toml"),
    ("relay.local.toml", "relay.local.toml"),
    ("rules.md", "rules.md"),
    ("protocol.md", "protocol.md"),
    ("protocol-interactive.md", "protocol-interactive.md"),
    ("protocol-auto.md", "protocol-auto.md"),
)


@click.command()
@click.option(
    "--project",
    help="Initialize a project directory (creates relay-os/ inside). "
    "Omit to initialize the current directory as a Relay repo.",
)
def init(project: str | None) -> None:
    """Initialize a new Relay repo or project."""
    if project is None:
        _init_repo(Path.cwd())
    else:
        _init_project(project)


def _init_repo(target: Path) -> None:
    created: list[str] = []
    skipped: list[str] = []

    for d in REPO_DIRS:
        _mkdir_if_missing(target / d, target, created, skipped)

    for filename, template_name in REPO_TEMPLATES:
        _write_template_if_missing(
            target / filename, template_name, target, created, skipped
        )

    cron = target / "scripts" / "cron.sh"
    if cron.exists():
        skipped.append(str(cron.relative_to(target)))
    else:
        cron.parent.mkdir(parents=True, exist_ok=True)
        cron.write_text(_read_template("cron.sh"))
        cron.chmod(0o755)
        created.append(str(cron.relative_to(target)))

    _ensure_gitignore_entry(target, "relay.local.toml", created, skipped)

    _print_summary(target, created, skipped)


def _init_project(name: str) -> None:
    try:
        cfg = RelayConfig.load()
    except ConfigError as e:
        raise click.ClickException(str(e))

    if cfg.project(name) is None:
        valid = sorted(cfg.shared.projects.keys())
        raise click.ClickException(
            f"no project named {name!r} in relay.toml. Valid projects: {valid}"
        )

    project_path = cfg.project_path(name)
    if project_path is None:
        raise click.ClickException(
            f"project {name!r} has no path in relay.local.toml [paths]. "
            f'Add an entry like: {name} = "./projects/{name}"'
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
        context.write_text(_project_context_stub(name))
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


def _read_template(name: str) -> str:
    return resource_files("relay_os.templates").joinpath(name).read_text()


def _write_template_if_missing(
    dest: Path,
    template_name: str,
    base: Path,
    created: list[str],
    skipped: list[str],
) -> None:
    rel = str(dest.relative_to(base))
    if dest.exists():
        skipped.append(rel)
    else:
        dest.write_text(_read_template(template_name))
        created.append(rel)


def _mkdir_if_missing(
    path: Path, base: Path, created: list[str], skipped: list[str]
) -> None:
    rel = f"{path.relative_to(base)}/"
    if path.exists():
        skipped.append(rel)
    else:
        path.mkdir(parents=True, exist_ok=True)
        created.append(rel)


def _ensure_gitignore_entry(
    target: Path, entry: str, created: list[str], skipped: list[str]
) -> None:
    gi = target / ".gitignore"
    if gi.exists():
        lines = gi.read_text().splitlines()
        if entry in lines:
            skipped.append(".gitignore")
            return
        with gi.open("a") as f:
            if lines and lines[-1] != "":
                f.write("\n")
            f.write(f"{entry}\n")
        created.append(".gitignore (entry added)")
    else:
        gi.write_text(f"{entry}\n")
        created.append(".gitignore")


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
