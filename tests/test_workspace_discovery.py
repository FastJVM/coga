from __future__ import annotations

from pathlib import Path

import pytest

from coga.workspace_discovery import discover_coga_repos


def _workspace(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "coga.toml").write_text("version = 1\n", encoding="utf-8")
    return path


def test_scan_root_named_coga_is_the_workspace(tmp_path: Path) -> None:
    root = _workspace(tmp_path / "coga")
    assert discover_coga_repos(root) == [root]


def test_scan_root_is_recognized_whatever_its_basename(tmp_path: Path) -> None:
    # `find_repo_root()` resolves a workspace from a `coga.toml` at any
    # directory, so discovery must agree: requiring the `coga` basename made
    # `_live_checkout_claim()` report the current workspace as missing, which
    # skipped every `coga retire`'s worktree and branch cleanup.
    root = _workspace(tmp_path / "not-named-coga")
    assert discover_coga_repos(root) == [root]


def test_nested_workspaces_are_found_below_the_scan_root(tmp_path: Path) -> None:
    first = _workspace(tmp_path / "one" / "coga")
    second = _workspace(tmp_path / "two" / "coga")
    assert discover_coga_repos(tmp_path) == sorted([first, second])


def test_same_named_directory_without_config_is_still_traversed(
    tmp_path: Path,
) -> None:
    # A host repo may itself be named `coga`; only the `coga.toml` makes it one.
    (tmp_path / "coga").mkdir()
    nested = _workspace(tmp_path / "coga" / "coga")
    assert discover_coga_repos(tmp_path) == [nested]


def test_underscore_and_tool_state_trees_are_skipped(tmp_path: Path) -> None:
    _workspace(tmp_path / "_archive" / "coga")
    _workspace(tmp_path / ".venv" / "coga")
    live = _workspace(tmp_path / "live" / "coga")
    assert discover_coga_repos(tmp_path) == [live]


def test_strict_mode_raises_on_an_unreadable_directory(tmp_path: Path) -> None:
    _workspace(tmp_path / "live" / "coga")
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o000)
    try:
        with pytest.raises(OSError):
            discover_coga_repos(tmp_path, strict=True)
    finally:
        blocked.chmod(0o755)
