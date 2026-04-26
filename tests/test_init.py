"""`relay init` — scaffolds a relay-os/ from upstream into a target directory."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands import update as update_cmd


EXPECTED_FILES = {
    "relay-os/.gitignore",
    "relay-os/relay.toml",
    "relay-os/rules.md",
    "relay-os/context.md",
    "relay-os/counter",
    "relay-os/scripts/cron.sh",
    "relay-os/contexts/_template/SKILL.md",
    "relay-os/skills/_template/SKILL.md",
    "relay-os/workflows/_template.md",
    "relay-os/recurring/_template.md",
    "relay-os/tasks/_template/ticket.md",
}


def _seed_fake_clone(clone_dir: Path) -> None:
    """Mimic the layout of the real repo: templates + CLI source."""
    templates = clone_dir / update_cmd.TEMPLATE_SUBPATH
    templates.mkdir(parents=True)
    (templates / ".gitignore").write_text("relay.local.toml\n")
    (templates / "relay.toml").write_text("version = 1\n")
    (templates / "rules.md").write_text("rules\n")
    (templates / "context.md").write_text("context\n")
    (templates / "counter").write_text("0\n")
    (templates / "scripts").mkdir()
    (templates / "scripts" / "cron.sh").write_text("#!/bin/sh\n")
    for kind, fname in [
        ("contexts", "_template/SKILL.md"),
        ("skills", "_template/SKILL.md"),
        ("tasks", "_template/ticket.md"),
        ("workflows", "_template.md"),
        ("recurring", "_template.md"),
    ]:
        path = templates / kind / fname
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {kind} template\n")

    cli_src = clone_dir / update_cmd.CLI_SRC_SUBPATH
    cli_src.mkdir(parents=True, exist_ok=True)
    (cli_src / "__init__.py").write_text("")
    (cli_src / "cli.py").write_text("# fake cli\n")

    (clone_dir / "pyproject.toml").write_text("[project]\nname = 'relay-os'\n")
    (clone_dir / "requirements.txt").write_text("typer>=0.12\nPyYAML>=6\n")


@pytest.fixture
def fake_clone(monkeypatch: pytest.MonkeyPatch):
    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "clone"]:
            _seed_fake_clone(Path(cmd[-1]))
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess: {cmd}")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)


def test_init_into_empty_dir(tmp_path: Path, fake_clone) -> None:
    target = tmp_path / "company"
    target.mkdir()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    for rel in EXPECTED_FILES:
        assert (target / rel).is_file(), f"missing {rel}"

    assert (target / "relay-os" / "counter").read_text().strip() == "0"
    assert "version = 1" in (target / "relay-os" / "relay.toml").read_text()


def test_init_vendors_cli_and_writes_wrapper(
    tmp_path: Path, fake_clone, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    # Force the shim path off — keep this test focused on the wrapper.
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    assert (target / "relay-os" / ".relay" / "src" / "relay" / "cli.py").is_file()
    assert (target / "relay-os" / ".relay" / "pyproject.toml").is_file()
    assert (target / "relay-os" / ".relay" / "requirements.txt").is_file()

    wrapper = target / "relay-os" / ".relay" / "bin" / "relay"
    assert wrapper.is_file()
    assert wrapper.stat().st_mode & 0o111  # executable
    assert "python3 -m relay" in wrapper.read_text()

    assert "Add the bin dir to your PATH" in result.output
    assert "pip install -r" in result.output


def test_init_writes_local_toml_placeholder(
    tmp_path: Path, fake_clone, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    local_toml = target / "relay-os" / "relay.local.toml"
    assert local_toml.is_file()
    text = local_toml.read_text()
    assert 'user = ""' in text
    assert "[paths]" in text  # commented example present


def test_init_installs_shim_when_local_bin_on_path(
    tmp_path: Path, fake_clone, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")

    target = tmp_path / "company"
    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    shim = local_bin / "relay"
    assert shim.is_symlink()
    assert shim.resolve() == (target / "relay-os" / ".relay" / "bin" / "relay").resolve()
    assert "is on your PATH via" in result.output
    assert "Add the bin dir to your PATH" not in result.output


def test_init_skips_shim_when_target_exists(
    tmp_path: Path, fake_clone, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    (local_bin / "relay").write_text("# pre-existing\n")
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")

    target = tmp_path / "company"
    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    # Pre-existing file untouched, instructions fall back to PATH export.
    assert (local_bin / "relay").read_text() == "# pre-existing\n"
    assert "Add the bin dir to your PATH" in result.output


def test_init_into_non_empty_dir_is_fine(tmp_path: Path, fake_clone) -> None:
    target = tmp_path / "existing-repo"
    target.mkdir()
    (target / "README.md").write_text("hi")
    (target / "src").mkdir()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "relay-os" / "relay.toml").is_file()
    assert (target / "README.md").read_text() == "hi"


def test_init_refuses_existing_relay_os(tmp_path: Path, fake_clone) -> None:
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "relay-os").mkdir()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 2
    assert "already exists" in result.output


def test_init_creates_missing_dir(tmp_path: Path, fake_clone) -> None:
    target = tmp_path / "fresh"
    assert not target.exists()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "relay-os" / "relay.toml").is_file()
