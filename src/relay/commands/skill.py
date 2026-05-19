"""`relay skill` — manage project-local Relay skills under relay-os/skills."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from relay.config import ConfigError, load_config
from relay.skill_manager import (
    SkillManagerError,
    install_github_skill,
    install_local_skill,
    install_url_skill,
    remove_skill,
    render_update_pr_body,
    resolve_installed_skill_dir,
    run_skill_update_pr_flow,
    status_skills,
    update_skills,
)


app = typer.Typer(
    help="Install, update, remove, and inspect Relay-managed skills.",
    no_args_is_help=True,
)


@app.command("install")
def install(
    source: str = typer.Argument(..., help="GitHub owner/repo or GitHub URL."),
    skill: str | None = typer.Argument(None, help="Optional skill name/path in the repo."),
) -> None:
    """Install a GitHub-backed skill through `gh skill`."""
    cfg = _load_config_or_exit()
    try:
        result = install_github_skill(cfg, source, skill)
    except SkillManagerError as exc:
        _bail(str(exc))
    typer.echo(result.message)


@app.command("install-local")
def install_local(
    path: Path = typer.Argument(..., help="Local skill directory or bundle path."),
    skill: str | None = typer.Argument(None, help="Optional skill name/path."),
) -> None:
    """Install an already-downloaded local skill through `gh skill --from-local`."""
    cfg = _load_config_or_exit()
    try:
        result = install_local_skill(cfg, path, skill)
    except SkillManagerError as exc:
        _bail(str(exc))
    typer.echo(result.message)


@app.command("install-url")
def install_url(
    url: str = typer.Argument(..., help="URL to a skill archive or SKILL.md file."),
    skill_or_path: str | None = typer.Argument(
        None,
        help="Path to the skill directory inside the archive when the URL has more than one.",
    ),
) -> None:
    """Download a non-GitHub URL, install locally, and preserve Relay metadata."""
    cfg = _load_config_or_exit()
    try:
        result = install_url_skill(cfg, url, skill_or_path)
    except SkillManagerError as exc:
        _bail(str(exc))
    typer.echo(result.message)


@app.command("update")
def update(
    skill: str | None = typer.Argument(None, help="Exact installed skill name/path."),
    all_skills: bool = typer.Option(
        False,
        "--all",
        help="Update all Relay-managed skills.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON summary.",
    ),
    pr: bool = typer.Option(
        False,
        "--pr",
        help="Open or update one draft PR with the skill-update summary.",
    ),
    pr_title: str = typer.Option(
        "Update Relay-managed skills",
        "--pr-title",
        help="Title for the skill-update PR.",
    ),
    verify: list[str] | None = typer.Option(
        None,
        "--verify",
        help="Verification command to run before creating/updating the PR. Repeatable.",
    ),
) -> None:
    """Update one skill or every managed skill."""
    cfg = _load_config_or_exit()
    try:
        summary = update_skills(cfg, skill, all_skills=all_skills)
        if pr:
            if not all_skills:
                raise SkillManagerError("--pr is only supported with `relay skill update --all`.")
            commands = verify or ["relay validate --json"]
            summary = run_skill_update_pr_flow(
                cfg,
                summary,
                title=pr_title,
                verification_commands=commands,
            )
    except SkillManagerError as exc:
        _bail(str(exc))

    if json_output:
        json.dump(summary.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        typer.echo(render_update_pr_body(summary))


@app.command("remove")
def remove(
    skill: str = typer.Argument(..., help="Exact installed skill name/path."),
) -> None:
    """Remove one exact installed skill path, leaving a git-visible delete."""
    cfg = _load_config_or_exit()
    try:
        target = resolve_installed_skill_dir(cfg, skill)
        typer.echo(f"Removing {target}")
        remove_skill(cfg, skill)
    except SkillManagerError as exc:
        _bail(str(exc))
    typer.echo(f"Removed {skill}")


@app.command("status")
def status(
    check: bool = typer.Option(
        False,
        "--check",
        help="Fetch URL-backed sources to check update availability.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON status.",
    ),
) -> None:
    """Summarize installed skills and their recorded source metadata."""
    cfg = _load_config_or_exit()
    try:
        results = status_skills(cfg, check=check)
    except SkillManagerError as exc:
        _bail(str(exc))

    if json_output:
        json.dump([result.__dict__ for result in results], sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    if not results:
        typer.echo("No installed skills found.")
        return
    for result in results:
        typer.echo(
            f"{result.name}: {result.status} ({result.source_type}) - {result.message}"
        )


def _load_config_or_exit():
    try:
        return load_config()
    except ConfigError as exc:
        _bail(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(2)
