"""Relay CLI entry point."""

from __future__ import annotations

import shlex
import signal
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version

import typer

from relay.commands import automerge as automerge_cmd
from relay.commands import create as create_cmd
from relay.commands import delete as delete_cmd
from relay.commands import digest as digest_cmd
from relay.commands import init as init_cmd
from relay.commands import launch as launch_cmd
from relay.commands import mark as mark_cmd
from relay.commands import panic as panic_cmd
from relay.commands import project as project_cmd
from relay.commands import recurring as recurring_cmd
from relay.commands import retire as retire_cmd
from relay.commands import secret as secret_cmd
from relay.commands import show as show_cmd
from relay.commands import slack as slack_cmd
from relay.commands import status as status_cmd
from relay.commands import skill as skill_cmd
from relay.commands import ticket as ticket_cmd
from relay.commands import bump as bump_cmd
from relay.commands import uninstall as uninstall_cmd
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
app.command("uninstall")(uninstall_cmd.uninstall)
app.command("create")(create_cmd.create)
app.command("draft")(create_cmd.draft)
app.command("ticket")(ticket_cmd.ticket)
app.command("project")(project_cmd.project)
app.command("launch")(launch_cmd.launch)
app.command("status")(status_cmd.status)
app.command("show")(show_cmd.show)
app.command("bump")(bump_cmd.bump)
app.command("automerge")(automerge_cmd.automerge)
app.command("delete")(delete_cmd.delete)
app.command("retire")(retire_cmd.retire)
app.command("panic")(panic_cmd.panic)
app.command("slack")(slack_cmd.slack)
app.command("digest")(digest_cmd.digest)
app.command("validate")(validate_cmd.validate)
app.add_typer(skill_cmd.app, name="skill")
app.add_typer(mark_cmd.app, name="mark")
app.add_typer(recurring_cmd.app, name="recurring")
app.add_typer(secret_cmd.app, name="secret")


# Names of commands registered above. Used to validate that user-defined
# aliases don't collide with built-ins and that alias expansions target
# real commands.
_BUILTIN_COMMANDS = frozenset(
    {
        "init", "uninstall", "create", "launch", "status", "show", "bump",
        "automerge", "delete", "draft", "retire", "panic", "slack", "digest",
        "skill", "mark", "recurring", "ticket", "project", "validate", "secret",
    }
)


# Aliases registered for every user, regardless of whether their `relay.toml`
# has an `[aliases]` section. Anything in the user's `[aliases]` overrides
# (same key wins). Keeps `relay chat` discoverable in `--help` — and actually
# dispatchable — for repos init'd before the alias defaults convention, or
# where the user dropped the section.
#
# `dream` is a default alias rather than a built-in command: a Dream run is an
# ordinary recurring task (`relay-os/recurring/dream/`), and `relay dream`
# just creates and launches it on demand — the same path `relay recurring
# launch dream` takes. Shipping it as a default keeps `relay dream` working in
# repos init'd before the recurring template landed.
#
# `build` is the first-run onboarding entry point: it just launches the
# packaged `relay-build` ticket (`relay launch relay-build`), the same path a
# manual launch takes. As an alias it dispatches through normal `relay launch`
# CLI parsing — so it requires an already-init'd repo and captures no name (both
# now `relay init`'s job) and never hits the in-code `launch()` sentinel pitfall.
_DEFAULT_ALIASES: dict[str, str] = {
    "chat": "launch bootstrap/orient",
    "dream": "recurring launch dream",
    "build": "launch relay-build",
}


_LEGACY_ALIASES: dict[str, str] = {
    "create": "launch bootstrap/ticket",
}


def _validate_aliases(aliases: dict[str, str]) -> None:
    """Reject aliases that collide with built-ins or expand to unknown commands.

    Exactly one shape is soft-skipped instead of crashing: legacy default
    aliases we shipped that later became built-ins (today: the
    `create = "launch bootstrap/ticket"` line every pre-split repo carries).
    We print a one-line stderr notice and drop the alias so the CLI keeps
    working before the user has had a chance to clean up their `relay.toml`.
    """
    for name in list(aliases):
        expansion = aliases[name]
        if _LEGACY_ALIASES.get(name) == expansion:
            print(
                f"relay: dropping legacy alias {name!r} from relay.toml "
                f"({name!r} is now a built-in command — remove the line "
                f"under [aliases]).",
                file=sys.stderr,
            )
            del aliases[name]
            continue
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


def _restore_default_sigpipe() -> None:
    """Behave like a standard Unix filter when output is piped to a consumer
    that closes early (`relay status | head`, `relay skill update --json | jq`).

    Python sets SIGPIPE to SIG_IGN and turns a write to a closed pipe into a
    `BrokenPipeError`; when that surfaces during the interpreter's
    shutdown-time stdout flush, CPython exits 120 with a noisy
    "Exception ignored" traceback instead of dying quietly. Restoring the
    default disposition makes the process terminate on SIGPIPE the way `cat`
    and `grep` do. It also fixes the well-known SIG_IGN-inheritance footgun for
    the many `git`/`gh` subprocesses relay spawns. Guarded for platforms
    without SIGPIPE (Windows).
    """
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def main() -> None:
    """Console-script entry point. Loads config, registers aliases, dispatches."""
    _restore_default_sigpipe()
    invoked_command = sys.argv[1] if len(sys.argv) > 1 else None
    # `relay init` (fresh or `--update`) is the create/recovery command — it
    # must run even when the current config is missing, legacy, or broken,
    # since repairing exactly that is often why it's invoked. A stale CLI plus
    # a migrated `relay.toml` would otherwise deadlock: the update that fixes
    # the CLI can't run because the stale CLI rejects the new config first.
    # `uninstall` shares this leniency: a broken/legacy config is itself a
    # reason to remove Relay, so it must not be blocked by config load failure.
    init_invoked = invoked_command in ("init", "uninstall")
    try:
        find_repo_root()
        cfg = load_config()
    except ConfigError as exc:
        msg = str(exc)
        if "No relay.toml found" in msg:
            cfg = None
        elif init_invoked:
            typer.secho(
                f"Note: ignoring config error so `{sys.argv[1]}` can run — {msg}",
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
                "relay: ignoring legacy alias 'uninstall' from relay.toml "
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
