from __future__ import annotations

from pathlib import Path

# The "Splitting a ticket" contract is inlined, byte-identical, in both step
# skills that instruct a split. It has no single owner file on purpose: the
# split decision arises inside a composed `code/design` or `code/implement`
# step, `dev/code` is attached per ticket rather than composed by default, and
# no CLI prints a bundled non-step skill for a downstream repo's agent to read.
# Like the live/packaged twin rule, the duplication is enforced here rather
# than remembered.

_SKILLS = "src/coga/resources/templates/coga/bootstrap/skills"
_HEADING = "## Splitting a ticket\n"


def _section(skill: str) -> str:
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / _SKILLS / skill / "SKILL.md").read_text()
    assert text.count(_HEADING) == 1, skill
    body = text.split(_HEADING, 1)[1]
    return body.split("\n## ", 1)[0]


def test_design_and_implement_share_one_split_contract() -> None:
    assert _section("code/design") == _section("code/implement")


def test_split_contract_names_its_conventions() -> None:
    section = _section("code/implement")

    assert "made by `coga create`" in section
    assert "`## Split`" in section
    assert "**Split from `<source-slug>` (<date>).**" in section
    assert "After: `<prerequisite-slug>`." in section
    assert "*Co-equal*" in section and "*Sequenced*" in section
    assert "a draft cannot be blocked" in section
    assert "megalaunch dependency drain" in section
    assert 'coga mark canceled <slug> --message "Split into <a>, <b>"' in section
    assert "Do not invent a `dependencies:` field" in section


def test_both_step_skills_point_at_the_split_contract() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    design = (repo_root / _SKILLS / "code/design/SKILL.md").read_text()
    implement = (repo_root / _SKILLS / "code/implement/SKILL.md").read_text()

    assert "*Splitting a\n   ticket* contract below" in design
    assert "*Splitting a ticket* contract above" in implement
    assert "opens with `**Split from`" in implement
