"""Detect period-task runs that complete without advancing declared state.

A recurring task declares the blackboard keys it owns via a `state_keys:` list
in its `ticket.md` frontmatter. When `relay recurring` scaffolds a period task,
it snapshots those keys' current values from the parent recurring task's
blackboard into the period task directory (`.state-snapshot.json`). When the
period task completes (`relay mark done`), we diff: a declared key still equal
to its scaffold-time value did not advance this run — which means the next
firing reads the same stale cursor and redoes the same range. We warn (and
broadcast an FYI) rather than silently accept it.

The whole mechanism keys off the snapshot file's presence, so ordinary
(non-recurring) tasks — which never get one — never participate. A genuine
no-work period (a cursor that legitimately did not move) produces a harmless
false-positive warning; that trade was chosen over a skip-sentinel protocol.

This module is pure data: snapshot read/write and key comparison. The user
surface (the local warning echo and the Slack FYI) lives in `relay.mark`, and
the static sweep lives in `relay.validate`; both reuse the helpers here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from relay.config import Config
from relay.paths import recurring_dir

# A dotfile, deliberately: it sits beside the three canonical task files
# (ticket/blackboard/log) without being mistaken for one, and `relay validate`'s
# required-file check ignores it. It is git-tracked with the rest of the task
# dir so a stuck cursor is reconstructable after the fact.
SNAPSHOT_FILE = ".state-snapshot.json"


@dataclass
class StateSnapshot:
    """The parent's declared-key values as they stood when this period scaffolded.

    `parent` is the recurring task name (the period slug minus its period
    suffix); the live blackboard is reconstructed from it via `recurring_dir`,
    so the snapshot stays valid across worktrees and checkouts. `keys` maps each
    declared key to its scaffold-time value, or `None` when the key was absent
    from the blackboard at that time.
    """

    parent: str
    keys: dict[str, str | None]


def _key_line_re(key: str) -> re.Pattern[str]:
    # Match a `key: value` line anywhere in the blackboard. Declared keys are
    # specific (e.g. `last_commit`), so a stray prose collision is unlikely;
    # the first match wins.
    return re.compile(rf"^[ \t]*{re.escape(key)}[ \t]*:[ \t]*(.*?)[ \t]*$", re.MULTILINE)


def parse_keys(blackboard_text: str, keys: list[str]) -> dict[str, str | None]:
    """Read each declared key's value from blackboard text.

    A key's value is the captured remainder of the first `key: value` line.
    A missing key reads as `None`; an empty value (`key:` with nothing after)
    reads as `""`. Both an absent key and an unchanged value count as "did not
    advance" at comparison time.
    """
    out: dict[str, str | None] = {}
    for key in keys:
        match = _key_line_re(key).search(blackboard_text)
        out[key] = match.group(1) if match else None
    return out


def write_snapshot(
    task_dir: Path, parent: str, blackboard_path: Path, state_keys: list[str]
) -> None:
    """Snapshot the parent blackboard's declared keys into the period task dir.

    Called from the recurring scaffolder for any template that declares
    `state_keys`. A no-op-safe write: a missing parent blackboard snapshots
    every key as `None`.
    """
    text = blackboard_path.read_text() if blackboard_path.is_file() else ""
    keys = parse_keys(text, list(state_keys))
    payload = {"parent": parent, "keys": keys}
    (task_dir / SNAPSHOT_FILE).write_text(json.dumps(payload, indent=2) + "\n")


def read_snapshot(task_dir: Path) -> StateSnapshot | None:
    """Load a period task's state snapshot, or `None` when it has none.

    `None` covers every non-recurring task and any recurring task that declares
    no `state_keys`. A corrupt or malformed snapshot is treated as absent
    rather than fatal — the check is advisory and must never break completion.
    """
    path = task_dir / SNAPSHOT_FILE
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    parent = data.get("parent")
    keys = data.get("keys")
    if not isinstance(parent, str) or not isinstance(keys, dict):
        return None
    return StateSnapshot(parent=parent, keys=keys)


def stale_keys(cfg: Config, snapshot: StateSnapshot) -> list[str]:
    """Declared keys whose current parent-blackboard value equals the snapshot.

    An unchanged value means the run finished without advancing that key.
    Returns the stale keys in their declared (snapshot) order; an empty list
    means every declared key moved (a healthy run).
    """
    blackboard = recurring_dir(cfg) / snapshot.parent / "blackboard.md"
    text = blackboard.read_text() if blackboard.is_file() else ""
    current = parse_keys(text, list(snapshot.keys))
    return [key for key, was in snapshot.keys.items() if current.get(key) == was]


__all__ = [
    "SNAPSHOT_FILE",
    "StateSnapshot",
    "parse_keys",
    "write_snapshot",
    "read_snapshot",
    "stale_keys",
]
