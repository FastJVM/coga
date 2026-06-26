from __future__ import annotations

from types import SimpleNamespace

from coga.paths import (
    resolve_context_path,
    resolve_skill_path,
    resolve_workflow_path,
    workflow_path,
)


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
    bundled = tmp_path / "bootstrap" / "contexts" / "coga" / "sync" / "SKILL.md"
    local = tmp_path / "contexts" / "coga" / "sync" / "SKILL.md"
    bundled.parent.mkdir(parents=True)
    local.parent.mkdir(parents=True)
    bundled.write_text("bundled\n")
    local.write_text("local\n")

    assert resolve_context_path(cfg, "coga/sync") == local


def test_resolve_workflow_path_falls_back_to_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    bundled = tmp_path / "bootstrap" / "workflows" / "code" / "with-review.md"
    bundled.parent.mkdir(parents=True)
    bundled.write_text("bundled\n")

    assert resolve_workflow_path(cfg, "code/with-review") == bundled


def test_resolve_workflow_path_prefers_local_over_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    bundled = tmp_path / "bootstrap" / "workflows" / "code" / "with-review.md"
    local = tmp_path / "workflows" / "code" / "with-review.md"
    bundled.parent.mkdir(parents=True)
    local.parent.mkdir(parents=True)
    bundled.write_text("bundled\n")
    local.write_text("local\n")

    assert resolve_workflow_path(cfg, "code/with-review") == local


def test_resolve_workflow_path_falls_back_to_local_when_neither_exists(tmp_path):
    # When neither a local nor a bundled workflow exists, resolution returns the
    # conventional local path so a caller's Workflow.load(...) raises a
    # not-found error naming coga/workflows/ rather than bootstrap/.
    cfg = SimpleNamespace(repo_root=tmp_path)

    assert resolve_workflow_path(cfg, "code/nope") == workflow_path(cfg, "code/nope")
