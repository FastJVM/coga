"""`relay init` — scaffolds the bundled template into a target directory."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from relay.cli import app


EXPECTED_FILES = {
    ".gitignore",
    "relay.toml",
    "rules.md",
    "context.md",
    "counter",
    "scripts/cron.sh",
    "contexts/.gitkeep",
    "skills/.gitkeep",
    "workflows/.gitkeep",
    "recurring/.gitkeep",
    "tasks/.gitkeep",
}


def test_init_into_empty_dir(tmp_path: Path) -> None:
    target = tmp_path / "company"
    target.mkdir()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    for rel in EXPECTED_FILES:
        assert (target / rel).is_file(), f"missing {rel}"

    assert (target / "counter").read_text().strip() == "1"
    assert "version = 1" in (target / "relay.toml").read_text()


def test_init_refuses_non_empty(tmp_path: Path) -> None:
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "existing.txt").write_text("hi")

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 2
    assert "not empty" in result.output


def test_init_creates_missing_dir(tmp_path: Path) -> None:
    target = tmp_path / "fresh"
    assert not target.exists()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "relay.toml").is_file()
