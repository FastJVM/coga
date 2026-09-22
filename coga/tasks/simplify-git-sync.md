---
title: Simplify git sync
status: done
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
agent: claude
---

## Description

Coga's git sync does something simple — commit coga state (`coga/tasks/**`,
`coga/log.md`) on every transition, push it to the control branch, and pull
the control branch's state back into the checkout — but the implementation
has grown far past that: `src/coga/git.py` is ~7,300 lines (141 functions,
120 private, 31 of them reached into from 32 modules), `tests/test_git.py`
is 225 tests of similar size, and the `coga/sync` git section is ~90 KB. It
still fails in live repos. The usage audit (blackboard, `## Audit`, taken
2026-09-20 from all 15 checkouts under `~/Code`) found the root causes; the
findings the plan rests on are:

- **A1 — local-first commits are the live failure.** Every `merge --ff-only`
  refresh miss (13 `coga`, 8 `multiply`, 3 `patents`, 1 `magicator`), every
  megalaunch `moved from verified tip` refusal, and all 85 stash/rebase misses
  descend from one behavior: when a push fails (204 offline fetches in
  Aug–Sep), `_sync_paths_on_control_branch` has already committed on local
  `main`, and only a later transition's `_rebase_onto_remote` repairs the
  divergence.
- **A2 — the feature-branch machinery fires only by accident.** Coga commands
  run from a primary checkout on `main` in every repo; the 7 linked worktrees
  carry **zero** state commits. The only post-#785 trace of the reconcile
  path is 31 `Merge main state into …` merges on two `coga` PR branches
  (#836: 15 state commits + 13 merges on an 8-commit PR) because the primary
  checkout was left on a branch. ~1,950 `git.py` lines and 99 tests serve
  that case; the lease/compensation half has no trace at all.
- **A3 — the guard + sweep pair strands state instead of converging it.** A
  refused ticket is re-offered by every later command's sweep (14× and 18×
  for one file). Both September strandings ended with a human hand-commit
  after 24–30 h: `multiply`'s recurring rollover (`done` ticket recreated as
  `active` at the same path, refused as a backward move) and `coga`'s claim
  clear after an offline bump (the documented "retry of an offline bump"
  allowance did not fire).
- **A4 — the leftovers are not where the ticket assumed.** `git.py`'s only
  stash message (`coga-sync-autostash`) exists in no repo; `multiply`'s two
  stashes are agent-made. The real leftovers are one orphaned
  `refs/coga/fetch/<uuid>` each in `multiply` and `xpllm`, and dirty tickets
  that never converge (A3).
- **A5 — what is actually load-bearing:** the control-branch commit+push
  (~11,000 commits), the catch-all sweep (15–26 % of state commits and the
  *only* retry after an offline miss), the `log.md` union merge (zero
  conflicts ever), megalaunch's cross-checkout claim (372 launches in
  `coga`, heavy in `admin`), and the cross-branch overlay landing (the way
  state reaches `main` when HEAD is not `main`).

The owner confirmed the direction on 2026-09-20 (this session): the
**never-commit-locally** model below, with the two tradeoffs it carries
recorded under `## Open Questions` as accepted decisions.

### Invariants

- **I1 — canonical.** `origin/<control>` is the only durable home of
  `coga/tasks/**`, `coga/log.md`, and `coga/recurring/**`. A write is durable
  when, and only when, it is on that ref. Coga never creates a commit on any
  local branch; the checkout's `main` only ever fast-forwards.
- **I2 — nothing is lost.** The on-disk markdown is the write. A publish that
  cannot reach control leaves the file exactly as written (dirty), reports
  once on stderr + `coga/log.md`, never crashes the command, and is retried
  by the next command's sweep. `coga/log.md` is only ever appended and only
  ever three-way union-merged, never overlaid.
- **I3 — nothing moves backward.** A ticket on control never has its lifecycle
  (`status` ladder, `step` index, terminal state) decreased by a stale
  checkout, and a ticket carrying a `launch_generation` on control is not
  replaced by a writer that did not base itself on that exact control copy.
  The only backward move is a human `coga bump --to/--backward`. A refusal
  names the one-line fix (`git checkout origin/<control> -- <path>`).
- **I4 — one integrate path.** "Make this checkout's control branch equal
  `origin/<control>`" is one function used by publish, refresh, and the
  recurring entry gate alike.

### Proposed shape

**One write primitive.** `git.publish(cfg, paths, message, *, expect=None)
-> bool` in `src/coga/git.py`:

1. Resolve `root = toplevel(cfg.repo_root)`; soft-skip (one calm line, no
   commit) when git is disabled, not a repo, control branch absent
   (`control_branch_mismatch_message`), or no remote configured
   (`remote_configured`) — the four existing soft-skips, unchanged.
2. `base = refs/remotes/<remote>/<control>` (optimistic; no fetch on the hot
   path). Read `expect` and the I3 rules against `base`'s tree
   (`ticket_regression_reason(base_blob, worktree_bytes)`, the two-rule
   successor of `_ticket_state_regression_reason`: terminal not replaced,
   step/status not decreased, `launch_generation` untouched unless the writer
   passed `expect` for that path). A refusal raises `StateRegressionError`.
3. Build the tree in a UUID-named temporary `GIT_INDEX_FILE` seeded from
   `base`: overlay every path in `paths` from the working tree (delete when
   the file is gone); for paths `git check-attr merge` reports as `union`
   (`union_merge_paths`), write `git merge-file --union` of (merge-base copy,
   base copy, worktree copy) instead of the overlay. If the tree equals
   `base`'s, return `False` (nothing to publish).
4. `commit-tree` on `base`, `push <remote> <new>:refs/heads/<control>`. A
   non-fast-forward rejection means `base` moved: `fetch <remote> <control>`
   (updating the remote-tracking ref — no `FETCH_HEAD`, no `refs/coga/*`),
   go to 2. Bounded by `MAX_PUBLISH_ATTEMPTS`; exhaustion is a `GitError`.
5. On success, `fast_forward_control(root, new)`: if a worktree holds
   `<control>`, `git -C <holder> add -- <paths>` then `merge --ff-only <new>`
   there (verified: a dirty file whose bytes equal the target blocks
   `--ff-only` until staged; staged, it fast-forwards cleanly); otherwise
   `update-ref refs/heads/<control> <new>`. A refused fast-forward (local
   `main` has unpushed *human* commits) is one stderr line naming
   `git pull --rebase <remote> <control>`; the publish already succeeded.

`expect` is `{rel_path: blob_oid | None}` — the blob the writer read before
it wrote (`git hash-object` of the pre-write bytes, `None` for "must not
exist"). Publish refuses when `base`'s blob differs. This is the whole
cross-checkout claim mechanism: megalaunch reads control's ticket, writes
`launch_generation`, publishes with `expect`; two checkouts starting from the
same revision cannot both win the push. The pending/plain two-phase protocol
stays megalaunch's, expressed as two `publish` calls.

**Three thin entry points keep their names and lose their kwargs:**
`sync_task_state(cfg, task_path, *, message, expect=None)` →
`publish([task_path, log_path(cfg)], …)`; `sync_log(cfg, *, message)` →
`publish([log_path(cfg)], …)`; `sync_coga_state(cfg)` → `publish` of every
dirty path under `tasks_dir(cfg)`, `log_path(cfg)`, and `coga/recurring/`
(from `git status --porcelain` on those pathspecs) with message
`Sync coga state`. Each catches `GitError`/`StateRegressionError` exactly as
today (`sync failed` / `sync refused` lines; `sync_log` stderr-only). No
`guard=`, `feature_publication=`, `publish_current_branch=`,
`commit_detached=`, `land_union_files_to_control=`, `raise_*`, or
`generated_paths=` parameters survive; callers that need "refuse and tell
me" pass `expect` and catch `StateRegressionError` from `publish` directly.

**One integrate path.** `git.refresh(cfg) -> bool`: `fetch <remote>
<control>`; if HEAD is `<control>`, `merge --ff-only
refs/remotes/<remote>/<control>` (refusal = one line naming `git pull
--rebase`); otherwise return `True` without touching files — a feature-branch
or detached checkout is stale-by-design for tickets other checkouts advance,
and `stale_coga_task_rels` keeps warning in `coga status`. Callers:
`launch._refresh_launch_checkout` (teardown), the recurring preflight in
`commands/launch.py` (bail on `False`), and `recurring_runner`'s entry gate
(replaces `_rebase_checked_out_branch_onto` and `_sync_control_checkout_ahead`).

**One lock.** `git.state_lock(cfg)`: the existing per-checkout `fcntl.flock`
from `state_publication_barrier`, renamed, kept for the read-modify-write of
ticket files by same-checkout processes; `publish` takes it around steps 2–5.
`write_ticket_under_barrier` becomes `write_ticket(cfg, path, bytes)` inside
`state_lock`. `FileMutationRollback`, `restore_files_under_barrier`,
`capture_task_file_bytes`, `capture_revision_file_bytes`,
`capture_task_mutation_snapshot`, `FeaturePublicationLease`,
`feature_publication_lease`, `FeaturePublicationError`,
`UncertainFeaturePublicationError` are deleted: under I2 a failed publish
leaves the on-disk write in place, so there is nothing to roll back; a caller
that must not proceed on failure (megalaunch before spawn) rewrites the ticket
from the bytes it read — its own two lines, not a barrier class.

**Keep / drop, each tied to a finding**

| current piece | fate | because |
|---|---|---|
| control-branch commit + push (`_sync_paths_on_control_branch`, `_push_control_branch`, `_commit_paths`, `_commit_task_dir`) | replaced by `publish` steps 3–5 | A1: the local commit is the defect, the push is the value |
| push-reject rebase + stash (`_rebase_onto_remote`, `_stash_if_dirty`, `_pop_stash`, `_restore_to_orig`, `_run_git_quiet`) | **dropped** | A1: no local commit ⇒ nothing to rebase; contention is the CAS retry in step 4 |
| cross-branch overlay (`_land_paths_on_control_branch`, `_build_overlay_tree`, `_overlay_paths_from_bytes`/`_from_revision`, `_merge_union_bytes`, `_tree_bytes`, `_tree_entry_mode`) | **kept**, folded into step 3 as the *only* landing for every branch shape | A5: it is how state reaches `main` from anywhere; making it universal removes the branch split |
| local feature commit + payload reconcile (`_reconcile_feature_payload`, `_generated_commit_rels`, `_landed_generated_rels`, `_control_history_contains_generated_paths`, `_report_base_sync`, `_land_and_reconcile_log`, `_restore_unpushed_sync_commit`) | **dropped** | A2: fires only by accident; 13–19 merges per branch is a worse disease than the one #785 cured; I1 forbids the local commit |
| feature publication: `publish_current_branch`, `_prepare_feature_branch_publication`, `_feature_publication_lease`, `_push_ref` leases, force-with-lease assists, `_single_assist_push_url`, `_remote_push_urls`, `_remote_branch_descends_from`, compensation trees (`_build_feature_compensation_tree`, `_inverse_compensated_bytes`, `_merge_inverse_bytes`) | **dropped** | A2: no trace for the lease/compensation half; under I1 coga never pushes a PR branch — the usage-log commit after a gated bump and `open_pr._sync_pr_record` go to control only |
| strict publication (`_sync_paths_on_control_branch_strict`, `_land_strict_state_on_control`, `_raise_strict_control_landing_failure`, `_restore_strict_state_commit`, `_require_checkout_tip`, candidate probes, released-witness handling in `git.py`) | **replaced** by `expect` | A5: megalaunch's guarantee is a per-file CAS on control; `publish` gives every writer the same one |
| launch-claim seal (`_pending_launch_admission_reason`, `_ticket_launch_claim_change_reason`, `_changes_involve_launch_claim`, `_assist_control_ticket_guard`, detached baselines) | **replaced** by one I3 rule: when control's copy carries a `launch_generation` that the local copy lacks or differs from, refuse — unless the writer passed a matching `expect` (megalaunch's own phases) or the local copy is a session-ending transition relative to control (`step` greater, or status left `in_progress`). The sweep passes no `expect`, so the second clause is what lets an offline `bump` retry converge (Open Question 3) | A3: the HEAD-blob allowance failed in its one incident because it depended on a local commit that I1 removes; a lifecycle comparison needs no baseline |
| state-regression guard (`guard_ticket_state`, `ticket_state_guard`, `_guard_coga_state_regressions`, `_ticket_state_regression_reason`, `_STATUS_PROGRESS`, `_ticket_lifecycle_state`, `TicketRoutingState`, `ticket_routing_state`) | **kept as `ticket_regression_reason`** (~60 lines) inside `publish`, plus `allow_step_rewind` for `advance_step(rewind=True)` | A3/I3: the rules are right; the binding machinery is not. Recurring rollover passes `expect={ticket: <done blob>}` meaning "replace this exact terminal copy", which is a replace, not a regression |
| catch-all sweep (`sync_coga_state`, `_coga_state_pathspecs`, `_ROOT_LAYOUT_COGA_PATHS`, contexts-relocation tracking, `_ignored_untracked_paths`) | **kept, narrowed** to tasks + log + recurring, config-derived; relocation/root-layout code dropped | A5: it is the retry mechanism; hand-authored contexts/skills/workflows are review work (policy already says so); no repo relocates contexts or uses the root layout |
| launch-end pull-back (`refresh_coga_state_from_control`, `_refresh_branch_from_control`, `_refresh_log_from_control`, `_RefreshCommit`) | **replaced** by `refresh` | A1/I4: the control half is `fetch` + `--ff-only`; the feature-branch half committed on the branch (I1) |
| local control ref update (`_try_update_local_ref`, `_worktree_holding_branch`, `_WORKTREES_UNKNOWN`) | **kept** as `fast_forward_control` (step 5) | A5: what keeps the `main` checkout coherent after a publish from elsewhere |
| UUID fetch refs (`_fetch_branch_oid` with `refs/coga/fetch/*`, `--no-write-fetch-head`) | **dropped** for the remote-tracking ref | A4: leaks refs; the CAS is the push, not the fetch |
| `coga/log.md` union merge (`union_merge_paths`, `.gitattributes`) | **kept**; `_union_merge_paths` alias dropped | A5 |
| barriers/rollback/snapshots | `state_lock` kept; the rest dropped (above) | I2 |
| soft-skips (`enabled=false`, non-git, control mismatch, no remote), `summarize_git_failure`, `stale_coga_task_rels`, `last_commit_times`, `is_linked_worktree`, `STALE_CONTROL_EXIT_CODE` / `RETRY_WITHOUT_SWEEP_EXIT_CODE` | **kept** | unchanged contracts; the exit codes keep the CLI's "do not sweep after a refused rewind/leased command" behavior |
| plumbing (`_run_git`, `_toplevel`, `_current_branch`, `_remote_configured`, `_control_branch_present`, `_control_branch_mismatch_message`, `_symbolic_head`, `_relative_to_root`) | **kept, made public** (`run_git`, `toplevel`, …) — the 31 private reach-ins become a sanctioned surface of ~10 names | the audit shows they are the real API |

**Every `src/coga` consumer, by module** (from `grep -rn "git\." src/coga`
this session; counts drift, names do not):

- `mark`, `bump`, `commands/bump`, `commands/mark`, `commands/block`,
  `commands/unblock`, `blocker_reminders`, `recurring_autofix`,
  `commands/create`, `create`, `commands/retire`, `authoring`,
  `notification/__init__` — call `sync_task_state`/`sync_paths` with
  `guard=`/lease kwargs → call `sync_task_state(cfg, path, message=…,
  expect=…)`; `sync_paths` is removed (its two non-task users, `authoring`
  and `notification`, call `publish` with their explicit paths). `mark`'s
  `stranded_product_paths` moves next to its single consumer.
- `megalaunch` — `_sync_paths_without_barrier`, strict publication,
  `FileMutationRollback` ×7, `restore_files_under_barrier` ×3,
  `ticket_state_guard` ×4, `_fetch_branch_oid`, `_remote_push_urls` → reads
  control's ticket blob via `run_git(root, "rev-parse",
  f"refs/remotes/{remote}/{control}:{rel}")` after `refresh`-style fetch,
  publishes each claim phase with `expect`, and restores its own pre-write
  bytes on failure. The pending/plain protocol and `released:` witness are
  unchanged in meaning.
- `commands/launch` — 25 distinct names including
  `_prepare_feature_branch_publication`, `feature_publication_lease` ×4,
  `refresh_coga_state_from_control` ×2, `_sync_paths_without_barrier` →
  `refresh`, `sync_task_state`, `sync_log`, `state_lock`, `run_git`,
  `toplevel`. The human-step assist keeps its checkout alignment (its own
  code); its PR-tip lease and `publish_current_branch` are removed.
- `launch_script` — `capture_task_file_bytes`, `capture_revision_file_bytes`,
  `feature_publication_lease` ×4, `ticket_routing_state` ×2 → `sync_task_state`
  + `sync_log`; the "result publication" lease becomes a plain publish.
- `pr_assist` — `feature_publication_lease`, `_single_assist_push_url`,
  `FeaturePublicationError` → the module's lease half is deleted; what
  remains (PR identity checks) uses `run_git`.
- `open_pr` — `sync_paths(publish_current_branch=True)` → `sync_task_state`
  (control only); `union_merge_paths` kept.
- `recurring_runner` — the heaviest reach-in (`_build_overlay_tree`,
  `_push_ref`, `_is_non_fast_forward`, `_try_update_local_ref`,
  `_MAX_SYNC_ATTEMPTS`, `_push_control_branch`, `_commit_paths` ×4,
  `_tree_bytes` ×3, `_fetch_branch_oid` ×2, `_worktree_holding_branch`,
  `_run_git` ×12, `_toplevel` ×4, `_remote_configured` ×2,
  `_remote_push_urls`) → `_land_recurring_create_on_control_branch`,
  `_sync_recurring_create_on_checked_out_control_branch`,
  `_sync_control_checkout_ahead`, `_commit_global_log`, and
  `_rebase_checked_out_branch_onto` are replaced by `publish(..., expect=…)`
  and `refresh`; the control-worktree service (`_service_from_control_worktree`
  and its owner file) stays as is (it is about where recurring *children run*,
  not about sync) and uses `run_git`.
- `cli` — `sync_coga_state` at the dispatch boundary and
  `RETRY_WITHOUT_SWEEP_EXIT_CODE`: unchanged.
- `blackboard`, `validate`, `delete_task`, `retire_worklist` —
  `state_publication_barrier` → `state_lock`.
- `commands/delete` — `sync_paths(update_local_control_ref=False)` (Retro's
  isolated delete) and `is_linked_worktree` → `publish(..., fast_forward=False)`
  is the one optional flag kept on `publish`.
- `commands/recurring` — `sync_paths` → `publish`.
- `commands/init` — `_control_branch_present`, `_symbolic_head`, `GitError` →
  public names, unchanged behavior.
- `autoclose`, `branchsweep`, `version_skew`, `skill_manager`, `views` —
  `_toplevel`, `_run_git`, `_remote_branch_oid`, `last_commit_times`,
  `stale_coga_task_rels` → public names.

**Child tickets, one PR each, in order** (each updates its slice of
`coga/contexts/coga/sync/SKILL.md` and the packaged twin in the same PR, per
`CLAUDE.md`; each cites `simplify-git-sync` in its `## Context`):

1. **`publish` + `refresh` replace the control path** — add `publish`,
   `fast_forward_control`, `refresh`, `ticket_regression_reason` with
   `expect`; route the three entry points through `publish`; delete the
   local-commit, rebase/stash, strict, feature-publication, reconcile, and
   UUID-fetch code; port `mark`/`bump`/`open_pr`/`launch`/`launch_script`/
   `pr_assist`/`megalaunch` to the slim signatures. This PR alone closes
   `fix-git-sync-failure` and A1–A2. Tests: rewrite `tests/test_git.py`
   around the guarantees list under acceptance; keep the `git_repo`
   fixture. Largest PR; it is one PR because the strict/ordinary/feature
   split cannot be removed piecemeal without shims.
2. **`state_lock` replaces the barrier classes** — delete
   `FileMutationRollback`, `restore_files_under_barrier`, `capture_*`,
   `write_ticket_under_barrier`; port `megalaunch`, `launch`, `mark`, `bump`,
   `block`, `unblock`, `blackboard`, `validate`, `delete_task`,
   `retire_worklist`, `launch_script`, `recurring_runner`.
3. **`recurring_runner` adopts `publish`/`refresh`** — delete its private
   landing loop, `_rebase_checked_out_branch_onto`,
   `_sync_control_checkout_ahead`; period rollover passes `expect` for the
   done copy it replaces (closes A3's `multiply` incident).
4. **Narrow the sweep and finish the context** — `sync_coga_state` to
   tasks + log + recurring; drop relocation/root-layout tracking; rewrite
   `## Git — durable task-state sync` and `## Control-branch contention and
   merge=union` to the one-page contract (invariants, the five steps, the
   soft-skips, the refusal message), delete the four `###` subsections; sync
   the packaged twin; `docs/` grep per `Where a fact lives`.

If the owner prefers a single PR, 1–4 in one branch is ~the same diff;
the split exists so each step is reviewable and the context shrinks with the
code.

### Evaluator findings — resolutions (owner-confirmed 2026-09-20, implement step)

The evaluate-design step recorded eight must-resolve findings (blackboard,
`## Evaluator review`). The owner advanced to `implement` with these
resolutions, which amend the shape above where they conflict:

- **E1 — pending seal.** `ticket_regression_reason` keeps today's byte-exact
  admission rule unconditionally: when control's copy carries
  `pending:<uuid>`, the only accepted replacement is the identical ticket with
  the prefix stripped; `expect` never overrides it, and a working copy carrying
  `released:` is refused outright. The final-fetch-to-release race test stays.
- **E2/E5 — a real baseline replaces the lifecycle ladder (closes Open
  Question 3).** `publish` defaults `expect` for every path to the blob at
  `git merge-base HEAD refs/remotes/<remote>/<control>` — what this checkout
  last integrated from control. The CAS passes when control's blob equals that
  baseline **or** already equals the working bytes (idempotent retry). An
  explicit `expect` entry overrides the default per path. Consequences: the
  offline bump/rollover retry converges with no hidden state; a same-ticket
  stale write is refused with the `git checkout origin/<control> -- <path>`
  hint; different tickets from one base both land; a peer blackboard edit is
  never overlaid. `_STATUS_PROGRESS`, `allow_step_rewind`, and
  `allow_terminal_change` are dropped: a `bump --backward` from a fresh
  checkout passes the CAS, from a stale one it is refused.
- **E3 — one integration function.** `fast_forward_control(root, new,
  published)` checks `git merge-base --is-ancestor <local> <new>` *first*
  (ahead or diverged: one stderr line naming `git pull --rebase`, index
  untouched, `False`); then, in the worktree holding `<control>`, writes the
  *published* bytes (the union result for `coga/log.md`) into each published
  path still equal to what `publish` read, `git add`s those, and
  `merge --ff-only`. With no holder it is `update-ref` with the old-oid guard
  after the same ancestry check. `refresh` is `fetch` + this function with no
  published paths (I4).
- **E4 — reentrant lock.** `state_lock` is process-reentrant (a module-level
  held count over the same flock), so `publish` takes it inside megalaunch's
  admission window without a `_without_barrier` escape hatch.
- **E6/E8 — three outcomes.** `publish` returns `True` (pushed), `False` (the
  built tree already equals control's), or `None` (soft-skipped). It raises
  `StateRegressionError` for *definitely not landed* (refused before any push
  was accepted) and `GitError` for *unknown or not durable*; either way the
  working file stays as written. A push error that is not a clean
  non-fast-forward rejection triggers one fetch, and `publish` returns `True`
  when control now carries the commit. Megalaunch restores its pre-write
  bytes only on `StateRegressionError`; on `GitError` it keeps the pending or
  `released:` witness as today.
- **E8 — no remote.** Stated exception to I1: with no remote configured,
  `publish` builds the same commit on local `<control>` and skips the push —
  canonical is local `<control>` when there is nothing to push to. When the
  remote-tracking ref is absent after a fetch, `publish` bases on local
  `<control>` and the push creates the remote branch. `fast_forward=False`
  is a keyword of `publish` (Retro's isolated delete).
- **E7 — one PR.** The frozen workflow has one `implement` and one `open-pr`;
  the four-child split is dropped and every consumer port, `recurring_runner`
  included, lands on this ticket's branch. `fix-git-sync-failure` is canceled
  with a pointer here.

### Acceptance criteria

- [~] `src/coga/git.py` ≤ 900 lines and ≤ 30 top-level functions; no
      function longer than 80 lines; no `_`-prefixed name imported outside
      the module (`grep -rn "git\._" src/coga` is empty). *Landed at 1,095
      lines / 50 functions (longest 70 lines, reach-ins empty); the ceiling
      is the number to renegotiate per Open Question 5 — see the
      blackboard.*
- [x] Coga never creates a commit on a local branch: after any sequence of
      `mark`/`bump`/`block`/`create`/`delete`/recurring create in a
      checkout on `<control>`, `git rev-list origin/<control>..<control>` is
      empty whenever the push succeeded, and `git stash list` is unchanged.
- [x] Offline publish leaves the file dirty and unchanged, writes one `sync
      failed` line, exits 0; the next `sync_coga_state` with the remote back
      publishes it and leaves the tree clean.
- [x] Contention: two checkouts publishing different tickets on the same
      base both land (second retries once); publishing the same ticket from a
      stale base is refused with the `git checkout origin/<control> -- <path>`
      hint; `coga/log.md` appended on both sides keeps both lines.
- [x] `expect` CAS: two megalaunch claims from the same control revision —
      exactly one wins; the loser's local ticket is restored to its pre-write
      bytes and no commit reaches control.
- [x] Regression rules (E2): a path whose control blob differs from both the
      checkout baseline (`merge-base HEAD origin/<control>`) and the working
      bytes is refused, with the `git checkout origin/<control> -- <path>`
      hint; an explicit `expect` overrides the baseline; a control copy
      carrying `pending:<uuid>` accepts only the prefix-stripped admission
      (E1); a working copy carrying `released:` is never published; an
      offline bump or rollover retried by the sweep lands when control did
      not move that path.
- [x] After a publish from a feature-branch or detached checkout in a repo
      whose `main` is held by another worktree, that worktree's `main`, index,
      and files all advance to the new tip when it was at the base; when it
      was ahead, nothing there moves and one stderr line names `git pull
      --rebase`.
- [x] `refresh` on a control checkout that is behind fast-forwards (explicit
      ancestry check, not `merge --ff-only`'s exit code); ahead or
      diverged reports the `pull --rebase` line and returns `False`; on a
      feature branch it touches nothing and returns `True`. A launch teardown
      followed by a megalaunch pick in a checkout whose remote moved meanwhile
      admits the pick (the `fix-git-sync-failure` end-to-end shape).
- [x] No `refs/coga/*` refs and no `FETCH_HEAD` reads remain in `src/coga`.
- [x] The sweep publishes only dirty paths under `tasks_dir(cfg)`,
      `log_path(cfg)`, and `coga/recurring/`; a dirty context or skill is left
      alone.
- [x] `coga/contexts/coga/sync/SKILL.md`'s git section fits one page (≤ 150
      lines) and states nothing `git.py` does not do; the packaged twin is
      byte-identical (`tests/test_packaging.py`); `docs/` carries no second
      copy of the contract.
- [x] `python -m pytest` passes; `tests/test_git.py` covers each bullet
      above with a named test.

### Out of scope

- The notification half of `coga/sync`; the `coga usage` transcript-matching
  ambiguity.
- Megalaunch's admission protocol itself (pending → plain, released witness,
  `validate_before_spawn`/`after_spawn`): it is re-expressed on `publish` +
  `expect`, not redesigned.
- The recurring control-worktree service (`_service_from_control_worktree`)
  and `coga launch`'s human-step checkout alignment — where sessions *run*
  is not sync.
- Reading ticket state from control in a feature-branch checkout (a
  "stale-by-design" checkout keeps its `coga status` warning; anything more
  is its own ticket).
- Any change to `[git]` config keys or to `.gitattributes` policy.
- Reconciling the existing leftovers in live repos (`multiply`/`xpllm`
  orphan refs, `multiply`'s agent stashes) — a one-line hand cleanup, noted
  on the blackboard.

## Context

- Audit evidence and method are on the blackboard under `## Audit`; the
  checkouts were `admin`, `coga`, `demo-hackathon`, `magicator`, `multiply`,
  `patents`, `tablet`, `xpllm` plus linked worktrees `coga-*` (4) and
  `multiply-*` (3), all `origin`/`main`. Re-run `find ~/Code -maxdepth 3
  -name coga.toml` if a number needs refreshing.
- **Where things are today** (symbols in `src/coga/git.py`; navigate with
  `grep -n "^def "`, do not trust line numbers): the entry points
  `sync_task_state` → `sync_paths` → `_sync_paths_without_barrier` →
  `_dispatch_branch_sync` (the 740-line branch switch: control /
  detached / feature); the control path `_sync_paths_on_control_branch` →
  `_commit_paths` → `_push_control_branch` → `_rebase_onto_remote`
  (`_stash_if_dirty`, `_pop_stash`, `_restore_to_orig`); the cross-branch
  landing `_land_on_control_branch` → `_land_paths_on_control_branch` →
  `_build_overlay_tree` (temp `GIT_INDEX_FILE`, `read-tree`, `update-index`,
  `write-tree`, `commit-tree`) and `_merge_union_bytes` (`git merge-file
  --union` of merge-base/base/worktree bytes — reuse this for step 3);
  `_try_update_local_ref` + `_worktree_holding_branch` (reuse for
  `fast_forward_control`, adding the `git add` of published paths before
  `merge --ff-only`); the guard `_ticket_state_regression_reason` and
  `_STATUS_PROGRESS` (reuse the rules; drop `allow_terminal_change`,
  `expected_lifecycle`, `checkout_ticket_bytes`); `refresh_coga_state_from_control`
  (keep only the `if branch == cfg.git_control_branch` block's intent);
  `state_publication_barrier` (becomes `state_lock` unchanged);
  `_coga_state_pathspecs` (replace with the three config-derived pathspecs).
- Verified git behavior for step 5 (scratch repo, this session): after
  building a commit on `origin/main` via temp index and pushing it,
  `merge --ff-only <new>` in the `main` checkout **refuses** while the
  published file is dirty even though its bytes equal the target; `git add
  -- <path>` first, then `merge --ff-only`, fast-forwards ref, index, and
  the rest of the tree. With local `main` ahead by an unrelated commit,
  `--ff-only` fails (expected) and `git rebase` refuses on the dirty file —
  which is why the plan never rebases.
- `expect` values: writers already hold the pre-write bytes — `mark`/`bump`
  read the ticket through `tasks.read_ticket` before `ticket.write`; hash
  with `git hash-object --stdin` (or `hashlib` over the git blob header) so
  no index is touched. The sweep has no pre-write bytes and passes none.
- `fix-git-sync-failure` (`coga/tasks/fix-git-sync-failure.md`, draft) is
  closed by child 1; its repro tests (control ahead + remote moved → refresh
  succeeds; diverged product file → clean tree + recovery hint; strict-ahead
  and end-to-end megalaunch-after-teardown) are the acceptance tests here,
  restated for `publish`/`refresh`. Mark it `canceled` with a pointer when
  child 1 is created.
- `stop-syncing-task-state-onto-the-feature-branch` (done, PR #785) is the
  origin of `_reconcile_feature_payload`; its five "properties" are
  superseded by I1 (no local commit ⇒ no payload to reconcile). Its
  `open_pr` publishability classifier stays.
- The recurring rollover writes: `recurring_runner._land_recurring_create_on_control_branch`
  with `restore_existing_control_task` / `overwrite_dirty_control_task`
  flags, and `_sync_recurring_create_on_checked_out_control_branch`; the
  period create deletes the done period ticket and creates the new one at the
  same path — under the plan that is `publish([path], expect={rel: <done
  blob>})`.
- Megalaunch's protocol is specified in `coga/contexts/coga/architecture/SKILL.md`
  under `## One shared agent-spawn path` and the `launch_generation`
  paragraph under `## Canonical ticket frontmatter`; the barrier paragraph
  under `## Status is the signal` is the spec `state_lock` must still meet
  (advisory, outside the worktree, released by the kernel). Those paragraphs
  shrink with child 2; the docs/contexts owner rule is `Where a fact lives:
  docs vs contexts` in the same file.
- Principles the plan holds to (`coga/contexts/coga/principles/SKILL.md`,
  `## 1`, `## 3`, `## 6`): markdown on disk is the write; git is transport;
  standard plumbing (`read-tree`/`write-tree`/`commit-tree`/`merge-file
  --union`/`merge --ff-only`) over stash/rebase choreography; every miss is
  loud and non-fatal.
- `coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`): `git.py` stays
  shared infra; `stranded_product_paths` (one consumer, `mark`) and the
  recurring-only helpers move to their consumers. Test expectations:
  `python -m pytest`; `tests/test_packaging.py` for the twin.
- Packaged twin: `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`.

<!-- coga:blackboard -->
## Dev

pr: https://github.com/FastJVM/coga/pull/848
branch: publish-sync
worktree: /home/n/Code/coga-publish-sync

## Open-PR (2026-09-20)

PR #848 opened by `coga open-pr` from the primary checkout (separate-worktree
layout); `origin/main` was ahead only by this ticket's own generated task/log
commits, which the command classified as safe. No review was ordered by the
implement step (the frozen workflow has no self-qa/peer-review step), so
nothing was in flight. Reviewer: see `### Acceptance deviations for the
reviewer` above (size ceiling, three behaviour changes) and the hand-cleanup
leftovers listed under the implement handoff.

## Implement handoff (2026-09-20)

Branch `publish-sync` (worktree `/home/n/Code/coga-publish-sync`), three
commits on top of `origin/main`: core+consumers, tests, contexts. Full suite:
2,400 passed (`.venv/bin/python -m pytest`, worktree venv from
`pip install -e ".[test]"`). `coga validate --json` from the worktree: the same
pre-existing warnings/errors as before (nothing about this ticket).
`fix-git-sync-failure` canceled with a pointer here.

### What changed

- `src/coga/git.py` rewritten: `publish` (candidates → base → provenance
  check → temp-index tree with `merge-file --union` for union paths →
  `commit-tree` + push, non-ff retry, ambiguous-failure re-read →
  `fast_forward_control`), `refresh`, `state_lock` (thread-reentrant),
  `write_ticket`, `fetch_control`, `ticket_regression_reason`, and a public
  plumbing surface (`run_git`, `toplevel`, `tree_bytes`, `current_branch`,
  `symbolic_head`, `remote_configured`, `remote_branch_oid`,
  `control_branch_present`, `control_branch_mismatch_message`,
  `relative_to_root`, `union_merge_paths`, `worktree_holding_branch`,
  `is_linked_worktree`, `last_commit_times`, `stale_coga_task_rels`,
  `summarize_git_failure`). 7,285 → 1,095 lines; 141 → 50 functions;
  `grep -rn "git\._" src/coga` empty; no `refs/coga/*`, no `FETCH_HEAD`
  (`github_preflight.check_branch_contains_control` now fetches into and
  reads the remote-tracking ref too).
- Consumers ported: `mark`/`bump` transitions take `strict=` instead of
  guard/lease/snapshot kwargs (`mark._publish` reports or re-raises);
  `commands/{bump,mark,block,unblock}` lose the assist lease/rollback code;
  `pr_assist` is identity only (`AssistSession`, `verify_recorded_assist_pr_head`);
  `launch_script` and `commands/launch` keep the assist alignment
  (`_align_recorded_assist_checkout`: fetch, ancestry check, Coga-state-only
  dirt, `merge --ff-only`) and attribution but publish to control only;
  `megalaunch` claims/activates with `sync_task_state(strict=True)`, revalidates
  via `fetch_control` + `tree_bytes`, admits with `publish(expect=pending)`;
  `recurring_runner` creates with one `publish(expect={ledger, template})` in a
  bounded loop that re-reads control on refusal and adopts a handled period,
  verifies delegated leases with `_verify_period_on_control`, and catches up
  with `git.refresh`; `open_pr` excludes live Coga state from the
  single-checkout cleanliness gate; `step_gate` loses `publish_current_branch`;
  `cli` loses the assist sweep suppression; `logfile.retract_log_lines` is the
  shared audit-line undo for definitely-refused strict writes.
- `stranded_product_paths` moved to `mark.py` (single consumer).
- Tests: `tests/test_git.py` rewritten (48 tests, one per guarantee);
  `test_launch.py` −49 lease/rollback/no-sweep tests, 12 assist tests adapted;
  `test_recurring.py`, `test_megalaunch.py`, `test_mark.py`, `test_open_pr*.py`,
  `test_launch_script.py`, `test_commands.py`, `test_cli.py`, `test_init.py`,
  `test_validate.py`, `test_authoring.py`, `test_period_state.py`,
  `test_layout_contexts.py` adapted; `conftest._stub_git` stubs `publish`.
- Contexts: `coga/sync` git section is 143 lines; `coga/launch-internals`
  rewritten; `coga/architecture` (barrier → state lock, admission paragraphs,
  assist identity), `coga/codebase`, `coga/blackboard`, `coga/recurring`,
  `coga/extension-model`, `dev/code`, `code/implement`, `code/open-pr`, the
  packaged `coga/cli`, `docs/operations.md`, `docs/concepts.md`. Twins synced
  (`tests/test_packaging.py` green).

### Decisions made while implementing (beyond the E1–E8 resolutions)

- **Provenance candidates include a per-worktree published tree.** A feature
  or detached checkout's HEAD never advances with control, so its second
  publish of the same ticket would fail a HEAD/merge-base-only baseline.
  `refs/worktree/coga/published` (git keeps `refs/worktree/*` private to each
  checkout; verified on git 2.43) records the blobs this checkout published;
  it is the fourth candidate next to HEAD, merge-base, and the working bytes.
  Inspectable with `git ls-tree refs/worktree/coga/published`; no `.coga/`
  state.
- **Candidates also include committed-ahead Coga state.** A clean file whose
  HEAD copy moved past control from a copy this checkout derived from (a
  feature branch that committed a ticket it had itself published) is
  published; a clean file merely behind control is not. Without this the
  blocked-resume reblock in a single checkout (ticket equal to a committed
  copy) never reached control.
- **Three failure classes, not two.** `GitError` = definitely not on control
  (offline, or the post-failure re-read shows control lacks the commit);
  `UncertainPublishError(GitError)` = push reported failure and control could
  not be re-read; `StateRegressionError` = refused. Strict callers restore
  and retract audit lines (`retract_log_lines`) on the first and third, keep
  the write on the second. This is E6 made precise.
- **`expect` on union paths.** An explicit `expect` for `coga/log.md` adds a
  CAS the union path otherwise never has; the recurring create uses it to pin
  the serviced ledger it decided from, so a peer's ledger line between fetch
  and push refuses the duplicate period (the old per-attempt re-check).
- **Seal before provenance.** The pending-claim message wins over the generic
  "control copy changed" message when both apply.
- **No-change publish fast-forwards only a control checkout.** A `False`
  publish never reaches into another worktree (Retro's isolated delete
  followed by the sweep must not move the primary).
- **Missing git binary is a soft skip** ("`git` not found on PATH (sync
  skipped)"), not a logged sync failure.
- **`_align_recorded_assist_checkout`** no longer requires exactly one push
  URL; the identity check reads `remote get-url --push`.
- **PR 747 finding fixed in passing**: released-witness reconciliation
  re-reads the witness after its fetch and refuses when it changed.

### Acceptance deviations for the reviewer

- Size: 1,095 lines / 50 functions vs the ≤ 900 / ≤ 30 target. Module and
  function docstrings carry the contract (the sync context links to them);
  folding further would replace explicit boundaries with dense helpers, which
  the evaluator warned against. Open Question 5 anticipated this.
- Behaviour changes worth knowing: a recurring named launch from a control
  checkout that is ahead of origin now creates and publishes the period but
  leaves that checkout un-fast-forwarded (one stderr line names
  `git pull --rebase`); previously Coga rebased the human's commits.
  `coga open-pr` in the single-checkout layout ignores dirty Coga state.
  Assist sessions no longer get exit 75 on refusals — there is nothing to
  retry-protect.

### Adjacent findings (not fixed here)

- `commands/init.py` still shells out to `subprocess.run` for `remote
  get-url`; could use `git.remote_configured`. Cosmetic.
- `recurring_runner._control_tip_owner` fetches from the push URL into the
  remote-tracking ref; a remote whose fetch URL differs then has its tracking
  ref pointing at the push repository's tip until the next fetch. Harmless
  (same repository in every configured repo today) but worth a note in
  `coga/recurring` if push/fetch URL splits ever appear.

### Leftovers to clean by hand once merged (unchanged from the design step)

`git update-ref -d refs/coga/fetch/<uuid>` in `multiply` and `xpllm`; the two
agent stashes in `multiply`; `multiply`'s dirty `coga/tasks/v1/debug-messages.md`.
Installed CLIs (`uv tool` editable at `/home/n/Code/claude/coga/src`) keep the
old sync until that checkout is updated.

## Decisions (implement step, 2026-09-20)

- Owner confirmed (attended session): one PR here, every consumer ported on
  this branch; the four-child split is dropped (E7).
- Owner confirmed the two design deviations: the CAS on the checkout
  baseline (`merge-base HEAD origin/<control>` blob) replaces the
  `_STATUS_PROGRESS` ladder and `allow_step_rewind` (E2/E5); with no remote
  configured `publish` commits on local `<control>` without pushing (E8).
  Full resolutions are in the ticket body under
  `### Evaluator findings — resolutions`.

## Evaluator review

2026-09-20 — **Not ready for implementation.** The never-commit-locally
model fits the shared-infrastructure boundary and the accepted offline/feature
checkout tradeoffs. The specified algorithm does not yet meet its safety and
convergence criteria. These findings concern the ticket body on its own terms;
the blackboard's open questions do not resolve the contradictions.

### Must resolve before implementation

1. **Preserve the pending admission seal, not just claim acquisition CAS.**
   `expect` proves which blob a writer read; it does not authorize that writer
   to replace a pending claim. A peer can read `pending:<uuid>` after the last
   admission fetch and publish a bump with matching `expect` before child
   release. The proposed lifecycle exception also permits that via the sweep.
   This breaks the explicitly unchanged admission protocol. Evidence:
   `architecture/SKILL.md` (under `coga/contexts/coga/`), **One shared
   agent-spawn path**; `src/coga/git.py::_pending_launch_admission_reason`;
   `tests/test_megalaunch.py::test_pending_claim_blocks_remote_lifecycle_between_final_fetch_and_gate`.
   Specify how pending bytes remain sealed and how only the admission
   transition can change them. Retain the final-fetch-to-release race test.

2. **The sweep cannot prove freshness from lifecycle fields.** Two copies
   with equal status, step, and generation but different blackboards pass the
   proposed guard: the second overlay loses the first writer's prose. An old
   claimless copy advancing a step also passes the session-ending exception
   even if a peer has since acquired a claim. Thus I2/I3 and the stale-same-ticket
   acceptance criterion conflict with the algorithm. Evidence:
   `tests/test_git.py::test_same_claim_edit_refuses_when_control_changed_since_checkout_baseline`
   and `test_catch_all_sync_cannot_release_a_claim_from_a_stale_baseline`
   already cover these cases. This is especially consequential when successful
   feature publication deliberately leaves a dirty file for every later sweep.
   Choose a provable baseline/merge policy or explicitly revise the guarantees;
   lifecycle comparison cannot establish the provenance asserted in Open
   Question 3. Define deletion and newly added claim handling too, since a
   missing blob has no lifecycle to compare.

3. **The integration recipe fails its ordinary contention case and can
   alter another checkout's index on refusal.** After union-merging remote
   and local log appends, the published log differs from local bytes. Staging
   the local file then running `merge --ff-only` refuses. I reproduced this in
   a disposable repo: base log `base`, published log `base/remote/local`,
   staged local log `base/local`; Git exits 1, “local changes ... would be
   overwritten.” On a diverged holder, staging happens before the refusal,
   violating the criterion that nothing there moves. From a feature checkout,
   the holder may have independent edits to these same paths. Evidence:
   `src/coga/git.py::_try_update_local_ref`, `_overlay_union_paths`, and
   `_merge_union_bytes` distinguish remote tree bytes from holder bytes today.
   Specify safe integration for merged bytes, unrelated staged/unstaged edits,
   deletions, and holder races. Also share this integration with `refresh`
   as I4 requires: its separate bare `merge --ff-only` recipe cannot handle
   pending dirty writes. A second scratch check found an ahead-only checkout
   returns 0 / “Already up to date,” contrary to the refresh acceptance
   criterion. Require an explicit ancestry check. The no-holder `update-ref`
   path also needs an ancestry check and old-OID comparison to honor “only
   ever fast-forwards” when local human commits exist.

4. **Renaming the unchanged flock and taking it inside every publish
   deadlocks existing admission callers.**
   `src/coga/git.py::state_publication_barrier` opens a separate descriptor
   for each acquisition; it is not reentrant. The post-release publication in
   `src/coga/megalaunch.py` explicitly calls `_sync_paths_without_barrier`
   because the supervisor already holds this lock (the comment calls out the
   deadlock). The new design removes that escape while making `publish` acquire
   the lock. Define lock ownership/nesting for read-modify-write, publication,
   and the entire admission window. Retain same-checkout concurrent-writer
   tests; moving the lock to publication alone is insufficient.

5. **Offline rollover still strands the exact case A3 promises to fix.**
   A recurring writer can initially supply `expect=<done blob>`, but after
   an offline failure its replacement remains dirty and the next sweep has
   no `expect`. The terminal guard refuses it forever. The on-disk replacement
   does not retain the authority to replace the terminal copy. Evidence:
   the proposed `sync_coga_state` signature/rules and
   `src/coga/recurring_runner.py::_land_recurring_create_on_control_branch`
   / `_sync_recurring_create_on_checked_out_control_branch` (the current
   rollover callers). Specify the retry owner and evidence that survive the
   failure, and add an offline-rollover-then-sweep acceptance case. Resolve
   the analogous retry of an explicitly authorized rewind.

6. **A failed push response is not proof that control rejected the write.**
   The server can accept a claim and the connection can fail before its
   acknowledgement. Blindly restoring pre-write bytes leaves a live control
   claim paired with an apparently unclaimed checkout; retrying the original
   `expect` then refuses the already-landed write. The design deletes candidate
   probes and uncertainty handling while saying admission/released-witness
   semantics are unchanged. Evidence: `src/coga/git.py::UncertainFeaturePublicationError`,
   `tests/test_git.py::test_strict_state_landing_probes_attempted_candidate_before_regression_cleanup`,
   and the post-release error paths in `src/coga/megalaunch.py`. Specify accepted,
   rejected, and unverifiable outcomes and their retained local state, including
   post-release witness recovery. Test a push that accepts but reports failure;
   the issue exists even with one remote destination.

7. **The four PRs are not independently implementable as ordered.** Child 1
   deletes `_commit_paths`, `_push_control_branch`, strict publication and
   related APIs while `recurring_runner` still calls them until child 3.
   Child 2 removes its barrier/snapshot dependencies before that migration too.
   Evidence: `src/coga/recurring_runner.py` still calls `_commit_paths` four
   times, `_push_control_branch`, and `_build_overlay_tree`; child 1's consumer
   port list does not include all the other `sync_paths` users. Move each
   consumer migration into the PR deleting its dependencies, or choose one
   atomic PR. Require each proposed intermediate PR to pass the suite. The
   frozen workflow is a single implementation/PR workflow; owner review must
   also settle whether this ticket implements or coordinates child tickets.

8. **Complete the public contract before handing it to an implementer.**
   `allow_step_rewind` is required but absent from the proposed publish and
   wrapper signatures; `fast_forward=False` appears only in the delete consumer
   list. Define how a rewind reaches the guard without restoring removed
   kwargs. `expect` is described both as concurrency validation and as permission
   to replace a terminal ticket: specify which regression rules it overrides
   (rollover may lower both status and step). Also, the “four existing soft-skips,
   unchanged” claim is incorrect for no remote:
   `src/coga/git.py::_sync_paths_on_control_branch(push=False)` deliberately
   commits locally today. The new no-commit behavior is consistent with I1,
   but must be stated as a change. Define bootstrap when the control branch
   exists but its remote-tracking ref does not, and the distinction between
   skipped/no-change/failed publication for strict launch callers. The current
   boolean API and early no-change return do not explain how they establish
   durable remote success.

### Optional recommendations

- Keep the size targets subordinate to correctness; avoid replacing explicit
  protocol boundaries with dense helpers merely to meet 30 functions. Split
  acceptance coverage between `test_git.py`, `test_megalaunch.py`, and recurring
  tests where the behavior is actually observable.
- Attach `coga/sync`, `coga/architecture`, and `coga/codebase` to implementation
  work. This ticket has no `contexts` field; its source pointers are useful
  but do not compose those behavioral contracts. Update architecture's
  admission/baseline contract in the same PR that changes it, not only the
  sync context and its packaged twin.

### Verification and scope

Read the frozen workflow, the shipped design-review skill/workflow, relevant
source and tests, product thesis, and canonical context sections. Ran isolated
Git plumbing probes in `/tmp` for union-result integration, ahead-only refresh,
and staging before a divergent merge. No source, test, ticket-body, branch,
or PR changes were made; no full suite was run for this design-only review.
The historical 15-checkout audit was treated as supplied evidence, not rerun.

## Decisions (design step, 2026-09-20)

- Owner confirmed the never-commit-locally model in the attended design
  session, including its two tradeoffs: (a) an offline write stays dirty in
  the working tree until the next command's sweep instead of being committed
  on local `main`; (b) a feature-branch/detached checkout gets no local state
  commit and no refresh — its published ticket stays dirty there and its
  `coga status` is stale-by-design for other checkouts' tickets. Reason: (a)
  removes the whole local-ahead failure family (A1) by construction; (b)
  removes ~1,950 lines that fire only by accident (A2). The conservative
  alternative (keep local-first, fix only the refresh — the
  `fix-git-sync-failure` plan) was offered and declined.
- Sweep narrowed to tasks + log + recurring: hand-authored contexts/skills/
  workflows already are review work per the sync policy; the one conflict
  ever seen in a rebase was a swept hand-edited context (08-19).
- Entry-point names `sync_task_state` / `sync_log` / `sync_coga_state` stay
  (32 consumers, readable git history by subject); `sync_paths` goes.
- `publish` reads `refs/remotes/<remote>/<control>` optimistically and
  fetches only after a rejected push, so the common case adds no network
  round-trip over today's push.
- Leftovers to clean by hand once child 1 lands (not code): `git update-ref
  -d refs/coga/fetch/<uuid>` in `multiply` and `xpllm`; the two agent stashes
  in `multiply` (`git stash drop` after a look); `multiply`'s dirty
  `coga/tasks/v1/debug-messages.md` (46 deleted lines — decide whether that
  deletion is wanted before the next sweep publishes it).

## Open Questions

1. **One PR or four?** The plan splits into four child tickets so the
   context shrinks with the code; child 1 is still ~5,000 deleted lines and
   ~12 consumer modules. If the owner prefers "implement here", attach
   `coga/codebase` for the implement step and expect one large PR.
2. **Agents committing the dirty ticket into a PR** (tradeoff b). The plan
   relies on `open_pr`'s existing generated-only classifier and on the
   implement/open-pr skills saying "do not `git add` `coga/tasks/**`". Should
   child 1 also make `open-pr` refuse a PR whose diff touches
   `coga/tasks/**` or `coga/log.md` outside deliberate prose (the classifier
   already distinguishes), or is a warning enough?
3. **The sweep's claim rule.** Without a pre-write baseline the sweep can
   only compare lifecycle content: allow replacing a control ticket that
   carries a `launch_generation` when the local copy's `step` is greater or
   its status left `in_progress`; refuse otherwise. This admits an offline
   bump's retry (the 09-10 incident) and still refuses a stale copy. Is the
   owner comfortable that a session-ending transition is provable from
   lifecycle fields alone, or should `bump`/`mark` persist the pre-write blob
   oid beside the write (e.g. a `.coga/pending-publish/<slug>` file) so the
   retry can pass a real `expect`? The plan recommends the lifecycle rule —
   no hidden state.
4. **`refresh` on a feature checkout returns `True` and does nothing.** The
   recurring preflight and launch teardown treat that as "verified". For a
   team that mandates single-checkout feature branches (magicator's rule)
   this means launched sessions may read stale sibling tickets. Accept, or
   make `coga launch` refuse to start from a non-control checkout unless
   `--allow-stale-checkout`? The plan recommends accept + the existing
   `coga status` warning.
5. **Target size.** Acceptance says ≤ 900 lines / ≤ 30 functions for
   `git.py`. If the implementer lands well under that, fine; if the
   `expect`/regression rules push it over, the ceiling is the number to
   renegotiate, not the invariants.

## Audit

Read-only inventory taken 2026-09-20 from every checkout with `coga/coga.toml`
under `~/Code` (15 hits: 8 primary clones, 7 linked worktrees, all
`origin`/`main`). Its findings are the A1–A5 bullets in `## Description`; the
full per-checkout and per-special-case tables are in this ticket's history
(`git show 65a9e63e:coga/tasks/simplify-git-sync.md`, section `## Audit`).
Headline numbers: ~11,000 state commits across repos; 478 `coga` failure
lines (185 read-only-FS, 77 step-backward refusals, 70 claim refusals, 63
rebase/stash misses, 61 offline, 13 refresh misses); 15 `multiply` refusals all
from the recurring rollover; zero `coga-sync-autostash` stashes anywhere; one
orphaned `refs/coga/fetch/<uuid>` each in `multiply` and `xpllm`; zero state
commits in any linked worktree. `git.py` was 7,285 lines / 141 functions
(31 private names reached from 32 modules); `tests/test_git.py` 225 tests.
