from __future__ import annotations

from types import SimpleNamespace

from relay.paths import resolve_context_path, resolve_skill_path


def test_resolve_skill_path_falls_back_to_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    bundled = tmp_path / "bootstrap" / "skills" / "tools" / "example" / "SKILL.md"
    bundled.parent.mkdir(parents=True)
    bundled.write_text("bundled\n")

    assert resolve_skill_path(cfg, "tools/example") == bundled


def test_resolve_skill_path_prefers_local_over_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    bundled = tmp_path / "bootstrap" / "skills" / "tools" / "example" / "SKILL.md"
    local = tmp_path / "skills" / "tools" / "example" / "SKILL.md"
    bundled.parent.mkdir(parents=True)
    local.parent.mkdir(parents=True)
    bundled.write_text("bundled\n")
    local.write_text("local\n")

    assert resolve_skill_path(cfg, "tools/example") == local


def test_resolve_context_path_prefers_local_over_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    bundled = tmp_path / "bootstrap" / "contexts" / "relay" / "sync" / "SKILL.md"
    local = tmp_path / "contexts" / "relay" / "sync" / "SKILL.md"
    bundled.parent.mkdir(parents=True)
    local.parent.mkdir(parents=True)
    bundled.write_text("bundled\n")
    local.write_text("local\n")

    assert resolve_context_path(cfg, "relay/sync") == local
