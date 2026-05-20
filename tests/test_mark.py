"""Tests for `relay mark <state>`."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.scaffold import scaffold_task
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
        company / "workflows" / "code.md",
        """
        ---
        name: code
        description: tiny.
        steps:
          - name: implement
          - name: pr
          - name: merge
        ---
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(repo: Path, *, workflow: str | None = "code", status: str = "draft") -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="Work", workflow_name=workflow,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status=status,
    )
    return ref["slug"], ref["path"]


# --- mark active --------------------------------------------------------------


def test_mark_active_from_draft(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "active"
    log = (task_path / "log.md").read_text()
    assert "activated (draft → active)" in log


def test_mark_active_from_paused(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "active"
    log = (task_path / "log.md").read_text()
    assert "activated (paused → active)" in log


def test_mark_active_already_active_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="active")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "already 'active'" in result.output


def test_mark_active_from_done_errors(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    # Hand-set to done.
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["status"] = "done"
    t.write(task_path / "ticket.md")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "'done'" in result.output


def test_mark_active_refuses_workflow_less_ticket(repo: Path) -> None:
    """A draft with no workflow can't be activated — it would have no steps
    and could never be advanced by `relay bump`."""
    slug, task_path = _make_task(repo, workflow=None, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "no workflow" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "draft"


def test_mark_active_freezes_string_workflow(repo: Path) -> None:
    """A draft carrying `workflow:` as a bare string ref is frozen into its
    snapshot on activation, and seeded at step 1."""
    slug, task_path = _make_task(repo, workflow=None, status="draft")
    # Hand-author a bare-string workflow ref, as guided authoring would.
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["workflow"] = "code"
    t.write(task_path / "ticket.md")

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output

    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "active"
    assert isinstance(t.workflow, dict)
    assert t.workflow["name"] == "code"
    assert t.step == "1 (implement)"


def test_mark_active_refuses_unknown_string_workflow(repo: Path) -> None:
    """A bare-string `workflow:` ref that names no known workflow is refused
    at activation, when the freeze fails."""
    slug, task_path = _make_task(repo, workflow=None, status="draft")
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["workflow"] = "no-such-workflow"
    t.write(task_path / "ticket.md")

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "could not" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "draft"


def test_mark_active_blocks_on_required_extension_empty(repo: Path) -> None:
    """`mark active` refuses a draft whose `required = true` extension fields
    are empty."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "USPTO docket"\n'
            "required = true\n"
        )
    )
    slug, task_path = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "required extension field" in result.output
    assert "docket" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "draft"


def test_mark_active_allows_filled_required_extension(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "USPTO docket"\n'
            "required = true\n"
        )
    )
    slug, task_path = _make_task(repo, status="draft")
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["docket"] = "55-12345"
    t.write(task_path / "ticket.md")

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "active"
    assert t.frontmatter["docket"] == "55-12345"


def test_mark_active_ignores_required_when_not_required(repo: Path) -> None:
    """Empty non-required extension fields don't block activation."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "x"\n'
    )
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output


# --- mark paused --------------------------------------------------------------


def test_mark_paused_from_active(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "paused"
    log = (task_path / "log.md").read_text()
    assert "paused (active → paused)" in log


def test_mark_paused_preserves_step(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="in_progress")
    # Advance to step 2.
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (pr)"
    # Pausing preserves the step.
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "paused"
    assert t.step == "2 (pr)"


def test_mark_paused_from_draft_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 2


def test_mark_paused_already_paused_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 2
    assert "already 'paused'" in result.output


# --- mark done ----------------------------------------------------------------


def test_mark_done_from_active_clears_step(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "done"
    assert t.step is None
    log = (task_path / "log.md").read_text()
    assert "task done" in log


def test_mark_done_from_draft_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 2


def test_mark_done_from_paused_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 2


def test_mark_done_already_done_errors(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["status"] = "done"
    t.write(task_path / "ticket.md")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 2
    assert "already 'done'" in result.output


# --- --message ----------------------------------------------------------------


def test_mark_active_message_appended(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(
        app, ["mark", "active", slug, "--message", "kicking off"]
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "activated (draft → active) — kicking off" in log


def test_mark_paused_message_appended(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="in_progress")
    runner = CliRunner()
    result = runner.invoke(
        app, ["mark", "paused", slug, "--message", "blocked on review"]
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "paused (in_progress → paused) — blocked on review" in log


def test_mark_done_message_appended(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    runner = CliRunner()
    result = runner.invoke(
        app, ["mark", "done", slug, "--message", "shipped"]
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "task done — shipped" in log


def test_mark_rejects_empty_message(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug, "--message", ""])
    assert result.exit_code == 2


# --- prefix resolution --------------------------------------------------------


def test_mark_resolves_prefix(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug[:4]])
    assert result.exit_code == 0, result.output


def test_mark_unknown_task_errors(repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", "no-such-task-xyz"])
    assert result.exit_code == 2


# --- slack text ---------------------------------------------------------------


def test_mark_active_slack_text(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug, _ = _make_task(repo, status="draft")
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("relay.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    assert any(f"🚀 marc activated *{slug}*" in m for m in posts)


def test_mark_paused_slack_text(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug, _ = _make_task(repo, status="active")
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("relay.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 0, result.output
    assert any(f"⏸️ marc paused *{slug}*" in m for m in posts)


def test_mark_done_slack_text(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug, _ = _make_task(repo, status="active")
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("relay.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert any(f"🎉 claude finished *{slug}*" in m for m in posts)
