---
title: Prevent autostash spool conflicts on control-branch sync
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/sync
- relay/architecture
- relay/principles
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
secrets: null
---

## Description

Relay's git sync repeatedly leaves the working tree with conflict markers and
orphaned `autostash` stash entries on the digest spool. This keeps happening:
the prior commit `e66c302` ("digest: restore PR #368 spool record") was a hand
cleanup of the same wound, and a recent occurrence even wrote a `[git] sync
failed` trace *into a task's `log.md`*. Goal: make concurrent appends to the
shared append-only files merge cleanly instead of conflicting, so no human (or
agent) has to hand-resolve markers and prune leftover stashes.

### Root cause (confirmed)

The contention is on the **state plane**, not code. Ticket transitions, the
digest spool, recurring markers and dream logs are committed **directly to
`origin/main`** by `git.py:sync_task_state` / `_push_control_branch` — no
branch, no PR (only `(#NN)` commits go through PRs). So two relay processes
(here: two separate clones, `~/Code/claude/relay` and `~/Code/relay`, both
running against one GitHub origin) race directly on `main`. PRs don't protect
this; a PR *merge* by anyone advances `main` and is itself a frequent trigger.

When a clone's direct push is rejected non-fast-forward, `_rebase_onto_remote`
runs `git rebase --autostash` (`git.py:244`). The autostash captures the dirty
spool, rebases, and pops it back — and the pop has to *content-merge* the spool.

The specific reason it conflicts is the **drain**: `spool.py:drain` rewrites the
whole `## Spool (pending)` section to empty — it deletes lines 1..n **including
the trailing region where the other writer just appended**. A delete-everything
that overlaps a concurrent append is the worst case for git's 3-way merge, so it
conflicts; the `rebase --abort` handler re-applies the same autostash and
re-conflicts, leaving markers **and** an undropped stash. `merge=union` would
make this *worse* — it would resurrect the just-drained records (this is exactly
`e66c302 "restore PR #368 spool record"`, and why the live spool still carried
records back to 06-06).

`spool.py`'s comment *"Relay runs one CLI process at a time, so appends and
drains are serialized"* is simply false — there were two processes live during
this incident.

### Proposed fix — make the spool merge by construction

Invariant: git auto-merges hunks separated by ≥1 unchanged line. So arrange
every write so **deletes only happen at the top, appends only at the bottom,
with an untouched anchor record between them.** Concretely, reshape the spool to
a watermark + prefix-compacting drain:

- **Record id** — `append_record` assigns each record a unique `id` (random
  hex; no cross-clone coordination needed) and inserts it at the **bottom** of
  the section. Producers are pure tail-appenders; they never touch the watermark
  or existing records.
- **Watermark** — a single `consumed_through: <id>` line in a fixed slot under
  the heading names the last record the digest has posted.
- **Drain → consume** (`digest`, the single consumer): post records below the
  watermark, advance `consumed_through` to the newest seen, then **trim every
  consumed record from the top, keeping the single newest record in place as the
  anchor.** Never empties the tail.

Then a concurrent `drain` (deletes a top prefix + bumps the watermark) and
`append` (adds one line at the bottom) touch disjoint hunks separated by the
anchor → git merges them automatically, no markers, no resurrection, and the
watermark stops the anchor being re-posted. Size stays bounded to ~one digest
interval of records + the anchor (consumed records are still trimmed).

Supporting pieces:
- **`.gitattributes` `merge=union`** on the genuinely append-only `**/log.md`,
  and as a *backstop* on the spool for the near-empty edge case. Not the primary
  mechanism.
- **De-dup at post time** by `id` (or `ts`+`ticket`+`kind`) so two clones that
  independently recorded the same event (e.g. the duplicate `1password — done`
  seen here) don't double-post.
- **Failure-handler hardening** (`_rebase_onto_remote`): guarantee it never
  leaves a dirty/conflicted tree or an orphaned stash, and never appends the git
  error trace into a task `log.md` (it did, here).

### Out of scope — split into follow-up tickets

- **Per-agent `git worktree` isolation** in `launch.py` for the *intra-clone*
  shared-working-tree race the Explore pass found (recurring sweep + an agent's
  `relay mark`/`bump` both autostashing one checkout). Real, but distinct from
  the spool-merge bug; harness behavior, **not** a base-prompt instruction.
- **One control-writer / retire the duplicate clone** — operational: today's
  contention was two clones on one origin. Stop the second clone's recurring run
  to remove the live source independent of the code fix.

### Acceptance criteria

- [ ] `append_record` is tail-only and id-stamped; `drain` becomes a
  watermark-advance + prefix-trim that always leaves the newest record as anchor.
- [ ] A regression test simulates a contended-push → rebase-autostash where one
  side drained and the other appended, and asserts: clean auto-merge, no markers,
  no orphaned stash, no resurrected (already-consumed) records, anchor not
  re-posted.
- [ ] De-dup by record id verified (same event from two writers posts once).
- [ ] `_rebase_onto_remote` never leaves markers/stashes and never logs its
  error trace into a ticket `log.md`.
- [ ] `spool.py`'s stale "one process at a time" comment corrected.
- [ ] The spool concurrency/merge contract is documented in the `relay/sync`
  context (the **Context block** below), landed in the **same PR** as the
  behavior change — per repo rule, durable explanation lives in a context, not
  task notes.
- [ ] Follow-up tickets filed for worktree isolation and retiring the second
  clone.

## Context block — land in `relay/sync` SKILL.md

> The implementer lifts this into `relay-os/contexts/relay/sync/SKILL.md` (and
> the packaged copy under `src/relay/resources/templates/relay-os/`) in the same
> PR, adjacent to the existing spool/digest section. It is written as the
> *target* contract (post-implementation), so it must not land before the code.

### Why the spool is a contended file, and how it stays mergeable

State-plane writes — ticket transitions, the digest spool, recurring markers,
dream logs — are committed **directly to `origin/main`** by `sync_task_state` /
`_push_control_branch`, with no branch and no PR. (Only `(#NN)` commits go
through PRs; those are the code plane.) So any number of relay processes — in
this repo, in another clone, on another machine — push state straight to the
same `main`. The digest spool (`recurring/digest/blackboard.md`'s
`## Spool (pending)`) is the hottest such file: every done/error event appends
to it, and the daily `relay digest` drains it. Two writers therefore routinely
collide on it during a rejected-push → `rebase --autostash` recovery.

git resolves a 3-way merge cleanly only when the two sides' changed line ranges
don't touch. The spool is engineered around that one fact, with **two** distinct
concurrency cases and a different mechanism for each:

1. **Append vs append** (two producers each add a record at the bottom). Plain
   git conflicts — both insert at the same EOF anchor. This is resolved by
   marking the append-only files `merge=union` in `.gitattributes`: union keeps
   **both** sides' lines. It is *safe here precisely because both sides only
   add* — there is nothing to resurrect. Records carry a unique `id`, so the
   ours-then-theirs order union picks is harmless (the digest orders by
   `ts`/`id`, not file position).

2. **Drain vs append** (the digest consumes while a producer adds). This is the
   dangerous case, and `merge=union` makes it *worse*: if union ever sees a hunk
   where one side **deleted** lines, it keeps them — resurrecting just-consumed
   records (the historical `e66c302 "restore PR #368 spool record"` bug; stale
   records lingering for days). The fix is structural, not a merge driver:

   - Producers **append only at the bottom**, never touching the watermark or
     existing records.
   - A `consumed_through: <id>` watermark in a fixed slot names the last record
     the digest has posted.
   - The digest **drains by compacting the consumed *prefix*** — it deletes the
     run of already-posted records from the **top**, but always **keeps the
     newest record in place as an anchor** (and never empties the tail).

   Now the delete (top) and any concurrent append (bottom) are separated by the
   anchor — disjoint hunks — so git auto-merges them with **no conflict and no
   resurrection**, and `merge=union` is never invoked on a delete. The watermark
   stops the retained anchor being re-posted next run. Size stays bounded to
   ~one digest interval of records plus the anchor.

**The invariant, stated once:** deletes only at the top, appends only at the
bottom, always an untouched anchor between them. `merge=union` is the *backstop*
for the pure-append collision (case 1); prefix-compaction is what guarantees
union never has to touch a delete (case 2). The current `drain` violates this by
rewriting the whole section to empty — deleting the very region producers append
to — which is the entire root cause.

(Process-level races within a single clone — a recurring sweep and an agent's
`relay mark`/`bump` both `rebase --autostash`-ing one working tree — are a
separate concern handled by per-agent worktree isolation, tracked in its own
ticket. relay is intentionally lock-free; this contract is what makes that safe
for the spool.)

## Context

This was found while hand-fixing a live occurrence on `main` on 2026-06-18:
a failed autostash restore left conflict markers in the digest blackboard and
two orphaned `autostash` stashes; a redundant duplicate "done" commit had also
been produced by **two clones on one machine** (`~/Code/claude/relay` and
`~/Code/relay`, the latter running `relay launch …recurring…`, PID 35644) racing
the same ticket transition through one shared GitHub origin. Resolved by hand
(union of spool records, reset to origin, dropped the redundant commit and stale
stashes). The fix here is to stop it recurring.

See `relay/architecture` ("Status is the signal" — no filesystem mutex; the
spool as a producer/consumer queue on a blackboard) and `src/relay/git.py`,
`src/relay/spool.py`, `src/relay/notification/` (the spool writers).
