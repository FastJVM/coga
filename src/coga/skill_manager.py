"""Coga-managed skill install, update, status, and removal helpers."""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from coga.config import Config
from coga.github_source import github_owner_repo
from coga.paths import packaged_template_path
from coga.skill import Skill


SOURCE_METADATA = ".coga-source.json"
SOURCE_SCHEMA = "coga.skill-source.v1"
# Dedicated branch the `--pr` flow commits skill updates onto. The flow is
# launched from the control-plane checkout (on `main` during a Dream run), so
# updates must never be committed or pushed on the caller's branch.
SKILL_UPDATE_BRANCH = "coga/skill-update"
GH_SKILL_REQUIRED = (
    "GitHub CLI 2.90.0+ with `gh skill` is required for this command. "
    "Upgrade `gh`, then verify with `gh skill --help`."
)

Runner = Callable[[Sequence[str], Path | None], subprocess.CompletedProcess[str]]
Downloader = Callable[[str], bytes]


class SkillManagerError(Exception):
    """Raised for user-facing skill-management failures."""


class GhSkillUnavailableError(SkillManagerError):
    """Raised when `gh skill` is unavailable — gh missing or older than 2.90."""


@dataclass
class SkillResult:
    name: str
    source_type: str
    status: str
    message: str
    changed: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    command: str
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class SkillUpdateSummary:
    results: list[SkillResult] = field(default_factory=list)
    verification: list[VerificationResult] = field(default_factory=list)
    pr_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
        return {
            "counts": counts,
            "results": [asdict(result) for result in self.results],
            "verification": [asdict(result) for result in self.verification],
            "pr_url": self.pr_url,
        }


@dataclass(frozen=True)
class MaterializedSkill:
    path: Path
    source_digest: str
    source_tree_digest: str


def skills_root(cfg: Config) -> Path:
    return cfg.repo_root / "skills"


def bundled_skills_root(cfg: Config) -> Path:
    return packaged_template_path("bootstrap", "skills")


def install_github_skill(
    cfg: Config,
    source: str,
    skill: str | None = None,
    *,
    runner: Runner | None = None,
) -> SkillResult:
    args = ["install", source]
    if skill:
        args.append(skill)
    args.extend(["--dir", str(skills_root(cfg))])
    run_gh_skill(args, runner=runner)
    name = skill or source
    return SkillResult(
        name=name,
        source_type="github",
        status="installed",
        message=f"installed {name} through gh skill",
        changed=True,
        details={"command": ["gh", "skill", *args]},
    )


def install_local_skill(
    cfg: Config,
    path: Path,
    skill: str | None = None,
    *,
    runner: Runner | None = None,
) -> SkillResult:
    source = path.expanduser().resolve()
    if not source.is_dir():
        raise SkillManagerError(f"Local skill path is not a directory: {source}")
    args = ["install", str(source)]
    if skill:
        args.append(skill)
    args.extend(["--from-local", "--dir", str(skills_root(cfg))])
    run_gh_skill(args, runner=runner)
    name = skill or source.name
    return SkillResult(
        name=name,
        source_type="local",
        status="installed",
        message=f"installed {name} through gh skill --from-local",
        changed=True,
        details={"command": ["gh", "skill", *args]},
    )


def install_url_skill(
    cfg: Config,
    url: str,
    selector: str | None = None,
    *,
    force: bool = False,
    runner: Runner | None = None,
    downloader: Downloader | None = None,
    now: Callable[[], str] | None = None,
) -> SkillResult:
    ensure_gh_skill(runner=runner)
    data = (downloader or download_url)(url)
    with tempfile.TemporaryDirectory(prefix="coga-skill-url-") as tmp:
        materialized = materialize_url_skill(url, data, Path(tmp), selector)
        skill_ref = _skill_ref_for_dir(materialized.path)
        args = [
            "install",
            str(materialized.path),
            "--from-local",
            "--dir",
            str(skills_root(cfg)),
        ]
        if force:
            args.append("--force")
        target = _skill_target(cfg, skill_ref)
        metadata = read_source_metadata(target) if target.is_dir() else None
        installed_digest = (
            metadata.get("installed_tree_digest")
            if metadata and metadata.get("source_type") == "url"
            else None
        )
        dirty_existing_skill = bool(
            installed_digest and hash_skill_tree(target) != installed_digest
        )
        if dirty_existing_skill and not force:
            raise SkillManagerError(
                f"{skill_ref} has local adaptations; rerun with --force to overwrite."
            )
        run_gh_skill(args, runner=runner, checked=True)
        if not target.is_dir():
            raise SkillManagerError(
                "`gh skill install` completed, but the expected Coga skill "
                f"path is missing: {target}"
            )
        installed_tree_digest = hash_skill_tree(target)
        metadata = _url_metadata(
            url=url,
            selector=selector,
            installed_ref=skill_ref,
            source_digest=materialized.source_digest,
            source_tree_digest=materialized.source_tree_digest,
            installed_tree_digest=installed_tree_digest,
            timestamp=(now or utc_now)(),
        )
        write_source_metadata(target, metadata)
        return SkillResult(
            name=skill_ref,
            source_type="url",
            status="installed",
            message=f"installed {skill_ref} from {url}",
            changed=True,
            details={
                "source_digest": materialized.source_digest,
                "installed_path": str(target),
            },
        )


def update_skills(
    cfg: Config,
    skill: str | None = None,
    *,
    all_skills: bool = False,
    runner: Runner | None = None,
    downloader: Downloader | None = None,
    now: Callable[[], str] | None = None,
) -> SkillUpdateSummary:
    if all_skills and skill:
        raise SkillManagerError("Pass either a skill name or --all, not both.")
    if not all_skills and not skill:
        raise SkillManagerError("Pass a skill name, or use --all.")

    summary = SkillUpdateSummary()
    bundled_refs = _bundled_skill_refs(cfg)
    if all_skills:
        local_skill_dirs = list_installed_skill_dirs(skills_root(cfg))
        if local_skill_dirs:
            summary.results.append(_update_gh_backed_skills(cfg, runner=runner))
        for skill_dir in local_skill_dirs:
            metadata = read_source_metadata(skill_dir)
            if metadata and metadata.get("source_type") == "url":
                summary.results.append(
                    _update_url_skill_dir(
                        cfg,
                        skill_dir,
                        metadata,
                        downloader=downloader,
                        now=now,
                    )
                )
        local_refs = {
            _skill_ref_from_path(skills_root(cfg), skill_dir)
            for skill_dir in local_skill_dirs
        }
        for ref in sorted(bundled_refs - local_refs):
            summary.results.append(_bundled_update_result(ref))
        return summary

    skill_ref = skill or ""
    target_path = _skill_target(cfg, skill_ref)
    if not target_path.exists() and skill_ref in bundled_refs:
        summary.results.append(_bundled_update_result(skill_ref))
        return summary

    target = resolve_installed_skill_dir(cfg, skill_ref)
    metadata = read_source_metadata(target)
    if metadata and metadata.get("source_type") == "url":
        summary.results.append(
            _update_url_skill_dir(
                cfg,
                target,
                metadata,
                downloader=downloader,
                now=now,
            )
        )
        return summary

    args = ["update", "--dir", str(skills_root(cfg)), skill_ref]
    run_gh_skill(args, runner=runner)
    summary.results.append(
        SkillResult(
            name=skill_ref,
            source_type="github",
            status="delegated",
            message=f"delegated {skill} update to gh skill",
            changed=True,
            details={"command": ["gh", "skill", *args]},
        )
    )
    return summary


def status_skills(
    cfg: Config,
    *,
    check: bool = False,
    downloader: Downloader | None = None,
) -> list[SkillResult]:
    results: list[SkillResult] = []
    bundled_refs = _bundled_skill_refs(cfg)
    local_refs: set[str] = set()
    for skill_dir in list_installed_skill_dirs(skills_root(cfg)):
        ref = _skill_ref_from_path(skills_root(cfg), skill_dir)
        local_refs.add(ref)
        metadata = read_source_metadata(skill_dir)
        if metadata and metadata.get("source_type") == "url":
            result = _status_url_skill(
                ref,
                skill_dir,
                metadata,
                check=check,
                downloader=downloader,
            )
            if ref in bundled_refs:
                result = _local_override_result(result)
            results.append(result)
            continue
        source_type = _infer_non_coga_source_type(skill_dir)
        if source_type == "github":
            status = "delegated"
            message = "managed by gh skill metadata"
        else:
            status = "unmanaged"
            message = "no Coga source metadata"
        result = SkillResult(
            name=ref,
            source_type=source_type,
            status=status,
            message=message,
        )
        if ref in bundled_refs:
            result = _local_override_result(result)
        results.append(result)
    for ref in sorted(bundled_refs - local_refs):
        results.append(_bundled_status_result(ref))
    return results


def resolve_installed_skill_dir(cfg: Config, skill_ref: str) -> Path:
    target = _skill_target(cfg, skill_ref)
    if not target.exists():
        raise SkillManagerError(f"Installed skill not found: {skill_ref}")
    if not (target / "SKILL.md").is_file():
        raise SkillManagerError(f"Exact skill path has no SKILL.md: {target}")
    return target


def remove_skill(cfg: Config, skill_ref: str) -> Path:
    target = resolve_installed_skill_dir(cfg, skill_ref)
    if target.is_symlink():
        target.unlink()
    else:
        shutil.rmtree(target)
    return target


def run_skill_update_pr_flow(
    cfg: Config,
    summary: SkillUpdateSummary,
    *,
    title: str,
    verification_commands: Sequence[str],
    runner: Runner | None = None,
    branch: str = SKILL_UPDATE_BRANCH,
) -> SkillUpdateSummary:
    changed = [result for result in summary.results if result.changed]
    if not changed:
        # `update_skills` wrote nothing to the working tree, so there is nothing
        # to commit. Opening a PR with no diff just fails on `gh pr create`, so
        # leave `pr_url` unset and let the caller report a clean no-op.
        return summary

    run = runner or run_subprocess
    git_cwd = cfg.repo_root.parent
    _assert_no_unmerged_paths(run, git_cwd)
    original_branch = _current_git_branch(run, git_cwd)
    try:
        committed = _commit_skill_updates(
            cfg,
            branch=branch,
            base_branch=cfg.git_control_branch,
            runner=runner,
            cwd=git_cwd,
        )
        if not committed:
            # A `changed=True` result that produced no on-disk diff — e.g. an
            # opaque `gh skill update` that found nothing upstream. Nothing to
            # PR; the `finally` still restores the caller's branch.
            return summary
        for command in verification_commands:
            result = run_command_string(command, runner=runner, cwd=git_cwd)
            summary.verification.append(
                VerificationResult(
                    command=command,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
            )
        body = render_update_pr_body(summary)
        summary.pr_url = open_or_update_pr(
            title,
            body,
            branch=branch,
            remote=cfg.git_remote,
            runner=runner,
            cwd=git_cwd,
        )
    finally:
        # Return the checkout to where the caller left it. A Dream run launches
        # this on `main`; it must not be left sitting on the skill-update branch.
        if original_branch and original_branch != branch:
            _checkout(run, git_cwd, original_branch)
    return summary


def _assert_no_unmerged_paths(run: Runner, cwd: Path) -> None:
    """Fail loud before the PR flow if the working tree has unmerged paths.

    The flow runs `git checkout -B <branch> <base>` to carry skill updates onto
    a dedicated branch, and git refuses *any* checkout while an unmerged path
    exists ("error: you need to resolve your current index first"). Detecting it
    up front lets us name the offending files and the fix instead of surfacing a
    raw, context-free git error from deep inside the checkout.
    """
    result = run(["git", "diff", "--name-only", "--diff-filter=U"], cwd)
    if result.returncode != 0:
        raise SkillManagerError((result.stderr or result.stdout).strip())
    unmerged = [line for line in result.stdout.splitlines() if line.strip()]
    if unmerged:
        listed = "\n".join(f"  - {path}" for path in unmerged)
        raise SkillManagerError(
            "Cannot open a skill-update PR while the working tree has unmerged "
            "paths. Resolve the conflict and `git add` these files, then retry:\n"
            f"{listed}"
        )


def _current_git_branch(run: Runner, cwd: Path) -> str:
    result = run(["git", "branch", "--show-current"], cwd)
    if result.returncode != 0:
        raise SkillManagerError("Could not determine current git branch for skill update PR.")
    return result.stdout.strip()


def _checkout(
    run: Runner,
    cwd: Path,
    branch: str,
    *,
    create: bool = False,
    start_point: str | None = None,
) -> None:
    if create:
        args = ["git", "checkout", "-B", branch]
        if start_point:
            args.append(start_point)
    else:
        args = ["git", "checkout", branch]
    result = run(args, cwd)
    if result.returncode != 0:
        raise SkillManagerError((result.stderr or result.stdout).strip())


def _commit_skill_updates(
    cfg: Config,
    *,
    branch: str,
    base_branch: str,
    runner: Runner | None,
    cwd: Path,
) -> bool:
    """Carry the just-applied skill changes onto a dedicated branch and commit.

    `update_skills` has already written the updated files into the working tree
    under `skills_root(cfg)`. `git checkout -B <branch> <base>` carries those
    uncommitted changes onto a dedicated branch based on Coga's configured
    control branch — so the commit never lands on the caller's branch, and the
    PR never inherits unrelated feature commits. We stage only the skills tree
    so the PR diff is exactly the skill update and nothing the caller left
    uncommitted alongside it.

    Returns `True` when a commit was made, `False` when staging the skills tree
    produced no diff (e.g. an opaque `gh skill update` that changed nothing) so
    the caller can skip the PR instead of failing on an empty commit.
    """
    run = runner or run_subprocess
    _checkout(run, cwd, branch, create=True, start_point=base_branch)
    added = run(["git", "add", "--", str(skills_root(cfg))], cwd)
    if added.returncode != 0:
        raise SkillManagerError((added.stderr or added.stdout).strip())
    staged = run(["git", "diff", "--cached", "--quiet", "--", str(skills_root(cfg))], cwd)
    if staged.returncode == 0:
        return False
    committed = run(["git", "commit", "-m", "Update Coga-managed skills"], cwd)
    if committed.returncode != 0:
        raise SkillManagerError((committed.stderr or committed.stdout).strip())
    return True


def render_update_pr_body(summary: SkillUpdateSummary) -> str:
    lines = [
        "## Summary",
        "",
        "- Ran `coga skill update --all` for Coga-managed skills.",
    ]
    counts = summary.to_dict()["counts"]
    if counts:
        lines.append(
            "- Results: "
            + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        )
    lines.extend(["", "## Skill Results", ""])
    if not summary.results:
        lines.append("- No installed skills found.")
    for result in summary.results:
        lines.append(
            f"- `{result.name}`: {result.status} ({result.source_type}) - {result.message}"
        )
    conflicts = [result for result in summary.results if result.status == "conflict"]
    if conflicts:
        lines.extend(["", "## Conflicts", ""])
        for result in conflicts:
            details = result.details
            previous = details.get("previous_source_tree_digest") or details.get(
                "source_tree_digest"
            )
            upstream = details.get("upstream_tree_digest")
            lines.append(
                f"- `{result.name}`: manual resolution required "
                f"(recorded={previous}, upstream={upstream})"
            )
    lines.extend(["", "## Verification", ""])
    if not summary.verification:
        lines.append("- Not run.")
    for result in summary.verification:
        status = "pass" if result.returncode == 0 else f"fail ({result.returncode})"
        lines.append(f"- `{result.command}`: {status}")
    return "\n".join(lines).rstrip() + "\n"


def run_gh_skill(
    args: Sequence[str],
    *,
    runner: Runner | None = None,
    checked: bool = False,
) -> subprocess.CompletedProcess[str]:
    if not checked:
        ensure_gh_skill(runner=runner)
    command = ["gh", "skill", *args]
    result = (runner or run_subprocess)(command, None)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        translated = _translate_gh_skill_error(args, stderr)
        if translated is not None:
            raise SkillManagerError(translated)
        raise SkillManagerError(
            f"`{shlex.join(command)}` failed with exit {result.returncode}:\n"
            f"{stderr}"
        )
    return result


def _translate_gh_skill_error(args: Sequence[str], stderr: str) -> str | None:
    if "must specify a skill name when not running interactively" not in stderr:
        return None
    if len(args) < 2 or args[0] != "install":
        return None
    source = args[1]
    lines = [
        f"`gh skill install {source}` could not pick a skill: the source "
        "exposes more than one, and `gh` only auto-picks in interactive mode.",
        f"Rerun with a skill name: `coga skill install {source} <skill>`.",
    ]
    if "--from-local" in args:
        lines.append(f"List candidates with `ls {source}`.")
    else:
        repo = _github_owner_repo(source)
        if repo is not None:
            lines.append(
                f"List candidates with `gh api repos/{repo}/contents/skills`."
            )
    return "\n".join(lines)


def _github_owner_repo(source: str) -> str | None:
    return github_owner_repo(source)


def ensure_gh_skill(*, runner: Runner | None = None) -> None:
    command = ["gh", "skill", "--help"]
    try:
        result = (runner or run_subprocess)(command, None)
    except FileNotFoundError as exc:
        raise GhSkillUnavailableError(GH_SKILL_REQUIRED) from exc
    if result.returncode != 0:
        # Old gh follows `unknown command "skill"` with its full usage screen;
        # keep only the first line so callers can report the failure compactly.
        output = (result.stderr or result.stdout).strip()
        detail = output.splitlines()[0].strip() if output else ""
        message = f"{GH_SKILL_REQUIRED}\n{detail}" if detail else GH_SKILL_REQUIRED
        raise GhSkillUnavailableError(message)


def run_command_string(
    command: str,
    *,
    runner: Runner | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return (runner or run_subprocess)(shlex.split(command), cwd)


def open_or_update_pr(
    title: str,
    body: str,
    *,
    branch: str | None = None,
    remote: str = "origin",
    runner: Runner | None = None,
    cwd: Path | None = None,
) -> str:
    if branch is None:
        branch_result = (runner or run_subprocess)(["git", "branch", "--show-current"], cwd)
        if branch_result.returncode != 0 or not branch_result.stdout.strip():
            raise SkillManagerError(
                "Could not determine current git branch for skill update PR."
            )
        branch = branch_result.stdout.strip()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as fh:
        fh.write(body)
        body_file = fh.name
    try:
        pushed = (runner or run_subprocess)(
            ["git", "push", "--force-with-lease", "-u", remote, branch],
            cwd,
        )
        if pushed.returncode != 0:
            raise SkillManagerError((pushed.stderr or pushed.stdout).strip())
        existing = (runner or run_subprocess)(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "open",
                "--json",
                "url",
                "--jq",
                ".[0].url // \"\"",
            ],
            cwd,
        )
        if existing.returncode != 0:
            raise SkillManagerError((existing.stderr or existing.stdout).strip())
        existing_url = existing.stdout.strip()
        if existing_url:
            edited = (runner or run_subprocess)(
                ["gh", "pr", "edit", existing_url, "--title", title, "--body-file", body_file],
                cwd,
            )
            if edited.returncode != 0:
                raise SkillManagerError((edited.stderr or edited.stdout).strip())
            return existing_url
        created = (runner or run_subprocess)(
            ["gh", "pr", "create", "--draft", "--title", title, "--body-file", body_file],
            cwd,
        )
        if created.returncode != 0:
            raise SkillManagerError((created.stderr or created.stdout).strip())
        return created.stdout.strip()
    finally:
        Path(body_file).unlink(missing_ok=True)


def run_subprocess(
    args: Sequence[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def materialize_url_skill(
    url: str,
    data: bytes,
    root: Path,
    selector: str | None = None,
) -> MaterializedSkill:
    source_digest = _sha256_bytes(data)
    payload = root / "payload"
    payload.write_bytes(data)
    extracted = root / "extracted"
    extracted.mkdir()

    if zipfile.is_zipfile(payload):
        with zipfile.ZipFile(payload) as archive:
            _validate_zip_members(archive, extracted)
            archive.extractall(extracted)
    elif tarfile.is_tarfile(payload):
        with tarfile.open(payload) as archive:
            _validate_tar_members(archive, extracted)
            archive.extractall(extracted)
    else:
        name = _plain_skill_dir_name(url)
        plain_dir = extracted / name
        plain_dir.mkdir()
        (plain_dir / "SKILL.md").write_bytes(data)

    skill_dir = _select_skill_dir(extracted, selector)
    return MaterializedSkill(
        path=skill_dir,
        source_digest=source_digest,
        source_tree_digest=hash_skill_tree(skill_dir),
    )


def download_url(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def list_installed_skill_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    out: list[Path] = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        skill_dir = skill_md.parent
        if any(
            skill_dir != existing and skill_dir.is_relative_to(existing)
            for existing in out
        ):
            continue
        out.append(skill_dir)
    return out


def read_source_metadata(skill_dir: Path) -> dict[str, Any] | None:
    path = skill_dir / SOURCE_METADATA
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SkillManagerError(f"Invalid skill source metadata: {path}: {exc}") from exc
    if data.get("schema") != SOURCE_SCHEMA:
        raise SkillManagerError(f"Unsupported skill source metadata schema in {path}")
    return data


def write_source_metadata(skill_dir: Path, metadata: dict[str, Any]) -> None:
    path = skill_dir / SOURCE_METADATA
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def hash_skill_tree(skill_dir: Path) -> str:
    hasher = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(skill_dir).as_posix()
        if rel == SOURCE_METADATA:
            continue
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _update_gh_backed_skills(
    cfg: Config,
    *,
    runner: Runner | None = None,
) -> SkillResult:
    args = ["update", "--dir", str(skills_root(cfg)), "--all"]
    run_gh_skill(args, runner=runner)
    return SkillResult(
        name="gh-managed",
        source_type="github",
        status="delegated",
        message="delegated GitHub-backed skill updates to gh skill",
        changed=True,
        details={"command": ["gh", "skill", *args]},
    )


def _bundled_skill_refs(cfg: Config) -> set[str]:
    return {
        _skill_ref_from_path(bundled_skills_root(cfg), skill_dir)
        for skill_dir in list_installed_skill_dirs(bundled_skills_root(cfg))
    }


def _local_skill_refs(cfg: Config) -> set[str]:
    return {
        _skill_ref_from_path(skills_root(cfg), skill_dir)
        for skill_dir in list_installed_skill_dirs(skills_root(cfg))
    }


def _bundled_status_result(ref: str) -> SkillResult:
    return SkillResult(
        name=ref,
        source_type="bundled",
        status="package-backed",
        message=(
            "bundled with coga; update by upgrading the coga package"
        ),
    )


def _bundled_update_result(ref: str) -> SkillResult:
    return SkillResult(
        name=ref,
        source_type="bundled",
        status="skipped-bundled",
        message=(
            "bundled skill updates come from the coga package; run "
            "`pip install --upgrade coga`"
        ),
    )


def _local_override_result(result: SkillResult) -> SkillResult:
    details = dict(result.details)
    details["local_status"] = result.status
    details["local_source_type"] = result.source_type
    return SkillResult(
        name=result.name,
        source_type=result.source_type,
        status="local-override",
        message=f"{result.message}; shadows bundled package-backed skill",
        changed=result.changed,
        details=details,
    )


def _update_url_skill_dir(
    cfg: Config,
    skill_dir: Path,
    metadata: dict[str, Any],
    *,
    downloader: Downloader | None = None,
    now: Callable[[], str] | None = None,
) -> SkillResult:
    ref = _skill_ref_from_path(skills_root(cfg), skill_dir)
    current_digest = hash_skill_tree(skill_dir)
    installed_digest = metadata.get("installed_tree_digest")
    locally_adapted = bool(installed_digest and current_digest != installed_digest)

    url = metadata.get("source_url")
    if not isinstance(url, str) or not url:
        return SkillResult(
            name=ref,
            source_type="url",
            status="failed",
            message="source_url missing from Coga skill metadata",
        )
    selector = metadata.get("selector")
    if selector is not None and not isinstance(selector, str):
        return SkillResult(
            name=ref,
            source_type="url",
            status="failed",
            message="selector in Coga skill metadata is not a string",
        )

    try:
        data = (downloader or download_url)(url)
        with tempfile.TemporaryDirectory(prefix="coga-skill-update-") as tmp:
            materialized = materialize_url_skill(url, data, Path(tmp), selector)
            previous_source_tree = metadata.get("source_tree_digest")
            if materialized.source_tree_digest == previous_source_tree:
                if locally_adapted:
                    return SkillResult(
                        name=ref,
                        source_type="url",
                        status="skipped-local-adaptation",
                        message=(
                            "local files differ from recorded installed digest; "
                            "upstream digest unchanged; not overwriting"
                        ),
                        details={
                            "expected_digest": installed_digest,
                            "current_digest": current_digest,
                            "source_tree_digest": previous_source_tree,
                        },
                    )
                return SkillResult(
                    name=ref,
                    source_type="url",
                    status="unchanged",
                    message="upstream digest unchanged",
                    details={"source_tree_digest": previous_source_tree},
                )
            if locally_adapted:
                return SkillResult(
                    name=ref,
                    source_type="url",
                    status="conflict",
                    message=(
                        "local files differ from recorded installed digest and "
                        "upstream changed; manual resolution required"
                    ),
                    details={
                        "installed_ref": metadata.get("installed_ref"),
                        "source_url": url,
                        "expected_digest": installed_digest,
                        "current_digest": current_digest,
                        "previous_source_tree_digest": previous_source_tree,
                        "upstream_source_digest": materialized.source_digest,
                        "upstream_tree_digest": materialized.source_tree_digest,
                    },
                )
            _replace_skill_tree(materialized.path, skill_dir)
            installed_tree_digest = hash_skill_tree(skill_dir)
            refreshed = _url_metadata(
                url=url,
                selector=selector,
                installed_ref=ref,
                source_digest=materialized.source_digest,
                source_tree_digest=materialized.source_tree_digest,
                installed_tree_digest=installed_tree_digest,
                timestamp=(now or utc_now)(),
                local_adaptation_notes=_local_adaptation_notes(metadata),
            )
            write_source_metadata(skill_dir, refreshed)
            return SkillResult(
                name=ref,
                source_type="url",
                status="updated",
                message="updated from URL source",
                changed=True,
                details={
                    "previous_source_tree_digest": previous_source_tree,
                    "source_tree_digest": materialized.source_tree_digest,
                },
            )
    except Exception as exc:
        if isinstance(exc, SkillManagerError):
            message = str(exc)
        else:
            message = f"{type(exc).__name__}: {exc}"
        return SkillResult(
            name=ref,
            source_type="url",
            status="failed",
            message=message,
        )


def _status_url_skill(
    ref: str,
    skill_dir: Path,
    metadata: dict[str, Any],
    *,
    check: bool,
    downloader: Downloader | None,
) -> SkillResult:
    current_digest = hash_skill_tree(skill_dir)
    installed_digest = metadata.get("installed_tree_digest")
    locally_adapted = bool(installed_digest and current_digest != installed_digest)
    if locally_adapted and not check:
        return SkillResult(
            name=ref,
            source_type="url",
            status="locally-adapted",
            message="installed files differ from recorded digest",
            details={
                "expected_digest": installed_digest,
                "current_digest": current_digest,
            },
        )
    if not check:
        return SkillResult(
            name=ref,
            source_type="url",
            status="not-checked",
            message="URL source recorded; run with --check to fetch upstream",
            details={
                "source_url": metadata.get("source_url"),
                "source_tree_digest": metadata.get("source_tree_digest"),
            },
        )
    try:
        url = metadata.get("source_url")
        if not isinstance(url, str) or not url:
            raise SkillManagerError("source_url missing from Coga skill metadata")
        selector = metadata.get("selector")
        if selector is not None and not isinstance(selector, str):
            raise SkillManagerError("selector in Coga skill metadata is not a string")
        data = (downloader or download_url)(url)
        with tempfile.TemporaryDirectory(prefix="coga-skill-status-") as tmp:
            materialized = materialize_url_skill(url, data, Path(tmp), selector)
        upstream_changed = (
            materialized.source_tree_digest != metadata.get("source_tree_digest")
        )
        if locally_adapted:
            details = {
                "source_url": url,
                "expected_digest": installed_digest,
                "current_digest": current_digest,
                "source_tree_digest": metadata.get("source_tree_digest"),
                "upstream_tree_digest": materialized.source_tree_digest,
            }
            if upstream_changed:
                return SkillResult(
                    name=ref,
                    source_type="url",
                    status="conflict",
                    message=(
                        "installed files differ from recorded digest and "
                        "upstream changed"
                    ),
                    details=details,
                )
            return SkillResult(
                name=ref,
                source_type="url",
                status="locally-adapted",
                message="installed files differ from recorded digest; upstream unchanged",
                details=details,
            )
        return SkillResult(
            name=ref,
            source_type="url",
            status="upstream-changed" if upstream_changed else "up-to-date",
            message="checked URL source",
            details={
                "source_url": url,
                "source_tree_digest": metadata.get("source_tree_digest"),
                "upstream_tree_digest": materialized.source_tree_digest,
            },
        )
    except Exception as exc:
        return SkillResult(
            name=ref,
            source_type="url",
            status="fetch-failed",
            message=str(exc),
            details={"source_url": metadata.get("source_url")},
        )


def _replace_skill_tree(source: Path, target: Path) -> None:
    backup = target.parent / f".{target.name}.coga-update-backup"
    if backup.exists():
        shutil.rmtree(backup)
    target.rename(backup)
    try:
        shutil.copytree(source, target, symlinks=True)
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        backup.rename(target)
        raise
    else:
        shutil.rmtree(backup)


def _skill_target(cfg: Config, skill_ref: str) -> Path:
    ref = _safe_skill_ref(skill_ref)
    return skills_root(cfg).joinpath(*ref.parts)


def _safe_skill_ref(skill_ref: str) -> PurePosixPath:
    cleaned = skill_ref.strip()
    ref = PurePosixPath(cleaned)
    if not cleaned or str(ref) == "." or ref.is_absolute():
        raise SkillManagerError(f"Invalid skill name: {skill_ref!r}")
    if any(part in {"", ".", ".."} for part in ref.parts):
        raise SkillManagerError(f"Invalid skill name: {skill_ref!r}")
    return ref


def _skill_ref_for_dir(skill_dir: Path) -> str:
    try:
        skill = Skill.load(skill_dir / "SKILL.md")
        name = skill.name
    except Exception:
        name = skill_dir.name
    if not isinstance(name, str) or not name.strip():
        name = skill_dir.name
    return str(_safe_skill_ref(name))


def _skill_ref_from_path(root: Path, skill_dir: Path) -> str:
    return skill_dir.relative_to(root).as_posix()


def _url_metadata(
    *,
    url: str,
    selector: str | None,
    installed_ref: str,
    source_digest: str,
    source_tree_digest: str,
    installed_tree_digest: str,
    timestamp: str,
    local_adaptation_notes: str = "",
) -> dict[str, Any]:
    return {
        "schema": SOURCE_SCHEMA,
        "source_type": "url",
        "source_url": url,
        "selector": selector,
        "installed_ref": installed_ref,
        "installed_at": timestamp,
        "updated_at": timestamp,
        "source_digest": source_digest,
        "source_tree_digest": source_tree_digest,
        "installed_tree_digest": installed_tree_digest,
        "local_adaptation_notes": local_adaptation_notes,
    }


def _local_adaptation_notes(metadata: dict[str, Any]) -> str:
    notes = metadata.get("local_adaptation_notes", "")
    return notes if isinstance(notes, str) else ""


def _infer_non_coga_source_type(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(errors="replace")
    lowered = text.lower()
    if "github.com" in lowered or "gh skill" in lowered:
        return "github"
    return "unknown"


def _select_skill_dir(root: Path, selector: str | None) -> Path:
    if selector:
        ref = _safe_skill_ref(selector)
        selected = root.joinpath(*ref.parts).resolve()
        root_resolved = root.resolve()
        if selected != root_resolved and not selected.is_relative_to(root_resolved):
            raise SkillManagerError(f"URL skill selector escapes archive root: {selector}")
        if not (selected / "SKILL.md").is_file():
            raise SkillManagerError(f"Selected URL path has no SKILL.md: {selector}")
        return selected
    if (root / "SKILL.md").is_file():
        return root
    matches = list_installed_skill_dirs(root)
    if not matches:
        raise SkillManagerError("Downloaded URL did not contain a SKILL.md")
    if len(matches) > 1:
        rels = ", ".join(path.relative_to(root).as_posix() for path in matches)
        raise SkillManagerError(
            "Downloaded URL contains multiple skills; pass the skill path explicitly "
            f"({rels})"
        )
    return matches[0]


def _plain_skill_dir_name(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    stem = Path(path).stem or "downloaded-skill"
    if stem == "SKILL":
        parent = Path(path).parent.name
        stem = parent or "downloaded-skill"
    return stem


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_zip_members(archive: zipfile.ZipFile, root: Path) -> None:
    root_resolved = root.resolve()
    for info in archive.infolist():
        target = (root / info.filename).resolve()
        if target != root_resolved and not target.is_relative_to(root_resolved):
            raise SkillManagerError(f"Refusing unsafe zip member: {info.filename}")


def _validate_tar_members(archive: tarfile.TarFile, root: Path) -> None:
    root_resolved = root.resolve()
    for member in archive.getmembers():
        target = (root / member.name).resolve()
        if target != root_resolved and not target.is_relative_to(root_resolved):
            raise SkillManagerError(f"Refusing unsafe tar member: {member.name}")
        if member.islnk() or member.issym():
            link_target = (target.parent / member.linkname).resolve()
            if (
                link_target != root_resolved
                and not link_target.is_relative_to(root_resolved)
            ):
                raise SkillManagerError(f"Refusing unsafe tar link: {member.name}")
