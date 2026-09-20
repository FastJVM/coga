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
has grown far past that: `src/coga/git.py` is ~7,300 lines (141 top-level
functions, 120 of them private), backed by a 225-test `tests/test_git.py` of
similar size, and the `coga/sync` context that specifies it is ~90 KB. It
still produces sync failures in live repos: a launch teardown fails
`merge --ff-only` whenever local control is ahead of a moved remote (seen in
`multiply` on 2026-09-09 and 2026-09-18 and in this repo), the same
divergence makes `coga megalaunch` refuse picks, and `multiply` carries
orphaned coga stashes from a September run.

The problem is established; do not re-prove it. The `design` step delivers
two things:

1. **A usage audit** of what sync is actually asked to do, taken from the
   repos coga runs in (listed under `## Context`), not from the code's own
   claims. Its output is bounded: one fixed table row per checkout —
   checkout shape (main / linked worktree / PR branch / offline episodes),
   control branch name, transitions by sync path, failures by class,
   leftover artifacts (stashes, unpushed control commits, state on the wrong
   branch), recovered cause — plus one row per `git.py` special case saying
   whether it was ever exercised outside the test suite. "No trace" is
   recorded as *unknown*, never as *never fires*; contention and strict
   publication paths are rare by design but load-bearing for `megalaunch`.
   The audit lives on the blackboard under `## Audit`; only the findings the
   plan cites go into `## Description`, so later steps do not compose the
   whole thing.
2. **A simplification plan**, a page or two, that states the sync
   invariants (what must never be lost, what must never move backward,
   which branch is canonical), the small set of git operations that
   satisfy them, which current special cases survive and which are dropped
   — each tied to an audit finding — how the `coga/sync` git section
   shrinks to match, and a proposed implementation split into child
   tickets, one per PR. The plan may rewrite the consumer contract — the
   public entry points and the private helpers other modules reach into are
   inputs, not constraints — as long as every `src/coga` consumer is
   enumerated by module and accounted for.

At `review-design` the owner either bumps to `implement` (plan small enough
for one PR) or creates the child tickets the plan proposes and marks this
ticket `done` with the plan as its deliverable; each child cites
`simplify-git-sync` in its `## Context`. Done, for the whole effort, means a
`git.py` an engineer can read end to end, a `coga/sync` git section that
fits the same page as the plan, and the behavioral guarantees the plan keeps
still covered by tests.

## Context

- Audit scope — every checkout with `coga/coga.toml` under `~/Code` on the
  owner's machine; re-run `find ~/Code -maxdepth 3 -name coga.toml` rather
  than trusting this list. As of this writing: `admin`, `coga`,
  `demo-hackathon`, `magicator`, `multiply`, `patents`, `tablet`, `xpllm`,
  plus linked worktrees `coga-*` (4) and `multiply-*` (3); several sit on
  `dream/*`, `codex/*`, or PR branches, and `multiply` shares 2 orphaned
  coga stashes with its worktrees. The `design` step is launched attended
  so reads outside this checkout do not stall on permission prompts.
- Evidence, and what each source can show. `coga/log.md` records only
  `sync failed` / `sync refused` / `refresh failed` lines, never successes.
  The durable trace of the success paths is the control-branch commit
  subject: `Ticket: …` = `sync_task_state`, `Log: …` = `sync_log`,
  `Sync coga state` = `sync_coga_state` (this repo's last 400 `coga/`
  commits: 245 / 97 / 44). The special cases — compensation trees,
  force-with-lease assists, stash restore, strict publication — leave no
  positive trace, only failures or leftovers: `git stash list`, `git reflog`
  on the control branch, `.coga/` run records, and `git log -- coga/` on
  control vs. feature branches for state that landed in the wrong place.
- `fix-git-sync-failure` (draft) is superseded by this ticket, not a
  prerequisite: its description is the first audit finding (refresh and
  publish are the same operation on the control branch and must not differ;
  `refresh_coga_state_from_control`'s `merge --ff-only` leaves a local-ahead
  control branch stranded; `_sync_paths_on_control_branch_strict` refuses a
  `HEAD` merely ahead by coga's own unpushed commits) and its `## Context`
  names the symbols, the two `launch.py` callers, and the repro tests worth
  keeping. It also notes `recurring_runner._rebase_checked_out_branch_onto`
  as a third integrate-remote routine.
- Public surface of `git.py` today, by consumer across `src/coga` — 29
  modules import it; enumerate with `grep -rn "git\." src/coga` at design
  time, the counts here drift. Heaviest: `sync_task_state`,
  `ticket_state_guard`, `write_ticket_under_barrier` /
  `state_publication_barrier` / `restore_files_under_barrier`,
  `feature_publication_lease`, `sync_paths`, `sync_log`,
  `capture_task_mutation_snapshot`, `ticket_routing_state`,
  `refresh_coga_state_from_control`, `sync_coga_state`. Beyond that, ~70
  call sites across ~20 private names reach in directly (`_toplevel`,
  `_run_git`, `_tree_bytes`, `_control_branch_present`,
  `_sync_paths_without_barrier`, `_remote_configured`, `_commit_paths`,
  `_fetch_branch_oid`, …): the real surface is several times the public
  list.
- Where the complexity lives, as things the plan must explicitly keep or
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
  - *Launch-end pull-back* (`refresh_coga_state_from_control`) — a separate
    integrate-remote path from `_push_control_branch`'s fetch+rebase (and
    from `recurring_runner._rebase_checked_out_branch_onto`); the plan
    should leave one.
  - *Stash-based dirty-tree handling* (`_rebase_onto_remote`,
    `_stash_if_dirty`, `_restore_to_orig`) — the orphaned stashes in
    `multiply` show the restore path does not always run, contradicting the
    "no leftover stash" claim in the contention section of the sync context.
  - *Barriers and leases* (`state_publication_barrier`,
    `FeaturePublicationLease`, `FileMutationRollback`) — in-process
    transactions around ticket writes.
  - `coga/log.md` union merge (`merge=union` via `.gitattributes`,
    `union_merge_paths`) — the one piece that is clearly simple and should
    stay. `git.py` also defines a `_union_merge_paths` alias for it and uses
    the underscore name internally; drop the alias.
- Contexts cited, not attached. `coga/sync`
  (`coga/contexts/coga/sync/SKILL.md`) is the spec this ticket rewrites, so
  it is read at the design step, not composed; the design step must read
  `## Control-branch contention and merge=union` and `## Git — durable
  task-state sync` through `## Design rule for new features` in full.
  `coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`) owns the
  microkernel rule and test expectations; the fact that matters: `git.py`
  is shared infra (≥2 consumers) and stays in core, but a single-consumer
  helper does not belong there — if the owner chooses "implement here",
  reconsider attaching `coga/codebase` for that step. `coga/architecture`
  (`coga/contexts/coga/architecture/SKILL.md`): `Where a fact lives: docs vs
  contexts` decides which surface owns each fact when the sync context is
  rewritten, and the "state admission/publication barrier" paragraphs under
  `## Status is the signal` are the spec for `state_publication_barrier` /
  `FeaturePublicationLease` — read them before deciding what a barrier must
  still guarantee. The packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`
  must be updated byte-identically (`tests/test_packaging.py`).
- Principles the plan cannot trade away — `coga/principles`
  (`coga/contexts/coga/principles/SKILL.md`) is cited, not attached; the
  design step reads `## 1. Hackable`, `## 3. Obvious`, and `## 6. Fail loud`
  in full. The facts the plan depends on: markdown on disk is the source
  of truth, git is the durable transport, the control branch is canonical for
  task state, no hidden state, boring standard git operations over clever
  ones, and failures are loud and non-fatal (a sync miss never crashes a
  command or loses the on-disk edit).
- Multi-checkout reality the plan has to cover: the owner runs coga from
  several repos, sometimes offline, sometimes from a PR branch, sometimes
  with linked worktrees (`is_linked_worktree`). Concurrent agents push to the
  same control branch (contention is real; `_MAX_SYNC_ATTEMPTS`).
- Out of scope: the notification half of `coga/sync` (Slack), the
  `coga usage` transcript-matching ambiguity seen in the same `multiply`
  session (separate ticket if it recurs).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
