from __future__ import annotations

from pathlib import Path

import yaml

# `code/split-ticket` is the one owner of the split mechanic. The steps that
# can reach a split decision compose it beside their own skill, and those
# skills point at it rather than restating it.

_BOOTSTRAP = Path(__file__).resolve().parents[1] / (
    "src/coga/resources/templates/coga/bootstrap"
)


def _skill(name: str) -> str:
    return (_BOOTSTRAP / "skills" / name / "SKILL.md").read_text()


def test_split_ticket_skill_names_its_conventions() -> None:
    section = _skill("code/split-ticket")

    assert "drafts made by `coga create`, complete when created" in section
    assert "Do not edit a sibling after creating it" in section
    assert "`## Split`" in section
    assert "**Split from `<source-slug>` (<date>).** After: `<prerequisite-slug>`." in section
    assert "*Co-equal*" in section and "*Sequenced*" in section
    assert "a draft cannot be blocked" in section
    assert "megalaunch dependency drain" in section
    assert 'coga mark canceled <slug> --message "Split into <a>, <b>"' in section
    assert "Do not invent a `dependencies:` field" in section


def test_design_and_implement_point_at_the_split_skill_without_restating_it() -> None:
    design = _skill("code/design")
    implement = _skill("code/implement")

    for text in (design, implement):
        assert "`code/split-ticket`" in text
        assert "## Splitting a ticket" not in text
        assert "## Split\n" not in text
    assert "`## Description` opens with `**Split from`" in implement


def test_every_design_and_implement_step_composes_the_split_skill() -> None:
    steps = []
    for path in sorted((_BOOTSTRAP / "workflows" / "code").glob("*.md")):
        frontmatter = yaml.safe_load(path.read_text().split("---", 2)[1])
        steps += [
            (path.name, step)
            for step in frontmatter["steps"]
            if {"code/design", "code/implement"} & set(step.get("skills", []))
        ]

    assert steps
    for name, step in steps:
        assert "code/split-ticket" in step["skills"], (name, step["name"])
