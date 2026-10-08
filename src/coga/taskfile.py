"""Single-file task format — frontmatter + body + blackboard in one `ticket.md`.

A task's `ticket.md` carries three regions:

1. YAML frontmatter (`--- ... ---`), parsed by `coga.ticket.Ticket`.
2. the body (`## Description`, `## Context`, plus any spec sections).
3. the blackboard — the freeform working state shared by human and agent.

The body and the blackboard are separated by exactly one fence line::

    <!-- coga:blackboard -->

The fence is machine-findable and HTML-comment-shaped, so it renders invisibly
in any markdown viewer while staying trivially greppable. The append-only audit
log is **not** a region here: it lives in one repo-global `coga/log.md`
(see `coga.logfile`). That is the whole point of the single-file format — the
unbounded thing (history) is the one file compose never reads, so the per-task
file stays small and bounded (frontmatter + body + blackboard) and the prompt
composer goes back to "read the small task file, ignore the log".

Two write paths share one file without clobbering each other:

- **Frontmatter / step writers** (`coga bump`, `coga mark`, …) go through
  `coga.ticket.Ticket`, which re-renders the YAML and treats the whole body
  (fence + blackboard included) as opaque bytes — so a status write preserves
  the blackboard verbatim.
- **Blackboard writers** (`append_to_section`, recurring
  high-water) call `replace_blackboard`, which byte-splices only the region
  after the fence and leaves the frontmatter + body bytes above it untouched —
  so a blackboard write never reformats the frontmatter. The primitive remains
  config-free; shipped command/recipe writers wrap their read-transform-write
  in `blackboard.update_blackboard_under_barrier` (or an explicit equivalent)
  so the mutation cannot cross held-child admission.

Bootstrap tickets (package `bootstrap/<name>/ticket.md` resources) are
stateless launch targets with no blackboard; they legitimately have no fence.
Pass `blackboard_required=False` to parse them without failing loud.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Iterator
from pathlib import Path

from coga.atomicio import atomic_write_text
from coga.ticket import Ticket

# The single machine-findable separator between the body and the blackboard.
# HTML-comment shaped so it is invisible in rendered markdown but trivially
# greppable; the only structural marker the single-file format adds.
BLACKBOARD_FENCE = "<!-- coga:blackboard -->"

# Match the fence only as a line of its own (optionally trailing whitespace), so
# a ticket body that *mentions* the fence string inline — e.g. a ticket about
# this very format — is not mistaken for a region split. Raw-byte CAS readers do
# not apply universal-newline translation, so accept the carriage return in a
# CRLF fence line explicitly.
_FENCE_RE = re.compile(
    rf"^{re.escape(BLACKBOARD_FENCE)}[ \t]*\r?$",
    re.MULTILINE,
)


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


def read_blackboard(
    path: Path,
    *,
    blackboard_required: bool = True,
    expected_bytes: bytes | None = None,
) -> str:
    """Return the blackboard region of `path` (text after the fence marker).

    Returns ``""`` for a fence-less file when `blackboard_required` is False
    (bootstrap tickets have no blackboard). The byte-faithful inverse of
    `replace_blackboard`: ``replace_blackboard(p, read_blackboard(p))`` is a
    no-op.
    """
    raw = path.read_bytes()
    if expected_bytes is not None and raw != expected_bytes:
        raise TaskFileError(
            f"ticket changed before its blackboard update: {path}"
        )
    text = raw.decode("utf-8")
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


def replace_blackboard(
    path: Path,
    new_blackboard: str,
    *,
    expected_bytes: bytes | None = None,
) -> bytes:
    """Replace only the blackboard region of `path`, leaving the rest verbatim.

    Byte-splices the file: everything up to and including the fence marker is
    preserved exactly (frontmatter + body bytes untouched — the YAML is **not**
    re-rendered), and the region after the fence is replaced with
    `new_blackboard`. Atomic so a crash mid-write can't truncate the ticket.
    """
    raw = path.read_bytes()
    if expected_bytes is not None and raw != expected_bytes:
        raise TaskFileError(
            f"ticket changed before its blackboard update: {path}"
        )
    text = raw.decode("utf-8")
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
    rendered = text[: matches[0].end()] + new_blackboard
    atomic_write_text(path, rendered)
    return rendered.encode("utf-8")


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


# The `##` sections above the fence that compose into launch prompts
# (`coga/tickets`, Body regions). `## PR` is the one deliberately separate
# operational section: legacy PR preparation `open_pr` reads, never intent.
COMPOSED_SECTIONS = ("description", "context")
OPERATIONAL_SECTIONS = ("pr",)

# A level-2 ATX heading line, bare `##` included (it still ends a section).
# CommonMark: up to three spaces of indent, and an optional closing `#` run
# that follows whitespace (`## Description ##`) is not part of the text.
_SECTION_HEADING_LINE_RE = re.compile(
    r"^ {0,3}##(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$"
)
_CODE_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


@dataclass(frozen=True)
class BodySection:
    """One `## <heading>` section of a markdown body, as offsets into it."""

    heading: str
    start: int
    content_start: int
    end: int

    @property
    def key(self) -> str:
        return self.heading.lower()


def markdown_lines(text: str) -> Iterator[tuple[str, bool]]:
    """Yield each line of `text` (ends kept) with whether it is code-fenced.

    Fence marker lines count as fenced. A backtick or tilde run of three or
    more opens a fence (a backtick opener's info string may not contain a
    backtick) and the same character, at least as long, with nothing after it
    closes it. An opener never closed is plain text, not a fence to EOF: a
    stray or truncated example must not hide the `## Context` heading below it.
    """
    lines = text.splitlines(keepends=True)
    unclosed: set[int] = set()
    while True:
        flags, opener = _fence_flags(lines, unclosed)
        if opener is None:
            yield from zip(lines, flags)
            return
        unclosed.add(opener)


def _fence_flags(
    lines: list[str], unclosed: set[int]
) -> tuple[list[bool], int | None]:
    """Fenced flags per line, and the index of a fence left open at EOF."""
    flags: list[bool] = []
    fence, opener = "", None
    for i, line in enumerate(lines):
        marker = _CODE_FENCE_RE.match(line.rstrip("\r\n"))
        if fence:
            if (
                marker
                and marker.group(1)[0] == fence[0]
                and len(marker.group(1)) >= len(fence)
                and not marker.group(2).strip(" \t")
            ):
                fence = ""
            flags.append(True)
        elif (
            marker
            and i not in unclosed
            and (marker.group(1)[0] == "~" or "`" not in marker.group(2))
        ):
            fence, opener = marker.group(1), i
            flags.append(True)
        else:
            flags.append(False)
    return flags, opener if fence else None


def body_sections(text: str) -> list[BodySection]:
    """Every level-2 section of `text`, in order, skipping code-fenced lines.

    The one section parser for ticket bodies: compose, validate, `open_pr` and
    create-time description checks all read it, so a heading inside a backtick
    or tilde fenced example is text to every one of them. A section runs from
    its heading line to the next one or EOF; `###` and deeper stay inside it.
    Callers split off the blackboard first (`split_body`) when they mean the
    ticket body above the fence.
    """
    sections: list[BodySection] = []
    heading: str | None = None
    start = content_start = offset = 0
    for line, fenced in markdown_lines(text):
        match = None if fenced else _SECTION_HEADING_LINE_RE.match(line.rstrip("\r\n"))
        if match:
            if heading is not None:
                sections.append(BodySection(heading, start, content_start, offset))
            heading = (match.group(1) or "").strip()
            start, content_start = offset, offset + len(line)
        offset += len(line)
    if heading is not None:
        sections.append(BodySection(heading, start, content_start, len(text)))
    return sections


def uncomposed_sections(body_above: str) -> list[str]:
    """Headings of `##` sections above the fence that no launch prompt carries.

    Excludes the composed sections and the operational `## PR`. Returned as
    written, in order, so a warning can name each one.
    """
    allowed = COMPOSED_SECTIONS + OPERATIONAL_SECTIONS
    return [s.heading for s in body_sections(body_above) if s.key not in allowed]


def uncomposed_sections_message(headings: list[str]) -> str:
    """The shared validate/launch wording for `uncomposed_sections` output."""
    named = ", ".join(f"`## {h}`" if h else "a bare `##`" for h in headings)
    return (
        f"ticket body has sections no launch prompt carries: {named}. Only "
        "`## Description` and `## Context` above the blackboard fence are "
        "composed, and each section ends at the next `##` heading. Demote "
        "each heading to `###` under `## Description` or `## Context`, or "
        "move working notes below the blackboard fence"
    )


def uncomposed_sections_warning(ticket_path: Path) -> str | None:
    """`uncomposed_sections_message` for a ticket file, or None when clean."""
    try:
        body = read_task_file(ticket_path).body
    except (FileNotFoundError, TaskFileError):
        return None
    headings = uncomposed_sections(body)
    return uncomposed_sections_message(headings) if headings else None


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
    "COMPOSED_SECTIONS",
    "OPERATIONAL_SECTIONS",
    "BodySection",
    "body_sections",
    "markdown_lines",
    "uncomposed_sections",
    "uncomposed_sections_message",
    "uncomposed_sections_warning",
]
