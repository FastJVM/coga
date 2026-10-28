"""Event-aware audit publication and its Git-history subsumption proof.

The maintenance job and the publisher share pinned policy/inventory reads.
The selector itself remains a pure function. No edge code is imported here.
"""
from __future__ import annotations

import re
from collections import Counter
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Mapping

from coga.config import Config, ConfigError, _parse_log
from coga.lifecycle import VALID_STATUSES
from coga.log_retention import RetentionError, RetentionSnapshot, cutoff_at, select
from coga.logfile import LogMutation, parse_events
from coga.movement_cursor import MovementError, _state, migrate, movements
from coga.paths import log_path, recurring_dir, tasks_dir
from coga.taskfile import BLACKBOARD_FENCE
from coga.ticket import Ticket, TicketError


@dataclass(frozen=True)
class Inputs:
    days: int
    refs: frozenset[str]
    parent: bytes | None
    # Exact decision inputs for guards, including modes and directory shape.
    entries: tuple[tuple[str, str, str], ...]
    parent_rel: str | None


def inventory(files: Mapping[str, bytes]) -> frozenset[str]:
    """The list_tasks discovery rules over a pinned tree (no checkout reads)."""
    # The tasks root is never a task: list_tasks skips a root-level ticket.md.
    directories = {str(PurePosixPath(p).parent) for p in files
                   if PurePosixPath(p).name == "ticket.md" and PurePosixPath(p).parent != PurePosixPath(".")}
    found: set[str] = set()
    for name, raw in sorted(files.items()):
        p = PurePosixPath(name)
        if any(part.startswith("_") for part in p.parts) or p.suffix != ".md" or p.name == "README.md":
            continue
        if p == PurePosixPath("ticket.md"):
            continue
        if any(str(ancestor) in directories for ancestor in p.parents if str(ancestor) != str(p.parent)):
            continue
        if str(p.parent) in directories and p.name != "ticket.md":
            continue
        slug = str(p.parent) if p.name == "ticket.md" else str(p.with_suffix(""))
        if slug in found:
            raise RetentionError(f"duplicate task inventory ref: {slug}")
        ticket = Ticket.parse(raw.decode("utf-8"))
        status = ticket.frontmatter.get("status")
        if not isinstance(status, str) or status not in VALID_STATUSES:
            raise RetentionError(f"invalid task status: {slug}")
        found.add(slug)
    return frozenset(found)


def read_inputs(cfg: Config, root: Path, rev: str, overlays: Mapping[str, bytes | None] | None = None) -> Inputs:
    from coga import git

    config_rel = git.relative_to_root(root, cfg.repo_root / "coga.toml")
    tasks_rel = git.relative_to_root(root, tasks_dir(cfg)) + "/"
    phone_dirs = tuple(git.relative_to_root(root, recurring_dir(cfg) / name) + "/"
                       for name in ("phone-home", "_phone-home"))
    entries: dict[str, tuple[str, str]] = {}
    for record in git.run_git(root, "ls-tree", "-r", "-z", rev, "--", config_rel, tasks_rel, *phone_dirs).split("\0"):
        if record:
            meta, name = record.split("\t", 1)
            mode, kind, oid = meta.split()
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise RetentionError(f"non-regular retention input: {name}")
            entries[name] = (mode, oid)
    data = {name: git._blob_bytes(root, oid) for name, (_, oid) in entries.items()}
    for name, raw in (overlays or {}).items():
        if name == config_rel or name.startswith((tasks_rel, *phone_dirs)):
            if raw is None:
                data.pop(name, None)
            else:
                data[name] = raw
    shared = tomllib.loads(data.get(config_rel, b"").decode("utf-8"))
    days = _parse_log(shared.get("log"))
    refs = inventory({name[len(tasks_rel):]: raw for name, raw in data.items() if name.startswith(tasks_rel)})
    parents = [directory + "ticket.md" for directory in phone_dirs
               if any(name.startswith(directory) for name in data)]
    if len(parents) > 1:
        raise RetentionError("both active and parked phone-home parents exist; reconcile their cursors before trimming")
    parent_rel = parents[0] if parents else None
    if parent_rel is not None and parent_rel not in data:
        raise RetentionError("installed phone-home is missing its parent cursor; restore it before trimming")
    return Inputs(days, refs, data.get(parent_rel) if parent_rel else None,
                  tuple((name, *entry) for name, entry in sorted(entries.items())), parent_rel)


def cursor_state(parent: bytes | None, raw: bytes) -> dict | None:
    if parent is None:
        return None
    text = parent.decode("utf-8")
    if text.count(BLACKBOARD_FENCE) != 1:
        raise RetentionError("phone-home parent needs exactly one blackboard fence")
    state, _ = _state(text.split(BLACKBOARD_FENCE, 1)[1])
    try:
        return migrate(raw, state)[0]
    except MovementError:
        # A schema-1 offset/digest counts the bytes phone-home read; a CRLF
        # checkout read this LF blob expanded. Line-ending conversion is not
        # lost history, so validate that form too. A mixed prefix still fails.
        if b"\r" in raw:
            raise
        return migrate(raw.replace(b"\n", b"\r\n"), state)[0]


def snapshot(inputs: Inputs, raw: bytes) -> RetentionSnapshot:
    state = cursor_state(inputs.parent, raw)
    unread = (movements(raw) - set(state["seen_movements"])) if state and state["repo_id"] is not None else set()
    return RetentionSnapshot(inputs.refs, frozenset(unread))


def archived_events(root: Path, rev: str, rel: str, wanted: set[bytes]) -> set[bytes]:
    """Prove exact events from reachable control history, one transient scan.

    Scan patches to locate candidates without materializing every historical
    multi-megabyte log. A positive match is always checked in the full blob;
    patches alone cannot prove a legacy event's continuation boundary.
    Inspection failure is an error, never positive archival evidence.
    """
    from coga import git

    if not wanted:
        return set()
    headers = {e.split(b"\n", 1)[0] for e in wanted}
    patch = git._run([
        "git", "-C", str(root), "log", "--format=@@COGA:%H", "--full-history",
        "--no-color", "--no-ext-diff", "--no-textconv", "--no-renames", "--text",
        "-m", "-p", "--unified=0", rev, "--", rel,
    ])
    if patch.returncode:
        raise git.GitError("cannot inspect reachable audit history: " + patch.stderr.decode(errors="replace"))
    found: set[bytes] = set()
    checked: set[str] = set()
    commit = ""
    for line in patch.stdout.split(b"\n"):
        if re.fullmatch(rb"@@COGA:[0-9a-f]{40,64}", line):
            commit = line[7:].decode("ascii")
        elif commit and commit not in checked and line.startswith(b"+") and line[1:].removesuffix(b"\r") in headers:
            raw = git.tree_bytes(root, commit, rel)
            if raw is None:
                raise git.GitError(f"audit history blob missing at {commit}")
            found.update(e.canonical for e in parse_events(raw) if e.canonical in wanted)
            checked.add(commit)
            if found == wanted:
                break
    return found


def reconcile(
    cfg: Config, root: Path, rev: str, source: bytes, *,
    source_base: bytes = b"", head: bytes = b"", overlays: Mapping[str, bytes | None] | None = None,
    today: date | None = None, mutation: LogMutation | None = None,
) -> bytes:
    from coga import git
    try:
        return _reconcile(cfg, root, rev, source, source_base=source_base, head=head,
                          overlays=overlays, today=today, mutation=mutation)
    except (ValueError, TicketError, ConfigError) as exc:
        raise git.StateRegressionError(f"cannot classify audit history: {exc}") from exc


def _reconcile(
    cfg: Config, root: Path, rev: str, source: bytes, *,
    source_base: bytes = b"", head: bytes = b"", overlays: Mapping[str, bytes | None] | None = None,
    today: date | None = None, mutation: LogMutation | None = None,
) -> bytes:
    from coga import git

    rel = git.relative_to_root(root, log_path(cfg))
    current = git.tree_bytes(root, rev, rel) or b""
    if mutation is not None:
        before = git._clean_bytes(root, mutation.preimage, rel)
        after = git._clean_bytes(root, mutation.postimage, rel)
        if current != before or source != after:
            raise git.StateRegressionError("audit mutation preimage/postimage changed; recover and replan")
        return after
    control_events = parse_events(current)
    source_events = parse_events(source)
    held = {e.canonical for e in control_events}
    # An ordinary source may be stale, but may not delete events its own HEAD
    # held and control still needs. No PUBLISHED_REF blob is a source base.
    provenance = (Counter(e.canonical for e in parse_events(head))
                  | Counter(e.canonical for e in parse_events(source_base)))
    missing = provenance - Counter(e.canonical for e in source_events)
    if missing.keys() & held:
        raise git.StateRegressionError("audit log was truncated without a LogMutation receipt; restore or recover before publication")
    incoming = [e for e in source_events if e.canonical not in held]
    if not incoming:
        return current
    # Preserve control's sequence and occurrence counts. Only source events
    # absent there are appended, in their original source order.
    addition = b"".join(e.raw for e in incoming)
    if current and not current.endswith(b"\n"):
        raise git.StateRegressionError("audit log has an incomplete control tail; repair before appending")
    combined = current + addition
    config_rel = git.relative_to_root(root, cfg.repo_root / "coga.toml")
    config_raw = (overlays or {}).get(config_rel, git.tree_bytes(root, rev, config_rel)) or b""
    days = _parse_log(tomllib.loads(config_raw.decode("utf-8")).get("log"))
    cutoff = cutoff_at(today or date.today(), days)
    if not days or not any(e.complete and e.timestamp is not None and e.timestamp < cutoff for e in incoming):
        return combined
    inputs = read_inputs(cfg, root, rev, overlays)
    # Unread protection comes from the pinned CONTROL snapshot, not candidate
    # hashes. Otherwise a forgotten consumed hash would resurrect itself.
    protected = snapshot(inputs, current)
    selected = select(combined, protected, cutoff)
    removable = {selected.events[i].canonical for i in selected.mutation.removed
                 if selected.events[i].start >= len(current)}
    archived = archived_events(root, rev, rel, removable)
    return current + b"".join(e.raw for e in incoming if e.canonical not in archived)
