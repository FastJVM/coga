"""Tests for the recurring sweep's autofix loop (`coga/recurring_autofix.py`)."""

from __future__ import annotations

import subprocess
from dataclasses import replace
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

from tests.test_recurring import (  # noqa: F401 — shared repo fixture
    _write_recurring,
    repo,
)


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
    message = str(exc.value)
    assert "analyze" in message
    assert "coga.toml or coga.local.toml" in message


def test_a_working_claude_api_key_is_used_without_an_auth_probe(
    cfg_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "working-key")
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append((cmd, kwargs["env"]))
        return subprocess.CompletedProcess(
            cmd,
            0,
            "VERDICT: problem\n"
            "TITLE: Fix the exhausted downstream key\n"
            "---\n"
            "The run reported: Credit balance is too low.\n",
            "",
        )

    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")

    assert autofix.analyze_record(cfg_repo, "failing run").verdict == "problem"
    assert len(calls) == 1
    assert calls[0][1]["ANTHROPIC_API_KEY"] == "working-key"


def test_claude_billing_failure_retries_with_a_verified_subscription(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, capfd
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "out-of-credit-key")
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_CUSTOM_HEADERS", raising=False)
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        env = kwargs["env"]
        calls.append((cmd, env))
        if cmd[1:] == ["auth", "status"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                '{"loggedIn":true,"authMethod":"claude.ai",'
                '"apiProvider":"firstParty","subscriptionType":"max",'
                '"forcedLoginMethod":"claudeai"}',
                "",
            )
        analysis_attempt = sum(
            previous[0][1:] != ["auth", "status"] for previous in calls
        )
        if analysis_attempt == 1:
            return subprocess.CompletedProcess(
                cmd, 1, "Credit balance is too low", ""
            )
        return subprocess.CompletedProcess(cmd, 0, "VERDICT: ok\n", "")

    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")

    assert autofix.analyze_record(cfg_repo, "healthy run").verdict == "ok"
    assert [cmd[1:] == ["auth", "status"] for cmd, _env in calls] == [
        False,
        True,
        False,
    ]
    assert calls[0][1]["ANTHROPIC_API_KEY"] == "out-of-credit-key"
    assert "ANTHROPIC_API_KEY" not in calls[1][1]
    assert "ANTHROPIC_API_KEY" not in calls[2][1]
    assert "retrying with the signed-in claude.ai subscription" in (
        capfd.readouterr().err
    )


@pytest.mark.parametrize(
    "status_payload",
    (
        '{"loggedIn":false,"authMethod":"none"}',
        '{"loggedIn":true,"authMethod":"claude.ai",'
        '"subscriptionType":null}',
        '{"loggedIn":true,"authMethod":"claude.ai",'
        '"subscriptionType":"max","forcedLoginMethod":"console"}',
        '{"loggedIn":true,"authMethod":"claude.ai",'
        '"subscriptionType":"max","apiKeySource":"apiKeyHelper"}',
    ),
    ids=("signed-out", "no-entitlement", "forced-console", "other-api-key"),
)
def test_claude_api_key_failure_stays_loud_without_a_usable_subscription(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, status_payload: str
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "out-of-credit-key")
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_CUSTOM_HEADERS", raising=False)
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        if cmd[1:] == ["auth", "status"]:
            return subprocess.CompletedProcess(cmd, 0, status_payload, "")
        return subprocess.CompletedProcess(cmd, 1, "Credit balance is too low", "")

    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")

    with pytest.raises(autofix.AutofixUnavailable, match="Credit balance"):
        autofix.analyze_record(cfg_repo, "healthy run")
    assert [cmd[1:] == ["auth", "status"] for cmd in calls] == [False, True]


def test_a_custom_claude_analyze_argv_never_switches_authentication(
    cfg_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "out-of-credit-key")
    cfg_repo.agents["claude"] = replace(
        cfg_repo.agents["claude"],
        analyze="--settings analyst-settings.json -p {prompt}",
    )
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "Credit balance is too low", "")

    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")

    with pytest.raises(autofix.AutofixUnavailable, match="Credit balance"):
        autofix.analyze_record(cfg_repo, "healthy run")
    assert len(calls) == 1
    assert "--settings" in calls[0]


@pytest.mark.parametrize(
    "routing_env", ("ANTHROPIC_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS")
)
def test_custom_claude_auth_routing_never_switches_authentication(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, routing_env: str
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "out-of-credit-key")
    monkeypatch.setenv(routing_env, "configured")
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "Credit balance is too low", "")

    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")

    with pytest.raises(autofix.AutofixUnavailable, match="Credit balance"):
        autofix.analyze_record(cfg_repo, "healthy run")
    assert len(calls) == 1


def test_an_unrelated_claude_failure_never_switches_authentication(
    cfg_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "configured-key")
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "network unavailable", "")

    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")

    with pytest.raises(autofix.AutofixUnavailable, match="network unavailable"):
        autofix.analyze_record(cfg_repo, "healthy run")
    assert len(calls) == 1


# --- one timeout budget across the fallback -----------------------------------
#
# `COGA_AUTOFIX_TIMEOUT` is documented as the bound on the analysis call, so the
# retry path must not be able to double it (or add the auth probe on top). These
# drive a fake clock so the assertions are on the timeouts actually handed to
# each subprocess rather than on wall time.


class _FakeClock:
    """A `time` stand-in whose monotonic reading only moves when told to."""

    def __init__(self) -> None:
        self.now = 1_000.0

    def monotonic(self) -> float:
        return self.now


def _auth_fallback_calls(
    monkeypatch: pytest.MonkeyPatch,
    *,
    spend: dict[str, float],
    retry_returncode: int = 0,
    retry_stdout: str = "VERDICT: ok\n",
) -> tuple[_FakeClock, list[tuple[list[str], float | None]]]:
    """Fake a failing API-key call, an entitled auth probe, and the retry.

    `spend` says how many seconds each leg burns off the clock, keyed
    `first` / `probe` / `retry`. Returns the clock plus every `(cmd, timeout)`
    the module asked `subprocess.run` for.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "out-of-credit-key")
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_CUSTOM_HEADERS", raising=False)
    clock = _FakeClock()
    seen: list[tuple[list[str], float | None]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        timeout = kwargs.get("timeout")
        seen.append((cmd, timeout))
        if cmd[1:] == ["auth", "status"]:
            clock.now += spend.get("probe", 0.0)
            return subprocess.CompletedProcess(
                cmd,
                0,
                '{"loggedIn":true,"authMethod":"claude.ai",'
                '"apiProvider":"firstParty","subscriptionType":"max",'
                '"forcedLoginMethod":"claudeai"}',
                "",
            )
        analyses = sum(1 for prev, _t in seen if prev[1:] != ["auth", "status"])
        if analyses == 1:
            clock.now += spend.get("first", 0.0)
            return subprocess.CompletedProcess(
                cmd, 1, "Credit balance is too low", ""
            )
        clock.now += spend.get("retry", 0.0)
        if retry_returncode:
            raise subprocess.TimeoutExpired(cmd, timeout or 0.0)
        return subprocess.CompletedProcess(cmd, retry_returncode, retry_stdout, "")

    monkeypatch.setattr(autofix, "time", clock)
    monkeypatch.setattr(autofix.subprocess, "run", fake_run)
    monkeypatch.setattr(autofix.shutil, "which", lambda _cli: "/usr/bin/claude")
    return clock, seen


def test_the_subscription_retry_spends_the_remaining_budget_not_a_fresh_one(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, capfd
) -> None:
    """The documented bound is on the analysis, not on each subprocess in it."""
    monkeypatch.setenv("COGA_AUTOFIX_TIMEOUT", "100")
    _clock, seen = _auth_fallback_calls(
        monkeypatch, spend={"first": 95.0, "probe": 2.0}
    )

    assert autofix.analyze_record(cfg_repo, "failing run").verdict == "ok"
    first, probe, retry = seen
    assert first[1] == pytest.approx(100.0)
    # Only 5s of the budget is left, so the deadline beats the 10s probe cap...
    assert probe[1] == pytest.approx(5.0)
    # ...and the retry gets what the probe left, not a second full budget.
    assert retry[1] == pytest.approx(3.0)
    assert retry[1] < 100.0


def test_the_auth_probe_keeps_its_own_cap_inside_a_large_budget(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, capfd
) -> None:
    """A hung status call must not eat the budget the retry still needs."""
    monkeypatch.setenv("COGA_AUTOFIX_TIMEOUT", "300")
    _clock, seen = _auth_fallback_calls(
        monkeypatch, spend={"first": 10.0, "probe": 1.0}
    )

    assert autofix.analyze_record(cfg_repo, "failing run").verdict == "ok"
    _first, probe, retry = seen
    assert probe[1] == pytest.approx(10.0)
    assert retry[1] == pytest.approx(289.0)
    capfd.readouterr()


def test_a_spent_budget_declines_the_fallback_and_keeps_the_first_failure(
    cfg_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No budget left is not a reason to start two more subprocesses."""
    monkeypatch.setenv("COGA_AUTOFIX_TIMEOUT", "30")
    _clock, seen = _auth_fallback_calls(
        monkeypatch, spend={"first": 30.0}
    )

    with pytest.raises(
        autofix.AutofixUnavailable, match="Credit balance is too low"
    ):
        autofix.analyze_record(cfg_repo, "failing run")
    assert [cmd[1:] == ["auth", "status"] for cmd, _t in seen] == [False]


def test_a_timed_out_retry_reports_the_configured_bound(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, capfd
) -> None:
    """The operator set 100s; a retry that inherited 8s did not fail 'within 8s'."""
    monkeypatch.setenv("COGA_AUTOFIX_TIMEOUT", "100")
    _clock, _seen = _auth_fallback_calls(
        monkeypatch,
        spend={"first": 90.0, "probe": 2.0},
        retry_returncode=1,
    )

    with pytest.raises(autofix.AutofixUnavailable) as exc:
        autofix.analyze_record(cfg_repo, "failing run")
    assert "did not answer within 100s" in str(exc.value)
    capfd.readouterr()


def test_a_disarmed_budget_leaves_the_whole_fallback_unbounded(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, capfd
) -> None:
    """`COGA_AUTOFIX_TIMEOUT=0` disarms the analysis; the probe keeps its cap."""
    monkeypatch.setenv("COGA_AUTOFIX_TIMEOUT", "0")
    _clock, seen = _auth_fallback_calls(
        monkeypatch, spend={"first": 5_000.0, "probe": 5.0}
    )

    assert autofix.analyze_record(cfg_repo, "failing run").verdict == "ok"
    first, probe, retry = seen
    assert first[1] is None
    assert probe[1] == pytest.approx(10.0)
    assert retry[1] is None
    capfd.readouterr()


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


# --- a firing that eats its own template --------------------------------------


def _fenced_template(repo: Path, name: str, *, description: str, notes: str) -> None:
    """A recurring template shaped the way the format requires: instructions
    above the fence, cross-run state below it."""
    _write_recurring(repo, name, f"""
        ---
        schedule: "0 8 * * 1"
        title: "{name}"
        ---

        ## Description

        {description}

        <!-- coga:blackboard -->

        ## Run Summary

        {notes}
        """)


def test_a_firing_that_rewrites_only_its_blackboard_is_clean(cfg_repo) -> None:
    """Writing cross-run state below the fence is what a firing is *supposed*
    to do, so it must not read as damage."""
    from coga.recurring_runner import _template_damage, _template_description

    _fenced_template(
        cfg_repo.repo_root, "sweeper", description="Rebase stale branches.", notes="W35."
    )
    before = _template_description(cfg_repo, "sweeper")
    _fenced_template(
        cfg_repo.repo_root, "sweeper", description="Rebase stale branches.", notes="W36."
    )

    assert before is not None
    assert _template_damage(before, _template_description(cfg_repo, "sweeper")) is None


def test_a_firing_that_overwrote_its_template_description_is_a_problem(
    cfg_repo,
) -> None:
    """The failure this guard exists for: the ticket reached `done`, so status
    alone reported the run `completed` and the sweep printed `problems: 0`."""
    from coga.recurring_runner import (
        _task_outcome,
        _template_damage,
        _template_description,
    )

    _fenced_template(
        cfg_repo.repo_root, "sweeper", description="Rebase stale branches.", notes="W35."
    )
    before = _template_description(cfg_repo, "sweeper")
    _fenced_template(
        cfg_repo.repo_root, "sweeper", description="W36 run: 5 branches.", notes="W36."
    )

    damage = _template_damage(before, _template_description(cfg_repo, "sweeper"))
    ref = _ref_with_status(cfg_repo, "done")
    outcome = _task_outcome(
        cfg_repo, "sweeper", ref, kind="script", template_damage=damage
    )

    assert outcome.final_status == "done"
    assert outcome.result == "damaged-template"
    assert outcome.is_problem
    assert "rewrote its recurring template's Description" in outcome.detail


def test_a_firing_that_ate_the_fence_names_the_composition_risk(cfg_repo) -> None:
    from coga.recurring_runner import (
        _task_outcome,
        _template_damage,
        _template_description,
    )

    _fenced_template(
        cfg_repo.repo_root, "sweeper", description="Rebase stale branches.", notes="W35."
    )
    before = _template_description(cfg_repo, "sweeper")
    _write_recurring(cfg_repo.repo_root, "sweeper", """
        ---
        schedule: "0 8 * * 1"
        title: "sweeper"
        ---

        ## Description

        W36 run: 5 branches.
        """)

    damage = _template_damage(before, _template_description(cfg_repo, "sweeper"))
    outcome = _task_outcome(
        cfg_repo,
        "sweeper",
        _ref_with_status(cfg_repo, "done"),
        kind="script",
        template_damage=damage,
    )

    assert outcome.result == "damaged-template"
    assert "compose this run's output as its instructions" in outcome.detail


def test_a_template_that_never_had_a_fence_is_not_blamed_on_this_run(
    cfg_repo,
) -> None:
    """No baseline means no verdict. A template that was already fence-less is
    `coga validate`'s `recurring-template-fence` finding, not this firing's."""
    from coga.recurring_runner import _template_damage, _template_description

    _write_recurring(cfg_repo.repo_root, "fenceless", """
        ---
        schedule: "0 8 * * 1"
        title: "fenceless"
        ---

        ## Description

        Hand-authored, predates the single-file format.
        """)

    before = _template_description(cfg_repo, "fenceless")
    assert before is None
    assert _template_damage(before, _template_description(cfg_repo, "fenceless")) is None


def test_an_unreadable_template_does_not_abort_the_sweep(cfg_repo) -> None:
    """A check that only observes must never be the thing that crashes the run.

    `Ticket.read` goes through `read_text`, so non-UTF-8 bytes raise
    `UnicodeDecodeError` — a `ValueError`, not an `OSError`.
    """
    from coga.recurring_runner import _template_description

    _fenced_template(
        cfg_repo.repo_root, "sweeper", description="Rebase stale branches.", notes="W35."
    )
    path = cfg_repo.repo_root / "recurring" / "sweeper" / "ticket.md"
    path.write_bytes(b"---\ntitle: \xff\xfe broken\n---\n")

    assert _template_description(cfg_repo, "sweeper") is None


def test_a_missing_template_directory_yields_no_baseline(cfg_repo) -> None:
    from coga.recurring_runner import _template_description

    assert _template_description(cfg_repo, "never-existed") is None


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

    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", finishing_launch
    )

    record = RunRecord(started=datetime(2026, 8, 24, 9, 0))
    code = recurring_runner._launch_created(
        cfg_repo,
        ref,
        record=record,
        template="nightly-check",
        control_remote_expected=False,
    )

    assert code == 0
    assert [o.result for o in record.outcomes] == ["completed"]
    assert record.outcomes[0].template == "nightly-check"


def test_an_on_demand_firing_that_eats_its_template_warns_without_autofix(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`coga dream` and friends fire through `_launch_created`, not the sweep.

    Dream is the actor that overwrote a template's Description in the first
    place, so the on-demand path is exactly where this must not be missed. The
    ticket still reaches `done`, and `COGA_AUTOFIX=0` must disable only the
    optional analyst — not the direct warning.
    """
    from coga import recurring_runner

    from coga.ticket import Ticket

    monkeypatch.setenv("COGA_AUTOFIX", "0")

    _fenced_template(
        cfg_repo.repo_root, "sweeper", description="Rebase stale branches.", notes="W35."
    )
    ref = _ref_with_status(cfg_repo, "active")

    def eats_its_template(slug, **kwargs):  # type: ignore[no-untyped-def]
        _fenced_template(
            cfg_repo.repo_root,
            "sweeper",
            description="W36 run: 5 branches.",
            notes="W36.",
        )
        ticket = Ticket.read(ref.ticket_path)
        ticket.frontmatter["status"] = "done"
        ticket.write(ref.ticket_path)
        return None

    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", eats_its_template
    )

    record = RunRecord(started=datetime(2026, 8, 24, 9, 0))
    assert recurring_runner._launch_created(
        cfg_repo,
        ref,
        record=record,
        template="sweeper",
        control_remote_expected=False,
    ) == 0

    assert [o.result for o in record.outcomes] == ["damaged-template"]
    assert record.outcomes[0].final_status == "done"
    assert record.problems
    warning = capsys.readouterr().err
    assert "Recurring template 'sweeper' was damaged" in warning
    assert "Repair the template from git history before another firing" in warning


def test_an_on_demand_firing_that_leaves_its_template_alone_is_clean(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    """The guard must not turn every on-demand run into a reported problem."""
    from coga import recurring_runner

    from coga.ticket import Ticket

    _fenced_template(
        cfg_repo.repo_root, "sweeper", description="Rebase stale branches.", notes="W35."
    )
    ref = _ref_with_status(cfg_repo, "active")

    def finishing_launch(slug, **kwargs):  # type: ignore[no-untyped-def]
        ticket = Ticket.read(ref.ticket_path)
        ticket.frontmatter["status"] = "done"
        ticket.write(ref.ticket_path)
        return None

    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", finishing_launch
    )

    record = RunRecord(started=datetime(2026, 8, 24, 9, 0))
    assert recurring_runner._launch_created(
        cfg_repo,
        ref,
        record=record,
        template="sweeper",
        control_remote_expected=False,
    ) == 0

    assert [o.result for o in record.outcomes] == ["completed"]
    assert not record.problems


def test_a_refused_on_demand_launch_is_not_a_run(
    cfg_repo, monkeypatch: pytest.MonkeyPatch, autofix_enabled
) -> None:
    """A paused or closed template never launched, so there is nothing to analyze."""
    from coga import recurring_runner

    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period",
        lambda slug, **kwargs: pytest.fail("launched a parked template"),
    )

    ref = _ref_with_status(cfg_repo, "paused")
    record = RunRecord(started=datetime(2026, 8, 24, 9, 0))
    assert recurring_runner._launch_created(
        cfg_repo,
        ref,
        record=record,
        control_remote_expected=False,
    ) == 0
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
