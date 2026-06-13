"""`relay setup` — one-command onboarding: init, name, interview.

Drives the bootstrap end to end, in order: scaffold the repo (`relay init`)
when there is no relay repo yet, collect the operator's name for the `user`
field in `relay.local.toml`, then launch the `relay-setup` interview ticket.
Each stage is skipped when already satisfied, so re-running `relay setup`
resumes wherever the bootstrap last stopped — including after a failed
launch (e.g. the Slack webhook wasn't configured yet).
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
from relay.config import ConfigError, find_repo_root


def setup(
    path: Path | None = typer.Argument(
        None,
        help="Directory to set up (default: current directory).",
    ),
) -> None:
    """Set up a relay repo end to end: `relay init` if needed, record your name, then launch the relay-setup interview."""
    target = (path or Path(".")).resolve()

    try:
        root = find_repo_root(target)
    except ConfigError:
        init_cmd._do_init(target, via_setup=True)
        root = target / "relay-os"

    _ensure_user(root / "relay.local.toml")

    ticket_path = root / "tasks" / "relay-setup" / "ticket.md"
    if not ticket_path.is_file():
        typer.echo(
            "No relay-setup ticket in this repo — it was either finished and "
            "retired, or the repo predates `relay setup`. Nothing left to do."
        )
        return
    if _ticket_status(ticket_path) == "done":
        typer.echo("relay-setup is already done — this repo is set up.")
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


def _ticket_status(ticket_path: Path) -> str:
    match = re.search(r"^status:\s*(\S+)", ticket_path.read_text(), flags=re.M)
    return match.group(1) if match else ""
