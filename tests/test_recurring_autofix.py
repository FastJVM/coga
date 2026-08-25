"""Tests for the recurring sweep's autofix loop (`coga/recurring_autofix.py`)."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from coga import recurring_autofix as autofix
from coga.config import AgentType, load_config
from coga.recurring_autofix import (
    Analysis,
    RunRecord,
    TaskOutcome,
    blackboard_for_ref,
    build_analyze_command,
    build_prompt,
    parse_analysis,
)

from tests.test_recurring import repo  # noqa: F401 — shared repo fixture


# --- parsing the analyst's reply ---------------------------------------------


def test_parses_a_clean_problem_reply() -> None:
    analysis = parse_analysis(
        "VERDICT: problem\n"
        "TITLE: Fix the digest recipe's timezone handling\n"
        "---\n"
        "The `digest` recipe exited 1 with a `ZoneInfoNotFoundError`.\n"
    )
    assert analysis.verdict == "problem"
    assert analysis.title == "Fix the digest recipe's timezone handling"
    assert analysis.body.startswith("The `digest` recipe exited 1")
    assert "---" not in analysis.body


def test_parses_ok_and_duplicate_verdicts() -> None:
    assert parse_analysis("VERDICT: ok\n").verdict == "ok"
    dup = parse_analysis("VERDICT: duplicate\nDUPLICATE: autofix/digest-tz\n")
    assert dup.verdict == "duplicate"
    assert dup.duplicate_of == "autofix/digest-tz"


def test_unparseable_reply_surfaces_as_a_problem() -> None:
    """A broken analyst must not silently swallow the run it was hired to read."""
    analysis = parse_analysis("the digest recipe blew up and I forgot the format")
    assert analysis.verdict == "problem"
    assert analysis.title == "the digest recipe blew up and I forgot the format"
    assert "digest recipe blew up" in analysis.body


def test_long_titles_are_clipped_to_one_line() -> None:
    analysis = parse_analysis(
        "VERDICT: problem\nTITLE: " + "fix the thing " * 20 + "\n---\nbody\n"
    )
    assert len(analysis.title) <= 70
    assert "\n" not in analysis.title


# --- the argv for the one-shot call ------------------------------------------


def test_known_clis_get_built_in_one_shot_argv() -> None:
    claude = AgentType(name="claude", cli="claude", file="CLAUDE.md", mode="local")
    assert build_analyze_command(claude, "hello") == ["claude", "-p", "hello"]
    codex = AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local")
    assert build_analyze_command(codex, "hello") == ["codex", "exec", "hello"]


def test_configured_analyze_template_wins() -> None:
    agent = AgentType(
        name="custom",
        cli="mycli",
        file="AGENTS.md",
        mode="local",
        analyze="--batch --input {prompt}",
    )
    assert build_analyze_command(agent, "hi") == [
        "mycli",
        "--batch",
        "--input",
        "hi",
    ]


def test_unknown_cli_without_a_template_refuses_rather_than_guessing() -> None:
    """A positional fallback would open a REPL nobody can drive — the exact hang
    this loop exists to report."""
    agent = AgentType(name="weird", cli="weirdcli", file="AGENTS.md", mode="local")
    with pytest.raises(autofix.AutofixUnavailable) as exc:
        build_analyze_command(agent, "hi")
    assert "analyze" in str(exc.value)


# --- the run record ------------------------------------------------------------


def _record() -> RunRecord:
    record = RunRecord(started=datetime(2026, 8, 24, 9, 0, 0), repo="coga")
    record.scan_lines = ["digest              ready (Mon 09:00)      launch"]
    record.add(
        TaskOutcome(
            template="digest",
            slug="recurring/digest",
            result="failed",
            exit_code=1,
            final_status="in_progress",
            blackboard="## Digest\n\nTraceback...\nZoneInfoNotFoundError\n",
        )
    )
    record.add(
        TaskOutcome(
            template="dream",
            slug="recurring/dream",
            result="completed",
            final_status="done",
        )
    )
    return record


def test_record_renders_outcomes_and_flags_problems() -> None:
    record = _record()
    assert [o.slug for o in record.problems] == ["recurring/digest"]
    text = record.render()
    assert "recurring/digest — failed" in text
    assert "exit code: 1" in text
    assert "ZoneInfoNotFoundError" in text
    assert "recurring/dream — completed" in text


def test_record_strips_ansi_and_keeps_the_tail_of_a_long_blackboard() -> None:
    record = RunRecord(started=datetime(2026, 8, 24, 9, 0, 0))
    record.add(
        TaskOutcome(
            template="noisy",
            slug="recurring/noisy",
            result="failed",
            exit_code=2,
            blackboard=(
                "\x1b[31m" + ("filler line\n" * 5000) + "the real error\x1b[0m\n"
            ),
        )
    )
    text = record.render()
    assert "\x1b[" not in text
    assert "the real error" in text
    assert "truncated" in text


def test_an_on_demand_run_is_not_labelled_a_sweep() -> None:
    """`coga dream` runs one template; calling that a sweep that scanned
    nothing would mislead the analyst about what it is reading."""
    record = RunRecord(
        started=datetime(2026, 8, 24, 9, 0, 0), repo="coga", on_demand="dream"
    )
    record.add(
        TaskOutcome(template="dream", slug="recurring/dream", result="completed")
    )
    text = record.render()
    assert "# Recurring launch: dream" in text
    assert "on-demand `coga recurring launch dream`" in text
    assert "templates scanned" not in text


def test_prompt_lists_open_autofix_tickets_for_dedupe() -> None:
    prompt = build_prompt(
        "run record here",
        [("autofix/digest-tz", "Fix the digest timezone", "active")],
    )
    assert "run record here" in prompt
    assert "autofix/digest-tz" in prompt
    assert "VERDICT:" in prompt


# --- reading what a run reported ----------------------------------------------


def test_blackboard_is_read_from_the_period_task(cfg_repo) -> None:
    """The record reads the run's own report channel, not console bytes."""
    from coga.create import create_task
    from coga.tasks import resolve_task

    created = create_task(
        cfg=cfg_repo,
        title="Period task",
        workflow_name=None,
        contexts=[],
        owner="tester",
        assignee=None,
        watchers=[],
        status="draft",
    )
    ref = resolve_task(cfg_repo, created["slug"])
    ticket = ref.ticket_path.read_text()
    ref.ticket_path.write_text(ticket + "\nvalidate-drift found 3 broken refs.\n")

    assert "validate-drift found 3 broken refs." in blackboard_for_ref(ref)


def test_a_missing_or_reaped_task_still_leaves_an_outcome(cfg_repo) -> None:
    """A run worth analyzing must not be lost because its ticket went away."""
    assert blackboard_for_ref(None) == ""

    from coga.tasks import TaskRef

    gone = TaskRef(
        slug="ghost",
        path=cfg_repo.repo_root / "tasks" / "ghost",
        directory=None,
    )
    assert blackboard_for_ref(gone) == ""


# --- classifying one task's run -----------------------------------------------


def _ref_with_status(cfg, status: str):  # type: ignore[no-untyped-def]
    from coga.create import create_task
    from coga.tasks import resolve_task
    from coga.ticket import Ticket

    created = create_task(
        cfg=cfg,
        title=f"Period {status}",
        workflow_name=None,
        contexts=[],
        owner="tester",
        assignee=None,
        watchers=[],
        status="draft",
    )
    ref = resolve_task(cfg, created["slug"])
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = status
    ticket.write(ref.ticket_path)
    return ref


def test_a_script_that_closed_its_step_is_completed_not_unfinished(cfg_repo) -> None:
    """`kind == "script"` only means the deterministic phase ended the launch.

    The ordinary success — `ticket.py` closing the step itself — comes back as
    "script" too, so reading that as a failure reported every healthy template
    as unfinished.
    """
    from coga.recurring_runner import _task_outcome

    ref = _ref_with_status(cfg_repo, "done")
    outcome = _task_outcome(cfg_repo, "nightly-check", ref, kind="script")
    assert outcome.result == "completed"
    assert not outcome.is_problem


def test_a_script_that_stopped_early_is_unfinished(cfg_repo) -> None:
    from coga.recurring_runner import _task_outcome

    ref = _ref_with_status(cfg_repo, "in_progress")
    outcome = _task_outcome(cfg_repo, "nightly-check", ref, kind="script")
    assert outcome.result == "unfinished"
    assert "before the step closed" in outcome.detail


def test_a_wedged_run_is_recorded_as_timed_out(cfg_repo) -> None:
    from coga.recurring_runner import _task_outcome

    ref = _ref_with_status(cfg_repo, "paused")
    outcome = _task_outcome(cfg_repo, "nightly-check", ref, kind="timeout")
    assert outcome.result == "timed-out"
    assert outcome.is_problem


def test_a_blocked_script_phase_names_the_script(cfg_repo) -> None:
    from coga.recurring_runner import _task_outcome

    ref = _ref_with_status(cfg_repo, "blocked")
    outcome = _task_outcome(cfg_repo, "nightly-check", ref, kind="script")
    assert outcome.result == "unfinished"
    assert "`ticket.py` phase recorded a blocker" in outcome.detail


def test_the_outcome_carries_the_run_blackboard(cfg_repo) -> None:
    from coga.recurring_runner import _task_outcome

    ref = _ref_with_status(cfg_repo, "done")
    ref.ticket_path.write_text(
        ref.ticket_path.read_text() + "\nvalidate-drift found 3 broken refs.\n"
    )
    outcome = _task_outcome(cfg_repo, "nightly-check", ref, kind="script")
    assert "validate-drift found 3 broken refs." in outcome.blackboard


# --- the loop end to end -------------------------------------------------------


@pytest.fixture
def cfg_repo(repo: Path):  # noqa: F811 — the shared recurring fixture
    return load_config(repo)


def _fake_agent_reply(
    monkeypatch, reply: str, *, returncode: int = 0
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode, reply, "")

    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")
    return calls


def test_run_autofix_creates_an_active_ticket_in_the_autofix_directory(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    calls = _fake_agent_reply(
        monkeypatch,
        "VERDICT: problem\n"
        "TITLE: Fix the digest recipe timezone crash\n"
        "---\n"
        "`digest` exited 1 with ZoneInfoNotFoundError.\n",
    )
    posts: list[str] = []
    monkeypatch.setattr(autofix, "post", lambda cfg, msg, **kw: posts.append(msg))

    autofix.run_autofix(cfg_repo, _record())

    assert len(calls) == 1
    task_dir = cfg_repo.repo_root / "tasks" / "autofix"
    created = list(task_dir.iterdir())
    assert len(created) == 1
    ticket = (created[0] / "ticket.md").read_text()
    assert "status: active" in ticket
    assert "Fix the digest recipe timezone crash" in ticket
    assert "code/with-self-review" in ticket
    # The run that produced the finding travels with the ticket.
    assert "ZoneInfoNotFoundError" in (created[0] / "run-log.md").read_text()
    assert posts and "autofix created" in posts[0]


def test_run_autofix_creates_nothing_on_an_ok_verdict(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    _fake_agent_reply(monkeypatch, "VERDICT: ok\n")
    autofix.run_autofix(cfg_repo, _record())
    assert not (cfg_repo.repo_root / "tasks" / "autofix").exists()


def test_run_autofix_creates_nothing_for_an_already_ticketed_problem(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    _fake_agent_reply(
        monkeypatch, "VERDICT: duplicate\nDUPLICATE: autofix/digest-tz\n"
    )
    autofix.run_autofix(cfg_repo, _record())
    assert not (cfg_repo.repo_root / "tasks" / "autofix").exists()


def test_a_failing_analyst_never_breaks_the_sweep(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled, capfd
) -> None:
    _fake_agent_reply(monkeypatch, "", returncode=1)
    autofix.run_autofix(cfg_repo, _record())  # must not raise
    assert "analysis skipped" in capfd.readouterr().err
    assert not (cfg_repo.repo_root / "tasks" / "autofix").exists()


def test_a_hung_analyst_is_bounded_by_a_timeout(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled, capfd
) -> None:
    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout") or 300)

    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")
    autofix.run_autofix(cfg_repo, _record())
    assert "did not answer within" in capfd.readouterr().err


def test_env_switch_disables_the_loop(
    cfg_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COGA_AUTOFIX", "0")

    def unreachable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("the disabled loop ran an analysis")

    monkeypatch.setattr(autofix, "analyze_record", unreachable)
    autofix.run_autofix(cfg_repo, _record())


def test_an_empty_record_is_not_worth_a_call(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    """An early refusal never scanned anything; there is no run to analyze."""

    def unreachable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("analyzed a sweep that never ran")

    monkeypatch.setattr(autofix, "analyze_record", unreachable)
    autofix.run_autofix(cfg_repo, RunRecord(started=datetime(2026, 8, 24, 9, 0)))


def test_the_run_log_is_written_machine_locally_even_without_a_ticket(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    _fake_agent_reply(monkeypatch, "VERDICT: ok\n")
    autofix.run_autofix(cfg_repo, _record())
    logs = list((cfg_repo.repo_root / ".coga" / "recurring-runs").glob("*.md"))
    assert len(logs) == 1
    assert "ZoneInfoNotFoundError" in logs[0].read_text()


# --- the on-demand entry point -------------------------------------------------


def test_on_demand_launch_closes_the_same_loop(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    """`coga recurring launch <name>` — and so `coga dream` — analyzes its run.

    It creates and launches a real template, so a wedge or a failed
    `ticket.py` there is exactly as worth ticketing as one in the sweep.
    """
    from coga import recurring_runner

    from coga.ticket import Ticket

    ref = _ref_with_status(cfg_repo, "active")

    def finishing_launch(slug, **kwargs):  # type: ignore[no-untyped-def]
        ticket = Ticket.read(ref.ticket_path)
        ticket.frontmatter["status"] = "done"
        ticket.write(ref.ticket_path)
        return None

    monkeypatch.setattr("coga.commands.launch.launch", finishing_launch)

    record = RunRecord(started=datetime(2026, 8, 24, 9, 0))
    code = recurring_runner._launch_created(
        cfg_repo, ref, record=record, template="nightly-check"
    )

    assert code == 0
    assert [o.result for o in record.outcomes] == ["completed"]
    assert record.outcomes[0].template == "nightly-check"


def test_a_refused_on_demand_launch_is_not_a_run(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    """A paused or closed template never launched, so there is nothing to analyze."""
    from coga import recurring_runner

    monkeypatch.setattr(
        "coga.commands.launch.launch",
        lambda slug, **kwargs: pytest.fail("launched a parked template"),
    )

    ref = _ref_with_status(cfg_repo, "paused")
    record = RunRecord(started=datetime(2026, 8, 24, 9, 0))
    assert recurring_runner._launch_created(cfg_repo, ref, record=record) == 0
    assert record.outcomes == []


# --- the recipe surface --------------------------------------------------------


def test_recipe_analyzes_the_latest_run_log_by_default(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    runs = cfg_repo.repo_root / ".coga" / "recurring-runs"
    runs.mkdir(parents=True)
    (runs / "20260101T000000.md").write_text("older run\n")
    (runs / "20260824T090000.md").write_text("digest exited 1\n")
    calls = _fake_agent_reply(monkeypatch, "VERDICT: ok\n")

    from coga.runner import run_recipe

    assert run_recipe(cfg_repo, "autofix-analyze", []) == 0
    assert "digest exited 1" in calls[0][-1]


def test_recipe_dry_run_reports_without_creating_a_ticket(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled, capfd
) -> None:
    log = cfg_repo.repo_root / ".coga" / "recurring-runs" / "run.md"
    log.parent.mkdir(parents=True)
    log.write_text("digest exited 1\n")
    _fake_agent_reply(
        monkeypatch,
        "VERDICT: problem\nTITLE: Fix digest\n---\nIt crashed.\n",
    )

    from coga.runner import run_recipe

    assert run_recipe(cfg_repo, "autofix-analyze", [str(log), "--dry-run"]) == 0
    assert "Fix digest" in capfd.readouterr().out
    assert not (cfg_repo.repo_root / "tasks" / "autofix").exists()


def test_recipe_fails_loud_with_no_run_log(cfg_repo, autofix_enabled) -> None:
    from coga.runner import run_recipe

    assert run_recipe(cfg_repo, "autofix-analyze", []) == 2
