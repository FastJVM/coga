"""The shared fence-aware ticket body section parser (`taskfile.body_sections`)."""

from __future__ import annotations

from coga.taskfile import body_sections, uncomposed_sections


def _sections(text: str) -> dict[str, str]:
    return {
        s.key: text[s.content_start:s.end].strip() for s in body_sections(text)
    }


def test_an_unclosed_fence_does_not_hide_the_context_heading() -> None:
    """A truncated example must not fold `## Context` into Description."""
    text = "## Description\n\n```py\nx = 1\n\n## Context\n\nctx here\n"
    sections = _sections(text)
    assert sections["description"] == "```py\nx = 1"
    assert sections["context"] == "ctx here"


def test_a_closed_fence_after_an_unclosed_opener_still_hides_its_heading() -> None:
    text = (
        "## Description\n\n```py\nstray\n\n~~~\n## Example\n~~~\n\n"
        "## Context\n\nctx\n"
    )
    assert list(_sections(text)) == ["description", "context"]


def test_commonmark_heading_indent_and_closing_sequence() -> None:
    text = "## Description ##\n\nintent\n\n   ## Notes\n\nnotes\n"
    sections = _sections(text)
    assert sections == {"description": "intent", "notes": "notes"}
    assert uncomposed_sections(text) == ["Notes"]


def test_a_hash_run_without_space_is_heading_text() -> None:
    text = "## Description\n\n## C#\n\nlang\n"
    assert list(_sections(text)) == ["description", "c#"]
