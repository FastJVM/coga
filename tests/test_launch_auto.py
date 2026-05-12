from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.scaffold import scaffold_task
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
    result = runner.invoke(app, ["launch", "auto-run"])
    assert result.exit_code == 0, result.output
    assert "Launch: task auto-run (status=active, mode=auto, assignee=claude1)" in result.output
    assert "Launch: agent claude1 -> claude (cli=claude)" in result.output
    assert "Launch: found agent CLI at /usr/bin/claude" in result.output
    assert "Launch: prompt written to" in result.output
    assert "Launch: command: claude -p '<prompt-text " in result.output
    assert "Launch: agent exited with code 0" in result.output
    assert "Launch: reading task state after agent exit" in result.output

    cmd = captured["cmd"]
    assert cmd[0] == "claude"
    assert cmd[1] == "-p"
    # Last arg is the full prompt text, not a file path
    assert "Relay task — auto-run" in cmd[2]
    assert "Auto mode" in cmd[2]



def test_launch_auto_stream_json_writes_tokens_to_log(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stream-json launches append a `tokens: ...` line to log.md."""
    import json
    import subprocess

    # Override agent so the command path includes --output-format stream-json.
    _write(
        repo / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p --output-format stream-json"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )

    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="Stream run", workflow_name=None,
        contexts=[], mode="auto", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )

    fake_result_event = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 12300,
        "total_cost_usd": 0.0456,
        "num_turns": 5,
        "usage": {
            "input_tokens": 9000,
            "output_tokens": 1200,
            "cache_creation_input_tokens": 300,
            "cache_read_input_tokens": 7000,
        },
    }

    class _FakeProc:
        def __init__(self) -> None:
            import io as _io
            self.stdout = _io.StringIO(json.dumps(fake_result_event) + "\n")
        def wait(self) -> int:
            return 0
        def terminate(self) -> None:
            pass

    def fake_popen(cmd, env=None, stdout=None, text=None, bufsize=None):  # type: ignore[no-untyped-def]
        return _FakeProc()

    monkeypatch.setattr("relay.commands.launch.subprocess.Popen", fake_popen)
    monkeypatch.setattr(
        "relay.commands.launch.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(args=[], returncode=0),
    )
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "stream-run"])
    assert result.exit_code == 0, result.output

    ref = list_tasks(cfg)[0]
    log_text = (ref.path / "log.md").read_text()
    token_lines = [ln for ln in log_text.splitlines() if "tokens:" in ln]
    assert len(token_lines) == 1, log_text
    line = token_lines[0]
    assert "[agent:claude1]" in line
    assert "in=9000" in line
    assert "out=1200" in line
    assert "cache_read=7000" in line
    assert "cache_create=300" in line
    assert "cost=$0.0456" in line
    assert "turns=5" in line
    assert "duration=12.3s" in line


def test_launch_auto_non_stream_does_not_log_tokens(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-stream-json auto launches cannot attribute tokens, so log no `tokens:` line."""
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="Plain run", workflow_name=None,
        contexts=[], mode="auto", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )

    class _R:
        returncode = 0

    monkeypatch.setattr(
        "relay.commands.launch.subprocess.run",
        lambda *a, **kw: _R(),
    )
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "plain-run"])
    assert result.exit_code == 0, result.output

    ref = list_tasks(cfg)[0]
    log_text = (ref.path / "log.md").read_text()
    assert "tokens:" not in log_text
