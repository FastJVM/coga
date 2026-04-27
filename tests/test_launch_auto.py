from __future__ import annotations

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
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "ready"
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
    monkeypatch.chdir(company)
    return company


def test_launch_auto_mode(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="Auto run", workflow_name=None,
        contexts=[], mode="auto", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )
    captured: dict = {}

    class _R:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["env_keys"] = set(env or {})
        return _R()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "--task", "001"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert cmd[0] == "claude"
    assert cmd[1] == "-p"
    # Last arg is the full prompt text, not a file path
    assert "Relay task — 001-auto-run" in cmd[2]
    assert "Auto mode" in cmd[2]

    # Lock released
    ref = list_tasks(cfg)[0]
    assert not (ref.path / "task.lock").exists()
