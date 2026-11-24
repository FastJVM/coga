"""Discover Coga workspaces below a filesystem root."""

from __future__ import annotations

import os
from pathlib import Path


# Temporary recurring checkouts are real Coga workspaces, but they are
# implementation-owned children of a parent sweep, never independent scheduler
# targets. Both the distinctive directory prefix and the private regular-file
# marker are required so a user's similarly named directory remains visible.
# Parent-directory scans discover real Coga workspaces, not dependency,
# tool-state, or intentionally inert `_`-prefixed trees. Once one workspace is
# found its subtree is a unit: Coga refuses nested workspaces, and descending
# would only find fixtures or packaged templates inside the repo.
_REPO_SCAN_SKIP_DIRS: frozenset[str] = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", ".mypy_cache"}
)


def discover_coga_repos(
    root: Path, *, strict: bool = False
) -> list[Path]:
    """Find local Coga workspaces without descending into an identified workspace."""
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
        dirnames[:] = [
            name
            for name in dirnames
            if name not in _REPO_SCAN_SKIP_DIRS
            and not name.startswith("_")
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
    "discover_coga_repos",
]
