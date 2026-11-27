from __future__ import annotations

from pathlib import Path

import pytest

from coga.workflow import Workflow, _parse_inline_sections

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "src/coga/resources/templates/coga"
BOOTSTRAP_WORKFLOWS = TEMPLATES / "bootstrap/workflows"
PEER_REVIEW_SKILL = TEMPLATES / "bootstrap/skills/code/peer-review/SKILL.md"

# Every packaged workflow whose implement step records `branch:` under
# `## Dev`; its `done` ticket leaves a branch (or legacy worktree) behind.
CHECKOUT_BEARING_WORKFLOWS = (
    "code/with-review.md",
    "code/with-self-review.md",
    "code/design-then-implement.md",
    "docs/with-review.md",
)

# Packaged workflows with an `other-agent` peer-review step.
PEER_REVIEW_WORKFLOWS = (
    "code/agent-merge.md",
    "code/with-review.md",
    "docs/with-review.md",
)


AGENT_MERGE = BOOTSTRAP_WORKFLOWS / "code/agent-merge.md"
MERGE_PR_SKILL = TEMPLATES / "bootstrap/skills/code/merge-pr/SKILL.md"


def _review_section(name: str) -> str:
    text = (BOOTSTRAP_WORKFLOWS / name).read_text(encoding="utf-8")
    marker = "\n## review\n"
    assert marker in text, f"{name} has no `## review` section"
    return text.split(marker, 1)[1]


@pytest.mark.parametrize("name", CHECKOUT_BEARING_WORKFLOWS)
def test_review_section_names_owner_completion_publication(name: str) -> None:
    text = _review_section(name).split("\n## ", 1)[0]
    assert "final bump" in text
    assert "`exit` step script" in text
    assert "publishes the finished ticket to the base" in text


@pytest.mark.parametrize("name", PEER_REVIEW_WORKFLOWS)
def test_peer_review_section_carries_the_authorship_caveat(name: str) -> None:
    text = (BOOTSTRAP_WORKFLOWS / name).read_text(encoding="utf-8")
    sections = _parse_inline_sections(text, {"peer-review"})

    # Only step-named sections are composed, so the caveat must live in the
    # step body itself, not in the workflow preamble the reviewer never sees.
    peer_review = " ".join(sections["peer-review"].split())
    assert "record the actual reviewer" in peer_review


def test_peer_review_skill_carries_the_authorship_caveat() -> None:
    text = " ".join(PEER_REVIEW_SKILL.read_text(encoding="utf-8").split())
    assert "record the actual reviewer" in text
    # A shared step skill refers to the next frozen step, never a step by name.
    assert "`open-pr` step" not in text


def _all_workflow_files() -> list[Path]:
    roots = (
        BOOTSTRAP_WORKFLOWS,
        TEMPLATES / "workflows",
        REPO / "coga/workflows",
    )
    return sorted(
        path
        for root in roots
        for path in root.rglob("*.md")
        if path.name != "_template.md"
    )


@pytest.mark.parametrize(
    "path", _all_workflow_files(), ids=lambda path: str(path.relative_to(REPO))
)
def test_every_workflow_has_other_agent_review_or_says_why_not(path: Path) -> None:
    workflow = Workflow.load(path)
    reviews = [
        index for index, step in enumerate(workflow.steps)
        if step.name == "peer-review" and step.assignee == "other-agent"
    ]
    if reviews:
        # Design evaluation alone is not code review: the peer must inspect
        # the implementation before publication.
        names = [step.name for step in workflow.steps]
        assert names.index("implement") < reviews[0] < names.index("push-and-open-pr")
        return
    # The rationale lives in a real H2 that names no step, so it is framing
    # only and never composes into a launched prompt.
    assert "\n## No other-agent code review\n" in path.read_text(encoding="utf-8")


def test_agent_merge_mirrors_with_review_except_the_final_step() -> None:
    merge = Workflow.load(AGENT_MERGE)
    review = Workflow.load(BOOTSTRAP_WORKFLOWS / "code/with-review.md")

    assert merge.steps[:-1] == review.steps[:-1]
    final = merge.steps[-1]
    assert (final.name, final.assignee, final.run) == (
        "merge", "agent", "code/merge-pr",
    )
    assert all(step.assignee != "owner" for step in merge.steps)


def test_agent_merge_section_names_head_and_checks() -> None:
    text = AGENT_MERGE.read_text(encoding="utf-8")
    merge = " ".join(_parse_inline_sections(text, {"merge"})["merge"].split())
    assert "waits for checks" in merge
    assert "merges that exact head" in merge
    assert "final bump publishes the finished ticket to the base" in merge
