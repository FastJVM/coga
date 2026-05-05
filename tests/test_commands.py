from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.scaffold import scaffold_task
from relay.config import load_config
from relay.tasks import list_tasks
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
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
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

        ## implement
        Write the code.
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(repo: Path, *, workflow: str | None = "code", status: str = "active") -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="Work", workflow_name=workflow,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status=status,
    )
    return ref["slug"], ref["path"]


# --- bump ---------------------------------------------------------------------


def test_bump_advances(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    cfg = load_config(repo)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    assert t.step == "2 (pr)"
    assert "advanced to step 2" in (ref.path / "log.md").read_text()


def test_bump_to_done_marks_done(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    # Workflow has 3 steps; bumping past the last marks done.
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "done"
    assert t.step is None
    assert "task done" in (task_path / "log.md").read_text()


def test_bump_rejects_non_active(repo: Path) -> None:
    slug, _ = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 2


def test_bump_no_workflow_marks_done(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None)
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["step"] = "1 (legacy)"
    t.write(task_path / "ticket.md")

    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    assert "done" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "done"
    assert t.step is None


# --- panic --------------------------------------------------------------------


def test_panic_writes_blocker_and_releases_lock(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    # Simulate a held lock
    from relay.lock import TaskLock
    TaskLock(task_path).acquire("claude1")
    runner = CliRunner()
    result = runner.invoke(app, ["panic", "--task", slug, "--reason", "unclear ceiling for 429 backoff"])
    # Panic exits non-zero so a parent process can detect agent distress.
    assert result.exit_code == 1, result.output
    blackboard = (task_path / "blackboard.md").read_text()
    assert "unclear ceiling for 429 backoff" in blackboard
    assert "## Blockers" in blackboard
    assert not TaskLock(task_path).path.exists()
    assert "panic:" in (task_path / "log.md").read_text()


# --- delete -------------------------------------------------------------------


def test_delete_removes_task_directory(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    assert task_path.is_dir()
    runner = CliRunner()
    result = runner.invoke(app, ["delete", slug])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()
    assert "deleted" in result.output


def test_delete_resolves_prefix(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["delete", slug[:6]])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()


def test_delete_unknown_task_exits_nonzero(repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["delete", "no-such-task-xyz"])
    assert result.exit_code == 2


def test_delete_refuses_when_locked(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    from relay.lock import TaskLock
    TaskLock(task_path).acquire("claude1")
    runner = CliRunner()
    result = runner.invoke(app, ["delete", slug])
    assert result.exit_code == 2, result.output
    assert task_path.is_dir()
    assert "task.lock" in result.output


def test_delete_force_overrides_lock(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    from relay.lock import TaskLock
    TaskLock(task_path).acquire("claude1")
    runner = CliRunner()
    result = runner.invoke(app, ["delete", slug, "--force"])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()


# --- slack --------------------------------------------------------------------


def test_slack_logs(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["slack", "--task", slug, "--message", "opened PR #142"])
    assert result.exit_code == 0
    assert "slack: opened PR #142" in (task_path / "log.md").read_text()


# --- bump --message -----------------------------------------------------------


def test_bump_message_appended_to_log(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["bump", slug, "--message", "PR opened: https://example/142"],
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "advanced to step 2 (pr) — PR opened: https://example/142" in log


def test_bump_message_on_no_workflow_done(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(
        app, ["bump", slug, "--message", "talked to marc, scope ok"]
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "task done — talked to marc, scope ok" in log


def test_bump_message_on_final_step_done(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])
    result = runner.invoke(
        app, ["bump", slug, "--message", "shipped to prod"]
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "task done — shipped to prod" in log


def test_bump_rejects_empty_message(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug, "--message", ""])
    assert result.exit_code == 2


# --- bump assignee handoff ----------------------------------------------------


def _write_assignee_workflow(repo: Path) -> None:
    """Workflow whose three steps each declare a different role token."""
    _write(
        repo / "workflows" / "review.md",
        """
        ---
        name: review
        description: Roles per step.
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: human
          - name: signoff
            assignee: owner
        ---
        """,
    )


def test_bump_resolves_role_token_to_ticket_field(repo: Path) -> None:
    _write_assignee_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude1",
        human="marc", agent="claude1",
        watchers=[], status="active",
    )
    slug = ref["slug"]
    task_path = ref["path"]

    # Step 1 declared `assignee: agent` → resolved at scaffold time.
    t = Ticket.read(task_path / "ticket.md")
    assert t.assignee == "claude1"

    # Bump into step 2 (assignee: human) → ticket.assignee = ticket.human.
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (review)"
    assert t.assignee == "marc"
    log = (task_path / "log.md").read_text()
    assert "→ assigned to marc" in log

    # Bump into step 3 (assignee: owner) → ticket.assignee = ticket.owner.
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.assignee == "marc"  # owner == marc, no change → no handoff line
    log = (task_path / "log.md").read_text()
    # Only one handoff line so far (the human→owner step is a no-op handoff).
    assert log.count("→ assigned to") == 1


def test_bump_no_assignee_declared_leaves_assignee_unchanged(repo: Path) -> None:
    # The default `code` workflow in this fixture has no assignee declarations.
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.assignee == "claude1"  # unchanged
    log = (task_path / "log.md").read_text()
    assert "→ assigned to" not in log


def test_bump_role_token_with_missing_field_fails_loud(repo: Path) -> None:
    _write_assignee_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude1",
        human="marc", agent="claude1",
        watchers=[], status="active",
    )
    # Hand-edit the ticket to remove the `human` field, then bump into the
    # human step. Bump must refuse rather than silently skip.
    t = Ticket.read(ref["path"] / "ticket.md")
    del t.frontmatter["human"]
    t.write(ref["path"] / "ticket.md")

    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 2, result.output
    assert "human" in result.output


def test_bump_freezes_bare_string_workflow_then_advances(repo: Path) -> None:
    # Hand-authored ticket: `workflow:` is a bare string ref, no `step:`.
    legacy = repo / "tasks" / "legacy"
    legacy.mkdir(parents=True)
    (legacy / "ticket.md").write_text(dedent(
        """
        ---
        title: Legacy
        status: active
        mode: interactive
        owner: marc
        assignee: claude1
        workflow: code
        ---
        """
    ).lstrip())
    (legacy / "blackboard.md").write_text("")
    (legacy / "log.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(app, ["bump", "legacy"])
    assert result.exit_code == 0, result.output
    t = Ticket.read(legacy / "ticket.md")
    # Workflow now frozen; bump advanced step 1 → 2.
    assert isinstance(t.workflow, dict)
    assert t.step == "2 (pr)"


def test_bump_handoff_appears_in_slack_text(repo: Path) -> None:
    _write_assignee_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude1",
        human="marc", agent="claude1",
        watchers=[], status="active",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 0, result.output
    # Echo to stdout includes the same handoff phrasing as the slack text.
    assert "→ assigned to marc" in result.output


# --- show ---------------------------------------------------------------------


def test_show_prints_ticket_blackboard_and_log(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    (task_path / "blackboard.md").write_text("# Plan\n\nfigure it out\n")
    (task_path / "log.md").write_text("created task\n")
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug])
    assert result.exit_code == 0, result.output
    assert "ticket.md" in result.output
    assert "blackboard.md" in result.output
    assert "log.md" in result.output
    assert "figure it out" in result.output


def test_show_resolves_prefix(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug[:6]])
    assert result.exit_code == 0, result.output
    assert "ticket.md" in result.output


def test_show_handles_missing_blackboard_and_log(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    (task_path / "blackboard.md").unlink(missing_ok=True)
    (task_path / "log.md").unlink(missing_ok=True)
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug])
    assert result.exit_code == 0, result.output
    assert "no blackboard.md" in result.output
    assert "no log.md" in result.output


def test_show_unknown_task_exits_nonzero(repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["show", "no-such-task-xyz"])
    assert result.exit_code == 2


# --- status -------------------------------------------------------------------


def test_status_shows_active(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert slug in result.output


def test_status_narrow_terminal_keeps_each_task_on_one_line(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="anything", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="active", slug_override="t1",
    )
    monkeypatch.setenv("COLUMNS", "60")
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    # Header + one data row + separator. Anything more means Rich wrapped.
    body = [line for line in result.output.splitlines() if line.strip()]
    assert len(body) <= 3, result.output


def test_status_does_not_show_title_column(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="A distinctive ticket title", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="active", slug_override="t1",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "A distinctive ticket title" not in result.output
    assert "title" not in result.output.lower().split()


# --- validate -----------------------------------------------------------------


def test_validate_clean_repo_succeeds(repo: Path) -> None:
    _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0, result.output
    assert "All good" in result.output


def test_validate_json_emits_payload(repo: Path) -> None:
    _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--json"])
    assert result.exit_code == 0, result.output
    import json
    payload = json.loads(result.output)
    assert payload["fixes"] == []
    assert payload["issues"] == []
    assert payload["ok_count"] == 1


def test_validate_fix_json_repairs_missing_workspace_file(repo: Path) -> None:
    _, task_path = _make_task(repo, workflow=None)
    (task_path / "blackboard.md").unlink()

    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--fix", "--json"])

    assert result.exit_code == 0, result.output
    import json
    payload = json.loads(result.output)
    assert payload["fixes"][0]["message"] == "created blackboard.md"
    assert payload["issues"] == []
    assert (task_path / "blackboard.md").is_file()


def test_validate_warns_for_large_blackboard(repo: Path) -> None:
    _, task_path = _make_task(repo, workflow=None)
    (task_path / "blackboard.md").write_text("x" * 2048)

    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--max-blackboard-kb", "1"])
    assert result.exit_code == 0, result.output
    assert "[WARN]" in result.output
    assert "large-blackboard" in result.output


def test_status_shows_done_tasks(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None)
    # Mark done directly
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["status"] = "done"
    t.write(task_path / "ticket.md")
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert slug in result.output


# --- status --order-by / --reverse / updated column ---------------------------


def _set_log_timestamp(task_path: Path, when: str) -> None:
    """Overwrite task's log.md with a single line at the given timestamp."""
    (task_path / "log.md").write_text(f"{when} [system] backdated\n")


def test_status_includes_updated_column(repo: Path) -> None:
    _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "updated" in result.output


def test_status_default_orders_by_updated_desc(repo: Path) -> None:
    cfg = load_config(repo)
    older = scaffold_task(
        cfg=cfg, title="older", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="active", slug_override="aaa-old",
    )
    newer = scaffold_task(
        cfg=cfg, title="newer", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="active", slug_override="zzz-new",
    )
    _set_log_timestamp(older["path"], "2026-01-01 09:00")
    _set_log_timestamp(newer["path"], "2026-04-30 17:00")

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    new_idx = result.output.index("zzz-new")
    old_idx = result.output.index("aaa-old")
    assert new_idx < old_idx, result.output


def test_status_order_by_slug_is_alphabetical(repo: Path) -> None:
    cfg = load_config(repo)
    for slug in ("zeta", "alpha", "mu"):
        scaffold_task(
            cfg=cfg, title=slug, workflow_name=None,
            contexts=[], mode="interactive", owner="marc", assignee="claude1",
            watchers=[], status="active", slug_override=slug,
        )
    runner = CliRunner()
    result = runner.invoke(app, ["status", "--order-by", "slug"])
    assert result.exit_code == 0, result.output
    a = result.output.index("alpha")
    m = result.output.index("mu")
    z = result.output.index("zeta")
    assert a < m < z, result.output


def test_status_reverse_flips_order(repo: Path) -> None:
    cfg = load_config(repo)
    for slug in ("alpha", "zeta"):
        scaffold_task(
            cfg=cfg, title=slug, workflow_name=None,
            contexts=[], mode="interactive", owner="marc", assignee="claude1",
            watchers=[], status="active", slug_override=slug,
        )
    runner = CliRunner()
    result = runner.invoke(app, ["status", "--order-by", "slug", "--reverse"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zeta") < result.output.index("alpha"), result.output


def test_status_rejects_unknown_order_by(repo: Path) -> None:
    _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["status", "--order-by", "bogus"])
    assert result.exit_code == 2


def test_status_tasks_without_log_sort_to_end(repo: Path) -> None:
    cfg = load_config(repo)
    has_log = scaffold_task(
        cfg=cfg, title="logged", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="active", slug_override="zzz-logged",
    )
    no_log = scaffold_task(
        cfg=cfg, title="no log", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="active", slug_override="aaa-nolog",
    )
    _set_log_timestamp(has_log["path"], "2026-04-30 17:00")
    (no_log["path"] / "log.md").unlink()

    runner = CliRunner()
    # Default order (updated desc) — logged task on top, no-log task at bottom.
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zzz-logged") < result.output.index("aaa-nolog")

    # Even with --reverse, missing log stays at the bottom.
    result = runner.invoke(app, ["status", "--reverse"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zzz-logged") < result.output.index("aaa-nolog")
