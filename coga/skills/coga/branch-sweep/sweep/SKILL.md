---
name: coga/branch-sweep/sweep
description: Delete local and remote git branches whose work has already landed.
---

# Branch Sweep

This skill documents the branch sweep behind the
`recurring/branch-sweep/` ticket, whose `ticket.py` runs the registered
`branch-sweep` recipe (`coga.branchsweep.run_branch_sweep_recipe`) through
`coga.runner.run_recipe` — no agent, no composed prompt. It is the safety
net behind `coga retire`'s
branch deletion — retire's
cleanup is best-effort (failures are swallowed), and branches also leak when
a ticket is deleted without going through retire or a session dies mid-flight.

1. prune registrations for worktrees whose directories are gone (`git
   worktree prune`), then enumerate the branches held by the remaining live
   worktrees,
2. enumerate every local branch and every branch on `[git].remote`,
3. skip `[git].control_branch`, the checked-out branch, and any branch a
   non-terminal ticket names anywhere in its task files
   (`_live_ticket_branches`): the whole ticket above and below the fence plus
   every attachment of a directory-form task, matched as a whole branch name.
   A `## Dev` `branch:` line is one such mention, not the contract — a draft
   that named its branch only in prose and a handoff manifest was invisible to
   the old `## Dev`-only guard. A mention pins; a ticket whose frontmatter
   cannot be read is treated as live. Recurring period tasks
   (`tasks/recurring/**`) are the exception and pin only a `## Dev`
   `branch:` line: their blackboards are generated reports that name
   branches — this sweep's own record when a failed run leaves its period
   `in_progress`, autoclose's retire follow-ups — and scanning them would let
   one failed sweep pin every branch it skipped,
4. for the rest, authorize deletion two independent ways: the local tip being
   reachable from `[git].control_branch`
   (`branchcleanup.local_branch_landed`) — a real merge-commit or
   fast-forward landing, which needs no PR at all — or a merged PR for that
   **head branch name** (`gh pr list --head <branch>` with `number,headRefOid`)
   and no PR currently open for it, judged by `merged_pr_verdict`: the merged
   PR vouches for the ref only when every commit in `git rev-list <tip>
   ^<merged head> ^<control> ^<remote>/<control>` (each control ref only when
   it exists locally) touches only generated Coga state (`tasks/**`,
   `log.md` — `github_preflight.is_coga_state_path`, the same carve-out
   `validate --check-github` makes). `git diff-tree --cc` lists a merge
   commit's paths only where the result differs from every parent, so Coga's
   clean `Merge <control> state into <branch>` commits pass and an evil merge
   does not. One rule therefore covers the exact merged tip, a local ref that
   *lags* the merged head (its last commit was pushed from another checkout),
   and a ref that walked *past* the merged head through state-sync commits;
   a ref with real unmerged source commits is skipped with the offending
   paths in the run record. When the merged head is not a local object it is
   fetched from `refs/pull/<number>/head` without writing a ref. The remote
   ref takes only a merged PR at its exact tip: its objects are usually not
   local, and ancestry never authorizes deleting `<remote>/<branch>`.

   **A rebased copy is refused by design, every week, until a human deletes
   it.** The verdict above admits ancestors only; it has no `git cherry` /
   patch-id equivalence check (`branchsweep.py`, `branchcleanup.py`). So a
   local ref whose commits were re-applied under new SHAs from *another*
   checkout — a review follow-up pushed from a scratch clone that rebased
   onto fresh control first, or a `resolve-conflicts` rebase — and then
   merged from that copy is reported as `has merged PR #N at <oid>, but the
   ref carries commits touching <source paths>` and left in place, local and
   remote: the merged PR vouches for the head *name*, but the recorded
   worktree's pre-rebase commits are patch-equivalent rather than ancestors
   and touch real source paths. The 2026-09-21 sweep carried six such refs
   (`branch-sweep-landed` #811, `dream-w38-extract-backlog` #812,
   `sweep-abandoned-record` #813, `recurring-missing-workflow` #814,
   `title-only-validator` #815, `v2-premise-holes` #819); the W39 Dream scan
   verified #812's shape — local tip `1d23cb4c` is a rebase of the same two
   commits the merged head `35b9b609` carries as `8714fda3` + `a2659a86`, and
   `git merge-base --is-ancestor 1d23cb4c 35b9b609` is false. Clear one by
   hand after proving equivalence — `git cherry <merged-head> <tip>` printing
   only `-` lines — with `git branch -D <branch>` and `git push <remote>
   --delete <branch>`; or extend `merged_pr_verdict` with a patch-id check.
   Neither is owned by a ticket yet (`clean-up-all-the-working-trees`
   excludes branch deletion),
5. for a branch whose **local tip** landed either way but is still held by
   a live worktree, require no open PR before removing the checkout. A merged
   remote tip alone never authorizes removing newer unmerged local work:
   with `[git].worktrees_ticket_owned` unset or `false` (the default),
   preserve both refs and report the distinct, non-fatal
   `skipped-worktree-pinned` outcome. With it `true`, the repo has declared
   that every linked worktree of its git repository belongs to a Coga ticket
   (the assumption is stated in the `dev/checkout-cleanup` context, *Unrecorded
   worktrees*),
   so a landed one nobody claims is finished work: GC the worktree first, then
   fall through to step 6 for its refs. The worktree proofs are retire's,
   shared through `branchcleanup.inspect_worktree_for_removal` and
   `checkout_disposal.live_checkout_claim`: no non-terminal ticket in any
   Coga workspace of the repository records that worktree path (the
   branch-name guard in step 3 already covered the branch); the path is a
   linked worktree of the checkout the sweep runs from — an independent clone
   or another repository's worktree is preserved, so each clone GCs only its
   own worktrees; it is not the checkout running the sweep; it holds that
   branch; and it carries no tracked or untracked local state (ignored
   regenerable caches — `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`,
   `.mypy_cache/` — go with it; any other ignored file preserves it). Then
   `git worktree remove`, unforced, reported under `removed worktree`. A
   worktree that fails any proof keeps both refs `skipped-worktree-pinned`,
   with the reason in the run record,
6. delete the remote ref (`git push <configured-remote> --delete`) when a
   merged PR covers its tip, and the local branch following the same policy
   retire uses: plain `git branch -d` on the ancestry path, or a logged `-D`
   — after re-reading the ref and preserving the branch if it moved off the
   authorized tip — for the squash-merge case, where the merged PR is the only
   thing vouching for the work,
7. write a `## Branch Sweep` report (`render_sweep_report`) — the outcome
   counts and lists, then every per-branch decision — to the period task's
   blackboard named by `COGA_TASK_BLACKBOARD`, or to stdout when the recipe
   runs outside a task. It is written before the exit code is decided, so a
   sweep that stopped early records why.

The scope is defined by `coga.branchsweep.sweep_branches`. If worktree state
cannot be pruned/listed, or the Coga OS root cannot be located in git, the
sweep fails before deleting anything. If `gh` is missing or unauthed, the
sweep fails and performs no further gated deletes — never a delete with
incomplete safety information.

The sweep only sees worktrees linked to the clone it runs from. In this repo
the recurring jobs run from `/home/n/Code/claude/coga`; another clone's
review or scratch worktrees (`/home/n/Code/coga`'s `/tmp/coga-pr*-review`
checkouts, say) need their own `coga run branch-sweep` from that clone.

Run it directly with `coga run branch-sweep`.
