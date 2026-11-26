from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from coga.paths import (
    LocalOverrideError,
    bootstrap_context_path,
    bootstrap_skill_path,
    bootstrap_workflow_path,
    load_workflow,
    resolve_context_path,
    resolve_skill_path,
    resolve_workflow_path,
    workflow_not_found_message,
    workflow_path,
)
from coga.workflow import WorkflowError, WorkflowNotFoundError, git_mode


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


@pytest.mark.parametrize("shape", ["nested-attachment", "dangling-owner", "unreadable-owner"])
def test_incomplete_skill_directory_never_selects_stock(tmp_path, monkeypatch, shape):
    owner = tmp_path / "skills/code/implement"
    owner.parent.mkdir(parents=True)
    if shape == "dangling-owner":
        owner.symlink_to(tmp_path / "missing", target_is_directory=True)
    else:
        owner.mkdir()
        if shape == "nested-attachment":
            (owner / "scripts").mkdir()
            (owner / "scripts/helper.py").write_text("# attachment\n", encoding="utf-8")
        else:
            original = Path.iterdir
            def denied(path):
                if path == owner:
                    raise PermissionError("unreadable override")
                return original(path)
            monkeypatch.setattr(Path, "iterdir", denied)
    with pytest.raises(LocalOverrideError, match="local skill override"):
        resolve_skill_path(_cfg(tmp_path), "code/implement")


def test_resolve_context_path_falls_back_to_configured_contexts_dir(tmp_path):
    """A relocated contexts directory resolves ahead of the packaged batteries."""
    cfg = _cfg(tmp_path, contexts_root=tmp_path / "docs" / "contexts")
    local = tmp_path / "docs" / "contexts" / "coga" / "git" / "SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("relocated\n", encoding="utf-8", newline="\n")
    # The default location holds a decoy: resolution must not fall back to it.
    decoy = tmp_path / "contexts" / "coga" / "git" / "SKILL.md"
    decoy.parent.mkdir(parents=True)
    decoy.write_text("default\n", encoding="utf-8", newline="\n")

    assert resolve_context_path(cfg, "coga/git") == local


def test_resolve_skill_path_falls_back_to_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)

    assert resolve_skill_path(cfg, "bootstrap/ticket") == bootstrap_skill_path(
        cfg, "bootstrap/ticket"
    )


def test_resolve_skill_path_prefers_local_over_bootstrap(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    local = tmp_path / "skills" / "tools" / "example" / "SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("local\n", encoding="utf-8", newline="\n")

    assert resolve_skill_path(cfg, "tools/example") == local


def test_resolve_context_path_prefers_local_over_bootstrap(tmp_path):
    cfg = _cfg(tmp_path)
    local = tmp_path / "contexts" / "coga" / "git" / "SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("local\n", encoding="utf-8", newline="\n")

    assert resolve_context_path(cfg, "coga/git") == local


def test_resolve_context_path_falls_back_to_packaged_bootstrap(tmp_path):
    cfg = _cfg(tmp_path)

    assert resolve_context_path(cfg, "coga/git") == bootstrap_context_path(
        cfg, "coga/git"
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
    local.write_text("local\n", encoding="utf-8", newline="\n")

    assert resolve_workflow_path(cfg, "code/with-review") == local


def test_resolve_workflow_path_falls_back_to_local_when_neither_exists(tmp_path):
    # When neither a local nor a bundled workflow exists, resolution returns the
    # conventional local path so a caller's Workflow.load(...) raises a
    # not-found error naming coga/workflows/ rather than bootstrap/.
    cfg = SimpleNamespace(repo_root=tmp_path)

    assert resolve_workflow_path(cfg, "code/nope") == workflow_path(cfg, "code/nope")


def test_workflow_not_found_lists_group_members_local_and_bundled(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    local = tmp_path / "workflows" / "code" / "house-style.md"
    local.parent.mkdir(parents=True)
    local.write_text("local\n", encoding="utf-8", newline="\n")

    message = workflow_not_found_message(cfg, "code")

    assert "'code' is a workflow group" in message
    assert "code/house-style" in message  # local member
    assert "code/with-review" in message  # bundled member


def test_workflow_not_found_suggests_close_matches_across_sources(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)
    local = tmp_path / "workflows" / "ops" / "deploy.md"
    local.parent.mkdir(parents=True)
    local.write_text("local\n", encoding="utf-8", newline="\n")

    assert "did you mean: ops/deploy" in workflow_not_found_message(cfg, "ops/deplyo")
    assert "code/with-review" in workflow_not_found_message(cfg, "code/with-reveiw")
    # A bare leaf points at every workflow sharing it.
    leaf = workflow_not_found_message(cfg, "with-reveiw")
    assert "code/with-review" in leaf and "docs/with-review" in leaf


def test_workflow_not_found_without_matches_names_local_path(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)

    starter = tmp_path / "workflows" / "_template.md"
    starter.parent.mkdir(parents=True)
    starter.write_text("starter\n", encoding="utf-8", newline="\n")

    message = workflow_not_found_message(cfg, "zzz-qqq")
    assert "_template" not in workflow_not_found_message(cfg, "template")

    assert "did you mean" not in message
    assert str(workflow_path(cfg, "zzz-qqq")) in message


def test_load_workflow_raises_not_found_with_diagnosis(tmp_path):
    cfg = SimpleNamespace(repo_root=tmp_path)

    with pytest.raises(WorkflowNotFoundError, match="is a workflow group"):
        load_workflow(cfg, "code")
    with pytest.raises(WorkflowNotFoundError, match="is a workflow group"):
        git_mode("code", cfg)
    assert load_workflow(cfg, "code/with-review").name == "code/with-review"


@pytest.mark.parametrize("kind", ["directory", "broken-symlink"])
def test_unusable_local_workflow_is_not_replaced_with_bundled_text(tmp_path, kind):
    cfg = SimpleNamespace(repo_root=tmp_path)
    local = workflow_path(cfg, "code/with-review")
    local.parent.mkdir(parents=True)
    if kind == "directory":
        local.mkdir()
    else:
        local.symlink_to(tmp_path / "missing.md")
    assert resolve_workflow_path(cfg, "code/with-review") == local


def test_workflow_path_with_file_as_parent_reports_workflow_error(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    local = workflow_path(cfg, "code/with-review")
    local.parent.parent.mkdir(parents=True)
    local.parent.write_text("not a directory\n", encoding="utf-8", newline="\n")
    with pytest.raises(WorkflowError) as caught:
        resolve_workflow_path(cfg, "code/with-review")
    assert str(local) in str(caught.value)
    assert isinstance(caught.value.__cause__, NotADirectoryError)


@pytest.mark.parametrize("bundled", [False, True])
def test_unsearchable_workflow_path_reports_workflow_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bundled: bool,
) -> None:
    cfg = _cfg(tmp_path)
    candidate = (bootstrap_workflow_path if bundled else workflow_path)(cfg, "code/with-review")
    original = Path.lstat

    def deny(path: Path, *args, **kwargs):
        if path == candidate:
            raise PermissionError("workflow directory cannot be searched")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", deny)
    with pytest.raises(WorkflowError) as caught:
        resolve_workflow_path(cfg, "code/with-review")
    assert str(candidate) in str(caught.value)
    assert isinstance(caught.value.__cause__, PermissionError)


def test_skill_symlink_remains_supported(tmp_path):
    cfg = _cfg(tmp_path)
    target = tmp_path / "local-skill.md"
    target.write_text("skill body\n", encoding="utf-8", newline="\n")
    local = tmp_path / "skills" / "tools" / "example" / "SKILL.md"
    local.parent.mkdir(parents=True)
    local.symlink_to(target)
    assert resolve_skill_path(cfg, "tools/example") == local
