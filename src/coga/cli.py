"""Coga CLI entry point."""

from __future__ import annotations

import shlex
import signal
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version

import typer

from coga import git
from coga.aliases import (
    BUILTIN_COMMANDS as _BUILTIN_COMMANDS,
    DEFAULT_ALIASES as _DEFAULT_ALIASES,
    validate_aliases as _validate_aliases,
)
from coga.commands import block as block_cmd
from coga.commands import create as create_cmd
from coga.commands import delete as delete_cmd
from coga.commands import digest as digest_cmd
from coga.commands import init as init_cmd
from coga.commands import launch as launch_cmd
from coga.commands import mark as mark_cmd
from coga.commands import megalaunch as megalaunch_cmd
from coga.commands import open_pr as open_pr_cmd
from coga.commands import project as project_cmd
from coga.commands import recurring as recurring_cmd
from coga.commands import retire as retire_cmd
from coga.commands import secret as secret_cmd
from coga.commands import show as show_cmd
from coga.commands import slack as slack_cmd
from coga.commands import status as status_cmd
from coga.commands import skill as skill_cmd
from coga.commands import ticket as ticket_cmd
from coga.commands import bump as bump_cmd
from coga.commands import uninstall as uninstall_cmd
from coga.commands import unblock as unblock_cmd
from coga.commands import usage as usage_cmd
from coga.commands import validate as validate_cmd
from coga.commands.update import read_pin, read_pin_source
from coga.config import ConfigError, find_repo_root, load_config


def _print_version_and_exit(value: bool) -> None:
    if not value:
        return
    try:
        pkg = _pkg_version("coga")
    except PackageNotFoundError:
        pkg = "unknown"
    typer.echo(f"coga {pkg}")
    try:
        coga_os = find_repo_root()
    except ConfigError:
        coga_os = None
    pin = read_pin(coga_os) if coga_os else None
    if pin is not None:
        pin_source = read_pin_source(coga_os)
        suffix = f" (from {pin_source})" if pin_source else ""
        typer.echo(f"vendored CLI {pin}{suffix}")
    raise typer.Exit()


app = typer.Typer(
    name="coga",
    help="Organize agent work in markdown.",
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
        help="Print the coga package and vendored CLI versions.",
    ),
) -> None:
    """Organize agent work in markdown."""


app.command("init")(init_cmd.init)
app.command("uninstall")(uninstall_cmd.uninstall)
app.command("create")(create_cmd.create)
app.command("ticket")(ticket_cmd.ticket)
app.command("project")(project_cmd.project)
app.command("launch")(launch_cmd.launch)
app.command("megalaunch")(megalaunch_cmd.megalaunch)
app.command("status")(status_cmd.status)
app.command("show")(show_cmd.show)
app.command("bump")(bump_cmd.bump)
app.command("open-pr")(open_pr_cmd.open_pr_command)
app.command("block")(block_cmd.block)
app.command("unblock")(unblock_cmd.unblock)
app.command("delete")(delete_cmd.delete)
app.command("retire")(retire_cmd.retire)
app.command("slack")(slack_cmd.slack)
app.command("digest")(digest_cmd.digest)
app.command("usage")(usage_cmd.usage)
app.command("validate")(validate_cmd.validate)
app.add_typer(skill_cmd.app, name="skill")
app.add_typer(mark_cmd.app, name="mark")
app.add_typer(recurring_cmd.app, name="recurring")
app.add_typer(secret_cmd.app, name="secret")


# Commands that must NOT trigger the end-of-command `coga/` state sweep.
# Read-only commands are excluded because `coga/principles` #6 forbids a render
# from mutating as a side effect (committing dirty OS state *is* a mutation).
# `init`/`uninstall` are excluded because they create or remove the repo itself
# and run with a possibly-absent config — not the steady-state boundary the
# sweep is for.
_NON_SWEEPING_COMMANDS = frozenset(
    {"status", "show", "validate", "usage", "init", "uninstall"}
)
_SWEEPING_COMMANDS = frozenset(
    {
        "create",
        "ticket",
        "project",
        "launch",
        "megalaunch",
        "bump",
        "block",
        "unblock",
        "delete",
        "retire",
        "slack",
        "digest",
    }
)
_SWEEPING_SKILL_SUBCOMMANDS = frozenset(
    {"install", "install-local", "install-url", "update", "remove"}
)
_SWEEPING_MARK_SUBCOMMANDS = frozenset({"active", "paused", "done"})


def _sweep_coga_state(cfg) -> None:
    """Catch-all: commit anything still dirty under `coga/` after a mutating
    command, so machine side-effects and human hand-edits converge on git at the
    next invocation (the "no daemon" alternative to instant commits).

    Wired only to mutating commands via `_NON_SWEEPING_COMMANDS` and the
    option/`--help` guards: a bare `coga`, `--version`, or any `--help` is not a
    state change and must not commit. No repo (`cfg is None`) → nothing to sweep.
    The sweep is itself non-fatal (`git.sync_coga_state` swallows git failures),
    so it never masks the command's own exit.
    """
    if cfg is None:
        return
    if _should_sweep_coga_state(sys.argv):
        git.sync_coga_state(cfg)


def _should_sweep_coga_state(argv: list[str]) -> bool:
    args = argv[1:]
    if not args:
        return False
    if "--help" in args or "-h" in args:
        return False
    command = args[0]
    if command.startswith("-") or command in _NON_SWEEPING_COMMANDS:
        return False
    if command in _SWEEPING_COMMANDS:
        return True
    if command == "skill":
        subcommand = args[1] if len(args) > 1 else None
        return subcommand in _SWEEPING_SKILL_SUBCOMMANDS
    if command == "mark":
        subcommand = args[1] if len(args) > 1 else None
        return subcommand in _SWEEPING_MARK_SUBCOMMANDS
    if command == "recurring":
        if "--all" in args[1:]:
            # The parent dispatcher owns no repo state; each child recurring
            # CLI performs its normal end-of-command sweep in its own repo.
            return False
        subcommand = args[1] if len(args) > 1 else None
        return subcommand is None or subcommand.startswith("-") or subcommand == "launch"
    if command == "secret":
        return False
    return False


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


def main() -> None:
    """Console-script entry point. Loads config, registers aliases, dispatches."""
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
    # This eager load only feeds aliases and the end-of-command state sweep,
    # neither of which reads `current_user` — so it tolerates a missing `user`
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
            help_invoked = any(arg in ("--help", "-h") for arg in sys.argv[1:])
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

    try:
        app()
    finally:
        # End-of-command boundary: commit any dirty `coga/` OS state the command
        # itself didn't sync (a human hand-edit, a side-effect write). Runs after
        # `app()` whether it returned or raised `SystemExit`/`typer.Exit`; the
        # on-disk markdown is the source of truth, and atomic writes mean a
        # mid-command crash never leaves a half-written file to commit.
        _sweep_coga_state(cfg)


if __name__ == "__main__":
    main()
