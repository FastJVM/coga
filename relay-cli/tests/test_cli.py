"""Smoke tests for the CLI scaffold.

Asserts that the package installs correctly, the click group wires up
every subcommand, and each subcommand's --help advertises its flags.
Functional behavior is covered by subsequent tickets.
"""

from __future__ import annotations

from click.testing import CliRunner

import relay_os
from relay_os.cli import main


SUBCOMMANDS = ("init", "create", "launch", "status", "step", "panic", "feed")


def test_package_importable() -> None:
    """`from relay_os import cli` works and the package has a version."""
    assert relay_os.__version__


def test_main_help_lists_every_subcommand() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    for cmd in SUBCOMMANDS:
        assert cmd in result.output, f"{cmd!r} missing from `relay --help`"


def test_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert relay_os.__version__ in result.output


def test_create_help_shows_stubbed_args() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["create", "--help"])
    assert result.exit_code == 0, result.output
    for flag in ("--project", "--title", "--workflow", "--context", "--mode"):
        assert flag in result.output, f"{flag} missing from `relay create --help`"


def test_launch_help_shows_stubbed_args() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["launch", "--help"])
    assert result.exit_code == 0, result.output
    assert "--task" in result.output
    assert "--dry-run" in result.output


def test_panic_requires_task_and_reason() -> None:
    runner = CliRunner()
    # No args — click should error out on the required options.
    result = runner.invoke(main, ["panic"])
    assert result.exit_code != 0
    assert "--task" in result.output or "--reason" in result.output


def test_every_subcommand_is_a_stub() -> None:
    """Every subcommand prints "not implemented" when invoked with the
    minimum valid args. Serves as a checklist: once a ticket fills in a
    command, that command's assertion moves out of this test."""
    runner = CliRunner()
    invocations = [
        ["init"],
        ["create"],
        ["launch", "--task", "001"],
        ["status"],
        ["step", "--task", "001"],
        ["panic", "--task", "001", "--reason", "test"],
        ["feed", "--task", "001", "--message", "test"],
    ]
    for argv in invocations:
        result = runner.invoke(main, argv)
        assert result.exit_code == 0, f"{argv}: {result.output}"
        assert "not implemented" in result.output, f"{argv} should print stub marker"
