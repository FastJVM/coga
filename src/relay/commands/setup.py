"""`relay setup` — one-command onboarding, then plan your first project.

Drives the bootstrap end to end, in order: create `relay-os/` via `relay init`
when there is no relay repo yet, collect the operator's name for the `user`
field in `relay.local.toml`, then run the `relay-setup` interview ticket. Each
onboarding stage is skipped when already satisfied, so re-running `relay setup`
resumes wherever the bootstrap last stopped — including after a failed launch
(e.g. the Slack webhook wasn't configured yet).

Once onboarding finishes, `relay setup` immediately offers to plan a project —
interviewing the human and creating an ordered set of draft tickets via the
shared `plan_project` helper, all in the same run. There is no separate
`relay project` command; re-running `relay setup` on a set-up repo skips
straight to that same offer.
"""

from __future__ import annotations

import os
import re
import sys
import tomllib
from pathlib import Path

import typer

from relay.commands import init as init_cmd
from relay.commands import launch as launch_cmd
from relay.commands.project import plan_project
from relay.config import ConfigError, find_repo_root, load_config


def setup(
    path: Path | None = typer.Argument(
        None,
        help="Directory to set up (default: current directory).",
    ),
) -> None:
    """Set up a relay repo end to end, then plan your first project.

    `relay init` if needed, record your name, run the relay-setup interview,
    then offer to plan a project — all in one run. There is no separate
    `relay project` command; re-running `relay setup` skips straight to the
    project offer.
    """
    target = (path or Path(".")).resolve()

    try:
        root = find_repo_root(target)
    except ConfigError:
        init_cmd._do_init(target, via_setup=True)
        root = target / "relay-os"

    _ensure_user(root / "relay.local.toml")

    # The repo is set up once the interview ticket reaches `done` — or is gone
    # entirely (finished and retired, or a repo predating `relay setup`). Either
    # way, `relay setup` becomes the project-planning entry.
    ticket_path = root / "tasks" / "relay-setup" / "ticket.md"
    onboarded = (not ticket_path.is_file()) or _ticket_status(ticket_path) == "done"
    if onboarded:
        os.chdir(root)
        typer.echo("")
        typer.secho("✓ This repo is already set up.", fg=typer.colors.GREEN)
        _offer_project_planning(root)
        return

    # `relay launch` resolves the repo and config from the cwd.
    os.chdir(root)
    launch_cmd.launch(
        task="relay-setup",
        agent_override=None,
        prompt_report=False,
        no_verify=False,
        mode_override=None,
        idle_timeout=None,
    )

    # The launch session has exited. If the setup workflow ran to completion
    # (its final step calls `relay mark done`) point the user at their first
    # real move; if they stopped partway, tell them how to resume. We re-read
    # status from disk because the agent just edited it; a missing ticket means
    # it was finished and cleaned up, so treat that as done too.
    finished = (not ticket_path.is_file()) or _ticket_status(ticket_path) == "done"
    if finished:
        typer.echo("")
        typer.secho(
            "✓ Setup complete — your relay-os is seeded.", fg=typer.colors.GREEN
        )
        _offer_project_planning(root)
    else:
        typer.echo("")
        typer.echo(
            "Setup isn't finished yet — re-run `relay setup` to resume the "
            "interview where you left off."
        )


def _offer_project_planning(root: Path) -> None:
    """Offer to plan a project, right after the repo is set up.

    This is the only entry to project planning — there is no separate
    `relay project` command — so the same offer runs at the end of a fresh
    `relay setup` and on any later run against an already-set-up repo. Confirm
    first so a returning user isn't dropped into an interactive session unasked;
    declining just prints how to start one later. Nothing is passed into the
    session: the repo's generated contexts ride in through normal prompt
    composition, and the interview itself gathers the goal (and any vision doc).
    """
    if not typer.confirm("Plan a project now?", default=False):
        _print_next_steps()
        return
    plan_project(load_config(root))


def _ensure_user(local_toml: Path) -> None:
    """Make sure `user` is set in relay.local.toml, prompting for it if not."""
    if not local_toml.is_file():
        local_toml.write_text(init_cmd.LOCAL_TOML_TEMPLATE)
    current = tomllib.loads(local_toml.read_text()).get("user")
    if current:
        typer.echo(f"user: {current} (from {local_toml})")
        return

    while True:
        name = typer.prompt(
            "Your name — it becomes `user` in relay.local.toml, the name "
            "tickets and agents refer to you by (e.g. marc)"
        ).strip()
        if name and '"' not in name and "\\" not in name:
            break
        typer.echo("Give a non-empty name without quotes or backslashes.")

    text = local_toml.read_text()
    new_text, replaced = re.subn(
        r"^user\s*=.*$", f'user = "{name}"', text, count=1, flags=re.M
    )
    if not replaced:
        new_text = f'user = "{name}"\n{text}'
    if tomllib.loads(new_text).get("user") != name:
        typer.secho(
            f"Failed to set `user` in {local_toml} — edit it by hand, then "
            "re-run `relay setup`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    local_toml.write_text(new_text)
    typer.echo(f'Set user = "{name}" in {local_toml}.')


def _print_next_steps() -> None:
    """Terminal nudge when the human declines the project offer.

    Project planning lives behind `relay setup` — run it whenever you're ready
    and accept the prompt; a single ticket is `relay create`. The setup
    workflow's final step echoes a similar sign-off in the agent session.
    """
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo(
        "  1. Plan a project anytime — run `relay setup` and accept the prompt; "
        "it runs a short interview and creates an ordered set of tickets."
    )
    typer.echo('  2. Or create a single ticket — `relay create "<title>"`.')
    typer.echo("  3. See everything anytime — `relay status`.")


def _ticket_status(ticket_path: Path) -> str:
    match = re.search(r"^status:\s*(\S+)", ticket_path.read_text(), flags=re.M)
    return match.group(1) if match else ""
