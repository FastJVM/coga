---
title: Recover when local main carries hand commits of coga state
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
step: 5 (open-pr)
agent: claude
---

## Description

When local `main` carries commits that touch only Coga state (`coga/tasks/**`, `coga/log.md`, `coga/recurring/**`) and are not on origin, Coga can no longer bring the control checkout level. `fast_forward_control` (`src/coga/git.py`) prints a `git pull --rebase` note, and `coga launch` refuses ("bringing this checkout to a clean 'main' at origin/main refused to change the checkout"). The operator's `git pull --rebase` then also fails, because the unpublished log lines Coga appended in the meantime leave `coga/log.md` dirty. Recovery is manual, and the documented command does not work.

There are two gaps. Content may already have reached origin through an earlier publication, but `_plan_preparation()` refuses on ancestry before checking content. Alternatively, a clean hand-committed ticket has never been published: today's `sync_coga_state()` passes only dirty paths to `publish()`, so `_candidates()` never sees that ticket. This ticket passes the full configured state areas to the existing publisher, allowing its provenance checks to select eligible committed state as well as dirty state, and adds one shared deterministic realignment guard. After publication, when every local-only commit touches only Coga state and its remaining content changes are already on control, the CLI realigns local `main` to control. Otherwise it refuses with an actionable remedy. Agents are never asked to judge or repair this.

This ticket and the draft `fix-coga-git-sync-failures-that-leave-main-diverge` share the guard: its item 3 ("fast-forward when local content already matches origin") is delivered here by the same helper. That ticket keeps its root-cause work (sandboxed `hash-object` / `fetch` failures) and should cite this guard rather than add a second one.

This changes the `coga/sync` contract on purpose. The sweep considers eligible committed state as well as dirty state, using the existing publication guards; clean state merely behind control is still not a write. The local control branch either fast-forwards or *realigns*: the local ref moves to the control commit after the guard proves that local-only commits are state-only and their net changes are already on control. Publication still creates its own commits on the control tip rather than pushing the hand commits. Realignment never stashes, rebases, resets hard, or commits, and refuses while a Git operation is in progress.

### Acceptance criteria

- [ ] `sync_coga_state()` passes the configured tasks directory, log path, and recurring directory to `publish()` without narrowing them to `_dirty_paths()` or filtering out absent paths. This applies on control and feature checkouts, including a completely clean checkout with eligible committed state. `_candidates()`, `_provenance()`, `_guard()`, union merging, and push retry remain the publication authority: clean state behind control is not republished, and a committed ticket whose control copy moved beyond its provenance stays unselected. Code, contexts, skills, and workflows outside the configured state areas remain outside the sweep.
- [ ] A new helper in `src/coga/git.py` (working name `_local_control_subsumed(cfg, root, local, target)`) returns a frozen result with `kind` (`ok`, `foreign`, `unpublished`, or `unproven`), `reason`, blocking paths, dropped commit IDs/subjects, and proof evidence. It returns `ok` only when all of the following hold:
  - `git merge-base --all local target` yields exactly one base.
  - Every commit in `target..local`, checked **per commit** (`git log --no-renames --format= --name-only -m target..local` or equivalent), touches only paths under `_state_areas()`. A commit that touched code and a later commit that reverted it still fails.
  - Every path in `git diff --no-renames --name-only <base> <local>` passes `_published_proof()` with the local tip's entry as "working" (mode, bytes, or absent), `_tree_entry(target, rel)` as "published", and the merge-base entry as `head_entry`, plus `union=` from `union_merge_paths()`. Same existence, mode and bytes; for a `merge=union` path such as `coga/log.md`, union-merging the local copy onto control changes nothing. A symlink or submodule entry fails.
  - `foreign` names offending non-state commits and paths; `unpublished` lists each failed content proof after all commits have passed the state-only check. No or multiple merge bases, unsupported entries, and inspection errors are `unproven`, with the failed revision, path, or operation named. They fail closed and do not masquerade as unpublished content or suggest rebase as a proven remedy.
- [ ] `prepare_control_checkout()` (`_plan_preparation()` / `_apply_preparation()`) no longer refuses a diverged or ahead local control when the helper returns `ok` for `(local, pinned)`. The helper's evidence, including union-attribute decisions, is part of the re-observed plan evidence. Apply then realigns control to `pinned` and verifies a clean `main` at `pinned` exactly as today. Every existing check stays: detached HEAD, in-progress op, other worktree holding `main`, the per-path dirt proof, and ignored collisions.
- [ ] Realignment uses only `git read-tree -m -u HEAD <pinned>` (when HEAD is control; it refuses on conflicting dirty files) and `git update-ref refs/heads/<control> <pinned> <local>` (old-value guarded). With HEAD on a feature branch, the ref moves first and then the existing `git switch` runs. No `stash`, `rebase`, `reset --hard`, commit, or push.
- [ ] Each realignment writes one stderr line naming the dropped commits (short SHA and subject) and saying they remain in the reflog. Nothing is written to `coga/log.md` from inside preparation, because that would dirty the just-verified tree.
- [ ] `fast_forward_control()` uses the same helper. When `local` is not an ancestor of `new` and the helper returns `ok`, it realigns: through `update-ref` with an old-value guard when no worktree holds control, or `read-tree -m -u` plus `update-ref` when this checkout (`root`) holds it, after the existing `staged` step. Another worktree holding a diverged control is left alone with a note, as today. As a result `refresh()` returns `True` in this case, and the recurring pre-scan catch-up (`recurring_runner`, the `git.refresh` call in its control catch-up) no longer stalls on it.
- [ ] Before **any** staging, working-file change, or ref move on that realignment path, `fast_forward_control()` checks the invoking checkout using the same `_IN_PROGRESS_MARKERS` policy as preparation. An active merge, rebase, cherry-pick, revert, or bisect returns `False` with a finish-or-abort remedy; HEAD, index, files, and operation markers are unchanged by this call. Inspection failure also refuses before mutation. This applies through `refresh()` and after publication; publication may already have landed remotely, but does not authorize disturbing the local operation.
- [ ] For `unpublished`, the `_plan_preparation()` refusal and `fast_forward_control()` note list failing paths/reasons and suggest `git pull --rebase --autostash <remote> <control>` on the control checkout, then retrying the command. When preparation starts on a feature branch, the remedy explicitly says to switch to control before pulling; pulling on the feature branch would not repair local control. Any local commit touching non-state paths keeps today's refusal and reconciliation wording, with `--autostash` added. `refresh()` keeps its boolean interface; the `recurring_runner` catch-up reason directs the operator to the diagnostic just emitted and then to retry, instead of adding an unconditional pull command that would contradict an operation or inspection refusal.
- [ ] Regression test `tests/test_git.py`, 2026-10-01 shape: seed a ticket and a tracked log; on local `main`, commit a state-only change to the ticket (a hand commit); append unpublished lines to `coga/log.md` (dirty); push a competing commit to origin touching another state path. Run `sync_coga_state()` then `prepare_control_checkout()` (the launch entry order). Assert `prepared`, `main == origin/main`, a clean tree, the hand-committed ticket bytes on origin, and every locally appended log line present on origin's `coga/log.md`.
- [ ] Test: the same shape, but control's copy of the hand-committed ticket also changed after the merge-base, so the sweep cannot carry it. Assert preparation is `refused` and changes no local ref, index, or files relative to its post-sweep input (the sweep may publish the log). Run the suggested `git pull --rebase --autostash origin main` as given in the message; require exit 0, then retry `sync_coga_state()` and `prepare_control_checkout()`. Assert `prepared`, clean `main == origin/main`, both ticket edits and all log lines preserved on origin. Real conflicts still require human resolution; this fixture changes well-separated lines so rebase applies without a conflict.
- [ ] Sweep tests cover committed-only state in a clean checkout, control and feature checkouts, clean state behind control, a committed deletion even when its state directory is now absent, and exclusion of non-state files. Existing provenance and publication-regression tests keep passing.
- [ ] Test: a local commit touching `local.txt` (or touching state *and* code) is still refused. The existing `test_prepare_refuses_an_ahead_or_diverged_control_and_changes_nothing` and `test_refresh_refuses_an_ahead_or_diverged_control_checkout` keep passing, with their asserted string updated to include `--autostash`.
- [ ] Test: `fast_forward_control()` / `refresh()` realign a subsumed diverged control checkout, and leave alone a control holder in another worktree.
- [ ] Test: a subsumed state-only divergence plus an unfinished `merge --no-commit --no-ff` with staged code refuses realignment without changing HEAD, index, files, or `MERGE_HEAD`. Exercise `refresh()` and a direct `fast_forward_control(..., staged=...)` call, proving the operation check precedes staging. Cover every `_IN_PROGRESS_MARKERS` entry and inspection failure in the shared operation check.
- [ ] Direct guard tests cover code changed then reverted, merge commits with non-state changes, zero/multiple merge bases, deletions, executable modes, symlinks/submodules, and committed union-log content. Preparation tests cover HEAD on a feature branch with no control holder, proof evidence changing before apply, and a clean verified result after realignment.
- [ ] Docs, canonical and packaged twins kept byte-identical (`tests/test_packaging.py`):
  - `coga/internals/state-publication`: invariants 1 and 4, the post-publication integrate path, and the end-of-command sweep's expanded candidate scope.
  - `coga/internals/git-refresh`: opening paragraph, `fast_forward_control` including operation refusal, `refresh` outcomes, and `prepare_control_checkout`.
  - `dev/checkouts`: launch boundary steps 1, 2, and 4, and remedy text.
  - `coga/sync`: Git summary, control-checkout bullet, and sweep summary.
  - `coga/internals/recurring-control`: pre-scan integration and ahead/diverged refusal wording. Search these topics and implementation docstrings for remaining fast-forward-only or dirty-only sweep claims and correct them in the same PR.
- [ ] `python -m pytest` passes.

### Proposed shape

1. **Sweep discovery.** In `sync_coga_state()`, call `publish(cfg, [tasks_dir(cfg), log_path(cfg), recurring_dir(cfg)], message)` after the existing publishable-root check. Remove the outer dirty-path narrowing and existence filter, including the `if paths` gate. `_publish_locked()` already returns without making a commit when `_candidates()` is empty. Keep candidate provenance, sealed-ticket checks, union merging, and push retries unchanged. This exposes eligible committed state to the existing publisher, including on retry after rebase; it does not force publication of a committed path that the publisher declines.
2. **Guard** (`src/coga/git.py`, beside `_published_proof()` in the checkout-preparation section). Add `_local_control_subsumed()` with the frozen result specified above. Reuse `_state_areas()`, `_in_state_area()`, `_tree_entry()`, `_published_proof()`, and `union_merge_paths()`. Use NUL-delimited path output, disable rename detection, retain commit IDs for per-commit diagnostics, and use `GIT_LITERAL_PATHSPECS` for path probes as `_tree_entry()` does. For the local tip's bytes use `_tree_entry(local, rel)` plus `_blob_bytes()`; reject unsupported modes explicitly before calling `_published_proof()`, which does not itself reject identical symlink modes. Include the pinned/local/base IDs, dropped commits, examined entries, and union-attribute decisions in proof evidence. A failed Git probe or an ambiguous base yields `unproven`, never `ok`.
3. **Preparation.** In `_plan_preparation()`, replace the bare `_is_ancestor` refusal. If not an ancestor, call the guard. On `foreign`, `unpublished`, or `unproven`, refuse with the corresponding diagnostic, and `blocking=(control,)` plus relevant paths. On `ok`, record `realign=True` on `_PreparationPlan` and include the guard's full evidence in `evidence`. In `_apply_preparation()`:
   - HEAD on control: after the restores and removals, `read-tree -m -u HEAD pinned`, then `update-ref` with an old-value guard.
   - HEAD elsewhere: `update-ref` (old-value guard), then the existing `switch`.
   
   Skip the `merge --ff-only` when realigned. Keep the existing verification. Each mutation gets its own `stage` label for the `failed` report.
4. **`fast_forward_control()`.** In the not-ancestor branch, check for an in-progress operation in the invoking checkout, then call the guard with `(local, new)`. Factor preparation's existing marker inspection into a shared helper used by both callers; a marker or inspection failure must return before `staged` processing. On `ok`, resolve the holder and leave another holder untouched. With this checkout holding control, preserve the existing `staged` handling, then `read-tree` and guarded `update-ref`; with no holder, use guarded `update-ref` alone. Return `True` only after success. On refusal or error, report the corresponding reason and return `False`. Keep the ancestor fast-forward path unchanged. Update the docstrings.
5. **Messages.** The guard owns commit/path diagnostics; callers add the appropriate remedy. `foreign` retains manual reconciliation wording, `unpublished` names `git pull --rebase --autostash <remote> <control>` on control then retry, operation refusal says finish or abort, and `unproven` reports what could not be proved without prescribing a rebase. The retried sweep now discovers the rebased clean ticket and publishes through the existing guard instead of requiring a plain push. `_sync_control_checkout_ahead()` keeps the boolean `refresh()` API and points to its emitted diagnostic rather than supplying a second, generic rebase remedy; describe failed catch-up as failure to bring control level, since fast-forward is no longer the only successful path.
6. **Tests** in `tests/test_git.py`, beside the existing `test_prepare_*`, `test_refresh_*`, and sweep tests, using `git_repo` helpers (`_seed_ticket`, `push_competing_commit`, `_dirty`, `_head`, `_assert_prepared`). Seed the log as tracked before testing autostash. Add a recurring catch-up assertion for the changed remedy wording. The launch boundary itself and `_checkout_refusal_message()` stay unchanged.
7. **Docs** as listed in the acceptance criteria, edited in `docs/contexts/` and mirrored to `src/coga/resources/templates/coga/bootstrap/contexts/`. Correct implementation docstrings in `git.py` and `recurring_runner.py` alongside their changed behavior.

### Out of scope

- Root causes of failed syncs (sandboxed `hash-object` / `fetch` / `index.lock`): the sibling ticket `fix-coga-git-sync-failures-that-leave-main-diverge`.
- Bypassing `_candidates()` or its provenance rules when control's copy moved meanwhile. The broader sweep still skips that committed path; the operator reconciles it with rebase, then retries the now-capable sweep. Eligible committed-only state discovery is in scope.
- Realigning a diverged control checked out in *another* worktree.
- Any prompt rule telling agents not to commit Coga state (canceled by owner decision), and any detection of *who* made the commit.
- A backup ref or log entry preserving dropped commits beyond the stderr line and the reflog (see Choices retained for owner review).
- Changing `_checkout_refusal_message()` or the boundary flow in `src/coga/commands/launch.py`. `_CheckoutBoundary.enter` / `settle` already call `sync_coga_state()` then `prepare_control_checkout()`, which is the order the guard relies on.

## Context

- **Launch boundary order.** `src/coga/commands/launch.py`, `_CheckoutBoundary.enter()` and `.settle()`, each call `git.sync_coga_state()` and then `git.prepare_control_checkout()`. With this ticket's expanded discovery, the sweep can land eligible hand-committed state before preparation pins and proves. Exempt launches and recurring use `git.refresh()` → `fast_forward_control()` instead (`_refresh_launch_checkout()`, and the control catch-up in `recurring_runner` that calls `git.refresh`); refresh alone only realigns content already on control and does not acquire publication behavior.
- **Current discovery gap and reuse.** Today's sweep narrows `publish()` to dirty individual paths. Within supplied pathspecs, `_candidates()` can also add a clean path when `git diff base HEAD` lists it and control's blob is in `_provenance()` (HEAD, `refs/worktree/coga/published`, merge-base) minus HEAD's blob. Passing full state areas makes this existing logic available to the sweep. `_guard()` still decides whether selected content may land. If control moved beyond provenance, the committed ticket is unselected; after a successful rebase, the new merge base supplies the provenance needed on retry.
- **Proof reuse.** `_published_proof(root, rel, working, published, *, head_entry, union)` already implements "already on control", including the union rule (`_merge_union_bytes(current=control, base=head_entry, other=working) == control`). Passing the merge-base entry as `head_entry` gives the right three-way base for committed log lines.
- **After a publish.** In `_publish_locked()`, `fast_forward_control()` is called with `staged=` (path → bytes read, bytes landed). When control is diverged it currently returns before the staging step. A realigning path must keep that staging step so the published log comes clean before `read-tree -m -u`.
- **Operation safety.** `_plan_preparation()` checks `_IN_PROGRESS_MARKERS` today. `fast_forward_control()` currently relies in part on `merge --ff-only` refusing an unfinished merge. `read-tree -m -u` does not provide that refusal for a clean pending merge, so the new realignment path must explicitly share the marker check before staging.
- **Existing tests whose asserted string changes:** `test_fast_forward_leaves_an_ahead_main_alone_and_names_the_fix`, `test_refresh_refuses_an_ahead_or_diverged_control_checkout`, and `test_prepare_refuses_an_ahead_or_diverged_control_and_changes_nothing`. All three use a non-state `local.txt` commit, so their outcome stays a refusal.
- **Other `pull --rebase` text:**
  - `src/coga/commands/launch.py` has an unrelated branch-freshness message ("reconcile it (`git pull --rebase`) first") for the feature branch, outside this ticket.
  - Docs containing the old wording: `dev/checkouts` and `coga/internals/recurring-control`, plus their packaged twins.
- **Incident evidence:** the operator's working fix was `git pull --rebase --autostash origin main` then `git push`. The rebase dropped `ec16e4e6c` as already upstream.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (design step, 2026-10-01)

- Plan confirmed by the owner in-session: one shared guard (`_local_control_subsumed`) used by `prepare_control_checkout` and `fast_forward_control`. Realign is `read-tree -m -u` plus an old-value `update-ref`, with no stash, rebase, or reset. The suggested command becomes `git pull --rebase --autostash`, then retry.
- Contract change to defend at review-design: "local control only fast-forwards" becomes "fast-forwards or realigns when every local-only commit is Coga state already proven on control."

## Choices retained for owner review

1. **Preserving dropped commits.** Retain the existing design choice of stderr plus reflog, with no backup ref or deferred log write.
2. **The `unpublished` remedy.** Retain rebase with autostash, then retry without a plain push. The revised design now includes the sweep discovery change this remedy requires; the retry acceptance test must prove complete recovery.
3. **Recurring.** Retain shared realignment through `refresh()` during recurring catch-up, with a stderr report and explicit operation refusal. Refresh does not publish missing state itself.

These are the spec's retained choices, not an approval to advance the owner gate.

## Owner-review revisions (2026-10-02)

At the owner's request to fix the findings, revised the ticket body only:

- **Evaluator finding 1 addressed in the design:** broaden sweep discovery to
  all configured state paths, including absent paths and clean checkouts;
  keep the publisher's existing provenance checks. Corrected the false claim
  about current sweep behavior and made the rebase test assert successful
  retry, both ticket edits, all log lines, and a clean prepared checkout.
- **Evaluator finding 2 addressed in the design:** share the existing Git
  operation-marker check with the realignment caller and run it before
  staging, file writes, or ref moves. Added unchanged-state regression
  requirements for a pending merge, all marker kinds, and inspection failure.
- Resolved the result-type ambiguity with a frozen four-kind result, made
  ambiguous/failed proof distinct from unpublished content, specified proof
  evidence and additional guard tests, and expanded the documentation scope
  to remove contradictory fast-forward-only and dirty-only claims. Recurring
  catch-up points to the specific diagnostic rather than overriding it with
  a generic rebase hint.
- **Verification:** temporary real-Git probes using `init_git_repo`,
  `_seed_ticket`, `push_competing_commit`, and existing `git.publish()` with
  the full state paths confirmed both routes: an eligible committed ticket
  is published; a competing edit to that ticket is initially skipped, then
  `git pull --rebase --autostash origin main` exits 0 and a retried publication
  preserves both edits and the appended log. In each route the specified
  committed-content proof passes afterward. These verify the publication
  design with existing code, not the unimplemented realignment helper.
- `coga validate --task recover-when-local-main-carries-hand-commits-of-co --json`
  → **1 valid ticket, no issues**; `git diff --check` passed. Frontmatter is
  unchanged and the single blackboard fence is preserved.
- Implementation and owning-topic changes remain for the implementation
  step. The historical evaluator review below is retained as evidence; its
  findings have the design dispositions above. The owner gate remains open.

## Evaluator review

Reviewed cold on 2026-10-01 against the current source, fixtures, owning topics,
and frozen workflow. **Not ready for implementation: resolve the two findings
below at owner review.** The shared guard fits the microkernel rule (two real
consumers), and the evaluate-design → owner review workflow fits this work.
No implementation, ticket-body change, branch, or PR was produced.

### Must resolve before implementation

1. **P1 — The entry sweep does not publish the clean hand-committed ticket;
   the primary regression and the retry remedy cannot succeed as specified.**
   In `src/coga/git.py`, `sync_coga_state()` first calls `_dirty_paths()` and
   passes only those individual paths to `publish()`. `_candidates()` can add
   committed paths only within the supplied pathspecs. With a clean committed
   ticket and a dirty log, its pathspec is therefore only `coga/log.md`; the
   ticket never reaches the committed-path discovery described in the spec.
   A temporary real-Git fixture using `init_git_repo`, `_seed_ticket`, a
   tracked seed log, and `push_competing_commit` reproduced the exact shape:
   the sweep published the appended log line but left the hand-committed
   ticket bytes absent from origin. Applying the specified `_published_proof`
   to the committed ticket returns `content differs from control`, so the new
   guard must also refuse. `git pull --rebase --autostash origin main` then
   exited 0, but another sweep left a clean checkout one commit ahead, with
   the ticket still unpublished. Thus “then retry” also loops without an
   additional change. Decide explicitly whether to extend sweep candidate
   discovery through the existing provenance guard (and specify/test that
   contract change), or narrow this ticket to content independently published
   beforehand and provide a complete recovery procedure for unpublished
   content. A helper-only implementation cannot meet the current acceptance
   criteria. The retry test should assert successful subsequent recovery,
   not just a zero rebase exit code.

2. **P1 — The `fast_forward_control()` realignment path needs an explicit
   in-progress-operation refusal before staging or moving anything.**
   `_plan_preparation()` checks `_IN_PROGRESS_MARKERS`, but `refresh()` and
   `_publish_locked()` reach `fast_forward_control()` without that check.
   Its existing `merge --ff-only` invocation supplies Git's unfinished-merge
   protection; the proposed plumbing bypasses it. In a temporary fixture
   with a state-only local commit whose ticket bytes were separately on
   origin, starting a clean `merge --no-commit --no-ff feature` left
   `MERGE_HEAD` and staged `code.txt`. The existing merge invocation refused
   with exit 128 (“You have not concluded your merge”), while the proposed
   `read-tree -m -u HEAD <target>` followed by guarded `update-ref` succeeded,
   moved `main`, and left `MERGE_HEAD` and the staged code in place. The
   committed-content guard cannot detect this operation state. Specify the
   refusal for realignment through this caller and test that HEAD, index,
   working files, and operation markers remain unchanged. Reuse the existing
   operation-marker policy rather than relying on dirty-file conflicts.

### Optional recommendations and owner decisions

- Settle the helper's result contract: acceptance requires `str | None`,
  while Proposed Shape permits a tuple/dataclass. Also name the outcome for
  zero/multiple merge bases and inspection failures; neither establishes
  “non-state commit” nor “state not yet on control.” Preserve fail-closed
  behavior and distinguish inspection failure from an actionable content
  refusal.
- Add direct guard coverage for code changed then reverted, merge commits,
  zero/multiple merge bases, deletions, executable modes, symlinks/submodules,
  and committed union-log content. The listed end-to-end cases do not exercise
  these central proof conditions. Cover the feature-HEAD/no-holder path too.
- Update stale fast-forward-only statements throughout the named topics,
  including `dev/checkouts` launch-boundary step 4, the `git-refresh` opening
  paragraph and `refresh` outcomes, and `coga/sync`'s control-checkout bullet;
  updating only the specifically listed sentences leaves contradictions.
  Mirror all owning-topic changes to their packaged twins. The three existing
  Open Questions remain owner decisions, not evaluator approvals.

### Verification evidence

- Read `src/coga/git.py` publication, integration, and preparation paths;
  `commands/launch.py::_CheckoutBoundary.enter/settle`;
  `recurring_runner.py::_sync_control_checkout_ahead`; the relevant Git tests
  and fixture helpers; and the packaged `code/design-then-implement` workflow.
- Ran the two isolated real-Git reproductions described above under
  `PYTHONPATH=/home/n/Code/coga/src:/home/n/Code/coga/tests .venv/bin/python`
  using temporary repositories; no live Git refs or implementation files
  were changed by those probes.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_git.py -q -k 'fast_forward_leaves_an_ahead_main_alone_and_names_the_fix or refresh_refuses_an_ahead_or_diverged_control_checkout or prepare_refuses_an_ahead_or_diverged_control_and_changes_nothing'`
  → **4 passed, 88 deselected**. These confirm the current refusal baseline;
  no proposed implementation exists to run the full acceptance suite against.

## Dev

pr: https://github.com/FastJVM/coga/pull/948
branch: recover-state-only-divergence

## Implementation handoff (implement step, 2026-10-02)

Commit `5938263cc` on `recover-state-only-divergence` (rebased on
`origin/main` 0b007ef08, pushed). No PR yet.

**What changed**
- `src/coga/git.py`:
  - `sync_coga_state` passes the full tasks/log/recurring paths to `publish`
    (no dirty narrowing, no existence filter).
  - New `_Subsumption` (frozen; kind `ok|foreign|unpublished|unproven`,
    reason, blocking, dropped, evidence) and `_local_control_subsumed`.
  - New `_operation_in_progress` shared by `_plan_preparation` and the
    realignment path.
  - `_divergence_message` (remedies) and `_report_realignment` (one stderr
    line plus reflog note).
  - `fast_forward_control` → `_realign_control` for not-ancestor. Order:
    operation check, guard, holder, `_stage_landed`, `read-tree -m -u`,
    guarded `update-ref`.
  - `_PreparationPlan.realign`, with guard evidence in the plan evidence.
    `_apply_preparation` realigns: on control `read-tree` then
    `update-ref`; elsewhere `update-ref` then `switch`. It skips
    `merge --ff-only` after a realignment.
  - Docstrings updated, including the module docstring.
- `recurring_runner._sync_control_checkout_ahead`: the reason now says
  "could not be brought level … Resolve it in <root> as the [git] note
  above says". No generic pull command.
- Docs updated and twins synced byte-identical: `state-publication`,
  `git-refresh`, `dev/checkouts`, `coga/sync`, `recurring-control`, plus
  `recurring-temp-worktrees`, which repeated the old "only fast-forwards"
  docstring.

**Deviation from the spec (for review):** `_candidates()` is not fully
unchanged. Widening the sweep exposed a real hazard. On a feature branch,
control can hold a ticket this worktree published (`PUBLISHED_REF`)
while HEAD lacks it. `_candidates` then selected the path and would have
**published its deletion**. `test_launch_prepares_a_feature_checkout_and_resolves_a_ticket_created_on_control`
caught this. Fix: a clean committed path is skipped when HEAD's blob
equals the merge-base blob, meaning HEAD did not change it and control
moved. Regression: `test_sweep_does_not_republish_a_ticket_this_feature_checkout_lacks`
fails without the fix.

**Other decisions**
- For `foreign`, preparation keeps `blocking == (control,)` and names the
  offending commits and paths in `reason`, so the existing test keeps its
  blocking assertion. For `unpublished` and `unproven`, the failing paths
  are appended to `blocking`.
- The guard uses `diff-tree -m --root` per commit. A local merge of
  origin into main (plain `git pull`) is therefore `foreign`. This fails
  closed, per spec.
- `update-ref -m "coga: realign to <remote>/<control>"` makes the reflog
  entry identifiable.

**Verification**
- `python -m pytest`: 3253 passed, 6 failed. The 6 failures are
  `tests/test_edge_distribution.py` (installed-wheel shim tests). They
  fail identically on a clean `origin/main` worktree, so they are
  **pre-existing and unrelated** (`coga.commands.init` lacks
  `_check_external_dependencies` in the installed copy).
- After the rebase, `tests/test_git.py tests/test_recurring.py tests/test_launch.py tests/test_packaging.py`
  gave 792 passed.
- `coga validate --json` (example fixture, `SLACK_WEBHOOK_URL` unset):
  4 ok, no issues.
- New tests in `tests/test_git.py`:
  - 5 sweep tests.
  - The 2026-10-01 entry-order recovery test.
  - The rebase-then-retry recovery test (runs the suggested command
    verbatim).
  - Feature-branch remedy wording.
  - State-plus-code refusal.
  - Preparation realignment from a feature branch and on control, and
    proof drift refusing.
  - Realignment through refresh and fast-forward, including another
    holder left alone.
  - An unfinished merge left unchanged through `refresh` and direct
    `staged=`.
  - Every `_IN_PROGRESS_MARKERS` entry (parametrized).
  - Inspection failure.
  - Direct guard tests: revert, evil merge, zero and criss-cross bases,
    deletion, exec mode, symlink and submodule, union log.

  `tests/test_recurring.py` has a new catch-up realignment test.
