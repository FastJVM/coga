"""Tests for stale-cursor detection on recurring period tasks.

A recurring task declares the blackboard keys it owns via `state_keys:`. The
scaffolder snapshots their values into each period task; `relay mark done` and
`relay validate` flag a run that finished without advancing one.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.period_state import (
    SNAPSHOT_FILE,
    StateSnapshot,
    parse_keys,
    read_snapshot,
    stale_keys,
    write_snapshot,
)
from relay.recurring import RecurringError, Template, scan_due
from relay.tasks import list_tasks


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


# --- pure helpers -------------------------------------------------------------


def test_parse_keys_reads_present_missing_and_empty() -> None:
    text = dedent(
        """
        ### Dev Update State

        last_commit: 29dc3c1
        range:
        """
    )
    parsed = parse_keys(text, ["last_commit", "range", "absent"])
    assert parsed == {"last_commit": "29dc3c1", "range": "", "absent": None}


def test_parse_keys_takes_first_match() -> None:
    text = "last_commit: AAA\nlast_commit: BBB\n"
    assert parse_keys(text, ["last_commit"]) == {"last_commit": "AAA"}


def test_snapshot_round_trip(tmp_path: Path) -> None:
    parent_bb = tmp_path / "blackboard.md"
    parent_bb.write_text("last_commit: AAA\nposted: yes\n")
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    write_snapshot(task_dir, "relay-dev-update", parent_bb, ["last_commit"])

    snap = read_snapshot(task_dir)
    assert snap == StateSnapshot(parent="relay-dev-update", keys={"last_commit": "AAA"})


def test_snapshot_missing_blackboard_records_none(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    write_snapshot(task_dir, "p", tmp_path / "nope.md", ["last_commit"])
    assert read_snapshot(task_dir).keys == {"last_commit": None}


def test_read_snapshot_absent_returns_none(tmp_path: Path) -> None:
    assert read_snapshot(tmp_path) is None


def test_read_snapshot_corrupt_returns_none(tmp_path: Path) -> None:
    (tmp_path / SNAPSHOT_FILE).write_text("{not json")
    assert read_snapshot(tmp_path) is None


@pytest.mark.parametrize("payload", ["null", "[]", '"snapshot"'])
def test_read_snapshot_valid_json_non_object_returns_none(
    tmp_path: Path, payload: str
) -> None:
    (tmp_path / SNAPSHOT_FILE).write_text(payload)
    assert read_snapshot(tmp_path) is None


# --- stale_keys ---------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
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
    _write(
        company / "recurring" / "dev-update" / "ticket.md",
        """
        ---
        schedule: "0 9 * * *"
        title: "Dev update"
        mode: interactive
        assignee: claude
        owner: marc
        state_keys:
          - last_commit
        ---

        ## Description

        Post the daily digest.
        """,
    )
    _write(
        company / "recurring" / "dev-update" / "blackboard.md",
        """
        ### Dev Update State

        last_commit: AAA
        """,
    )
    return company


def test_stale_keys_flags_unchanged(repo: Path) -> None:
    cfg = load_config(repo)
    snap = StateSnapshot(parent="dev-update", keys={"last_commit": "AAA"})
    assert stale_keys(cfg, snap) == ["last_commit"]


def test_stale_keys_clears_when_advanced(repo: Path) -> None:
    cfg = load_config(repo)
    (repo / "recurring" / "dev-update" / "blackboard.md").write_text(
        "### Dev Update State\n\nlast_commit: BBB\n"
    )
    snap = StateSnapshot(parent="dev-update", keys={"last_commit": "AAA"})
    assert stale_keys(cfg, snap) == []


@pytest.mark.parametrize("text", ["### Dev Update State\n\n", "last_commit:\n"])
def test_stale_keys_flags_missing_or_blank_current_value(
    repo: Path, text: str
) -> None:
    cfg = load_config(repo)
    (repo / "recurring" / "dev-update" / "blackboard.md").write_text(text)
    snap = StateSnapshot(parent="dev-update", keys={"last_commit": "AAA"})
    assert stale_keys(cfg, snap) == ["last_commit"]


def test_stale_keys_ignores_removed_parent(repo: Path) -> None:
    cfg = load_config(repo)
    parent = repo / "recurring" / "dev-update"
    (parent / "blackboard.md").unlink()
    (parent / "ticket.md").unlink()
    parent.rmdir()
    snap = StateSnapshot(parent="dev-update", keys={"last_commit": "AAA"})
    assert stale_keys(cfg, snap) == []


# --- scaffold writes the snapshot ---------------------------------------------


def _allow_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.commands.recurring._interactive_stdio_has_tty", lambda: True
    )


def test_scaffold_snapshots_declared_keys(repo: Path) -> None:
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 6, 7, 10, 0, 0))
    period = scan.tasks[0].ref
    snap = read_snapshot(period.path)
    assert snap is not None
    assert snap.parent == "dev-update"
    assert snap.keys == {"last_commit": "AAA"}


def test_scaffold_without_state_keys_writes_no_snapshot(tmp_path: Path) -> None:
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
        company / "contexts" / "relay" / "period-task" / "SKILL.md",
        "---\nname: relay/period-task\ndescription: stub\n---\n\n# p\n",
    )
    _write(
        company / "recurring" / "plain" / "ticket.md",
        """
        ---
        schedule: "0 9 * * *"
        title: "Plain"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        No state.
        """,
    )
    cfg = load_config(company)
    scan = scan_due(cfg, now=datetime(2026, 6, 7, 10, 0, 0))
    assert read_snapshot(scan.tasks[0].ref.path) is None


@pytest.mark.parametrize(
    "state_keys_line",
    [
        "state_keys: last_commit",
        'state_keys: ""',
        "state_keys: 0",
        "state_keys: {}",
        "state_keys:",
    ],
)
def test_template_rejects_malformed_state_keys(
    tmp_path: Path, state_keys_line: str
) -> None:
    template = tmp_path / "recurring" / "bad"
    _write(
        template / "ticket.md",
        f"""
        ---
        schedule: "0 9 * * *"
        title: "Bad"
        mode: interactive
        assignee: claude
        owner: marc
        {state_keys_line}
        ---

        ## Description

        Bad state key shape.
        """,
    )
    with pytest.raises(RecurringError, match="state_keys"):
        Template.load(template)


# --- mark done warns ----------------------------------------------------------


def _scaffold_period(repo: Path) -> str:
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 6, 7, 10, 0, 0))
    return scan.tasks[0].ref.id_slug


def test_mark_done_warns_on_unchanged_cursor(repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(repo)
    slug = _scaffold_period(repo)
    # Parent blackboard untouched — the run "forgot" to advance last_commit.
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert "did not advance" in result.output
    assert "last_commit" in result.output


def test_mark_done_quiet_when_cursor_advanced(repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(repo)
    slug = _scaffold_period(repo)
    # The run recorded a new high-water mark before finishing.
    (repo / "recurring" / "dev-update" / "blackboard.md").write_text(
        "### Dev Update State\n\nlast_commit: BBB\n"
    )
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert "did not advance" not in result.output


def test_mark_done_syncs_parent_blackboard_when_cursor_advanced(
    repo: Path, monkeypatch
) -> None:
    monkeypatch.chdir(repo)
    slug = _scaffold_period(repo)
    (repo / "recurring" / "dev-update" / "blackboard.md").write_text(
        "### Dev Update State\n\nlast_commit: BBB\n"
    )

    synced: list[tuple[Path, list[Path], str]] = []

    def _capture_sync(cfg, anchor_path, paths, *, message):
        synced.append((anchor_path, list(paths), message))

    def _unexpected_task_sync(*args, **kwargs):
        raise AssertionError("state-keyed period tasks should sync explicit paths")

    monkeypatch.setattr("relay.git.sync_paths", _capture_sync)
    monkeypatch.setattr("relay.git.sync_task_state", _unexpected_task_sync)

    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output

    task_dir = repo / "tasks" / slug
    parent_blackboard = repo / "recurring" / "dev-update" / "blackboard.md"
    assert synced == [
        (task_dir, [task_dir, parent_blackboard], f"Ticket: {slug} — done")
    ]


def test_mark_done_plain_task_unaffected(repo: Path, monkeypatch) -> None:
    """A task with no snapshot (every non-recurring task) is never flagged."""
    monkeypatch.chdir(repo)
    slug = _scaffold_period(repo)
    # Drop the snapshot to simulate an ordinary (non-recurring) task.
    snap_path = next(
        ref.path / SNAPSHOT_FILE
        for ref in list_tasks(load_config(repo))
        if (ref.path / SNAPSHOT_FILE).is_file()
    )
    snap_path.unlink()
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert "did not advance" not in result.output


# --- validate sweep -----------------------------------------------------------


def test_validate_flags_done_stuck_cursor(repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(repo)
    slug = _scaffold_period(repo)
    CliRunner().invoke(app, ["mark", "done", slug])  # cursor never advanced

    from relay import validate as validate_mod

    cfg = load_config(repo)
    report = validate_mod.run(cfg)
    kinds = {(i.task, i.kind) for i in report.issues}
    assert any(
        kind == "recurring-state-stuck" and slug in task for task, kind in kinds
    ), report.issues


def test_validate_quiet_when_cursor_advanced(repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(repo)
    slug = _scaffold_period(repo)
    (repo / "recurring" / "dev-update" / "blackboard.md").write_text(
        "### Dev Update State\n\nlast_commit: BBB\n"
    )
    CliRunner().invoke(app, ["mark", "done", slug])

    from relay import validate as validate_mod

    cfg = load_config(repo)
    report = validate_mod.run(cfg)
    assert not any(i.kind == "recurring-state-stuck" for i in report.issues)
