from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.create import create_task
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
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(
        company / "relay.local.toml",
        '''
        user = "marc"
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
            skills:
              - ops/checker
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
    script.write_text(
        "#!/bin/sh\n"
        "{\n"
        "  echo \"token=$token\"\n"
        "  echo \"source=$TEST_TOKEN\"\n"
        "  echo \"slug=$RELAY_TASK_SLUG\"\n"
        "  echo \"dir=$RELAY_TASK_DIR\"\n"
        "  echo \"blackboard=$RELAY_TASK_BLACKBOARD\"\n"
        "} > \"$PWD/script-output.txt\"\n"
    )
    script.chmod(0o755)

    monkeypatch.chdir(company)
    return company


def test_script_mode_executes_and_injects_secrets(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_TOKEN", "secret-abc")
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "check"])
    assert result.exit_code == 0, result.output

    # Script wrote to the host repo (parent of relay-os/) with the secret
    output = (cfg.repo_root.parent / "script-output.txt").read_text()
    assert "token=secret-abc" in output
    assert "source=\n" in output
    assert "slug=check" in output
    # File-form task has no per-task directory, so RELAY_TASK_DIR is the
    # `tasks/` parent the ticket file lives in.
    assert f"dir={ref.path.parent.resolve()}" in output
    # Single-file format: the blackboard region lives in the ticket file, so
    # RELAY_TASK_BLACKBOARD points at the ticket itself.
    assert f"blackboard={ref.ticket_path.resolve()}" in output

    # Log records launch + exit (in the repo-global log)
    log = (repo / "log.md").read_text()
    assert "launched as a script" in log
    assert "script exited with code 0" in log


def _set_ticket_secrets(ref, value) -> None:
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["secrets"] = value
    t.write(ref.ticket_path)


def test_script_mode_fails_loud_on_unset_declared_secret(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TEST_TOKEN", raising=False)
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    _set_ticket_secrets(ref, ["token"])

    result = CliRunner().invoke(app, ["launch", "check"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "token" in combined and "TEST_TOKEN" in combined
    # Fail-loud means the script never ran.
    assert not (cfg.repo_root.parent / "script-output.txt").exists()
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "active"
    log = (repo / "log.md").read_text()
    assert "started (active" not in log


def test_script_mode_least_privilege_empty_list_injects_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_TOKEN", "secret-abc")
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    _set_ticket_secrets(ref, [])

    result = CliRunner().invoke(app, ["launch", "check"])
    assert result.exit_code == 0, result.output
    output = (cfg.repo_root.parent / "script-output.txt").read_text()
    # `secrets: []` is a strict lockdown — the token is withheld even though
    # TEST_TOKEN is set in the environment.
    assert "token=\n" in output
    assert "source=\n" in output


def test_script_mode_rejects_agent_override(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "check", "--agent", "claude"])
    assert result.exit_code == 2
    assert "--agent is only supported for agent (interactive/auto) launches" in (
        result.output + (result.stderr or "")
    )


def test_script_mode_requires_skill_field(repo: Path) -> None:
    # Rewrite SKILL.md without `script:`
    skill_md = repo / "skills" / "ops" / "checker" / "SKILL.md"
    skill_md.write_text("---\nname: ops/checker\n---\n")
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "check"])
    assert result.exit_code == 2
    assert "script" in result.output.lower()


def test_script_mode_nonzero_exit_logged(repo: Path) -> None:
    script = repo / "skills" / "ops" / "checker" / "check.sh"
    script.write_text("#!/bin/sh\nexit 3\n")
    script.chmod(0o755)

    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Fail", workflow_name="ops",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fail"])
    assert result.exit_code == 3
    ref = list_tasks(cfg)[0]
    log = (repo / "log.md").read_text()
    assert "script exited with code 3" in log
