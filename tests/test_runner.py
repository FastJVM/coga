from __future__ import annotations

import sys
from typing import cast

from typer.testing import CliRunner

from coga.cli import app
from coga.commands import run as run_command
from coga.config import Config
from coga.runner import RECIPES, run_recipe


EXPECTED_RECIPES = (
    "autoclose",
    "digest",
    "blocker-reminders",
    "branch-sweep",
    "validate-drift",
    "cleanup-orphan-markers",
    "recurring-scan",
    "skill-update",
    "open-pr",
    "delete-task",
)


def test_recipe_registry_is_fixed_and_explicit() -> None:
    assert tuple(RECIPES) == EXPECTED_RECIPES


def test_run_command_is_discoverable() -> None:
    root_help = CliRunner().invoke(app, ["--help"])
    command_help = CliRunner().invoke(app, ["run", "--help"])

    assert root_help.exit_code == 0
    assert "run" in root_help.output
    assert command_help.exit_code == 0
    assert "RECIPE" in command_help.output


def test_run_recipe_forwards_argv_boundaries_and_spelling(monkeypatch) -> None:
    cfg = cast(Config, object())
    received: list[tuple[Config, list[str]]] = []

    def fake_recipe(recipe_cfg: Config, argv: list[str]) -> int:
        received.append((recipe_cfg, argv))
        return 9

    monkeypatch.setitem(RECIPES, "skill-update", fake_recipe)
    argv = ["two words", "--no-fix", "--label=value"]

    assert run_recipe(cfg, "skill-update", argv) == 9
    assert received == [(cfg, argv)]
    assert received[0][1] is not argv


def test_no_arg_recipes_reject_unexpected_tokens() -> None:
    cfg = cast(Config, object())

    for name in (
        "autoclose",
        "digest",
        "blocker-reminders",
        "branch-sweep",
        "cleanup-orphan-markers",
    ):
        assert run_recipe(cfg, name, ["unexpected"]) == 2


def test_run_command_passes_trailing_tokens_as_ordinary_argv(monkeypatch) -> None:
    cfg = cast(Config, object())
    received: list[tuple[Config, str, list[str]]] = []
    monkeypatch.setattr(run_command, "load_config", lambda: cfg)

    def fake_run_recipe(
        recipe_cfg: Config, name: str, argv: list[str]
    ) -> int:
        received.append((recipe_cfg, name, argv))
        return 0

    monkeypatch.setattr(run_command, "run_recipe", fake_run_recipe)

    result = CliRunner().invoke(
        app,
        ["run", "skill-update", "two words", "--no-fix", "--label=value"],
    )

    assert result.exit_code == 0, result.output
    assert received == [
        (cfg, "skill-update", ["two words", "--no-fix", "--label=value"])
    ]


def test_run_command_rejects_unknown_recipe_with_known_names(monkeypatch) -> None:
    monkeypatch.setattr(run_command, "load_config", lambda: cast(Config, object()))

    result = CliRunner().invoke(app, ["run", "not-a-recipe"])

    assert result.exit_code == 2
    assert "unknown recipe 'not-a-recipe'" in result.output
    for name in EXPECTED_RECIPES:
        assert name in result.output


def test_run_command_preserves_output_and_exit_code(monkeypatch) -> None:
    monkeypatch.setattr(run_command, "load_config", lambda: cast(Config, object()))

    def fake_run_recipe(
        cfg: Config, name: str, argv: list[str]
    ) -> int:
        print("recipe stdout")
        print("recipe stderr", file=sys.stderr)
        return 7

    monkeypatch.setattr(run_command, "run_recipe", fake_run_recipe)

    result = CliRunner().invoke(app, ["run", "digest"])

    assert result.exit_code == 7
    assert result.stdout == "recipe stdout\n"
    assert result.stderr == "recipe stderr\n"


def test_run_command_leaves_unexpected_exceptions_loud(monkeypatch) -> None:
    monkeypatch.setattr(run_command, "load_config", lambda: cast(Config, object()))

    def fail(cfg: Config, name: str, argv: list[str]) -> int:
        raise RuntimeError("recipe exploded")

    monkeypatch.setattr(run_command, "run_recipe", fail)

    result = CliRunner().invoke(app, ["run", "digest"])

    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "recipe exploded"
