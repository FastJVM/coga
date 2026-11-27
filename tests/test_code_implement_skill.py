from __future__ import annotations

from pathlib import Path

BOOTSTRAP = (
    Path(__file__).resolve().parents[1] / "src/coga/resources/templates/coga/bootstrap"
)


def test_implement_skill_uses_the_entered_branch_and_keeps_ticket_state_off_it() -> None:
    skill = " ".join(
        (BOOTSTRAP / "skills/code/implement/SKILL.md").read_text(encoding="utf-8").split()
    )

    assert "recorded Git fields" in skill
    assert "The workflow's `enter` script has switched to the recorded branch" in skill
    assert "rather than opening a branch by hand" in skill
    assert "without `coga/tasks/**` or `coga/log.md`" in skill
    assert "`git/ticket-enter/run.py rebase`" in skill
    assert "git/open-branch" not in skill
