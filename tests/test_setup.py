"""`relay setup` — one-command onboarding: init if needed, record the user
name in relay.local.toml, then launch the relay-setup interview ticket."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands import init as init_cmd
from relay.commands import launch as launch_cmd


def _seed_repo(
    root: Path, *, user: str = "", ticket_status: str | None = "active"
) -> Path:
    """Minimal already-initialized repo: relay.toml, relay.local.toml, and
    (unless ticket_status is None) a relay-setup ticket."""
    relay_os = root / "relay-os"
    relay_os.mkdir(parents=True, exist_ok=True)
    (relay_os / "relay.toml").write_text("version = 1\n")
    (relay_os / "relay.local.toml").write_text(f'user = "{user}"\n')
    if ticket_status is not None:
        task = relay_os / "tasks" / "relay-setup"
        task.mkdir(parents=True)
        (task / "ticket.md").write_text(
            f"---\ntitle: relay-setup\nstatus: {ticket_status}\n---\n\n## Description\n"
        )
    return relay_os


@pytest.fixture
def launch_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def fake_launch(task: str, **kwargs) -> None:
        calls.append(task)

    monkeypatch.setattr(launch_cmd, "launch", fake_launch)
    return calls


def test_setup_fresh_dir_inits_prompts_and_launches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_calls: list[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "company"
    init_calls: list[tuple[Path, bool]] = []

    def fake_do_init(path: Path, *, via_setup: bool = False) -> None:
        init_calls.append((path, via_setup))
        _seed_repo(path)

    monkeypatch.setattr(init_cmd, "_do_init", fake_do_init)

    result = CliRunner().invoke(app, ["setup", str(target)], input="zach\n")
    assert result.exit_code == 0, result.output

    assert init_calls == [(target.resolve(), True)]
    local = (target / "relay-os" / "relay.local.toml").read_text()
    assert 'user = "zach"' in local
    assert launch_calls == ["relay-setup"]


def test_setup_skips_satisfied_stages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_calls: list[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _seed_repo(tmp_path, user="zach")

    def no_init(path: Path, *, via_setup: bool = False) -> None:
        raise AssertionError("init must not run for an initialized repo")

    monkeypatch.setattr(init_cmd, "_do_init", no_init)

    # No stdin provided: if setup prompted for a name, the invoke would fail.
    result = CliRunner().invoke(app, ["setup", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "user: zach" in result.output
    assert launch_calls == ["relay-setup"]


def test_setup_rejects_bad_name_then_accepts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_calls: list[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _seed_repo(tmp_path, user="")

    result = CliRunner().invoke(app, ["setup", str(tmp_path)], input='za"ch\nzach\n')
    assert result.exit_code == 0, result.output
    assert "without quotes" in result.output
    local = (tmp_path / "relay-os" / "relay.local.toml").read_text()
    assert 'user = "zach"' in local
    assert launch_calls == ["relay-setup"]


def test_setup_recreates_missing_local_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_calls: list[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    relay_os = _seed_repo(tmp_path)
    (relay_os / "relay.local.toml").unlink()

    result = CliRunner().invoke(app, ["setup", str(tmp_path)], input="zach\n")
    assert result.exit_code == 0, result.output
    local = (relay_os / "relay.local.toml").read_text()
    assert 'user = "zach"' in local
    # Rest of the template (commented examples) survives alongside the value.
    assert "[secrets]" in local
    assert launch_calls == ["relay-setup"]


def test_setup_noop_when_ticket_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_calls: list[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _seed_repo(tmp_path, user="zach", ticket_status="done")

    result = CliRunner().invoke(app, ["setup", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "already done" in result.output
    # Re-running setup after it's finished still nudges toward the first move.
    assert "relay project" in result.output
    assert launch_calls == []


def test_setup_nudges_to_project_when_workflow_finishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    relay_os = _seed_repo(tmp_path, user="zach")
    ticket = relay_os / "tasks" / "relay-setup" / "ticket.md"

    def fake_launch(task: str, **kwargs) -> None:
        # Simulate the setup workflow running through its final mark-done step.
        ticket.write_text(ticket.read_text().replace("status: active", "status: done"))

    monkeypatch.setattr(launch_cmd, "launch", fake_launch)

    result = CliRunner().invoke(app, ["setup", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "Setup complete" in result.output
    assert "relay project" in result.output
    assert 'relay draft "<title>"' in result.output


def test_setup_tells_resume_when_workflow_unfinished(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_calls: list[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _seed_repo(tmp_path, user="zach")  # stays `active`; fake_launch is a no-op

    result = CliRunner().invoke(app, ["setup", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "re-run `relay setup` to resume" in result.output
    # No completion nudge when setup didn't finish.
    assert "Setup complete" not in result.output


def test_setup_explains_missing_ticket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_calls: list[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _seed_repo(tmp_path, user="zach", ticket_status=None)

    result = CliRunner().invoke(app, ["setup", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "No relay-setup ticket" in result.output
    assert launch_calls == []
