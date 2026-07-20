"""Shared `## Dev` PR-link parsers and `gh` PR-state helpers.

The PR link convention lives in the `dev/code` context: a `pr:` line
under `## Dev` on the blackboard. We parse it directly; coga-the-CLI
treats the blackboard as plain text on purpose.

This module is **shared core infra**: the parsers (`parse_pr_url`,
`parse_branch_name`, `parse_worktree_path`) and the `gh` helpers (`GhError`,
`pr_state`) each have multiple consumers — `open_pr`, `step_gate`,
`branchcleanup` (used by `coga retire`), the `branch-sweep` recipe, and the
Dream orphan-marker worker. The single-consumer auto-close *sweep* recipe that
used to live here (`sweep_merged` and its helpers) now lives in the
`coga/autoclose/sweep` skill dir under the microkernel policy and imports the
shared helpers below.
"""

from __future__ import annotations

import json
import re
import subprocess


class GhError(Exception):
    """Raised when `gh` is missing, unauthed, or returns a non-zero exit."""


_DEV_SECTION_RE = re.compile(
    r"^##\s+Dev\s*\n(.*?)(?=\n##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
# Tolerate an optional `- ` list prefix, exactly like `_BRANCH_LINE_RE` below:
# `## Dev` lines are written both bare (`pr: <url>`) and bulleted
# (`- pr: <url>`), and the bulleted shape is perfectly natural. Without the
# prefix group a bulleted `pr:` line is invisible to `parse_pr_url`, so a merged
# final-step ticket is silently skipped by the autoclose sweep and left stranded
# `in_progress`.
_PR_LINE_RE = re.compile(r"^\s*(?:-\s*)?pr:\s*(\S+)\s*$", re.MULTILINE)
# The `branch:` line is written inconsistently across existing tickets:
# `branch: my-branch`, `- branch: \`my-branch\``, ``branch: `my-branch` ``.
# Tolerate an optional `- ` list prefix and capture the rest of the line; the
# surrounding backticks/whitespace are normalized in `parse_branch_name`. A
# leading backtick delimits the value through its matching closing backtick;
# bare values still consume the whole remainder of the line.
_BRANCH_LINE_RE = re.compile(r"^\s*(?:-\s*)?branch:\s*(.+?)\s*$", re.MULTILINE)
# The `worktree:` line follows the same accreted shapes as `branch:` (bare,
# list-item, backtick-wrapped), so parse it the same way. The open-pr command
# needs it to locate the feature checkout it pushes from.
_WORKTREE_LINE_RE = re.compile(r"^\s*(?:-\s*)?worktree:\s*(.+?)\s*$", re.MULTILINE)


def parse_pr_url(blackboard_text: str) -> str | None:
    """Return the `pr:` URL under `## Dev`, or None if absent."""
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    pr = _PR_LINE_RE.search(section.group(1))
    return pr.group(1) if pr else None


def parse_branch_name(blackboard_text: str) -> str | None:
    """Return the normalized `branch:` name under `## Dev`, or None if absent.

    Normalizes the inconsistent shapes the convention has accreted: tolerates a
    leading "- " list prefix. A leading backtick delimits the value through the
    next backtick, allowing trailing annotations; an unmatched backtick falls
    back to whole-line normalization. Bare values still consume the entire line.
    Returns None for a missing or empty branch line.
    """
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    match = _BRANCH_LINE_RE.search(section.group(1))
    if not match:
        return None
    name = match.group(1).strip()
    closing_tick = name.find("`", 1) if name.startswith("`") else -1
    if closing_tick >= 0:
        name = name[1:closing_tick].strip()
    else:
        name = name.strip("`").strip()
    return name or None


def parse_worktree_path(blackboard_text: str) -> str | None:
    """Return the normalized `worktree:` path under `## Dev`, or None if absent.

    Mirrors `parse_branch_name`'s normalization: a leading backtick delimits the
    value through the next backtick, while bare values and unmatched backticks
    retain whole-line handling so paths with spaces remain valid. Returns None
    for a missing or empty worktree line, or a placeholder like
    `(not yet created)`.
    """
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    match = _WORKTREE_LINE_RE.search(section.group(1))
    if not match:
        return None
    path = match.group(1).strip()
    closing_tick = path.find("`", 1) if path.startswith("`") else -1
    if closing_tick >= 0:
        path = path[1:closing_tick].strip()
    else:
        path = path.strip("`").strip()
    if not path or path.startswith("("):
        return None
    return path


def pr_state(url: str) -> str:
    """Query `gh` for the PR's state. Raises GhError on any failure.

    Returns the raw state string ("MERGED", "CLOSED", "OPEN").
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "view", url, "--json", "state"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhError("`gh` not found on PATH") from exc
    if result.returncode != 0:
        raise GhError(
            f"`gh pr view {url}` failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GhError(f"`gh pr view {url}` returned non-JSON: {exc}") from exc
    return str(data.get("state", ""))


__all__ = [
    "GhError",
    "parse_pr_url",
    "parse_branch_name",
    "parse_worktree_path",
    "pr_state",
]
