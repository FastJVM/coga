"""Coga-managed skill manifest install/update helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
import tomllib

from coga.config import Config
from coga.github_source import github_owner_repo
from coga.skill_manager import (
    Downloader,
    Runner,
    SkillManagerError,
    SkillResult,
    SkillUpdateSummary,
    _skill_target,
    install_github_skill,
    install_url_skill,
    run_subprocess,
    update_skills,
)


MANAGED_SKILL_MANIFEST_PACKAGE = "coga.resources"
MANAGED_SKILL_MANIFEST_PATH = ("managed-skills.toml",)

GithubInstaller = Callable[
    [Config, str, str | None],
    SkillResult,
]
SkillUpdater = Callable[[Config, str], SkillUpdateSummary]


class ManagedSkillError(Exception):
    """Raised when required Coga-managed skill reconciliation fails."""


@dataclass(frozen=True)
class ManagedSkillSpec:
    ref: str
    source: str
    source_type: str = "github"
    required: bool = False
    selector: str | None = None

    def remediation_command(self) -> str:
        if self.source_type == "github":
            return f"coga skill install {self.source} {self.ref}"
        if self.source_type == "url":
            selector = f" {self.selector}" if self.selector else ""
            return f"coga skill install-url {self.source}{selector}"
        return "check coga managed skill manifest"


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
    coga_os: Path,
    *,
    specs: Sequence[ManagedSkillSpec] | None = None,
    runner: Runner | None = None,
    downloader: Downloader | None = None,
    github_installer: GithubInstaller | None = None,
) -> ManagedSkillSummary:
    cfg = _manifest_skill_config(coga_os)
    summary = ManagedSkillSummary()
    skill_specs = specs if specs is not None else load_managed_skill_manifest()
    access_cache: dict[str, str | None] = {}
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
                access_cache=access_cache,
            )
        )
    return summary


def reconcile_managed_skills(
    coga_os: Path,
    *,
    specs: Sequence[ManagedSkillSpec] | None = None,
    runner: Runner | None = None,
    downloader: Downloader | None = None,
    github_installer: GithubInstaller | None = None,
    updater: SkillUpdater | None = None,
) -> ManagedSkillSummary:
    cfg = _manifest_skill_config(coga_os)
    summary = ManagedSkillSummary()
    skill_specs = specs if specs is not None else load_managed_skill_manifest()
    access_cache: dict[str, str | None] = {}
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
                    access_cache=access_cache,
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
    access_cache: dict[str, str | None] | None = None,
) -> SkillResult:
    try:
        if spec.source_type == "github":
            if github_installer is not None:
                return github_installer(cfg, spec.source, spec.ref)
            # Managed manifests routinely pull several skills from one source
            # repo, and an onboarding user often can't see that repo at all
            # (private, or gh unauthenticated). Probe each unique source once
            # instead of letting every `gh skill install` fail separately.
            reason = _github_source_unavailable_reason(
                spec.source, runner=runner, cache=access_cache
            )
            if reason is not None:
                if spec.required:
                    raise ManagedSkillError(
                        _required_failure_message(
                            spec, f"no access to {spec.source} ({reason})"
                        )
                    )
                return _no_access_result(spec, reason)
            return install_github_skill(cfg, spec.source, spec.ref, runner=runner)
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


def _github_source_unavailable_reason(
    source: str,
    *,
    runner: Runner | None,
    cache: dict[str, str | None] | None,
) -> str | None:
    """Return why `source` can't be reached through `gh`, or None if it can.

    Cached per reconcile/install run so a manifest with many skills from one
    repo probes that repo once, not once per skill.
    """
    key = source.strip()
    if cache is not None and key in cache:
        return cache[key]
    reason = _probe_github_source(key, runner=runner)
    if cache is not None:
        cache[key] = reason
    return reason


def _probe_github_source(source: str, *, runner: Runner | None) -> str | None:
    target = github_owner_repo(source) or source
    command = ["gh", "repo", "view", target, "--json", "name"]
    try:
        result = (runner or run_subprocess)(command, None)
    except FileNotFoundError:
        return "GitHub CLI (`gh`) is not installed"
    if result.returncode == 0:
        return None
    output = result.stderr or result.stdout
    reason = _github_access_denial_reason(output)
    if reason is not None:
        return reason
    # A failed reachability probe is not necessarily an access denial. Let the
    # real installer report rate limits, network outages, and other operational
    # failures through the existing optional/required failure path.
    return None


def _github_access_denial_reason(output: str) -> str | None:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return None
    normalized = output.casefold()
    access_markers = (
        "could not resolve to a repository",
        "not logged into any github hosts",
        "authentication failed",
        "bad credentials",
        "requires authentication",
        "must authenticate",
        "gh auth login",
        "resource not accessible by",
        "http 401",
        "http 404",
    )
    if any(marker in normalized for marker in access_markers):
        return lines[0]
    return None


def _no_access_result(spec: ManagedSkillSpec, reason: str) -> SkillResult:
    return SkillResult(
        name=spec.ref,
        source_type=spec.source_type,
        status="skipped-no-access",
        message=(
            f"optional skill skipped — {spec.source} is not accessible with "
            f"your GitHub credentials ({reason})"
        ),
        details={
            "source": spec.source,
            "required": spec.required,
            "remediation": spec.remediation_command(),
            "reason": reason,
        },
    )


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


def _manifest_skill_config(coga_os: Path) -> Config:
    return Config(
        repo_root=coga_os,
        current_user="",
        default_status="draft",
        agents={},
        slack_webhook=None,
        slack_enabled=False,
    )
