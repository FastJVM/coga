"""Generate the skill view exposed to agent CLIs."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


AGENT_SKILLS_DIRNAME = ".agent-skills"


@dataclass(frozen=True)
class AgentSkillViewResult:
    view_dir: Path
    linked: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def refresh_agent_skill_view(coga_os: Path) -> AgentSkillViewResult:
    """Rebuild `coga-os/.agent-skills` from local + bundled skills.

    The generated view is what Claude Code and Codex scan. Local skills under
    `coga-os/skills` win over bundled package-backed batteries under
    `coga-os/bootstrap/skills`.
    """
    view_dir = coga_os / AGENT_SKILLS_DIRNAME
    _remove_existing(view_dir)
    view_dir.mkdir(parents=True, exist_ok=True)

    refs: dict[str, Path] = {}
    # Bootstrap first, local second: local overrides exact bundled refs.
    refs.update(_skill_refs(coga_os / "bootstrap" / "skills"))
    refs.update(_skill_refs(coga_os / "skills"))

    linked: list[str] = []
    skipped: list[str] = []
    for ref, source in sorted(refs.items()):
        link = view_dir.joinpath(*ref.split("/"))
        if _has_symlink_parent(link, view_dir):
            skipped.append(ref)
            continue
        try:
            link.parent.mkdir(parents=True, exist_ok=True)
            rel_target = Path(os.path.relpath(source, link.parent))
            link.symlink_to(rel_target, target_is_directory=True)
        except OSError:
            skipped.append(ref)
            continue
        linked.append(ref)

    return AgentSkillViewResult(view_dir=view_dir, linked=linked, skipped=skipped)


def _skill_refs(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    out: dict[str, Path] = {}
    found_dirs: list[Path] = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        skill_dir = skill_md.parent
        if any(
            skill_dir != existing and skill_dir.is_relative_to(existing)
            for existing in found_dirs
        ):
            continue
        found_dirs.append(skill_dir)
        out[skill_dir.relative_to(root).as_posix()] = skill_dir
    return out


def _has_symlink_parent(path: Path, root: Path) -> bool:
    for parent in path.parents:
        if parent == root or parent == root.parent:
            return False
        if parent.is_symlink():
            return True
    return False


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
