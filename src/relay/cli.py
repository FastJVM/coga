"""Relay CLI entry point."""

from __future__ import annotations

import typer

from relay.commands import create as create_cmd
from relay.commands import feed as feed_cmd
from relay.commands import launch as launch_cmd
from relay.commands import panic as panic_cmd
from relay.commands import status as status_cmd
from relay.commands import step as step_cmd

app = typer.Typer(
    name="relay",
    help="A blackboard for humans and agents.",
    no_args_is_help=True,
    add_completion=False,
)

app.command("create")(create_cmd.create)
app.command("launch")(launch_cmd.launch)
app.command("status")(status_cmd.status)
app.command("step")(step_cmd.step)
app.command("panic")(panic_cmd.panic)
app.command("feed")(feed_cmd.feed)


if __name__ == "__main__":
    app()
