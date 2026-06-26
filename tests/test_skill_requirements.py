"""Tests for per-skill dependency installation at bootstrap.

`install_skill_requirements` is what makes a bootstrapped skill bring its own
Python deps: it pip-installs every `coga/skills/**/requirements.txt` into
the `.coga/.venv`. Tests fake `subprocess.run` so nothing is actually
installed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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


def test_no_skills_dir_is_noop(tmp_path: Path) -> None:
    assert install_skill_requirements(tmp_path, tmp_path / ".venv") == []


def test_skills_dir_without_requirements_is_noop(tmp_path: Path) -> None:
    (tmp_path / "skills" / "coga" / "x").mkdir(parents=True)
    assert install_skill_requirements(tmp_path, tmp_path / ".venv") == []


def test_installs_each_requirements_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Both roots are scanned: project-local skills/ and bundled bootstrap/skills/.
    req_a = _mk_req(tmp_path / "bootstrap" / "skills", "coga/google-calendar")
    req_b = _mk_req(tmp_path / "skills", "team/other")

    calls: list[list[str]] = []

    def fake_run(cmd, capture_output=False, text=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _ok()

    monkeypatch.setattr(subprocess, "run", fake_run)
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
