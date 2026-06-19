"""`relay uninstall` — removes a repo's Relay footprint, the inverse of init."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from relay import cli as relay_cli
from relay.cli import app
from relay.commands import uninstall as uninstall_cmd
from relay.commands.init import AGENT_GUIDE_TEMPLATE
from relay.commands.update import ensure_host_gitignore


def _seed_footprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_shim: bool = True,
) -> Path:
    """Build the on-disk footprint `relay init` leaves behind, and return the
    host repo root (with cwd + HOME pointed at it)."""
    target = tmp_path / "company"
    relay_os = target / "relay-os"
    relay_os.mkdir(parents=True)
    (relay_os / "relay.toml").write_text("version = 1\n")
    # Vendored CLI the shim points back into.
    bin_dir = relay_os / ".relay" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "relay").write_text("#!/bin/sh\n")
    (relay_os / ".agent-skills").mkdir()

    # Agent skill discovery symlinks.
    for agent in (".claude", ".codex"):
        skills = target / agent / "skills"
        skills.mkdir(parents=True)
        (skills / "relay").symlink_to(relay_os / ".agent-skills")

    # Root orientation guides (shipped content, unmodified).
    (target / "CLAUDE.md").write_text(AGENT_GUIDE_TEMPLATE)
    (target / "AGENTS.md").write_text(AGENT_GUIDE_TEMPLATE)

    # Relay-managed .gitignore block (needs a git dir to be written).
    (target / ".git").mkdir()
    (target / ".gitignore").write_text("node_modules/\n")
    ensure_host_gitignore(target)

    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    if with_shim:
        (local_bin / "relay").symlink_to(bin_dir / "relay")
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.chdir(target)
    return target


def test_uninstall_removes_full_footprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output

    assert not (target / "relay-os").exists()
    assert not (target / ".claude").exists()  # pruned once empty
    assert not (target / ".codex").exists()
    assert not (target / "CLAUDE.md").exists()
    assert not (target / "AGENTS.md").exists()
    assert (Path(tmp_path / "home" / ".local" / "bin" / "relay")).exists() is False
    # User .gitignore line survives; managed block is gone.
    gi = (target / ".gitignore").read_text()
    assert "node_modules/" in gi
    assert ".claude/skills/relay" not in gi


def test_uninstall_aborts_on_no_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["uninstall"], input="n\n")
    assert result.exit_code == 0, result.output
    assert "Aborted" in result.output
    # Nothing removed.
    assert (target / "relay-os").is_dir()
    assert (target / "CLAUDE.md").is_file()


def test_uninstall_confirm_yes_via_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["uninstall"], input="y\n")
    assert result.exit_code == 0, result.output
    assert not (target / "relay-os").exists()


def test_uninstall_backs_up_modified_guide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    (target / "CLAUDE.md").write_text("# my own edits\n")

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output

    # Edited guide is preserved under a backup name; the original is gone.
    assert not (target / "CLAUDE.md").exists()
    assert (target / "CLAUDE.md.relay-bak").read_text() == "# my own edits\n"
    # Unmodified guide is removed outright (no backup).
    assert not (target / "AGENTS.md").exists()
    assert not (target / "AGENTS.md.relay-bak").exists()


def test_uninstall_leaves_unrelated_shim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch, with_shim=False)
    # A `relay` on PATH that points somewhere else entirely.
    local_bin = tmp_path / "home" / ".local" / "bin"
    other = tmp_path / "other-relay"
    other.write_text("#!/bin/sh\n")
    (local_bin / "relay").symlink_to(other)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output
    assert (local_bin / "relay").is_symlink()


def test_uninstall_without_purge_prints_pip_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output
    assert "left installed" in result.output
    assert "uninstall relay-os" in result.output


def test_uninstall_purge_runs_pipx_for_pipx_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(uninstall_cmd.shutil, "which", lambda name: "/usr/bin/pipx")
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(
        uninstall_cmd, "running_cli_location", lambda relay_os: ("pipx", Path("/x"))
    )

    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert calls == [["/usr/bin/pipx", "uninstall", "relay-os"]]
    assert "Uninstalled `relay-os` via pipx" in result.output


def test_uninstall_purge_runs_pip_for_other_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(uninstall_cmd.sys, "executable", "/venv/bin/python")
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(
        uninstall_cmd, "running_cli_location", lambda relay_os: ("other", Path("/x"))
    )

    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert calls == [
        ["/venv/bin/python", "-m", "pip", "uninstall", "-y", "relay-os"]
    ]
    assert "Uninstalled `relay-os` via pip" in result.output


def test_uninstall_purge_skips_global_package_when_running_vendored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    calls: list[str] = []

    def fake_which(name: str) -> str:
        calls.append(name)
        return "/usr/bin/pipx"

    monkeypatch.setattr(uninstall_cmd.shutil, "which", fake_which)
    monkeypatch.setattr(
        uninstall_cmd, "running_cli_location", lambda relay_os: ("vendored", Path("/x"))
    )

    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert calls == []
    assert "no global package to uninstall" in result.output


def test_uninstall_errors_if_relay_os_remains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)

    monkeypatch.setattr(uninstall_cmd.shutil, "rmtree", lambda path: None)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 2
    assert "path still exists" in result.output
    assert (target / "relay-os").is_dir()
    assert "Relay uninstalled" not in result.output


def test_main_uninstall_ignores_legacy_uninstall_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    (target / "relay-os" / "relay.local.toml").write_text('user = "me"\n')
    (target / "relay-os" / "relay.toml").write_text(
        'version = 1\n[aliases]\nuninstall = "status"\n'
    )
    monkeypatch.setattr(sys, "argv", ["relay", "uninstall", "--yes"])

    with pytest.raises(SystemExit) as exc:
        relay_cli.main()

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "ignoring legacy alias 'uninstall'" in captured.err
    assert not (target / "relay-os").exists()


def test_uninstall_outside_repo_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "nowhere"
    empty.mkdir()
    monkeypatch.chdir(empty)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 2
    assert "No relay.toml" in result.output
