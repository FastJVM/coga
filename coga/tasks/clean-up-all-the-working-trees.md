---
title: clean up all the working trees
status: draft
owner: nicktoper
workflow: maintenance/with-approval
---

## Description

Reclaim disk space by cleaning up unused Git worktrees under `/tmp` and
`~/Code` (`/home/n/Code`) across every repository in those locations. This is
a one-time maintenance task: inventory the worktrees, present an exact removal
list for the owner's approval, then remove approved eligible worktrees and
verify the result. Preserve worktrees with uncommitted files or unmerged work
and report them for review; do not back them up as a substitute for retaining
them. Done means the approved cleanup is verified and the blackboard records
what was removed, approximate space recovered, and what remains with reasons.


## Context

### Scope and boundaries

- The owner is `nicktoper`. Scope covers all repositories under both roots,
  including separate clones of the same project and their linked worktrees.
  Group worktrees by their actual Git common directory; one clone's
  `git worktree list --porcelain` does not enumerate another clone's worktrees.
- Remove eligible linked-worktree directories, not primary repositories or
  standalone clones. Identify standalone scratch clones and test fixtures in
  the inventory, but leave their deletion for a separate owner decision.
  Branch deletion, remote changes, general `/tmp` cleanup, and changes to
  Coga's cleanup automation are outside this ticket.
- Preserve primary/control checkouts, the checkout running this task, locked
  or in-use worktrees, and any worktree required by an unfinished task. Use
  available process/session and task evidence; directory age or an old branch
  name is not sufficient evidence that a worktree is unused. Uncertain cases
  stay in place for review.
- Resolve paths and inspect nested repositories before proposing removal.
  Preserve both roots themselves, paths outside them, and shared repository
  object stores and branch refs. Normal removal and approved pruning may
  remove the corresponding per-worktree administrative registrations. Do not
  follow a symlink into a different cleanup scope.

### Inventory and approval

1. Discover repositories and enumerate their registered worktrees using Git.
   Report inaccessible locations and discovery limits rather than claiming
   complete coverage. Distinguish existing directories, missing registered
   paths, standalone clones, and Git test fixtures.
2. For each candidate, record its absolute path, repository/common directory,
   branch or detached HEAD and commit, approximate allocated disk usage,
   tracked/untracked/ignored state, merge evidence, activity or task evidence,
   and a proposed action with its reason. Check for unfinished Git operations
   and commits that would lose their last durable reference on removal.
3. Preserve tracked modifications, untracked files, unmerged or unique work,
   and ignored local data such as credentials or machine configuration.
   Ignored caches may leave with an otherwise eligible worktree only when
   confirmed regenerable and described in the removal list. Unknown ignored
   data stays. Keep secret contents out of the inventory and blackboard.
4. A merged branch or PR alone does not prove the current worktree disposable:
   inspect commits added after the merge and account for squash/rebase merges.
   Use fresh evidence where available; missing or uncertain evidence means
   preserve and report. Keep local and remote branch refs unchanged.
5. Write the inventory and exact proposed paths/actions on this ticket's
   blackboard. The owner approves that concrete list at the `approve` step;
   approving this draft or launching it does not approve any deletions.
   Keep the approval table concise, with exact paths and evidence for every
   proposed action. Summarize repetitive retained test fixtures where that
   does not hide a candidate's eligibility or a discovery limitation.

### Cleanup and verification

- Recheck each approved path's identity, HEAD, local files, and activity just
  before removal. Changed or newly uncertain candidates stay and are reported;
  approval does not override the preservation rules above.
- Prefer normal `git worktree remove` for eligible linked worktrees. Do not
  force past a refusal or use recursive deletion as a fallback. Do not run
  Coga retirement or branch-sweep commands, which can also change branches or
  ticket state beyond this cleanup's scope.
- Missing worktree registrations may be pruned only after reviewing Git's
  dry-run output and confirming every affected registration is approved and
  in scope. A repository-wide prune with other affected entries must be
  skipped. Preserve locked registrations and uncertain missing paths.
- Verify removed directories and registrations, preserved primary checkouts,
  and remaining worktrees. Record removals, skips/failures, approximate space
  recovered, and retained candidates with actionable reasons. Do not call a
  failed removal successful; partial cleanup must be explicit.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Ticket authoring notes

- Owner confirmed all repositories under `/tmp` and `~/Code`; preserve
  worktrees with uncommitted or unmerged work and report them for review.
- Owner approved adding `maintenance/with-approval`: inventory, owner approval,
  cleanup and verification. Main agent remains unset so activation uses the
  configured default; no contexts or extra skills are needed.
- Read-only discovery found separate Coga clones, linked worktrees, and many
  Git test fixtures. The scope and inventory instructions distinguish these.
  No cleanup has run. Final draft confirmation remains.
- Independent review found no must-fix issues. Its two optional clarifications
  are now in Context: distinguish per-worktree registrations from shared Git
  storage, and keep repetitive fixture findings from overwhelming approval.
- All three planned prompts compose successfully. Repository validation also
  reports pre-existing authoring-note errors on three other draft tickets;
  this draft's authoring sections will be cleared after final confirmation.

## Evaluator review

**Must-fix:** None found. A future agent can begin discovery without interview history. The ticket defines the two roots, distinguishes separate clones from linked worktrees, protects dirty or uncertain work, and states concrete completion evidence. The scope is coherent for one maintenance task.

The workflow fits: inventory precedes a distinct owner gate, and cleanup follows approval of exact actions. Draft approval cannot authorize deletion. Rechecking eligibility, preserving changed candidates, avoiding forced removal, and requiring owner acceptance of partial completion provide appropriate safeguards.

No context attachments appear necessary. The inline specification contains the task-specific rules, and the workflow supplies the process. There are no broad attached contexts, cited contexts requiring attachment, or stale size-based citation justifications.

**Optional clarifications:**

- “Shared Git metadata may not be deleted” could distinguish the shared repository itself from individual worktree administrative registrations. Normal removal and approved pruning necessarily remove those registrations. The intended distinction is inferable, but stating it would eliminate a literal conflict.
- Discovery may produce many fixtures and retained candidates. Keep the approval table easy to review, with exact paths and evidence for every proposed action; summarize repetitive fixture findings where individual details do not affect eligibility. Missing merge or activity evidence should remain a reason to retain, as already specified.

**Prompt-size review:** The shared base prompt accounts for approximately 44–45% at every step, exceeding the proportional review threshold. Its core-development guidance is a concrete trim candidate for a separate shared-prompt improvement. This is baseline overhead, not excessive ticket attachment. Ticket context is approximately 30%; its detail supports the deletion safeguards. No ticket-controlled layer currently exceeds 40%.
