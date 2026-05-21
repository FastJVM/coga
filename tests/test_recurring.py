from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.recurring import check_recurring, scaffold_named
from relay.tasks import list_tasks
from relay.ticket import Ticket


SHIPPED_DREAM_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "recurring"
    / "dream.md"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


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
    _write(
        company / "recurring" / "weekly-check.md",
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


def test_check_recurring_creates_task(repo: Path) -> None:
    cfg = load_config(repo)
    fixed_now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am
    result = check_recurring(cfg, now=fixed_now)
    assert len(result.created) == 1
    assert result.errors == []
    ref = result.created[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    assert ticket.title == "Weekly deliverability check"
    assert ticket.mode == "interactive"
    assert ticket.owner == "marc"
    # Period key for weekly = ISO week of the firing (Mon 2026-04-20, ISO week 17)
    assert ref.slug.endswith("-2026-W17")
    # Description body made it in
    body = (ref.path / "ticket.md").read_text()
    assert "Run the full deliverability diagnostic suite" in body


def test_check_recurring_idempotent(repo: Path) -> None:
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = check_recurring(cfg, now=now)
    second = check_recurring(cfg, now=now)
    assert len(first.created) == 1
    assert len(second.created) == 0
    assert len(list_tasks(cfg)) == 1


def test_check_recurring_different_period_creates_new(repo: Path) -> None:
    cfg = load_config(repo)
    check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    result = check_recurring(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18
    assert len(result.created) == 1
    assert result.created[0].slug.endswith("-2026-W18")


def test_check_recurring_skips_bad_template(repo: Path, capsys) -> None:
    _write(repo / "recurring" / "bad.md", "no frontmatter here\n")
    cfg = load_config(repo)
    result = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(result.created) == 1  # good one still created
    assert len(result.errors) == 1
    assert result.errors[0][0] == "bad.md"
    assert "skipping bad.md" in capsys.readouterr().err


def test_check_recurring_skips_auto_mode_template(repo: Path, capsys) -> None:
    """`mode: auto` templates are skipped with a stderr + result-errors note.

    Auto launches produce no live console output, so scheduled runs would
    sit silently. Until streaming lands, the recurring scanner refuses
    to scaffold them.
    """
    _write(
        repo / "recurring" / "daily-auto.md",
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
    result = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    # Good (interactive) template still creates; auto one is skipped + reported.
    assert len(result.created) == 1
    assert result.created[0].slug.startswith("weekly-check-")
    assert len(result.errors) == 1
    name, msg = result.errors[0]
    assert name == "daily-auto.md"
    assert "mode=auto is temporarily disabled" in msg
    assert "skipping daily-auto.md" in capsys.readouterr().err


def test_check_recurring_skips_template_without_explicit_mode(
    repo: Path, capsys
) -> None:
    """Templates without `mode:` are treated as auto (legacy default) and skipped."""
    _write(
        repo / "recurring" / "no-mode.md",
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
    result = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert any(name == "no-mode.md" for name, _ in result.errors)


def test_check_recurring_skips_underscore_template(repo: Path, capsys) -> None:
    # `_template.md` is a scaffold, not a live recurring task — must be ignored
    # silently (no stderr complaint) even though its placeholder fields wouldn't
    # validate.
    _write(
        repo / "recurring" / "_template.md",
        """
        ---
        schedule: "0 9 * * 1"
        title: placeholder
        ---
        """,
    )
    cfg = load_config(repo)
    result = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(result.created) == 1  # only the real one
    assert result.errors == []
    assert "_template.md" not in capsys.readouterr().err


# --- relay recurring scaffold / the `dream` alias path ------------------------


@pytest.fixture
def dream_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo carrying the real shipped `recurring/dream.md` template.

    `relay recurring scaffold` and `relay recurring check` are the two entry
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
    (company / "tasks").mkdir(parents=True)
    (company / "recurring").mkdir(parents=True)
    shutil.copy(SHIPPED_DREAM_TEMPLATE, company / "recurring" / "dream.md")
    monkeypatch.chdir(company)
    return company


def test_recurring_scaffold_creates_dream_task(dream_repo: Path) -> None:
    result = CliRunner().invoke(app, ["recurring", "scaffold", "dream"])

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
    assert "### Run order" in ticket.body
    # Slug uses the schedule-derived period key, not plain `dream`.
    assert refs[0].slug.startswith("dream-")
    assert refs[0].slug != "dream"


def test_recurring_scaffold_defaults_assignee_to_default_agent(
    dream_repo: Path,
) -> None:
    """A workflow-less recurring task (Dream) with no template `assignee:`
    defaults to the repo's default agent, not the human owner — otherwise
    `relay launch` cannot resolve the assignee to an agent type."""
    CliRunner().invoke(app, ["recurring", "scaffold", "dream"])

    cfg = load_config(dream_repo)
    refs = list_tasks(cfg)
    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.workflow is None
    assert ticket.owner == "marc"
    assert ticket.assignee == "claude"


def test_recurring_scaffold_is_idempotent(dream_repo: Path) -> None:
    runner = CliRunner()
    first = runner.invoke(app, ["recurring", "scaffold", "dream"])
    second = runner.invoke(app, ["recurring", "scaffold", "dream"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert "Created dream-" in first.output
    assert "already scaffolded for this period" in second.output
    # Idempotent: one task directory, not two.
    assert len(list_tasks(load_config(dream_repo))) == 1


def test_recurring_scaffold_and_check_converge(dream_repo: Path) -> None:
    """A manual `scaffold dream` and the cron `check` produce one task dir."""
    cfg = load_config(dream_repo)
    now = datetime(2026, 5, 20, 10, 0, 0)  # a Wednesday

    manual = scaffold_named(cfg, "dream", now=now)
    assert manual.created is True

    # The cron path, same period, sees the task already exists → no-op.
    check = check_recurring(cfg, now=now)
    assert check.created == []
    assert check.errors == []
    assert len(list_tasks(cfg)) == 1


def test_recurring_scaffold_unknown_template_fails(dream_repo: Path) -> None:
    result = CliRunner().invoke(app, ["recurring", "scaffold", "nope"])
    assert result.exit_code == 2
    assert "no recurring template `recurring/nope.md`" in result.output


def test_recurring_scaffold_launch_activates_and_launches(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--launch` (the `relay dream` alias path) launches the scaffolded task.

    Recurring tasks are workflow-less and scaffold straight to `active`, so
    `--launch` hands off to `relay launch` directly — no `mark active` step.
    """
    calls: list[str] = []

    def fake_launch(
        task: str,
        agent_override: str | None,
        prompt_report: bool,
        no_verify: bool,
    ) -> None:
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        assert ticket.status == "active"
        calls.append(task)

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring", "scaffold", "dream", "--launch"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    slug = calls[0]
    assert slug.startswith("dream-")
    ticket = Ticket.read(dream_repo / "tasks" / slug / "ticket.md")
    assert ticket.status == "active"
    log = (dream_repo / "tasks" / slug / "log.md").read_text()
    assert "created (mode=" in log and "status=active)" in log
