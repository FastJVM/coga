"""Repo-owned state for recurring parents, separate from their definitions.

A recurring job's *definition* (schedule, body, workflow, `ticket.py`, runbooks)
may come from the repo or from the installed package. Its cross-run *state*
always lives at the repo path `coga/recurring/<name>/ticket.md`, below the
blackboard fence, so period snapshots and publication keep their old paths.

For a package-backed job that path holds a **state-only carrier**: empty YAML
frontmatter, the reserved own-line marker, then exactly one blackboard fence
and the saved blackboard. It has no schedule, instructions, workflow or script.
A local parent with a genuine full definition remains its own state owner.

Shared by creation/snapshots, completion/publication, phone-home and audit
retention. The write path always derives from `cfg.repo_root`, never from a
resolved definition directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from coga.config import Config
from coga.paths import IGNORABLE_OVERRIDE_ENTRIES, recurring_dir
from coga.taskfile import BLACKBOARD_FENCE, TaskFileError, fence_count, read_blackboard


STATE_MARKER = "<!-- coga:recurring-state -->"
PARENT_TICKET = "ticket.md"
CARRIER_PREFIX = f"---\n{{}}\n---\n{STATE_MARKER}\n\n{BLACKBOARD_FENCE}"
"""Everything above (and including) the fence of a state-only carrier."""

RUNTIME_STATE_FILES: frozenset[str] = frozenset({"retires.md"})
"""Recognized runtime state that may sit beside a carrier (or alone).

Anything else in a parent directory is definition material: a `ticket.py` or
runbook beside a carrier is an incomplete fork, never silently inherited.
"""

# Directory kinds reported by `inspect_parent_dir`.
ABSENT = "absent"
DEFINITION = "definition"
CARRIER = "carrier"
STATE_ONLY = "state-only"
INCOMPLETE = "incomplete"


class RecurringStateError(Exception):
    """A recurring parent's repo state is malformed or ambiguous."""


@dataclass(frozen=True)
class ParentDir:
    """Classification of one `coga/recurring/<dir>/` entry."""

    path: Path
    kind: str
    problem: str | None = None
    state_files: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ticket_path(self) -> Path:
        return self.path / PARENT_TICKET

    @property
    def has_state(self) -> bool:
        return self.kind in {DEFINITION, CARRIER, STATE_ONLY}


def has_state_marker(text: str) -> bool:
    return any(line.rstrip("\r") == STATE_MARKER for line in text.split("\n"))


def carrier_problem(text: str) -> str | None:
    """Why `text` is not an exact state-only carrier, or None when it is."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith(CARRIER_PREFIX):
        return (
            f"a ticket marked {STATE_MARKER!r} must be exactly a state-only "
            f"carrier: `---`, `{{}}`, `---`, the marker line, a blank line, then "
            f"the blackboard fence; definition fields or prose above the fence "
            "are not allowed"
        )
    if fence_count(normalized) != 1:
        return "a state-only carrier needs exactly one blackboard fence"
    return None


def render_carrier(blackboard_region: str) -> str:
    """A carrier holding `blackboard_region` (the text after the fence)."""
    return CARRIER_PREFIX + blackboard_region


def is_carrier_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return has_state_marker(text) and carrier_problem(text) is None


def inspect_parent_dir(path: Path) -> ParentDir:
    """Classify a recurring parent directory without validating a definition.

    `definition` means an unmarked `ticket.md` (validated later as a template);
    `carrier` a marked, well-shaped one with only runtime state beside it;
    `state-only` recognized runtime state with no ticket; `incomplete` anything
    else that cannot be classified safely.
    """
    if not path.exists() and not path.is_symlink():
        return ParentDir(path, ABSENT)
    if path.is_symlink() or not path.is_dir():
        return ParentDir(path, INCOMPLETE, f"{path} is not a regular directory")
    names = sorted(
        child.name for child in path.iterdir()
        if child.name not in IGNORABLE_OVERRIDE_ENTRIES
    )
    state = tuple(n for n in names if n in RUNTIME_STATE_FILES)
    others = [n for n in names if n not in RUNTIME_STATE_FILES and n != PARENT_TICKET]
    ticket = path / PARENT_TICKET
    if PARENT_TICKET in names:
        if not ticket.is_file():
            return ParentDir(path, INCOMPLETE, f"{ticket} is not a regular file", state)
        try:
            text = ticket.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return ParentDir(path, INCOMPLETE, f"{ticket} is unreadable: {exc}", state)
        if not has_state_marker(text):
            return ParentDir(path, DEFINITION, None, state)
        problem = carrier_problem(text)
        if problem is not None:
            return ParentDir(path, INCOMPLETE, f"{ticket}: {problem}", state)
        if others:
            return ParentDir(
                path, INCOMPLETE,
                f"{path} holds a state-only carrier beside definition files "
                f"({', '.join(others)}); a carrier inherits nothing from them. "
                "Make it a full local override (copy the definition into "
                "ticket.md) or remove those files",
                state,
            )
        return ParentDir(path, CARRIER, None, state)
    if others:
        return ParentDir(
            path, INCOMPLETE,
            f"{path} has no ticket.md but holds definition files "
            f"({', '.join(others)}); restore ticket.md or remove the "
            "incomplete override",
            state,
        )
    if state:
        return ParentDir(path, STATE_ONLY, None, state)
    return ParentDir(path, ABSENT)


def active_parent_dir(cfg: Config, name: str) -> Path:
    return recurring_dir(cfg) / name


def parked_parent_dir(cfg: Config, name: str) -> Path:
    return recurring_dir(cfg) / f"_{name}"


def parent_state_path(cfg: Config, name: str, *, include_parked: bool = True) -> Path:
    """The repo-local ticket holding `name`'s cross-run state.

    The active `recurring/<name>/ticket.md` when it exists; otherwise, when
    `include_parked`, a unique parked `_<name>/ticket.md` (parking keeps state
    with the directory); otherwise the active path, where first use creates
    it. Two tickets (active and parked) are ambiguous cursors and raise.
    """
    active = active_parent_dir(cfg, name) / PARENT_TICKET
    parked = parked_parent_dir(cfg, name) / PARENT_TICKET
    active_exists = active.exists() or active.is_symlink()
    parked_exists = include_parked and (parked.exists() or parked.is_symlink())
    if active_exists and parked_exists:
        raise RecurringStateError(
            f"both {active} and {parked} exist; reconcile their state before "
            "running recurring/{name} (never guess which cursor is current)"
            .replace("{name}", name)
        )
    if parked_exists:
        return parked
    return active


def ensure_parent_state(
    cfg: Config, name: str, *, seed_ticket: Path | None,
) -> Path:
    """Return `name`'s state ticket, creating a carrier once on first use.

    `seed_ticket` is the selected *package* definition whose blackboard seeds
    the carrier; pass None for a local definition (it owns its own state, so
    nothing is created). Existing state is never reseeded, including an
    intentionally empty state region, and concurrent creation is detected by
    an exclusive create rather than overwritten. A pending audit-log mutation
    receipt blocks initialization.
    """
    path = parent_state_path(cfg, name)
    if path.exists() or path.is_symlink() or seed_ticket is None:
        return path
    from coga.log_transaction import ensure_clear

    ensure_clear(cfg)
    try:
        region = read_blackboard(seed_ticket)
    except (OSError, UnicodeError, TaskFileError) as exc:
        raise RecurringStateError(
            f"cannot seed recurring/{name} state from {seed_ticket}: {exc}"
        ) from exc
    data = render_carrier(region).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o644)
    except FileExistsError:
        return path
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    return path


__all__ = [
    "ABSENT",
    "CARRIER",
    "DEFINITION",
    "INCOMPLETE",
    "STATE_ONLY",
    "STATE_MARKER",
    "CARRIER_PREFIX",
    "RUNTIME_STATE_FILES",
    "ParentDir",
    "RecurringStateError",
    "active_parent_dir",
    "carrier_problem",
    "ensure_parent_state",
    "has_state_marker",
    "inspect_parent_dir",
    "is_carrier_file",
    "parent_state_path",
    "parked_parent_dir",
    "render_carrier",
]
