from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coga.config import Config
from coga.managed_skills import (
    ManagedSkillError,
    ManagedSkillSpec,
    install_managed_skills,
    load_managed_skill_manifest,
    reconcile_managed_skills,
)
from coga.skill_manager import SkillManagerError, SkillResult, SkillUpdateSummary


def test_load_managed_skill_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "managed-skills.toml"
    manifest.write_text(
        """
[[skills]]
ref = "tools/example"
source_type = "github"
source = "owner/repo"
required = true
"""
    )

    assert load_managed_skill_manifest(manifest) == [
        ManagedSkillSpec(
            ref="tools/example",
            source="owner/repo",
            source_type="github",
            required=True,
        )
    ]


def test_install_managed_skills_uses_installer_for_missing_skill(tmp_path: Path) -> None:
    calls: list[tuple[Path, str, str | None]] = []

    def install(cfg: Config, source: str, skill: str | None) -> SkillResult:
        calls.append((cfg.repo_root, source, skill))
        target = cfg.repo_root / "skills" / "tools" / "example"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("---\nname: tools/example\n---\n")
        return SkillResult(
            name=skill or "",
            source_type="github",
            status="installed",
            message="installed",
            changed=True,
        )

    summary = install_managed_skills(
        tmp_path,
        specs=[ManagedSkillSpec(ref="tools/example", source="owner/repo")],
        github_installer=install,
    )

    assert calls == [(tmp_path, "owner/repo", "tools/example")]
    assert summary.counts() == {"installed": 1}


def test_install_managed_skills_preserves_existing_local_skill(tmp_path: Path) -> None:
    existing = tmp_path / "skills" / "tools" / "example"
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("local\n")
    calls: list[str | None] = []

    def install(_: Config, __: str, skill: str | None) -> SkillResult:
        calls.append(skill)
        raise AssertionError("existing skills should not be reinstalled")

    summary = install_managed_skills(
        tmp_path,
        specs=[ManagedSkillSpec(ref="tools/example", source="owner/repo")],
        github_installer=install,
    )

    assert calls == []
    assert summary.counts() == {"skipped-existing": 1}
    assert existing.joinpath("SKILL.md").read_text() == "local\n"


def test_required_managed_skill_install_failure_fails_loud(tmp_path: Path) -> None:
    def install(_: Config, __: str, ___: str | None) -> SkillResult:
        raise SkillManagerError("gh skill is missing")

    with pytest.raises(ManagedSkillError) as exc:
        install_managed_skills(
            tmp_path,
            specs=[
                ManagedSkillSpec(
                    ref="tools/example",
                    source="owner/repo",
                    required=True,
                )
            ],
            github_installer=install,
        )

    assert "Required managed skill `tools/example` failed from owner/repo" in str(exc.value)
    assert "Remediation: coga skill install owner/repo tools/example" in str(exc.value)


def test_optional_managed_skill_install_failure_is_reported(tmp_path: Path) -> None:
    def install(_: Config, __: str, ___: str | None) -> SkillResult:
        raise SkillManagerError("network unavailable")

    summary = install_managed_skills(
        tmp_path,
        specs=[ManagedSkillSpec(ref="tools/example", source="owner/repo")],
        github_installer=install,
    )

    assert summary.counts() == {"failed": 1}
    [result] = summary.results
    assert result.details["required"] is False
    assert result.details["remediation"] == "coga skill install owner/repo tools/example"


def test_install_managed_skills_skips_optional_skills_from_inaccessible_source(
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    def runner(args, cwd) -> subprocess.CompletedProcess[str]:
        command = list(args)
        commands.append(command)
        if command[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(
                command,
                1,
                stdout="",
                stderr=(
                    "GraphQL: Could not resolve to a Repository with the name "
                    "'owner/private'. (repository)"
                ),
            )
        raise AssertionError(f"unexpected command past failed probe: {command}")

    summary = install_managed_skills(
        tmp_path,
        specs=[
            ManagedSkillSpec(ref="tools/one", source="owner/private"),
            ManagedSkillSpec(ref="tools/two", source="owner/private"),
        ],
        runner=runner,
    )

    # One probe for the shared source, and no `gh skill install` attempts.
    assert commands == [["gh", "repo", "view", "owner/private", "--json", "name"]]
    assert summary.counts() == {"skipped-no-access": 2}
    first = summary.results[0]
    assert "owner/private is not accessible" in first.message
    assert first.details["remediation"] == "coga skill install owner/private tools/one"
    assert "Could not resolve to a Repository" in first.details["reason"]


def test_install_managed_skills_skips_optional_skills_when_gh_missing(
    tmp_path: Path,
) -> None:
    def runner(args, cwd) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("gh")

    summary = install_managed_skills(
        tmp_path,
        specs=[ManagedSkillSpec(ref="tools/example", source="owner/repo")],
        runner=runner,
    )

    assert summary.counts() == {"skipped-no-access": 1}
    [result] = summary.results
    assert result.details["reason"] == "GitHub CLI (`gh`) is not installed"


def test_required_managed_skill_from_inaccessible_source_fails_loud(
    tmp_path: Path,
) -> None:
    def runner(args, cwd) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            list(args), 1, stdout="", stderr="HTTP 404: Not Found"
        )

    with pytest.raises(ManagedSkillError) as exc:
        install_managed_skills(
            tmp_path,
            specs=[
                ManagedSkillSpec(
                    ref="tools/core",
                    source="owner/private",
                    required=True,
                )
            ],
            runner=runner,
        )

    assert "no access to owner/private" in str(exc.value)
    assert "Remediation: coga skill install owner/private tools/core" in str(exc.value)


def test_install_managed_skills_installs_when_source_accessible(
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    def runner(args, cwd) -> subprocess.CompletedProcess[str]:
        command = list(args)
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    summary = install_managed_skills(
        tmp_path,
        specs=[ManagedSkillSpec(ref="tools/example", source="owner/repo")],
        runner=runner,
    )

    assert summary.counts() == {"installed": 1}
    assert commands[0] == ["gh", "repo", "view", "owner/repo", "--json", "name"]
    assert [
        "gh",
        "skill",
        "install",
        "owner/repo",
        "tools/example",
        "--dir",
        str(tmp_path / "skills"),
    ] in commands


def test_reconcile_managed_skills_uses_update_path_for_existing_skill(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "skills" / "tools" / "example"
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("local adaptation\n")
    updated: list[str] = []

    def update(_: Config, skill: str) -> SkillUpdateSummary:
        updated.append(skill)
        return SkillUpdateSummary(
            [
                SkillResult(
                    name=skill,
                    source_type="url",
                    status="skipped-local-adaptation",
                    message="local files differ; upstream unchanged",
                )
            ]
        )

    summary = reconcile_managed_skills(
        tmp_path,
        specs=[ManagedSkillSpec(ref="tools/example", source="https://example.test/skill")],
        updater=update,
    )

    assert updated == ["tools/example"]
    assert summary.counts() == {"skipped-local-adaptation": 1}
    assert existing.joinpath("SKILL.md").read_text() == "local adaptation\n"
