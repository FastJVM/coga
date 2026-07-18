from __future__ import annotations

from pathlib import Path


def test_implement_skill_has_read_only_git_clone_fallback() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill = (
        repo_root
        / "src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md"
    ).read_text()

    assert "git clone --no-hardlinks" in skill
    assert "mktemp -d /tmp/coga-feature" in skill
    assert "switch -C main FETCH_HEAD" in skill
    assert "switch -c <branch-name>" in skill
    assert "Record that clone's repo path as `worktree:`" in skill
    assert "coga block --task <slug>" in skill
