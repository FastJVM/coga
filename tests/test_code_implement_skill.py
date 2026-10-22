from __future__ import annotations

from pathlib import Path

BOOTSTRAP = (
    Path(__file__).resolve().parents[1] / "src/coga/resources/templates/coga/bootstrap"
)


def test_implement_skill_has_read_only_git_clone_fallback() -> None:
    skill = (BOOTSTRAP / "skills/code/implement/SKILL.md").read_text(encoding="utf-8")
    owner = (BOOTSTRAP / "contexts/coga/checkouts/sandbox-clone/SKILL.md").read_text(encoding="utf-8")

    assert "coga/checkouts/sandbox-clone" in skill
    assert "First refusal after launch switched" in skill
    # The recipe itself is owned by the sandbox-clone topic.
    assert "git clone --no-hardlinks" in owner
    assert "mktemp -d /tmp/coga-feature" in owner
    assert "switch -C main FETCH_HEAD" in owner
    assert "switch -c <branch-name>" in owner
    assert "Record that clone's repo path as `worktree:`" in owner
    assert "coga block --task <slug>" in owner
    assert "git clone --no-hardlinks" not in skill
