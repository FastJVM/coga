---
name: coga-dev/internals/blackboard-io
description: How Coga's ticket IO parses and writes a ticket file — the fence matcher, body-section parser, superseded-design projection, stock-blackboard comparison, the creation template, and the writer races the shipped helpers do and do not close.
---

# Ticket body and blackboard IO

The user contracts are [coga/tickets](../../../coga/tickets/SKILL.md) (body
regions) and [coga/blackboard](../../../coga/blackboard/SKILL.md) (writer
rules). This page holds the parser and writer details behind them, in
`src/coga/taskfile.py`, `src/coga/blackboard.py`, and `src/coga/create.py`.
Where the source disagrees with this page, the source wins.

## The fence

`taskfile._FENCE_RE` matches `BLACKBOARD_FENCE` only as a whole line: no
leading indentation, optional trailing spaces/tabs, optional `\r`. It does not
parse Markdown, so an own-line fence inside a code block counts, while an
inline mention does not. The region starts right after the match (a fence at
EOF gives an empty region) and `read_blackboard` / `replace_blackboard`
round-trip it byte-for-byte.

`split_body` and `read_blackboard` raise `TaskFileError` on zero or several
fences. Bootstrap tickets legitimately have none (`blackboard_required=False`);
`upsert_blackboard` appends a fence to a fence-less legacy recurring template.
Substring fence searches have corrupted tickets twice; recovery came from Git.

Frontmatter and step writers go through `coga.ticket.Ticket` and keep the body
they loaded, which may not be the latest on disk. Blackboard writers use
`replace_blackboard`, which splices only the region and never reformats YAML.
`blackboard.append_to_section_text` / `append_to_section` append into a named
section (heading to next `## `), creating it at the end if missing.

## Body sections

Compose, validate, `open_pr`'s request snapshot and create-time checks share
one parser, `taskfile.body_sections`: a `##` inside a backtick or tilde code
fence is text, a fence never closed is not a fence, a heading may be indented
up to three spaces and carry a closing `#` run, and the region below the
blackboard fence is never read as body sections. `coga validate`,
`coga launch` and `--prompt-report` share the uncomposed diagnostic from
`taskfile.uncomposed_body_message`.

Coga deliberately composes only Description and Context: an allowlist of
intent names would drop the next unlisted one, and composing every heading
would pull operational material into intent. `## PR` above the fence is
legacy PR preparation read by `open_pr`, never composed.

## Superseded-design projection

`blackboard.blackboard_for_prompt` leaves stored history unchanged and
includes only a pointer to it. Composition, draft readiness, and blocker
reading share `_without_superseded_designs`: only the exact, unindented,
case-sensitive heading starts an archive (trailing spaces/tabs allowed). It
ends at the next ATX `#` or `##` heading outside a code fence, or EOF. Deeper
headings and Setext underlines do not end it; fenced examples, prose mentions
and similar headings do not start it. Every exact section is omitted if
duplicates exist.

The projection treats an unmatched code-fence opener as extending to EOF, so
headings after it cannot start or end an archive. `parse_blockers_text`
applies the projection first, then uses `taskfile.markdown_lines` to skip
closed fenced examples in the live text. That reader treats unmatched openers
as ordinary text, so a stray opener in live notes cannot hide a genuine
blocker. `read_blockers` / `open_blockers`, launch and megalaunch eligibility,
and the composed blocker preamble all use this interpretation.

## Stock blackboard and activation readiness

`render_blackboard` fills resource `blackboard.md` with `{task_title}`.
Tickets created before a repo override keep the packaged stub, so
`_is_stock_blackboard` counts the packaged stub, the raw override, and the
title-rendered override all as stock. Comparisons exclude
`## Superseded designs` from both the ticket and the template. Activation
refuses `PRELAUNCH_AUTHORING_HEADINGS` sections or a large custom scratchpad
before any freeze, status change, log, post, composition or spawn.
`blackboard_size_warning` measures live notes plus the archive pointer against
`BLACKBOARD_WARN_BYTES`.

## Creation template

The ordinary `create_task` path renders the `ticket.md` body resource (repo
override first), replacing `{description}` with the supplied text. Frontmatter
is generated from validated arguments; the configured `blackboard.md` supplies
working space. Resource reads and the exactly-one `{description}` check happen
before creating the destination. Callers supplying an explicit `body` (such
as recurring periods) keep that body.

The guide sits in an HTML comment under `## Context`, so `Ticket.render`
preserves it when rewriting YAML and composition includes it. Description
stays empty until intent is supplied, so `empty-description` still works.
Examples use indentation rather than code fences: an unfinished fence in a
supplied Description must not close against an example and swallow the
Context heading. Existing tickets are not migrated; a repo override owns its
own instructions.

## Writer races

`update_blackboard_under_barrier` holds `git.state_lock`, captures the bytes,
and at replacement compares them again via `expected_bytes`, raising
`TaskFileError` rather than overwriting an intervening edit. It detects, but
cannot lock, an outside editor. The low-level helpers take no lock; callers
own admission and pass `expected_bytes`.

Lifecycle writes are weaker: `git.write_ticket` serializes but does not
reread, and `coga mark active` loads the `Ticket` before the lock, so a
blackboard update landing in between can be overwritten by the old body.
Megalaunch's strict writes compare source bytes under the lock and are safe.
Atomic rename gives crash-safety, not serialization
([coga-dev/patterns](../../patterns/SKILL.md)).
