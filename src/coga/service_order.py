"""The order megalaunch services tasks in.

Two rules, in one sort key:

1. **Age.** Tasks are serviced oldest-first — the first `coga/log.md` line per
   ref, which is the draft/create entry. The log is committed content, so the
   ordering survives clones where file mtimes collapse to "all equal".
2. **Numbered sub-directories.** A sub-directory whose tasks are named
   `1-schema`, `2-migrate`, `3-cutover` runs in that number order. The prefix
   is a plain naming convention on the task directory — no flag, no
   frontmatter field, no config. You express the ordering with `mv`, the same
   verb you already use to organize `tasks/` (principle 3: reuse the shell the
   operator knows).

The two rules are composed so numbering never silently reshuffles work that
didn't ask for it:

- A sub-directory **opts in** by having at least one `<n>-` task. Only then
  are its tasks pulled into one contiguous block.
- That block keeps the directory's existing place in the age ordering: it is
  anchored at its oldest member, so a numbered sub-tree runs when its first
  task would have run, not sooner.
- Inside the block, numbered tasks run by number, then the unnumbered ones by
  age.
- Everything else — top-level tasks, and every sub-directory with no numbered
  task in it — keeps its own per-task age slot, exactly as before.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime

from coga.tasks import TaskRef

# A leading run of digits followed by `-`. Deliberately strict: `2fa-login`
# is not numbered (digits must be the whole first segment), and the number is
# read as an int so `02-` and `2-` are the same position.
_NUMBERED = re.compile(r"^(\d+)-")

# Sorts after every real timestamp: a task with no parseable log line goes
# last rather than first (a missing entry is not "infinitely old work").
_NO_TIMESTAMP = (True, datetime.min)


def leading_number(leaf: str) -> int | None:
    """The `N` in a `N-...` task leaf, or `None` when it isn't numbered."""
    match = _NUMBERED.match(leaf)
    return int(match.group(1)) if match else None


def _age(created: Mapping[str, datetime], slug: str) -> tuple[bool, datetime]:
    """Sortable creation time, with "unknown" ordered last."""
    ts = created.get(slug)
    return _NO_TIMESTAMP if ts is None else (False, ts)


def service_order(
    refs: Sequence[TaskRef],
    created: Mapping[str, datetime],
) -> list[TaskRef]:
    """`refs` in the order megalaunch services them (see the module docstring).

    `created` maps `id_slug` → creation timestamp (`first_activity_map`);
    refs missing from it sort last, stable by slug.
    """
    numbers = {ref.id_slug: leading_number(ref.slug) for ref in refs}
    # A sub-directory opts into number ordering by naming at least one of its
    # tasks `<n>-...`. Without this gate, grouping would reorder every
    # existing sub-tree in the repo — a change nobody asked for by renaming
    # anything.
    numbered_dirs = {
        ref.directory
        for ref in refs
        if ref.directory and numbers[ref.id_slug] is not None
    }

    def group(ref: TaskRef) -> tuple[int, str]:
        """The block a task is serviced in — its numbered directory, or itself.

        A task outside a numbered directory is its own single-member group, so
        it keeps its plain age slot and nothing about the sweep changes for it.
        """
        if ref.directory in numbered_dirs:
            return (0, ref.directory or "")
        return (1, ref.id_slug)

    # Each block runs where its oldest member would have run, so opting a
    # sub-tree into numbering reorders it internally without jumping the queue.
    anchors: dict[tuple[int, str], tuple[bool, datetime]] = {}
    for ref in refs:
        key = group(ref)
        age = _age(created, ref.id_slug)
        if key not in anchors or age < anchors[key]:
            anchors[key] = age

    _Key = tuple[
        tuple[bool, datetime], tuple[int, str], bool, int, tuple[bool, datetime], str
    ]

    def sort_key(ref: TaskRef) -> _Key:
        number = numbers[ref.id_slug]
        return (
            anchors[group(ref)],
            group(ref),
            number is None,  # unnumbered siblings run after the numbered ones
            number or 0,
            _age(created, ref.id_slug),
            ref.id_slug,
        )

    return sorted(refs, key=sort_key)


__all__ = ["leading_number", "service_order"]
