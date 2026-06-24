---
slug: prevent-autostash-spool-conflicts-on-control-branc
title: Prevent autostash spool conflicts on control-branch sync
status: draft
autonomy: interactive
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

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan / findings (implement step, claude)

### Code map (confirmed)
- `relay.spool` callers: `commands/digest.py`, `notification/__init__.py`, tests
  only. (`usage.py` has its *own* unrelated `append_record` — out of scope.)
- `spool.py`: `append_record` (EOF-insert), `read_records` (all), `drain`
  (rewrites whole `## Spool (pending)` section to empty — **the root cause**).
- `digest.py::run_digest`: `read_records` → decide post → `post` → `drain`.
  `done_pr_numbers(records)` suppresses git-scan commits already in Done records.
- `git.py::_rebase_onto_remote` (same-branch push retry): `rebase --autostash`;
  on failure `rebase --abort` then raise. The abort can fail to re-apply the
  autostash (pop conflicts on the overlapping spool), leaving markers + an
  orphan stash. Only runs on the **same-branch** (HEAD==control) path.
- `logfile.append_log` writes ONLY to the repo-global `relay-os/log.md` (there
  is no per-task log.md). It is already `merge=union`. So AC4's "logs its trace
  into a ticket log.md" = the global union-merged log, tagged with the digest
  ref — benign. The substantive half of AC4 is the no-markers/no-orphan-stash
  guarantee in `_rebase_onto_remote`.
- `.gitattributes` currently: `/log.md merge=union` (top-level only — nested
  recurring-template `log.md` not covered).

### Planned API reshape (spool.py)
- `append_record`: stamp a random hex `id` if absent; still EOF-only.
- add `read_unconsumed(path)`: records physically **after** the anchor
  (record whose id == `consumed_through`); all records if no watermark.
- `drain(path)`: becomes watermark-advance + prefix-trim — set
  `consumed_through` to the newest record's id, delete every record above it,
  keep the newest as the **anchor**; returns the consumed records. (zero-arg;
  the peek→drain loss window is identical to today's read→drain, fine for a
  single daily consumer.)
- `read_records` stays (all records) for compat.
- `digest.py`: `read_unconsumed` for the post decision + `done_pr_numbers`;
  `drain` after a successful post; dedup before render (see open Q2).
- watermark = `consumed_through: <id>` line in a fixed slot under the heading.
  Lazy — absent watermark ⇒ everything unconsumed, so existing live spools and
  the shipped template need no migration/seeding.

### `_rebase_onto_remote` hardening (planned)
Replace implicit `--autostash` with an explicit, reversible stash dance: stash
iff dirty (tracked only, never untracked); rebase; on rebase failure → abort +
restore-to-ORIG_HEAD + pop (clean, since stash came from ORIG_HEAD's tree);
on a conflicted pop after a *successful* rebase → discard partial pop, reset
--hard ORIG_HEAD, pop there (clean), raise. Net: never a conflicted tree, never
an orphan stash; dirty changes preserved; sync miss surfaced (stderr + global
union log) per the existing non-fatal failure model.

### Decisions (nick, 2026-06-24)
- **Q1 → dedicated spool file.** Spool moves to `recurring/digest/spool.md`;
  `.gitattributes` gets `**/log.md merge=union` + `**/spool.md merge=union`.
  `### Digest State` (last_commit/range/posted) **stays in ticket.md**.
  Union on the whole spool.md is safe: static header identical → no dup; record
  lines append-only → union keeps both (the two-producer backstop); the mutable
  `consumed_through:` line has a single writer normally → no conflicting hunk →
  union not invoked → preserved (reader tolerates dup watermark = last wins).
- **Q2 → content tuple + id.** Dedup on `(project, kind, ticket, detail)` to
  collapse cross-clone same-event dupes; plus exact-`id` for union line dups.

### Implementation surface (both copies per CLAUDE.md)
1. `spool.py` reshape (id stamp, read_unconsumed, watermark drain; reads the
   file directly, not a blackboard region).
2. `commands/digest.py`: read_unconsumed + dedup + drain; thread `state_path`
   (ticket.md) separately from `spool_path` (spool.md).
3. `notification/__init__.py`: `digest_spool_path` → spool.md; add
   `digest_state_path` → ticket.md; add `dedupe_records`.
4. `.gitattributes` ×3 (relay-os, example/relay-os, templates/relay-os).
5. `recurring/digest/` × (live, template, example): add `spool.md`, drop the
   `## Spool (pending)` section from `ticket.md`, refresh prose.
6. `relay/sync` SKILL.md (+ shipped copy): land the ticket's Context block.
7. `git.py::_rebase_onto_remote` hardening + tests.

## Dev

branch: spool-merge-by-construction
worktree: /home/n/Code/claude/relay-spool-merge
commit: 2f982cb3 (one logical change, working tree clean)

## Implementation status (implement step done)

All ACs met; `887 passed, 1 skipped` (full suite) + `relay validate` on the
example fixture clean. Per-AC:
- [x] `append_record` tail-only + id-stamped; `drain` = watermark-advance +
  prefix-trim, always leaves newest as anchor. (`spool.py`)
- [x] Regression: `test_drain_vs_append_merge_without_conflict` drives a real
  `git merge-file` 3-way of a drained side vs an appended side → clean merge,
  no markers, consumed records not resurrected, anchor not re-posted. Stash/
  marker hardening covered by
  `test_sync_control_branch_unpoppable_dirty_change_leaves_no_markers_or_stash`.
- [x] De-dup by content tuple: `test_dedupe_collapses_same_event_from_two_clones`
  + `test_run_digest_posts_a_duplicated_event_once`.
- [x] `_rebase_onto_remote` hardened (explicit reversible stash dance); never
  leaves markers/stash. The trace lands only in the repo-global, union-merged
  `relay-os/log.md` (there is no per-task log.md) — that's the fail-loud
  contract, kept.
- [x] Stale "one process at a time" comment removed (whole `spool.py` docstring
  rewritten to the merge-by-construction contract).
- [x] `relay/sync` context block landed in the SAME commit (live + template
  copy; template also absorbed prior automerge→autoclose drift).
- [ ] Follow-up tickets — NOT yet filed (filing pushes drafts to origin); see
  specs below, holding for nick's go-ahead.

### Decisions made during impl (beyond Q1/Q2)
- Union backstop can't be a `.gitattributes` entry on a mid-ticket section, so
  the dedicated `spool.md` file is what makes union viable (Q1). Union on the
  whole spool.md is safe (static header identical; record lines append-only;
  single-writer watermark → no conflicting hunk).
- `spool.md` vendored in `update.py` (`VENDORED_RECURRING_TEMPLATES`) so repos
  predating it gain the file on `relay init --update`; wholesale-overwrite
  matches the existing digest-ticket refresh (resets daily-ephemeral records,
  acceptable).
- `### Digest State` stays in `ticket.md`; threaded as a separate `state_path`
  in `digest.py`.

### Follow-up ticket specs (file on nick's ok — AC7)
1. **Per-agent `git worktree` isolation in `launch.py`** — intra-clone race: a
   recurring sweep and an agent's `relay mark`/`bump` both `rebase --autostash`
   one shared working tree. Distinct from this spool fix; harness behavior.
2. **Retire the duplicate clone / one control-writer** — operational: stop the
   second clone's recurring run (`~/Code/relay`) so only one process writes
   state to the shared origin.

### Migration / live-state note for nick
- Live `relay-os/recurring/digest/ticket.md` is dirty in your main working
  tree; this PR removes its `## Spool (pending)` section, so a `git pull` will
  conflict there — resolve by keeping the ticket.md frontmatter/Digest State and
  moving any pending records into the new `spool.md`. The 2 pending records
  currently in your working copy are daily-ephemeral; worst case they miss one
  digest. Shipped `spool.md` starts empty (header + empty `consumed_through:`).
