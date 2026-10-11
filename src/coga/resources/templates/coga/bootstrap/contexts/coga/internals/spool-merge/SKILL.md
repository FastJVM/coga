---
name: coga/internals/spool-merge
description: How concurrent writers to shared Coga state files stay correct — `merge=union` append-only files (`log.md`, `retires.md`), the union three-way merge in `publish`, content guards on union files, and why atomic replacement is crash-safety rather than a lock; also records that the digest spool no longer exists.
---

# Append-only state and concurrent writers

Coga lets several processes, worktrees, and clones write state at once. No
lock spans them: `git.state_lock` serializes one checkout only, and
cross-checkout coordination is the push compare-and-swap in
[`coga/internals/state-publication`](../state-publication/SKILL.md). Files that
many writers touch must therefore be correct **by shape**.

**No spool exists.** The daily digest and its outcome spool were removed
(#786); outcomes post live ([`coga/notifications`](../../notifications/SKILL.md)).
There is no hidden queue, drain step, or high-water watermark for
notifications. This page keeps the reusable merge rules that outlived it.

## `merge=union` files

`coga/.gitattributes` marks `**/log.md` and `**/retires.md` `merge=union`.
Union keeps both sides' lines, which is safe only when resurrecting a line
is harmless:

- `coga/log.md` — every writer only appends, so union never loses or revives
  anything meaningful. Usage records ride it (`coga/usage`).
- `coga/recurring/<name>/retires.md` — the autoclose retire worklist is
  rewritten, so a union can resurrect a dropped line, and a git-native union
  merge (or a differing line for the same slug) can still duplicate a slug;
  its reader collapses duplicates and the next reconcile re-applies the
  discharge rule (`src/coga/retire_worklist.py`).

A file that is compacted, trimmed, or rewritten without such a healing reader
must never carry the attribute: union would resurrect deletions. Because
`git.union_merge_paths` asks `git check-attr merge` rather than hardcoding
names, adding a path to `.gitattributes` is enough to route it through the
union merge — which is also why adding the wrong file is the mistake to avoid.

## How `publish` lands a union path

- No provenance check: union paths merge rather than overlay.
- The landed bytes are `git merge-file --union` of (merge-base copy, control's
  copy, working copy) (`_merge_union_bytes`), and those bytes are what the
  control checkout is fast-forwarded to.
- **Invariant: a union-merged publication never increases the occurrence
  count of a byte-identical line already on control.** A feature-branch or
  detached checkout publishes without its HEAD advancing, so its merge base
  can lag lines it already landed; diffed from that base, control and the
  working copy both "insert" them and the raw union emits them twice. The
  same happens with no merge base at all (empty base).
- `_merge_union_bytes` therefore filters the raw merge by occurrence count:
  a line on control keeps `min(control count, raw merge count)` occurrences;
  a line absent from control keeps all of them. When the raw merge contains
  control's whole line sequence as a subsequence, its earliest such
  embedding is kept; otherwise the earliest occurrences within each cap are.
  The result is always a subsequence of the raw merge — nothing is reordered
  or added, so a clean move keeps the raw merge's order. Lines compare as
  bytes with their line ends. Prepare's "already on control" proof
  (`_published_proof`) uses the same function, so it agrees with what
  publish lands.
- Deletions: a line the working copy dropped still lands as a deletion when
  the merge base also had it (`coga retire` drops its `retires.md` slug this
  way), and a clean deletion of one historical duplicate still lands. A
  control line both the working copy and the base lack (a concurrent
  control addition) is kept. Union is not "never deletes".
- The published ref (`refs/worktree/coga/published`) is not used as the
  base: it holds the *landed* bytes, so against it the working copy would
  look like it deleted a peer's line and the merge would erase it. Recording
  the working bytes instead would be new hidden state that still fails with
  no ref, in another clone, or with no merge base; the filter needs none.
- Tradeoff: a line identical to one control already has cannot be added
  again by publish. `retires.md` collapses duplicates anyway; `log.md` lines
  carry a minute timestamp (usage records a session id), so only an
  identical line written in the same minute and published separately
  collapses. Existing duplicates are kept, not rewritten.
- A union path missing locally while control has it is refused, never
  published as a deletion (`coga/internals/git-regressions`).
- When a writer decided something from control's exact copy, it pins it:
  `expect` adds a blob check (only while the path is a candidate), and
  `guard` re-evaluates control's *content* before every attempt. The
  recurring create uses both — it pins the ledger and template it read and
  refuses once control records the period as serviced — so a peer that
  serviced the period between fetch and push makes the create re-read
  control instead of landing a duplicate.

## Crash-safe replacement is not a lock

`atomicio.atomic_write_text` writes a same-directory temp file (fsync by
default), then `os.replace`s it, so a reader sees the old or the new complete
file and a crash never leaves a half-written file for the sweep to publish. It
does **not** serialize writers: two read-modify-write cycles can still race,
and the later one wins. A composition must stay correct through one of:

- append-only regions (union-merged);
- disjoint hunks that git merges cleanly;
- an explicit primitive — `state_lock` within a checkout or launch claims
  ([`coga/internals/launch-claims`](../launch-claims/SKILL.md)), `expect`/`guard`
  across checkouts.

`merge=union` resolves only the pure append-versus-append case; it resolves
nothing else.
