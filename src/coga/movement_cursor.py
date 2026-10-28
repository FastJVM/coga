"""Shared movement identity/cursor contract for reporting and log retention."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from uuid import UUID

from coga.logfile import LogEvent, decode_log_message, parse_events


class MovementError(ValueError):
    """Invalid local cursor input (messages contain no private data)."""


def _hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


_STATE_LINE = re.compile(r"^period_state: ([^\r\n]+)(?=\r?$)", re.MULTILINE)
# Names are producer-owned free text: actors/operators can contain spaces and
# step names can contain parentheses. Only envelope delimiters end a field.
_ENTRY = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}) (?P<version>v1 )?\[([^\[\]\r\n]+)\] \[([^\[\]\r\n]+)\] (.+)")
_MOVEMENT = re.compile(
    r"(?:advanced to step [1-9][0-9]* \([^\r\n]+\)(?: → \S[^\r\n]*)?(?: — [\s\S]+)?"
    r"|task done(?: — [\s\S]+)?"
    r"|auto-bumped on merge of (?:PR #[0-9]+|the linked PR) → done)"
)

def _uuid(value: object) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value and UUID(value).version == 4
    except ValueError:
        return False


def _state(region: str) -> tuple[dict, re.Match[str]]:
    matches = list(_STATE_LINE.finditer(region))
    if len(matches) != 1:
        raise MovementError("phone-home requires one period_state line")
    try:
        state = json.loads(matches[0][1])
        if not isinstance(state, dict):
            raise ValueError
        if type(state.get("schema")) is not int or state["schema"] not in (1, 2):
            raise ValueError
        keys = {"schema", "run", "repo_id"} | ({"offset", "digest"} if state["schema"] == 1 else {"seen_movements"})
        if set(state) != keys or type(state["run"]) is not int or state["run"] < 0:
            raise ValueError
        if state["repo_id"] is not None and not _uuid(state["repo_id"]):
            raise ValueError
        if state["schema"] == 1:
            if type(state["offset"]) is not int or state["offset"] < 0 or not _hash(state["digest"]):
                raise ValueError
        else:
            seen = state["seen_movements"]
            if not isinstance(seen, list) or any(not _hash(h) for h in seen) or seen != sorted(set(seen)):
                raise ValueError
    except (ValueError, TypeError):
        raise MovementError("invalid phone-home period_state") from None
    return state, matches[0]


def _housekeeping(ref: str) -> bool:
    return ref == "recurring" or ref.startswith("recurring/")


def _movement(line: bytes) -> bool:
    try:
        match = _ENTRY.fullmatch(line.decode("utf-8").removesuffix("\r"))
        if not match or not match[3].strip() or not match[4].strip() or _housekeeping(match[3]):
            return False
        datetime.strptime(match[1], "%Y-%m-%d %H:%M")
        message = decode_log_message(match[5]) if match["version"] else match[5]
        return _MOVEMENT.fullmatch(message) is not None
    except (UnicodeDecodeError, ValueError):
        return False


def fingerprint(event: LogEvent) -> str | None:
    if not event.complete or event.timestamp is None:
        return None
    if not _movement(event.raw.split(b"\n", 1)[0]):
        return None
    return hashlib.sha256(event.canonical.removesuffix(b"\n")).hexdigest()


def movements(raw: bytes) -> set[str]:
    return {h for e in parse_events(raw) if (h := fingerprint(e)) is not None}


def migrate(raw: bytes, state: dict, *, allow_reset: bool = False) -> tuple[dict, bool]:
    """Migrate consumed prefix only. Trim cannot infer a broken prefix's past."""
    if state["schema"] == 2:
        return dict(state), False
    complete = raw[:raw.rfind(b"\n") + 1]
    offset = state["offset"]
    valid = (offset <= len(complete) and (offset == 0 or complete[offset - 1:offset] == b"\n")
             and hashlib.sha256(complete[:offset]).hexdigest() == state["digest"])
    reset = not valid and state["repo_id"] is not None
    if reset and not allow_reset:
        raise MovementError("phone-home schema-1 prefix is invalid; run phone-home to acknowledge its visible reset before trimming")
    seen = movements(raw if state["repo_id"] is None or reset else complete[:offset])
    return {"schema": 2, "run": state["run"], "repo_id": state["repo_id"],
            "seen_movements": sorted(seen)}, reset


def cursor(raw: bytes, state: dict, *, baseline: bool) -> tuple[list[str], int, bool]:
    migrated, reset = migrate(raw, state, allow_reset=True)
    current = movements(raw)
    count = 0 if baseline or reset else len(current - set(migrated["seen_movements"]))
    return sorted(current), count, reset and not baseline


def replace_state(region: str, state: dict) -> str:
    _, match = _state(region)
    return (region[:match.start()] + "period_state: " + json.dumps(state, separators=(",", ":"))
            + region[match.end():])
