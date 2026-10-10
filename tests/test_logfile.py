from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest

from coga.config import load_config
from coga.logfile import (
    append_log,
    decode_log_message,
    first_activity,
    first_activity_map,
    iter_log_messages,
    iter_log_messages_reverse,
    last_activity_map,
    retract_log_lines,
    task_log_lines,
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


# A sync failure carrying complete Git stderr, as `mark.py` logs it.
_GIT_STDERR = (
    "sync failed: git push failed:\n"
    "To github.com:org/repo.git\r\n"
    " ! [rejected]        main -> main (fetch first)\r"
    "hint: see C:\\new\\repo and a literal \\n here"
)


def test_append_log_writes_one_physical_line_for_multiline_messages(
    repo: Path,
) -> None:
    """LF, CRLF, bare CR, and literal backslashes all stay on one line."""
    cfg = load_config(repo)

    written = append_log(cfg, "alpha", "git", _GIT_STDERR)

    data = log_path(cfg).read_bytes()
    assert data == written
    assert data.count(b"\n") == 1 and data.endswith(b"\n")
    assert b"\r" not in data
    assert written.decode("utf-8").rstrip("\n").endswith(
        "sync failed: git push failed:\\nTo github.com:org/repo.git\\r\\n"
        " ! [rejected]        main -> main (fetch first)\\r"
        "hint: see C:\\\\new\\\\repo and a literal \\\\n here"
    )
    assert list(iter_log_messages(cfg)) == [("alpha", _GIT_STDERR)]
    assert list(iter_log_messages_reverse(cfg, block_size=5)) == [
        ("alpha", _GIT_STDERR)
    ]
    assert task_log_lines(cfg, "alpha") == [written.decode("utf-8").rstrip("\n")]


def test_decode_log_message_passes_other_backslash_sequences_through() -> None:
    assert decode_log_message(r'{"q":"say \"hi\"","t":"\t"}') == (
        r'{"q":"say \"hi\"","t":"\t"}'
    )


def test_append_log_keeps_other_line_breaking_characters_in_one_event(
    repo: Path,
) -> None:
    """Out-of-scope controls pass through, and readers split on LF only."""
    cfg = load_config(repo)
    message = "tab\tform\x0cfeed\x0bvt\u2028sep\x1b[31mred"

    append_log(cfg, "alpha", "system", message)

    assert list(iter_log_messages(cfg)) == [("alpha", message)]
    assert len(task_log_lines(cfg, "alpha")) == 1


def test_readers_tolerate_legacy_continuation_lines(repo: Path) -> None:
    """Pre-encoding events left untagged continuation lines; skip, never crash."""
    cfg = load_config(repo)
    log_path(cfg).write_text(
        "2026-06-01 10:00 [alpha] [git] sync failed: git push failed:\n"
        "[alpha] To github.com:org/repo.git\n"
        " ! [rejected]        main -> main (fetch first)\n"
        "2026-06-02 10:00 [beta] [human:marc] created\n"
        "hint: stray continuation of beta\n"
        "2026-06-03 10:00 [alpha] [human:marc] bumped\n"
    )

    assert list(iter_log_messages(cfg)) == [
        ("alpha", "sync failed: git push failed:"),
        ("beta", "created"),
        ("alpha", "bumped"),
    ]
    assert list(iter_log_messages_reverse(cfg, block_size=9)) == [
        ("alpha", "bumped"),
        ("beta", "created"),
        ("alpha", "sync failed: git push failed:"),
    ]
    assert last_activity_map(cfg) == {
        "alpha": datetime(2026, 6, 3, 10, 0),
        "beta": datetime(2026, 6, 2, 10, 0),
    }
    assert first_activity(cfg, "alpha") == datetime(2026, 6, 1, 10, 0)
    # `coga show` keeps each legacy continuation with the event it follows.
    assert task_log_lines(cfg, "alpha") == [
        "2026-06-01 10:00 [alpha] [git] sync failed: git push failed:",
        "[alpha] To github.com:org/repo.git",
        " ! [rejected]        main -> main (fetch first)",
        "2026-06-03 10:00 [alpha] [human:marc] bumped",
    ]
    assert task_log_lines(cfg, "beta") == [
        "2026-06-02 10:00 [beta] [human:marc] created",
        "hint: stray continuation of beta",
    ]


def test_retract_log_lines_removes_the_whole_multiline_event(repo: Path) -> None:
    cfg = load_config(repo)
    append_log(cfg, "beta", "human:marc", "created")
    before = log_path(cfg).read_bytes()
    append_log(cfg, "alpha", "git", _GIT_STDERR)
    peer = append_log(cfg, "beta", "git", "push failed:\nrefusing [alpha]\r\n")
    append_log(cfg, "alpha", "human:marc", "bumped")

    retract_log_lines(cfg, "alpha", before)

    assert log_path(cfg).read_bytes() == before + peer
    assert [ref for ref, _ in iter_log_messages(cfg)] == ["beta", "beta"]


def test_retract_log_lines_keeps_peer_event_mentioning_the_tag(
    repo: Path,
) -> None:
    """Match the `[ref]` field, not a substring anywhere in the line."""
    cfg = load_config(repo)
    before = b"2026-06-01 10:00 [alpha] [human:marc] created\n"
    peer = b"2026-06-01 10:01 [beta] [system] blocked on [alpha]\n"
    log_path(cfg).write_bytes(
        before
        + b"2026-06-01 10:02 [alpha] [git] sync failed: one\n"
        + b"legacy continuation two\n"
        + peer
        + b"2026-06-01 10:03 [alpha] [human:marc] bumped"
    )

    retract_log_lines(cfg, "alpha", before)

    assert log_path(cfg).read_bytes() == before + peer


def test_version_marker_preserves_legacy_text_and_distinguishes_new_events(repo: Path) -> None:
    cfg = load_config(repo)
    message = r'v1 C:\temp\file literal \n and \\ and \r'
    legacy = f"2026-06-01 10:00 [alpha] [system] {message}\n"
    log_path(cfg).write_text(legacy)
    written = append_log(cfg, "alpha", "system", message)
    assert b" v1 [alpha] [system] " in written
    assert log_path(cfg).read_bytes().startswith(legacy.encode())
    expected = [("alpha", message), ("alpha", message)]
    assert list(iter_log_messages(cfg)) == expected
    assert list(iter_log_messages_reverse(cfg, block_size=3)) == expected[::-1]
    assert first_activity(cfg, "alpha") == datetime(2026, 6, 1, 10, 0)
    assert last_activity_map(cfg)["alpha"] == datetime.strptime(
        written.decode()[:16], "%Y-%m-%d %H:%M"
    )
    assert task_log_lines(cfg, "alpha") == [legacy.rstrip("\n"), written.decode().rstrip("\n")]
