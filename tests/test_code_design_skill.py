from __future__ import annotations

from pathlib import Path


def test_design_skill_requires_symbol_citations() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill = (
        repo_root
        / "src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md"
    ).read_text()

    assert "**Cite symbols, not line numbers.**" in skill
    assert "never a bare" in skill
    assert "navigational aid that is\n     expected to drift" in skill
    assert "state the *relationship* that makes the fact" in skill
    assert "Every source citation in the spec names a file and a symbol." in skill
