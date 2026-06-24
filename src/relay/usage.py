"""Usage records parsed from agent transcripts and stored in blackboards."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Literal

from relay.atomicio import atomic_write_text


USAGE_SCHEMA = 1
USAGE_HEADING = "Usage"

UsageStatus = Literal["ok", "unknown"]
ParserKey = Literal["claude", "codex"]

_USAGE_SECTION_RE = re.compile(
    rf"^##\s+{re.escape(USAGE_HEADING)}\s*$\n?(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
_SECTION_RE = re.compile(r"^(## .+?)$", re.MULTILINE)


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
    reason: str | None = None


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
    schema: int = USAGE_SCHEMA

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, line: str) -> "UsageRecord":
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("usage record is not JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("usage record must be an object")
        if data.get("schema") != USAGE_SCHEMA:
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
                schema=USAGE_SCHEMA,
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
) -> ParsedUsage:
    if provider == "claude":
        return _parse_claude_session(
            cwd=cwd,
            session_id=session_id,
            window_start=window_start,
            window_end=window_end,
        )
    if provider == "codex":
        return _parse_codex_session(cwd=cwd, pre_existing=pre_existing or set())
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
    blackboard: Path,
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
) -> None:
    if not blackboard.is_file():
        return
    provider_key = parser_key_for_cli(cli)
    try:
        parsed = parse_session(
            provider_key,
            cwd=cwd,
            session_id=session_id,
            pre_existing=pre_existing,
            window_start=window_start,
            window_end=window_end,
        )
    except Exception as exc:  # pragma: no cover - defensive launch guard
        print(f"relay usage: failed to parse session usage: {exc}", file=sys.stderr)
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
        print(f"relay usage: {parsed.reason}", file=sys.stderr)

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
    )
    try:
        append_record(blackboard, record)
    except Exception as exc:  # pragma: no cover - defensive launch guard
        print(f"relay usage: failed to append usage record: {exc}", file=sys.stderr)


def append_record(blackboard: Path, record: UsageRecord) -> None:
    text = blackboard.read_text()
    line = record.to_json()

    matches = list(_SECTION_RE.finditer(text))
    for i, match in enumerate(matches):
        if match.group(1).strip() != f"## {USAGE_HEADING}":
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[:end].rstrip()
        new_text = section + "\n\n" + line + "\n" + text[end:]
        atomic_write_text(blackboard, new_text)
        return

    tail = "" if text.endswith("\n") else "\n"
    new_text = text + f"{tail}\n## {USAGE_HEADING}\n\n{line}\n"
    atomic_write_text(blackboard, new_text)


def load_records(relay_os: Path) -> list[UsageRecord]:
    records: list[UsageRecord] = []
    for blackboard in _usage_blackboards(relay_os):
        try:
            text = blackboard.read_text()
        except OSError:
            continue
        for section in _USAGE_SECTION_RE.findall(text):
            for line in section.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    records.append(UsageRecord.from_json(stripped))
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
            continue
        if obj.get("type") != "assistant":
            continue
        line_ts = _parse_ts(obj.get("timestamp"))
        if line_ts is not None and not _inside_window(
            line_ts, window_start=window_start, window_end=window_end
        ):
            continue
        message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        usage = message.get("usage") or obj.get("usage") or {}
        if not isinstance(usage, dict):
            continue
        matched = True
        model = _first_str(message.get("model"), obj.get("model")) or model
        input_tokens += _int_value(usage.get("input_tokens"))
        cache_creation_input_tokens += _int_value(
            usage.get("cache_creation_input_tokens")
        )
        cache_read_input_tokens += _int_value(usage.get("cache_read_input_tokens"))
        output_tokens += _int_value(usage.get("output_tokens"))

    if not matched:
        return _unknown(
            "anthropic",
            session_id=session_id,
            reason=f"claude transcript had no assistant usage: {path}",
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
    )


def _parse_codex_session(cwd: Path, pre_existing: set[Path]) -> ParsedUsage:
    candidates: list[Path] = []
    cwd_str = str(cwd.resolve())
    for path in set(_codex_rollout_paths()) - pre_existing:
        meta = _read_codex_session_meta(path)
        if meta is None:
            continue
        if meta.get("cwd") == cwd_str:
            candidates.append(path)
    if not candidates:
        return _unknown("openai", reason=f"codex rollout not found for cwd: {cwd_str}")
    path = max(candidates, key=lambda item: (_mtime_ns(item), str(item)))
    return _parse_codex_rollout(path)


def _parse_codex_rollout(path: Path) -> ParsedUsage:
    provider = "openai"
    session_id: str | None = None
    model: str | None = None
    last_usage: dict | None = None
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
            continue
        kind = obj.get("type")
        payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
        if kind == "session_meta":
            provider = _first_str(payload.get("model_provider"), provider) or provider
            session_id = _first_str(payload.get("id"), session_id)
        elif kind == "turn_context":
            model = _first_str(payload.get("model"), model) or model
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

    if last_usage is None:
        return _unknown(
            provider,
            session_id=session_id,
            reason=f"codex rollout had no token_count event: {path}",
        )
    output_tokens = _int_value(last_usage.get("output_tokens")) + _int_value(
        last_usage.get("reasoning_output_tokens")
    )
    return ParsedUsage(
        provider=provider,
        model=model,
        session_id=session_id,
        input_tokens=_int_value(last_usage.get("input_tokens")),
        cache_creation_input_tokens=None,
        cache_read_input_tokens=_int_value(last_usage.get("cached_input_tokens")),
        output_tokens=output_tokens,
        usage_status="ok",
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
                }
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _usage_blackboards(relay_os: Path) -> list[Path]:
    roots = [relay_os / "tasks", relay_os / "recurring"]
    paths: list[Path] = []
    for root in roots:
        if root.is_dir():
            paths.extend(root.glob("**/blackboard.md"))
    return sorted(paths)


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
) -> ParsedUsage:
    return ParsedUsage(
        provider=provider,
        model=None,
        session_id=session_id,
        input_tokens=None,
        cache_creation_input_tokens=None,
        cache_read_input_tokens=None,
        output_tokens=None,
        usage_status="unknown",
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


def _usage_status(data: dict) -> UsageStatus:
    value = data["usage_status"]
    if value in {"ok", "unknown"}:
        return value
    raise ValueError("usage_status must be ok or unknown")


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


def _mtime_ns(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0
