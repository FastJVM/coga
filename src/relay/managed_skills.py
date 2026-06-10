"""Relay-managed skill manifest install/update helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from pathlib import PurePosixPath
import tomllib

from relay.config import Config
from relay.skill_manager import (
    Downloader,
    Runner,
    SkillManagerError,
    SkillResult,
    SkillUpdateSummary,
    install_github_skill,
    install_url_skill,
    skills_root,
    update_skills,
)


MANAGED_SKILL_MANIFEST_PACKAGE = "relay.resources"
MANAGED_SKILL_MANIFEST_PATH = ("managed-skills.toml",)

GithubInstaller = Callable[
    [Config, str, str | None],
    SkillResult,
]
UrlInstaller = Callable[
    [Config, str, str | None],
    SkillResult,
]
SkillUpdater = Callable[[Config, str], SkillUpdateSummary]


class ManagedSkillError(Exception):
    """Raised when required Relay-managed skill reconciliation fails."""


@dataclass(frozen=True)
class ManagedSkillSpec:
    ref: str
    source: str
    source_type: str = "github"
    required: bool = False
    selector: str | None = None

    def remediation_command(self) -> str:
        if self.source_type == "github":
            return f"relay skill install {self.source} {self.ref}"
        if self.source_type == "url":
            selector = f" {self.selector}" if self.selector else ""
            return f"relay skill install-url {self.source}{selector}"
        return "check relay managed skill manifest"


@dataclass
class ManagedSkillSummary:
    results: list[SkillResult] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
        return counts


def managed_skill_manifest_root() -> Traversable:
    return files(MANAGED_SKILL_MANIFEST_PACKAGE).joinpath(*MANAGED_SKILL_MANIFEST_PATH)


def load_managed_skill_manifest(
    manifest: Traversable | Path | None = None,
) -> list[ManagedSkillSpec]:
    manifest = manifest or managed_skill_manifest_root()
    if not manifest.is_file():
        return []
    data = tomllib.loads(manifest.read_text())
    raw_skills = data.get("skills", [])
    if not isinstance(raw_skills, list):
        raise ManagedSkillError("managed-skills.toml: `skills` must be an array")

    specs: list[ManagedSkillSpec] = []
    for index, raw in enumerate(raw_skills, 1):
        if not isinstance(raw, dict):
            raise ManagedSkillError(
                f"managed-skills.toml: skills[{index}] must be a table"
            )
        ref = raw.get("ref")
        source = raw.get("source")
        if not isinstance(ref, str) or not ref.strip():
            raise ManagedSkillError(
                f"managed-skills.toml: skills[{index}].ref must be a string"
            )
        if not isinstance(source, str) or not source.strip():
            raise ManagedSkillError(
                f"managed-skills.toml: skills[{index}].source must be a string"
            )
        source_type = raw.get("source_type", "github")
        if source_type not in {"github", "url"}:
            raise ManagedSkillError(
                f"managed-skills.toml: skills[{index}].source_type must be "
                "'github' or 'url'"
            )
        required = raw.get("required", False)
        if not isinstance(required, bool):
            raise ManagedSkillError(
                f"managed-skills.toml: skills[{index}].required must be a bool"
            )
        selector = raw.get("selector")
        if selector is not None and not isinstance(selector, str):
            raise ManagedSkillError(
                f"managed-skills.toml: skills[{index}].selector must be a string"
            )
        specs.append(
            ManagedSkillSpec(
                ref=ref.strip(),
                source=source.strip(),
                source_type=source_type,
                required=required,
                selector=selector,
            )
        )
    return specs


def install_managed_skills(
    relay_os: Path,
    *,
    specs: Sequence[ManagedSkillSpec] | None = None,
    runner: Runner | None = None,
    downloader: Downloader | None = None,
    github_installer: GithubInstaller | None = None,
    url_installer: UrlInstaller | None = None,
) -> ManagedSkillSummary:
    cfg = _manifest_skill_config(relay_os)
    summary = ManagedSkillSummary()
    skill_specs = specs if specs is not None else load_managed_skill_manifest()
    for spec in skill_specs:
        target = _skill_target(cfg, spec.ref)
        if target.exists():
            summary.results.append(
                SkillResult(
                    name=spec.ref,
                    source_type=spec.source_type,
                    status="skipped-existing",
                    message="local skill already exists; not overwriting",
                    details={"source": spec.source, "required": spec.required},
                )
            )
            continue
        summary.results.append(
            _run_install(
                cfg,
                spec,
                runner=runner,
                downloader=downloader,
                github_installer=github_installer,
                url_installer=url_installer,
            )
        )
    return summary


def reconcile_managed_skills(
    relay_os: Path,
    *,
    specs: Sequence[ManagedSkillSpec] | None = None,
    runner: Runner | None = None,
    downloader: Downloader | None = None,
    github_installer: GithubInstaller | None = None,
    url_installer: UrlInstaller | None = None,
    updater: SkillUpdater | None = None,
) -> ManagedSkillSummary:
    cfg = _manifest_skill_config(relay_os)
    summary = ManagedSkillSummary()
    skill_specs = specs if specs is not None else load_managed_skill_manifest()
    for spec in skill_specs:
        target = _skill_target(cfg, spec.ref)
        if not target.exists():
            summary.results.append(
                _run_install(
                    cfg,
                    spec,
                    runner=runner,
                    downloader=downloader,
                    github_installer=github_installer,
                    url_installer=url_installer,
                )
            )
            continue
        try:
            if updater is not None:
                update_summary = updater(cfg, spec.ref)
            else:
                update_summary = update_skills(
                    cfg,
                    spec.ref,
                    runner=runner,
                    downloader=downloader,
                )
        except SkillManagerError as exc:
            result = _failure_result(spec, exc)
            if spec.required:
                raise ManagedSkillError(_required_failure_message(spec, exc)) from exc
            summary.results.append(result)
            continue
        for result in update_summary.results:
            if spec.required and result.status == "failed":
                raise ManagedSkillError(
                    _required_failure_message(spec, result.message)
                )
            summary.results.append(result)
    return summary


def _run_install(
    cfg: Config,
    spec: ManagedSkillSpec,
    *,
    runner: Runner | None,
    downloader: Downloader | None,
    github_installer: GithubInstaller | None,
    url_installer: UrlInstaller | None,
) -> SkillResult:
    try:
        if spec.source_type == "github":
            if github_installer is not None:
                return github_installer(cfg, spec.source, spec.ref)
            return install_github_skill(cfg, spec.source, spec.ref, runner=runner)
        if url_installer is not None:
            return url_installer(cfg, spec.source, spec.selector)
        return install_url_skill(
            cfg,
            spec.source,
            spec.selector,
            runner=runner,
            downloader=downloader,
        )
    except SkillManagerError as exc:
        if spec.required:
            raise ManagedSkillError(_required_failure_message(spec, exc)) from exc
        return _failure_result(spec, exc)


def _failure_result(spec: ManagedSkillSpec, exc: object) -> SkillResult:
    return SkillResult(
        name=spec.ref,
        source_type=spec.source_type,
        status="failed",
        message=str(exc),
        details={
            "source": spec.source,
            "required": spec.required,
            "remediation": spec.remediation_command(),
        },
    )


def _required_failure_message(spec: ManagedSkillSpec, exc: object) -> str:
    return (
        f"Required managed skill `{spec.ref}` failed from {spec.source}: {exc}\n"
        f"Remediation: {spec.remediation_command()}"
    )


def _skill_target(cfg: Config, ref: str) -> Path:
    cleaned = ref.strip()
    path = PurePosixPath(cleaned)
    if not cleaned or str(path) == "." or path.is_absolute():
        raise ManagedSkillError(f"Invalid managed skill ref: {ref!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ManagedSkillError(f"Invalid managed skill ref: {ref!r}")
    return skills_root(cfg).joinpath(*path.parts)


def _manifest_skill_config(relay_os: Path) -> Config:
    return Config(
        repo_root=relay_os,
        current_user="",
        default_status="draft",
        agents={},
        slack_webhook=None,
        slack_enabled=False,
        secrets={},
    )
