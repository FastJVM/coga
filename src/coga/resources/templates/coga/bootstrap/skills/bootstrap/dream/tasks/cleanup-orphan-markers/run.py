#!/usr/bin/env python3
"""Run the cleanup-orphan-markers Dream skill."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


# `## Retro` must be matched only as a line-start markdown heading. A ticket
# that documents the marker format mentions `## Retro` inline in prose; that is
# not a marker and must not be detected as one.
RETRO_HEADING_RE = re.compile(r"^## Retro[ \t]*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^## ", re.MULTILINE)
RETRO_SKILL = "skill: retro/done-ticket"
RETRO_STATUS = "status: processed"
RETRO_NO_NEW = "result: no-new-durable-knowledge"
DELETE_SKILL = "bootstrap/delete-task"


@dataclass(frozen=True)
class Candidate:
    slug: str
    path: Path


@dataclass(frozen=True)
class OpenPrState:
    paths: set[str] | None
    reason: str | None = None


def coga_os_root() -> Path:
    env_root = os.environ.get("COGA_COGA_OS_ROOT")
    if env_root:
        return Path(env_root)

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        coga_os = candidate / "coga"
        if (coga_os / "coga.toml").is_file():
            return coga_os
        if candidate.name == "coga" and (candidate / "coga.toml").is_file():
            return candidate
    raise RuntimeError("could not find coga root")


def repo_root(coga_os: Path) -> Path:
    env_root = os.environ.get("COGA_REPO_ROOT")
    if env_root:
        return Path(env_root)
    return coga_os.parent if coga_os.name == "coga" else coga_os


def script_blackboard() -> Path | None:
    value = os.environ.get("COGA_TASK_BLACKBOARD")
    return Path(value) if value else None


def script_task_slug() -> str | None:
    return os.environ.get("COGA_TASK_SLUG")


def load_status(ticket_path: Path) -> str | None:
    text = ticket_path.read_text()
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(frontmatter, dict):
        return None
    status = frontmatter.get("status")
    return str(status) if status is not None else None


def retro_block(text: str) -> str:
    """Return the body of the `## Retro` heading section, or "" if absent.

    Only a line-start `## Retro` heading counts. A bare mention of the string
    `## Retro` inside prose is not a marker.
    """
    heading = RETRO_HEADING_RE.search(text)
    if heading is None:
        return ""
    rest = text[heading.end() :]
    next_heading = NEXT_HEADING_RE.search(rest)
    if next_heading is None:
        return rest
    return rest[: next_heading.start()]


_BLACKBOARD_FENCE = "<!-- coga:blackboard -->"


def blackboard_region(ticket: Path) -> str:
    """The blackboard region of a single-file `ticket.md` (text after the
    `<!-- coga:blackboard -->` fence), or "" when absent.

    The `## Retro` marker lives in this region under the v2 single-file format
    (it was a separate `blackboard.md` before)."""
    if not ticket.is_file():
        return ""
    text = ticket.read_text()
    idx = text.find(_BLACKBOARD_FENCE)
    return text[idx + len(_BLACKBOARD_FENCE):] if idx != -1 else ""


def has_cleanup_eligible_retro_marker(ticket: Path) -> bool:
    block = retro_block(blackboard_region(ticket))
    return RETRO_SKILL in block and RETRO_STATUS in block and RETRO_NO_NEW not in block


def find_candidates(coga_os: Path) -> list[Candidate]:
    tasks = coga_os / "tasks"
    if not tasks.is_dir():
        return []
    candidates: list[Candidate] = []
    for task_dir in sorted(tasks.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith("_"):
            continue
        ticket = task_dir / "ticket.md"
        if not ticket.is_file():
            continue
        if load_status(ticket) != "done":
            continue
        if not has_cleanup_eligible_retro_marker(ticket):
            continue
        candidates.append(Candidate(slug=task_dir.name, path=task_dir))
    return candidates


def delete_skill_path(coga_os: Path) -> Path:
    """Resolve the delete-task skill: project-local override before bundled.

    A repo may override the skill under `coga/skills/`; otherwise it is
    materialized into `coga/bootstrap/skills/` by `coga init`. Mirrors
    Coga's standard local-then-bootstrap resolution. When neither exists the
    bundled path is returned so the caller's `is_file()` gate reports missing.
    """
    local = coga_os / "skills" / "bootstrap" / "delete-task" / "SKILL.md"
    if local.is_file():
        return local
    return coga_os / "bootstrap" / "skills" / "bootstrap" / "delete-task" / "SKILL.md"


def open_pr_state(repo: Path) -> OpenPrState:
    gh = shutil.which("gh")
    if gh is None:
        return OpenPrState(paths=None, reason="`gh` is not available")

    listed = subprocess.run(
        [gh, "pr", "list", "--state", "open", "--json", "number"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if listed.returncode != 0:
        detail = listed.stderr.strip() or listed.stdout.strip() or "no output"
        return OpenPrState(paths=None, reason=f"`gh pr list` failed: {detail}")

    try:
        prs = json.loads(listed.stdout)
    except json.JSONDecodeError as exc:
        return OpenPrState(paths=None, reason=f"`gh pr list` emitted invalid JSON: {exc}")
    if not isinstance(prs, list):
        return OpenPrState(paths=None, reason="`gh pr list` JSON was not a list")

    paths: set[str] = set()
    for item in prs:
        if not isinstance(item, dict) or "number" not in item:
            continue
        number = str(item["number"])
        diff = subprocess.run(
            [gh, "pr", "diff", number, "--name-only"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        if diff.returncode != 0:
            detail = diff.stderr.strip() or diff.stdout.strip() or "no output"
            return OpenPrState(paths=None, reason=f"`gh pr diff {number}` failed: {detail}")
        for line in diff.stdout.splitlines():
            path = line.strip()
            if path:
                paths.add(path)
    return OpenPrState(paths=paths)


def pr_touches_task(paths: set[str], slug: str) -> bool:
    prefix = f"coga/tasks/{slug}/"
    exact = f"coga/tasks/{slug}"
    return any(path == exact or path.startswith(prefix) for path in paths)


def render_report(
    *,
    generated_at: str,
    task_slug: str | None,
    candidates: list[Candidate],
    delete_skill: Path,
    pr_state: OpenPrState | None,
) -> str:
    lines = [
        "## Dream Skill: cleanup-orphan-markers",
        "",
        f"Generated: {generated_at}",
    ]
    if task_slug:
        lines.append(f"Task: `{task_slug}`")
    lines.append("")

    if not candidates:
        lines.append(
            "Result: no-op. No cleanup-eligible processed done tickets still have "
            "task directories."
        )
        return "\n".join(lines) + "\n"

    lines.append(f"Candidates: {len(candidates)} processed done task(s).")
    lines.append("")

    if not delete_skill.is_file():
        lines.append("Result: human-needed.")
        lines.append(
            f"Required delete skill is missing: `{delete_skill}`. "
            f"Install `{DELETE_SKILL}` before cleanup can delete through the public surface."
        )
        lines.append("")
        for candidate in candidates:
            lines.append(f"- `{candidate.slug}`: processed marker present; deletion skipped.")
        return "\n".join(lines) + "\n"

    if pr_state is None or pr_state.paths is None:
        reason = pr_state.reason if pr_state else "open PR state was not checked"
        lines.append("Result: human-needed.")
        lines.append(
            "Deletion is gated on proving no open PR already touches the exact task "
            f"directory. Open PR check failed: {reason}."
        )
        lines.append("")
        for candidate in candidates:
            lines.append(f"- `{candidate.slug}`: processed marker present; deletion skipped.")
        return "\n".join(lines) + "\n"

    eligible = [
        candidate for candidate in candidates if not pr_touches_task(pr_state.paths, candidate.slug)
    ]
    in_flight = [
        candidate for candidate in candidates if pr_touches_task(pr_state.paths, candidate.slug)
    ]

    if not eligible:
        lines.append("Result: no-op. Every candidate already has an open PR touching it.")
        lines.append("")
        for candidate in in_flight:
            lines.append(f"- `{candidate.slug}`: skipped because an open PR touches it.")
        return "\n".join(lines) + "\n"

    lines.append("Result: human-needed.")
    lines.append(
        f"`{DELETE_SKILL}` is present, but cleanup PR dispatch should follow the "
        "sibling delete-task skill's final launch contract. Do not delete through "
        "private filesystem helpers."
    )
    lines.append("")
    for candidate in eligible:
        lines.append(
            f"- `{candidate.slug}`: eligible after marker and open-PR gates; dispatch via "
            f"`{DELETE_SKILL}` in a reviewable cleanup PR worktree."
        )
    for candidate in in_flight:
        lines.append(f"- `{candidate.slug}`: skipped because an open PR touches it.")
    return "\n".join(lines) + "\n"


def append_report(blackboard: Path, report: str) -> None:
    if not blackboard.parent.is_dir():
        raise RuntimeError(f"Blackboard parent does not exist: {blackboard.parent}")
    existing = blackboard.read_text() if blackboard.is_file() else ""
    if not existing or existing.endswith("\n\n"):
        separator = ""
    elif existing.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    blackboard.write_text(existing + separator + report)


def main() -> int:
    try:
        coga_os = coga_os_root()
        candidates = find_candidates(coga_os)
        delete_skill = delete_skill_path(coga_os)
        pr_state = None
        if candidates and delete_skill.is_file():
            pr_state = open_pr_state(repo_root(coga_os))
        report = render_report(
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            task_slug=script_task_slug(),
            candidates=candidates,
            delete_skill=delete_skill,
            pr_state=pr_state,
        )
        blackboard = script_blackboard()
        if blackboard:
            append_report(blackboard, report)
        else:
            sys.stdout.write(report)
    except RuntimeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
