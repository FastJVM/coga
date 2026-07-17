from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.usage import (
    ParsedUsage,
    UsageRecord,
    append_record,
    capture_session,
    load_records,
    parse_session,
    rollup,
)


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


def test_parse_claude_activity_excludes_injected_text_and_redacts(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    session_id = "session-activity"
    cwd_hash = str(cwd.resolve()).replace("/", "-").replace(".", "-")
    transcript = tmp_path / ".claude" / "projects" / cwd_hash / f"{session_id}.jsonl"
    long_outcome = "Finished " + "x" * 510 + " secret-value"
    _write(
        transcript,
        f"""
        {{"type":"user","timestamp":"2026-06-23T12:00:01Z","message":{{"role":"user","content":"# composed prompt"}}}}
        {{"type":"user","timestamp":"2026-06-23T12:00:02Z","message":{{"role":"user","content":"Begin"}}}}
        {{"type":"user","timestamp":"2026-06-23T12:01:00Z","message":{{"role":"user","content":"Please use secret-value\\ncarefully"}}}}
        {{"type":"user","timestamp":"2026-06-23T12:01:30Z","message":{{"role":"user","content":[{{"type":"tool_result","content":"not human"}}]}}}}
        {{"type":"user","timestamp":"2026-06-23T12:02:00Z","message":{{"role":"user","content":[{{"type":"text","text":"Then summarize it"}}]}}}}
        {{"type":"assistant","timestamp":"2026-06-23T12:03:00Z","message":{{"role":"assistant","model":"claude-sonnet-4","content":[{{"type":"text","text":"Working"}},{{"type":"tool_use","name":"Read"}}],"usage":{{"input_tokens":2,"output_tokens":3}}}}}}
        {{"type":"assistant","timestamp":"2026-06-23T12:04:00Z","message":{{"role":"assistant","model":"claude-sonnet-4","content":[{{"type":"text","text":{json.dumps(long_outcome)}}}],"usage":{{"input_tokens":1,"output_tokens":2}}}}}}
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
        excluded_user_texts=("# composed prompt", "Begin"),
        secret_values=("secret-value",),
    )

    assert parsed.content_status == "ok"
    assert parsed.human_turns == 2
    assert parsed.agent_turns == 2
    assert parsed.request == "Please use [REDACTED] carefully Then summarize it"
    assert parsed.outcome is not None
    assert len(parsed.outcome) == 500
    assert parsed.outcome.endswith("…")
    assert "secret-value" not in parsed.outcome

    unsafe = parse_session(
        "claude",
        cwd=cwd,
        session_id=session_id,
        pre_existing=None,
        window_start=start,
        window_end=end,
        excluded_user_texts=("# composed prompt", "Begin"),
        secret_values=None,
    )
    assert unsafe.human_turns == 2
    assert unsafe.agent_turns == 2
    assert unsafe.request is None
    assert unsafe.outcome is None
    assert unsafe.content_status == "unknown"


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


def test_parse_codex_activity_uses_messages_after_turn_context_only(
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
        / "rollout-activity.jsonl"
    )
    _write(
        rollout,
        f"""
        {{"type":"session_meta","timestamp":"2026-06-23T12:00:00Z","payload":{{"id":"codex-activity","timestamp":"2026-06-23T12:00:00Z","cwd":"{cwd.resolve()}","model_provider":"openai"}}}}
        {{"type":"response_item","timestamp":"2026-06-23T12:00:01Z","payload":{{"type":"message","role":"user","content":[{{"type":"input_text","text":"injected environment"}}]}}}}
        {{"type":"turn_context","timestamp":"2026-06-23T12:00:02Z","payload":{{"model":"gpt-5.4"}}}}
        {{"type":"response_item","timestamp":"2026-06-23T12:00:03Z","payload":{{"type":"message","role":"user","content":[{{"type":"input_text","text":"# composed prompt"}}]}}}}
        {{"type":"response_item","timestamp":"2026-06-23T12:01:00Z","payload":{{"type":"message","role":"user","content":[{{"type":"input_text","text":"Inspect secret-value"}}]}}}}
        {{"type":"response_item","timestamp":"2026-06-23T12:02:00Z","payload":{{"type":"custom_tool_call_output","output":"not agent text"}}}}
        {{"type":"response_item","timestamp":"2026-06-23T12:03:00Z","payload":{{"type":"message","role":"assistant","content":[{{"type":"output_text","text":"First answer"}}]}}}}
        {{"type":"turn_context","timestamp":"2026-06-23T12:04:00Z","payload":{{"model":"gpt-5.4"}}}}
        {{"type":"response_item","timestamp":"2026-06-23T12:04:01Z","payload":{{"type":"message","role":"user","content":[{{"type":"input_text","text":"Finish"}}]}}}}
        {{"type":"response_item","timestamp":"2026-06-23T12:05:00Z","payload":{{"type":"message","role":"assistant","content":[{{"type":"output_text","text":"Final secret-value outcome"}}]}}}}
        {{"type":"event_msg","timestamp":"2026-06-23T12:05:01Z","payload":{{"type":"token_count","info":{{"total_token_usage":{{"input_tokens":10,"cached_input_tokens":2,"output_tokens":3}}}}}}}}
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
        excluded_user_texts=("# composed prompt",),
        secret_values=("secret-value",),
    )

    assert parsed.content_status == "ok"
    assert parsed.human_turns == 2
    assert parsed.agent_turns == 2
    assert parsed.request == "Inspect [REDACTED] Finish"
    assert parsed.outcome == "Final [REDACTED] outcome"


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


def test_append_and_load_records_from_log(tmp_path: Path) -> None:
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
    cfg = load_config(coga_os)
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

    append_record(cfg, record)
    log = coga_os / "log.md"
    with log.open("a") as f:
        f.write("2026-06-23 12:01 [work] [human:marc] bumped to step 2\n")

    # The record rides one standard tagged log line, JSON as the message.
    first = log.read_text().splitlines()[0]
    assert "[work] [system] " in first
    assert first.endswith(record.to_json())
    # Non-record log lines are skipped, not errors.
    assert load_records(cfg) == [record]


def test_capture_appends_schema_two_activity_record(
    tmp_path: Path, monkeypatch
) -> None:
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
    monkeypatch.setattr(
        "coga.usage.parse_session",
        lambda *args, **kwargs: ParsedUsage(
            provider="anthropic",
            model="claude-sonnet-4",
            session_id="session-2",
            input_tokens=1,
            cache_creation_input_tokens=2,
            cache_read_input_tokens=3,
            output_tokens=4,
            usage_status="ok",
            human_turns=2,
            agent_turns=3,
            request="Do the work",
            outcome="Work completed",
            content_status="ok",
        ),
    )
    start, end = _window()

    capture_session(
        cfg=load_config(coga_os),
        title="Work",
        slug="work",
        step="implement",
        agent="claude",
        cli="claude",
        cwd=tmp_path,
        session_id="session-2",
        pre_existing=None,
        window_start=start,
        window_end=end,
        outcome_status="completed",
    )

    record = load_records(load_config(coga_os))[0]
    assert record.schema == 2
    assert record.ts == "2026-06-23T13:00:00Z"
    assert record.started_at == "2026-06-23T12:00:00Z"
    assert record.ended_at == "2026-06-23T13:00:00Z"
    assert record.elapsed_seconds == 3600.0
    assert record.human_turns == 2
    assert record.agent_turns == 3
    assert record.request == "Do the work"
    assert record.outcome == "Work completed"
    assert record.content_status == "ok"
    assert record.outcome_status == "completed"


def test_load_schema_one_record_with_activity_fields_absent(tmp_path: Path) -> None:
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
    old_record = {
        "schema": 1,
        "ts": "2026-06-23T12:00:00Z",
        "title": "Old work",
        "slug": "old-work",
        "step": "implement",
        "agent": "claude",
        "cli": "claude",
        "provider": "anthropic",
        "model": "claude-sonnet-4",
        "session_id": "old-session",
        "input_tokens": 1,
        "cache_creation_input_tokens": 2,
        "cache_read_input_tokens": 3,
        "output_tokens": 4,
        "usage_status": "ok",
    }
    _write(
        coga_os / "log.md",
        "2026-06-23 12:00 [old-work] [system] "
        + json.dumps(old_record, separators=(",", ":"))
        + "\n",
    )

    records = load_records(load_config(coga_os))

    assert len(records) == 1
    record = records[0]
    assert record.schema == 1
    assert record.started_at is None
    assert record.human_turns is None
    assert record.content_status is None
    assert record.outcome_status is None
    assert rollup(records).overall.total_tokens == 10


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
    append_record(
        load_config(coga_os),
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
