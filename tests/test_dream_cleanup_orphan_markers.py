from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay.dream_cleanup_orphan_markers import (
    ACTION_CANDIDATE_ONLY,
    ACTION_HUMAN_NEEDED,
    ACTION_PR_OPENED,
    ACTION_SKIPPED_OPEN_PR,
    CleanupAction,
    OrphanCandidate,
    _blackboard_has_processed_marker,
    _ticket_is_done,
    build_slack_summary,
    find_orphan_candidates,
    process_candidates,
    render_blackboard_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _seed_done_with_marker(relay_os: Path, slug: str) -> Path:
    task = relay_os / "tasks" / slug
    _write(
        task / "ticket.md",
        """
        ---
        title: Done one
        status: done
        mode: auto
        owner: nick
        assignee: claude1
        ---

        ## Description

        Stuff.
        """,
    )
    _write(
        task / "blackboard.md",
        """
        Notes.

        ## Retro

        skill: retro/done-ticket
        status: processed
        """,
    )
    _write(task / "log.md", "")
    return task


def _seed_done_no_marker(relay_os: Path, slug: str) -> Path:
    task = relay_os / "tasks" / slug
    _write(
        task / "ticket.md",
        """
        ---
        title: Done unprocessed
        status: done
        mode: auto
        owner: nick
        assignee: claude1
        ---

        ## Description
        """,
    )
    _write(task / "blackboard.md", "Notes only.\n")
    _write(task / "log.md", "")
    return task


def _seed_active_with_marker(relay_os: Path, slug: str) -> Path:
    """Active tickets with the marker should not be candidates."""
    task = relay_os / "tasks" / slug
    _write(
        task / "ticket.md",
        """
        ---
        title: Active with marker
        status: active
        mode: auto
        owner: nick
        assignee: claude1
        ---
        """,
    )
    _write(
        task / "blackboard.md",
        """
        ## Retro

        skill: retro/done-ticket
        status: processed
        """,
    )
    _write(task / "log.md", "")
    return task


def test_ticket_is_done_matches_exact_status_only(tmp_path: Path) -> None:
    done = tmp_path / "done.md"
    _write(
        done,
        """
        ---
        status: done
        ---
        body
        """,
    )
    active = tmp_path / "active.md"
    _write(
        active,
        """
        ---
        status: active
        ---
        body
        """,
    )
    notdone = tmp_path / "notdone.md"
    _write(
        notdone,
        """
        ---
        status: done-ish
        ---
        body
        """,
    )
    assert _ticket_is_done(done) is True
    assert _ticket_is_done(active) is False
    assert _ticket_is_done(notdone) is False


def test_blackboard_marker_requires_both_skill_and_status(tmp_path: Path) -> None:
    both = tmp_path / "both.md"
    both.write_text(
        "## Retro\n\nskill: retro/done-ticket\nstatus: processed\n"
    )
    only_skill = tmp_path / "only_skill.md"
    only_skill.write_text("## Retro\n\nskill: retro/done-ticket\n")
    only_status = tmp_path / "only_status.md"
    only_status.write_text("## Retro\n\nstatus: processed\n")
    other_section = tmp_path / "other.md"
    other_section.write_text(
        "## Notes\n\nskill: retro/done-ticket\nstatus: processed\n"
    )
    assert _blackboard_has_processed_marker(both) is True
    assert _blackboard_has_processed_marker(only_skill) is False
    assert _blackboard_has_processed_marker(only_status) is False
    assert _blackboard_has_processed_marker(other_section) is False


def test_find_orphan_candidates_filters_correctly(tmp_path: Path) -> None:
    relay_os = tmp_path / "relay-os"
    _seed_done_with_marker(relay_os, "alpha")
    _seed_done_no_marker(relay_os, "beta")
    _seed_active_with_marker(relay_os, "gamma")

    candidates = find_orphan_candidates(relay_os)
    slugs = sorted(c.slug for c in candidates)
    assert slugs == ["alpha"]


def test_process_candidates_reports_only_without_open_prs_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relay_os = tmp_path / "relay-os"
    _seed_done_with_marker(relay_os, "alpha")
    candidates = find_orphan_candidates(relay_os)

    monkeypatch.setattr(
        "relay.dream_cleanup_orphan_markers.list_open_prs_touching",
        lambda repo, slug: [],
    )

    actions = process_candidates(relay_os, candidates, open_prs=False)
    assert len(actions) == 1
    assert actions[0].action == ACTION_CANDIDATE_ONLY
    assert actions[0].pr_url is None


def test_process_candidates_skips_when_open_pr_touches_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relay_os = tmp_path / "relay-os"
    _seed_done_with_marker(relay_os, "alpha")
    candidates = find_orphan_candidates(relay_os)

    monkeypatch.setattr(
        "relay.dream_cleanup_orphan_markers.list_open_prs_touching",
        lambda repo, slug: [42],
    )

    actions = process_candidates(relay_os, candidates, open_prs=True)
    assert len(actions) == 1
    assert actions[0].action == ACTION_SKIPPED_OPEN_PR
    assert "#42" in actions[0].detail


def test_process_candidates_opens_pr_when_flag_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relay_os = tmp_path / "relay-os"
    _seed_done_with_marker(relay_os, "alpha")
    candidates = find_orphan_candidates(relay_os)

    monkeypatch.setattr(
        "relay.dream_cleanup_orphan_markers.list_open_prs_touching",
        lambda repo, slug: [],
    )
    monkeypatch.setattr(
        "relay.dream_cleanup_orphan_markers.open_cleanup_pr",
        lambda repo, slug, base_branch="main": "https://example/pr/1",
    )

    actions = process_candidates(relay_os, candidates, open_prs=True)
    assert len(actions) == 1
    assert actions[0].action == ACTION_PR_OPENED
    assert actions[0].pr_url == "https://example/pr/1"


def test_render_report_no_op_when_empty() -> None:
    report = render_blackboard_report([], generated_at="2026-05-08T00:00:00", opened_prs=True)
    assert "## Dream Worker: cleanup-orphan-markers" in report
    assert "no orphan-marker done tickets" in report


def test_render_report_includes_counts_and_urls() -> None:
    actions = [
        CleanupAction(slug="alpha", action=ACTION_PR_OPENED, detail="opened", pr_url="u1"),
        CleanupAction(slug="beta", action=ACTION_SKIPPED_OPEN_PR, detail="open PR(s) already touching the dir: #99"),
        CleanupAction(slug="gamma", action=ACTION_CANDIDATE_ONLY, detail="report"),
        CleanupAction(slug="delta", action=ACTION_HUMAN_NEEDED, detail="boom"),
    ]
    report = render_blackboard_report(actions, generated_at="2026-05-08T00:00:00", opened_prs=True)
    assert "1 pr-opened" in report
    assert "1 skipped (open PR)" in report
    assert "1 candidate-only" in report
    assert "1 human-needed" in report
    assert "u1" in report
    assert "`alpha`" in report


def test_build_slack_summary_describes_actions() -> None:
    actions = [
        CleanupAction(slug="alpha", action=ACTION_PR_OPENED, detail=""),
        CleanupAction(slug="beta", action=ACTION_SKIPPED_OPEN_PR, detail=""),
    ]
    summary = build_slack_summary(actions, opened_prs=True)
    assert "1 PR(s) opened" in summary
    assert "1 already-in-flight" in summary

    empty = build_slack_summary([], opened_prs=False)
    assert "no orphan-marker done tickets" in empty
