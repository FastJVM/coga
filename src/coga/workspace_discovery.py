"""Discover Coga workspaces below a filesystem root."""

from __future__ import annotations

import os
from pathlib import Path


# Parent-directory scans discover real Coga workspaces, not dependency,
# tool-state, or intentionally inert `_`-prefixed trees. Once one workspace is
# found its subtree is a unit: Coga refuses nested workspaces, and descending
# would only find fixtures or packaged templates inside the repo.
_REPO_SCAN_SKIP_DIRS: frozenset[str] = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", ".mypy_cache"}
)


def discover_coga_repos(root: Path, *, strict: bool = False) -> list[Path]:
    """Return every ``coga/`` workspace at or below ``root``.

    A workspace is identified by a directory named ``coga`` containing
    ``coga.toml``. A host repo may itself be named ``coga``, so a same-named
    directory without that file is still traversed. Directory segments whose
    names start with ``_`` are explicit exclusions below the scan root.

    ``strict`` makes an unreadable directory fail the scan instead of being
    silently omitted. Destructive callers use that mode so incomplete
    discovery preserves shared state; parent schedulers retain best-effort
    discovery and report configuration/dispatch failures per workspace.
    """
    if root.name == "coga" and (root / "coga.toml").is_file():
        return [root]

    def _raise_walk_error(error: OSError) -> None:
        raise error

    found: list[Path] = []
    for dirpath, dirnames, _ in os.walk(
        root,
        onerror=_raise_walk_error if strict else None,
    ):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in _REPO_SCAN_SKIP_DIRS and not name.startswith("_")
        ]
        if "coga" not in dirnames:
            continue
        coga_os = Path(dirpath) / "coga"
        if not (coga_os / "coga.toml").is_file():
            continue
        found.append(coga_os)
        dirnames[:] = []
    return sorted(found)


__all__ = ["discover_coga_repos"]
