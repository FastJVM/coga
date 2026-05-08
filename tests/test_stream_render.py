from __future__ import annotations

import io
import json

from relay.stream_render import (
    is_stream_json_command,
    render_event,
    render_stream,
)


def test_is_stream_json_command_separate_arg() -> None:
    assert is_stream_json_command(
        ["claude", "-p", "--output-format", "stream-json", "prompt"]
    )


def test_is_stream_json_command_equals_form() -> None:
    assert is_stream_json_command(
        ["claude", "-p", "--output-format=stream-json", "prompt"]
    )


def test_is_stream_json_command_text_format_false() -> None:
    assert not is_stream_json_command(
        ["claude", "-p", "--output-format", "text", "prompt"]
    )


def test_is_stream_json_command_no_format_false() -> None:
    assert not is_stream_json_command(["claude", "-p", "prompt"])


def test_render_system_init() -> None:
    out = render_event(
        {
            "type": "system",
            "subtype": "init",
            "model": "claude-opus-4-7",
            "session_id": "abcd1234efgh",
        }
    )
    assert out == "agent: init model=claude-opus-4-7 session=abcd1234"


def test_render_system_status_suppressed() -> None:
    out = render_event(
        {"type": "system", "subtype": "status", "status": "requesting"}
    )
    assert out is None


def test_render_stream_event_tool_use_suppressed() -> None:
    # Tool inputs arrive as input_json_delta events; render from
    # the assistant event instead.
    out = render_event(
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "content_block": {
                    "type": "tool_use",
                    "name": "Bash",
                    "input": {},
                },
            },
        }
    )
    assert out is None


def test_render_assistant_text_and_tool_use() -> None:
    out = render_event(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "hello world"},
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "ls -la /tmp\nsecond line"},
                    },
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/tmp/x.py"},
                    },
                    {
                        "type": "tool_use",
                        "name": "Mystery",
                        "input": {"foo": "bar"},
                    },
                ]
            },
        }
    )
    assert out == "\n".join([
        "hello world",
        "  → Bash(ls -la /tmp)",
        "  → Read(/tmp/x.py)",
        "  → Mystery",
    ])


def test_render_user_tool_error() -> None:
    out = render_event(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "is_error": True,
                        "content": "permission denied",
                    }
                ]
            },
        }
    )
    assert out == "  ⚠ tool error: permission denied"


def test_render_user_tool_success_suppressed() -> None:
    out = render_event(
        {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "is_error": False, "content": "ok"}
                ]
            },
        }
    )
    assert out is None


def test_render_result_success() -> None:
    out = render_event(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "duration_ms": 1500,
            "total_cost_usd": 0.0123,
            "num_turns": 3,
        }
    )
    assert out == "agent: ✓ done | 1.5s | $0.0123 | 3 turns"


def test_render_result_error() -> None:
    out = render_event(
        {
            "type": "result",
            "subtype": "error",
            "is_error": True,
            "result": "rate limited",
        }
    )
    assert out.startswith("agent: ✗ error")
    assert "rate limited" in out


def test_render_unknown_event_suppressed() -> None:
    assert render_event({"type": "mystery"}) is None


def test_render_stream_passes_through_invalid_json() -> None:
    src = io.StringIO("not json at all\n")
    sink = io.StringIO()
    render_stream(src, sink)
    assert sink.getvalue() == "not json at all\n"


def test_render_stream_skips_blank_lines() -> None:
    src = io.StringIO("\n\n")
    sink = io.StringIO()
    render_stream(src, sink)
    assert sink.getvalue() == ""


def test_render_stream_full_session() -> None:
    events = [
        {"type": "system", "subtype": "init", "model": "claude-opus-4-7", "session_id": "12345678abcd"},
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "content_block": {"type": "tool_use", "name": "Bash", "input": {}},
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "echo hi"}},
                    {"type": "text", "text": "done"},
                ]
            },
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "duration_ms": 1000,
            "total_cost_usd": 0.01,
            "num_turns": 1,
        },
    ]
    src = io.StringIO("\n".join(json.dumps(e) for e in events) + "\n")
    sink = io.StringIO()
    render_stream(src, sink)
    lines = sink.getvalue().strip().splitlines()
    assert lines == [
        "agent: init model=claude-opus-4-7 session=12345678",
        "  → Bash(echo hi)",
        "done",
        "agent: ✓ done | 1.0s | $0.0100 | 1 turn",
    ]
