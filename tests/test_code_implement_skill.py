from __future__ import annotations

from pathlib import Path

BOOTSTRAP = (
    Path(__file__).resolve().parents[1] / "src/coga/resources/templates/coga/bootstrap"
)


def test_implement_skill_uses_the_ticket_branch_and_legacy_setup() -> None:
    skill = (BOOTSTRAP / "skills/code/implement/SKILL.md").read_text(encoding="utf-8")

    assert "recorded Git fields" in skill
    assert "git/open-branch/run.py --no-bump" in skill
    assert "Keep the current `implement` step open." in skill
    assert "stop if Git refuses" in skill
