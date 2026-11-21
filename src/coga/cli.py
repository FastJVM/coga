"""Coga CLI entry point."""

from __future__ import annotations

from coga.argv import command_help_requested

import importlib
import os
import shlex
import signal
import sys

import typer
from typer.core import TyperCommand, TyperGroup

from coga.aliases import (
    BUILTIN_COMMANDS as _BUILTIN_COMMANDS,
    DEFAULT_ALIASES as _DEFAULT_ALIASES,
    validate_aliases as _validate_aliases,
)
from coga.config import ConfigError, find_repo_root, load_config


def _print_version_and_exit(value: bool) -> None:
    if not value:
        return
    from importlib.metadata import PackageNotFoundError, version as _pkg_version

    try:
        pkg = _pkg_version("coga")
    except PackageNotFoundError:
        pkg = "unknown"
    typer.echo(f"coga {pkg}")
    raise typer.Exit()


# Built-in command → (module, attribute, extra `app.command` settings). A
# `typer.Typer` attribute is a command group. Modules import on first use so
# `coga <command>` loads only that command's dependencies; listing them all
# (top-level `--help`, an unknown command) imports everything.
#
# Help lists plain commands, then alias placeholders, then groups — the
# order eager Typer registration produced.
_GROUP_COMMANDS = ("skill", "mark", "recurring", "secret")
_LAZY_COMMANDS: dict[str, tuple[str, str, dict[str, object]]] = {
    "init": ("coga.commands.init", "init", {}),
    "uninstall": ("coga.commands.uninstall", "uninstall", {}),
    "create": ("coga.commands.create", "create", {}),
    "ticket": ("coga.commands.ticket", "ticket", {}),
    "launch": ("coga.commands.launch", "launch", {}),
    "bump": ("coga.commands.bump", "bump", {}),
    "block": ("coga.commands.block", "block", {}),
    "unblock": ("coga.commands.unblock", "unblock", {}),
    "owner": ("coga.commands.owner", "owner", {}),
    "delete": ("coga.commands.delete", "delete", {}),
    "validate": ("coga.commands.validate", "validate", {}),
    "skill": ("coga.commands.skill", "app", {}),
    "mark": ("coga.commands.mark", "app", {}),
    "recurring": ("coga.commands.recurring", "app", {}),
    "secret": ("coga.commands.secret", "app", {}),
    "run": (
        "coga.commands.run",
        "run",
        {
            "context_settings": {
                "ignore_unknown_options": True,
                "allow_extra_args": True,
            },
        },
    ),
}


def _load_command(name: str) -> TyperCommand | TyperGroup:
    module_name, attribute, settings = _LAZY_COMMANDS[name]
    target = getattr(importlib.import_module(module_name), attribute)
    if isinstance(target, typer.Typer):
        command: TyperCommand | TyperGroup = typer.main.get_group(target)
    else:
        holder = typer.Typer(add_completion=False)
        holder.command(name, **settings)(target)
        command = typer.main.get_command(holder)
    command.name = name
    return command


class _LazyGroup(TyperGroup):
    """Root group that builds built-in commands on demand; alias placeholders
    stay eagerly registered and list after the built-ins."""

    def list_commands(self, ctx: typer.Context) -> list[str]:
        commands = [n for n in _LAZY_COMMANDS if n not in _GROUP_COMMANDS]
        aliases = [n for n in self.commands if n not in _LAZY_COMMANDS]
        return [*commands, *aliases, *_GROUP_COMMANDS]

    def get_command(
        self, ctx: typer.Context, cmd_name: str
    ) -> TyperCommand | TyperGroup | None:
        if cmd_name not in self.commands and cmd_name in _LAZY_COMMANDS:
            self.commands[cmd_name] = _load_command(cmd_name)
        return self.commands.get(cmd_name)

    def resolve_command(
        self, ctx: typer.Context, args: list[str]
    ) -> tuple[str | None, TyperCommand | TyperGroup | None, list[str]]:
        if args and args[0] not in self.commands and args[0] not in _LAZY_COMMANDS:
            # Typer's "Did you mean" draws on loaded commands only.
            for name in _LAZY_COMMANDS:
                self.get_command(ctx, name)
        return super().resolve_command(ctx, args)


app = typer.Typer(
    name="coga",
    help="Organize agent work in markdown.",
    no_args_is_help=True,
    add_completion=False,
    cls=_LazyGroup,
)


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_print_version_and_exit,
        is_eager=True,
        help="Print the coga version.",
    ),
) -> None:
    """Organize agent work in markdown."""


def _read_only_launch_requested(argv: list[str]) -> bool:
    """Select dispatch effects before any target/config-dependent launch work.

    Alias expansion has already produced the same argv as a direct launch.
    Operands after the CLI separator cannot change invocation policy.
    """
    options = argv[2:argv.index("--") if "--" in argv else len(argv)]
    return argv[1:2] == ["launch"] and "--read-only" in options


def _needs_no_config(args: list[str]) -> bool:
    """Whether this invocation reads neither aliases nor config: `--version`,
    or `--help` under a built-in command (alias names cannot shadow one).
    Neither sweeps state. Top-level `--help` still loads config to list the
    repo's `[aliases]`."""
    if args[:1] == ["--version"]:
        return True
    return (
        bool(args)
        and args[0] in _BUILTIN_COMMANDS
        and command_help_requested(args)
    )


def _register_alias_placeholder(name: str, expansion: str) -> None:
    """Register a no-op Typer command for `--help` discoverability.

    The actual dispatch happens via argv rewriting in `main()` before
    Typer ever sees the alias name; this placeholder exists so the alias
    appears in `coga --help` output.
    """

    @app.command(
        name,
        help=f"Alias → coga {expansion}",
        context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    )
    def _placeholder(  # pragma: no cover — never invoked; argv rewriting wins
        ctx: typer.Context,
    ) -> None:
        raise RuntimeError(
            f"alias {name!r} placeholder invoked — argv rewriting should have intercepted"
        )


def _restore_default_sigpipe() -> None:
    """Behave like a standard Unix filter when output is piped to a consumer
    that closes early (`coga status | head`, `coga skill update --json | jq`).

    Python sets SIGPIPE to SIG_IGN and turns a write to a closed pipe into a
    `BrokenPipeError`; when that surfaces during the interpreter's
    shutdown-time stdout flush, CPython exits 120 with a noisy
    "Exception ignored" traceback instead of dying quietly. Restoring the
    default disposition makes the process terminate on SIGPIPE the way `cat`
    and `grep` do. It also fixes the well-known SIG_IGN-inheritance footgun for
    the many `git`/`gh` subprocesses coga spawns. Guarded for platforms
    without SIGPIPE (Windows).
    """
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def main(*, existing_target_only: bool = False) -> None:
    """Console-script entry point. Loads config, registers aliases, dispatches."""
    if os.name == "nt":
        # Windows console I/O already supports Unicode, but pipes otherwise
        # inherit the ANSI code page (often cp1252), even for `coga --help`.
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
    _restore_default_sigpipe()
    invoked_command = sys.argv[1] if len(sys.argv) > 1 else None
    recurring_all_invoked = (
        invoked_command == "recurring" and "--all" in sys.argv[2:]
    )
    # `coga init` (fresh or `--update`) is the create/recovery command — it
    # must run even when the current config is missing, legacy, or broken,
    # since repairing exactly that is often why it's invoked. A stale CLI plus
    # a migrated `coga.toml` would otherwise deadlock: the update that fixes
    # the CLI can't run because the stale CLI rejects the new config first.
    # `uninstall` shares this leniency: a broken/legacy config is itself a
    # reason to remove Coga, so it must not be blocked by config load failure.
    init_invoked = invoked_command in ("init", "uninstall")
    if _needs_no_config(sys.argv[1:]):
        app()
        return
    # Eager alias discovery tolerates a missing `user`
    # (a teammate's fresh clone has no gitignored `coga.local.toml` yet).
    # Otherwise `coga`, `coga --help`, and every `<command> --help` would die
    # before Typer even parses them. Commands that act as someone still load
    # strictly in their own bodies and fail there with the actionable message.
    try:
        find_repo_root()
        cfg = load_config(require_user=False)
    except ConfigError as exc:
        msg = str(exc)
        if "No coga.toml found" in msg:
            help_invoked = command_help_requested(sys.argv[1:])
            known_command = (
                invoked_command in _BUILTIN_COMMANDS
                or invoked_command in _DEFAULT_ALIASES
            )
            if (
                known_command
                and not init_invoked
                and not recurring_all_invoked
                and not help_invoked
            ):
                typer.secho(
                    f"{msg}\nTo adopt an existing project, go to the project's "
                    "git root and run `coga init --user NAME`.",
                    fg=typer.colors.RED,
                    err=True,
                )
                sys.exit(2)
            cfg = None
        elif command_help_requested(sys.argv[1:]):
            cfg = None
        elif init_invoked or recurring_all_invoked:
            prefix = (
                f"Note: ignoring config error so `{sys.argv[1]}` can run"
                if init_invoked
                else "Note: ignoring current config error so the cross-repo "
                "recurring sweep can run"
            )
            typer.secho(
                f"{prefix} — {msg}",
                fg=typer.colors.YELLOW,
                err=True,
            )
            cfg = None
        else:
            typer.secho(msg, fg=typer.colors.RED, err=True)
            sys.exit(2)

    if invoked_command == "uninstall":
        if cfg and "uninstall" in cfg.aliases:
            print(
                "coga: ignoring legacy alias 'uninstall' from coga.toml "
                "('uninstall' is now a built-in command — remove the line "
                "under [aliases]).",
                file=sys.stderr,
            )
        app()
        return

    user_aliases = cfg.aliases if cfg else {}
    aliases = {**_DEFAULT_ALIASES, **user_aliases}
    try:
        _validate_aliases(aliases)
    except ConfigError as exc:
        if init_invoked or recurring_all_invoked:
            prefix = (
                f"Note: ignoring config error so `{sys.argv[1]}` can run"
                if init_invoked
                else "Note: ignoring current config error so the cross-repo "
                "recurring sweep can run"
            )
            typer.secho(
                f"{prefix} — {exc}",
                fg=typer.colors.YELLOW,
                err=True,
            )
            cfg = None
            aliases = dict(_DEFAULT_ALIASES)
        else:
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
        typer.secho(f"→ coga {' '.join(full)}", fg=typer.colors.BLUE, err=True)
        sys.argv = [sys.argv[0]] + full

    if _read_only_launch_requested(sys.argv):
        app()
        return

    from coga.repl_supervisor import deferred_done_marker

    with deferred_done_marker():
        adapter_tokens = []
        if existing_target_only:
            from coga import authoring

            adapter_tokens = [
                (authoring.existing_target_only,
                 authoring.existing_target_only.set(existing_target_only)),
            ]
        try:
            app()
        finally:
            for var, token in reversed(adapter_tokens):
                var.reset(token)


if __name__ == "__main__":
    main()
