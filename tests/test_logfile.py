from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest

from coga.config import load_config
from coga.logfile import (
    first_activity,
    first_activity_map,
    iter_log_messages,
    iter_log_messages_reverse,
)
from coga.paths import log_path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


def test_first_activity_is_earliest_line_even_when_log_is_unsorted(
    repo: Path,
) -> None:
    """`merge=union` can leave the log unsorted; the minimum timestamp wins."""
    cfg = load_config(repo)
    log_path(cfg).write_text(
        "2026-06-05 09:00 [alpha] [human:marc] bumped\n"
        "2026-06-01 10:00 [alpha] [human:marc] created\n"
        "not a log line\n"
        "2026-06-03 11:00 [beta] [human:marc] created\n"
    )

    created = first_activity_map(cfg)

    assert created["alpha"] == datetime(2026, 6, 1, 10, 0)
    assert created["beta"] == datetime(2026, 6, 3, 11, 0)
    assert first_activity(cfg, "alpha") == datetime(2026, 6, 1, 10, 0)


def test_first_activity_missing_log_returns_none(repo: Path) -> None:
    cfg = load_config(repo)

    assert first_activity_map(cfg) == {}
    assert first_activity(cfg, "alpha") is None


def test_iter_log_messages_reverse_yields_entries_newest_line_first(
    repo: Path,
) -> None:
    cfg = load_config(repo)
    log_path(cfg).write_text(
        "2026-06-01 10:00 [alpha] [system] created alpha for 2026-06-01\n"
        "not a log line\n"
        "2026-06-03 11:00 [beta] [system] created beta for 2026-06-03\n"
        "2026-06-05 09:00 [alpha] [human:marc] bumped\n"
    )

    assert list(iter_log_messages_reverse(cfg)) == [
        ("alpha", "bumped"),
        ("beta", "created beta for 2026-06-03"),
        ("alpha", "created alpha for 2026-06-01"),
    ]


def test_iter_log_messages_reverse_reads_across_block_boundaries(
    repo: Path,
) -> None:
    """A line split by the block window must survive the seam, not be dropped."""
    cfg = load_config(repo)
    log_path(cfg).write_text(
        "".join(
            f"2026-06-{day:02d} 10:00 [task-{day}] [system] message {day}\n"
            for day in range(1, 21)
        )
    )

    forward = list(iter_log_messages(cfg))

    assert list(iter_log_messages_reverse(cfg, block_size=7)) == forward[::-1]


def test_iter_log_messages_reverse_handles_a_missing_trailing_newline(
    repo: Path,
) -> None:
    cfg = load_config(repo)
    log_path(cfg).write_text(
        "2026-06-01 10:00 [alpha] [system] first\n"
        "2026-06-02 10:00 [alpha] [system] last"
    )

    assert list(iter_log_messages_reverse(cfg, block_size=4)) == [
        ("alpha", "last"),
        ("alpha", "first"),
    ]


def test_iter_log_messages_reverse_missing_log_yields_nothing(repo: Path) -> None:
    assert list(iter_log_messages_reverse(load_config(repo))) == []
