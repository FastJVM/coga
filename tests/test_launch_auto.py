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


def _write_script_task(repo: Path, *, slug: str, title: str) -> None:
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        slug: {slug}
        title: {title}
        status: active
        mode: script
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: null
        script: inline
        ---

        ## Description

        ## Script

        ```bash
        echo hi
        ```

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
        [launch]
        worktree = false
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    seed_direct_body_workflow(company)
    monkeypatch.chdir(company)
    return company


def test_launch_rejects_removed_autonomy_option(repo: Path) -> None:
    _write_script_task(repo, slug="script-run", title="Script run")

    result = CliRunner().invoke(
        app, ["launch", "script-run", "--autonomy", "interactive"]
    )

    assert result.exit_code != 0
    assert "--autonomy" in result.output


def test_prompt_report_rejects_script_mode(repo: Path) -> None:
    _write_script_task(repo, slug="script-run", title="Script run")

    result = CliRunner().invoke(app, ["launch", "script-run", "--prompt-report"])

    assert result.exit_code == 2
    assert "script tasks do not compose an agent prompt" in result.output


def test_launch_script_mode_runs_script_not_agent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_script_task(repo, slug="script-run", title="Script run")
    calls: list[str] = []

    def fake_script_mode(cfg, ref, ticket):  # type: ignore[no-untyped-def]
        calls.append(ref.id_slug)

    def fail_agent_lookup(name):  # type: ignore[no-untyped-def]
        raise AssertionError("script mode must not look up an agent CLI")

    monkeypatch.setattr("coga.commands.launch_script.run_script_mode", fake_script_mode)
    monkeypatch.setattr("coga.commands.launch.shutil.which", fail_agent_lookup)

    result = CliRunner().invoke(app, ["launch", "script-run"])

    assert result.exit_code == 0, result.output
    assert calls == ["script-run"]


def test_agent_override_rejects_script_mode(repo: Path) -> None:
    _write_script_task(repo, slug="script-run", title="Script run")

    result = CliRunner().invoke(app, ["launch", "script-run", "--agent", "claude"])

    assert result.exit_code == 2
    assert "--agent is only supported for agent launches" in result.output
