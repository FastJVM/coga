"""Single-file task format — frontmatter + body + blackboard in one `ticket.md`.

A task's `ticket.md` carries three regions:

1. YAML frontmatter (`--- ... ---`), parsed by `coga.ticket.Ticket`.
2. the body (`## Description`, `## Context`, plus any spec sections).
3. the blackboard — the freeform working state shared by human and agent.

The body and the blackboard are separated by exactly one fence line::

    <!-- coga:blackboard -->

The fence is machine-findable and HTML-comment-shaped, so it renders invisibly
in any markdown viewer while staying trivially greppable. The append-only audit
log is **not** a region here: it lives in one repo-global `coga-os/log.md`
(see `coga.logfile`). That is the whole point of the single-file format — the
unbounded thing (history) is the one file compose never reads, so the per-task
file stays small and bounded (frontmatter + body + blackboard) and the prompt
composer goes back to "read the small task file, ignore the log".

Two write paths share one file without clobbering each other:

- **Frontmatter / step writers** (`coga bump`, `coga mark`, …) go through
  `coga.ticket.Ticket`, which re-renders the YAML and treats the whole body
  (fence + blackboard included) as opaque bytes — so a status write preserves
  the blackboard verbatim.
- **Blackboard writers** (`append_to_section`, the spool, recurring
  high-water) call `replace_blackboard`, which byte-splices only the region
  after the fence and leaves the frontmatter + body bytes above it untouched —
  so a blackboard write never reformats the frontmatter.

Bootstrap tickets (`coga-os/bootstrap/<name>/ticket.md`) are stateless launch
targets with no blackboard; they legitimately have no fence. Pass
`blackboard_required=False` to parse them without failing loud.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from coga.atomicio import atomic_write_text
from coga.ticket import Ticket

# The single machine-findable separator between the body and the blackboard.
# HTML-comment shaped so it is invisible in rendered markdown but trivially
# greppable; the only structural marker the single-file format adds.
BLACKBOARD_FENCE = "<!-- coga:blackboard -->"

# Match the fence only as a line of its own (optionally trailing whitespace), so
# a ticket body that *mentions* the fence string inline — e.g. a ticket about
# this very format — is not mistaken for a region split.
_FENCE_RE = re.compile(rf"^{re.escape(BLACKBOARD_FENCE)}[ \t]*$", re.MULTILINE)


def _fence_matches(text: str) -> list[re.Match[str]]:
    return list(_FENCE_RE.finditer(text))


def fence_count(text: str) -> int:
    """Number of blackboard fence *lines* in `text` (own-line matches only)."""
    return len(_fence_matches(text))


class TaskFileError(Exception):
    """Raised when a task `ticket.md` is malformed for the single-file format.

    Specifically: a normal task ticket missing its blackboard fence, or one
    carrying more than one. Fail-loud rather than guessing where the blackboard
    starts — a wrong split would silently fold blackboard text into the prompt's
    body layer (or vice versa).
    """


@dataclass
class TaskFile:
    """A parsed task `ticket.md`: frontmatter + body-above-fence + blackboard."""

    ticket: Ticket
    body: str
    blackboard: str | None


def split_body(body: str, *, blackboard_required: bool = True) -> tuple[str, str | None]:
    """Split a ticket body into ``(body_above_fence, blackboard_below_fence)``.

    `body` is everything after the YAML frontmatter (i.e. `Ticket.body`). The
    return is the text above the fence and the blackboard region below it
    (everything after the fence marker, leading whitespace preserved so the
    split round-trips with `replace_blackboard`).

    Fail-loud when the fence is missing or duplicated and `blackboard_required`.
    When not required (bootstrap tickets), a fence-less body returns
    ``(body, None)``.
    """
    matches = _fence_matches(body)
    if not matches:
        if blackboard_required:
            raise TaskFileError(
                "ticket.md is missing its blackboard fence "
                f"({BLACKBOARD_FENCE!r}). A task ticket must carry exactly one "
                "fence (on its own line) separating the body from the blackboard."
            )
        return body, None
    if len(matches) > 1:
        raise TaskFileError(
            f"ticket.md carries {len(matches)} blackboard fences "
            f"({BLACKBOARD_FENCE!r}); exactly one is allowed."
        )
    m = matches[0]
    return body[: m.start()], body[m.end():]


def read_task_file(path: Path, *, blackboard_required: bool = True) -> TaskFile:
    """Parse a `ticket.md` into frontmatter, body-above-fence, and blackboard."""
    ticket = Ticket.read(path)
    above, blackboard = split_body(ticket.body, blackboard_required=blackboard_required)
    return TaskFile(ticket=ticket, body=above, blackboard=blackboard)


def read_blackboard(path: Path, *, blackboard_required: bool = True) -> str:
    """Return the blackboard region of `path` (text after the fence marker).

    Returns ``""`` for a fence-less file when `blackboard_required` is False
    (bootstrap tickets have no blackboard). The byte-faithful inverse of
    `replace_blackboard`: ``replace_blackboard(p, read_blackboard(p))`` is a
    no-op.
    """
    text = path.read_text(encoding="utf-8")
    matches = _fence_matches(text)
    if not matches:
        if blackboard_required:
            raise TaskFileError(
                "ticket.md is missing its blackboard fence "
                f"({BLACKBOARD_FENCE!r})."
            )
        return ""
    if len(matches) > 1:
        raise TaskFileError(
            f"ticket.md carries {len(matches)} blackboard fences "
            f"({BLACKBOARD_FENCE!r}); exactly one is allowed."
        )
    return text[matches[0].end():]


def replace_blackboard(path: Path, new_blackboard: str) -> None:
    """Replace only the blackboard region of `path`, leaving the rest verbatim.

    Byte-splices the file: everything up to and including the fence marker is
    preserved exactly (frontmatter + body bytes untouched — the YAML is **not**
    re-rendered), and the region after the fence is replaced with
    `new_blackboard`. Atomic so a crash mid-write can't truncate the ticket.
    """
    text = path.read_text(encoding="utf-8")
    matches = _fence_matches(text)
    if not matches:
        raise TaskFileError(
            "ticket.md is missing its blackboard fence "
            f"({BLACKBOARD_FENCE!r}); cannot replace the blackboard region."
        )
    if len(matches) > 1:
        raise TaskFileError(
            f"ticket.md carries {len(matches)} blackboard fences "
            f"({BLACKBOARD_FENCE!r}); exactly one is allowed."
        )
    atomic_write_text(path, text[: matches[0].end()] + new_blackboard)


def upsert_blackboard(path: Path, new_blackboard: str) -> None:
    """Set the blackboard region of `path`, adding a fence if there isn't one.

    Like `replace_blackboard`, but tolerant of a file (or template `ticket.md`)
    that has no fence yet: the fence + region are appended after the existing
    content. Used by writers that must not fail on a hand-authored recurring
    template that predates the single-file format. A file with >1 fence still
    fails loud.
    """
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    matches = _fence_matches(text)
    if len(matches) > 1:
        raise TaskFileError(
            f"ticket.md carries {len(matches)} blackboard fences "
            f"({BLACKBOARD_FENCE!r}); exactly one is allowed."
        )
    if matches:
        new_text = text[: matches[0].end()] + new_blackboard
    else:
        head = text.rstrip("\n")
        sep = "\n\n" if head else ""
        new_text = f"{head}{sep}{BLACKBOARD_FENCE}\n\n{new_blackboard.lstrip(chr(10))}"
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, new_text)


def join_task_body(body_above: str, blackboard_text: str) -> str:
    """Build a full ticket body: body-above-fence + fence + blackboard region.

    Used by scaffolding (`coga create`) to write one `ticket.md` from a body
    skeleton and a rendered blackboard. The result is what `Ticket(body=...)`
    stores; `split_body` round-trips it back into its two regions.
    """
    above = body_above.rstrip("\n")
    bb = blackboard_text.lstrip("\n")
    return f"{above}\n\n{BLACKBOARD_FENCE}\n\n{bb}"


__all__ = [
    "BLACKBOARD_FENCE",
    "fence_count",
    "TaskFileError",
    "TaskFile",
    "split_body",
    "read_task_file",
    "read_blackboard",
    "replace_blackboard",
    "upsert_blackboard",
    "join_task_body",
]
