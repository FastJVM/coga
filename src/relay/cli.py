"""Relay CLI entry point."""

from __future__ import annotations

import shlex
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version

import typer

from relay.commands import automerge as automerge_cmd
from relay.commands import delete as delete_cmd
from relay.commands import init as init_cmd
from relay.commands import launch as launch_cmd
from relay.commands import panic as panic_cmd
from relay.commands import recurring as recurring_cmd
from relay.commands import show as show_cmd
from relay.commands import slack as slack_cmd
from relay.commands import status as status_cmd
from relay.commands import bump as bump_cmd
from relay.commands import validate as validate_cmd
from relay.commands.update import read_pin
from relay.config import ConfigError, find_repo_root, load_config


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
app.command("launch")(launch_cmd.launch)
app.command("status")(status_cmd.status)
app.command("show")(show_cmd.show)
app.command("bump")(bump_cmd.bump)
app.command("automerge")(automerge_cmd.automerge)
app.command("delete")(delete_cmd.delete)
app.command("panic")(panic_cmd.panic)
app.command("slack")(slack_cmd.slack)
app.command("validate")(validate_cmd.validate)
app.add_typer(recurring_cmd.app, name="recurring")


# Names of commands registered above. Used to validate that user-defined
# aliases don't collide with built-ins and that alias expansions target
# real commands.
_BUILTIN_COMMANDS = frozenset(
    {
        "init", "launch", "status", "show", "bump", "automerge",
        "delete", "panic", "slack", "recurring", "validate",
    }
)


def _validate_aliases(aliases: dict[str, str]) -> None:
    """Reject aliases that collide with built-ins or expand to unknown commands."""
    for name, expansion in aliases.items():
        if name in _BUILTIN_COMMANDS:
            raise ConfigError(
                f"alias {name!r} collides with built-in command — rename it."
            )
        tokens = shlex.split(expansion)
        if not tokens:
            raise ConfigError(f"alias {name!r} expands to empty command")
        target = tokens[0]
        if target not in _BUILTIN_COMMANDS:
            raise ConfigError(
                f"alias {name!r} expands to unknown command {target!r} "
                f"(known: {sorted(_BUILTIN_COMMANDS)})"
            )


def _register_alias_placeholder(name: str, expansion: str) -> None:
    """Register a no-op Typer command for `--help` discoverability.

    The actual dispatch happens via argv rewriting in `main()` before
    Typer ever sees the alias name; this placeholder exists so the alias
    appears in `relay --help` output.
    """

    @app.command(
        name,
        help=f"Alias → relay {expansion}",
        context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    )
    def _placeholder(  # pragma: no cover — never invoked; argv rewriting wins
        ctx: typer.Context,
    ) -> None:
        raise RuntimeError(
            f"alias {name!r} placeholder invoked — argv rewriting should have intercepted"
        )


def main() -> None:
    """Console-script entry point. Loads config, registers aliases, dispatches."""
    try:
        find_repo_root()
        cfg = load_config()
    except ConfigError as exc:
        msg = str(exc)
        if "No relay.toml found" in msg:
            cfg = None
        else:
            typer.secho(msg, fg=typer.colors.RED, err=True)
            sys.exit(2)

    aliases = cfg.aliases if cfg else {}
    if aliases:
        try:
            _validate_aliases(aliases)
        except ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            sys.exit(2)
        for name, expansion in aliases.items():
            _register_alias_placeholder(name, expansion)

    if len(sys.argv) > 1 and sys.argv[1] in aliases:
        name = sys.argv[1]
        expansion = aliases[name]
        expanded = shlex.split(expansion)
        rest = sys.argv[2:]
        full = expanded + rest
        typer.secho(f"→ relay {' '.join(full)}", fg=typer.colors.BLUE, err=True)
        sys.argv = [sys.argv[0]] + full

    app()


if __name__ == "__main__":
    main()
