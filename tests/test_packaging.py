from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import tomllib


EXPECTED_BOOTSTRAP_RESOURCES = (
    "coga/resources/managed-skills.toml",
    "coga/resources/templates/coga/bootstrap/orient/ticket.md",
    "coga/resources/templates/coga/bootstrap/project/ticket.md",
    "coga/resources/templates/coga/bootstrap/ticket/ticket.md",
    "coga/resources/templates/coga/bootstrap/skills/bootstrap/"
    "ticket/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/eval/"
    "ticket-diagnostic/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/"
    "autoclose/sweep/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/"
    "autoclose/sweep/run.py",
    "coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md",
    "coga/resources/templates/coga/recurring/autoclose-merged/ticket.md",
    "coga/resources/templates/coga/recurring/digest/ticket.md",
    "coga/resources/templates/coga/recurring/digest/spool.md",
    "coga/resources/templates/coga/recurring/skill-update/ticket.md",
    "coga/resources/templates/coga/workflows/autoclose-merged/sweep.md",
    "coga/resources/templates/coga/workflows/direct/body.md",
    "coga/resources/templates/coga/workflows/skill-update/run.md",
    # Bundled reusable workflows ship under bootstrap/workflows/ (local-first
    # fallback) so a fresh repo can run the core code loop, the docs flow, the
    # Dream child workflows, and the digest battery without hand-copying.
    "coga/resources/templates/coga/bootstrap/workflows/code/"
    "with-review.md",
    "coga/resources/templates/coga/bootstrap/workflows/code/"
    "design-then-implement.md",
    "coga/resources/templates/coga/bootstrap/workflows/dev/"
    "with-self-review.md",
    "coga/resources/templates/coga/bootstrap/workflows/docs/"
    "create-google-doc.md",
    "coga/resources/templates/coga/bootstrap/workflows/dream/"
    "validate-drift.md",
    "coga/resources/templates/coga/bootstrap/workflows/dream/"
    "cleanup-orphan-markers.md",
    "coga/resources/templates/coga/bootstrap/workflows/digest/post.md",
    # …and the code/* and digest-flush skills those workflows reference.
    "coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/implement/"
    "SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/digest/flush/"
    "SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/digest/flush/"
    "run.py",
    "coga/resources/templates/coga/skills/_template/SKILL.md",
    "coga/resources/templates/coga/skills/direct/body/SKILL.md",
)


def test_package_includes_coga_resources() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text())

    # Resources live inside the `coga` package (`src/coga/resources/...`), so
    # declaring `packages = ["src/coga"]` ships them — no separate
    # `force-include` is needed (#259 dropped that duplicate). Guard that the
    # package is still declared and that the bootstrap battery sources exist on
    # disk to be shipped. `test_wheel_includes_bootstrap_batteries` proves they
    # actually land in a built wheel.
    packages = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert "src/coga" in packages
    for wheel_name in EXPECTED_BOOTSTRAP_RESOURCES:
        source_name = wheel_name.removeprefix("coga/resources/")
        assert (repo_root / "src" / "coga" / "resources" / source_name).is_file()


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

    [wheel] = wheel_dir.glob("coga-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    for name in EXPECTED_BOOTSTRAP_RESOURCES:
        assert name in names
