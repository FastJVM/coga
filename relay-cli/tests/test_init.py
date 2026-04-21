"""Tests for relay_os.commands.init.

`relay init <project>` scaffolds the per-project `relay-os/` directory
inside the path declared for that project in `relay.local.toml`.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from relay_os.cli import main


@pytest.fixture
def initialized_repo(tmp_path: Path) -> Path:
    """A tmp_path with relay.toml + relay.local.toml declaring a 'demo'
    project pointing at ./demo-proj."""
    (tmp_path / "relay.toml").write_text(dedent("""\
        version = 1

        [projects.demo]
        type = "local"
        default_status = "ready"
    """))
    (tmp_path / "relay.local.toml").write_text(dedent("""\
        user = "zach"

        [paths]
        demo = "./demo-proj"
    """))
    return tmp_path


def test_init_creates_relay_os(initialized_repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(initialized_repo)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "demo"])
    assert result.exit_code == 0, result.output

    project = initialized_repo / "demo-proj"
    assert (project / "relay-os").is_dir()
    assert (project / "relay-os" / "tasks").is_dir()
    assert (project / "relay-os" / "context.md").is_file()
    assert (project / "relay-os" / "counter").read_text() == "1\n"


def test_init_is_idempotent(initialized_repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(initialized_repo)
    runner = CliRunner()
    assert runner.invoke(main, ["init", "demo"]).exit_code == 0

    counter = initialized_repo / "demo-proj" / "relay-os" / "counter"
    counter.write_text("42\n")  # simulate tasks having been created
    result = runner.invoke(main, ["init", "demo"])
    assert result.exit_code == 0, result.output
    assert counter.read_text() == "42\n", "second init must not reset counter"


def test_init_errors_on_missing_project_arg(tmp_path: Path, monkeypatch) -> None:
    """With no positional argument, click should surface its standard
    missing-argument error, not a traceback."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code != 0
    assert "PROJECT" in result.output or "project" in result.output.lower()


def test_init_errors_on_unknown_project(
    initialized_repo: Path, monkeypatch
) -> None:
    monkeypatch.chdir(initialized_repo)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "nonesuch"])
    assert result.exit_code != 0
    assert "no project named" in result.output


def test_init_errors_when_not_in_relay_repo(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "demo"])
    assert result.exit_code != 0
    assert "not inside a Relay repo" in result.output


def test_init_errors_on_unmapped_path(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "relay.toml").write_text(dedent("""\
        [projects.demo]
        type = "local"
    """))
    (tmp_path / "relay.local.toml").write_text('user = "zach"\n')
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "demo"])
    assert result.exit_code != 0
    assert "no path" in result.output
