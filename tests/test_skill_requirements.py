"""Tests for per-skill dependency installation at bootstrap.

`install_skill_requirements` is what makes a skill bring its own Python deps:
it pip-installs every project-local and bundled-package `requirements.txt`
into the `.coga/.venv`. Tests fake `subprocess.run` so nothing is actually
installed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import coga.commands.update as update_cmd
from coga.commands.update import install_skill_requirements


def _ok(*args, **kwargs):  # type: ignore[no-untyped-def]
    return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")


def _mk_req(skills_dir: Path, ref: str, body: str = "somedep>=1\n") -> Path:
    skill = skills_dir / ref
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\nname: {ref}\n---\n")
    req = skill / "requirements.txt"
    req.write_text(body)
    return req


def test_no_skills_dir_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty_package_skills = tmp_path / "package-skills"
    empty_package_skills.mkdir()
    monkeypatch.setattr(
        update_cmd, "packaged_bootstrap_skills_dir", lambda: empty_package_skills
    )
    assert install_skill_requirements(tmp_path, tmp_path / ".venv") == []


def test_skills_dir_without_requirements_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty_package_skills = tmp_path / "package-skills"
    empty_package_skills.mkdir()
    monkeypatch.setattr(
        update_cmd, "packaged_bootstrap_skills_dir", lambda: empty_package_skills
    )
    (tmp_path / "skills" / "coga" / "x").mkdir(parents=True)
    assert install_skill_requirements(tmp_path, tmp_path / ".venv") == []


def test_installs_each_requirements_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Both roots are scanned: project-local skills/ and bundled package skills.
    package_skills = tmp_path / "package-skills"
    req_a = _mk_req(package_skills, "coga/google-calendar")
    req_b = _mk_req(tmp_path / "skills", "team/other")

    calls: list[list[str]] = []

    def fake_run(cmd, capture_output=False, text=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _ok()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        update_cmd, "packaged_bootstrap_skills_dir", lambda: package_skills
    )
    venv = tmp_path / ".venv"
    installed = install_skill_requirements(tmp_path, venv)

    assert installed == sorted([req_a, req_b])
    # one pip invocation per requirements file, each targeting the venv python
    # with `-r <file>`.
    assert len(calls) == 2
    for cmd in calls:
        assert cmd[0] == str(venv / "bin" / "python")
        assert "-r" in cmd
    installed_targets = {cmd[cmd.index("-r") + 1] for cmd in calls}
    assert installed_targets == {str(req_a), str(req_b)}


def test_failed_install_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mk_req(tmp_path / "skills", "coga/google-calendar")

    def fake_run(cmd, capture_output=False, text=False):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        install_skill_requirements(tmp_path, tmp_path / ".venv")


def test_failed_install_hash_mode_prints_remediation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A pip forced into hash-checking mode (PIP_REQUIRE_HASHES=1 on managed
    # machines) rejects requirement files without pinned hashes; the failure
    # message must name the setting and the escape hatch, not just dump pip
    # stderr.
    _mk_req(tmp_path / "skills", "coga/google-calendar")

    pip_stderr = (
        "ERROR: Hashes are required in --require-hashes mode, but they are "
        "missing from some requirements."
    )

    def fake_run(cmd, capture_output=False, text=False):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr=pip_stderr
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        install_skill_requirements(tmp_path, tmp_path / ".venv")
    err = capsys.readouterr().err
    assert "hash-checking mode" in err
    assert "PIP_REQUIRE_HASHES=0" in err


def test_hash_checking_hint_recognizes_pip_hash_errors() -> None:
    # The four shapes pip's hash-checking mode actually emits: unpinned
    # requirements, missing hashes, local directories, and the editable-install
    # refusal.
    unpinned = (
        "ERROR: In --require-hashes mode, all requirements must have their "
        "versions pinned with ==. These do not:\n    coga"
    )
    missing = (
        "ERROR: Hashes are required in --require-hashes mode, but they are "
        "missing from some requirements."
    )
    local_directory = (
        "ERROR: Can't verify hashes for these file:// requirements because "
        "they point to directories:\n    file:///src/coga"
    )
    editable = (
        "ERROR: The editable requirement file:///src/coga cannot be installed "
        "when requiring hashes, because there is no single file to hash."
    )
    for stderr in (unpinned, missing, local_directory, editable):
        assert "PIP_REQUIRE_HASHES=0" in update_cmd.hash_checking_hint(stderr)


def test_hash_checking_hint_empty_for_other_failures() -> None:
    other = "ERROR: No matching distribution found for somedep>=1"
    assert update_cmd.hash_checking_hint(other) == ""
