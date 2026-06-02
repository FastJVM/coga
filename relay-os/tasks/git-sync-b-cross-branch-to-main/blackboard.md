The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: git-sync-b
worktree: (none — single-checkout flow; user removed the sibling worktrees)
pr: https://github.com/FastJVM/relay/pull/263

base: A (PR #262) is now **MERGED** to main. PR #263 targets `main` directly.
commit: fd43544 "Land ticket-state on main from any branch (cross-branch sync)"
  (was 352d2da; rebased — see open-pr note below)

Worktree workflow note: user deleted the external `../relay-git-sync-*` dirs and
asked to work in the primary checkout instead. So the code work was done by
checking out `git-sync-b` *in this repo* (stashing the control-plane task-state
edits, committing code on the branch, then returning to `main` and popping the
stash). No sibling worktree exists — `branch:` is the link.

## open-pr done (claude, 2026-06-01)

A (#262) merged to `main` between implement and open-pr, so the dependency is
resolved and B targets `main` directly (no longer `git-sync-a`).

- `git-sync-b` was branched off A's *pre-squash* commits (`c114fa0`, `f0422dc`),
  which are absent from `origin/main` (A landed as squash commit `522850d`). A
  plain rebase onto `origin/main` hit add/add conflicts replaying A's commits.
- Fixed with `git rebase --onto origin/main f0422dc git-sync-b` — replays only
  B's single commit. Result: `fd43544` sits directly on `origin/main` with a
  clean 5-file diff (git.py, conftest.py, test_git.py, live + packaged sync
  context). Branch was never pushed before, so the history rewrite was safe.
- Re-ran `tests/test_git.py` on the rebased base (relay venv python) → 22 passed.
- Pushed `git-sync-b`; opened **PR #263** against `main`.
- Control-plane task-state edits were stashed during the branch checkout and
  popped on return to `main` (single-checkout dance).

## Implement done (claude, 2026-06-01)

Implemented per the approved spec. Commit `352d2da` on `git-sync-b`.

- `git.py`: `sync_task_state` now commits the task dir on HEAD in both cases
  (extracted `_commit_task_dir`), and on a feature branch / detached HEAD calls
  the new `_land_on_control_branch` — temp-index overlay (`_build_overlay_tree`
  via `GIT_INDEX_FILE`), `commit-tree`, push-as-CAS to `refs/heads/<control>`,
  bounded non-ff retry (`_MAX_SYNC_ATTEMPTS=5`). `_push_ref` returns stderr
  (vs raising) so the loop can tell non-ff from a hard failure;
  `_try_update_local_ref` best-effort ff's local main (skips when HEAD==main).
  `_run_git` gained an `env=` overlay for the temp-index ops. Same-branch path
  unchanged → all A tests still green.
- `conftest.py`: `GitRepo.push_competing_commit` (rival lands straight on
  origin/main from a throwaway clone; pins the clone to origin/main since the
  bare origin's symbolic HEAD isn't `main`).
- `test_git.py`: replaced the old feature-branch no-op test; added
  lands-on-main-and-HEAD, working-tree-untouched (staged+unstaged survive),
  non-ff anti-clobber, deterministic mid-flight race (wraps `_push_ref` to inject
  a competing push between fetch and our push → forces the retry branch),
  no-op-when-identical, detached-HEAD, and cross-branch crash-loud.
- `relay/sync` context: live + packaged copies updated to describe cross-branch
  landing (replacing the same-branch/"deferred" placeholder). The materialized
  `relay-os/bootstrap/...` copy is gitignored (regen'd by `relay init`); I synced
  it locally too but it isn't committed.

### Verification
- `pytest tests/test_git.py` → 22 passed.
- Full suite → 506 passed, 2 failed (both `test_packaging.py`,
  calendar-reminder wheel resources — **pre-existing**, confirmed failing on the
  clean `git-sync-a` base; unrelated to this change).
- `relay validate --json` on `example/` → 0 errors, 0 issues.
- Note: the venv backing `relay` had a stale non-editable install missing A's
  `git` module; reinstalled `pip install -e .` against it.

### For open-pr step
PR must target/merge **after A (#262)**. Base branch is `git-sync-a`, not `main`
— either retarget once A merges, or open against `git-sync-a` and rebase. Call
this out in the PR body.

## Dependency
A (`git-sync-a-helper-and-same-branch`) is **not yet merged** — its code lives
on branch `git-sync-a` / PR #262 (not on `main`). B's implement step must
branch off A (or wait for A to merge). Design here is against A's interface as
shipped on `git-sync-a`.

## Design done (claude, 2026-06-01)

Spec written into `ticket.md`: Acceptance Criteria, Proposed Shape, Out of
Scope. Summary of the decisions and why.

### Mechanism: pure plumbing (not a worktree)
Chosen **option 1 (plumbing)** from the ticket. Build main's new tree in a
**temporary index** (`GIT_INDEX_FILE=<tmp>`): `read-tree origin/main` →
`rm -r --cached --ignore-unmatch -- <task-dir>` → `add -- <task-dir>` →
`write-tree`, then `commit-tree -p origin-tip` and `push <sha>:main`.
- Touches **no working tree and not the real index** — the feature work
  (staged + unstaged) is structurally untouchable because every staging op
  runs against the temp index. This is the cleanest way to satisfy the
  "feature working tree undisturbed" acceptance criterion.
- Rejected the worktree option: adds a hidden on-disk checkout, lifecycle/GC,
  and a second copy — more moving parts, against relay's "no hidden state"
  grain. The ticket itself calls plumbing "the natural fit."
- `add -- <task-dir>` against a temp index seeded from origin/main's tree
  cleanly overlays the working-tree task files onto main's tree while keeping
  main's code blobs (we only touch the task pathspec). Handles create +
  modify uniformly; the `rm --cached` first makes it a true mirror of the
  current task dir.

### Concurrency: push-as-CAS, NO lock (relay has none, by design)
Confirmed by grep: **zero locking primitives in the codebase** (no flock /
lockfile / threading.Lock). `relay/architecture` is explicit: "There is no
filesystem mutex... the cost of a hard mutex is not [worth it]" — status +
git recoverability is the model. So B introduces **no lock**.
- Origin is the source of truth; the `git push <sha>:refs/heads/main` is the
  atomic compare-and-swap. Each relay process fetches → builds on origin's
  tip → pushes; exactly one fast-forwards per round; losers see a non-ff
  reject, refetch, and retry (bounded `_MAX_SYNC_ATTEMPTS = 5`).
- This single mechanism covers BOTH the "concurrent local relay processes"
  case (auto-chain + post-merge hook + manual) AND remote/cross-machine
  divergence — strictly more robust than a local-only lock or a local-ref
  CAS alone.
- Local `refs/heads/main` is best-effort fast-forwarded after a successful
  push (nicety; failure is non-fatal since origin already has the commit).

### Failure model: inherit A's crash-loud
Fetch/push failure on the control-branch path → `GitError` → stderr +
`log.md` + `typer.Exit(1)`, exactly like A's same-branch push failure and
`slack.post`. `[git].enabled=false` and "not a git repo" stay soft no-ops.
The owner already settled crash-loud for A; B matches rather than relitigates.

### Reuse, don't fork (per ticket)
- Reuse A's `_toplevel`, `_relative_to_root`, `GitError`, the GitError
  boundary in `sync_task_state`, and the `git_repo` fixture.
- Extract A's same-branch commit body into `_commit_task_dir(root, rel, msg)`
  and call it on HEAD in BOTH branches (so files land on the current branch
  too) — minimal, additive refactor.
- Same-branch path otherwise unchanged → A's tests must still pass.

## Open Questions — RESOLVED (owner nick, review-design, 2026-06-01)

1. **Commit on HEAD** — YES. Spec stands as written (`git commit --only`,
   code untouched). Accepted that control-plane commits land on the feature
   branch; benign dedup on merge.
2. **Detached HEAD** — SKIP the HEAD commit (warn), still land on main via the
   cross-branch path. Folded into Proposed Shape step 1.
3. **Same-branch non-ff** — stays crash-loud as A shipped; retry loop is
   cross-branch-only. Unifying deferred to a later ticket (already Out of Scope).

Design approved. Bumping to `implement`.

## Open Questions (original — for owner @ review-design)

1. **Commit task files on the feature branch HEAD, or leave uncommitted?**
   Spec currently **commits on HEAD** (scoped via `--only`, code untouched).
   - Pro: clean working tree; a later `git add -A` for code won't sweep task
     files into the code PR; the branch's checkout reflects ticket state.
   - Con: the `dev/code` "checkout boundary" context prefers task-state
     commits kept *off* the feature branch (separate from the code PR). The
     merge-dedup when the branch later merges to main is benign (identical
     content, no conflict), but it does put control-plane commits on the
     feature branch.
   - Alternative: leave the task files uncommitted in the working tree and
     only land them on main. Riskier re: accidental sweep, but truer to the
     checkout-boundary model.
   **Recommend commit-on-HEAD; want your call since it touches the
   checkout-boundary philosophy.**

2. **Detached HEAD** (`branch == "HEAD"`): currently treated as a feature
   branch → would attempt a commit on detached HEAD (orphan-ish) before
   landing on main. Proposed: **skip the HEAD commit when detached** (warn),
   still land on main. OK, or crash instead?

3. **Same-branch non-ff left crash-loud (Out of Scope).** Confirming you're
   fine that the retry loop is cross-branch-only and the same-branch push
   stays crash-loud as A shipped it (unifying is a later ticket).
