#!/usr/bin/env python3
"""Deterministic half of the upstream-coga period task.

Sweeps the client checkouts named by machine-local `[upstream] checkouts`,
reads each one's `coga/upstream-coga.md` — the append-only file a client-repo
Dream run writes its `owner: coga` findings to — and files one draft ticket in
this repo per entry not yet processed.

Single-consumer, ticket-owned logic: it imports only shared core infra and adds
nothing to `src/coga/`. State is one cursor line per checkout under
`## Upstream cursors` on the *template's* blackboard, written through the
blackboard helpers so frontmatter is never hand-edited.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from coga import git
from coga.blackboard import append_to_section_text, update_blackboard_under_barrier
from coga.config import Config, load_config
from coga.create import create_task
from coga.paths import recurring_dir
from coga.taskfile import read_blackboard
from coga.tasks import list_tasks

JOB = "recurring/upstream-coga"
UPSTREAM_FILE = Path("coga") / "upstream-coga.md"
CURSORS_HEADING = "Upstream cursors"
# Provenance line every filed ticket carries. Its value is `<checkout-key>/<id>`,
# and the processor greps existing tasks for it before creating anything, so a
# run interrupted between ticket creation and the cursor write files nothing
# twice on retry. The line, not the cursor, is the durable identity.
UPSTREAM_ID_LABEL = "upstream-id"

_REQUIRED_FIELDS = ("id", "repo", "date", "class", "target", "evidence")
_FIELD_RE = re.compile(r"^-\s+(?P<key>[a-z]+):\s*(?P<value>.*?)\s*$")
_CURSOR_RE = re.compile(r"^-\s+(?P<key>\S+):\s*(?P<id>\S+)\s*$")
_SECTION_RE = re.compile(r"^##[ \t]+(?P<heading>.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Entry:
    """One parsed `## <title>` block of a client's `upstream-coga.md`."""

    title: str
    id: str
    repo: str
    date: str
    cls: str
    target: str
    evidence: str
    prose: str


def parse_entries(text: str) -> tuple[list[Entry], list[str]]:
    """Split `upstream-coga.md` on `^## ` and parse each block.

    Returns the entries in file order plus one problem note per malformed block.
    A malformed block is skipped, never fatal — the rest of the file still
    files. Anything before the first `## ` heading is the documented file
    header and is ignored.
    """
    entries: list[Entry] = []
    problems: list[str] = []
    matches = list(_SECTION_RE.finditer(text))
    for i, match in enumerate(matches):
        title = match.group("heading").strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.end():end].strip("\n")
        fields: dict[str, str] = {}
        prose_lines: list[str] = []
        in_fields = True
        for line in block.splitlines():
            field = _FIELD_RE.match(line) if in_fields else None
            if field:
                fields[field.group("key")] = field.group("value")
                continue
            if in_fields and not line.strip():
                # Blank lines between the heading and the first field, or
                # between fields, are fine; the first blank after any field
                # ends the field list.
                if fields:
                    in_fields = False
                continue
            in_fields = False
            prose_lines.append(line)
        missing = [key for key in _REQUIRED_FIELDS if not fields.get(key)]
        if missing:
            problems.append(
                f"entry {title!r} is missing {', '.join(missing)}; skipped"
            )
            continue
        entries.append(
            Entry(
                title=title,
                id=fields["id"],
                repo=fields["repo"],
                date=fields["date"],
                cls=fields["class"],
                target=fields["target"],
                evidence=fields["evidence"],
                prose="\n".join(prose_lines).strip(),
            )
        )
    return entries, problems


def checkout_key(checkout: Path) -> str:
    """The cursor key for a configured checkout: its directory name."""
    return checkout.name


def template_ticket_path(cfg: Config) -> Path:
    return recurring_dir(cfg) / "upstream-coga" / "ticket.md"


def read_cursors(blackboard: str) -> dict[str, str]:
    """Parse `- <checkout-key>: <last-processed-id>` lines under the heading."""
    target = CURSORS_HEADING.casefold()
    matches = list(_SECTION_RE.finditer(blackboard))
    section = ""
    for i, match in enumerate(matches):
        if match.group("heading").strip().casefold() != target:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(blackboard)
        section = blackboard[match.end():end]
        break
    cursors: dict[str, str] = {}
    for line in section.splitlines():
        cursor = _CURSOR_RE.match(line)
        if cursor:
            # Later lines win: the cursor is appended, never rewritten in place.
            cursors[cursor.group("key")] = cursor.group("id")
    return cursors


def write_cursor(cfg: Config, key: str, entry_id: str) -> None:
    """Append the checkout's new cursor line to the template blackboard."""
    update_blackboard_under_barrier(
        cfg,
        template_ticket_path(cfg),
        lambda region: append_to_section_text(
            region, CURSORS_HEADING, f"- {key}: {entry_id}"
        ),
    )


def upstream_id(key: str, entry: Entry) -> str:
    return f"{key}/{entry.id}"


def filed_upstream_ids(cfg: Config) -> set[str]:
    """Every `upstream-id:` already carried by a ticket in this repo."""
    marker = re.compile(rf"^-\s+{UPSTREAM_ID_LABEL}:\s*(?P<value>\S+)\s*$", re.M)
    found: set[str] = set()
    for ref in list_tasks(cfg):
        try:
            text = ref.ticket_path.read_text(encoding="utf-8")
        except OSError:
            continue
        found.update(m.group("value") for m in marker.finditer(text))
    return found


def describe(key: str, entry: Entry) -> str:
    """The filed ticket's `## Description` body: provenance lines, then prose."""
    return (
        f"Filed by `{JOB}` from `{key}/{UPSTREAM_FILE.as_posix()}`.\n\n"
        f"- {UPSTREAM_ID_LABEL}: {upstream_id(key, entry)}\n"
        f"- repo: {entry.repo}\n"
        f"- date: {entry.date}\n"
        f"- class: {entry.cls}\n"
        f"- target: {entry.target}\n"
        f"- evidence: {entry.evidence}\n\n"
        f"{entry.prose}\n"
    )


def sweep(cfg: Config, *, out: TextIO = sys.stdout) -> list[Path]:
    """Process every configured checkout. Returns the paths to publish."""
    template = template_ticket_path(cfg)
    if not cfg.upstream_checkouts:
        out.write(
            "[upstream] no checkouts configured — add "
            "`[upstream] checkouts = [...]` to coga.local.toml.\n"
        )
        return []

    # Two configured checkouts with one directory name would share a cursor
    # line; refuse to file for either rather than guess which one it belongs to.
    by_key: dict[str, list[Path]] = {}
    for checkout in dict.fromkeys(cfg.upstream_checkouts):
        by_key.setdefault(checkout_key(checkout), []).append(checkout)
    ambiguous = {key: paths for key, paths in by_key.items() if len(paths) > 1}
    for key, paths in ambiguous.items():
        out.write(
            f"[upstream] {key}: ambiguous checkout name shared by "
            f"{', '.join(str(p) for p in paths)}; nothing filed for either — "
            "rename one directory or drop it from `[upstream] checkouts`.\n"
        )

    cursors = read_cursors(read_blackboard(template, blackboard_required=False))
    already = filed_upstream_ids(cfg)
    touched: list[Path] = [template]
    for key, paths in by_key.items():
        if key in ambiguous:
            continue
        checkout = paths[0]
        source = checkout / UPSTREAM_FILE
        if not checkout.is_dir():
            out.write(f"[upstream] {key}: checkout {checkout} not found; skipped.\n")
            continue
        if not source.is_file():
            out.write(f"[upstream] {key}: no {UPSTREAM_FILE.as_posix()}; skipped.\n")
            continue
        entries, problems = parse_entries(source.read_text(encoding="utf-8"))
        for problem in problems:
            out.write(f"[upstream] {key}: {problem}\n")
        cursor = cursors.get(key)
        if cursor is not None:
            ids = [entry.id for entry in entries]
            if cursor not in ids:
                # The file is append-only, so a recorded id can only vanish if
                # it was rewritten or truncated. Re-filing every entry would be
                # the worse failure; stop and say so.
                out.write(
                    f"[upstream] {key}: cursor {cursor} is no longer in "
                    f"{source}; the file was truncated or rewritten. Stopped — "
                    "restore the file or reset the cursor by hand.\n"
                )
                continue
            entries = entries[ids.index(cursor) + 1:]
        filed = 0
        for entry in entries:
            uid = upstream_id(key, entry)
            if uid in already:
                out.write(f"[upstream] {key}: {entry.id} already filed; skipped.\n")
            else:
                created = create_task(
                    cfg=cfg,
                    title=entry.title,
                    workflow_name=None,
                    contexts=[],
                    owner=None,
                    status=None,
                    description=describe(key, entry),
                    created_by=JOB,
                )
                already.add(uid)
                touched.append(created["path"])
                filed += 1
                out.write(f"[upstream] {key}: filed {created['slug']} for {entry.id}\n")
            # Advance after every entry, not once at the end, so an interrupted
            # run resumes from the last entry it actually settled.
            write_cursor(cfg, key, entry.id)
        out.write(f"[upstream] {key}: {filed} ticket(s) filed, {len(entries)} entr(ies) seen.\n")
    return touched


def main(cfg: Config, *, out: TextIO = sys.stdout) -> int:
    touched = sweep(cfg, out=out)
    if len(touched) > 1:
        # Explicit path set: the cursor, every ticket it accounts for, and (added
        # by `sync_paths` itself) the log lines `create_task` appended. Publishing
        # the cursor without its tickets would strand them; a failed sync is
        # reported and logged, and the `upstream-id` dedupe makes the retry safe.
        git.sync_paths(
            cfg,
            touched[0],
            touched,
            message=f"Recurring: {JOB} filed {len(touched) - 1} upstream ticket(s)",
        )
    return 0


if __name__ == "__main__":
    code = main(load_config())
    if code:
        sys.exit(code)
    # Complete the step through the CLI: calling a Typer command function
    # in-process would pass `OptionInfo` sentinels instead of real defaults.
    sys.exit(
        subprocess.run(
            [sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]],
            check=False,
        ).returncode
    )
