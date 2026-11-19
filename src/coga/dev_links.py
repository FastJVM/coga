"""The `## Dev` links a ticket records and the `gh` lookups for its PR.

A ticket's blackboard names its working state in a `## Dev` section: the
`pr:` link, every owned `branch:`, and an optional `worktree:`. The parsers
here are the one reading of those lines, shared by launch, the step gates,
`open-pr`, `bump`, checkout disposal, branch cleanup, the branch sweep, the
packaged retire ticket and the autoclose job. Fenced examples never count as
linkage.

The `gh` helpers normalize every CLI or JSON failure into `GhError`, so each
caller decides once whether a missing or unauthed `gh` is fatal. Callers use
them to prove a recorded PR merged, read its exact head, and find other PRs on
the same head before any branch is disposed of.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from coga.taskfile import TaskFileError, read_blackboard


class GhError(Exception):
    """Raised when `gh` is missing, unauthed, or returns a non-zero exit."""


_DEV_SECTION_RE = re.compile(
    r"^##\s+Dev\s*\n(.*?)(?=\n##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
# Tolerate an optional `- ` list prefix, exactly like `_BRANCH_LINE_RE` below:
# `## Dev` lines are written both bare (`pr: <url>`) and bulleted
# (`- pr: <url>`), and the bulleted shape is perfectly natural. Without the
# prefix group a bulleted `pr:` line is invisible to the sweep, so a merged
# final-step ticket is silently skipped and left stranded `in_progress`. The
# same sentence applied to a trailing annotation (`pr: <url> (no CI here)`),
# which an anchored `(\S+)$` capture rejected while the `branch:` / `worktree:`
# siblings tolerated it. Capture the rest of the line like they do and
# normalize in `parse_pr_url`. Spell the surrounding runs `[ \t]` rather than
# `\s`: `\s` matches newlines, so a non-greedy `(.+?)` on an empty `pr:` line
# would reach past it and capture the next non-blank line, which is not a
# `pr:` line at all.
_PR_LINE_RE = re.compile(r"^ {0,3}(?:-[ \t]*)?pr:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
_PR_NUMBER_RE = re.compile(r"/pull/(\d+)")
# The `branch:` line is written inconsistently across existing tickets:
# `branch: my-branch`, `- branch: \`my-branch\``, ``branch: `my-branch` ``.
# Tolerate an optional `- ` list prefix and capture the rest of the line; the
# surrounding backticks/whitespace are normalized in `parse_branch_name`. A
# leading backtick delimits the value through its matching closing backtick;
# bare values still consume the whole remainder of the line.
_BRANCH_LINE_RE = re.compile(r"^ {0,3}(?:-[ \t]*)?branch:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
_CODE_FENCE_RE = re.compile(
    r"^[ \t]*(?:(?:[-+*]|\d{1,9}[.)])[ \t]+|>[ \t]*)*(`{3,}|~{3,})(.*)$"
)
# The `worktree:` line follows the same accreted shapes as `branch:` (bare,
# list-item, backtick-wrapped), so parse it the same way. The open-pr command
# needs it to locate the feature checkout it pushes from.
_WORKTREE_LINE_RE = re.compile(r"^ {0,3}(?:-[ \t]*)?worktree:[ \t]*(.*?)[ \t]*$", re.MULTILINE)


def _delimited_value(raw: str) -> str:
    """Normalize one captured `## Dev` line value.

    A leading backtick delimits the value through its matching closing
    backtick, which is what lets a caller append a trailing annotation
    (``branch: `name` (Magicator repo)``). An unmatched backtick falls back to
    whole-line stripping, so a half-written line still yields something usable.
    Shared by the `pr:` / `branch:` / `worktree:` parsers so the three fields
    cannot drift apart on the next edit.
    """
    value = raw.strip()
    closing_tick = value.find("`", 1) if value.startswith("`") else -1
    if closing_tick >= 0:
        return value[1:closing_tick].strip()
    return value.strip("`").strip()


def _dev_section_text(blackboard_text: str) -> str:
    """Read the live Dev section without interpreting fenced examples."""
    section = _DEV_SECTION_RE.search(_unfenced_text(blackboard_text))
    if not section:
        return ""
    return section.group(1)


def dev_heading_line(blackboard_text: str) -> int | None:
    """Index of the live `## Dev` heading in `splitlines(keepends=True)`.

    Fenced examples are ignored, as by the `## Dev` parsers.
    """
    text = _unfenced_text(blackboard_text)
    section = _DEV_SECTION_RE.search(text)
    if not section:
        return None
    return len(text[:section.start()].splitlines(keepends=True))


def _unfenced_text(blackboard_text: str) -> str:
    """The text with each fenced line blanked, keeping one line per line."""
    # Examples cannot create ownership or terminate the real Dev section.
    # A shorter or differently marked fence does not close the current one.
    lines: list[str] = []
    marker = ""
    for line in blackboard_text.splitlines(keepends=True):
        fence = _CODE_FENCE_RE.match(line.rstrip("\r\n"))
        if marker:
            if (
                fence
                and fence.group(1)[0] == marker[0]
                and len(fence.group(1)) >= len(marker)
                and not fence.group(2).strip()
            ):
                marker = ""
            lines.append("\n")
        elif fence and (fence.group(1)[0] == "~" or "`" not in fence.group(2)):
            marker = fence.group(1)
            lines.append("\n")
        else:
            lines.append(line)
    return "".join(lines)


def parse_pr_url(blackboard_text: str) -> str | None:
    """Return the `pr:` URL under `## Dev`, or None if absent.

    Normalizes like `parse_branch_name` via `_delimited_value`, then keeps only
    the first whitespace-delimited token, since a URL never contains
    whitespace — so a trailing annotation (`pr: <url> (no CI configured)`)
    still yields the bare URL. Returns None for a missing, empty, or
    placeholder value.

    Scans *every* `pr:` line rather than only the first. The old anchored regex
    simply failed to match a placeholder line and kept searching; rejecting it
    in the guard instead would strand a ticket that records `pr: (not opened
    yet)` and later appends the real link below it — the same silent skip this
    parser exists to prevent.
    """
    section = _dev_section_text(blackboard_text)
    for match in _PR_LINE_RE.finditer(section):
        tokens = _delimited_value(match.group(1)).split()
        if tokens and _looks_like_pr_url(tokens[0]):
            return tokens[0]
    return None


def _looks_like_pr_url(value: str) -> bool:
    """Whether a `pr:` capture is a link rather than a placeholder.

    `parse_worktree_path` rejects placeholders the same way, but here the stakes
    are higher: the old `$`-anchored regex rejected `pr: (not opened yet)` and
    `pr: none - blocked on CI` by accident, and without a guard those captures
    reach `gh pr view`, whose `GhError` aborts the *whole* autoclose sweep with
    exit 2 instead of skipping one ticket. Require the documented full PR URL
    shape: downstream consumers also need its `/pull/<n>` component.
    """
    if not value or value.startswith("("):
        return False
    return parse_pr_number(value) is not None


def parse_branch_name(blackboard_text: str) -> str | None:
    """Return the normalized `branch:` name under `## Dev`, or None if absent.

    Normalizes the inconsistent shapes the convention has accreted: tolerates a
    leading "- " list prefix. A leading backtick delimits the value through the
    next backtick, allowing trailing annotations; an unmatched backtick falls
    back to whole-line normalization. Bare values still consume the entire line.
    Returns None for a missing or empty branch line.
    """
    return next(iter(parse_branch_names(blackboard_text)), None)


def parse_branch_names(blackboard_text: str) -> list[str]:
    """Every `branch:` name under `## Dev`, in order and without duplicates.

    A ticket explicitly owns each branch it records this way; terminal branch
    cleanup (`branchsweep`) treats the list as the ticket's ownership claim.
    `parse_branch_name` keeps returning the first, which is the checkout the
    workflow gates and `coga open-pr` act on. A prose mention elsewhere in the
    ticket is never ownership.
    """
    section = _dev_section_text(blackboard_text)
    names = (
        _delimited_value(match.group(1))
        for match in _BRANCH_LINE_RE.finditer(section)
    )
    return list(dict.fromkeys(name for name in names if name))


def parse_worktree_path(blackboard_text: str) -> str | None:
    """Return the normalized `worktree:` path under `## Dev`, or None if absent.

    Mirrors `parse_branch_name`'s normalization: a leading backtick delimits the
    value through the next backtick, while bare values and unmatched backticks
    retain whole-line handling so paths with spaces remain valid. Returns None
    for a missing or empty worktree line, or a placeholder like
    `(not yet created)`.
    """
    section = _dev_section_text(blackboard_text)
    match = _WORKTREE_LINE_RE.search(section)
    if not match:
        return None
    path = _delimited_value(match.group(1))
    if not path or path.startswith("("):
        return None
    return path


def parse_pr_number(url: str) -> int | None:
    m = _PR_NUMBER_RE.search(url)
    return int(m.group(1)) if m else None


def pr_state(url: str) -> str:
    """Query `gh` for the PR's state. Raises GhError on any failure.

    Returns the raw state string ("MERGED", "CLOSED", "OPEN").
    """
    data = pr_view(url, "state")
    return str(data.get("state", ""))


def pr_head(url: str) -> tuple[str, str]:
    """Return the PR's ``(head branch, head commit)`` from GitHub.

    Cleanup callers use the exact head commit to prove a branch has not been
    reused or advanced since the recorded PR merged. Missing fields are an
    error: treating an incomplete response as authorization would make a stale
    ``pr:`` line destructive.
    """
    data = pr_view(url, "headRefName,headRefOid")
    branch = str(data.get("headRefName", "")).strip()
    oid = str(data.get("headRefOid", "")).strip()
    if not branch or not oid:
        raise GhError(
            f"`gh pr view {url}` returned no complete headRefName/headRefOid"
        )
    return branch, oid


def prs_for_head(
    branch: str, state: str, *, repository: str | None = None
) -> list[dict[str, object]]:
    """Return GitHub PRs for one head branch and state.

    Branch retirement and the repository-wide branch sweep share this lookup:
    neither may dispose of a branch while another PR still has that head.
    """
    scope = ["--repo", repository, "--limit", "1000"] if repository else []
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                state,
                "--json",
                "number,headRefOid",
                *scope,
            ],
            capture_output=True,
            text=True, encoding="utf-8",
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhError("`gh` not found on PATH") from exc
    if result.returncode != 0:
        raise GhError(
            f"`gh pr list --head {branch} --state {state}` failed "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GhError(f"`gh pr list --head {branch}` returned non-JSON: {exc}") from exc
    if not isinstance(data, list):
        raise GhError(f"`gh pr list --head {branch}` returned unexpected JSON")
    if repository and (len(data) >= 1000 or any(not isinstance(item, dict) for item in data)):
        raise GhError(f"`gh pr list --head {branch}` returned incomplete PR evidence")
    return [item for item in data if isinstance(item, dict)]


def pr_view(url: str, fields: str) -> dict[str, object]:
    """Query selected JSON fields for one PR, normalizing CLI failures."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", url, "--json", fields],
            capture_output=True,
            text=True, encoding="utf-8",
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
    if not isinstance(data, dict):
        raise GhError(f"`gh pr view {url}` returned unexpected JSON")
    return data


def read_dev_blackboard(ticket: Path) -> str | None:
    """The blackboard region holding `## Dev`, or None when unreadable."""
    if not ticket.is_file():
        return None
    try:
        # The `## Dev` section lives in the blackboard region below the fence.
        return read_blackboard(ticket, blackboard_required=False)
    except (OSError, TaskFileError) as exc:
        # A read error on a single ticket shouldn't sink the scanner.
        sys.stderr.write(f"[autoclose] could not read {ticket}: {exc}\n")
        return None


__all__ = [
    "GhError",
    "dev_heading_line",
    "parse_branch_name",
    "parse_branch_names",
    "parse_pr_number",
    "parse_pr_url",
    "parse_worktree_path",
    "pr_head",
    "pr_state",
    "pr_view",
    "prs_for_head",
    "read_dev_blackboard",
]
