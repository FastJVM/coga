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
    reviews = [
        index for index, step in enumerate(workflow.steps)
        if step.name == "peer-review" and step.assignee == "other-agent"
    ]
    if reviews:
        # Design evaluation alone is not code review: the peer must inspect
        # the implementation before publication.
        names = [step.name for step in workflow.steps]
        assert names.index("implement") < reviews[0] < names.index("open-pr")
        return
    # The rationale lives in a real H2 that names no step, so it is framing
    # only and never composes into a launched prompt.
    assert "\n## No other-agent code review\n" in path.read_text(encoding="utf-8")


def test_agent_merge_mirrors_with_review_except_the_final_step() -> None:
    merge = Workflow.load(AGENT_MERGE)
    review = Workflow.load(BOOTSTRAP_WORKFLOWS / "code/with-review.md")

    assert merge.steps[:-1] == review.steps[:-1]
    final = merge.steps[-1]
    assert (final.name, final.assignee, final.skills) == (
        "merge", "agent", ("code/merge-pr",)
    )
    assert all(step.assignee != "owner" for step in merge.steps)


def test_agent_merge_section_names_coga_retire_as_the_closing_act() -> None:
    text = AGENT_MERGE.read_text(encoding="utf-8")
    merge = " ".join(text.split("\n## merge\n", 1)[1].split())

    # A bump close disposes of nothing, so the branch outlives `done`.
    assert "`done` is not the end of the ticket" in merge
    assert "`coga retire <slug>`" in merge
    assert "`bootstrap/retire/ticket.md`" in merge
    assert "`autoclose-merged`" in merge


def test_merge_pr_skill_refuses_instead_of_forcing() -> None:
    text = " ".join(MERGE_PR_SKILL.read_text(encoding="utf-8").split())

    # The merge is pinned to the reviewed, verified head and never bypasses
    # protection or defers to a scheduled merge.
    assert "--match-head-commit <verified-head>" in text
    assert "never pass `--admin`" in text
    assert "Do not pass `--auto` or `--delete-branch`" in text
    assert "viewerDefaultMergeMethod" in text
    assert "escalate per your launch mode" in text
    assert "`coga bump <slug>" in text
    # A shared step skill refers to the preceding steps by skill, not name.
    assert "`peer-review` step" not in text
