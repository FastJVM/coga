from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import tomllib


EXPECTED_BOOTSTRAP_RESOURCES = (
    "relay/resources/templates/relay-os/bootstrap/skills/relay/"
    "calendar-reminder/SKILL.md",
    "relay/resources/templates/relay-os/bootstrap/skills/eval/"
    "ticket-diagnostic/SKILL.md",
    "relay/resources/templates/relay-os/bootstrap/skills/"
    "google-agents-cli-workflow/SKILL.md",
    "relay/resources/templates/relay-os/bootstrap/contexts/relay/sync/SKILL.md",
)


def test_package_force_includes_relay_resources() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text())

    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]

    assert force_include["src/relay/resources"] == "relay/resources"
    for wheel_name in EXPECTED_BOOTSTRAP_RESOURCES:
        source_name = wheel_name.removeprefix("relay/resources/")
        assert (repo_root / "src" / "relay" / "resources" / source_name).is_file()


def test_wheel_includes_bootstrap_batteries(tmp_path: Path) -> None:
    pytest.importorskip("hatchling")
    repo_root = Path(__file__).resolve().parents[1]
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--quiet",
            "--no-build-isolation",
            "--no-deps",
            ".",
            "-w",
            str(wheel_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    [wheel] = wheel_dir.glob("relay_os-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    for name in EXPECTED_BOOTSTRAP_RESOURCES:
        assert name in names
