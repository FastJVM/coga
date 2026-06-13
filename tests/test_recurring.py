from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from relay.commands import recurring as recurring_cmd
from relay.cli import app
from relay.config import load_config
from relay.paths import tasks_dir
from relay.recurring import (
    is_debug_slug,
    read_last_serviced_period,
    scaffold_named,
    scan_debug,
    scan_due,
)
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


def _allow_interactive_recurring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.commands.recurring._interactive_stdio_has_tty", lambda: True
    )


@pytest.fixture
def repo(tmp_path: Path):
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
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


# --- relay recurring list: the read-only schedule view ------------------------


def test_recurring_list_is_read_only_and_shows_schedule(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    monkeypatch.setenv("COLUMNS", "200")  # avoid Rich truncating the cells
    result = CliRunner().invoke(app, ["recurring", "list"])
    assert result.exit_code == 0, result.output
    assert "weekly-check" in result.output
    assert "0 9 * * 1" in result.output  # the schedule cron
    # Listing scaffolds nothing — a view never mutates (principle 6).
    assert list_tasks(load_config(repo)) == []


def test_recurring_list_shows_picked_tasks(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    fixed_now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am
    scan_due(cfg, now=fixed_now)  # instantiate this period's task
    monkeypatch.chdir(repo)
    monkeypatch.setenv("COLUMNS", "200")
    result = CliRunner().invoke(app, ["recurring", "list"])
    assert result.exit_code == 0, result.output
    assert "Picked tasks" in result.output
    assert "recurring/weekly-check" in result.output


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
    assert task.ref.group == "recurring"
    assert task.ref.slug == "weekly-check"
    assert task.ref.id_slug == "recurring/weekly-check"
    assert task.ref.path == repo / "tasks" / "recurring" / "weekly-check"
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "blackboard.md"
    ) == "2026-W17"
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


def test_scaffold_preserves_non_description_template_sections(repo: Path) -> None:
    """Template sections beyond `## Description` survive into the period task.

    Regression: the scaffolder used to keep only the `## Description` slice, so
    a template's `## Script config` (which sets a script step's mode/sync) was
    dropped and scheduled runs silently fell back to the default mode. The full
    template body must be carried verbatim, with a `## Context` appended.
    """
    _write_recurring(
        repo,
        "script-config-template",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Has script config"
        mode: script
        assignee: claude
        owner: marc
        ---

        ## Description

        Verify daily that every row has an alert.

        ## Script config

        ```yaml
        mode: watchdog
        ```

        ## Output

        Writes one JSON summary to stdout.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    task = next(t for t in scan.tasks if t.template == "script-config-template")
    body = (task.ref.path / "ticket.md").read_text()
    assert "## Script config" in body
    assert "mode: watchdog" in body
    assert "## Output" in body
    # The canonical `## Context` section is still appended for body uniformity.
    assert "## Context" in body


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
    shutil.rmtree(first.tasks[0].ref.path)

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18
    assert scan.tasks[0].created is True
    assert scan.tasks[0].ref.id_slug == "recurring/weekly-check"
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "blackboard.md"
    ) == "2026-W18"
    assert len(list_tasks(cfg)) == 1


def test_scan_due_resumes_stuck_prior_run_instead_of_new_period(
    repo: Path,
) -> None:
    """A stuck prior-period `in_progress` run is resumed, deferring the new period.

    One live task per template: identity is the `recurring` group plus the
    template leaf slug, so a stale orphan is found and resumed (`created=False`)
    rather than a fresh current-period task scaffolded alongside it.
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
    resumed = scan.tasks[0]
    # The stale orphan is resumed, not superseded by another task dir.
    assert resumed.created is False
    assert resumed.launchable is True
    assert resumed.resuming is True
    assert resumed.ref.id_slug == ref.id_slug
    assert resumed.ref.id_slug == "recurring/weekly-check"
    # The resumed prior-period run still owns week 17. Week 18 is not marked
    # serviced until the stale run is gone and a new run is scaffolded.
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "blackboard.md"
    ) == "2026-W17"
    # Only the stuck run exists — no duplicate scaffold.
    assert {r.id_slug for r in list_tasks(cfg)} == {"recurring/weekly-check"}

    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    shutil.rmtree(ref.path)
    next_scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))
    assert next_scan.tasks[0].created is True
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "blackboard.md"
    ) == "2026-W18"


def test_scan_due_does_not_rescaffold_after_period_task_deleted(
    repo: Path,
) -> None:
    """A completed-this-period task that has been deleted stays completed.

    A later Dream retro pass deletes done recurring period tickets; a human
    `relay delete` is the other case. The recurring template's blackboard
    carries the `last_serviced_period` high-water mark, so a successful run
    isn't silently re-launched by the next `relay recurring`.
    """
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am

    first = scan_due(cfg, now=now)
    assert first.tasks[0].created is True
    ref = first.tasks[0].ref

    # The load-bearing period state lands in the template's persistent
    # blackboard, while log.md keeps append-only human history.
    log = (repo / "recurring" / "weekly-check" / "log.md").read_text()
    bb_path = repo / "recurring" / "weekly-check" / "blackboard.md"
    assert "scaffolded recurring/weekly-check for 2026-W17" in log
    assert read_last_serviced_period(bb_path) == "2026-W17"

    # Simulate the run completing and later being deleted by Dream or a human.
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


def test_due_orders_dream_last(repo: Path) -> None:
    """A bare sweep launches the cleanup template (Dream) after every other
    due template, so Dream's retro pass reaps this sweep's freshly-`done`
    period tickets instead of trailing them by a full sweep.

    Alphabetically `dream` sorts between `digest` and `weekly-summary`; the
    layered `due` key (`is_cleanup` leading) overrides that so it lands last.
    """
    # Three due weekly templates whose names bracket `dream` alphabetically.
    for name in ("digest", "dream", "weekly-summary"):
        _write_recurring(
            repo,
            name,
            f"""
            ---
            schedule: "0 9 * * 1"
            title: "{name}"
            mode: interactive
            assignee: claude
            owner: marc
            ---

            ## Description

            Run {name}.
            """,
        )

    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # Wed after Mon 9am

    order = [t.template for t in scan.due]
    assert order[-1] == "dream"
    assert set(order) == {"digest", "dream", "weekly-summary", "weekly-check"}


def test_due_resuming_orphan_runs_before_fresh_dream(repo: Path) -> None:
    """Dream-last leads the sort key, but resume-first still holds *among the
    non-cleanup templates*: a stuck `in_progress` orphan is picked up before a
    fresh Dream launch."""
    for name in ("digest", "dream"):
        _write_recurring(
            repo,
            name,
            f"""
            ---
            schedule: "0 9 * * 1"
            title: "{name}"
            mode: interactive
            assignee: claude
            owner: marc
            ---

            ## Description

            Run {name}.
            """,
        )

    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    # Strand the digest period task as a dead-sweep orphan.
    digest_ref = next(t.ref for t in first.tasks if t.template == "digest")
    ticket = Ticket.read(digest_ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(digest_ref.path / "ticket.md")

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18
    order = [t.template for t in scan.due]
    # Resumed digest orphan first; Dream still last.
    assert order[0] == "digest"
    assert order[-1] == "dream"


def test_is_debug_slug() -> None:
    """Debug runs (and their children) match; ordinary names don't."""
    # `recurring --all` throwaway run and a child task embedding its slug.
    assert is_debug_slug("weekly-summary-dbg-20260606T204523")
    assert is_debug_slug("dream-cleanup-orphan-markers-child-of-dream-dbg-20")
    # A digit must follow `-dbg-`, so an ordinary hyphenated name is spared.
    assert not is_debug_slug("fix-dbg-output")
    assert not is_debug_slug("add-retry-to-webhook")
    assert not is_debug_slug("weekly-summary-2026-W17")


def test_reap_debug_orphans_removes_only_debug_dirs(repo: Path) -> None:
    """`_reap_debug_orphans` clears `*-dbg-*` scratch a crashed sweep left behind,
    sparing real tasks and `_template` — the "take over on relaunch" guarantee."""
    from relay.commands.recurring import _reap_debug_orphans

    cfg = load_config(repo)
    tasks_root = tasks_dir(cfg)
    tasks_root.mkdir(parents=True, exist_ok=True)

    def _mk(slug: str) -> Path:
        d = tasks_root / slug
        d.mkdir(parents=True)
        (d / "ticket.md").write_text("---\ntitle: x\n---\n\nbody\n")
        return d

    orphan = _mk("digest-dbg-20260607T084314")
    other_orphan = _mk("weekly-summary-dbg-20260606T222205")
    child_orphan = _mk("dream-cleanup-child-of-dream-dbg-20260607T084314")
    real = _mk("add-retry-to-webhook")
    template = _mk("_template")

    _reap_debug_orphans(cfg)

    assert not orphan.exists()
    assert not other_orphan.exists()
    assert not child_orphan.exists()
    assert real.exists()  # real tasks untouched
    assert template.exists()  # `_template` is spared


def test_scan_due_recognizes_blackboard_high_water(repo: Path) -> None:
    """A period recorded in `last_serviced_period` is honored."""
    now = datetime(2026, 4, 22, 10, 0, 0)  # week 17
    bb = repo / "recurring" / "weekly-check" / "blackboard.md"
    bb.write_text("### State\n\nlast_serviced_period: 2026-W17\n")

    cfg = load_config(repo)
    scan = scan_due(cfg, now=now)
    assert scan.errors == []
    assert len(scan.tasks) == 1
    assert scan.tasks[0].created is False  # recognized as already handled
    assert scan.due == []
    assert list_tasks(cfg) == []  # not re-scaffolded


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


def test_scan_due_skips_interactive_template_without_tty(
    repo: Path, capsys
) -> None:
    """Unattended scans skip interactive templates before scaffolding.

    This mirrors the `mode: auto` skip path: the error lands in
    `DueScan.errors`, so `relay recurring` can post its scan-error summary and
    still continue to other due templates.
    """
    _write_recurring(
        repo,
        "z-script-check",
        """
        ---
        schedule: "0 9 * * *"
        title: "Script check"
        mode: script
        assignee: claude
        owner: marc
        ---

        ## Description

        Script.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 0, 0), allow_interactive=False
    )
    assert len(scan.tasks) == 1
    assert scan.tasks[0].template == "z-script-check"
    assert len(scan.errors) == 1
    assert scan.errors[0][0] == "weekly-check"
    assert "mode=interactive requires a TTY" in scan.errors[0][1]
    assert "skipping weekly-check" in capsys.readouterr().err


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


def test_scan_due_resumes_orphaned_in_progress_task(repo: Path) -> None:
    """An `in_progress` current-period task is a dead sweep's orphan — resume it.

    A sweep whose supervisor died mid-run (laptop sleep) leaves its in-flight
    period task frozen `in_progress`. There is no daemon and no concurrent
    sweep, so the next bare `relay recurring` re-includes it in `.due` and
    `relay launch` resumes it from its current step — rather than skipping it
    forever (the old behavior, which stranded the orphan).
    """
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    task = first.tasks[0]

    # Simulate the supervisor dying mid-run: the task is frozen `in_progress`.
    ticket = Ticket.read(task.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(task.ref.path / "ticket.md")

    second = scan_due(cfg, now=now)
    resumed = second.tasks[0]
    assert resumed.status == "in_progress"
    assert resumed.created is False  # get-or-create returned the existing dir
    assert resumed.launchable is True
    assert resumed.resuming is True
    assert resumed in second.due


def test_scan_due_skips_paused_task(repo: Path) -> None:
    """A `paused` period task stays skipped — a human deliberately parked it."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    task = first.tasks[0]

    ticket = Ticket.read(task.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "paused"
    ticket.write(task.ref.path / "ticket.md")

    second = scan_due(cfg, now=now)
    assert second.tasks[0].status == "paused"
    assert second.tasks[0].launchable is False
    assert second.tasks[0].resuming is False
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
    assert "Created recurring/dream" in result.output

    cfg = load_config(dream_repo)
    refs = list_tasks(cfg)
    assert len(refs) == 1
    assert refs[0].group == "recurring"
    assert refs[0].slug == "dream"
    assert refs[0].id_slug == "recurring/dream"
    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.title == "Dream"
    assert ticket.mode == "interactive"
    assert ticket.workflow is None
    # The recurring template's `## Description` body composes into the ticket.
    assert "Run the Dream cleanup pass for this Relay repo." in ticket.body
    # The grouped task id carries recurring identity; the period lives in the
    # recurring template blackboard, not the slug.
    assert refs[0].id_slug != "dream"
    assert read_last_serviced_period(
        dream_repo / "recurring" / "dream" / "blackboard.md"
    ) is not None


def test_recurring_launch_syncs_period_task_and_high_water(
    git_repo, monkeypatch
) -> None:
    """The git control branch gets the task dir and period high-water together.

    Dream later deletes done recurring period tickets. That deletion is
    idempotent only if another checkout can still see the advanced
    `last_serviced_period` after the task dir is gone.
    """
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    ledger_rel = "relay-os/recurring/weekly-check/log.md"
    blackboard_rel = "relay-os/recurring/weekly-check/blackboard.md"
    ticket_rel = f"relay-os/tasks/{ref.id_slug}/ticket.md"
    assert git_repo.origin_tracks(ticket_rel)
    assert git_repo.origin_tracks(ledger_rel)
    assert git_repo.origin_tracks(blackboard_rel)
    blackboard = git_repo.git("show", f"main:{blackboard_rel}", cwd=git_repo.origin)
    assert "last_serviced_period: 2026-W24" in blackboard
    ledger = git_repo.git("show", f"main:{ledger_rel}", cwd=git_repo.origin)
    assert f"scaffolded {ref.id_slug}" in ledger


def test_recurring_launch_syncs_ledger_without_debug_log_entries(
    git_repo, monkeypatch
) -> None:
    """`--all` debug audit lines stay local when the next real scaffold syncs."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    log = relay_os / "recurring" / "weekly-check" / "log.md"
    _write(log, "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    debug_line = (
        "2026-06-08 10:00 [system] debug run "
        "weekly-check-dbg-20260608T100000: completed → done\n"
    )
    log.write_text(debug_line)

    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    ledger_rel = "relay-os/recurring/weekly-check/log.md"
    ledger = git_repo.git("show", f"main:{ledger_rel}", cwd=git_repo.origin)
    assert f"scaffolded {ref.id_slug}" in ledger
    assert "-dbg-" not in ledger
    assert debug_line in log.read_text()


def test_recurring_launch_preserves_remote_ledger_entries_from_stale_branch(
    git_repo, monkeypatch
) -> None:
    """A stale checkout appends its scaffold line without replacing main's log."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    log = relay_os / "recurring" / "weekly-check" / "log.md"
    _write(
        log,
        "2026-06-01 09:00 [system] scaffolded "
        "recurring-weekly-check-2026-W23\n",
    )
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    git_repo.checkout_branch("feature/stale")
    remote_line = (
        "2026-06-08 09:00 [system] scaffolded "
        "recurring-weekly-check-2026-W22\n"
    )
    git_repo.push_competing_commit(
        "relay-os/recurring/weekly-check/log.md",
        log.read_text() + remote_line,
    )

    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    ledger_rel = "relay-os/recurring/weekly-check/log.md"
    ledger = git_repo.git("show", f"main:{ledger_rel}", cwd=git_repo.origin)
    assert remote_line in ledger
    assert f"scaffolded {ref.id_slug}" in ledger
    assert git_repo.origin_tracks(f"relay-os/tasks/{ref.id_slug}/ticket.md")


def test_recurring_launch_does_not_publish_feature_only_template_log(
    git_repo, monkeypatch
) -> None:
    """A feature-only recurring template does not become a malformed main dir."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    git_repo.git("add", "relay-os/contexts")
    git_repo.git("commit", "-m", "seed recurring context")
    git_repo.git("push", "origin", "main")

    git_repo.checkout_branch("feature/new-recurring")
    _write_recurring(
        relay_os,
        "new-weekly",
        """
        ---
        schedule: "0 9 * * 1"
        title: "New weekly"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the new weekly check.
        """,
    )
    _write(relay_os / "recurring" / "new-weekly" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "new-weekly" / "log.md", "")
    git_repo.git("add", "relay-os/recurring/new-weekly")
    git_repo.git("commit", "-m", "add new recurring template")

    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "new-weekly"])

    assert result.exit_code == 0, result.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    assert git_repo.origin_tracks(f"relay-os/tasks/{ref.id_slug}/ticket.md")
    assert not git_repo.origin_tracks("relay-os/recurring/new-weekly/log.md")
    assert not git_repo.origin_tracks("relay-os/recurring/new-weekly/ticket.md")
    local_ledger = git_repo.git("show", "HEAD:relay-os/recurring/new-weekly/log.md")
    assert f"scaffolded {ref.id_slug}" in local_ledger
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_preserves_remote_ledger_entries_on_stale_main(
    git_repo, monkeypatch
) -> None:
    """A local control branch behind origin rebases cleanly and preserves logs."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    log = relay_os / "recurring" / "weekly-check" / "log.md"
    _write(
        log,
        "2026-06-01 09:00 [system] scaffolded "
        "recurring-weekly-check-2026-W23\n",
    )
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    remote_line = (
        "2026-06-08 09:00 [system] scaffolded "
        "recurring-weekly-check-2026-W22\n"
    )
    git_repo.push_competing_commit(
        "relay-os/recurring/weekly-check/log.md",
        log.read_text() + remote_line,
    )

    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    ledger_rel = "relay-os/recurring/weekly-check/log.md"
    ledger = git_repo.git("show", f"main:{ledger_rel}", cwd=git_repo.origin)
    assert remote_line in ledger
    assert f"scaffolded {ref.id_slug}" in ledger
    assert git_repo.origin_tracks(f"relay-os/tasks/{ref.id_slug}/ticket.md")
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_does_not_resurrect_remote_deleted_period_from_stale_main(
    git_repo, monkeypatch
) -> None:
    """A stale control checkout honors a remotely handled-and-deleted period."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    launch_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "relay.commands.launch.launch", lambda *a, **k: launch_calls.append(a)
    )
    first = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])
    assert first.exit_code == 0, first.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    launch_calls.clear()

    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    git_repo.git("add", f"relay-os/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"relay-os/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)
    monkeypatch.setattr(
        "relay.commands.recurring._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr("relay.commands.recurring.notify", lambda *a, **k: None)

    second = CliRunner().invoke(app, ["recurring"])

    assert second.exit_code == 0, second.output
    assert launch_calls == []
    assert not git_repo.origin_tracks(f"relay-os/tasks/{ref.id_slug}/ticket.md")
    assert not ref.path.exists()
    ledger = git_repo.git(
        "show",
        "main:relay-os/recurring/weekly-check/log.md",
        cwd=git_repo.origin,
    )
    assert f"scaffolded {ref.id_slug}" in ledger
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_explicit_rerun_bypasses_handled_period_ledger(
    git_repo, monkeypatch
) -> None:
    """Manual `recurring launch` is an explicit same-period rerun override."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    launch_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "relay.commands.launch.launch", lambda *a, **k: launch_calls.append(a)
    )
    first = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])
    assert first.exit_code == 0, first.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    launch_calls.clear()

    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    git_repo.git("add", f"relay-os/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"relay-os/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    (relay_os / "tasks").mkdir(exist_ok=True)

    second = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert second.exit_code == 0, second.output
    assert launch_calls == [(ref.id_slug,)]
    assert (relay_os / "tasks" / ref.id_slug / "ticket.md").is_file()
    assert git_repo.origin_tracks(f"relay-os/tasks/{ref.id_slug}/ticket.md")


def test_recurring_scaffold_sync_restores_control_ledger_for_handled_period(
    git_repo,
) -> None:
    """A stale control checkout discards its attempted duplicate period state."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    log = relay_os / "recurring" / "weekly-check" / "log.md"
    _write(log, "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    cfg = load_config(relay_os)
    remote = scaffold_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 0))
    recurring_cmd._sync_recurring_scaffold(cfg, "weekly-check", remote.ref)
    ticket = Ticket.read(remote.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(remote.ref.path / "ticket.md")
    git_repo.git("add", f"relay-os/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"relay-os/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)

    cfg = load_config(relay_os)
    stale = scaffold_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    recurring_cmd._sync_recurring_scaffold(cfg, "weekly-check", stale.ref)

    ledger_rel = "relay-os/recurring/weekly-check/log.md"
    control_log = git_repo.git("show", f"main:{ledger_rel}", cwd=git_repo.origin)
    assert log.read_text() == control_log
    assert "10:05" not in log.read_text()
    assert f"scaffolded {stale.ref.id_slug}" in log.read_text()
    assert not stale.ref.path.exists()
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_scaffold_sync_failure_after_removing_stale_task_is_soft(
    git_repo, monkeypatch, capsys
) -> None:
    """A handled-period restore can remove the task before a later git error."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    cfg = load_config(relay_os)
    remote = scaffold_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 0))
    recurring_cmd._sync_recurring_scaffold(cfg, "weekly-check", remote.ref)
    ticket = Ticket.read(remote.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(remote.ref.path / "ticket.md")
    git_repo.git("add", f"relay-os/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"relay-os/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/stale",)
    git_repo.git("reset", "--hard", stale_head)

    cfg = load_config(relay_os)
    stale = scaffold_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))

    def fail_commit(*args, **kwargs):
        raise recurring_cmd.git.GitError("simulated index lock")

    monkeypatch.setattr("relay.commands.recurring.git._commit_paths", fail_commit)

    recurring_cmd._sync_recurring_scaffold(cfg, "weekly-check", stale.ref)

    assert "sync failed: simulated index lock" in capsys.readouterr().err
    assert not stale.ref.path.exists()


def test_recurring_sweep_skips_task_removed_by_scaffold_sync(
    git_repo, monkeypatch
) -> None:
    """The bare sweep does not launch a stale task removed during broadcast sync."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    cfg = load_config(relay_os)
    remote = scaffold_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 0))
    recurring_cmd._sync_recurring_scaffold(cfg, "weekly-check", remote.ref)
    ticket = Ticket.read(remote.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(remote.ref.path / "ticket.md")
    git_repo.git("add", f"relay-os/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"relay-os/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)

    launch_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "relay.commands.recurring._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "relay.commands.launch.launch", lambda *a, **k: launch_calls.append(a)
    )
    monkeypatch.setattr("relay.commands.recurring.notify", lambda *a, **k: None)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert launch_calls == []
    assert "No recurring tasks due." in result.output
    assert not (relay_os / "tasks" / remote.ref.id_slug).exists()
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_does_not_revert_remote_done_period_from_stale_main(
    git_repo, monkeypatch
) -> None:
    """A stale control checkout does not replace a remote done task with active."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    launch_calls: list[tuple[object, ...]] = []
    notify_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "relay.commands.launch.launch", lambda *a, **k: launch_calls.append(a)
    )
    monkeypatch.setattr(
        "relay.commands.recurring.notify", lambda *a, **k: notify_calls.append(a)
    )
    first = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])
    assert first.exit_code == 0, first.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    launch_calls.clear()
    notify_calls.clear()

    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    (ref.path / "blackboard.md").write_text("remote done state\n")
    git_repo.git("add", f"relay-os/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)

    second = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert second.exit_code == 0, second.output
    assert f"Created {ref.id_slug}" not in second.output
    assert launch_calls == []
    assert notify_calls == []
    ticket_rel = f"relay-os/tasks/{ref.id_slug}/ticket.md"
    remote_ticket = git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    assert "status: done" in remote_ticket
    assert "status: active" not in remote_ticket
    assert Ticket.read(ref.path / "ticket.md").status == "done"
    assert (ref.path / "blackboard.md").read_text() == "remote done state\n"
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_preserves_unpushed_control_branch_commits(
    git_repo, monkeypatch
) -> None:
    """Checked-out main keeps local work and takes unrelated remote changes."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    log = relay_os / "recurring" / "weekly-check" / "log.md"
    _write(
        log,
        "2026-06-01 09:00 [system] scaffolded "
        "recurring-weekly-check-2026-W23\n",
    )
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    local_file = git_repo.root / "LOCAL.txt"
    local_file.write_text("local\n")
    git_repo.git("add", "LOCAL.txt")
    git_repo.git("commit", "-m", "local unpushed")
    git_repo.push_competing_commit("UNRELATED.txt", "remote\n")
    remote_line = (
        "2026-06-08 09:00 [system] scaffolded "
        "recurring-weekly-check-2026-W22\n"
    )
    git_repo.push_competing_commit(
        "relay-os/recurring/weekly-check/log.md",
        log.read_text() + remote_line,
    )

    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    assert git_repo.origin_tracks("LOCAL.txt")
    assert git_repo.origin_tracks("UNRELATED.txt")
    assert git_repo.origin_tracks(f"relay-os/tasks/{ref.id_slug}/ticket.md")
    assert local_file.read_text() == "local\n"
    assert (git_repo.root / "UNRELATED.txt").read_text() == "remote\n"
    ledger = git_repo.git(
        "show",
        "main:relay-os/recurring/weekly-check/log.md",
        cwd=git_repo.origin,
    )
    assert remote_line in ledger
    assert f"scaffolded {ref.id_slug}" in ledger
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_preserves_midflight_remote_ledger_race(
    git_repo, monkeypatch
) -> None:
    """A log line pushed after local commit but before control landing survives."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    log = relay_os / "recurring" / "weekly-check" / "log.md"
    _write(
        log,
        "2026-06-01 09:00 [system] scaffolded "
        "recurring-weekly-check-2026-W23\n",
    )
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    git_repo.checkout_branch("feature/race")
    base_log = log.read_text()
    race_line = (
        "2026-06-08 09:00 [system] scaffolded "
        "recurring-weekly-check-2026-W22\n"
    )
    real_commit_paths = recurring_cmd.git._commit_paths

    def racing_commit(root, rels, message):
        committed = real_commit_paths(root, rels, message)
        git_repo.push_competing_commit(
            "relay-os/recurring/weekly-check/log.md",
            base_log + race_line,
        )
        return committed

    monkeypatch.setattr("relay.commands.recurring.git._commit_paths", racing_commit)
    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    ledger_rel = "relay-os/recurring/weekly-check/log.md"
    ledger = git_repo.git("show", f"main:{ledger_rel}", cwd=git_repo.origin)
    assert race_line in ledger
    assert f"scaffolded {ref.id_slug}" in ledger
    assert git_repo.origin_tracks(f"relay-os/tasks/{ref.id_slug}/ticket.md")
    local_ledger = git_repo.git("show", f"HEAD:{ledger_rel}")
    assert race_line not in local_ledger
    assert f"scaffolded {ref.id_slug}" in local_ledger
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_does_not_resurrect_midflight_handled_period(
    git_repo, monkeypatch
) -> None:
    """A same-slug handled-period race wins over the local active scaffold."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/handled-race")

    cfg = load_config(relay_os)
    outcome = scaffold_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    handled_blackboard = (
        "state\n\nremote_cursor: kept\n\nlast_serviced_period: 2026-W24\n"
    )
    real_commit_paths = recurring_cmd.git._commit_paths
    raced = False

    def racing_commit(root, rels, message):
        nonlocal raced
        committed = real_commit_paths(root, rels, message)
        if not raced:
            git_repo.push_competing_commit(
                "relay-os/recurring/weekly-check/blackboard.md",
                handled_blackboard,
            )
            raced = True
        return committed

    monkeypatch.setattr("relay.commands.recurring.git._commit_paths", racing_commit)

    recurring_cmd._sync_recurring_scaffold(cfg, "weekly-check", outcome.ref)

    blackboard_rel = "relay-os/recurring/weekly-check/blackboard.md"
    control_bb = git_repo.git("show", f"main:{blackboard_rel}", cwd=git_repo.origin)
    assert control_bb == handled_blackboard
    assert (
        relay_os / "recurring" / "weekly-check" / "blackboard.md"
    ).read_text() == handled_blackboard
    assert not git_repo.origin_tracks(f"relay-os/tasks/{outcome.ref.id_slug}/ticket.md")
    assert not outcome.ref.path.exists()
    ledger_rel = "relay-os/recurring/weekly-check/log.md"
    assert "10:05" not in git_repo.git("show", f"HEAD:{ledger_rel}")
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_removes_checked_out_control_task_when_race_handled(
    git_repo, monkeypatch, capsys
) -> None:
    """A checked-out control branch drops a new task if the remote handled it."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(relay_os)
    outcome = scaffold_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    handled_blackboard = "state\n\nlast_serviced_period: 2026-W24\n"
    real_fetch = recurring_cmd._fetch_control_branch
    fetch_calls = 0

    def racing_fetch(cfg_arg, root):
        nonlocal fetch_calls
        fetch_calls += 1
        real_fetch(cfg_arg, root)
        if fetch_calls == 2:
            git_repo.push_competing_commit(
                "relay-os/recurring/weekly-check/blackboard.md",
                handled_blackboard,
            )

    monkeypatch.setattr(recurring_cmd, "_fetch_control_branch", racing_fetch)

    recurring_cmd._sync_recurring_scaffold(cfg, "weekly-check", outcome.ref)

    assert "sync failed" not in capsys.readouterr().err
    assert not outcome.ref.path.exists()
    assert not git_repo.origin_tracks(f"relay-os/tasks/{outcome.ref.id_slug}/ticket.md")
    blackboard_rel = "relay-os/recurring/weekly-check/blackboard.md"
    assert (
        git_repo.git("show", f"main:{blackboard_rel}", cwd=git_repo.origin)
        == handled_blackboard
    )
    assert (
        relay_os / "recurring" / "weekly-check" / "blackboard.md"
    ).read_text() == handled_blackboard
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_scaffold_sync_missing_git_is_soft(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    cfg = load_config(dream_repo)
    outcome = scaffold_named(cfg, "dream", now=datetime(2026, 5, 20, 10, 0, 0))

    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(recurring_cmd.subprocess, "run", missing_git)
    recurring_cmd._sync_recurring_scaffold(cfg, "dream", outcome.ref)

    assert "sync skipped" in capsys.readouterr().err


def test_recurring_launch_preserves_local_commit_when_control_fetch_fails(
    git_repo, monkeypatch
) -> None:
    """An unreachable control branch still leaves the scaffold committed locally."""
    relay_os = git_repo.relay_os
    _seed_period_task_context(relay_os)
    _write_recurring(
        relay_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _write(relay_os / "recurring" / "weekly-check" / "blackboard.md", "state\n")
    _write(relay_os / "recurring" / "weekly-check" / "log.md", "")
    git_repo.git("add", "relay-os/contexts", "relay-os/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    git_repo.git(
        "remote",
        "set-url",
        "origin",
        str(git_repo.origin.parent / "missing.git"),
    )

    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(relay_os)
    ref = list_tasks(cfg)[0]
    ledger_rel = "relay-os/recurring/weekly-check/log.md"
    ticket_rel = f"relay-os/tasks/{ref.id_slug}/ticket.md"
    assert git_repo.git("log", "--format=%s", "-1").strip() == (
        f"Ticket: {ref.id_slug} — recurring scaffold"
    )
    assert f"scaffolded {ref.id_slug}" in git_repo.git("show", f"HEAD:{ledger_rel}")
    assert "title: Weekly check" in git_repo.git("show", f"HEAD:{ticket_rel}")


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
    assert "Created recurring/dream" in first.output
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


# --- relay recurring --all (debug) --------------------------------------------


def test_scan_debug_scaffolds_fresh_isolated_run(repo: Path) -> None:
    """`--all` scaffolds a throwaway run per template, even when the real
    current-period task already exists and is past `active`."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)

    # The real current-period task exists and has moved past `active`, so the
    # normal sweep would skip it.
    period = scan_due(cfg, now=now)
    period_slug = period.tasks[0].ref.id_slug
    ticket_path = period.tasks[0].ref.path / "ticket.md"
    t = Ticket.read(ticket_path)
    t.frontmatter["status"] = "done"
    ticket_path.write_text(t.render())
    assert scan_due(cfg, now=now).due == []  # nothing launchable normally

    debug = scan_debug(cfg, now=now)
    assert debug.errors == []
    assert len(debug.tasks) == 1
    run = debug.tasks[0]
    # Fresh, isolated slug — never the real period slug.
    assert run.ref.id_slug != period_slug
    assert "-dbg-" in run.ref.id_slug
    assert run.launchable is True  # scaffolds straight to `active`
    assert Ticket.read(run.ref.path / "ticket.md").title.startswith("[debug]")

    # Real period task untouched, two task dirs now on disk.
    assert Ticket.read(ticket_path).status == "done"
    assert len(list_tasks(cfg)) == 2


def test_scan_debug_does_not_advance_period_high_water(repo: Path) -> None:
    """A debug run must not advance the template's serviced-period high-water."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    scan_debug(cfg, now=now)
    ledger = repo / "recurring" / "weekly-check" / "blackboard.md"
    if ledger.is_file():
        assert "-dbg-" not in ledger.read_text()


def test_recurring_all_launches_every_template(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[str] = []
    _allow_interactive_recurring(monkeypatch)
    monkeypatch.setattr(
        "relay.commands.launch.launch",
        lambda slug, **k: launched.append(slug),
    )
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(app, ["recurring", "--all"])

    assert result.exit_code == 0, result.output
    assert len(launched) == 1
    dbg_slug = launched[0]
    assert "-dbg-" in dbg_slug
    # The throwaway run is folded back into the template log and its scratch
    # dir removed, so nothing lingers in `relay status`.
    assert "scratch dir removed" in result.output
    assert not (repo / "tasks" / dbg_slug).exists()
    template_log = (repo / "recurring" / "weekly-check" / "log.md").read_text()
    assert f"debug run {dbg_slug}" in template_log


def test_recurring_all_skips_interactive_template_without_tty(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[str] = []
    monkeypatch.setattr(
        "relay.commands.recurring._interactive_stdio_has_tty", lambda: False
    )
    monkeypatch.setattr(
        "relay.commands.launch.launch",
        lambda slug, **k: launched.append(slug),
    )
    monkeypatch.chdir(repo)

    result = CliRunner().invoke(app, ["recurring", "--all"])

    assert result.exit_code == 0, result.output
    assert launched == []
    assert "No recurring templates to launch." in result.output
    combined = result.output + (result.stderr or "")
    assert "skipping weekly-check" in combined
    assert "mode=interactive requires a TTY" in combined
    assert list_tasks(load_config(repo)) == []


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
        return_timeout: bool = False,
    ) -> None:
        assert return_timeout is False
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        assert ticket.status == "active"
        calls.append(task)

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls == ["recurring/dream"]


def test_recurring_launch_resumes_in_progress_orphan(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay recurring launch <name>` resumes an orphaned `in_progress` task.

    The on-demand path (the `relay dream` alias) follows the same rule as the
    bare sweep: an `in_progress` period task left by a dead supervisor is
    relaunched (resumed), not refused.
    """
    calls: list[str] = []
    monkeypatch.setattr(
        "relay.commands.launch.launch", lambda task, **k: calls.append(task)
    )

    # First call scaffolds the period task (`active`); freeze it `in_progress`
    # to mimic a sweep that died mid-run.
    CliRunner().invoke(app, ["recurring", "launch", "dream"])
    cfg = load_config(dream_repo)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.path / "ticket.md")
    calls.clear()

    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert "Resuming" in result.output
    assert calls == [ref.id_slug]  # relaunched, not refused


def test_recurring_launch_refuses_done_task(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `done` period task is left alone — re-running finished work is wrong."""
    calls: list[str] = []
    monkeypatch.setattr(
        "relay.commands.launch.launch", lambda task, **k: calls.append(task)
    )

    CliRunner().invoke(app, ["recurring", "launch", "dream"])
    cfg = load_config(dream_repo)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    calls.clear()

    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert "is done; not launching" in result.output
    assert calls == []


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
    _allow_interactive_recurring(monkeypatch)

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
    assert calls == ["recurring/dream"]


def test_bare_recurring_skips_interactive_without_tty_and_continues(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unattended recurring skips interactive work and launches later due tasks."""
    _write_recurring(
        repo,
        "z-script-check",
        """
        ---
        schedule: "* * * * *"
        title: "Script check"
        mode: script
        assignee: claude
        owner: marc
        ---

        ## Description

        Script.
        """,
    )
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "relay.commands.recurring._interactive_stdio_has_tty", lambda: False
    )
    calls: list[str] = []
    slack_msgs: list[str] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(repo / "tasks" / task / "ticket.md")

    def capture_slack(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        slack_msgs.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)
    monkeypatch.setattr("relay.slack.requests.post", capture_slack)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls == ["recurring/z-script-check"]
    combined = result.output + (result.stderr or "")
    assert "skipping weekly-check" in combined
    assert "mode=interactive requires a TTY" in combined
    assert any(
        "skipped 1 template" in msg and "weekly-check" in msg
        for msg in slack_msgs
    )


def test_bare_recurring_continues_past_unfinished_interactive_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interactive templates do not gate the sweep on `status: done`.

    The human is driving — exiting the agent without marking done is a
    "park this run and move on" signal, not a stuck task. The sweep pauses
    that task, prints a note, and proceeds to the next due task.
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
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "in_progress"
        ticket.write(repo / "tasks" / task / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 2
    assert calls == ["recurring/weekly-check", "recurring/z-weekly-check"]
    assert "paused and continuing to next due task (interactive)" in result.output

    cfg = load_config(repo)
    refs = list_tasks(cfg)
    assert {Ticket.read(ref.path / "ticket.md").status for ref in refs} == {"paused"}

    calls.clear()
    second = CliRunner().invoke(app, ["recurring"])
    assert second.exit_code == 0, second.output
    assert calls == []
    assert "No recurring tasks due." in second.output


def test_bare_recurring_records_liveness_timeout_not_human_pause(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A launch that ends in a liveness timeout is recorded as a watchdog
    timeout — not the human-pause masquerade.

    `launch` returns "timeout" when the supervisor tore a wedged REPL down. The
    sweep must pause the task (so the next scan doesn't relaunch the orphan) but
    log/broadcast it as a timeout with a system actor, and continue the sweep.
    """
    monkeypatch.chdir(repo)
    calls: list[str] = []
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "in_progress"
        ticket.write(repo / "tasks" / task / "ticket.md")
        return "timeout"

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "timed out" in result.output
    assert "paused as a watchdog timeout" in result.output

    cfg = load_config(repo)
    ref = list_tasks(cfg)[0]
    assert Ticket.read(ref.path / "ticket.md").status == "paused"
    # The durable trace names the watchdog on the pause line, not a human — the
    # whole point of the fix is that this is distinguishable from a deliberate
    # human pause (which would log `[human:<user>] paused ...`).
    pause_lines = [
        line
        for line in (ref.path / "log.md").read_text().splitlines()
        if "→ paused" in line
    ]
    assert pause_lines, "expected a pause entry in log.md"
    assert all("[system:watchdog]" in line for line in pause_lines)
    assert any("timed out before signalling done" in line for line in pause_lines)
    assert all(f"[human:{cfg.current_user}]" not in line for line in pause_lines)


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
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
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
    assert calls == ["recurring/nightly-check"]
    combined = result.output + (result.stderr or "")
    assert "stopping before the next due task" in combined


def test_bare_recurring_interactive_overrides_mode(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay recurring --interactive` threads mode_override to each launch."""
    seen: list[str | None] = []
    _allow_interactive_recurring(monkeypatch)

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
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append(kwargs.get("mode_override"))
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(dream_repo / "tasks" / task / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert seen == [None]


def _capture_idle_timeout(
    repo: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> list[float | None]:
    """Run a recurring sweep with a stubbed launch and return the
    `idle_timeout` each launch was called with."""
    seen: list[float | None] = []
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        assert kwargs.get("return_timeout") is True
        seen.append(kwargs.get("idle_timeout"))
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(repo / "tasks" / task / "ticket.md")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)
    assert CliRunner().invoke(app, argv).exit_code == 0
    return seen


def test_bare_recurring_arms_idle_timeout(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The automatic sweep arms the default idle backstop on each launch."""
    assert _capture_idle_timeout(dream_repo, monkeypatch, ["recurring"]) == [900.0]


def test_bare_recurring_config_can_disarm_idle_timeout(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`[launch].idle_timeout = 0` explicitly disables the built-in default."""
    relay_toml = dream_repo / "relay.toml"
    relay_toml.write_text(relay_toml.read_text() + "\n[launch]\nidle_timeout = 0\n")

    assert _capture_idle_timeout(dream_repo, monkeypatch, ["recurring"]) == [None]


def test_bare_recurring_interactive_leaves_idle_timeout_off(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--interactive` (a human driving by hand) leaves the REPL unbounded."""
    assert _capture_idle_timeout(
        dream_repo, monkeypatch, ["recurring", "--interactive"]
    ) == [None]


def _timeout_cfg(
    *,
    idle: float | None = None,
    idle_present: bool = False,
    max_session: float | None = None,
) -> SimpleNamespace:
    """Minimal stand-in for `Config` carrying only the launch-limit fields the
    timeout resolvers read — keeps these unit tests free of a full repo."""
    return SimpleNamespace(
        launch_idle_timeout=idle,
        launch_idle_timeout_present=idle_present,
        launch_max_session=max_session,
    )


def test_recurring_idle_timeout_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`RELAY_REPL_IDLE_TIMEOUT` overrides the default window; a `<= 0`,
    non-finite, or unparseable value disarms the backstop."""
    from relay.commands.recurring import (
        _RECURRING_IDLE_TIMEOUT_SECONDS,
        _recurring_idle_timeout,
    )

    cfg = _timeout_cfg()
    monkeypatch.delenv("RELAY_REPL_IDLE_TIMEOUT", raising=False)
    assert _recurring_idle_timeout(cfg) == _RECURRING_IDLE_TIMEOUT_SECONDS

    monkeypatch.setenv("RELAY_REPL_IDLE_TIMEOUT", "30")
    assert _recurring_idle_timeout(cfg) == 30.0

    for disarm in ("0", "-5", "inf", "nan", "later"):
        monkeypatch.setenv("RELAY_REPL_IDLE_TIMEOUT", disarm)
        assert _recurring_idle_timeout(cfg) is None, disarm


def test_recurring_idle_timeout_config_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Precedence is env > `[launch].idle_timeout` > the built-in default; an
    env override wins even to disarm a committed config value."""
    from relay.commands.recurring import (
        _RECURRING_IDLE_TIMEOUT_SECONDS,
        _recurring_idle_timeout,
    )

    monkeypatch.delenv("RELAY_REPL_IDLE_TIMEOUT", raising=False)
    # Config value used when no env override is set.
    assert (
        _recurring_idle_timeout(_timeout_cfg(idle=120.0, idle_present=True))
        == 120.0
    )
    assert _recurring_idle_timeout(_timeout_cfg(idle=None, idle_present=True)) is None
    # No config and no env → built-in default.
    assert _recurring_idle_timeout(_timeout_cfg()) == _RECURRING_IDLE_TIMEOUT_SECONDS
    # Env beats config, including the disarm case.
    monkeypatch.setenv("RELAY_REPL_IDLE_TIMEOUT", "45")
    assert (
        _recurring_idle_timeout(_timeout_cfg(idle=120.0, idle_present=True))
        == 45.0
    )
    monkeypatch.setenv("RELAY_REPL_IDLE_TIMEOUT", "0")
    assert (
        _recurring_idle_timeout(_timeout_cfg(idle=120.0, idle_present=True)) is None
    )


def test_recurring_max_session_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Max-session has no built-in default — None unless config or env sets it.
    Precedence mirrors idle-timeout: env > `[launch].max_session` > None."""
    from relay.commands.recurring import _recurring_max_session

    monkeypatch.delenv("RELAY_REPL_MAX_SESSION", raising=False)
    assert _recurring_max_session(_timeout_cfg()) is None
    assert _recurring_max_session(_timeout_cfg(max_session=600.0)) == 600.0

    monkeypatch.setenv("RELAY_REPL_MAX_SESSION", "90")
    assert _recurring_max_session(_timeout_cfg(max_session=600.0)) == 90.0
    for disarm in ("0", "-5", "inf", "nan", "later"):
        monkeypatch.setenv("RELAY_REPL_MAX_SESSION", disarm)
        assert _recurring_max_session(_timeout_cfg(max_session=600.0)) is None, disarm


def test_bare_recurring_nothing_due(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second bare run in the same period whose task is `done` is a no-op.

    (An `in_progress` task is no longer a no-op — it is resumed; see
    `test_scan_due_resumes_orphaned_in_progress_task`.)
    """
    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)
    _allow_interactive_recurring(monkeypatch)
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
