---
name: coga/blackboard
description: The contract for writing to a ticket blackboard — how the fence is located and why only an anchored line match is safe, which sections a pass appends to and which it rewrites in place, what happens to content a later pass replaces, and the concurrency limits of shipped writers. Attach to any ticket whose work writes to a blackboard programmatically.
---

# Writing to a ticket blackboard

The blackboard is the region of a task's `.md` ticket (or a directory task's
`ticket.md`) below the `<!-- coga:blackboard -->` fence: the free-form working
memory shared by human and agent. Its live state composes into the next launch
alongside the ticket's Description and Context; `coga/architecture` owns that
projection. This context is the writer's contract. It describes what shipped
code and the shipped contexts already do; where this context and the source
disagree, the source wins.

`coga validate` already checks fence count and draft-authoring readiness and
warns about blackboard size. It does not check whether an edit respected the
boundary or a section's append/rewrite convention. This context adds no
validation; writers must still scope their edits correctly.

## The fence is a boundary

The separator is one HTML-comment-shaped line, `BLACKBOARD_FENCE` in
`coga.taskfile`:

```
<!-- coga:blackboard -->
```

**Locate it only as an anchored line match.** The shipped matcher is

```python
_FENCE_RE = re.compile(rf"^{re.escape(BLACKBOARD_FENCE)}[ \t]*\r?$", re.MULTILINE)
```

Three details the obvious paraphrase gets wrong:

- It matches the fence **only on a line of its own**, so a ticket body that
  *mentions* the fence string inline — a ticket about this very format, for
  instance — is not mistaken for a region split. Leading indentation is not
  accepted. The matcher does not parse Markdown: an own-line fence inside a
  code block still counts.
- The line **tolerates trailing spaces or tabs and a CRLF carriage return**. It
  is not "a line equal to the fence and nothing else"; raw-byte
  compare-and-swap readers do not apply universal-newline translation, so the
  carriage return is accepted explicitly.
- The region is everything **after the match** — any line-ending LF after the
  fence is the region's first byte; a fence at EOF has an empty region — with
  leading whitespace preserved, so
  `read_blackboard` and `replace_blackboard` round-trip byte-for-byte.

**Never locate the fence by substring.** `text.split(BLACKBOARD_FENCE)`,
`.find`, `.partition`, or an unanchored `sed`/`grep` will match the string
where it is quoted in prose and truncate the body. This is not hypothetical:
two recorded corruptions have this exact shape — a Dream run's dedup pass
matched a heading mentioned in a ticket *body* and truncated 258 lines of it,
and a pass authoring the ticket behind this context split on the first
occurrence of the fence *string* and truncated the body again. Both were
recoverable only from git.

**Exactly one fence, and fail loud otherwise.** `fence_count()` counts own-line
matches; `split_body()` and `read_blackboard()` raise `TaskFileError` on zero
or more than one, rather than guessing where the blackboard starts — a wrong
split silently folds blackboard text into the prompt's body layer or the
reverse. Two exceptions, both deliberate:

- `split_body(blackboard_required=False)` returns `(body, None)` for a
  fence-less file. **Bootstrap tickets legitimately carry no fence**: they are
  stateless launch targets with no blackboard.
  `read_blackboard(blackboard_required=False)` returns `""` in that case.
  Both still reject multiple fences. Normal task tickets require one fence.
- `upsert_blackboard()` appends a fence and region to a file that has none, for
  writers that must not fail on a hand-authored recurring template predating
  the single-file format. More than one fence still fails loud.

**Scope each edit to its intended region.** The two write paths preserve other
regions from the version they read; that alone is not a concurrency guarantee:

- **Frontmatter and step writers** (`coga bump`, `coga mark`, …) go through
  `coga.ticket.Ticket`, which re-renders the YAML and retains its loaded body,
  fence and blackboard included. A status write preserves that loaded
  blackboard, not necessarily the latest blackboard on disk.
- **Blackboard writers** call `replace_blackboard`, which byte-splices only the
  region after the fence and leaves the frontmatter and body bytes above it
  untouched, so a blackboard write never reformats the YAML.

Compute every blackboard transform on the region returned by
`read_blackboard`, never on whole-file text. A `## Heading` pattern aimed at a
blackboard section will happily match the same heading in the body; scoping the
transform to the region is what makes that impossible.

**What may be edited above the fence.** Per the base prompt: the body sections
and the `contexts:` frontmatter list, and nothing else. Every other frontmatter
field — `status`, `step`, `workflow`, `owner`, `assignee`, `skills`,
`secrets`, and any repo extension field — is owned by CLI commands and humans;
editing one silently reroutes later launches. A specialized authoring skill may
grant an explicit exception; absent that, the allowlist holds.

Note also what composes: layer 6 of a launch prompt carries `## Description`,
`## Context`, and the live blackboard with an archive pointer, and nothing else. Any other `##`
section above the fence is dropped silently. Content a later step must read
belongs under one of those two headings or on the blackboard (see
`coga/architecture`).

## Append or rewrite in place

There are three regimes already in use. Match the one the section belongs to;
do not invent a fourth.

- **Live state — rewrite in place.** A section holding one current value per
  named line. `## Dev` is canonical (`dev/code`): `branch:`, `worktree:`, and
  `pr:` are machine-readable fields, and a superseded value is simply
  replaced. The old value has no readers.
- **Record — append, never delete.** A section whose earlier entries stay true.
  `## Superseded designs` (`dev/code`) appends dated entries oldest to newest;
  `## Blockers` appends one checkbox line per ask, and `coga unblock` marks the
  existing line `- [x]` and appends an indented `resolved:` line rather than
  removing it.
- **Authoring scratch — append during authoring, synthesize before launch.**
  The `bootstrap/ticket` skill's final cleanup folds durable substance from
  `## Evaluator review`, `## Ticket authoring notes`, and `## Proposals` into
  the body. For a **draft**, it preserves `## Superseded designs` and every
  dated entry, then resets the rest to the stock placeholder, leaving no empty
  authoring headings. When authoring an **existing non-draft** ticket, it
  removes only the authoring sections it used and preserves unrelated blockers,
  dev notes, production notes, and handoff notes. These are authoring actions;
  activation does not synthesize or clear notes automatically.

Draft activation checks readiness in `coga.blackboard`, using
`PRELAUNCH_AUTHORING_HEADINGS` and `_is_stock_blackboard`. Remaining authoring
sections or large custom scratchpads make `coga mark active` and launch-time
auto-activation refuse; `coga validate` reports the same error. A
`## Production notes` section explicitly marks the remaining blackboard as
intentional launch material and exempts it from that check.
`## Superseded designs` is separately excluded without exempting unrelated
notes. Later reactivation does not repeat this first-launch check. An
`## Evaluator review` written by a live workflow step remains working state
for the following owner gate, not draft-authoring residue (`coga/current-direction`).

`append_to_section_text` / `append_to_section` in `coga.blackboard` are the
shipped answer to "append into a named section": a section runs from its `## `
heading to the next one, the entry is inserted at its end, and a missing
section is appended at the end of the region.

Two constraints shape the choice:

- **The live blackboard is composed into the next prompt**, so it must stay small;
  `coga/log.md` is never composed and may grow without bound.
  Working state the next run must read goes on the blackboard; lifecycle
  history goes in the log. `blackboard_size_warning` warns above
  `BLACKBOARD_WARN_BYTES` (32 KiB), measuring live notes and the archive pointer
  rather than stored design history. See `coga/architecture` for composition
  and for the remedy (sibling attachments and unattached contexts).
- **CLI audit history lives in the log.** The recurring scan's
  serviced-period ledger lives in the union-merged `coga/log.md` precisely so
  that a co-writer rewriting a region of a template's blackboard cannot destroy
  an appended line. CLI commands write that log; agents do not edit it.
  Findings and decisions remain blackboard working memory, with durable
  requirements folded into the ticket body.

## What happens to content a later pass replaces

- **A replaced live value leaves the current section.** `## Dev` records
  current linkage; committed earlier values remain in git history.
  `coga/log.md` records CLI lifecycle history, not every manual field edit.
- **A replaced design is not gone.** Move the abandoned direction below the
  fence into exactly one `## Superseded designs` section, as a dated entry with
  `Superseded by:` and `Reason:` lines and retained headings nested at `####`
  or deeper. The body keeps at most a one-line pointer to it. Do not scatter
  the same history under improvised headings. Keep current decision rationale
  in live notes, since only an archive pointer composes. `dev/code` owns the
  full shape.
- **Resolving a blocker preserves the ask.** `coga unblock` marks it resolved
  with its answer appended, so asks and resolutions stay readable in place.
- **A period task's own blackboard disappears** at Dream's retro cleanup, so
  anything durable it learned must be written where it survives: a reusable
  gotcha under `## Gotchas` (extracted into a knowledge PR before the delete),
  and last-run state on the **parent recurring template's** blackboard, which
  persists across every run. See `coga/period-task` and `coga/recurring`.

## Concurrent writers

A launched agent and a shipped command or sweep writer can touch the same
ticket at the same time. **There is deliberately no ownership mutex.** From
`coga/architecture` ("Status is the signal"), which is the authority here:

> The failure mode of two divergent workers (two blackboard edits, two PR
> branches) is visible and recoverable in git; the cost of a hard ownership
> mutex (stale lock state, `--force` flags, orphan-lock cleanup) is not.

What does exist is a narrow **state lock**, and "shipped blackboard writers
use the same read/transform/compare/write boundary." Read that passage for the
lock's full scope; in code it is `update_blackboard_under_barrier`, which
holds `git.state_lock`, captures the live bytes, and compares them again at
replacement via `expected_bytes` — raising `TaskFileError` if a comparison
detects a change, rather than overwriting it. This detects intervening edits
even from an editor outside the lock; it does not lock that editor.

Lifecycle writes have a narrower guarantee. `git.write_ticket` serializes the
write but does not reread the body. Ordinary `coga mark active` loads a
`Ticket` before taking that lock. A blackboard update that finishes between
that load and the lifecycle write can therefore be overwritten by the old
`Ticket.body`. Preserving separate regions is safe without an intervening
edit; concurrent preservation requires the read/transform/write to share the
lock or an unchanged-byte check covering the read. The ordinary lifecycle
path does not yet provide that guarantee; megalaunch's strict writes do, by
comparing the exact source bytes under the lock immediately before writing.

For a programmatic section append, call `append_to_section_text` with the
heading and entry inside the transform passed to
`update_blackboard_under_barrier`. The low-level
`append_to_section` and `replace_blackboard` helpers do not acquire the
lock themselves; command and recipe callers own admission and supply the
captured `expected_bytes` when using those helpers directly.

Atomicity is not a lock. As `coga/patterns` puts it under "Durability and
concurrency", a rename-based atomic write buys **crash-safety** — a reader sees
the old or the new complete file — and correctness comes from the shape of the
write, not from process serialization. For a blackboard writer that means:

- Read the region immediately before writing it. Do not hold a copy across a
  long step and write it back wholesale; everything another writer appended in
  between disappears.
- Prefer appending to a named section over rewriting the whole region.
- Keep the write as small as the change: a section, not the file.
- Route programmatic writes through the shipped helpers rather than
  hand-rolling a splice.

**Out of scope: cross-checkout reconciliation.** This section covers a launched
agent versus a command or sweep writer in one checkout. Two checkouts diverging
is the live subject of `detect-stranded-ticket-writes-across-checkouts`; that
design is still in flight, and cross-checkout and cross-machine coordination
comes from exact Git compare-and-swap publication in the meantime.

## What this context does not cover

- **New enforcement or writer behavior changes.** Existing checks are
  described above; adding checks for edit discipline is a separate job.
- **Cross-checkout reconciliation**, per above.
- **Frontmatter semantics** beyond the edit allowlist — see the base prompt and
  `coga/architecture`.
- **The `## Dev` and `## Superseded designs` section shapes** in detail — those
  belong to `dev/code`, which this context generalizes from rather than
  restates.
