"""Render `claude -p --output-format stream-json` events to human text.

Claude's `-p` text mode buffers its entire response and prints only on exit,
so a long agentic launch looks identical to a hang. The stream-json output
format emits one JSON object per line as work happens; we read those, pull
out the events a watcher actually wants to see (model init, tool calls,
final text, result summary, tool errors), and write a one-line summary per
event to stdout.

Unknown event shapes are passed through unchanged so we never silently drop
output when claude adds new event types.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import IO


@dataclass(frozen=True)
class RunSummary:
    """Token + cost + timing extracted from a stream-json `result` event.

    Only populated for stream-json runs — interactive launches inherit stdio
    so the parent has no way to attribute usage to the task.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    total_cost_usd: float | None = None
    num_turns: int | None = None
    duration_ms: int | None = None
    is_error: bool = False


def render_stream(stdin: IO[str], stdout: IO[str] | None = None) -> RunSummary | None:
    """Read newline-delimited JSON events from stdin, write summaries to stdout.

    Returns a `RunSummary` extracted from the final `result` event, or None
    if no result event was seen.
    """
    out = stdout if stdout is not None else sys.stdout
    summary: RunSummary | None = None
    for raw in stdin:
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            out.write(line + "\n")
            out.flush()
            continue
        if event.get("type") == "result":
            summary = _extract_run_summary(event)
        rendered = render_event(event)
        if rendered:
            out.write(rendered + "\n")
            out.flush()
    return summary


def _extract_run_summary(event: dict) -> RunSummary:
    usage = event.get("usage") or {}
    return RunSummary(
        input_tokens=_coerce_int(usage.get("input_tokens")),
        output_tokens=_coerce_int(usage.get("output_tokens")),
        cache_creation_input_tokens=_coerce_int(usage.get("cache_creation_input_tokens")),
        cache_read_input_tokens=_coerce_int(usage.get("cache_read_input_tokens")),
        total_cost_usd=_coerce_float_or_none(event.get("total_cost_usd")),
        num_turns=_coerce_int_or_none(event.get("num_turns")),
        duration_ms=_coerce_int_or_none(event.get("duration_ms")),
        is_error=bool(event.get("is_error") or event.get("subtype") == "error"),
    )


def _coerce_int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def _coerce_int_or_none(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _coerce_float_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def render_event(event: dict) -> str | None:
    """Map one parsed JSON event to a single line, or None to suppress."""
    etype = event.get("type")
    if etype == "system":
        return _render_system(event)
    if etype == "stream_event":
        return _render_stream_event(event.get("event") or {})
    if etype == "assistant":
        return _render_assistant(event.get("message") or {})
    if etype == "user":
        return _render_user(event.get("message") or {})
    if etype == "result":
        return _render_result(event)
    return None


def _render_system(event: dict) -> str | None:
    if event.get("subtype") == "init":
        model = event.get("model") or "?"
        sid = event.get("session_id") or ""
        return f"agent: init model={model} session={sid[:8]}"
    return None


def _render_stream_event(event: dict) -> str | None:
    # Tool_use inputs stream in as input_json_delta events, so they're
    # empty at content_block_start. Render tool calls from the `assistant`
    # event instead, which carries the fully-built block.
    return None


def _summarize_tool_input(tool: str, raw: dict) -> str:
    if not isinstance(raw, dict):
        return ""
    if tool == "Bash":
        cmd = raw.get("command") or ""
        first = cmd.splitlines()[0] if cmd else ""
        return _truncate(first, 80)
    if tool in ("Read", "Edit", "Write", "NotebookEdit"):
        return raw.get("file_path") or raw.get("path") or ""
    if tool == "Grep":
        return _truncate(str(raw.get("pattern") or ""), 60)
    if tool == "Glob":
        return str(raw.get("pattern") or "")
    if tool == "Task":
        return _truncate(str(raw.get("description") or raw.get("subagent_type") or ""), 60)
    if tool == "WebFetch":
        return _truncate(str(raw.get("url") or ""), 80)
    return ""


def _render_assistant(message: dict) -> str | None:
    blocks = message.get("content") or []
    lines: list[str] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        btype = b.get("type")
        if btype == "text":
            t = (b.get("text") or "").strip()
            if t:
                lines.append(t)
        elif btype == "tool_use":
            name = b.get("name") or "?"
            summary = _summarize_tool_input(name, b.get("input") or {})
            if summary:
                lines.append(f"  → {name}({summary})")
            else:
                lines.append(f"  → {name}")
    if not lines:
        return None
    return "\n".join(lines)


def _render_user(message: dict) -> str | None:
    blocks = message.get("content") or []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "tool_result" and b.get("is_error"):
            content = b.get("content") or ""
            if isinstance(content, list):
                content = " ".join(
                    str(c.get("text") or "") for c in content if isinstance(c, dict)
                )
            return f"  ⚠ tool error: {_truncate(str(content), 200)}"
    return None


def _render_result(event: dict) -> str:
    if event.get("is_error") or event.get("subtype") == "error":
        msg = event.get("result") or event.get("error") or "unknown"
        return f"agent: ✗ error — {_truncate(str(msg), 200)}"
    parts = ["agent: ✓ done"]
    duration = event.get("duration_ms")
    if isinstance(duration, (int, float)):
        parts.append(f"{duration / 1000:.1f}s")
    cost = event.get("total_cost_usd")
    if isinstance(cost, (int, float)):
        parts.append(f"${cost:.4f}")
    turns = event.get("num_turns")
    if isinstance(turns, int):
        parts.append(f"{turns} turn{'s' if turns != 1 else ''}")
    return " | ".join(parts)


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def format_run_summary_log(summary: RunSummary) -> str:
    """Format a `RunSummary` as a one-line `log.md` message.

    Always starts with `tokens: ` so the line is greppable. Token counts
    that are zero are still written (so summing by grep works); cost,
    turns, and duration are only included when reported by the agent.
    """
    parts = [
        f"in={summary.input_tokens}",
        f"out={summary.output_tokens}",
        f"cache_read={summary.cache_read_input_tokens}",
        f"cache_create={summary.cache_creation_input_tokens}",
    ]
    if summary.total_cost_usd is not None:
        parts.append(f"cost=${summary.total_cost_usd:.4f}")
    if summary.num_turns is not None:
        parts.append(f"turns={summary.num_turns}")
    if summary.duration_ms is not None:
        parts.append(f"duration={summary.duration_ms / 1000:.1f}s")
    if summary.is_error:
        parts.append("error=true")
    return "tokens: " + " ".join(parts)


def is_stream_json_command(cmd: list[str]) -> bool:
    """True if `cmd` requests claude's stream-json output format."""
    for i, arg in enumerate(cmd):
        if arg == "--output-format" and i + 1 < len(cmd) and cmd[i + 1] == "stream-json":
            return True
        if arg.startswith("--output-format=") and arg.split("=", 1)[1] == "stream-json":
            return True
    return False
