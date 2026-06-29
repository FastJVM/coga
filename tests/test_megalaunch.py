from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.megalaunch import run_megalaunch, trim_megalaunch_blackboard_text
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [git]
        enabled = false
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "code.md",
        """
        ---
        name: code
        description: tiny.
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: owner
        ---
        """,
    )
    monkeypatch.chdir(company)
    return company


def test_megalaunch_runs_active_agent_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Run me",
        workflow_name="code",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg, ref_obj, ticket, agent, mode, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert run.results[0].slug == ref["slug"]
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_chains_agent_owned_steps(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        repo / "workflows" / "two-agent.md",
        """
        ---
        name: two-agent
        description: two agent steps.
        steps:
          - name: implement
            assignee: agent
          - name: verify
            assignee: agent
        ---
        """,
    )
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Run twice",
        workflow_name="two-agent",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    seen_steps: list[str] = []

    def fake_spawn(cfg, ref_obj, ticket, agent, mode, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        seen_steps.append(updated.step or "")
        if updated.step == "1 (implement)":
            updated.frontmatter["step"] = "2 (verify)"
            updated.frontmatter["assignee"] = "claude"
        else:
            updated.frontmatter["status"] = "done"
            updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert seen_steps == ["1 (implement)", "2 (verify)"]
    assert run.counts["completed"] == 1
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_skips_open_blocker(repo: Path) -> None:
    from typer.testing import CliRunner

    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Blocked",
        workflow_name="code",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    result = CliRunner().invoke(
        app,
        ["block", "--task", ref["slug"], "--reason", "need owner answer"],
    )
    assert result.exit_code == 0, result.output

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 0
    assert run.counts["skipped-unresolved-blocker"] == 1
    assert "need owner answer" in run.results[0].detail


def test_megalaunch_budget_guard_skips(repo: Path) -> None:
    text = (repo / "coga.toml").read_text()
    (repo / "coga.toml").write_text(
        text + "\n[megalaunch]\ndefault_token_budget = 100\ntoken_guard = 200\n"
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Too expensive",
        workflow_name="code",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 0
    assert run.counts["skipped-budget"] == 1


def test_trim_megalaunch_blackboard_replaces_old_summaries() -> None:
    text = """## Blockers

- [ ] [2026-06-29 10:00] [agent:claude] id=b1 Need answer

## Megalaunch Run Summary

old

## Decisions

Keep this.

## Megalaunch Run Summary

older
"""

    trimmed = trim_megalaunch_blackboard_text(text, "new summary\n")

    assert trimmed.count("## Megalaunch Run Summary") == 1
    assert "new summary" in trimmed
    assert "old" not in trimmed
    assert "older" not in trimmed
    assert "Need answer" in trimmed
    assert "Keep this." in trimmed
