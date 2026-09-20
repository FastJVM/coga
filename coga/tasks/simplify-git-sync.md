---
title: Simplify git sync
status: in_progress
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
step: 2 (evaluate-design)
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

### Acceptance criteria

- [ ] `src/coga/git.py` ≤ 900 lines and ≤ 30 top-level functions; no
      function longer than 80 lines; no `_`-prefixed name imported outside
      the module (`grep -rn "git\._" src/coga` is empty).
- [ ] Coga never creates a commit on a local branch: after any sequence of
      `mark`/`bump`/`block`/`create`/`delete`/recurring create in a
      checkout on `<control>`, `git rev-list origin/<control>..<control>` is
      empty whenever the push succeeded, and `git stash list` is unchanged.
- [ ] Offline publish leaves the file dirty and unchanged, writes one `sync
      failed` line, exits 0; the next `sync_coga_state` with the remote back
      publishes it and leaves the tree clean.
- [ ] Contention: two checkouts publishing different tickets on the same
      base both land (second retries once); publishing the same ticket from a
      stale base is refused with the `git checkout origin/<control> -- <path>`
      hint; `coga/log.md` appended on both sides keeps both lines.
- [ ] `expect` CAS: two megalaunch claims from the same control revision —
      exactly one wins; the loser's local ticket is restored to its pre-write
      bytes and no commit reaches control.
- [ ] Regression rules: `done`/`canceled` on control is never replaced except
      by a writer passing `expect` for that exact blob; `step`/status never
      decrease except under `allow_step_rewind`; a ticket whose control copy
      carries a `launch_generation` the local pre-write copy did not is
      refused (Open Question 3 fixes the sweep's rule).
- [ ] After a publish from a feature-branch or detached checkout in a repo
      whose `main` is held by another worktree, that worktree's `main`, index,
      and files all advance to the new tip when it was at the base; when it
      was ahead, nothing there moves and one stderr line names `git pull
      --rebase`.
- [ ] `refresh` on a control checkout that is behind fast-forwards; ahead or
      diverged reports the `pull --rebase` line and returns `False`; on a
      feature branch it touches nothing and returns `True`. A launch teardown
      followed by a megalaunch pick in a checkout whose remote moved meanwhile
      admits the pick (the `fix-git-sync-failure` end-to-end shape).
- [ ] No `refs/coga/*` refs and no `FETCH_HEAD` reads remain in `src/coga`.
- [ ] The sweep publishes only dirty paths under `tasks_dir(cfg)`,
      `log_path(cfg)`, and `coga/recurring/`; a dirty context or skill is left
      alone.
- [ ] `coga/contexts/coga/sync/SKILL.md`'s git section fits one page (≤ 150
      lines) and states nothing `git.py` does not do; the packaged twin is
      byte-identical (`tests/test_packaging.py`); `docs/` carries no second
      copy of the contract.
- [ ] `python -m pytest` passes; `tests/test_git.py` covers each bullet
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
under `~/Code` (`find ~/Code -maxdepth 3 -name coga.toml`: 15 hits — 8 primary
clones + 4 `coga-*` and 3 `multiply-*` linked worktrees). No repo overrides
`[git]`: every one is `origin` / `main` / enabled. Method: `git rev-list
--left-right --count`, `git stash list`, `git for-each-ref refs/coga`, `git
log --format=%s main -- coga/` bucketed by subject prefix, and every
`sync failed` / `sync refused` / `refresh failed` line in `coga/log.md`
classified by message text (script kept in the session scratchpad, not the
repo). "unknown" means no trace either way.

### Per checkout

| checkout | shape | control | state commits on control `Ticket:` / `Log:` / `Sync coga state` (share of sweep) | failure lines by class | leftovers | recovered cause |
|---|---|---|---|---|---|---|
| `coga` | primary, on `main`, in sync with origin | main | 2573 / 990 / 786 (18 %) | 478 total: 185 read-only-FS (`FETCH_HEAD`/`index.lock`, Jun–Jul sandbox), 77 step/status-backward refusals, 70 launch-claim refusals (all Sept), 63 rebase/stash misses (`could not reapply local changes`, `could not rebase … CONFLICT`), 61 offline fetch, 13 `merge --ff-only` refresh misses | 2 stashes, both hand-made (`WIP on (no branch)` 09-09, a stranded worktree 08-27); `coga/log.md` dirty (this session); 0 `refs/coga/*` | Claim refusals: one ticket refused 18× over 24 h after an offline bump cleared its claim; a human hand-committed `Reconcile stranded step-3 bumps after failed sync` (09-10 22:22). Step-backward refusals: same file refused up to 14× (07-15) — a stale copy the sweep re-offers on every command. Refresh misses: local `main` ahead by coga's own offline commits (the `fix-git-sync-failure` shape). |
| `multiply` | primary, on `main`, in sync | main | 685 / 408 / 388 (26 %) | 192: 143 offline fetch (DNS), 22 rebase/stash misses, 15 guard refusals, 8 refresh `--ff-only` misses, 3 read-only FS | 2 stashes (`coga log.md launch line (session b8b9626f)` 09-09, `coga open-pr borrow: …` 09-09) — **agent-made** (natural-language messages; `git.py`'s only stash message is `coga-sync-autostash`, present in no repo); 1 dirty ticket (`v1/debug-messages.md`, 46-line deletion); 1 orphaned `refs/coga/fetch/<uuid>` | All 15 refusals are `terminal status would change from 'done' to 'active'` on the three recurring period tickets (09-14 14:04, re-refused 16:13): the recurring rollover *recreates* a done ticket at the same path and the regression guard reads it as a backward move. Hand-fixed 30 h later: `Recurring: land the 2026-09-14 period tasks stranded by the digest crash` (09-15 20:43). |
| `xpllm` | primary, on `main`, in sync | main | 563 / 117 / 236 (26 %) | 167: 160 read-only FS (Jul), 5 guard, 1 rebase, 1 offline | 2 stashes (May–Jun, human), 1 orphaned `refs/coga/fetch/<uuid>` | quiet since 09-14; recurring autofix creates dominate recent history |
| `admin` | primary, on `main`, in sync | main | 834 / 297 / 291 (20 %) | 29: 20 offline, 5 read-only FS, 3 rebase, 1 fetch | none | 228 megalaunch lines — second-heaviest megalaunch user |
| `magicator` | primary, **on a feature branch** (`observation-loop/…`, repo rule: single checkout, no worktrees), `main` in sync | main | 877 / 204 / 258 (19 %) + 2 `Refresh coga state after launch` (feature-branch refresh commits) | 82: 72 read-only FS, 7 offline, 1 rebase, 1 refresh | 3 stashes (`autostash` 08-25 — git's own, from a human rebase; two 2025 WIPs) | the originating repo of `stop-syncing-task-state-onto-the-feature-branch`; 27 `Ticket:` + 17 `Log:` commits sit on remote feature branches (all pre-PR #785); no coga command has run here since 08-28, so the post-#785 reconcile path is untested here |
| `patents` | primary, on `main`, in sync | main | 416 / 85 / 86 (15 %) | 10: 4 read-only FS, 4 push 403/protected, 2 other | 3 stashes (May, human) | idle since 07-24 |
| `demo-hackathon` | primary, **left on `dream/resync-phase4-retro-isolation`** by a Dream run; `main` in sync | main | 80 / 40 / 32 | 21: 20 read-only FS, 1 fetch | none | idle since 07-27; 2 hand-authored `coga/` commits on the dream branch (PR content, not state) |
| `tablet` | primary, **left on `dream/notification-claims`** by a Dream run; `main` in sync | main | 116 / 28 / 37 | 0 | none | idle since 08-17 |
| `coga-dispose-checkouts`, `coga-packaged-context-states`, `coga-remove-narrative-candidates`, `coga-ticket-done-criteria` | linked worktrees of `coga`, PR branches created 09-18/19, 1–2 ahead / 27–82 behind `main` | main | **0** state commits; 0 reconcile merges | — (share `coga`'s log) | 1–2 hand-authored `coga/` commits each (contexts/skills = PR content) | Coga commands never run in these worktrees: the launched agent's cwd is the primary checkout on `main`; the worktree is only where code is edited. |
| `multiply-harness-evidence`, `multiply-harness-wording`, `multiply-optim-harness` | linked worktrees of `multiply`, 0–7 ahead / 16–168 behind | main | 0 state commits | — | none | same as above |

Offline episodes: `multiply` 143 and `coga` 61 `Could not resolve host` fetch
failures, concentrated Aug–Sep; every one is a transition that committed
locally (on `main`) and never pushed until a later transition's rebase.

### Where the primary checkout was on a PR branch by accident

In `coga`, 09-18: the primary checkout sat on `gh-backed-readonly-context`
(PR #836, 8 code commits) while two *other* tickets ran their steps. Result on
that remote branch: 15 state commits (`Ticket:`/`Log:` for
`the-ticket-interview-…` and `installer-managed-skills-…`) and 13
`Merge main state into gh-backed-readonly-context` reconcile merges. The PR's
`coga/` diff against `main` is clean (the reconcile did its job); the branch
history is not. `cite-symbols-rule` (PR #793) shows the same: 19 reconcile
merges. Those 31 merges are the only positive trace of the post-#785
feature-branch machinery anywhere in the audited repos.

### Per special case — exercised outside tests?

| special case (symbols) | live trace | verdict |
|---|---|---|
| control-branch commit + push (`_sync_paths_on_control_branch`, `_push_control_branch`, `_commit_paths`) | ~11 000 `Ticket:`/`Log:`/`Sync coga state` commits across repos | dominant path |
| push-reject → fetch + rebase with explicit stash (`_rebase_onto_remote`, `_stash_if_dirty`, `_restore_to_orig`) | 85 misses across repos (`could not reapply local changes after rebasing`, `could not rebase … CONFLICT` in a hand-edited context, `untracked working tree files would be overwritten`); successes leave no trace; **no `coga-sync-autostash` stash exists anywhere** | fires; its restore-on-failure holds; the "orphaned stashes" in `multiply` are not its doing |
| cross-branch overlay landing (`_land_paths_on_control_branch`, `_build_overlay_tree`, temp `GIT_INDEX_FILE`, `commit-tree`) | magicator's history; `coga` 09-18 incident (state reached `main` while HEAD was a PR branch) | fires whenever a primary checkout is off `main` |
| feature payload reconcile (`_reconcile_feature_payload`, adopt/merge, `_generated_commit_rels`, `_landed_generated_rels`, `_control_history_contains_generated_paths`, `_report_base_sync`) | 31 `Merge main state into …` commits since 09-11, all in `coga`, all from the accidental-branch case | fires; only by accident |
| feature-branch publication / assist lease / force-with-lease / compensation trees (`_prepare_feature_branch_publication`, `feature_publication_lease`, `FeaturePublicationLease`, `_build_feature_compensation_tree`, `_inverse_compensated_bytes`, `_merge_inverse_bytes`, `_single_assist_push_url`) | `publish_current_branch` pushes are visible (the 09-18 state commits are on `origin/gh-backed-readonly-context`); 67 `launched (operator=…)` human-step assist launches in `coga`, 0 elsewhere; compensation trees fire only after a failed control landing that followed a feature push — no trace | push half: fires; lease/compensation half: **unknown** |
| strict control publication (`_sync_paths_on_control_branch_strict`, `_land_strict_state_on_control`, `_raise_strict_control_landing_failure`, `_restore_strict_state_commit`) | megalaunch: 372 launches in `coga`, heavy in `admin`; `launch claim publication refused: … moved from verified tip` 09-18 17:17 (stderr only, per `fix-git-sync-failure`) | load-bearing for megalaunch; refuses correctly; its precondition (`HEAD == fetched tip`) is what the local-ahead branch breaks |
| launch-claim seal (`_pending_launch_admission_reason`, `_ticket_launch_claim_change_reason`, `_changes_involve_launch_claim`, released-witness recovery) | 70 `published launch claim would be cleared without an authorized session-ending lifecycle transition` refusals in Sept (`coga`) | fires; the documented allowance for "retry of an offline bump" did **not** fire in the one incident it was written for — a human hand-committed the ticket 24 h later |
| state-regression guard (`_ticket_state_regression_reason`, `_guard_coga_state_regressions`, `_STATUS_PROGRESS`) | 77 (`coga`) + 15 (`multiply`) + 5 (`xpllm`) refusals | fires; two false-positive shapes: recurring period rollover (done → recreated active) and a stale file re-refused on every subsequent command with no convergence |
| catch-all sweep (`sync_coga_state`, `_coga_state_pathspecs`) | 15–26 % of all state commits per repo | fires constantly; it is also the *only* retry mechanism after an offline transition |
| sweep extras: contexts relocation (`_removed_paths_from_previous_contexts_root`, `_previous_contexts_root_snapshot`, `_contexts_root_from_revision`), root layout (`_ROOT_LAYOUT_COGA_PATHS`) | no repo sets `[layout] contexts`; every repo is nested `coga/coga.toml` | **unknown** — no live consumer today |
| launch-end pull-back (`refresh_coga_state_from_control`, `_refresh_branch_from_control`, `_refresh_log_from_control`) | 13 + 8 + 3 + 1 `refresh failed: merge --ff-only` misses; 2 `Refresh coga state after launch` feature-branch commits in magicator | fires; the control-branch half fails exactly when coga's own offline commits sit on local `main` |
| local control ref fast-forward through the holding worktree (`_try_update_local_ref`, `_worktree_holding_branch`) | `main` reflog shows 2–78 `Fast-forward` entries per repo (mixed with human `pull`s) | fires; indistinguishable from human pulls |
| UUID-scoped isolated fetch refs (`refs/coga/fetch/<uuid>`, `--no-write-fetch-head`) | present in every Sept fetch failure line; **1 orphaned ref each in `multiply` and `xpllm`** | fires; cleanup is not reliable |
| contention loop exhaustion (`_MAX_SYNC_ATTEMPTS`) | 0 `after N attempts — contention` lines in any repo | **unknown** (never exhausted) |
| detached-HEAD scoped commits (`commit_detached`, detached baselines) | 0 detached reflog entries in any repo; one hand stash `WIP on (no branch)` in `coga` | **unknown** |
| barriers / rollback / snapshots (`state_publication_barrier`, `FileMutationRollback`, `restore_files_under_barrier`, `capture_*`) | in-process only; by design no trace | **unknown** — cannot be observed from repos |
| no-remote / control-branch-mismatch / `enabled=false` soft skips | no repo lacks a remote or renames control; no `coga.local.toml` disables git | **unknown** outside `coga init` and tests |
| `coga/log.md` union merge (`union_merge_paths`, `.gitattributes merge=union`) | every rebase/overlay that touched `log.md` — zero `log.md` conflicts in any failure line | works |
| `recurring_runner._rebase_checked_out_branch_onto`, `_land_recurring_create_on_control_branch`, control-worktree service | recurring creates land daily; `STALE_CONTROL_EXIT_CODE` bails leave no log line | fires; a second sync implementation (~600 lines) outside `git.py` |

### Size, for the plan's accounting

`src/coga/git.py` 7 285 lines, 141 functions (21 public / 120 private), 10
classes; 59 symbols consumed from 32 modules, 31 of them private. By bucket
(definition lines): feature-branch lease/assist/compensation 972; overlay +
reconcile 969; dispatch/entry points/log sync 1 075; barriers/rollback/
snapshots 910; strict publication + claim seal 585; regression guard 469;
refresh 510; plumbing 517; sweep + relocation 276; **control-branch
push/rebase/stash 208**. `tests/test_git.py`: 225 tests — 72 feature/assist/
lease, 27 overlay/reconcile/detached, 17 strict/claim, 17 guard, 16 sweep/
layout, 13 refresh, 9 push/rebase/contention, 7 soft-skips, 4 barrier, 3
union, 40 other; 12 other test files reach `git.py` symbols.
