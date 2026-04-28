"""Relay CLI entry point."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

import typer

from relay.commands import create as create_cmd
from relay.commands import feed as feed_cmd
from relay.commands import init as init_cmd
from relay.commands import launch as launch_cmd
from relay.commands import panic as panic_cmd
from relay.commands import recurring as recurring_cmd
from relay.commands import status as status_cmd
from relay.commands import bump as bump_cmd
from relay.commands.update import read_pin
from relay.config import ConfigError, find_repo_root


def _print_version_and_exit(value: bool) -> None:
    if not value:
        return
    try:
        pkg = _pkg_version("relay-os")
    except PackageNotFoundError:
        pkg = "unknown"
    typer.echo(f"relay {pkg}")
    try:
        relay_os = find_repo_root()
    except ConfigError:
        relay_os = None
    pin = read_pin(relay_os) if relay_os else None
    if pin is not None:
        typer.echo(f"vendored from upstream {pin[:12]} (full: {pin})")
    raise typer.Exit()


app = typer.Typer(
    name="relay",
    help="A blackboard for humans and agents.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_print_version_and_exit,
        is_eager=True,
        help="Print the relay package version and pinned upstream SHA.",
    ),
) -> None:
    """A blackboard for humans and agents."""


app.command("init")(init_cmd.init)
app.command("create")(create_cmd.create)
app.command("launch")(launch_cmd.launch)
app.command("status")(status_cmd.status)
app.command("bump")(bump_cmd.bump)
app.command("panic")(panic_cmd.panic)
app.command("feed")(feed_cmd.feed)
app.add_typer(recurring_cmd.app, name="recurring")


if __name__ == "__main__":
    app()
