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


def _cfg(repo_root, contexts_root=None):
    """Stub config for the context resolvers, which read `contexts_root`.

    `contexts_root` is a real `Config` property (`[layout] contexts` or the
    default beside coga.toml), so the stub has to carry it too; pass an
    explicit value to stand in for a relocated contexts directory.
    """
    return SimpleNamespace(
        repo_root=repo_root,
        contexts_root=contexts_root or repo_root / "contexts",
    )


def test_resolve_context_path_falls_back_to_configured_contexts_dir(tmp_path):
    """A relocated contexts directory resolves ahead of the packaged batteries."""
    cfg = _cfg(tmp_path, contexts_root=tmp_path / "docs" / "contexts")
    local = tmp_path / "docs" / "contexts" / "coga" / "sync" / "SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("relocated\n")
    # The default location holds a decoy: resolution must not fall back to it.
    decoy = tmp_path / "contexts" / "coga" / "sync" / "SKILL.md"
    decoy.parent.mkdir(parents=True)
    decoy.write_text("default\n")

    assert resolve_context_path(cfg, "coga/sync") == local


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
    cfg = _cfg(tmp_path)
    local = tmp_path / "contexts" / "coga" / "sync" / "SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("local\n")

    assert resolve_context_path(cfg, "coga/sync") == local


def test_resolve_context_path_falls_back_to_packaged_bootstrap(tmp_path):
    cfg = _cfg(tmp_path)

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
