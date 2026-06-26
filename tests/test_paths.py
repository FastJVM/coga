from __future__ import annotations

from types import SimpleNamespace

from coga.paths import (
    bootstrap_context_path,
    bootstrap_skill_path,
    bootstrap_workflow_path,
    resolve_context_path,
    resolve_skill_path,
    resolve_workflow_path,
    workflow_path,
)


def test_resolve_skill_path_falls_back_to_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)

    assert resolve_skill_path(cfg, "bootstrap/ticket") == bootstrap_skill_path(
        cfg, "bootstrap/ticket"
    )


def test_resolve_skill_path_prefers_local_over_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    local = tmp_path / "skills" / "tools" / "example" / "SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("local\n")

    assert resolve_skill_path(cfg, "tools/example") == local


def test_resolve_context_path_prefers_local_over_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    local = tmp_path / "contexts" / "coga" / "sync" / "SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("local\n")

    assert resolve_context_path(cfg, "coga/sync") == local


def test_resolve_context_path_falls_back_to_packaged_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)

    assert resolve_context_path(cfg, "coga/sync") == bootstrap_context_path(
        cfg, "coga/sync"
    )


def test_resolve_workflow_path_falls_back_to_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)

    assert resolve_workflow_path(cfg, "code/with-review") == bootstrap_workflow_path(
        cfg, "code/with-review"
    )


def test_resolve_workflow_path_prefers_local_over_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    local = tmp_path / "workflows" / "code" / "with-review.md"
    local.parent.mkdir(parents=True)
    local.write_text("local\n")

    assert resolve_workflow_path(cfg, "code/with-review") == local


def test_resolve_workflow_path_falls_back_to_local_when_neither_exists(tmp_path):
    # When neither a local nor a bundled workflow exists, resolution returns the
    # conventional local path so a caller's Workflow.load(...) raises a
    # not-found error naming coga/workflows/ rather than bootstrap/.
    cfg = SimpleNamespace(repo_root=tmp_path)

    assert resolve_workflow_path(cfg, "code/nope") == workflow_path(cfg, "code/nope")
