"""Tests for blackboard helpers."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from coga.blackboard import (
    PRELAUNCH_SYNTHESIS_TEXT_CHARS,
    blackboard_for_prompt,
    blackboard_size_warning,
    prelaunch_blackboard_synthesis_reason,
    prelaunch_blackboard_synthesis_reason_text,
    render_blackboard,
)
from coga.config import Config, load_config


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


def test_prelaunch_blackboard_preserves_large_superseded_design() -> None:
    text = (
        render_blackboard("Work")
        + "\n\n## Superseded designs\n\n### 2026-09-04 — Old plan\n\n"
        + "Superseded by: Current plan\n\nReason: Simpler implementation\n\n"
        + "#### Prior requirements\n\n"
        + "Prior design detail. " * 60
    )
    assert prelaunch_blackboard_synthesis_reason_text(text) is None
    for scratch in (
        "\n## Evaluator review\n\nNeeds synthesis.\n",
        "\n## Notes\n\n" + "x" * PRELAUNCH_SYNTHESIS_TEXT_CHARS,
    ):
        assert prelaunch_blackboard_synthesis_reason_text(text + scratch) is not None
        assert prelaunch_blackboard_synthesis_reason_text(scratch + text) is not None


@pytest.mark.parametrize("fence", ["```", "~~~", "````"])
def test_prelaunch_blackboard_archive_examples_still_need_synthesis(fence: str) -> None:
    text = (
        f"{fence}markdown\n## Superseded designs\n"
        + "Authoring scratch. " * 60
        + f"\n{fence}\n"
    )
    assert prelaunch_blackboard_synthesis_reason_text(text) is not None


def test_prelaunch_blackboard_ignores_historical_headings_inside_archive() -> None:
    text = dedent(
        """\
        ## Superseded designs
        ### 2026-09-18 — Old plan
        ```markdown
        ## Evaluator review
        Retained review of the old plan.
        ## Production notes
        This old example does not exempt live scratch.
        ```

        ## Superseded designs
        Another archived plan.
        """
    )
    assert prelaunch_blackboard_synthesis_reason_text(text) is None
    assert prelaunch_blackboard_synthesis_reason_text(
        text + "\n## Evaluator review\nLive scratch needs synthesis.\n"
    ) == "authoring section(s): ## Evaluator review"


def test_superseded_designs_archive_ends_only_at_atx_headings(tmp_path: Path) -> None:
    # `dev/design-history` narrows the boundary to ATX `#`/`##` lines: a Setext
    # underline is not a boundary because `---` is also the blackboard's
    # section separator and would split the archive at every separator.
    text = dedent(
        """        ## Notes
        Live notes.

        ## Superseded designs
        ### 2026-09-18 — Old plan
        Old plan text.
        ---
        Still archived after the separator.
        Current handoff
        ---------------
        Still archived: a Setext underline is not a boundary.

        ## Verification
        Live again.
        """
    )
    projected = blackboard_for_prompt(text, tmp_path / "ticket.md")
    assert "Live notes." in projected
    assert "Live again." in projected
    assert "Old plan text." not in projected
    assert "Still archived after the separator." not in projected
    assert "Still archived: a Setext underline is not a boundary." not in projected


def test_blackboard_size_warning_measures_live_prompt_content(tmp_path: Path) -> None:
    ticket = tmp_path / "ticket.md"
    ticket.write_text(
        "---\ntitle: Work\n---\n\n## Description\nCurrent work.\n\n"
        "<!-- coga:blackboard -->\n\n## Superseded designs\n"
        + "Old design. " * 4000
    )
    before = ticket.read_bytes()

    assert blackboard_size_warning(ticket) is None
    assert ticket.read_bytes() == before

    ticket.write_bytes(before + b"\n## Notes\n" + b"Live notes. " * 4000)
    assert blackboard_size_warning(ticket) is not None


def test_prelaunch_blackboard_ignores_missing_optional_blackboard(
    tmp_path: Path,
) -> None:
    ticket = tmp_path / "ticket.md"
    ticket.write_text(
        dedent(
            """\
            ---
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


def _cfg_with_blackboard_override(tmp_path: Path, template: str | None) -> Config:
    root = tmp_path / "coga"
    root.mkdir()
    (root / "coga.toml").write_text(
        'version = 1\n[agents.claude]\ncli = "claude"\nfile = "CLAUDE.md"\n'
    )
    (root / "coga.local.toml").write_text('user = "marc"\n')
    if template is not None:
        (root / "resources").mkdir()
        (root / "resources" / "blackboard.md").write_text(template)
    return load_config(root)


def test_render_blackboard_uses_repo_override(tmp_path: Path) -> None:
    cfg = _cfg_with_blackboard_override(
        tmp_path, "## Working notes for {task_title}\n\nRepo stub.\n"
    )

    assert render_blackboard("Work", cfg=cfg) == (
        "## Working notes for Work\n\nRepo stub.\n"
    )


def test_render_blackboard_falls_back_to_packaged_template(tmp_path: Path) -> None:
    cfg = _cfg_with_blackboard_override(tmp_path, None)

    assert render_blackboard("Work", cfg=cfg) == render_blackboard("Work")


def test_prelaunch_blackboard_treats_every_stock_form_as_empty(
    tmp_path: Path,
) -> None:
    """With an override, the packaged stub (tickets created before it), the
    raw override, and the title-rendered override all count as stock."""
    template = "## Working notes for {task_title}\n\n" + "Repo stub. " * 60 + "\n"
    cfg = _cfg_with_blackboard_override(tmp_path, template)

    for text in (
        render_blackboard("Work"),
        template,
        render_blackboard("Fix retry logic", cfg=cfg),
    ):
        assert prelaunch_blackboard_synthesis_reason_text(text, cfg=cfg) is None

    edited = render_blackboard("Work", cfg=cfg) + "\n## Evaluator review\n\nx\n"
    assert prelaunch_blackboard_synthesis_reason_text(edited, cfg=cfg) == (
        "authoring section(s): ## Evaluator review"
    )
    # Without the repo config the long override is just non-placeholder text.
    assert prelaunch_blackboard_synthesis_reason_text(
        render_blackboard("Work", cfg=cfg)
    ) is not None
