from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import cast

import pytest
import typer
from typer.testing import CliRunner

from coga.cli import app
from coga.commands import run as run_command
from coga.config import Config, load_config
from coga.runner import RECIPES, render_failure_section, run_recipe
from coga.taskfile import read_blackboard


EXPECTED_RECIPES = (
    "autoclose",
    "blocker-reminders",
    "branch-sweep",
    "validate-drift",
    "cleanup-orphan-markers",
    "recurring-scan",
    "autofix-analyze",
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

    result = CliRunner().invoke(app, ["run", "autoclose"])

    assert result.exit_code == 7
    assert result.stdout == "recipe stdout\n"
    assert result.stderr == "recipe stderr\n"


def test_run_command_leaves_unexpected_exceptions_loud(monkeypatch) -> None:
    monkeypatch.setattr(run_command, "load_config", lambda: cast(Config, object()))

    def fail(cfg: Config, name: str, argv: list[str]) -> int:
        raise RuntimeError("recipe exploded")

    monkeypatch.setattr(run_command, "run_recipe", fail)

    result = CliRunner().invoke(app, ["run", "autoclose"])

    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "recipe exploded"


# --- the failure surface -------------------------------------------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [notification.slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"

        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    (coga_os / "tasks").mkdir(parents=True)
    monkeypatch.chdir(coga_os)
    return coga_os


@pytest.fixture
def period_blackboard(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A period task's fenced ticket, exported the way `coga launch` does."""
    ticket = repo / "tasks" / "recurring" / "autoclose-merged" / "ticket.md"
    _write(
        ticket,
        """
        ---
        title: Autoclose merged
        status: in_progress
        ---

        ## Description

        Run the sweep.

        <!-- coga:blackboard -->

        Fresh period blackboard.
        """,
    )
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(ticket))
    monkeypatch.setenv("COGA_TASK_SLUG", "recurring/autoclose-merged")
    return ticket


def test_failing_recipe_records_its_stderr_on_the_period_blackboard(
    repo: Path, period_blackboard: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    # The recurring sweep discards a `ticket.py` child's stderr and reads only
    # the period blackboard into its run record. A recipe that exits non-zero
    # to stderr alone used to show up there as a failed task with a blank
    # blackboard and no reason; the layer, not each recipe, now records it.
    def fail(cfg: Config, argv: list[str]) -> int:
        sys.stderr.write("[autoclose] gh pr view failed: \x1b[31mrate limited\x1b[0m\n")
        return 2

    monkeypatch.setitem(RECIPES, "autoclose", fail)

    assert run_recipe(load_config(repo), "autoclose", []) == 2

    # The console still sees every byte — the tail is a copy, not a capture.
    assert "gh pr view failed" in capsys.readouterr().err
    written = read_blackboard(period_blackboard)
    assert "Fresh period blackboard." in written
    assert "## Recipe Failure" in written
    assert "Recipe: `autoclose`" in written
    assert "Exit: 2" in written
    assert "Task: `recurring/autoclose-merged`" in written
    assert "[autoclose] gh pr view failed: rate limited" in written
    assert "\x1b[" not in written


def test_escaping_exception_is_recorded_and_still_raised(
    repo: Path, period_blackboard: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An uncaught exception in a `ticket.py` child is a traceback on stderr and
    # exit 1 — the same discarded stream. Record it, then let it propagate
    # unchanged so `coga run` stays as loud as before.
    def explode(cfg: Config, argv: list[str]) -> int:
        raise RuntimeError("recipe exploded")

    monkeypatch.setitem(RECIPES, "autoclose", explode)

    with pytest.raises(RuntimeError, match="recipe exploded"):
        run_recipe(load_config(repo), "autoclose", [])

    written = read_blackboard(period_blackboard)
    assert "## Recipe Failure" in written
    assert "Exit: 1" in written
    assert "RuntimeError: recipe exploded" in written


def test_argparse_refusal_is_recorded_with_its_exit_code(
    repo: Path, period_blackboard: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # argparse refuses argv by printing usage to stderr and raising
    # `SystemExit(2)`; a nested Typer command refuses with `typer.Exit`. Both
    # carry the exit the process will end with.
    def refuse(cfg: Config, argv: list[str]) -> int:
        sys.stderr.write("usage: coga run autoclose\n")
        raise SystemExit(2)

    monkeypatch.setitem(RECIPES, "autoclose", refuse)
    with pytest.raises(SystemExit):
        run_recipe(load_config(repo), "autoclose", ["--bogus"])
    written = read_blackboard(period_blackboard)
    assert "Exit: 2" in written
    assert "usage: coga run autoclose" in written

    def typer_refuse(cfg: Config, argv: list[str]) -> int:
        raise typer.Exit(3)

    monkeypatch.setitem(RECIPES, "autoclose", typer_refuse)
    with pytest.raises(typer.Exit):
        run_recipe(load_config(repo), "autoclose", [])
    assert "Exit: 3" in read_blackboard(period_blackboard)


def test_clean_exits_leave_the_blackboard_alone(
    repo: Path, period_blackboard: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Success is not reported by the layer — nothing in the `ticket.py`
    # contract asks for a run report, and a zero-carrying `SystemExit` or
    # `typer.Exit` is a return, not a failure.
    before = read_blackboard(period_blackboard)

    monkeypatch.setitem(RECIPES, "autoclose", lambda cfg, argv: 0)
    assert run_recipe(load_config(repo), "autoclose", []) == 0

    def zero_exit(cfg: Config, argv: list[str]) -> int:
        raise SystemExit(0)

    monkeypatch.setitem(RECIPES, "autoclose", zero_exit)
    with pytest.raises(SystemExit):
        run_recipe(load_config(repo), "autoclose", [])

    def zero_typer_exit(cfg: Config, argv: list[str]) -> int:
        raise typer.Exit(0)

    monkeypatch.setitem(RECIPES, "autoclose", zero_typer_exit)
    with pytest.raises(typer.Exit):
        run_recipe(load_config(repo), "autoclose", [])

    assert read_blackboard(period_blackboard) == before


def test_failure_without_a_blackboard_changes_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    # `coga run` from an operator's shell has no task: stderr already reached
    # the console, so the layer neither duplicates it on stdout nor warns.
    def fail(cfg: Config, argv: list[str]) -> int:
        sys.stderr.write("boom\n")
        return 2

    monkeypatch.setitem(RECIPES, "autoclose", fail)

    assert run_recipe(load_config(repo), "autoclose", []) == 2

    captured = capsys.readouterr()
    assert captured.err == "boom\n"
    assert captured.out == ""


def test_unwritable_blackboard_never_outranks_the_recipe_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    # A blackboard whose task directory is gone (a stale launch context) must
    # not replace the recipe's own exit code with a traceback.
    monkeypatch.setenv(
        "COGA_TASK_BLACKBOARD", str(repo / "tasks" / "missing" / "ticket.md")
    )

    def fail(cfg: Config, argv: list[str]) -> int:
        sys.stderr.write("boom\n")
        return 2

    monkeypatch.setitem(RECIPES, "autoclose", fail)

    assert run_recipe(load_config(repo), "autoclose", []) == 2
    assert "could not record the autoclose failure" in capsys.readouterr().err


def test_render_failure_section_bounds_the_detail_and_names_the_run() -> None:
    section = render_failure_section(
        "branch-sweep",
        2,
        generated_at="2026-09-16T00:00:00+00:00",
        task_slug="recurring/branch-sweep",
        stderr="x" * 5000,
    )

    assert section.startswith("## Recipe Failure\n")
    assert "Recipe: `branch-sweep`" in section
    assert "Task: `recurring/branch-sweep`" in section
    assert "Recorded: 2026-09-16T00:00:00+00:00" in section
    # Bounded to what the sweep's run record can carry, keeping the tail.
    assert "…" + "x" * 4000 + "\n```\n" in section
    assert "x" * 4001 not in section
    assert section.endswith("```\n")

    empty = render_failure_section(
        "autoclose", 1, generated_at="t", task_slug=None, stderr=""
    )
    assert "Task:" not in empty
    assert "no stderr output" in empty
