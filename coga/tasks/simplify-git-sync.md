---
title: Simplify git sync
status: draft
owner: nicktoper
contexts:
  - coga/principles
workflow: code/design-then-implement
---

## Description

Coga's git sync does something simple — commit coga state (`coga/tasks/**`,
`coga/log.md`) on every transition, push it to the control branch, and pull
the control branch's state back into the checkout — but the implementation
has grown far past that: `src/coga/git.py` is ~7,300 lines, 151 functions
(120 private), backed by a 225-test `tests/test_git.py` of similar size, and
the `coga/sync` context that specifies it is ~90 KB. It still produces sync
failures in live repos (`fix-git-sync-failure` is the latest; that ticket's
`multiply` repo also carries orphaned coga stashes from a September run).

Design a simpler sync model first, agree on it with the owner, then implement
it. The design must state, in a page or two: what the sync invariants are
(what must never be lost, what must never move backward, which branch is
canonical), the small set of git operations that satisfy them, which of the
current special cases survive and which are dropped, and how the
`coga/sync` context shrinks to match. Done means a `git.py` an engineer can
read end to end, a `coga/sync` git section that fits the same page as the
design, and the existing behavioral guarantees that the design keeps still
covered by tests.

## Context

- Public surface of `git.py` today, by consumer count across `src/coga`
  (the design should decide which of these remain): `sync_task_state` (21),
  `ticket_state_guard` (11), `write_ticket_under_barrier` /
  `state_publication_barrier` / `restore_files_under_barrier` (10 each),
  `feature_publication_lease` (9), `sync_paths` (8), `sync_log` (4),
  `capture_task_mutation_snapshot` (4), `ticket_routing_state` (3),
  `refresh_coga_state_from_control` (2), `sync_coga_state` (1), plus a few
  one-off helpers. 30 modules import it.
- Where the complexity lives, as things the design must explicitly keep or
  drop (each is a section of `coga/contexts/coga/sync/SKILL.md` under
  `## Git — durable task-state sync`):
  - *Feature-branch publication boundary* — landing state on control while
    the checkout is on a PR branch; assist publication with
    `force-with-lease`; the "verified single push destination" for forks;
    compensation trees (`_build_feature_compensation_tree`,
    `_inverse_compensated_bytes`) that unwind state out of a PR payload.
    `stop-syncing-task-state-onto-the-feature-branch` (done) already removed
    one half of this; the remaining machinery may be mostly for the half that
    no longer exists.
  - *State-regression guard* — `_guard_coga_state_regressions`,
    `_ticket_state_regression_reason`, launch-claim guards: refuse a push that
    would move a ticket's lifecycle backward.
  - *Catch-all subtree sweep* (`sync_coga_state`) vs the per-transition
    `sync_task_state` vs `sync_log` — three entry points for "commit and push
    coga state".
  - *Launch-end pull-back* (`refresh_coga_state_from_control`) — a fourth
    integrate-remote path, distinct from `_push_control_branch`'s
    fetch+rebase; `fix-git-sync-failure` papers over that split, this ticket
    should remove it.
  - *Stash-based dirty-tree handling* (`_rebase_onto_remote`,
    `_stash_if_dirty`, `_restore_to_orig`) — the orphaned stashes in
    `multiply` show the restore path does not always run.
  - *Barriers and leases* (`state_publication_barrier`,
    `FeaturePublicationLease`, `FileMutationRollback`) — in-process
    transactions around ticket writes.
  - `coga/log.md` union merge (`merge=union` via `.gitattributes`) — the one
    piece that is clearly simple and should stay.
- Contexts cited, not attached. `coga/sync`
  (`coga/contexts/coga/sync/SKILL.md`) is the spec this ticket rewrites, so
  it is read at the design step, not composed; the design step must read
  `## Git — durable task-state sync` through `## Design rule for new
  features` in full. `coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`)
  owns the microkernel rule and test expectations; the fact that matters:
  `git.py` is shared infra (≥2 consumers) and stays in core, but a
  single-consumer helper does not belong there. `coga/architecture`
  (`coga/contexts/coga/architecture/SKILL.md`, `Where a fact lives: docs vs
  contexts`) decides which surface owns each fact when the sync context is
  rewritten. The packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`
  must be updated byte-identically (`tests/test_packaging.py`).
- Principles the design cannot trade away (see attached `coga/principles`):
  markdown on disk is the source of truth, git is the durable transport,
  the control branch is canonical for task state, no hidden state, failures
  are loud and non-fatal (a sync miss never crashes a command or loses the
  on-disk edit).
- Multi-checkout reality the design has to cover: the owner runs coga from
  several repos, sometimes offline, sometimes from a PR branch, sometimes
  with linked worktrees (`is_linked_worktree`). Concurrent agents push to the
  same control branch (contention is real; `_MAX_SYNC_ATTEMPTS`).
- Sequencing: `fix-git-sync-failure` lands first as the minimal live fix.
  The design step here should treat its rebase-on-refresh change as an
  input, not a constraint.
- Out of scope: the notification half of `coga/sync` (Slack), the
  `coga usage` transcript-matching ambiguity seen in the same `multiply`
  session (separate ticket if it recurs).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
