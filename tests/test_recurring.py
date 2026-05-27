from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.recurring import scaffold_named, scan_due
from relay.tasks import list_tasks
from relay.ticket import Ticket


SHIPPED_DREAM_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "recurring"
    / "dream"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_recurring(company: Path, name: str, text: str) -> None:
    """Write a recurring task as a ticket-format directory."""
    _write(company / "recurring" / name / "ticket.md", text)


def _seed_period_task_context(company: Path) -> None:
    """Seed the auto-attached `relay/period-task` context.

    The scaffolder appends `relay/period-task` to every period task's
    `contexts:`, so the test repo needs a resolvable context file or
    `scaffold_task` rejects the unknown ref.
    """
    _write(
        company / "contexts" / "relay" / "period-task" / "SKILL.md",
        """
        ---
        name: relay/period-task
        description: stub
        ---

        # Period task
        """,
    )


@pytest.fixture
def repo(tmp_path: Path):
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _seed_period_task_context(company)
    _write_recurring(
        company,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the full deliverability diagnostic suite.
        """,
    )
    return company


# --- scan_due: the bare `relay recurring` library layer -----------------------


def test_scan_due_creates_task(repo: Path) -> None:
    cfg = load_config(repo)
    fixed_now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am
    scan = scan_due(cfg, now=fixed_now)
    assert scan.errors == []
    assert len(scan.tasks) == 1
    task = scan.tasks[0]
    assert task.created is True
    assert task.launchable is True  # scaffolds straight to `active`
    assert task in scan.due

    ticket = Ticket.read(task.ref.path / "ticket.md")
    assert ticket.title == "Weekly deliverability check"
    assert ticket.mode == "interactive"
    assert ticket.owner == "marc"
    # Period key for weekly = ISO week of the firing (Mon 2026-04-20, ISO week 17)
    assert task.ref.slug.endswith("-2026-W17")
    body = (task.ref.path / "ticket.md").read_text()
    assert "Run the full deliverability diagnostic suite" in body


def test_scaffold_auto_attaches_period_task_context(repo: Path) -> None:
    """Every period task gets `relay/period-task` appended to its contexts.

    The recurring template above declares no contexts; after scaffolding, the
    period task should carry exactly `["relay/period-task"]`. This is what
    teaches the launched run that persistent state lives in the parent
    recurring task's blackboard, not the per-period one.
    """
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ticket = Ticket.read(scan.tasks[0].ref.path / "ticket.md")
    assert ticket.contexts == ["relay/period-task"]


def test_scaffold_does_not_duplicate_explicit_period_task_context(
    repo: Path,
) -> None:
    """A recurring task that already lists `relay/period-task` doesn't get
    it appended again — the append is idempotent."""
    _write_recurring(
        repo,
        "explicit-period",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Already lists period-task"
        mode: interactive
        assignee: claude
        owner: marc
        contexts:
          - relay/period-task
        ---

        ## Description

        Body.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    task = next(t for t in scan.tasks if t.template == "explicit-period")
    ticket = Ticket.read(task.ref.path / "ticket.md")
    assert ticket.contexts == ["relay/period-task"]


def test_scan_due_idempotent(repo: Path) -> None:
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    second = scan_due(cfg, now=now)
    assert first.tasks[0].created is True
    # Same period: the task already exists, so it is found, not recreated.
    assert second.tasks[0].created is False
    assert len(list_tasks(cfg)) == 1


def test_scan_due_different_period_creates_new(repo: Path) -> None:
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    ticket = Ticket.read(first.tasks[0].ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(first.tasks[0].ref.path / "ticket.md")

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18
    assert scan.tasks[0].created is True
    assert scan.tasks[0].ref.slug.endswith("-2026-W18")
    assert len(list_tasks(cfg)) == 2


def test_scan_due_scaffolds_new_period_despite_stuck_prior_run(
    repo: Path,
) -> None:
    """A stuck prior-period `in_progress` task does not block the new period.

    The stuck run stays visible in `relay status` for the human to handle;
    today's scheduled task scaffolds and launches normally. Silently skipping
    today's task because a 4-day-old run never finished is exactly the
    "silent wrong answer" failure mode the principles forbid.
    """
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    ref = first.tasks[0].ref
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.path / "ticket.md")

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18

    assert scan.errors == []
    assert len(scan.tasks) == 1
    assert scan.tasks[0].created is True
    assert scan.tasks[0].launchable is True
    assert scan.tasks[0].ref.slug.endswith("-2026-W18")
    # Both the stuck prior run and the new period task exist.
    assert {ref.slug for ref in list_tasks(cfg)} == {
        "weekly-check-2026-W17",
        "weekly-check-2026-W18",
    }


def test_scan_due_does_not_rescaffold_after_period_task_deleted(
    repo: Path,
) -> None:
    """A completed-this-period task that has been deleted stays completed.

    Dream's contract is to self-delete after `relay mark done`; a human
    `relay delete` is the other case. The recurring template's
    `blackboard.md` is the period ledger — `scan_due` reads it instead of
    just checking for the task directory, so a successful run isn't
    silently re-launched by the next `relay recurring`.
    """
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am

    first = scan_due(cfg, now=now)
    assert first.tasks[0].created is True
    ref = first.tasks[0].ref

    # The ledger line lands in the template's persistent blackboard.md,
    # not in a separate log.md.
    bb = (repo / "recurring" / "weekly-check" / "blackboard.md").read_text()
    assert f"scaffolded {ref.slug}" in bb

    # Simulate the run completing and deleting itself.
    shutil.rmtree(ref.path)

    second = scan_due(cfg, now=now)
    assert second.errors == []
    assert len(second.tasks) == 1
    completed = second.tasks[0]
    assert completed.created is False
    assert completed.launchable is False
    assert completed.ref is None
    assert second.due == []
    # The directory stays gone — no re-scaffold.
    assert list_tasks(cfg) == []


def test_scan_due_skips_bad_template(repo: Path, capsys) -> None:
    _write(repo / "recurring" / "bad" / "ticket.md", "no frontmatter here\n")
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1  # good one still created
    assert len(scan.errors) == 1
    assert scan.errors[0][0] == "bad"
    assert "skipping bad" in capsys.readouterr().err


def test_scan_due_flags_legacy_md_file(repo: Path, capsys) -> None:
    """A leftover single-file `<name>.md` is flagged, not silently ignored."""
    _write(
        repo / "recurring" / "legacy.md",
        '---\nschedule: "0 9 * * 1"\n---\n',
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1  # the real directory still scaffolds
    assert scan.errors[0][0] == "legacy.md"
    assert "legacy single-file" in scan.errors[0][1]
    assert "skipping legacy.md" in capsys.readouterr().err


def test_scan_due_skips_auto_mode_template(repo: Path, capsys) -> None:
    """`mode: auto` templates are temporarily skipped with a Slack-visible error.

    Auto runs buffer stdout until completion, so a scheduled run produces no
    live console signal. Until streaming lands, `scan_due` refuses to scaffold
    these — the error lands in `DueScan.errors` and `relay recurring` fires
    its existing Slack scan-error summary.
    """
    _write_recurring(
        repo,
        "daily-auto",
        """
        ---
        schedule: "0 9 * * *"
        title: "Daily auto"
        mode: auto
        assignee: claude
        owner: marc
        ---

        ## Description

        Auto.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    # The good interactive template still scaffolds.
    assert len(scan.tasks) == 1
    assert scan.tasks[0].template == "weekly-check"
    # The auto template is skipped via scan.errors.
    assert len(scan.errors) == 1
    assert scan.errors[0][0] == "daily-auto"
    assert "mode=auto is temporarily disabled" in scan.errors[0][1]
    assert "skipping daily-auto" in capsys.readouterr().err


def test_scan_due_template_without_explicit_mode_is_skipped(
    repo: Path, capsys
) -> None:
    """A template without `mode:` defaults to auto and is skipped while
    auto is disabled."""
    _write_recurring(
        repo,
        "no-mode",
        """
        ---
        schedule: "0 9 * * *"
        title: "No mode"
        assignee: claude
        owner: marc
        ---

        ## Description

        Legacy template.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1
    assert scan.tasks[0].template == "weekly-check"
    assert len(scan.errors) == 1
    assert scan.errors[0][0] == "no-mode"
    assert "mode=auto is temporarily disabled" in scan.errors[0][1]


def test_scan_due_skips_underscore_template(repo: Path, capsys) -> None:
    # `_template/` is a scaffold, not a live recurring task — must be ignored
    # silently (no stderr complaint) even though its placeholder fields wouldn't
    # validate.
    _write_recurring(
        repo,
        "_template",
        """
        ---
        schedule: "0 9 * * 1"
        title: placeholder
        ---
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1  # only the real one
    assert scan.errors == []
    assert "_template" not in capsys.readouterr().err


def test_scan_due_excludes_handled_task(repo: Path) -> None:
    """A task already past `active` is not relaunched — it drops out of `.due`."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    task = first.tasks[0]

    # Simulate the task having been picked up / finished.
    ticket = Ticket.read(task.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(task.ref.path / "ticket.md")

    second = scan_due(cfg, now=now)
    assert second.tasks[0].status == "done"
    assert second.tasks[0].launchable is False
    assert second.due == []


# --- relay recurring launch / the `dream` alias path --------------------------


@pytest.fixture
def dream_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo carrying the real shipped `recurring/dream/` recurring task.

    `relay recurring launch` and a bare `relay recurring` are the two entry
    points into the same scaffold path; these tests prove they converge.
    """
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _seed_period_task_context(company)
    (company / "tasks").mkdir(parents=True)
    (company / "recurring").mkdir(parents=True)
    shutil.copytree(SHIPPED_DREAM_DIR, company / "recurring" / "dream")
    monkeypatch.chdir(company)
    return company


def test_recurring_launch_creates_dream_task(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert "Created dream-" in result.output

    cfg = load_config(dream_repo)
    refs = list_tasks(cfg)
    assert len(refs) == 1
    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.title == "Dream"
    assert ticket.mode == "interactive"
    assert ticket.workflow is None
    # The recurring template's `## Description` body composes into the ticket.
    assert "Run the Dream cleanup pass for this Relay repo." in ticket.body
    # Slug uses the schedule-derived period key, not plain `dream`.
    assert refs[0].slug.startswith("dream-")
    assert refs[0].slug != "dream"


def test_recurring_launch_defaults_assignee_to_default_agent(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workflow-less recurring task (Dream) with no template `assignee:`
    defaults to the repo's default agent, not the human owner — otherwise
    `relay launch` cannot resolve the assignee to an agent type."""
    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    CliRunner().invoke(app, ["recurring", "launch", "dream"])

    cfg = load_config(dream_repo)
    refs = list_tasks(cfg)
    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.workflow is None
    assert ticket.assignee == "claude"


def test_recurring_launch_is_idempotent(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    runner = CliRunner()
    first = runner.invoke(app, ["recurring", "launch", "dream"])
    second = runner.invoke(app, ["recurring", "launch", "dream"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert "Created dream-" in first.output
    assert "already scaffolded for this period" in second.output
    # Idempotent: one task directory, not two.
    assert len(list_tasks(load_config(dream_repo))) == 1


def test_recurring_launch_and_scan_converge(dream_repo: Path) -> None:
    """A manual `launch dream` and a bare `relay recurring` produce one dir."""
    cfg = load_config(dream_repo)
    now = datetime(2026, 5, 20, 10, 0, 0)  # a Wednesday

    manual = scaffold_named(cfg, "dream", now=now)
    assert manual.created is True

    # The bare-recurring scan, same period, sees the task already exists.
    scan = scan_due(cfg, now=now)
    assert [t.created for t in scan.tasks] == [False]
    assert scan.errors == []
    assert len(list_tasks(cfg)) == 1


def test_recurring_launch_unknown_template_fails(dream_repo: Path) -> None:
    result = CliRunner().invoke(app, ["recurring", "launch", "nope"])
    assert result.exit_code == 2
    assert "no recurring task `recurring/nope/`" in result.output


def test_recurring_launch_invokes_launch(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay recurring launch` hands the scaffolded `active` task to launch."""
    calls: list[str] = []

    def fake_launch(
        task: str,
        agent_override: str | None,
        prompt_report: bool,
        no_verify: bool,
        mode_override: str | None = None,
    ) -> None:
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        assert ticket.status == "active"
        calls.append(task)

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls[0].startswith("dream-")


def test_recurring_launch_interactive_overrides_mode(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay recurring launch <name> --interactive` threads mode_override."""
    seen: list[str | None] = []
    monkeypatch.setattr(
        "relay.commands.launch.launch",
        lambda task, **k: seen.append(k.get("mode_override")),
    )

    result = CliRunner().invoke(
        app, ["recurring", "launch", "dream", "--interactive"]
    )

    assert result.exit_code == 0, result.output
    assert seen == ["interactive"]


def test_bare_recurring_scans_and_launches_due(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare `relay recurring` scaffolds the due task and launches it."""
    calls: list[str] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(dream_repo / "tasks" / task / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert "Recurring scan" in result.output
    assert len(calls) == 1
    assert calls[0].startswith("dream-")


def test_bare_recurring_continues_past_unfinished_interactive_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interactive templates do not gate the sweep on `status: done`.

    The human is driving — exiting the agent without marking done is a
    "move on" signal, not a stuck task. The sweep prints a note and
    proceeds to the next due task.
    """
    _write_recurring(
        repo,
        "z-weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Second weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the second diagnostic suite.
        """,
    )
    monkeypatch.chdir(repo)
    calls: list[str] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "in_progress"
        ticket.write(repo / "tasks" / task / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 2
    assert calls[0].startswith("weekly-check-")
    assert calls[1].startswith("z-weekly-check-")
    assert "continuing to next due task (interactive)" in result.output


def test_bare_recurring_stops_before_next_due_task_if_script_unfinished(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-interactive (script/auto) templates still gate the sweep on done.

    Unattended runs can't be redirected by a human at the terminal, so a
    launched-but-unfinished task is a stuck task and stops the sweep.
    """
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _seed_period_task_context(company)
    _write_recurring(
        company,
        "nightly-check",
        """
        ---
        schedule: "0 9 * * *"
        title: "Nightly diagnostic"
        mode: script
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the nightly diagnostic suite.
        """,
    )
    _write_recurring(
        company,
        "z-nightly-check",
        """
        ---
        schedule: "0 9 * * *"
        title: "Second nightly check"
        mode: script
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the second nightly diagnostic suite.
        """,
    )
    monkeypatch.chdir(company)
    calls: list[str] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(company / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "in_progress"
        ticket.write(company / "tasks" / task / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 1, result.output
    assert len(calls) == 1
    assert calls[0].startswith("nightly-check-")
    combined = result.output + (result.stderr or "")
    assert "stopping before the next due task" in combined


def test_bare_recurring_interactive_overrides_mode(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay recurring --interactive` threads mode_override to each launch."""
    seen: list[str | None] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append(kwargs.get("mode_override"))
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(dream_repo / "tasks" / task / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring", "--interactive"])

    assert result.exit_code == 0, result.output
    assert seen == ["interactive"]


def test_bare_recurring_defaults_to_no_mode_override(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --interactive the ticket's own `mode:` is left to win."""
    seen: list[str | None] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append(kwargs.get("mode_override"))
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(dream_repo / "tasks" / task / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert seen == [None]


def test_bare_recurring_nothing_due(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second bare run in the same period — the task is in_progress/done — is a no-op."""
    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    runner = CliRunner()
    runner.invoke(app, ["recurring"])  # scaffolds + "launches" (no-op stub)

    # Mark the scaffolded task done so it is no longer launchable.
    cfg = load_config(dream_repo)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")

    result = runner.invoke(app, ["recurring"])
    assert result.exit_code == 0, result.output
    assert "No recurring tasks due." in result.output
