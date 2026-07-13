from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from coga.cli import app
from coga.usage import UsageRecord, append_record, load_records, parse_session, rollup


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _window() -> tuple[datetime, datetime]:
    return (
        datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 23, 13, 0, tzinfo=timezone.utc),
    )


def test_parse_claude_transcript_sums_assistant_usage(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    session_id = "session-123"
    cwd_hash = str(cwd.resolve()).replace("/", "-").replace(".", "-")
    transcript = tmp_path / ".claude" / "projects" / cwd_hash / f"{session_id}.jsonl"
    _write(
        transcript,
        """
        {"type":"assistant","timestamp":"2026-06-23T11:59:00Z","message":{"model":"claude-old","usage":{"input_tokens":999,"cache_creation_input_tokens":999,"cache_read_input_tokens":999,"output_tokens":999}}}
        {"type":"user","timestamp":"2026-06-23T12:01:00Z","message":{}}
        {"type":"assistant","timestamp":"2026-06-23T12:02:00Z","message":{"model":"claude-sonnet-4","usage":{"input_tokens":10,"cache_creation_input_tokens":2,"cache_read_input_tokens":3,"output_tokens":4}}}
        {"type":"assistant","timestamp":"2026-06-23T12:03:00Z","message":{"model":"claude-sonnet-4","usage":{"input_tokens":5,"cache_creation_input_tokens":1,"cache_read_input_tokens":7,"output_tokens":8}}}
        """,
    )
    start, end = _window()

    parsed = parse_session(
        "claude",
        cwd=cwd,
        session_id=session_id,
        pre_existing=None,
        window_start=start,
        window_end=end,
    )

    assert parsed.usage_status == "ok"
    assert parsed.provider == "anthropic"
    assert parsed.model == "claude-sonnet-4"
    assert parsed.session_id == session_id
    assert parsed.input_tokens == 15
    assert parsed.cache_creation_input_tokens == 3
    assert parsed.cache_read_input_tokens == 10
    assert parsed.output_tokens == 12


def test_parse_codex_rollout_takes_last_cumulative_usage(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    old = tmp_path / ".codex" / "sessions" / "2026" / "06" / "22" / "rollout-old.jsonl"
    _write(old, '{"type":"session_meta","payload":{"cwd":"/elsewhere"}}\n')
    new = tmp_path / ".codex" / "sessions" / "2026" / "06" / "23" / "rollout-new.jsonl"
    _write(
        new,
        f"""
        {{"type":"session_meta","payload":{{"id":"codex-session","timestamp":"2026-06-23T12:01:00Z","cwd":"{cwd.resolve()}","model_provider":"openai"}}}}
        {{"type":"turn_context","payload":{{"model":"gpt-5.4"}}}}
        {{"type":"event_msg","payload":{{"type":"token_count","info":{{"total_token_usage":{{"input_tokens":10,"cached_input_tokens":2,"output_tokens":3,"reasoning_output_tokens":1,"total_tokens":13}}}}}}}}
        {{"type":"event_msg","payload":{{"type":"token_count","info":{{"total_token_usage":{{"input_tokens":50,"cached_input_tokens":12,"output_tokens":13,"reasoning_output_tokens":5,"total_tokens":63}}}}}}}}
        """,
    )
    start, end = _window()

    parsed = parse_session(
        "codex",
        cwd=cwd,
        session_id=None,
        pre_existing={old},
        window_start=start,
        window_end=end,
    )

    assert parsed.usage_status == "ok"
    assert parsed.provider == "openai"
    assert parsed.model == "gpt-5.4"
    assert parsed.session_id == "codex-session"
    assert parsed.input_tokens == 38
    assert parsed.cache_creation_input_tokens is None
    assert parsed.cache_read_input_tokens == 12
    assert parsed.output_tokens == 13
    assert (
        parsed.input_tokens
        + parsed.cache_read_input_tokens
        + parsed.output_tokens
        == 63
    )


def test_parse_codex_rollout_ambiguous_cwd_matches_are_unknown(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    sessions = tmp_path / ".codex" / "sessions" / "2026" / "06" / "23"
    old = sessions / "rollout-old.jsonl"
    first = sessions / "rollout-first.jsonl"
    second = sessions / "rollout-second.jsonl"
    _write(old, '{"type":"session_meta","payload":{"cwd":"/elsewhere"}}\n')
    for path, session_id in ((first, "first"), (second, "second")):
        _write(
            path,
            f"""
            {{"type":"session_meta","payload":{{"id":"{session_id}","cwd":"{cwd.resolve()}","model_provider":"openai"}}}}
            {{"type":"event_msg","payload":{{"type":"token_count","info":{{"total_token_usage":{{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1,"reasoning_output_tokens":0,"total_tokens":2}}}}}}}}
            """,
        )
    start, end = _window()

    parsed = parse_session(
        "codex",
        cwd=cwd,
        session_id=None,
        pre_existing={old},
        window_start=start,
        window_end=end,
    )

    assert parsed.usage_status == "unknown"
    assert parsed.provider == "openai"
    assert parsed.session_id is None


def test_parse_codex_rollout_ignores_matches_outside_launch_window(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    rollout = (
        tmp_path
        / ".codex"
        / "sessions"
        / "2026"
        / "06"
        / "23"
        / "rollout-stale.jsonl"
    )
    _write(
        rollout,
        f"""
        {{"type":"session_meta","payload":{{"id":"stale","timestamp":"2026-06-23T11:00:00Z","cwd":"{cwd.resolve()}","model_provider":"openai"}}}}
        {{"type":"event_msg","payload":{{"type":"token_count","info":{{"total_token_usage":{{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1,"reasoning_output_tokens":0,"total_tokens":2}}}}}}}}
        """,
    )
    start, end = _window()

    parsed = parse_session(
        "codex",
        cwd=cwd,
        session_id=None,
        pre_existing=set(),
        window_start=start,
        window_end=end,
    )

    assert parsed.usage_status == "unknown"
    assert parsed.provider == "openai"
    assert parsed.reason == f"codex rollout not found for cwd: {cwd.resolve()}"


def test_append_and_load_records_from_usage_section(tmp_path: Path) -> None:
    coga_os = tmp_path / "coga"
    blackboard = coga_os / "tasks" / "work" / "blackboard.md"
    _write(blackboard, "Notes before usage\n")
    record = UsageRecord(
        ts="2026-06-23T12:00:00Z",
        title="Work",
        slug="work",
        step="implement",
        agent="claude",
        cli="claude",
        provider="anthropic",
        model="claude-sonnet-4",
        session_id="abc",
        input_tokens=1,
        cache_creation_input_tokens=2,
        cache_read_input_tokens=3,
        output_tokens=4,
        usage_status="ok",
    )

    append_record(blackboard, record)
    text = blackboard.read_text()
    _write(blackboard, text + "\nThis prose is ignored.\n")

    assert load_records(coga_os) == [record]


def test_rollup_filters_and_groups_records() -> None:
    records = [
        UsageRecord(
            ts="2026-06-23T12:00:00Z",
            title="A",
            slug="a",
            step="implement",
            agent="claude",
            cli="claude",
            provider="anthropic",
            model="claude-sonnet-4",
            session_id="a",
            input_tokens=10,
            cache_creation_input_tokens=1,
            cache_read_input_tokens=2,
            output_tokens=3,
            usage_status="ok",
        ),
        UsageRecord(
            ts="2026-06-23T13:00:00Z",
            title="B",
            slug="b",
            step="peer-review",
            agent="codex",
            cli="codex",
            provider="openai",
            model="gpt-5.4",
            session_id="b",
            input_tokens=20,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=4,
            output_tokens=5,
            usage_status="ok",
        ),
        UsageRecord(
            ts="2026-06-24T12:00:00Z",
            title="A",
            slug="a",
            step="implement",
            agent="claude",
            cli="claude",
            provider="anthropic",
            model=None,
            session_id=None,
            input_tokens=None,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None,
            output_tokens=None,
            usage_status="unknown",
        ),
    ]

    result = rollup(records, by="model", until="2026-06-23")

    assert result.overall.sessions == 2
    assert result.overall.total_tokens == 45
    assert [row.key for row in result.groups] == ["claude-sonnet-4", "gpt-5.4"]


def test_usage_command_outputs_json(tmp_path: Path, monkeypatch) -> None:
    coga_os = tmp_path / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    blackboard = coga_os / "tasks" / "work" / "blackboard.md"
    _write(blackboard, "# Blackboard\n")
    append_record(
        blackboard,
        UsageRecord(
            ts="2026-06-23T12:00:00Z",
            title="Work",
            slug="work",
            step="implement",
            agent="claude",
            cli="claude",
            provider="anthropic",
            model="claude-sonnet-4",
            session_id="abc",
            input_tokens=1,
            cache_creation_input_tokens=2,
            cache_read_input_tokens=3,
            output_tokens=4,
            usage_status="ok",
        ),
    )
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["usage", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["by"] == "task"
    assert payload["overall"]["total_tokens"] == 10
    assert payload["groups"][0]["key"] == "work"
