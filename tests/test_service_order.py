"""The megalaunch drain order — age, plus numbered sub-directories."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from coga.service_order import leading_number, service_order
from coga.tasks import TaskRef


def ref(id_slug: str) -> TaskRef:
    """A TaskRef for `<dir>/<leaf>` (or a bare top-level leaf)."""
    directory, _, leaf = id_slug.rpartition("/")
    return TaskRef(
        slug=leaf,
        path=Path("/tmp/tasks") / id_slug,
        directory=directory or None,
    )


def order(slugs: list[str], created: dict[str, str]) -> list[str]:
    stamps = {
        slug: datetime.strptime(value, "%Y-%m-%d %H:%M")
        for slug, value in created.items()
    }
    return [r.id_slug for r in service_order([ref(s) for s in slugs], stamps)]


def test_leading_number_reads_only_a_whole_first_segment() -> None:
    assert leading_number("1-schema") == 1
    assert leading_number("02-migrate") == 2  # zero-padded is the same slot
    assert leading_number("10-cutover") == 10  # numeric, not lexicographic
    # Not numbered: digits must be the entire first segment.
    assert leading_number("2fa-login") is None
    assert leading_number("schema-1") is None
    assert leading_number("spike-idea") is None


def test_numbered_subdir_runs_in_number_order_not_age_order() -> None:
    """The point of the feature: naming beats creation time inside a sub-tree."""
    assert order(
        ["v2/3-cutover", "v2/1-schema", "v2/2-migrate"],
        {
            # Created in exactly the wrong order.
            "v2/3-cutover": "2026-06-01 10:00",
            "v2/2-migrate": "2026-06-02 10:00",
            "v2/1-schema": "2026-06-03 10:00",
        },
    ) == ["v2/1-schema", "v2/2-migrate", "v2/3-cutover"]


def test_unnumbered_siblings_run_after_the_numbered_ones_by_age() -> None:
    assert order(
        ["v2/spike", "v2/2-migrate", "v2/hotfix", "v2/1-schema"],
        {
            "v2/spike": "2026-06-04 10:00",
            "v2/hotfix": "2026-06-01 10:00",
            "v2/1-schema": "2026-06-02 10:00",
            "v2/2-migrate": "2026-06-03 10:00",
        },
    ) == ["v2/1-schema", "v2/2-migrate", "v2/hotfix", "v2/spike"]


def test_numbered_block_is_anchored_at_its_oldest_task() -> None:
    """A numbered sub-tree runs when its first task would have, not sooner.

    `v2` is anchored at `2-migrate` (its oldest, 06-02), so the block lands
    between the two top-level tasks rather than jumping the whole queue.
    """
    assert order(
        ["alpha", "omega", "v2/1-schema", "v2/2-migrate"],
        {
            "alpha": "2026-06-01 10:00",
            "v2/2-migrate": "2026-06-02 10:00",
            "omega": "2026-06-05 10:00",
            "v2/1-schema": "2026-06-09 10:00",
        },
    ) == ["alpha", "v2/1-schema", "v2/2-migrate", "omega"]


def test_directory_without_numbered_tasks_keeps_plain_age_slots() -> None:
    """No opt-in, no grouping — an unnumbered sub-tree interleaves as before."""
    assert order(
        ["alpha", "marketing/brief", "omega", "marketing/draft"],
        {
            "marketing/brief": "2026-06-01 10:00",
            "alpha": "2026-06-02 10:00",
            "marketing/draft": "2026-06-03 10:00",
            "omega": "2026-06-04 10:00",
        },
    ) == ["marketing/brief", "alpha", "marketing/draft", "omega"]


def test_numbering_is_per_directory() -> None:
    """Two numbered sub-trees don't interleave; each runs as its own block."""
    assert order(
        ["v2/1-schema", "mkt/1-brief", "v2/2-migrate", "mkt/2-draft"],
        {
            "mkt/1-brief": "2026-06-01 10:00",
            "mkt/2-draft": "2026-06-02 10:00",
            "v2/1-schema": "2026-06-03 10:00",
            "v2/2-migrate": "2026-06-04 10:00",
        },
    ) == ["mkt/1-brief", "mkt/2-draft", "v2/1-schema", "v2/2-migrate"]


def test_nested_directories_are_distinct_groups() -> None:
    assert order(
        ["mkt/2-draft", "mkt/social/1-post", "mkt/1-brief", "mkt/social/2-boost"],
        {
            "mkt/1-brief": "2026-06-01 10:00",
            "mkt/2-draft": "2026-06-02 10:00",
            "mkt/social/1-post": "2026-06-03 10:00",
            "mkt/social/2-boost": "2026-06-04 10:00",
        },
    ) == ["mkt/1-brief", "mkt/2-draft", "mkt/social/1-post", "mkt/social/2-boost"]


def test_top_level_numbering_is_ignored() -> None:
    """`tasks/` itself is not a pipeline — top-level tasks stay age-ordered."""
    assert order(
        ["1-second", "2-first"],
        {"2-first": "2026-06-01 10:00", "1-second": "2026-06-02 10:00"},
    ) == ["2-first", "1-second"]


def test_tasks_with_no_log_line_sort_last_stable_by_slug() -> None:
    assert order(
        ["zeta", "alpha", "known"],
        {"known": "2026-06-09 10:00"},
    ) == ["known", "alpha", "zeta"]
