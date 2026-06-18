---
title: Prevent autostash spool conflicts on control-branch sync
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/principles
skills: []
workflow: null
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

`src/relay/git.py:_push_control_branch` → `_rebase_onto_remote` runs `rebase
--autostash` whenever a push to the control branch is rejected non-fast-forward
(origin moved under us — routine here with multiple machines/agents across the
`relay` and `relay-cli` repos pushing the same `main`). The autostash captures
the **uncommitted** digest-spool write; the rebase replays local commits onto
the moved tip; the autostash pops back. Both the remote commits and the stashed
working copy appended to the **same trailing region** of
`relay-os/recurring/digest/blackboard.md`'s `## Spool (pending)` section, so the
pop conflicts. The failure handler does `rebase --abort`, which re-applies the
same autostash and re-conflicts, leaving markers in the working tree **and** an
undropped stash. Repeat → litter accumulates.

`src/relay/spool.py` documents an assumption that no longer holds: *"Relay runs
one CLI process at a time, so appends and drains are serialized."* In practice
appends race across processes and machines, and git's line merge cannot
auto-merge appends to the same trailing region (no trailing context line).

### Proposed fix

1. **`.gitattributes` `merge=union`** for the append-only files — the headline
   fix. Union keeps both sides' lines on conflict instead of writing markers,
   which is exactly right for append-only JSONL/log content, and it applies on
   the rebase/stash-pop merge path that is biting us:
   ```
   relay-os/recurring/*/blackboard.md   merge=union
   **/log.md                            merge=union
   ```
   Declarative, standard git, no hidden state — fits principle 3 (obvious) and
   principle 6 (fail loud, not silent-wrong).

2. **Follow-up / decide:** `blackboard.md` is not purely append-only — it
   carries a small structured header (`### Digest State`, `last_serviced_period`).
   `merge=union` is per-file, so a rare concurrent header edit would union both
   header lines rather than conflict. Net-positive (header changes ~once/day,
   serialized; the spool conflicts constantly), but the clean long-term move is
   to split the spool into its own append-only file so union covers only
   append-only content. Decide split-now vs. follow-up during design.

3. **Consider:** the `_rebase_onto_remote` failure handler should guarantee it
   never leaves a dirty/conflicted tree (e.g. verify the autostash fully
   restored, surface loudly otherwise) and should not append the git error
   trace into a task `log.md`. The `merge=union` change should make this path
   succeed, but the handler robustness is worth a look.

### Acceptance criteria

- [ ] Concurrent appends to the spool and to `log.md` files merge without
  conflict markers across a sync-triggered rebase/autostash.
- [ ] A regression test simulates the contended-push → rebase-autostash path
  and asserts a clean, marker-free, stash-free working tree.
- [ ] `spool.py`'s stale "one process at a time" comment is corrected.
- [ ] Decision recorded (split the spool file or keep union on the whole
  blackboard) with rationale.

## Context

This was found while hand-fixing a live occurrence on `main` on 2026-06-18:
a failed autostash restore left conflict markers in the digest blackboard and
two orphaned `autostash` stashes; a redundant duplicate "done" commit had also
been produced by two machines racing the same ticket transition. Resolved by
hand (union of spool records, reset to origin, dropped the redundant commit and
stale stashes). The fix here is to stop it recurring.

See `relay/architecture` ("Status is the signal" — no filesystem mutex; the
spool as a producer/consumer queue on a blackboard) and `src/relay/git.py`,
`src/relay/spool.py`, `src/relay/notification/` (the spool writers).
