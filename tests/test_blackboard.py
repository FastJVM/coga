"""Tests for blackboard helpers."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from coga.blackboard import (
    PRELAUNCH_SYNTHESIS_TEXT_CHARS,
    prelaunch_blackboard_synthesis_reason,
    prelaunch_blackboard_synthesis_reason_text,
    render_blackboard,
)


def test_prelaunch_blackboard_treats_stock_placeholder_as_empty() -> None:
    reason = prelaunch_blackboard_synthesis_reason_text(render_blackboard("Work"))
    assert reason is None


def test_prelaunch_blackboard_detects_authoring_sections() -> None:
    text = dedent(
        """\
        The blackboard is a notepad to be written to often as the human and
        agent works through a task.

        ---

        ## Evaluator review

        stale scratch

        ---

        ## Dev

        branch: work
        """
    )

    reason = prelaunch_blackboard_synthesis_reason_text(text)
    assert reason == "authoring section(s): ## Evaluator review"


def test_prelaunch_blackboard_detects_qualified_authoring_headings() -> None:
    text = dedent(
        """\
        ## Evaluator review (T2, independent cold read)

        Looks underspecified.

        ## Proposals (draft)

        Add a narrower acceptance test.
        """
    )

    reason = prelaunch_blackboard_synthesis_reason_text(text)
    assert (
        reason
        == "authoring section(s): ## Evaluator review (T2, independent cold read), "
        "## Proposals (draft)"
    )


def test_prelaunch_blackboard_accepts_explicit_production_notes() -> None:
    text = dedent(
        """\
        ## Production notes

        Keep this context for launch.

        ---

        ## Evaluator review

        Deliberately retained.
        """
    )

    assert prelaunch_blackboard_synthesis_reason_text(text) is None


def test_prelaunch_blackboard_detects_large_custom_notes() -> None:
    text = "x" * PRELAUNCH_SYNTHESIS_TEXT_CHARS

    assert (
        prelaunch_blackboard_synthesis_reason_text(text)
        == "non-placeholder blackboard is 600 characters"
    )


def test_prelaunch_blackboard_ignores_missing_optional_blackboard(
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

    reason = prelaunch_blackboard_synthesis_reason(
        ticket, blackboard_required=False
    )

    assert reason is None
    assert ticket.read_text() == before
