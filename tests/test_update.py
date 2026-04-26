"""`relay update` — refresh vendored CLI + `_template` scaffolds from upstream."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands import update as update_cmd


def _seed_local_relay_os(root: Path) -> Path:
    """Stand in for `relay init` — make a relay-os/ with vendored CLI + scaffolds."""
    relay_os = root / "relay-os"
    (relay_os / "skills" / "_template").mkdir(parents=True)
    (relay_os / "tasks" / "_template").mkdir(parents=True)
    (relay_os / "skills" / "_template" / "SKILL.md").write_text("OLD skill template\n")
    (relay_os / "tasks" / "_template" / "ticket.md").write_text("OLD ticket template\n")
    (relay_os / "skills" / "myteam" / "real-skill").mkdir(parents=True)
    (relay_os / "skills" / "myteam" / "real-skill" / "SKILL.md").write_text("user content\n")
    (relay_os / "relay.toml").write_text("version = 1\n")

    vendored = relay_os / ".relay" / "src" / "relay"
    vendored.mkdir(parents=True)
    (vendored / "cli.py").write_text("# OLD vendored cli\n")
    return relay_os


def _seed_fake_upstream(clone_dir: Path) -> None:
    """Mimic the layout of the real repo: templates + CLI source."""
    templates = clone_dir / update_cmd.TEMPLATE_SUBPATH
    (templates / "skills" / "_template").mkdir(parents=True)
    (templates / "tasks" / "_template").mkdir(parents=True)
    (templates / "skills" / "_template" / "SKILL.md").write_text("NEW skill template\n")
    (templates / "tasks" / "_template" / "ticket.md").write_text("NEW ticket template\n")
    (templates / "rules.md").write_text("NEW rules — should NOT be copied (no _ prefix)\n")

    cli_src = clone_dir / update_cmd.CLI_SRC_SUBPATH
    cli_src.mkdir(parents=True, exist_ok=True)
    (cli_src / "cli.py").write_text("# NEW vendored cli\n")

    (clone_dir / "pyproject.toml").write_text("[project]\nname = 'relay-os'\n")


def test_update_refreshes_cli_and_underscore_templates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "clone"]:
            _seed_fake_upstream(Path(cmd[-1]))
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess: {cmd}")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    result = CliRunner().invoke(app, ["update"])
    assert result.exit_code == 0, result.output

    assert (relay_os / "skills" / "_template" / "SKILL.md").read_text() == "NEW skill template\n"
    assert (relay_os / "tasks" / "_template" / "ticket.md").read_text() == "NEW ticket template\n"
    assert (relay_os / "skills" / "myteam" / "real-skill" / "SKILL.md").read_text() == "user content\n"
    assert not (relay_os / "rules.md").exists()

    assert (relay_os / ".relay" / "src" / "relay" / "cli.py").read_text() == "# NEW vendored cli\n"
    assert (relay_os / ".relay" / "pyproject.toml").is_file()

    wrapper = relay_os / ".relay" / "bin" / "relay"
    assert wrapper.is_file()
    assert wrapper.stat().st_mode & 0o111
    assert "python3 -m relay" in wrapper.read_text()


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
