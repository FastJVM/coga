from __future__ import annotations

from pathlib import Path

import pytest

from relay.config import Config
from relay.managed_skills import (
    ManagedSkillError,
    ManagedSkillSpec,
    install_managed_skills,
    load_managed_skill_manifest,
    reconcile_managed_skills,
)
from relay.skill_manager import SkillManagerError, SkillResult, SkillUpdateSummary


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
    assert "Remediation: relay skill install owner/repo tools/example" in str(exc.value)


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
    assert result.details["remediation"] == "relay skill install owner/repo tools/example"


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
