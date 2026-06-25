"""A durable, human-visible producer/consumer queue in a dedicated git file.

A *spool* is a `## Spool (pending)` section in a standalone, git-tracked file
(`recurring/digest/spool.md`) holding one JSON object per line (JSONL).
Producers `append_record` as events happen; the single consumer (`relay digest`)
`drain`s the consumed records. The records are plain text in a git-tracked file
— never a hidden dotfile — so the queue stays legible and recoverable,
consistent with Relay's no-hidden-state rule.

JSONL (not a table) so a record's free-text fields can hold any characters
(pipes, arrows, emoji) without escaping, and each line stands alone. Records
keep non-ASCII verbatim (`ensure_ascii=False`), so reads and writes pin
`utf-8` explicitly rather than trusting the process locale — a digest fired
from a bare cron environment (`LANG=C`) would otherwise crash encoding `→`/`✅`.

Concurrency / merge contract — the spool is resolved by *construction*, not a
lock. State-plane writes land directly on the control branch from any number of
relay processes (this clone, another clone, another machine), so the spool is a
contended file. The shape keeps it mergeable:

- Producers `append_record` a uniquely-`id`'d record at the **bottom** only,
  never touching the watermark or existing records.
- A single `consumed_through: <id>` watermark line in a fixed slot under the
  heading names the last record the consumer has posted.
- The consumer `drain`s by advancing the watermark to the newest record's id
  and trimming every consumed record from the **top**, always keeping the
  newest record in place as an *anchor*. It never empties the tail.

A concurrent drain (deletes a top prefix + bumps the watermark) and append (adds
one bottom line) then touch disjoint hunks separated by the anchor, so git's
3-way merge resolves them with no conflict and no resurrection. The watermark
stops the retained anchor being re-posted next run. `**/spool.md merge=union`
(`.gitattributes`) is the *backstop* for the one remaining case — two producers
appending at the tail — where union safely keeps both added lines (records carry
an `id`, so the order union picks is harmless, and the digest de-dups by
content). See the `relay/sync` context for the full contract.

All entry points take the spool-file path and rewrite only its
`## Spool (pending)` section, leaving any header prose untouched. Writes go
through `atomic_write_text` so a crash mid-write can't truncate the file.
"""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

from relay.atomicio import atomic_write_text


SPOOL_HEADING = "Spool (pending)"
WATERMARK_KEY = "consumed_through"

# Matches the `## Spool (pending)` heading and captures its body up to the next
# `## ` heading (any section) or EOF. `_SECTION_RE` is intentionally narrow so a
# later `## Ledger`/`## Sent` section, or trailing free-text, is left untouched.
_SECTION_RE = re.compile(
    rf"^##\s+{re.escape(SPOOL_HEADING)}\s*$\n?(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def append_record(path: Path, record: dict) -> None:
    """Append one JSONL `record` to the `## Spool (pending)` section of `path`.

    The record is stamped with a unique random `id` (unless it already carries
    one) so the consumer's watermark can name it and the digest can de-dup, then
    serialized compactly on a single line and inserted at the **bottom** of the
    section — producers are pure tail-appenders. Creates the spool section at the
    end of the file when it doesn't already exist so it never collides with the
    header prose.
    """
    if "id" not in record:
        record = {"id": secrets.token_hex(6), **record}
    line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
    text = _read(path)

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
    """Return every pending JSONL record without modifying the file.

    Only lines that parse as JSON objects are returned; the `consumed_through`
    watermark line and any other non-record line are ignored.
    """
    if not path.is_file():
        return []
    match = _SECTION_RE.search(_read(path))
    if not match:
        return []
    return [rec for _, rec in _parse_section(match.group(1))[1]]


def read_unconsumed(path: Path) -> list[dict]:
    """Return only the records the consumer has not yet posted.

    Unconsumed records are those physically **after** the anchor — the record
    whose `id` equals the `consumed_through` watermark. With no watermark (a
    fresh spool, or one never drained) every record is unconsumed. This is the
    consumer's read: the retained anchor was posted on a prior run and must not
    be re-posted.
    """
    if not path.is_file():
        return []
    match = _SECTION_RE.search(_read(path))
    if not match:
        return []
    watermark, records = _parse_section(match.group(1))
    anchor = _anchor_index(watermark, records)
    return [rec for _, rec in records[anchor + 1 :]]


def drain(path: Path) -> list[dict]:
    """Advance the watermark to the newest record and trim the consumed prefix.

    Returns the newly-consumed records (everything after the previous anchor, in
    append order). The newest record is kept in place as the anchor and the
    `consumed_through` watermark is set to its id, so the tail is never emptied
    and the anchor is not re-posted next run. An absent file, an empty spool, or
    a spool with nothing new since the last drain yields `[]` and leaves the file
    untouched.

    Trimming only the consumed *prefix* (top) — rather than rewriting the whole
    section to empty as the original drain did — is what keeps a concurrent
    bottom append in a disjoint merge hunk. See the module docstring.
    """
    if not path.is_file():
        return []
    text = _read(path)
    match = _SECTION_RE.search(text)
    if not match:
        return []

    watermark, records = _parse_section(match.group(1))
    if not records:
        return []
    anchor = _anchor_index(watermark, records)
    consumed = [rec for _, rec in records[anchor + 1 :]]
    if not consumed:
        return []

    anchor_raw, anchor_rec = records[-1]
    new_watermark = str(anchor_rec.get("id") or "")
    new_body = f"\n{WATERMARK_KEY}: {new_watermark}\n{anchor_raw}\n"
    new_text = text[: match.start(1)] + new_body + text[match.end(1) :]
    atomic_write_text(path, new_text)
    return consumed


def _read(path: Path) -> str:
    """Return the spool file's full text (utf-8), or "" when it doesn't exist."""
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_section(body: str) -> tuple[str | None, list[tuple[str, dict]]]:
    """Split a section body into its watermark id and ordered record lines.

    Returns `(watermark, records)` where `watermark` is the last
    `consumed_through:` value seen (a union merge could leave a duplicate
    watermark line; last wins) or None, and `records` is a list of
    `(raw_line, parsed_dict)` in file order. Blank lines and any stray non-record
    line are skipped.
    """
    watermark: str | None = None
    records: list[tuple[str, dict]] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith(f"{WATERMARK_KEY}:"):
            watermark = stripped[len(WATERMARK_KEY) + 1 :].strip() or None
            continue
        rec = _as_record(raw)
        if rec is not None:
            records.append((raw, rec))
    return watermark, records


def _anchor_index(watermark: str | None, records: list[tuple[str, dict]]) -> int:
    """Index of the anchor record (id == watermark), or -1 when none matches.

    Scans from the end so a stray duplicate id resolves to the latest one. A
    None/empty watermark, or a watermark naming a record no longer present,
    yields -1 (everything is unconsumed) — at-least-once, never lost.
    """
    if not watermark:
        return -1
    for i in range(len(records) - 1, -1, -1):
        if records[i][1].get("id") == watermark:
            return i
    return -1


def _as_record(line: str) -> dict | None:
    """Parse one line as a JSONL record, or None if it isn't one."""
    stripped = line.strip()
    if not stripped:
        return None
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


__all__ = [
    "SPOOL_HEADING",
    "WATERMARK_KEY",
    "append_record",
    "read_records",
    "read_unconsumed",
    "drain",
]
