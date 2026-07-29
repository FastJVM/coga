from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from conftest import seed_direct_body_workflow
from coga.cli import app


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_legacy_null_task(repo: Path, *, slug: str, title: str) -> None:
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        slug: {slug}
        title: {title}
        status: active
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: null
        script: null
        ---

        ## Description

        ## Context

        <!-- coga:blackboard -->

        # Blackboard
    """).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    seed_direct_body_workflow(company)
    monkeypatch.chdir(company)
    return company


def test_launch_rejects_removed_autonomy_option(repo: Path) -> None:
    _write_legacy_null_task(repo, slug="agent-run", title="Agent run")

    result = CliRunner().invoke(
        app, ["launch", "agent-run", "--autonomy", "interactive"]
    )

    assert result.exit_code != 0
    assert "--autonomy" in result.output


def test_prompt_report_tolerates_legacy_null_script_key(repo: Path) -> None:
    _write_legacy_null_task(repo, slug="agent-run", title="Agent run")

    result = CliRunner().invoke(app, ["launch", "agent-run", "--prompt-report"])

    assert result.exit_code == 0, result.output
    assert "Prompt report for agent-run" in result.output
