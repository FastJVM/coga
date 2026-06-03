"""A durable, human-visible producer/consumer queue on a blackboard.

A *spool* is a `## Spool (pending)` section inside an ordinary `blackboard.md`,
holding one JSON object per line (JSONL). Producers `append_record` as events
happen; a consumer `drain`s the whole section, processes the records, and the
section is emptied back to just its heading. The records are plain text in a
git-tracked blackboard — never a hidden dotfile — so the queue stays legible
and recoverable, consistent with Relay's no-hidden-state rule.

JSONL (not a table) so a record's free-text fields can hold any characters
(pipes, arrows, emoji) without escaping, and each line stands alone. Records
keep non-ASCII verbatim (`ensure_ascii=False`), so reads and writes pin
`utf-8` explicitly rather than trusting the process locale — a digest fired
from a bare cron environment (`LANG=C`) would otherwise crash encoding `→`/`✅`.

Concurrency: Relay runs one CLI process at a time, so appends and drains are
serialized by that. Writes still go through `atomic_write_text` so a crash
mid-write can't truncate the blackboard. `drain` defensively ignores any
non-JSON line in the section (e.g. a stray ledger line appended at EOF), and
rewrites only the spool section — never the rest of the file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from relay.atomicio import atomic_write_text


SPOOL_HEADING = "Spool (pending)"

# Matches the `## Spool (pending)` heading and captures its body up to the next
# `## ` heading (any section) or EOF. `_SECTION_RE` is intentionally narrow so a
# later `## Ledger`/`## Sent` section, or trailing free-text, is left untouched.
_SECTION_RE = re.compile(
    rf"^##\s+{re.escape(SPOOL_HEADING)}\s*$\n?(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def append_record(path: Path, record: dict) -> None:
    """Append one JSONL `record` to the `## Spool (pending)` section of `path`.

    Creates the file (and the section) if absent. The record is serialized
    compactly on a single line; the spool section is created at EOF when it
    doesn't already exist so it never collides with other sections.
    """
    line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""

    match = _SECTION_RE.search(text)
    if match:
        body = match.group(1)
        new_body = body.rstrip("\n") + ("\n" if body.strip() else "") + line + "\n"
        new_text = text[: match.start(1)] + new_body + text[match.end(1) :]
    else:
        sep = "" if not text or text.endswith("\n") else "\n"
        new_text = f"{text}{sep}\n## {SPOOL_HEADING}\n\n{line}\n"

    atomic_write_text(path, new_text)


def read_records(path: Path) -> list[dict]:
    """Return the pending JSONL records without modifying the file.

    Only lines that parse as JSON objects are returned; any other line in the
    section (blank lines, a stray ledger line) is ignored.
    """
    if not path.is_file():
        return []
    match = _SECTION_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        return []
    return _parse_records(match.group(1))


def drain(path: Path) -> list[dict]:
    """Read every pending record, then clear them from the spool section.

    Returns the records in append order. An absent file or empty spool yields
    `[]` and leaves the file untouched (idempotent no-op). Only the JSON record
    lines are removed: any non-record line that happened to land in the section
    body — notably a `scaffolded …` period-ledger line that
    `recurring._record_run` appends at EOF when the spool is the last section —
    is preserved, and everything outside the section is untouched verbatim.
    """
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    match = _SECTION_RE.search(text)
    if not match:
        return []

    records: list[dict] = []
    kept: list[str] = []
    for raw in match.group(1).splitlines():
        if not raw.strip():
            continue
        rec = _as_record(raw)
        if rec is None:
            kept.append(raw)  # not a record (e.g. a ledger line) — preserve it
        else:
            records.append(rec)
    if not records:
        return []

    new_body = "\n"
    if kept:
        new_body += "\n".join(kept) + "\n"
    emptied = text[: match.start(1)] + new_body + text[match.end(1) :]
    atomic_write_text(path, emptied)
    return records


def _parse_records(body: str) -> list[dict]:
    return [rec for raw in body.splitlines() if (rec := _as_record(raw)) is not None]


def _as_record(line: str) -> dict | None:
    """Parse one line as a JSONL record, or None if it isn't one.

    A non-record line (a blank line, or a `scaffolded …` ledger line that
    `recurring._record_run` appended at EOF) returns None so callers can skip
    or preserve it.
    """
    stripped = line.strip()
    if not stripped:
        return None
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


__all__ = ["SPOOL_HEADING", "append_record", "read_records", "drain"]
