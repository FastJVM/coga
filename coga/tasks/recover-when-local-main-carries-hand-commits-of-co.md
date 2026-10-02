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
step: 2 (evaluate-design)
agent: claude
---

## Description

When local `main` carries commits that touch only Coga state (`coga/tasks/**`, `coga/log.md`, `coga/recurring/**`) and are not on origin, Coga can no longer bring the control checkout level. `fast_forward_control` (`src/coga/git.py`) prints a `git pull --rebase` note, and `coga launch` refuses ("bringing this checkout to a clean 'main' at origin/main refused to change the checkout"). The operator's `git pull --rebase` then also fails, because the unpublished log lines Coga appended in the meantime leave `coga/log.md` dirty. Recovery is manual, and the documented command does not work.

In the incident shape the *content* is usually already on origin by the time the refusal fires. The launch entry sweep (`sync_coga_state`) publishes a hand-committed ticket, because `_candidates()` picks up a committed path whose control copy has not moved since this checkout last saw it. It also union-merges the dirty log onto control. Only the *history* still diverges, and `_plan_preparation()` refuses on the ancestry check before it looks at content. This ticket adds one deterministic guard. When every local-only commit is Coga state whose content is already on control, the CLI realigns local `main` to control. Otherwise it refuses with a command that works. Agents are never asked to judge or repair this.

This ticket and the draft `fix-coga-git-sync-failures-that-leave-main-diverge` share the guard: its item 3 ("fast-forward when local content already matches origin") is delivered here by the same helper. That ticket keeps its root-cause work (sandboxed `hash-object` / `fetch` failures) and should cite this guard rather than add a second one.

This changes the `coga/sync` contract on purpose. Today "the local control branch only fast-forwards". After this ticket it either fast-forwards or *realigns*: the local ref moves to the control commit, which drops local commits whose every change is proven to be on control already. It still never commits on a local branch, stashes, rebases, resets hard, or pushes a hand commit.

### Acceptance criteria

- [ ] A new helper in `src/coga/git.py` (working name `_local_control_subsumed(cfg, root, local, target) -> str | None`) returns `None` only when all of the following hold, and otherwise returns a reason naming the offending commit or path:
  - `git merge-base --all local target` yields exactly one base.
  - Every commit in `target..local`, checked **per commit** (`git log --no-renames --format= --name-only -m target..local` or equivalent), touches only paths under `_state_areas()`. A commit that touched code and a later commit that reverted it still fails.
  - Every path in `git diff --no-renames --name-only <base> <local>` passes `_published_proof()` with the local tip's entry as "working" (mode, bytes, or absent), `_tree_entry(target, rel)` as "published", and the merge-base entry as `head_entry`, plus `union=` from `union_merge_paths()`. Same existence, mode and bytes; for a `merge=union` path such as `coga/log.md`, union-merging the local copy onto control changes nothing. A symlink or submodule entry fails.
- [ ] `prepare_control_checkout()` (`_plan_preparation()` / `_apply_preparation()`) no longer refuses a diverged or ahead local control when the helper returns `None` for `(local, pinned)`. The helper's evidence is part of the re-observed plan evidence. Apply then realigns control to `pinned` and verifies a clean `main` at `pinned` exactly as today. Every existing check stays: detached HEAD, in-progress op, other worktree holding `main`, the per-path dirt proof, and ignored collisions.
- [ ] Realignment uses only `git read-tree -m -u HEAD <pinned>` (when HEAD is control; it refuses on conflicting dirty files) and `git update-ref refs/heads/<control> <pinned> <local>` (old-value guarded). With HEAD on a feature branch, the ref moves first and then the existing `git switch` runs. No `stash`, `rebase`, `reset --hard`, commit, or push.
- [ ] Each realignment writes one stderr line naming the dropped commits (short SHA and subject) and saying they remain in the reflog. Nothing is written to `coga/log.md` from inside preparation, because that would dirty the just-verified tree.
- [ ] `fast_forward_control()` uses the same helper. When `local` is not an ancestor of `new` and the helper returns `None`, it realigns: through `update-ref` with an old-value guard when no worktree holds control, or `read-tree -m -u` plus `update-ref` when this checkout (`root`) holds it, after the existing `staged` step. Another worktree holding a diverged control is left alone with a note, as today. As a result `refresh()` returns `True` in this case, and the recurring pre-scan catch-up (`recurring_runner`, the `git.refresh` call in its control catch-up) no longer stalls on it.
- [ ] When the helper refuses only because state content is not yet on control (all local commits are state-only), the refusal in `_plan_preparation()`, the `fast_forward_control()` note, and the `recurring_runner` catch-up reason suggest `git pull --rebase --autostash <remote> <control>` and then retrying the command. The message lists the failing paths and their reasons. Any local commit touching non-state paths keeps today's refusal and wording, except that `--autostash` is added to the suggested pull so the command works with a dirty log.
- [ ] Regression test `tests/test_git.py`, 2026-10-01 shape: seed a ticket; on local `main`, commit a state-only change to the ticket (a hand commit); append unpublished lines to `coga/log.md` (dirty); push a competing commit to origin touching another state path. Run `sync_coga_state()` then `prepare_control_checkout()` (the launch entry order). Assert `prepared`, `main == origin/main`, a clean tree, the hand-committed ticket bytes on origin, and every locally appended log line present on origin's `coga/log.md`.
- [ ] Test: the same shape, but control's copy of the hand-committed ticket also changed after the merge-base, so the sweep cannot carry it. Assert `refused`, nothing moved, and that running the suggested `git pull --rebase --autostash origin main` as given in the message exits 0 in the fixture. A ticket conflict there is legitimate; the fixture changes a different line of the ticket than the hand commit, so the rebase applies.
- [ ] Test: a local commit touching `local.txt` (or touching state *and* code) is still refused. The existing `test_prepare_refuses_an_ahead_or_diverged_control_and_changes_nothing` and `test_refresh_refuses_an_ahead_or_diverged_control_checkout` keep passing, with their asserted string updated to include `--autostash`.
- [ ] Test: `fast_forward_control()` / `refresh()` realign a subsumed diverged control checkout, and leave alone a control holder in another worktree.
- [ ] Docs, canonical and packaged twins kept byte-identical (`tests/test_packaging.py`):
  - `coga/internals/state-publication`: rewrite invariant 1 ("the local control branch only fast-forwards") and invariant 4 to state the realign rule.
  - `coga/internals/git-refresh`: the `fast_forward_control` and `prepare_control_checkout` bullets.
  - `dev/checkouts`: launch boundary step 2 and its remedy text.
  - `coga/sync`: one sentence in the Git bullet.
  - `coga/internals/recurring-control`: the "ahead or diverged … naming `git pull --rebase`" sentence.
- [ ] `python -m pytest` passes.

### Proposed shape

1. **Guard** (`src/coga/git.py`, beside `_published_proof()` in the checkout-preparation section). Add `_local_control_subsumed()` as above. It returns a `str` reason, or `None` when proven. It also needs to say *which kind* of failure it found, either "non-state commit" or "state not yet on control", so callers can pick the wording. A small return such as `tuple[Literal["ok", "foreign", "unpublished"], str]` works, or a frozen dataclass. Reuse `_state_areas()`, `_in_state_area()`, `_tree_entry()`, `_published_proof()`, and `union_merge_paths()`. Use `GIT_LITERAL_PATHSPECS` as `_tree_entry()` does. For the local tip's bytes use `_tree_entry(local, rel)` plus `_blob_bytes()`.
2. **Preparation.** In `_plan_preparation()`, replace the bare `_is_ancestor` refusal. If not an ancestor, call the guard. On `foreign` or `unpublished`, refuse with the corresponding message, and `blocking=(control,)` plus the failing paths. On `ok`, record `realign=True` on `_PreparationPlan` and add the dropped commit list to `evidence`. In `_apply_preparation()`:
   - HEAD on control: after the restores and removals, `read-tree -m -u HEAD pinned`, then `update-ref` with an old-value guard.
   - HEAD elsewhere: `update-ref` (old-value guard), then the existing `switch`.
   
   Skip the `merge --ff-only` when realigned. Keep the existing verification. Each mutation gets its own `stage` label for the `failed` report.
3. **`fast_forward_control()`.** In the not-ancestor branch, call the guard with `(local, new)`. On `ok`, follow the existing holder logic, but realign instead of `merge --ff-only` / plain `update-ref`, and return `True`. On failure, write the note with the `--autostash` command and return `False`. Update the docstring.
4. **Messages.** Change all three suggestion sites to `git pull --rebase --autostash <remote> <control>`: the `fast_forward_control()` note, the `_plan_preparation()` refusal, and the `recurring_runner` control catch-up reason. For the `unpublished` case, say "then retry" rather than "and push", because the retried command's sweep publishes the rebased state through the guarded path instead of pushing a hand commit straight to control.
5. **Tests** in `tests/test_git.py`, beside the existing `test_prepare_*` and `test_refresh_*` tests, using the `git_repo` fixture helpers (`_seed_ticket`, `push_competing_commit`, `_dirty`, `_head`, `_assert_prepared`). Add one `tests/test_launch.py`-level check only if the boundary wording in `_checkout_refusal_message()` changes. It should not need to.
6. **Docs** as listed in the acceptance criteria, edited in `docs/contexts/` and mirrored to `src/coga/resources/templates/coga/bootstrap/contexts/`.

### Out of scope

- Root causes of failed syncs (sandboxed `hash-object` / `fetch` / `index.lock`): the sibling ticket `fix-coga-git-sync-failures-that-leave-main-diverge`.
- Publishing committed-only state that `_candidates()` does not pick up (control's copy moved meanwhile). That stays a refusal with the working command.
- Realigning a diverged control checked out in *another* worktree.
- Any prompt rule telling agents not to commit Coga state (canceled by owner decision), and any detection of *who* made the commit.
- A backup ref or log entry preserving dropped commits beyond the stderr line and the reflog (see Open Questions).
- Changing `_checkout_refusal_message()` or the boundary flow in `src/coga/commands/launch.py`. `_CheckoutBoundary.enter` / `settle` already call `sync_coga_state()` then `prepare_control_checkout()`, which is the order the guard relies on.

## Context

- **Launch boundary order.** `src/coga/commands/launch.py`, `_CheckoutBoundary.enter()` and `.settle()`, each call `git.sync_coga_state()` and then `git.prepare_control_checkout()`. The sweep's publish lands state on origin before preparation pins and proves. That is why, in the incident, content is on origin and only history diverges. Exempt launches and recurring use `git.refresh()` → `fast_forward_control()` instead (`_refresh_launch_checkout()`, and the control catch-up in `recurring_runner` that calls `git.refresh`).
- **Why the hand-committed ticket gets published.** `_candidates()` adds a clean path when `git diff base HEAD` lists it and control's blob is in `_provenance()` (HEAD, `refs/worktree/coga/published`, merge-base) minus HEAD's blob. In other words, control has not moved it past what this checkout saw. `_guard()` then accepts it. If control *did* move it, it is not a candidate, and the guard's `unpublished` refusal applies.
- **Proof reuse.** `_published_proof(root, rel, working, published, *, head_entry, union)` already implements "already on control", including the union rule (`_merge_union_bytes(current=control, base=head_entry, other=working) == control`). Passing the merge-base entry as `head_entry` gives the right three-way base for committed log lines.
- **After a publish.** In `_publish_locked()`, `fast_forward_control()` is called with `staged=` (path → bytes read, bytes landed). When control is diverged it currently returns before the staging step. A realigning path must keep that staging step so the published log comes clean before `read-tree -m -u`.
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

## Open Questions

1. **Preserving dropped commits.** Is a stderr line plus the reflog enough, or should a realign also keep a ref such as `refs/coga/realigned/<sha>`, or append a `coga/log.md` line at the next publish? The spec currently says stderr plus reflog only, to avoid hidden state.
2. **The `unpublished` remedy.** Should the remedy be `git pull --rebase --autostash` then retry the launch (the spec's choice: the retried sweep publishes through the guard), or also include `git push` as in the incident? A plain push lands a hand commit on control without the provenance guard.
3. **Recurring.** `refresh()` now realigns silently (apart from stderr) during the recurring pre-scan catch-up. Is that acceptable for unattended recurring runs, or should recurring keep refusing and leave realignment to `coga launch` only?

