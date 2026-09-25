from __future__ import annotations

from pathlib import Path

import pytest

BOOTSTRAP_WORKFLOWS = (
    Path(__file__).resolve().parents[1]
    / "src/coga/resources/templates/coga/bootstrap/workflows"
)

# Every packaged workflow whose implement step records `branch:` under
# `## Dev`; its `done` ticket leaves a branch (or legacy worktree) behind.
CHECKOUT_BEARING_WORKFLOWS = (
    "code/with-review.md",
    "code/with-self-review.md",
    "code/design-then-implement.md",
    "docs/with-review.md",
)


def _review_section(name: str) -> str:
    text = (BOOTSTRAP_WORKFLOWS / name).read_text()
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
    assert "`retro/done-ticket`" in review
