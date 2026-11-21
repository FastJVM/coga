from __future__ import annotations

from pathlib import Path


def test_address_pr_comments_skill_preserves_the_owner_gate() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill = (
        repo_root
        / "src"
        / "coga"
        / "resources"
        / "templates"
        / "coga"
        / "bootstrap"
        / "skills"
        / "code"
        / "address-pr-comments"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "`branch:` and `pr:` under `## Dev`" in skill
    assert "stop if Git refuses" in skill
    assert "owner about ambiguous or conflicting requests" in skill
    assert "Leave the final bump and merge to the owner." in skill
