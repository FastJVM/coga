"""`relay update` — refresh CLI + `_template` scaffolds from upstream."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands import update as update_cmd


def _seed_local_relay_os(root: Path) -> Path:
    """Stand in for `relay init` — make a relay-os/ with a relay.toml."""
    relay_os = root / "relay-os"
    (relay_os / "skills" / "_template").mkdir(parents=True)
    (relay_os / "tasks" / "_template").mkdir(parents=True)
    (relay_os / "skills" / "_template" / "SKILL.md").write_text("OLD skill template\n")
    (relay_os / "tasks" / "_template" / "ticket.md").write_text("OLD ticket template\n")
    (relay_os / "skills" / "myteam" / "real-skill").mkdir(parents=True)
    (relay_os / "skills" / "myteam" / "real-skill" / "SKILL.md").write_text("user content\n")
    (relay_os / "relay.toml").write_text("version = 1\n")
    return relay_os


def _seed_fake_upstream(clone_dir: Path) -> None:
    """Mimic the layout of the real repo: src/relay/resources/templates/relay-os/."""
    templates = clone_dir / update_cmd.TEMPLATE_SUBPATH
    (templates / "skills" / "_template").mkdir(parents=True)
    (templates / "tasks" / "_template").mkdir(parents=True)
    (templates / "skills" / "_template" / "SKILL.md").write_text("NEW skill template\n")
    (templates / "tasks" / "_template" / "ticket.md").write_text("NEW ticket template\n")
    (templates / "rules.md").write_text("NEW rules — should NOT be copied (no _ prefix)\n")


def test_update_refreshes_underscore_templates_and_leaves_user_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "clone"]:
            clone_dir = Path(cmd[-1])
            _seed_fake_upstream(clone_dir)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:3] == [__import__("sys").executable, "-m", "pip"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess: {cmd}")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(update_cmd, "_is_editable_install", lambda: True)

    result = CliRunner().invoke(app, ["update"])
    assert result.exit_code == 0, result.output

    assert (relay_os / "skills" / "_template" / "SKILL.md").read_text() == "NEW skill template\n"
    assert (relay_os / "tasks" / "_template" / "ticket.md").read_text() == "NEW ticket template\n"
    assert (relay_os / "skills" / "myteam" / "real-skill" / "SKILL.md").read_text() == "user content\n"
    assert not (relay_os / "rules.md").exists()


def test_update_fails_loudly_if_clone_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="fatal: nope\n")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    result = CliRunner().invoke(app, ["update"])
    assert result.exit_code == 2
    assert "git clone failed" in result.output


def test_update_skips_pip_for_editable_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    pip_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "clone"]:
            _seed_fake_upstream(Path(cmd[-1]))
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "pip" in cmd:
            pip_calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess: {cmd}")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(update_cmd, "_is_editable_install", lambda: True)

    result = CliRunner().invoke(app, ["update"])
    assert result.exit_code == 0
    assert pip_calls == []
    assert "Editable install detected" in result.output


def test_update_runs_pip_for_non_editable_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    pip_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "clone"]:
            _seed_fake_upstream(Path(cmd[-1]))
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "pip" in cmd:
            pip_calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess: {cmd}")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(update_cmd, "_is_editable_install", lambda: False)

    result = CliRunner().invoke(app, ["update"])
    assert result.exit_code == 0
    assert len(pip_calls) == 1
    assert pip_calls[0][:4] == [
        __import__("sys").executable,
        "-m",
        "pip",
        "install",
    ]
    assert "--upgrade" in pip_calls[0]
