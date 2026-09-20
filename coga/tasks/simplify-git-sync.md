---
title: Simplify git sync
status: draft
owner: nicktoper
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

The problem is established; do not re-prove it. The `design` step
delivers two things, in one document on this ticket:

1. **A usage audit** of what sync is actually asked to do, taken from the
   repos coga runs in (listed under `## Context`), not from the code's own
   claims: which `git.py` entry points fire on real transitions and from
   which checkout shapes (main checkout, linked worktree, PR branch,
   offline); which special cases have ever been exercised outside the test
   suite; and every sync failure or leftover artifact that occurred in
   practice, with its cause where it can be recovered. The audit is the
   evidence for every keep/drop decision the plan makes.
2. **A simplification plan**, a page or two, that states the sync
   invariants (what must never be lost, what must never move backward,
   which branch is canonical), the small set of git operations that
   satisfy them, which current special cases survive and which are dropped
   — each tied to an audit finding — how the `coga/sync` git section
   shrinks to match, and a proposed implementation split into child
   tickets, one per PR. The plan may rewrite the consumer contract — the
   ~14 public entry points and the ~30 call sites that reach into
   underscore helpers are inputs, not constraints — as long as every
   `src/coga` consumer is accounted for.

The owner decides at `review-design` whether to implement here or to create
the child tickets the plan proposes. Done, for the whole effort, means a
`git.py` an engineer can read end to end, a `coga/sync` git section that
fits the same page as the plan, and the behavioral guarantees the plan keeps
still covered by tests.

## Context

- Audit scope — every checkout with `coga/coga.toml` under `~/Code` on the
  owner's machine, as of this writing: `admin`, `coga`, `demo-hackathon`,
  `magicator`, `multiply`, `patents`, `tablet`, `xpllm`, plus linked
  worktrees `coga-*` (4) and `multiply-*` (3). Several sit on a non-`main`
  branch (`dream/*`, `codex/*`, PR branches); `multiply` and its worktrees
  share 2 orphaned coga stashes. Evidence per repo: `coga/log.md`
  transitions (which sync paths ran, retries, failures), `.coga/` run
  records, `git stash list` and `git reflog` on the control branch for
  leftover artifacts and force-pushes, and `git log` of `coga/**` on control
  vs. feature branches for state that landed in the wrong place. Also read
  the `fix-git-sync-failure` ticket and blackboard for the recorded live
  failure. Re-run the discovery (`find ~/Code -maxdepth 2 -name coga.toml`)
  rather than trusting this list.
- Public surface of `git.py` today, by consumer count across `src/coga`
  (the design should decide which of these remain): `sync_task_state` (21),
  `ticket_state_guard` (11), `write_ticket_under_barrier` /
  `state_publication_barrier` / `restore_files_under_barrier` (10 each),
  `feature_publication_lease` (9), `sync_paths` (8), `sync_log` (4),
  `capture_task_mutation_snapshot` (4), `ticket_routing_state` (3),
  `refresh_coga_state_from_control` (2), `sync_coga_state` (1), plus a few
  one-off helpers. 30 modules import it.
- Where the complexity lives, as things the design must explicitly keep or
  drop (the first four are `###` sections of `coga/contexts/coga/sync/SKILL.md`
  under `## Git — durable task-state sync`; the stash/rebase hardening is
  under `## Control-branch contention and merge=union`; barriers are
  specified in `coga/architecture`, see below):
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
    `multiply` show the restore path does not always run, contradicting the
    "no leftover stash" claim in the contention section of the sync context.
  - *Underscore reach-in* — roughly 30 call sites outside `git.py` import
    private helpers directly (`_toplevel` ×15, `_run_git` ×14, `_tree_bytes`
    ×5, `_remote_configured` ×4, `_commit_paths` ×4, `_fetch_branch_oid` ×3,
    …). The real surface is about twice the public list above.
  - *Barriers and leases* (`state_publication_barrier`,
    `FeaturePublicationLease`, `FileMutationRollback`) — in-process
    transactions around ticket writes.
  - `coga/log.md` union merge (`merge=union` via `.gitattributes`) — the one
    piece that is clearly simple and should stay.
- Contexts cited, not attached. `coga/sync`
  (`coga/contexts/coga/sync/SKILL.md`) is the spec this ticket rewrites, so
  it is read at the design step, not composed; the design step must read
  `## Control-branch contention and merge=union` and `## Git — durable
  task-state sync` through `## Design rule for new features` in full. (The
  context also cites `git.py::_union_merge_paths`; the symbol is
  `union_merge_paths` — fix in the rewrite.) `coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`)
  owns the microkernel rule and test expectations; the fact that matters:
  `git.py` is shared infra (≥2 consumers) and stays in core, but a
  single-consumer helper does not belong there. `coga/architecture`
  (`coga/contexts/coga/architecture/SKILL.md`): `Where a fact lives: docs vs
  contexts` decides which surface owns each fact when the sync context is
  rewritten, and the "state admission/publication barrier" paragraphs under
  `## Status is the signal` are the spec for `state_publication_barrier` /
  `FeaturePublicationLease` — read them before deciding what a barrier must
  still guarantee. The packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`
  must be updated byte-identically (`tests/test_packaging.py`).
- Principles the design cannot trade away — `coga/principles`
  (`coga/contexts/coga/principles/SKILL.md`) is cited, not attached; the
  design step reads `## 1. Hackable`, `## 3. Obvious`, and `## 6. Fail loud`
  in full. The facts the design depends on: markdown on disk is the source
  of truth, git is the durable transport, the control branch is canonical for
  task state, no hidden state, boring standard git operations over clever
  ones, and failures are loud and non-fatal (a sync miss never crashes a
  command or loses the on-disk edit).
- Multi-checkout reality the design has to cover: the owner runs coga from
  several repos, sometimes offline, sometimes from a PR branch, sometimes
  with linked worktrees (`is_linked_worktree`). Concurrent agents push to the
  same control branch (contention is real; `_MAX_SYNC_ATTEMPTS`).
- Sequencing: `fix-git-sync-failure` lands first as the minimal live fix.
  The design step here should treat its rebase-on-refresh change as an
  input, not a constraint; if that ticket has not merged when design starts,
  treat the change as hypothetical.
- Split is decided by the plan, not up front: `code/design-then-implement`
  has one `implement` step and no fan-out. The plan proposes how the work
  divides (a plausible shape: context rewrite; control-branch core + tests;
  feature-branch/PR consumers; barrier/lease consumers); at `review-design`
  the owner either bumps to `implement` (plan small enough for one PR) or
  creates the child tickets, one per PR, and this ticket becomes their
  parent directory. Do not pre-split before the plan exists.
- Out of scope: the notification half of `coga/sync` (Slack), the
  `coga usage` transcript-matching ambiguity seen in the same `multiply`
  session (separate ticket if it recurs).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
