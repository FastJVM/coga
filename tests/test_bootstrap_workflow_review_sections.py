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
    "code/with-review.md",
    "docs/with-review.md",
)


def _review_section(name: str) -> str:
    text = (BOOTSTRAP_WORKFLOWS / name).read_text(encoding="utf-8")
    marker = "\n## review\n"
    assert marker in text, f"{name} has no `## review` section"
    return text.split(marker, 1)[1]


@pytest.mark.parametrize("name", CHECKOUT_BEARING_WORKFLOWS)
def test_review_section_names_coga_retire_as_the_closing_act(name: str) -> None:
    review = _review_section(name)

    # Autoclose only closes the ticket; the owner-facing section must say the
    # checkout outlives `done` and name the command that disposes of it.
    assert "`autoclose-merged`" in review
    assert "run `coga retire <slug>`" in review
    assert "`done` is not the end of the ticket" in review
    # A done retire deletes the ticket with no agent; the command ticket owns
    # the procedure, so the summary points there instead of restating it.
    assert "`bootstrap/retire/ticket.md`" in review
    assert "`retro/done-ticket`" not in review


@pytest.mark.parametrize("name", PEER_REVIEW_WORKFLOWS)
def test_peer_review_section_carries_the_authorship_caveat(name: str) -> None:
    text = (BOOTSTRAP_WORKFLOWS / name).read_text(encoding="utf-8")
    sections = _parse_inline_sections(text, {"peer-review"})

    # Only step-named sections are composed, so the caveat must live in the
    # step body itself, not in the workflow preamble the reviewer never sees.
    peer_review = " ".join(sections["peer-review"].split())
    assert "does not prove independent authorship" in peer_review


def test_peer_review_skill_carries_the_authorship_caveat() -> None:
    text = " ".join(PEER_REVIEW_SKILL.read_text(encoding="utf-8").split())
    assert "does not prove independent authorship" in text
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
    if any(step.assignee == "other-agent" for step in workflow.steps):
        return
    # The rationale lives in a real H2 that names no step, so it is framing
    # only and never composes into a launched prompt.
    assert "\n## No other-agent code review\n" in path.read_text(encoding="utf-8")
