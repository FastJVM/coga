"""Usage records parsed from agent transcripts and stored in the global log."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Literal

from coga.config import Config
from coga.logfile import append_log
from coga.paths import log_path


USAGE_SCHEMA = 2
MAX_ACTIVITY_CHARS = 500
TRUNCATION_MARKER = "…"

UsageStatus = Literal["ok", "unknown"]
ContentStatus = Literal["ok", "unknown"]
OutcomeStatus = Literal[
    "completed", "failed", "timed_out", "interrupted", "unknown"
]
ParserKey = Literal["claude", "codex"]

# A usage record rides the standard `coga/log.md` line shape —
# `YYYY-MM-DD HH:MM [<task-ref>] [<actor>] <message>` — with the record's
# JSON object as the message.
_LOG_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} \[[^\]]*\] \[[^\]]*\] (\{.*)$"
)


@dataclass(frozen=True)
class ParsedUsage:
    provider: str
    model: str | None
    session_id: str | None
    input_tokens: int | None
    cache_creation_input_tokens: int | None
    cache_read_input_tokens: int | None
    output_tokens: int | None
    usage_status: UsageStatus
    human_turns: int | None = None
    agent_turns: int | None = None
    request: str | None = None
    outcome: str | None = None
    content_status: ContentStatus = "unknown"
    reason: str | None = None


@dataclass(frozen=True)
class _ParsedActivity:
    human_turns: int | None
    agent_turns: int | None
    request: str | None
    outcome: str | None
    content_status: ContentStatus


@dataclass(frozen=True)
class UsageRecord:
    ts: str
    title: str
    slug: str
    step: str | None
    agent: str
    cli: str
    provider: str
    model: str | None
    session_id: str | None
    input_tokens: int | None
    cache_creation_input_tokens: int | None
    cache_read_input_tokens: int | None
    output_tokens: int | None
    usage_status: UsageStatus
    started_at: str | None = None
    ended_at: str | None = None
    elapsed_seconds: float | None = None
    human_turns: int | None = None
    agent_turns: int | None = None
    request: str | None = None
    outcome: str | None = None
    content_status: ContentStatus | None = None
    outcome_status: OutcomeStatus | None = None
    schema: int = USAGE_SCHEMA

    def to_json(self) -> str:
        return json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    @classmethod
    def from_json(cls, line: str) -> "UsageRecord":
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("usage record is not JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("usage record must be an object")
        schema = data.get("schema")
        if schema not in {1, USAGE_SCHEMA}:
            raise ValueError("unsupported usage schema")
        try:
            return cls(
                ts=_require_str(data, "ts"),
                title=_require_str(data, "title"),
                slug=_require_str(data, "slug"),
                step=_optional_str(data, "step"),
                agent=_require_str(data, "agent"),
                cli=_require_str(data, "cli"),
                provider=_require_str(data, "provider"),
                model=_optional_str(data, "model"),
                session_id=_optional_str(data, "session_id"),
                input_tokens=_optional_int(data, "input_tokens"),
                cache_creation_input_tokens=_optional_int(
                    data, "cache_creation_input_tokens"
                ),
                cache_read_input_tokens=_optional_int(
                    data, "cache_read_input_tokens"
                ),
                output_tokens=_optional_int(data, "output_tokens"),
                usage_status=_usage_status(data),
                started_at=_optional_str_value(data.get("started_at")),
                ended_at=_optional_str_value(data.get("ended_at")),
                elapsed_seconds=_optional_number_value(
                    data.get("elapsed_seconds")
                ),
                human_turns=_optional_int_value(data.get("human_turns")),
                agent_turns=_optional_int_value(data.get("agent_turns")),
                request=_optional_str_value(data.get("request")),
                outcome=_optional_str_value(data.get("outcome")),
                content_status=_content_status(data.get("content_status")),
                outcome_status=_outcome_status(data.get("outcome_status")),
                schema=schema,
            )
        except KeyError as exc:
            raise ValueError(f"missing usage field: {exc.args[0]}") from exc


@dataclass(frozen=True)
class RollupRow:
    key: str
    sessions: int
    unknown_sessions: int
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
            + self.output_tokens
        )

    def to_dict(self) -> dict[str, int | str]:
        data = asdict(self)
        data["total_tokens"] = self.total_tokens
        return data


@dataclass(frozen=True)
class Rollup:
    by: str | None
    overall: RollupRow
    groups: list[RollupRow]

    def to_dict(self) -> dict:
        return {
            "by": self.by,
            "overall": self.overall.to_dict(),
            "groups": [row.to_dict() for row in self.groups],
        }


def parser_key_for_cli(cli: str) -> ParserKey | None:
    name = Path(cli).name
    if name == "claude":
        return "claude"
    if name == "codex":
        return "codex"
    return None


def snapshot_session_files(provider: ParserKey | None) -> set[Path]:
    if provider != "codex":
        return set()
    return set(_codex_rollout_paths())


def parse_session(
    provider: ParserKey | None,
    *,
    cwd: Path,
    session_id: str | None,
    pre_existing: set[Path] | None,
    window_start: datetime,
    window_end: datetime,
    excluded_user_texts: tuple[str, ...] = (),
    secret_values: tuple[str, ...] | None = (),
) -> ParsedUsage:
    if provider == "claude":
        return _parse_claude_session(
            cwd=cwd,
            session_id=session_id,
            window_start=window_start,
            window_end=window_end,
            excluded_user_texts=excluded_user_texts,
            secret_values=secret_values,
        )
    if provider == "codex":
        return _parse_codex_session(
            cwd=cwd,
            pre_existing=pre_existing or set(),
            window_start=window_start,
            window_end=window_end,
            excluded_user_texts=excluded_user_texts,
            secret_values=secret_values,
        )
    return ParsedUsage(
        provider="unknown",
        model=None,
        session_id=session_id,
        input_tokens=None,
        cache_creation_input_tokens=None,
        cache_read_input_tokens=None,
        output_tokens=None,
        usage_status="unknown",
        reason="unsupported agent cli",
    )


def capture_session(
    *,
    cfg: Config,
    title: str,
    slug: str,
    step: str | None,
    agent: str,
    cli: str,
    cwd: Path,
    session_id: str | None,
    pre_existing: set[Path] | None,
    window_start: datetime,
    window_end: datetime,
    excluded_user_texts: tuple[str, ...] = (),
    secret_values: tuple[str, ...] | None = (),
    outcome_status: OutcomeStatus = "unknown",
) -> None:
    provider_key = parser_key_for_cli(cli)
    try:
        parsed = parse_session(
            provider_key,
            cwd=cwd,
            session_id=session_id,
            pre_existing=pre_existing,
            window_start=window_start,
            window_end=window_end,
            excluded_user_texts=excluded_user_texts,
            secret_values=secret_values,
        )
    except Exception as exc:  # pragma: no cover - defensive launch guard
        print(f"coga usage: failed to parse session usage: {exc}", file=sys.stderr)
        parsed = ParsedUsage(
            provider=provider_key or "unknown",
            model=None,
            session_id=session_id,
            input_tokens=None,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None,
            output_tokens=None,
            usage_status="unknown",
            reason=str(exc),
        )
    if parsed.usage_status == "unknown" and parsed.reason:
        print(f"coga usage: {parsed.reason}", file=sys.stderr)

    record = UsageRecord(
        ts=_format_ts(window_end),
        title=title,
        slug=slug,
        step=step,
        agent=agent,
        cli=cli,
        provider=parsed.provider,
        model=parsed.model,
        session_id=parsed.session_id,
        input_tokens=parsed.input_tokens,
        cache_creation_input_tokens=parsed.cache_creation_input_tokens,
        cache_read_input_tokens=parsed.cache_read_input_tokens,
        output_tokens=parsed.output_tokens,
        usage_status=parsed.usage_status,
        started_at=_format_ts(window_start),
        ended_at=_format_ts(window_end),
        elapsed_seconds=max(
            0.0,
            (_ensure_utc(window_end) - _ensure_utc(window_start)).total_seconds(),
        ),
        human_turns=parsed.human_turns,
        agent_turns=parsed.agent_turns,
        request=parsed.request,
        outcome=parsed.outcome,
        content_status=parsed.content_status,
        outcome_status=outcome_status,
    )
    try:
        append_record(cfg, record)
    except Exception as exc:  # pragma: no cover - defensive launch guard
        print(f"coga usage: failed to append usage record: {exc}", file=sys.stderr)


def append_record(cfg: Config, record: UsageRecord) -> None:
    """Append one usage record to the repo-global `coga/log.md`.

    The record's JSON is the log line's message, behind the standard
    timestamp + task-ref + actor tagging, so the one line serves both
    `coga show` history and `coga usage` rollups.
    """
    append_log(cfg, record.slug, "system", record.to_json())


def load_records(cfg: Config) -> list[UsageRecord]:
    """Parse usage records back out of the repo-global `coga/log.md`.

    A usage line is an ordinary tagged log line whose message is the record's
    JSON object; every other line (state transitions, FYIs) fails the record
    parse and is skipped.
    """
    path = log_path(cfg)
    if not path.is_file():
        return []
    try:
        text = path.read_text()
    except OSError:
        return []
    records: list[UsageRecord] = []
    for line in text.splitlines():
        match = _LOG_LINE_RE.match(line)
        if not match:
            continue
        try:
            records.append(UsageRecord.from_json(match.group(1)))
        except ValueError:
            continue
    return records


def rollup(
    records: list[UsageRecord],
    *,
    by: str | None = "task",
    since: str | datetime | None = None,
    until: str | datetime | None = None,
    task: str | None = None,
) -> Rollup:
    if by not in {None, "task", "model", "agent", "step"}:
        raise ValueError("--by must be one of: task, model, agent, step")
    since_dt = _parse_filter_ts(since, is_until=False)
    until_dt = _parse_filter_ts(until, is_until=True)
    filtered = [
        record
        for record in records
        if _record_matches(record, since=since_dt, until=until_dt, task=task)
    ]
    overall = _build_row("overall", filtered)
    groups: list[RollupRow] = []
    if by is not None:
        grouped: dict[str, list[UsageRecord]] = {}
        for record in filtered:
            grouped.setdefault(_group_key(record, by), []).append(record)
        groups = [_build_row(key, grouped[key]) for key in sorted(grouped)]
    return Rollup(by=by, overall=overall, groups=groups)


def _parse_claude_session(
    *,
    cwd: Path,
    session_id: str | None,
    window_start: datetime,
    window_end: datetime,
    excluded_user_texts: tuple[str, ...],
    secret_values: tuple[str, ...] | None,
) -> ParsedUsage:
    if not session_id:
        return _unknown(
            "anthropic",
            session_id=session_id,
            reason="missing claude session id",
        )
    path = _claude_transcript_path(cwd, session_id)
    if not path.is_file():
        return _unknown(
            "anthropic",
            session_id=session_id,
            reason=f"claude transcript not found: {path}",
        )

    model: str | None = None
    input_tokens = 0
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0
    output_tokens = 0
    matched = False
    human_texts: list[str] = []
    agent_texts: list[str] = []
    human_turns = 0
    agent_turns = 0
    content_safe = True
    excluded_remaining = list(excluded_user_texts)
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        return _unknown("anthropic", session_id=session_id, reason=str(exc))
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            content_safe = False
            continue
        line_ts = _parse_ts(obj.get("timestamp"))
        if line_ts is not None and not _inside_window(
            line_ts, window_start=window_start, window_end=window_end
        ):
            continue
        kind = obj.get("type")
        message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        if kind == "assistant":
            usage = message.get("usage") or obj.get("usage") or {}
            if isinstance(usage, dict):
                matched = True
                model = _first_str(message.get("model"), obj.get("model")) or model
                input_tokens += _int_value(usage.get("input_tokens"))
                cache_creation_input_tokens += _int_value(
                    usage.get("cache_creation_input_tokens")
                )
                cache_read_input_tokens += _int_value(
                    usage.get("cache_read_input_tokens")
                )
                output_tokens += _int_value(usage.get("output_tokens"))

        if line_ts is None:
            if kind in {"user", "assistant"}:
                content_safe = False
            continue
        if obj.get("isMeta") is True or obj.get("isSidechain") is True:
            continue
        if kind not in {"user", "assistant"}:
            continue
        parts, parts_safe = _message_text_parts(message.get("content"))
        content_safe = content_safe and parts_safe
        if kind == "user":
            parts = _without_excluded_texts(parts, excluded_remaining)
            if parts:
                human_turns += 1
                human_texts.extend(parts)
        elif parts:
            agent_turns += 1
            agent_texts.extend(parts)

    activity = _finalize_activity(
        human_turns=human_turns,
        agent_turns=agent_turns,
        human_texts=human_texts,
        agent_texts=agent_texts,
        secret_values=secret_values,
        content_safe=content_safe,
    )

    if not matched:
        return _unknown(
            "anthropic",
            session_id=session_id,
            reason=f"claude transcript had no assistant usage: {path}",
            activity=activity,
        )
    return ParsedUsage(
        provider="anthropic",
        model=model,
        session_id=session_id,
        input_tokens=input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        output_tokens=output_tokens,
        usage_status="ok",
        human_turns=activity.human_turns,
        agent_turns=activity.agent_turns,
        request=activity.request,
        outcome=activity.outcome,
        content_status=activity.content_status,
    )


def _parse_codex_session(
    *,
    cwd: Path,
    pre_existing: set[Path],
    window_start: datetime,
    window_end: datetime,
    excluded_user_texts: tuple[str, ...],
    secret_values: tuple[str, ...] | None,
) -> ParsedUsage:
    candidates: list[Path] = []
    cwd_str = str(cwd.resolve())
    for path in set(_codex_rollout_paths()) - pre_existing:
        meta = _read_codex_session_meta(path)
        if meta is None:
            continue
        if meta.get("cwd") != cwd_str:
            continue
        started_at = _parse_ts(meta.get("timestamp"))
        if started_at is not None and not _inside_window(
            started_at, window_start=window_start, window_end=window_end
        ):
            continue
        candidates.append(path)
    if not candidates:
        return _unknown("openai", reason=f"codex rollout not found for cwd: {cwd_str}")
    if len(candidates) > 1:
        return _unknown(
            "openai",
            reason=(
                "multiple codex rollouts matched cwd: "
                + ", ".join(str(path) for path in sorted(candidates))
            ),
        )
    return _parse_codex_rollout(
        candidates[0],
        window_start=window_start,
        window_end=window_end,
        excluded_user_texts=excluded_user_texts,
        secret_values=secret_values,
    )


def _parse_codex_rollout(
    path: Path,
    *,
    window_start: datetime,
    window_end: datetime,
    excluded_user_texts: tuple[str, ...],
    secret_values: tuple[str, ...] | None,
) -> ParsedUsage:
    provider = "openai"
    session_id: str | None = None
    model: str | None = None
    last_usage: dict | None = None
    human_texts: list[str] = []
    agent_texts: list[str] = []
    human_turns = 0
    agent_turns = 0
    content_safe = True
    seen_turn_context = False
    excluded_remaining = list(excluded_user_texts)
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        return _unknown(provider, reason=str(exc))

    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            content_safe = False
            continue
        kind = obj.get("type")
        payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
        if kind == "session_meta":
            provider = _first_str(payload.get("model_provider"), provider) or provider
            session_id = _first_str(payload.get("id"), session_id)
        elif kind == "turn_context":
            model = _first_str(payload.get("model"), model) or model
            seen_turn_context = True
        elif kind == "event_msg":
            event = payload
            if not event:
                event = obj.get("msg") if isinstance(obj.get("msg"), dict) else {}
            if event.get("type") != "token_count":
                continue
            info = event.get("info") if isinstance(event.get("info"), dict) else {}
            total = info.get("total_token_usage")
            if isinstance(total, dict):
                last_usage = total
        elif kind == "response_item" and seen_turn_context:
            line_ts = _parse_ts(obj.get("timestamp"))
            if line_ts is None:
                content_safe = False
                continue
            if not _inside_window(
                line_ts, window_start=window_start, window_end=window_end
            ):
                continue
            if payload.get("type") != "message":
                continue
            role = payload.get("role")
            if role not in {"user", "assistant"}:
                continue
            parts, parts_safe = _codex_message_text_parts(
                payload.get("content"), role=role
            )
            content_safe = content_safe and parts_safe
            if role == "user":
                parts = _without_excluded_texts(parts, excluded_remaining)
                if parts:
                    human_turns += 1
                    human_texts.extend(parts)
            elif parts:
                agent_turns += 1
                agent_texts.extend(parts)

    activity = _finalize_activity(
        human_turns=human_turns,
        agent_turns=agent_turns,
        human_texts=human_texts,
        agent_texts=agent_texts,
        secret_values=secret_values,
        content_safe=content_safe,
    )

    if last_usage is None:
        return _unknown(
            provider,
            session_id=session_id,
            reason=f"codex rollout had no token_count event: {path}",
            activity=activity,
        )
    input_tokens = _int_value(last_usage.get("input_tokens"))
    cache_read_input_tokens = _int_value(last_usage.get("cached_input_tokens"))
    output_tokens = _int_value(last_usage.get("output_tokens"))
    return ParsedUsage(
        provider=provider,
        model=model,
        session_id=session_id,
        input_tokens=max(0, input_tokens - cache_read_input_tokens),
        cache_creation_input_tokens=None,
        cache_read_input_tokens=cache_read_input_tokens,
        output_tokens=output_tokens,
        usage_status="ok",
        human_turns=activity.human_turns,
        agent_turns=activity.agent_turns,
        request=activity.request,
        outcome=activity.outcome,
        content_status=activity.content_status,
    )


def _claude_transcript_path(cwd: Path, session_id: str) -> Path:
    cwd_hash = str(cwd.resolve()).replace("/", "-").replace(".", "-")
    return Path.home() / ".claude" / "projects" / cwd_hash / f"{session_id}.jsonl"


def _codex_rollout_paths() -> list[Path]:
    return list((Path.home() / ".codex" / "sessions").glob("**/rollout-*.jsonl"))


def _read_codex_session_meta(path: Path) -> dict[str, str] | None:
    try:
        with path.open() as fh:
            for line in fh:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if obj.get("type") != "session_meta":
                    return None
                payload = obj.get("payload")
                if not isinstance(payload, dict):
                    return None
                return {
                    "id": str(payload.get("id") or ""),
                    "cwd": str(payload.get("cwd") or ""),
                    "model_provider": str(payload.get("model_provider") or ""),
                    "timestamp": str(
                        payload.get("timestamp") or obj.get("timestamp") or ""
                    ),
                }
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _message_text_parts(content: object) -> tuple[list[str], bool]:
    """Return explicit Claude message text, ignoring tool payload blocks."""
    if isinstance(content, str):
        return ([content] if content else []), True
    if content is None:
        return [], True
    if not isinstance(content, list):
        return [], False
    texts: list[str] = []
    safe = True
    for block in content:
        if not isinstance(block, dict):
            safe = False
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if not isinstance(text, str):
            safe = False
            continue
        if text:
            texts.append(text)
    return texts, safe


def _codex_message_text_parts(
    content: object, *, role: str
) -> tuple[list[str], bool]:
    """Return explicit Codex message text, rejecting non-message payloads."""
    if not isinstance(content, list):
        return [], False
    expected_type = "input_text" if role == "user" else "output_text"
    texts: list[str] = []
    safe = True
    for block in content:
        if not isinstance(block, dict):
            safe = False
            continue
        if block.get("type") != expected_type:
            continue
        text = block.get("text")
        if not isinstance(text, str):
            safe = False
            continue
        if text:
            texts.append(text)
    return texts, safe


def _without_excluded_texts(
    parts: list[str], excluded_remaining: list[str]
) -> list[str]:
    """Remove each launcher-injected user text at most once."""
    kept: list[str] = []
    for part in parts:
        try:
            index = excluded_remaining.index(part)
        except ValueError:
            kept.append(part)
        else:
            excluded_remaining.pop(index)
    return kept


def _finalize_activity(
    *,
    human_turns: int,
    agent_turns: int,
    human_texts: list[str],
    agent_texts: list[str],
    secret_values: tuple[str, ...] | None,
    content_safe: bool,
) -> _ParsedActivity:
    """Bound and redact transcript text without discarding safe turn counts."""
    if not content_safe or secret_values is None:
        return _ParsedActivity(
            human_turns=human_turns,
            agent_turns=agent_turns,
            request=None,
            outcome=None,
            content_status="unknown",
        )
    try:
        request = _bounded_activity_text(" ".join(human_texts), secret_values)
        outcome = _bounded_activity_text(
            agent_texts[-1] if agent_texts else "", secret_values
        )
    except Exception:  # pragma: no cover - defensive sensitive-content guard
        return _ParsedActivity(
            human_turns=human_turns,
            agent_turns=agent_turns,
            request=None,
            outcome=None,
            content_status="unknown",
        )
    return _ParsedActivity(
        human_turns=human_turns,
        agent_turns=agent_turns,
        request=request,
        outcome=outcome,
        content_status="ok",
    )


def _bounded_activity_text(
    text: str, secret_values: tuple[str, ...]
) -> str | None:
    values = sorted(
        {value for value in secret_values if value}, key=len, reverse=True
    )
    for value in values:
        text = text.replace(value, "[REDACTED]")
    normalized = " ".join(text.split())
    if not normalized:
        return None
    if len(normalized) <= MAX_ACTIVITY_CHARS:
        return normalized
    return (
        normalized[: MAX_ACTIVITY_CHARS - len(TRUNCATION_MARKER)]
        + TRUNCATION_MARKER
    )


def _record_matches(
    record: UsageRecord,
    *,
    since: datetime | None,
    until: datetime | None,
    task: str | None,
) -> bool:
    if task is not None and record.slug != task:
        return False
    ts = _parse_ts(record.ts)
    if ts is None:
        return False
    if since is not None and ts < since:
        return False
    if until is not None and ts > until:
        return False
    return True


def _build_row(key: str, records: list[UsageRecord]) -> RollupRow:
    return RollupRow(
        key=key,
        sessions=len(records),
        unknown_sessions=sum(
            1 for record in records if record.usage_status == "unknown"
        ),
        input_tokens=sum(record.input_tokens or 0 for record in records),
        cache_creation_input_tokens=sum(
            record.cache_creation_input_tokens or 0 for record in records
        ),
        cache_read_input_tokens=sum(
            record.cache_read_input_tokens or 0 for record in records
        ),
        output_tokens=sum(record.output_tokens or 0 for record in records),
    )


def _group_key(record: UsageRecord, by: str) -> str:
    if by == "task":
        return record.slug
    value = getattr(record, by)
    return str(value) if value else "(unknown)"


def _unknown(
    provider: str,
    *,
    session_id: str | None = None,
    reason: str,
    activity: _ParsedActivity | None = None,
) -> ParsedUsage:
    activity = activity or _ParsedActivity(None, None, None, None, "unknown")
    return ParsedUsage(
        provider=provider,
        model=None,
        session_id=session_id,
        input_tokens=None,
        cache_creation_input_tokens=None,
        cache_read_input_tokens=None,
        output_tokens=None,
        usage_status="unknown",
        human_turns=activity.human_turns,
        agent_turns=activity.agent_turns,
        request=activity.request,
        outcome=activity.outcome,
        content_status=activity.content_status,
        reason=reason,
    )


def _format_ts(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        text = value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_filter_ts(
    value: str | datetime | None, *, is_until: bool
) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            parsed = datetime.combine(
                datetime.fromisoformat(value).date(),
                time.max if is_until else time.min,
            )
        else:
            parsed = _parse_ts(value)
            if parsed is None:
                raise ValueError(f"Invalid datetime: {value!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _inside_window(
    value: datetime,
    *,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    start = _ensure_utc(window_start)
    end = _ensure_utc(window_end)
    return start <= value <= end


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _require_str(data: dict, key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _optional_str(data: dict, key: str) -> str | None:
    value = data[key]
    if value is None or isinstance(value, str):
        return value
    raise ValueError(f"{key} must be a string or null")


def _optional_int(data: dict, key: str) -> int | None:
    value = data[key]
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"{key} must be an integer or null")


def _optional_str_value(value: object) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise ValueError("value must be a string or null")


def _optional_int_value(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError("value must be an integer or null")


def _optional_number_value(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raise ValueError("value must be a number or null")


def _usage_status(data: dict) -> UsageStatus:
    value = data["usage_status"]
    if value in {"ok", "unknown"}:
        return value
    raise ValueError("usage_status must be ok or unknown")


def _content_status(value: object) -> ContentStatus | None:
    if value is None:
        return None
    if value in {"ok", "unknown"}:
        return value
    raise ValueError("content_status must be ok, unknown, or null")


def _outcome_status(value: object) -> OutcomeStatus | None:
    if value is None:
        return None
    if value in {"completed", "failed", "timed_out", "interrupted", "unknown"}:
        return value
    raise ValueError("outcome_status is invalid")


def _first_str(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0
