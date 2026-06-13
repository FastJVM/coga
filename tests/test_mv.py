"""`relay mv` — relocate a task between top-level and a group directory."""

from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.paths import tasks_dir
from relay.scaffold import scaffold_task
from relay.tasks import list_tasks
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "relay-os"
    company.mkdir()
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
        mode = "local"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


def _new_task(cfg, title: str, *, group: str | None = None, status: str | None = None):
    """Scaffold a task, optionally relocating it into a group by hand.

    The grouped setup uses a manual move (not `scaffold_task(group=...)`) so
    these tests stay independent of the create-time grouping PR — `relay mv`
    is exercised against tasks however they came to be grouped.
    """
    res = scaffold_task(
        cfg=cfg,
        title=title,
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=status,
    )
    if group:
        dest = tasks_dir(cfg) / group / res["slug"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(res["path"]), str(dest))
        return {"slug": res["slug"], "path": dest, "group": group}
    return res


def test_mv_into_group(repo: Path) -> None:
    cfg = load_config(repo)
    _new_task(cfg, "Build the flow")

    result = CliRunner().invoke(app, ["mv", "build-the-flow", "--group", "killer-demo"])
    assert result.exit_code == 0, result.output
    assert "build-the-flow → killer-demo/build-the-flow" in result.output

    assert not (repo / "tasks" / "build-the-flow").exists()
    assert (repo / "tasks" / "killer-demo" / "build-the-flow" / "ticket.md").is_file()
    assert "killer-demo/build-the-flow" in {r.id_slug for r in list_tasks(cfg)}


def test_mv_ungroup_back_to_top_level(repo: Path) -> None:
    cfg = load_config(repo)
    _new_task(cfg, "Build the flow", group="killer-demo")

    result = CliRunner().invoke(app, ["mv", "killer-demo/build-the-flow", "--ungroup"])
    assert result.exit_code == 0, result.output
    assert "killer-demo/build-the-flow → build-the-flow" in result.output
    assert (repo / "tasks" / "build-the-flow" / "ticket.md").is_file()
    assert "build-the-flow" in {r.id_slug for r in list_tasks(cfg)}


def test_mv_requires_a_destination(repo: Path) -> None:
    cfg = load_config(repo)
    _new_task(cfg, "Build the flow")
    result = CliRunner().invoke(app, ["mv", "build-the-flow"])
    assert result.exit_code == 2
    assert "Pass a destination" in result.output


def test_mv_rejects_both_flags(repo: Path) -> None:
    cfg = load_config(repo)
    _new_task(cfg, "Build the flow")
    result = CliRunner().invoke(
        app, ["mv", "build-the-flow", "--group", "g", "--ungroup"]
    )
    assert result.exit_code == 2
    assert "not both" in result.output


def test_mv_noop_when_already_in_target_group(repo: Path) -> None:
    cfg = load_config(repo)
    _new_task(cfg, "Build the flow", group="killer-demo")
    result = CliRunner().invoke(
        app, ["mv", "killer-demo/build-the-flow", "--group", "killer-demo"]
    )
    assert result.exit_code == 2
    assert "already in group" in result.output


def test_mv_refuses_in_progress(repo: Path) -> None:
    cfg = load_config(repo)
    res = _new_task(cfg, "Build the flow")
    t = Ticket.read(res["path"] / "ticket.md")
    t.frontmatter["status"] = "in_progress"
    t.write(res["path"] / "ticket.md")

    result = CliRunner().invoke(app, ["mv", "build-the-flow", "--group", "killer-demo"])
    assert result.exit_code == 2
    assert "in_progress" in result.output
    # Not moved.
    assert (repo / "tasks" / "build-the-flow" / "ticket.md").is_file()


def test_mv_refuses_destination_collision(repo: Path) -> None:
    cfg = load_config(repo)
    # Create the grouped one first so the top-level "set-up" leaf stays free.
    _new_task(cfg, "Set up", group="killer-demo")  # killer-demo/set-up
    _new_task(cfg, "Set up")  # top-level set-up

    result = CliRunner().invoke(app, ["mv", "set-up", "--group", "killer-demo"])
    assert result.exit_code == 2
    assert "Destination already exists" in result.output


def test_mv_rejects_bad_group_name(repo: Path) -> None:
    cfg = load_config(repo)
    _new_task(cfg, "Build the flow")
    result = CliRunner().invoke(app, ["mv", "build-the-flow", "--group", "Nested/Bad"])
    assert result.exit_code == 2
    assert "don't nest" in result.output or "must be a slug" in result.output


def test_mv_rejects_group_colliding_with_top_level_task(repo: Path) -> None:
    cfg = load_config(repo)
    _new_task(cfg, "Onboarding")  # top-level task "onboarding"
    _new_task(cfg, "Build the flow")
    result = CliRunner().invoke(app, ["mv", "build-the-flow", "--group", "onboarding"])
    assert result.exit_code == 2
    assert "existing top-level task" in result.output


def test_mv_unknown_task(repo: Path) -> None:
    load_config(repo)
    result = CliRunner().invoke(app, ["mv", "does-not-exist", "--group", "g"])
    assert result.exit_code == 2
