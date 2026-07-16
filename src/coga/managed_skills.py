"""Coga-managed skill manifest install/update helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
import tomllib

from coga.config import Config
from coga.skill_manager import (
    Downloader,
    GhSkillUnavailableError,
    Runner,
    SkillManagerError,
    SkillResult,
    SkillUpdateSummary,
    _skill_target,
    install_github_skill,
    install_url_skill,
    update_skills,
)


MANAGED_SKILL_MANIFEST_PACKAGE = "coga.resources"
MANAGED_SKILL_MANIFEST_PATH = ("managed-skills.toml",)

# Rerunning `coga skill install` after a rate-limit 403 hits the same
# anonymous per-IP quota; authenticating is what actually raises it.
GH_AUTH_REMEDIATION = "gh auth login"

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
    access_cache: dict[str, tuple[str, str]] = {}
    gh_unavailable: GhSkillUnavailableError | None = None
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
        if gh_unavailable is not None:
            if spec.required:
                raise ManagedSkillError(
                    _required_failure_message(spec, gh_unavailable)
                ) from gh_unavailable
            summary.results.append(_gh_unavailable_result(spec, gh_unavailable))
            continue
        try:
            result = _run_install(
                cfg,
                spec,
                runner=runner,
                downloader=downloader,
                github_installer=github_installer,
                access_cache=access_cache,
            )
        except GhSkillUnavailableError as exc:
            # Every manifest install goes through `gh skill`, so one missing
            # `gh skill` means they all fail identically — record it once and
            # skip the rest instead of re-probing (and re-failing) per skill.
            gh_unavailable = exc
            summary.results.append(_gh_unavailable_result(spec, exc))
            continue
        summary.results.append(result)
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
    access_cache: dict[str, tuple[str, str]] = {}
    gh_unavailable: GhSkillUnavailableError | None = None
    for spec in skill_specs:
        target = _skill_target(cfg, spec.ref)
        if not target.exists():
            if gh_unavailable is not None:
                if spec.required:
                    raise ManagedSkillError(
                        _required_failure_message(spec, gh_unavailable)
                    ) from gh_unavailable
                summary.results.append(_gh_unavailable_result(spec, gh_unavailable))
                continue
            try:
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
            except GhSkillUnavailableError as exc:
                gh_unavailable = exc
                summary.results.append(_gh_unavailable_result(spec, exc))
            continue
        if gh_unavailable is not None and spec.source_type == "github":
            if spec.required:
                raise ManagedSkillError(
                    _required_failure_message(spec, gh_unavailable)
                ) from gh_unavailable
            summary.results.append(_gh_unavailable_result(spec, gh_unavailable))
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
        except GhSkillUnavailableError as exc:
            if spec.required:
                raise ManagedSkillError(_required_failure_message(spec, exc)) from exc
            gh_unavailable = exc
            summary.results.append(_gh_unavailable_result(spec, exc))
            continue
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
    access_cache: dict[str, tuple[str, str]] | None = None,
) -> SkillResult:
    try:
        if spec.source_type == "github":
            if github_installer is not None:
                return github_installer(cfg, spec.source, spec.ref)
            cached = _cached_github_source_failure(spec.source, cache=access_cache)
            if cached is not None:
                kind, reason = cached
                if kind == "rate-limit":
                    if spec.required:
                        raise ManagedSkillError(
                            _required_failure_message(
                                spec,
                                f"GitHub API rate limit ({reason})",
                                remediation=GH_AUTH_REMEDIATION,
                            )
                        )
                    return _rate_limited_result(spec, reason)
                if spec.required:
                    raise ManagedSkillError(
                        _required_failure_message(
                            spec, f"no access to {spec.source} ({reason})"
                        )
                    )
                return _no_access_result(spec, reason)
            try:
                return install_github_skill(cfg, spec.source, spec.ref, runner=runner)
            except GhSkillUnavailableError:
                # Not an access problem — the outer handler propagates it so
                # the caller can skip the remaining manifest entries.
                raise
            except SkillManagerError as exc:
                # Rate limit first: gh's rate-limit text can suggest
                # `gh auth login`, which the access-denial markers would
                # otherwise misread as a credential problem.
                rate_limit = _github_rate_limit_reason(str(exc))
                if rate_limit is not None:
                    if access_cache is not None:
                        access_cache[spec.source.strip()] = ("rate-limit", rate_limit)
                    if spec.required:
                        raise ManagedSkillError(
                            _required_failure_message(
                                spec,
                                f"GitHub API rate limit ({rate_limit})",
                                remediation=GH_AUTH_REMEDIATION,
                            )
                        ) from exc
                    return _rate_limited_result(spec, rate_limit)
                reason = _github_access_denial_reason(str(exc))
                if reason is None:
                    raise
                if access_cache is not None:
                    access_cache[spec.source.strip()] = ("no-access", reason)
                if spec.required:
                    raise ManagedSkillError(
                        _required_failure_message(
                            spec, f"no access to {spec.source} ({reason})"
                        )
                    ) from exc
                return _no_access_result(spec, reason)
        return install_url_skill(
            cfg,
            spec.source,
            spec.selector,
            runner=runner,
            downloader=downloader,
        )
    except GhSkillUnavailableError as exc:
        if spec.required:
            raise ManagedSkillError(_required_failure_message(spec, exc)) from exc
        # Let the caller see the missing `gh skill` so it can skip the
        # remaining manifest entries instead of failing each identically.
        raise
    except SkillManagerError as exc:
        if spec.required:
            raise ManagedSkillError(_required_failure_message(spec, exc)) from exc
        return _failure_result(spec, exc)


def _cached_github_source_failure(
    source: str,
    *,
    cache: dict[str, tuple[str, str]] | None,
) -> tuple[str, str] | None:
    """Return a prior (kind, reason) failure for this source within the current run."""
    key = source.strip()
    return cache.get(key) if cache is not None else None


def _github_access_denial_reason(output: str) -> str | None:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return None
    access_markers = (
        "could not resolve to a repository",
        "not logged into any github hosts",
        "authentication failed",
        "bad credentials",
        "requires authentication",
        "must authenticate",
        "gh auth login",
        "resource not accessible by",
        "saml enforcement",
        "grant your oauth token access",
        "http 401",
        "http 404",
    )
    for line in lines:
        normalized = line.casefold()
        if any(marker in normalized for marker in access_markers):
            return line
    return None


def _github_rate_limit_reason(output: str) -> str | None:
    """Return an anonymous rate-limit line, dropping the request-ID blob."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    normalized_output = " ".join(lines).casefold()
    if "authenticated requests get a higher rate limit" not in normalized_output:
        return None
    for line in lines:
        normalized = line.casefold()
        if "api rate limit exceeded" in normalized:
            return line
    return None


def _rate_limited_result(spec: ManagedSkillSpec, reason: str) -> SkillResult:
    return SkillResult(
        name=spec.ref,
        source_type=spec.source_type,
        status="skipped-rate-limited",
        message=(
            f"optional skill skipped — GitHub API rate limit reached while "
            f"fetching from {spec.source} ({reason})"
        ),
        details={
            "source": spec.source,
            "required": spec.required,
            "remediation": GH_AUTH_REMEDIATION,
            "reason": reason,
        },
    )


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


def _gh_unavailable_result(
    spec: ManagedSkillSpec, exc: GhSkillUnavailableError
) -> SkillResult:
    return SkillResult(
        name=spec.ref,
        source_type=spec.source_type,
        status="skipped-old-gh",
        message=str(exc),
        details={
            "source": spec.source,
            "required": spec.required,
            "remediation": spec.remediation_command(),
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


def _required_failure_message(
    spec: ManagedSkillSpec, exc: object, *, remediation: str | None = None
) -> str:
    return (
        f"Required managed skill `{spec.ref}` failed from {spec.source}: {exc}\n"
        f"Remediation: {remediation or spec.remediation_command()}"
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
