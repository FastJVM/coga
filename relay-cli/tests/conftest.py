"""Shared pytest fixtures.

Kept intentionally minimal for the scaffolding ticket. Subsequent
tickets (config, frontmatter, composer) will add fixtures for parsed
configs, sample tickets, temp repos, etc.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """An empty Relay-like repo rooted at a fresh tmp_path.

    Writes a minimal relay.toml so helpers that walk up looking for it
    succeed. Does not create any projects, skills, or contexts — those
    are added on a per-test basis as the test surface grows.
    """
    (tmp_path / "relay.toml").write_text("version = 1\n")
    return tmp_path
