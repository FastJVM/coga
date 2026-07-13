from __future__ import annotations

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
from coga.skill_manager import (
    GhSkillUnavailableError,
    SkillManagerError,
    SkillResult,
    SkillUpdateSummary,
)


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


def test_install_managed_skills_detects_old_gh_once_and_skips_rest(
    tmp_path: Path,
) -> None:
    calls: list[str | None] = []

    def install(_: Config, __: str, skill: str | None) -> SkillResult:
        calls.append(skill)
        raise GhSkillUnavailableError("GitHub CLI 2.90.0+ with `gh skill` is required")

    summary = install_managed_skills(
        tmp_path,
        specs=[
            ManagedSkillSpec(ref="tools/one", source="owner/repo"),
            ManagedSkillSpec(ref="tools/two", source="owner/repo"),
            ManagedSkillSpec(ref="tools/three", source="owner/repo"),
        ],
        github_installer=install,
    )

    assert calls == ["tools/one"]
    assert summary.counts() == {"skipped-old-gh": 3}
    for result in summary.results:
        assert "gh skill" in result.message
        assert result.details["remediation"].startswith("coga skill install owner/repo")


def test_required_managed_skill_fails_loud_on_old_gh(tmp_path: Path) -> None:
    def install(_: Config, __: str, ___: str | None) -> SkillResult:
        raise GhSkillUnavailableError("GitHub CLI 2.90.0+ with `gh skill` is required")

    with pytest.raises(ManagedSkillError) as exc:
        install_managed_skills(
            tmp_path,
            specs=[
                ManagedSkillSpec(ref="tools/optional", source="owner/repo"),
                ManagedSkillSpec(ref="tools/core", source="owner/repo", required=True),
            ],
            github_installer=install,
        )

    assert "Required managed skill `tools/core` failed from owner/repo" in str(exc.value)


def test_reconcile_managed_skills_detects_old_gh_once_and_skips_rest(
    tmp_path: Path,
) -> None:
    for name in ("one", "two"):
        existing = tmp_path / "skills" / "tools" / name
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("local\n")
    updated: list[str] = []

    def update(_: Config, skill: str) -> SkillUpdateSummary:
        updated.append(skill)
        raise GhSkillUnavailableError("GitHub CLI 2.90.0+ with `gh skill` is required")

    summary = reconcile_managed_skills(
        tmp_path,
        specs=[
            ManagedSkillSpec(ref="tools/one", source="owner/repo"),
            ManagedSkillSpec(ref="tools/two", source="owner/repo"),
        ],
        updater=update,
    )

    assert updated == ["tools/one"]
    assert summary.counts() == {"skipped-old-gh": 2}


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
