"""Discover Coga workspaces below a filesystem root."""

from __future__ import annotations

import os
from pathlib import Path


# Temporary recurring checkouts are real Coga workspaces, but they are
# implementation-owned children of a parent sweep, never independent scheduler
# targets. Both the distinctive directory prefix and the private regular-file
# marker are required so a user's similarly named directory remains visible.
CONTROL_WORKTREE_DIR_PREFIX = "coga-recurring-"
CONTROL_WORKTREE_OWNER_FILE = ".coga-recurring-owner.json"


# Parent-directory scans discover real Coga workspaces, not dependency,
# tool-state, or intentionally inert `_`-prefixed trees. Once one workspace is
# found its subtree is a unit: Coga refuses nested workspaces, and descending
# would only find fixtures or packaged templates inside the repo.
_REPO_SCAN_SKIP_DIRS: frozenset[str] = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", ".mypy_cache"}
)


def _is_control_worktree_parent(path: Path) -> bool:
    marker = path / CONTROL_WORKTREE_OWNER_FILE
    return (
        path.name.startswith(CONTROL_WORKTREE_DIR_PREFIX)
        and not marker.is_symlink()
        and marker.is_file()
    )


def _is_within_control_worktree(path: Path) -> bool:
    """Whether an explicit scan root is inside an owned temporary checkout."""
    try:
        current = path.resolve()
    except OSError:
        current = path.absolute()
    return any(
        _is_control_worktree_parent(candidate)
        for candidate in (current, *current.parents)
    )


def discover_coga_repos(root: Path, *, strict: bool = False) -> list[Path]:
    """Return every ``coga/`` workspace at or below ``root``.

    Below the scan root a workspace is identified by a directory named ``coga``
    containing ``coga.toml``. A host repo may itself be named ``coga``, so a
    same-named directory without that file is still traversed. Directory
    segments whose names start with ``_`` are explicit exclusions below the
    scan root. A Coga recurring temp parent is excluded only when its stable
    prefix and private owner marker both match, including when the explicit
    root is that parent, its checkout, or its workspace.

    The scan root itself is recognized by its ``coga.toml`` alone, whatever its
    basename. `find_repo_root()` resolves a workspace directly from a
    ``coga.toml`` at any directory, so requiring the ``coga`` basename here
    would leave such a workspace undiscoverable — `_live_checkout_claim()`
    would then report the current workspace as missing and every `coga retire`
    would skip its worktree and branch cleanup.

    ``strict`` makes an unreadable directory fail the scan instead of being
    silently omitted. Destructive callers use that mode so incomplete
    discovery preserves shared state; parent schedulers retain best-effort
    discovery and report configuration/dispatch failures per workspace.
    """
    if _is_within_control_worktree(root):
        return []
    if (root / "coga.toml").is_file():
        return [root]

    def _raise_walk_error(error: OSError) -> None:
        raise error

    found: list[Path] = []
    for dirpath, dirnames, _ in os.walk(
        root,
        onerror=_raise_walk_error if strict else None,
    ):
        current = Path(dirpath)
        # This second check closes the race where os.walk listed a just-created
        # temp parent before its owner marker was atomically published.
        if _is_control_worktree_parent(current):
            dirnames[:] = []
            continue
        dirnames[:] = [
            name
            for name in dirnames
            if name not in _REPO_SCAN_SKIP_DIRS
            and not name.startswith("_")
            and not _is_control_worktree_parent(current / name)
        ]
        if "coga" not in dirnames:
            continue
        coga_os = current / "coga"
        if not (coga_os / "coga.toml").is_file():
            continue
        found.append(coga_os)
        dirnames[:] = []
    return sorted(found)


__all__ = [
    "CONTROL_WORKTREE_DIR_PREFIX",
    "CONTROL_WORKTREE_OWNER_FILE",
    "discover_coga_repos",
]
