---
name: coga/blackboard
description: The writer's contract for a ticket blackboard — locating the fence, scoping edits, append versus rewrite-in-place sections, the draft-activation readiness check, size limits and their remedy, and the concurrency limits of shipped writers. Attach to tickets whose work writes blackboards programmatically.
---

# Writing to a ticket blackboard

The blackboard is everything below the `<!-- coga:blackboard -->` fence in a
ticket: working memory shared by human and agent and carried between
stateless sessions. Its live state is composed into every launch
([coga/prompt-composition](../prompt-composition/SKILL.md)); `coga/log.md`,
written only by CLI commands, holds lifecycle history and is never composed.
Working state the next run must read goes here and stays small; history goes
in the log. Where the source disagrees with this page, the source wins.

## The fence

`src/coga/taskfile.py` `_FENCE_RE` matches `BLACKBOARD_FENCE` only as a whole
line: no leading indentation, optional trailing spaces/tabs, optional `\r`.
It does not parse Markdown, so an own-line fence inside a code block counts,
while an inline mention does not. The region starts right after the match
(a fence at EOF gives an empty region) and `read_blackboard` /
`replace_blackboard` round-trip it byte-for-byte.

- **Never locate the fence by substring** (`split`, `find`, `partition`,
  unanchored `grep`/`sed`): a quoted fence in prose truncates the body. This
  has corrupted tickets twice; recovery came from git.
- **Exactly one fence.** `split_body` and `read_blackboard` raise
  `TaskFileError` on zero or several. Bootstrap tickets legitimately have none
  (`blackboard_required=False`); `upsert_blackboard` appends a fence to a
  fence-less legacy recurring template. Multiple fences always fail.
- **Scope each edit.** Frontmatter/step writers go through
  `coga.ticket.Ticket` and keep the body they loaded, which may not be the
  latest on disk. Blackboard writers use `replace_blackboard`, which splices
  only the region and never reformats YAML. Compute every transform on the
  region from `read_blackboard`, never on whole-file text, so a `## Heading`
  pattern cannot hit the body.

What may be edited above the fence is owned by
[coga/tickets](../tickets/SKILL.md) (agents: `contexts` and body sections).

## Section regimes

Match the section's regime; do not invent a fourth.

- **Live state: rewrite in place.** One current value per named line. `## Dev`
  (`branch:`, `worktree:`, `pr:`) is canonical; its shape is
  [dev/dev-record](../../dev/dev-record/SKILL.md). Old values live in git.
- **Record: append, never delete.** `## Superseded designs` takes dated
  entries (shape in [dev/design-history](../../dev/design-history/SKILL.md);
  only an archive pointer composes). `## Blockers` takes one checkbox per ask;
  `coga unblock` marks it `- [x]` and appends `resolved:`.
- **Authoring scratch: synthesize before launch.** `## Evaluator review`,
  `## Ticket authoring notes`, `## Proposals`. The `bootstrap/ticket` cleanup
  folds durable substance into the body; for a draft it keeps
  `## Superseded designs` and resets the rest to the stock placeholder; for a
  non-draft it removes only the authoring sections it used.

`src/coga/blackboard.py` `append_to_section_text` / `append_to_section`
append into a named section (heading to next `## `), creating it at the end
if missing.

## Draft-activation readiness

On first activation (`mark active` or launch auto-activation) Coga refuses a
draft whose blackboard holds `PRELAUNCH_AUTHORING_HEADINGS` sections or a
large custom scratchpad (`_is_stock_blackboard` treats the stock placeholder
as empty), before any freeze, status change, log, post, composition or spawn.
`coga validate` reports the same error. Merge durable requirements into
`## Description` / `## Context` first. A `## Production notes` section marks
remaining content as intentional launch material and exempts it;
`## Superseded designs` is excluded without exempting other notes. Later
reactivations and forced recurring reruns do not recheck. An
`## Evaluator review` written by a live workflow step is working state for
the next owner gate, not residue.

## Size and its remedy

`blackboard_size_warning` and `coga validate` (`large-blackboard`) warn above
`BLACKBOARD_WARN_BYTES` (32 KiB), measuring live notes plus the archive
pointer. When `coga launch --prompt-report` shows the blackboard as the
largest layer, do not delete history. Promote a file-form task to directory
form, move dated evidence into sibling attachments (`tasks/<slug>/<topic>.md`,
opening with an HTML comment naming the task and move date), and leave the
current handoff, worklist and verification with a pointer to each. Keep
`## Dev` and `## Blockers` in place, since CLI readers do not follow links.
Material several tickets cite belongs in an unattached context. Record the
before/after layer sizes on the blackboard.

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
git ([coga/launch](../launch/SKILL.md)). Shipped blackboard writers use
`update_blackboard_under_barrier`: it holds `git.state_lock`, captures the
bytes, and at replacement compares them again via `expected_bytes`, raising
`TaskFileError` rather than overwriting an intervening edit (it detects, but
cannot lock, an outside editor). Put programmatic appends inside its
transform. The low-level helpers take no lock; callers own admission and
pass `expected_bytes`.

Lifecycle writes are weaker: `git.write_ticket` serializes but does not
reread, and `coga mark active` loads the `Ticket` before the lock, so a
blackboard update landing in between can be overwritten by the old body.
Megalaunch's strict writes compare source bytes under the lock and are safe.

Atomic rename gives crash-safety, not serialization
([coga/patterns](../patterns/SKILL.md)). So: read the region immediately
before writing, prefer section appends to whole-region rewrites, keep writes
as small as the change, and use the shipped helpers. Cross-checkout
reconciliation is out of scope here ([coga/sync](../sync/SKILL.md)).
