from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import cast

import pytest
import typer
from typer.testing import CliRunner

from coga.cli import app
from coga.commands import run as run_command
from coga.config import Config, load_config
from coga.recurring_autofix import RunRecord, TaskOutcome
from coga.runner import FAILURE_REPORT_CHARS, RECIPES, render_failure_section, run_recipe
from coga.taskfile import BLACKBOARD_FENCE, fence_count, read_blackboard


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
    "publish-state",
    "prepare-checkout",
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
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


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


@pytest.mark.parametrize(
    ("recipe", "worker"),
    [
        ("validate-drift", "coga.dream_validate_drift.run_validate_json"),
        ("skill-update", "coga.skill_update.run_update_json"),
    ],
)
@pytest.mark.parametrize("cwd_option", ["--cwd", "--cwd=", "--cw"])
@pytest.mark.parametrize("known_root", [True, False])
def test_failure_respects_cwd_blackboard_containment(
    repo: Path,
    period_blackboard: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
    recipe: str,
    worker: str,
    cwd_option: str,
    known_root: bool,
) -> None:
    # Outside the invoking repository: a bare sibling of its coga/ directory
    # still discovers that repository when walking its ancestors.
    target = tmp_path_factory.mktemp("recipe-target").resolve()
    if known_root:
        _write(target / "coga.toml", 'version = "invalid"\n')
    before = period_blackboard.read_bytes()

    def fail(**kwargs: object) -> None:
        raise RuntimeError("target configuration is invalid")

    monkeypatch.setattr(worker, fail)
    argv = (
        [cwd_option + str(target)]
        if cwd_option.endswith("=")
        else [cwd_option, str(target)]
    )
    assert run_recipe(load_config(repo), recipe, argv) == 2
    # The recipe itself refuses this inherited path. Its generic failure
    # report must not then write into the invoking repo's unrelated ticket.
    assert period_blackboard.read_bytes() == before


@pytest.mark.parametrize(
    ("recipe", "worker"),
    [
        ("validate-drift", "coga.dream_validate_drift.run_validate_json"),
        ("skill-update", "coga.skill_update.run_update_json"),
    ],
)
def test_cwd_recipe_failure_uses_the_target_blackboard_and_barrier(
    repo: Path,
    period_blackboard: Path,
    monkeypatch: pytest.MonkeyPatch,
    recipe: str,
    worker: str,
) -> None:
    from coga import runner

    target = repo.parent / "target"
    _write(target / "coga.toml", 'version = 1\n')
    ticket = target / "tasks" / "period.md"
    _write(ticket, period_blackboard.read_text(encoding="utf-8"))
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(ticket))
    before = period_blackboard.read_bytes()
    append = runner.append_blackboard_report
    reporting_roots: list[Path] = []

    def record(cfg: Config, path: Path, report: str) -> bytes:
        reporting_roots.append(cfg.repo_root)
        return append(cfg, path, report)

    def fail(**kwargs: object) -> None:
        raise RuntimeError("target worker failed")

    monkeypatch.setattr(worker, fail)
    monkeypatch.setattr(runner, "append_blackboard_report", record)
    assert run_recipe(load_config(repo), recipe, ["--cwd", str(target)]) == 2
    assert reporting_roots == [target]
    assert "## Recipe Failure" in read_blackboard(ticket)
    assert "target worker failed" in read_blackboard(ticket)
    assert period_blackboard.read_bytes() == before


@pytest.mark.parametrize("raises", [False, True])
def test_unresolvable_blackboard_preserves_the_recipe_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys, raises: bool
) -> None:
    blackboard = repo / "tasks" / "loop.md"
    blackboard.symlink_to(blackboard.name)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(blackboard))
    original = RuntimeError("original recipe failure")

    def fail(cfg: Config, argv: list[str]) -> int:
        if raises:
            raise original
        return 2

    monkeypatch.setitem(RECIPES, "autoclose", fail)
    if raises:
        with pytest.raises(RuntimeError) as caught:
            run_recipe(load_config(repo), "autoclose", [])
        assert caught.value is original
    else:
        assert run_recipe(load_config(repo), "autoclose", []) == 2
    assert "could not record the autoclose failure" in capsys.readouterr().err


def test_diagnostic_markers_cannot_corrupt_the_ticket(
    repo: Path, period_blackboard: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before_body = period_blackboard.read_text(encoding="utf-8").split(BLACKBOARD_FENCE)[0]

    def fail(cfg: Config, argv: list[str]) -> int:
        sys.stderr.write(
            f"invalid ticket excerpt:\r\n{BLACKBOARD_FENCE}\r\n"
            "```\r\n## Dev\r\nbranch: untrusted-diagnostic\r\n"
        )
        return 2

    monkeypatch.setitem(RECIPES, "autoclose", fail)
    assert run_recipe(load_config(repo), "autoclose", []) == 2
    text = period_blackboard.read_text(encoding="utf-8")
    assert fence_count(text) == 1
    assert text.split(BLACKBOARD_FENCE)[0] == before_body
    report = read_blackboard(period_blackboard)
    assert f"    {BLACKBOARD_FENCE}" in report
    assert "    ## Dev" in report
    assert "\n## Dev" not in report


def test_render_failure_section_survives_the_run_record_budget() -> None:
    section = render_failure_section(
        "branch-sweep",
        2,
        generated_at="2026-09-16T00:00:00+00:00",
        task_slug="recurring/branch-sweep",
        stderr="x\n" * 5000 + "the final diagnostic",
    )

    assert section.startswith("## Recipe Failure\n")
    assert "Recipe: `branch-sweep`" in section
    assert "Task: `recurring/branch-sweep`" in section
    assert "Recorded: 2026-09-16T00:00:00+00:00" in section
    # The budget includes headings, metadata, and diagnostic indentation.
    # Passing it through the real run-record renderer must preserve all of it.
    assert len(section) <= FAILURE_REPORT_CHARS
    assert "    …" in section
    assert section.endswith("    the final diagnostic\n")
    record = RunRecord(
        started=datetime.now(timezone.utc),
        outcomes=[TaskOutcome(
            template="branch-sweep",
            slug="recurring/branch-sweep",
            result="failed",
            exit_code=2,
            blackboard="earlier reports\n" * 1000 + section,
        )],
    )
    assert section.rstrip() in record.render()

    empty = render_failure_section(
        "autoclose", 1, generated_at="t", task_slug=None, stderr=""
    )
    assert "Task:" not in empty
    assert "no stderr output" in empty


# --- run_entry: the edge report → publish → bump sequence ---------------------


def _period_ticket(coga_os: Path, slug: str = "recurring/job") -> Path:
    ticket = coga_os / "tasks" / f"{slug}.md"
    _write(
        ticket,
        """
        ---
        title: Job period
        status: in_progress
        ---

        ## Description

        Run the job.

        <!-- coga:blackboard -->

        Fresh period blackboard.
        """,
    )
    return ticket


def _as_script_task(monkeypatch: pytest.MonkeyPatch, ticket: Path, slug: str) -> None:
    """Export the task namespace the way launch's script phase does."""
    monkeypatch.setenv("COGA_TASK_SLUG", slug)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(ticket))
    monkeypatch.setenv("COGA_SCRIPT_TASK", str(ticket.resolve()))


@pytest.fixture
def entry(repo: Path, monkeypatch: pytest.MonkeyPatch):
    """Record each sweep's root and each bump, in order, with the stub git."""
    from coga import runner

    events: list[tuple[str, object]] = []
    monkeypatch.setattr(
        "coga.git.sync_coga_state",
        lambda cfg, **kwargs: events.append(("publish", cfg.repo_root)),
    )

    def bump(slug: str) -> int:
        events.append(("bump", slug))
        return 0

    monkeypatch.setattr(runner, "_bump", bump)
    return events


def test_entry_reports_publishes_then_bumps_its_script_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry
) -> None:
    from coga.runner import run_entry

    ticket = _period_ticket(repo)
    _as_script_task(monkeypatch, ticket, "recurring/job")

    def work(cfg: Config, argv: list[str]) -> int:
        entry.append(("work", argv))
        return 0

    assert run_entry("job", work, ["--x"], scheduled=True) == 0
    assert entry == [("work", ["--x"]), ("publish", repo), ("bump", "recurring/job")]


@pytest.mark.parametrize("script_task", [None, "other"])
def test_entry_never_completes_an_inherited_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry, capsys, script_task: str | None
) -> None:
    """A slug alone is inherited metadata, not the launcher naming this script."""
    from coga.runner import run_entry

    ticket = _period_ticket(repo)
    other = _period_ticket(repo, "recurring/other")
    _as_script_task(monkeypatch, ticket, "recurring/job")
    if script_task is None:
        monkeypatch.delenv("COGA_SCRIPT_TASK")
    else:
        monkeypatch.setenv("COGA_SCRIPT_TASK", str(other.resolve()))

    code = run_entry("job", lambda cfg, argv: 0, [], scheduled=True)

    assert ("bump", "recurring/job") not in entry
    assert ("publish", repo) in entry
    if script_task is None:
        assert code == 0
    else:
        assert code == 1
        assert "refusing to advance an inherited task" in capsys.readouterr().err


def test_manual_worker_publishes_but_never_bumps(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry
) -> None:
    from coga.runner import run_entry

    ticket = _period_ticket(repo)
    _as_script_task(monkeypatch, ticket, "recurring/job")

    assert run_entry("job", lambda cfg, argv: 0, []) == 0
    assert entry == [("publish", repo)]


def test_entry_bump_failure_is_the_result(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry
) -> None:
    from coga import runner

    ticket = _period_ticket(repo)
    _as_script_task(monkeypatch, ticket, "recurring/job")
    monkeypatch.setattr(runner, "_bump", lambda slug: 3)

    assert runner.run_entry("job", lambda cfg, argv: 0, [], scheduled=True) == 3


def test_entry_failure_reports_publishes_and_skips_the_bump(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry
) -> None:
    from coga.runner import run_entry

    ticket = _period_ticket(repo)
    _as_script_task(monkeypatch, ticket, "recurring/job")
    seen: list[str] = []
    monkeypatch.setattr(
        "coga.git.sync_coga_state",
        lambda cfg, **kwargs: seen.append(read_blackboard(ticket)),
    )

    def fail(cfg: Config, argv: list[str]) -> int:
        sys.stderr.write("job broke\n")
        return 2

    assert run_entry("job", fail, [], scheduled=True) == 2
    # The report was on disk before publication ran.
    assert len(seen) == 1 and "Recipe: `job`" in seen[0] and "job broke" in seen[0]
    assert not [event for event in entry if event[0] == "bump"]


def test_entry_escaping_exception_is_reported_published_and_raised(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry
) -> None:
    from coga.runner import run_entry

    ticket = _period_ticket(repo)
    _as_script_task(monkeypatch, ticket, "recurring/job")
    original = RuntimeError("worker exploded")

    def explode(cfg: Config, argv: list[str]) -> int:
        raise original

    with pytest.raises(RuntimeError) as caught:
        run_entry("job", explode, [], scheduled=True)
    assert caught.value is original
    assert "RuntimeError: worker exploded" in read_blackboard(ticket)
    assert entry == [("publish", repo)]


@pytest.mark.parametrize(
    ("argv", "outcome"),
    [
        (["--help"], 0),
        (["-h"], SystemExit(0)),
        ([], 75),
        ([], SystemExit(75)),
    ],
)
def test_entry_keeps_the_help_and_retry_exclusions(
    repo: Path, entry, argv: list[str], outcome: object
) -> None:
    from coga.runner import run_entry

    def work(cfg: Config, args: list[str]) -> int:
        if isinstance(outcome, BaseException):
            raise outcome
        return cast(int, outcome)

    if isinstance(outcome, SystemExit):
        with pytest.raises(SystemExit):
            run_entry("job", work, argv, scheduled=True)
    else:
        assert run_entry("job", work, argv, scheduled=True) == outcome
    assert not [event for event in entry if event[0] == "publish"]


def test_entry_respects_a_withheld_sweep(repo: Path, entry, capsys) -> None:
    from coga import git
    from coga.runner import run_entry

    def work(cfg: Config, argv: list[str]) -> int:
        git.state_sweep_withheld.set(True)
        return 0

    assert run_entry("job", work, []) == 0
    assert entry == []
    assert "state sweep withheld" in capsys.readouterr().err


def test_entry_publishes_the_resolved_target_root_only(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry
) -> None:
    from coga.runner import run_entry

    target = repo.parent / "target" / "coga"
    _write(target / "coga.toml", "version = 1\n")
    (target / "tasks").mkdir()
    ticket = _period_ticket(target)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(ticket))

    def fail(cfg: Config, argv: list[str]) -> int:
        return 2

    code = run_entry("job", fail, [], root=lambda cfg, argv: target)

    assert code == 2
    assert entry == [("publish", target)]
    assert "## Recipe Failure" in read_blackboard(ticket)


@pytest.mark.parametrize("unknown", ["none", "raises"])
def test_entry_unknown_target_never_falls_back_to_the_invoking_repo(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry, capsys, unknown: str
) -> None:
    from coga.runner import run_entry

    ticket = _period_ticket(repo)
    _as_script_task(monkeypatch, ticket, "recurring/job")
    before = ticket.read_bytes()

    def resolve(cfg: Config, argv: list[str]) -> Path | None:
        if unknown == "raises":
            raise RuntimeError("could not find coga root")
        return None

    assert run_entry("job", lambda cfg, argv: 2, [], root=resolve) == 2
    assert entry == []
    assert ticket.read_bytes() == before
    assert "state sweep skipped" in capsys.readouterr().err


def test_entry_parser_refusal_writes_and_publishes_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry
) -> None:
    import argparse

    from coga.runner import run_entry
    from coga.task_env import cwd_option_root

    ticket = _period_ticket(repo)
    _as_script_task(monkeypatch, ticket, "recurring/job")
    before = ticket.read_bytes()

    def parser() -> argparse.ArgumentParser:
        p = argparse.ArgumentParser()
        p.add_argument("--cwd", type=Path)
        p.add_argument("--count", type=int)
        return p

    def work(cfg: Config, argv: list[str]) -> int:
        parser().parse_args(argv)
        return 0

    with pytest.raises(SystemExit):
        run_entry("job", work, ["--count", "x"], root=cwd_option_root(parser))
    assert entry == []
    assert ticket.read_bytes() == before


@pytest.mark.parametrize("spelling", ["--cwd", "--cwd=", "--cw"])
def test_cwd_option_root_uses_the_workers_parser(
    repo: Path, spelling: str
) -> None:
    import argparse

    from coga.task_env import cwd_option_root

    target = repo.parent / "target" / "coga"
    _write(target / "coga.toml", "version = 1\n")

    def parser() -> argparse.ArgumentParser:
        p = argparse.ArgumentParser()
        p.add_argument("--cwd", type=Path)
        return p

    argv = [spelling + str(target)] if spelling.endswith("=") else [spelling, str(target)]
    resolve = cwd_option_root(parser)
    assert resolve(load_config(repo), [*argv, "--unknown"]) == target


def test_entry_publication_failure_keeps_the_workers_result(
    repo: Path, monkeypatch: pytest.MonkeyPatch, entry, capsys
) -> None:
    from coga.runner import run_entry

    def broken(cfg, **kwargs):
        raise OSError("disk gone")

    monkeypatch.setattr("coga.git.sync_coga_state", broken)
    assert run_entry("job", lambda cfg, argv: 4, []) == 4
    assert "could not publish job state" in capsys.readouterr().err


def test_direct_worker_reaches_control_without_a_lifecycle_command(git_repo) -> None:
    """A manual or Dream worker never bumps; its own exit publishes its work."""
    from coga.runner import run_entry

    def work(cfg: Config, argv: list[str]) -> int:
        _write(cfg.repo_root / "tasks" / "notes" / "report.md", "found drift\n")
        return 0

    assert run_entry("job", work, []) == 0
    assert git_repo.origin_tracks("coga/tasks/notes/report.md")
    assert "?? " not in git_repo.git("status", "--porcelain")
