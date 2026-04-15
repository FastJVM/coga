"""Relay CLI entry point.

Wires every subcommand into a single `click` group. The `main` function
is the console_script registered in pyproject.toml — `pip install -e .`
makes `relay` available on PATH.

Subcommand implementations live in relay_os.commands.*. Each command is
a thin `@click.command()` wrapper that delegates to helpers in this
package (config, frontmatter, composer, slack, etc.). Those helpers are
stubbed in this ticket and filled in by subsequent tickets.
"""

from __future__ import annotations

import click

from . import __version__
from .commands import (
    create as create_cmd,
    feed as feed_cmd,
    init as init_cmd,
    launch as launch_cmd,
    panic as panic_cmd,
    status as status_cmd,
    step as step_cmd,
)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Relay — a blackboard for humans and agents.",
)
@click.version_option(__version__, "-v", "--version")
def main() -> None:
    """Entry point for the `relay` console script."""


# Foreground commands (humans call these daily).
main.add_command(init_cmd.init)
main.add_command(create_cmd.create)
main.add_command(launch_cmd.launch)
main.add_command(status_cmd.status)

# Background commands (agents call these; humans can too).
main.add_command(step_cmd.step)
main.add_command(panic_cmd.panic)
main.add_command(feed_cmd.feed)


if __name__ == "__main__":
    main()
