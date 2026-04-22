from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands.create import scaffold_task
from relay.config import load_config
from relay.tasks import list_tasks


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "relay-os"
    project = tmp_path / "projects" / "email-tool"
    project.mkdir(parents=True)
    _write(
        company / "relay.toml",
        f"""
        version = 1
        [projects.email-tool]
        type = "local"
        default_status = "ready"
        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {{"claude1" = "claude"}}
        """,
    )
    _write(
        company / "relay.local.toml",
        f'''
        user = "marc"
        [paths]
        email-tool = "{project}"
        [secrets]
        token = "env:TEST_TOKEN"
        ''',
    )
    _write(
        company / "workflows" / "ops.md",
        """
        ---
        name: ops
        description: single-step.
        steps:
          - name: run
            skill: ops/checker
        ---
        """,
    )
    _write(
        company / "skills" / "ops" / "checker" / "SKILL.md",
        """
        ---
        name: ops/checker
        description: runs a health check.
        script: check.sh
        ---

        Runs the check.
        """,
    )
    script = company / "skills" / "ops" / "checker" / "check.sh"
    script.write_text("#!/bin/sh\necho \"token=$token\" > \"$PWD/script-output.txt\"\n")
    script.chmod(0o755)

    monkeypatch.chdir(company)
    return company


def test_script_mode_executes_and_injects_secrets(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_TOKEN", "secret-abc")
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, project="email-tool", title="Check", workflow_name="ops",
        contexts=[], mode="script", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg, "email-tool")[0]

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "--task", "email-tool/001"])
    assert result.exit_code == 0, result.output

    # Script wrote to the project path (cwd) with the secret
    output = (cfg.projects["email-tool"].path / "script-output.txt").read_text()
    assert "token=secret-abc" in output

    # Log records launch + exit
    log = (ref.path / "log.md").read_text()
    assert "launched in script mode" in log
    assert "script exited with code 0" in log

    # Lock released
    assert not (ref.path / "task.lock").exists()


def test_script_mode_requires_skill_field(repo: Path) -> None:
    # Rewrite SKILL.md without `script:`
    skill_md = repo / "skills" / "ops" / "checker" / "SKILL.md"
    skill_md.write_text("---\nname: ops/checker\n---\n")
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, project="email-tool", title="Check", workflow_name="ops",
        contexts=[], mode="script", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "--task", "email-tool/001"])
    assert result.exit_code == 2
    assert "script" in result.output.lower()


def test_script_mode_nonzero_exit_logged(repo: Path) -> None:
    script = repo / "skills" / "ops" / "checker" / "check.sh"
    script.write_text("#!/bin/sh\nexit 3\n")
    script.chmod(0o755)

    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, project="email-tool", title="Fail", workflow_name="ops",
        contexts=[], mode="script", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "--task", "email-tool/001"])
    assert result.exit_code == 3
    ref = list_tasks(cfg, "email-tool")[0]
    log = (ref.path / "log.md").read_text()
    assert "script exited with code 3" in log
