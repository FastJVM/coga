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
3. skip `[git].control_branch`, the checked-out branch, the shared skill-update
   branch protected by [dev/checkout-cleanup](context:dev/checkout-cleanup),
   and any branch a
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
   PR vouches for the ref only when every commit in `git rev-list
   --right-only --cherry-pick <merged head>...<tip> ^<control>
   ^<remote>/<control>` (each control ref only when it exists locally)
   touches only generated Coga state (`tasks/**`, `log.md` —
   `github_preflight.is_coga_state_path`, the same carve-out
   `validate --check-github` makes). `--cherry-pick` drops a ref commit whose
   patch-id matches a commit on the merged head. `git diff-tree --cc` lists a
   merge commit's paths only where the result differs from every parent, so
   Coga's clean `Merge <control> state into <branch>` commits pass and an evil
   merge does not. One rule therefore covers the exact merged tip, a local ref
   that *lags* the merged head (its last commit was pushed from another
   checkout), a ref that walked *past* the merged head through state-sync
   commits, and a *rebased copy* — a ref whose commits another checkout
   re-applied under new SHAs (a review follow-up rebased in a scratch clone,
   a `resolve-conflicts` rebase) and merged from that copy. A rebase that
   changed a patch, such as a conflict resolution, keeps that commit in the
   list; a ref with real unmerged source commits is skipped with the
   offending paths in the run record. Clear such a ref by hand only after
   reading the difference (`git cherry -v <merged-head> <tip>` lists the
   unmatched commits with `+`). When the merged head is not a local object it
   is fetched from `refs/pull/<number>/head` without writing a ref. The
   remote ref takes only a merged PR at its exact tip: its objects are usually
   not local, and ancestry never authorizes deleting `<remote>/<branch>`,
5. for a branch whose **local tip** landed either way but is still held by
   a live worktree, require no open PR before removing the checkout. A merged
   remote tip alone never authorizes removing newer unmerged local work:
   with `[git].worktrees_ticket_owned` unset or `false` (the default),
   preserve both refs and report the distinct, non-fatal
   `skipped-worktree-pinned` outcome. With it `true`, the repo has declared
   that every linked worktree of its git repository belongs to a Coga ticket
   (the assumption is stated in the `dev/checkout-cleanup` context, *Unrecorded
   worktrees*),
   so a landed one nobody claims is finished work: qualify the worktree for
   removal after archival in step 6. The worktree proofs are retire's,
   shared through `branchcleanup.inspect_worktree_for_removal` and
   `checkout_disposal.live_checkout_claim`: no non-terminal ticket in any
   Coga workspace of the repository records that worktree path (the
   branch-name guard in step 3 already covered the branch); the path is a
   linked worktree of the checkout the sweep runs from — an independent clone
   or another repository's worktree is preserved, so each clone GCs only its
   own worktrees; it is not the checkout running the sweep; it holds that
   branch; and it carries no tracked or untracked local state (ignored
   regenerable caches — `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`,
   `.mypy_cache/` — go with it; any other ignored file preserves it). A
   worktree that fails any proof keeps both refs `skipped-worktree-pinned`,
   with the reason in the run record,
6. publish the retirement tag under
   [dev/checkout-cleanup](context:dev/checkout-cleanup) before any worktree
   removal or ref deletion. An archive failure preserves the refs and
   worktree, records the reason, and makes the recipe fail after checking the
   other branches. Remove an eligible worktree with unforced `git worktree
   remove`, reported under `removed worktree`. Delete the local branch using
   retire's landing policy (`-d` for ancestry, a logged `-D` for a merged PR),
   re-reading the authorized tip first on both paths. Then delete the remote
   ref with a lease on its authorized tip when a merged PR covers it,
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
