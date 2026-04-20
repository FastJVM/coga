"""Tests for relay_os.commands.init.

Covers both modes (``relay init`` and ``relay init --project``), the
bundled templates that ship in the wheel, idempotency, and the drift
guard that keeps the package-data templates in sync with the repo-root
reference files.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from relay_os.cli import main
from relay_os.config import RelayConfig


REPO_ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------
# relay init  (repo mode)
# --------------------------------------------------------------------


def test_init_creates_full_structure_in_empty_dir(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as cwd:
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0, result.output

        root = Path(cwd)
        for d in ("skills", "contexts", "workflows", "recurring", "scripts"):
            assert (root / d).is_dir()
        for f in (
            "relay.toml",
            "relay.local.toml",
            "rules.md",
            "protocol.md",
            "protocol-interactive.md",
            "protocol-auto.md",
            "scripts/cron.sh",
            ".gitignore",
        ):
            assert (root / f).is_file(), f"missing {f}"

        assert (root / "scripts" / "cron.sh").stat().st_mode & 0o111, (
            "cron.sh should be executable"
        )
        assert "relay.local.toml" in (root / ".gitignore").read_text()


def test_init_produces_loadable_config(tmp_path: Path) -> None:
    """The bundled relay.toml + relay.local.toml pair must load through
    RelayConfig without a user touching anything. A broken starter
    template would silently ship otherwise."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as cwd:
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0, result.output
        cfg = RelayConfig.load(start=Path(cwd))
        assert cfg.shared.projects == {}
        assert cfg.shared.agents == {}


def test_init_is_idempotent(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as cwd:
        root = Path(cwd)

        assert runner.invoke(main, ["init"]).exit_code == 0
        (root / "rules.md").write_text("custom user content\n")

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0, result.output
        assert (root / "rules.md").read_text() == "custom user content\n", (
            "second init must not overwrite user edits"
        )
        assert "skipped" in result.output


# --------------------------------------------------------------------
# relay init --project  (project mode)
# --------------------------------------------------------------------


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


def test_init_project_creates_relay_os(initialized_repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(initialized_repo)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", "demo"])
    assert result.exit_code == 0, result.output

    project = initialized_repo / "demo-proj"
    assert (project / "relay-os").is_dir()
    assert (project / "relay-os" / "tasks").is_dir()
    assert (project / "relay-os" / "context.md").is_file()
    assert (project / "relay-os" / "counter").read_text() == "1\n"


def test_init_project_is_idempotent(
    initialized_repo: Path, monkeypatch
) -> None:
    monkeypatch.chdir(initialized_repo)
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--project", "demo"]).exit_code == 0

    counter = initialized_repo / "demo-proj" / "relay-os" / "counter"
    counter.write_text("42\n")  # simulate tasks having been created
    result = runner.invoke(main, ["init", "--project", "demo"])
    assert result.exit_code == 0, result.output
    assert counter.read_text() == "42\n", "second init must not reset counter"


def test_init_project_errors_on_unknown_project(
    initialized_repo: Path, monkeypatch
) -> None:
    monkeypatch.chdir(initialized_repo)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", "nonesuch"])
    assert result.exit_code != 0
    assert "no project named" in result.output


def test_init_project_errors_when_not_in_relay_repo(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", "demo"])
    assert result.exit_code != 0
    assert "not inside a Relay repo" in result.output


def test_init_project_errors_on_unmapped_path(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "relay.toml").write_text(dedent("""\
        [projects.demo]
        type = "local"
    """))
    (tmp_path / "relay.local.toml").write_text('user = "zach"\n')
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", "demo"])
    assert result.exit_code != 0
    assert "no path" in result.output


# --------------------------------------------------------------------
# Drift guard: bundled templates == repo-root canonical files
# --------------------------------------------------------------------
#
# Option A of the plan: templates are duplicated under the package so
# they ship with the wheel. This test asserts the copies stay in sync
# with the canonical files at the repo root — editing one without the
# other fails CI.


TEMPLATE_PAIRS = [
    ("relay.toml.empty", "relay.toml"),
    ("relay.local.toml.empty", "relay.local.toml"),
    ("protocol.md", "protocol.md"),
    ("protocol-interactive.md", "protocol-interactive.md"),
    ("protocol-auto.md", "protocol-auto.md"),
    ("scripts/cron.sh", "cron.sh"),
]


@pytest.mark.parametrize("repo_file,template_file", TEMPLATE_PAIRS)
def test_bundled_template_matches_repo_root(
    repo_file: str, template_file: str
) -> None:
    from importlib.resources import files as resource_files

    repo_content = (REPO_ROOT / repo_file).read_text()
    template_content = (
        resource_files("relay_os.templates").joinpath(template_file).read_text()
    )
    assert repo_content == template_content, (
        f"bundled template {template_file!r} has drifted from "
        f"{repo_file!r} at the repo root"
    )
