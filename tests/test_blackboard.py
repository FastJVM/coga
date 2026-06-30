"""Tests for blackboard helpers."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from coga.blackboard import (
    PRODUCTION_NOTES_BLACKBOARD,
    promote_to_production_notes,
    promote_to_production_notes_text,
)


def test_promote_to_production_notes_text_replaces_authoring_scratch() -> None:
    text = dedent(
        """\
        The blackboard.

        ---

        ## Evaluator review

        stale scratch

        ---

        ## Dev

        branch: work
        """
    )

    assert promote_to_production_notes_text(text) == PRODUCTION_NOTES_BLACKBOARD


def test_promote_to_production_notes_text_noops_when_already_promoted() -> None:
    text = (
        PRODUCTION_NOTES_BLACKBOARD
        + "\n---\n\n## Dev\n\nbranch: work\n"
    )

    assert promote_to_production_notes_text(text) == text


def test_promote_to_production_notes_noops_when_blackboard_is_not_required(
    tmp_path: Path,
) -> None:
    ticket = tmp_path / "ticket.md"
    ticket.write_text(
        dedent(
            """\
            ---
            slug: bootstrap/orient
            title: Bootstrap
            ---

            ## Description

            Stateless bootstrap ticket.
            """
        )
    )
    before = ticket.read_text()

    changed = promote_to_production_notes(ticket, blackboard_required=False)

    assert changed is False
    assert ticket.read_text() == before
