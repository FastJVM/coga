"""Tests for blackboard section helpers."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from coga.blackboard import delete_sections, delete_sections_text


def test_delete_sections_text_removes_middle_section_and_separator() -> None:
    text = dedent(
        """\
        The blackboard.

        ---

        ## Notes

        keep this

        ---

        ## Evaluator review

        stale scratch

        ---

        ## Dev

        branch: work
        """
    )

    assert delete_sections_text(text, ["Evaluator review"]) == dedent(
        """\
        The blackboard.

        ---

        ## Notes

        keep this

        ---

        ## Dev

        branch: work
        """
    )


def test_delete_sections_text_removes_orphan_trailing_separator() -> None:
    text = dedent(
        """\
        The blackboard.

        ---

        ## Evaluator review

        stale scratch
        """
    )

    assert delete_sections_text(text, ["## Evaluator review"]) == "The blackboard.\n"


def test_delete_sections_text_noops_when_heading_absent() -> None:
    text = dedent(
        """\
        The blackboard.

        ---

        ## Notes

        keep this
        """
    )

    assert delete_sections_text(text, ["Evaluator review"]) == text


def test_delete_sections_noops_when_blackboard_is_not_required(tmp_path: Path) -> None:
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

    changed = delete_sections(
        ticket,
        ["Evaluator review"],
        blackboard_required=False,
    )

    assert changed is False
    assert ticket.read_text() == before
