---
name: coga/blackboard
description: The writer's contract for a ticket blackboard — locating the fence, scoping edits, live sections and superseded designs, the draft-activation readiness check, size limits and their remedy, and safe concurrent writes. Attach to tickets whose work writes blackboards programmatically.
---

# Writing to a ticket blackboard

The blackboard is everything below the `<!-- coga:blackboard -->` fence in a
ticket: working memory shared by human and agent and carried between
stateless sessions. Its live state is composed into every launch
([coga/prompt-composition](../prompt-composition/SKILL.md)); `coga/log.md`,
written only by CLI commands, holds lifecycle history and is never composed.
Working state the next run must read goes here and stays small; history goes
in the log.

## The fence

The fence counts only as a whole line: no leading indentation, optional
trailing whitespace. Markdown is not parsed, so an own-line fence inside a
code block counts, while an inline mention does not.

- **Never locate the fence by substring** (`split`, `find`, `partition`,
  unanchored `grep`/`sed`): a quoted fence in prose truncates the body.
- **Exactly one fence.** Readers fail on zero or several. Bootstrap command
  tickets legitimately have none.
- **Scope each edit.** Compute every transform on the blackboard region, never
  on whole-file text, so a `## Heading` pattern cannot hit the body, and never
  reformat the YAML while writing below the fence.

What may be edited above the fence is owned by
[coga/tickets](../tickets/SKILL.md) (agents: `contexts` and body sections).

## Section regimes

Match the section's regime; do not invent a fourth.

- **Live state: rewrite in place.** One current value per named line. `## Dev`
  (`branch:`, `worktree:`, `pr:`) is canonical; its shape is in
  the ticket template's guide comment. Old values live in git.
- **Record: append, never delete.** `## Superseded designs` takes dated
  entries (shape [below](#superseded-designs);
  only an archive pointer composes). `## Blockers` takes one checkbox per ask;
  `coga unblock` marks it `- [x]` and appends `resolved:`. Blocker readers
  ignore fenced examples and superseded sections.
  The writer does not (known limitation, unfixed): when a real ask is open,
  `coga unblock` (`blackboard.resolve_open_blockers`) also flips `- [ ]`
  examples in fences and superseded sections and appends `resolved:` to
  them, so keep example blockers out of a blackboard that may be unblocked.
- **Authoring scratch: synthesize before launch.** `## Evaluator review`,
  `## Ticket authoring notes`, `## Proposals`. The `bootstrap/ticket` cleanup
  folds durable substance into the body; for a draft it keeps
  `## Superseded designs` and resets the rest to the stock placeholder; for a
  non-draft it removes only the authoring sections it used.

## Superseded designs

When a design changes, rewrite `## Description` and `## Context` to describe
current work, with live requirements under `###` subheadings. Other top-level
body sections do not compose. Move the abandoned plan below the blackboard
fence into one `## Superseded designs` section; append dated entries oldest
to newest:

```markdown
## Superseded designs

### YYYY-MM-DD — <abandoned direction>

Superseded by: <current direction or decision>
Reason: <why the ticket pivoted>

<prior plan, acceptance details, and evidence worth retaining>
```

Retain enough to understand or reconsider the old plan, with copied headings
at `####` or deeper inside each entry. Keep history in this single section,
not scattered under alternative headings or left only in Git; only the exact,
unindented `## Superseded designs` heading starts it. The body may carry one
short pointer when a reviewer needs it; keep current decisions and their
rationale in live notes. The prompt includes only a pointer to the stored
history.

## Draft-activation readiness

On first activation (`mark active` or launch auto-activation) Coga refuses a
draft whose blackboard still holds authoring scratch sections or a large
custom scratchpad, before anything is written or spawned; `coga validate`
reports the same error. The stock placeholder (resource `blackboard.md`, which
a repo may override under `<coga root>/resources/`) counts as empty. Merge
durable requirements into `## Description` / `## Context` first. A
`## Production notes` section marks remaining content as intentional launch
material and exempts it; `## Superseded designs` is excluded without
exempting other notes. Later reactivations and forced recurring reruns do not
recheck. An `## Evaluator review` written by a live workflow step is working
state for the next owner gate, not residue.

## Size and its remedy

`coga validate` (`large-blackboard`) and launch warn above 32 KiB of live
notes. When `coga launch --prompt-report` shows the blackboard as the
largest layer, do not delete history. Promote a file-form task to directory
form, move dated evidence into sibling attachments (`tasks/<slug>/<topic>.md`,
opening with an HTML comment naming the task and move date), and leave the
current handoff, worklist and verification with a pointer to each. Keep
`## Dev` and `## Blockers` in place, since CLI readers do not follow links.
Material several tickets cite belongs in an unattached context. Record the
before/after layer sizes on the blackboard. A moved section leaves a
same-named heading holding only the pointer, so references to it (an
evaluator review citing `## Design`) still resolve.

The remedy is for live tickets. A flagged `done` ticket is not trimmed: one
with no live recorded checkout is left to Dream's retro pass, and one with a
live checkout is retirement debt that `coga retire <slug>` disposes of and
deletes ([Dream template](https://github.com/FastJVM/coga/blob/main/coga/recurring/dream/ticket.md) owns that split). A section a writer rewrites
every run (a recurring template's state, Dream's own per-run report) is not
trimmed by hand either: the next run overwrites the edit, and
[coga/period-task](../period-task/SKILL.md) says to touch only your own keys.
Route it to its owner as a decision (attachment, exemption, or accepted
warning).

## What later passes do to content

- A replaced live value leaves the section; git keeps it.
- A replaced design moves into the single `## Superseded designs` section;
  the body keeps at most a one-line pointer. Keep rationale still needed for
  current work in live notes.
- A resolved blocker keeps its ask.
- A period task's blackboard is deleted at Dream's retro cleanup: durable
  gotchas go under `## Gotchas` for extraction and last-run state goes on the
  parent template's blackboard ([coga/period-task](../period-task/SKILL.md)).

## Concurrent writers

There is no ownership mutex; divergent workers are visible and recoverable in
git ([coga/launch](../launch/SKILL.md)). A `ticket.py` or other program that
writes a blackboard uses `blackboard.update_blackboard_under_barrier`, which
refuses rather than overwrite an intervening edit. Read the region
immediately before writing, prefer section appends to whole-region rewrites,
and keep writes as small as the change. Parser and race details are in
[blackboard IO](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/blackboard-io/SKILL.md);
cross-checkout reconciliation is in [coga/sync](../sync/SKILL.md).
