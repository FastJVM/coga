---
slug: auto-persist-dirty-launch-worktrees-to-pushed-bran
title: Auto-persist dirty launch worktrees to pushed branches
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/codebase
  - coga/architecture
  - coga/sync
  - dev/code
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

`[launch].worktree` runs each agent in a detached per-launch git worktree.
That isolates the primary checkout from agent sessions, but it creates a
data-loss hazard: launch cleanup currently protects Coga state
(`coga/tasks`, `coga/log.md`, spools) and ignores non-Coga source/docs changes.
If an agent accidentally edits product files in the launch checkout instead of
the recorded feature worktree, the normal branch/PR path can be broken and the
worktree may be removed or left untracked without a durable branch reference.

Make dirty non-Coga launch worktree cleanup durable by default. Before Coga
removes a launch worktree, any non-ignored non-Coga changes must be committed
to a named branch, pushed to the configured remote, and recorded on the ticket.

## Acceptance Criteria

- Clean launch worktrees still clean up normally.
- A launch worktree with dirty non-Coga tracked changes is not deleted until
  those changes are committed to a non-control branch, pushed, and recorded on
  the ticket.
- A launch worktree with dirty non-Coga untracked, non-ignored files gets the
  same treatment.
- Ignored files are not swept into the auto-persist commit.
- If `## Dev` already has `branch:`, cleanup uses that branch when it is safe;
  otherwise it creates a unique namespaced branch, for example
  `coga/<slug>-<session-short>`.
- Cleanup must never push to the configured control branch (`main` by
  default) or mutate it directly.
- The ticket blackboard records at least `branch:`, `worktree:`, `commit:`,
  and `base:` under `## Dev` before the worktree is removed.
- If commit or push fails, Coga leaves the launch worktree in place and prints
  clear recovery instructions with the path and branch/commit state.
- Coga task-state sync remains separate from product-code commits.
- Tests cover tracked changes, untracked files, ignored files, existing
  `## Dev branch:`, generated branch-name collision, push failure, and refusal
  to push the control branch.

## Proposed Shape

- Add a cleanup-time detector for dirty non-Coga worktree paths. Reuse
  structured git path queries rather than ad hoc parsing where possible.
- Add a helper that ensures a real branch exists for the launch worktree,
  preferring a safe existing `## Dev branch:` and otherwise generating a
  collision-resistant namespaced branch.
- Commit only the dirty non-Coga work paths to that branch. Keep Coga OS state
  (`coga/tasks`, `coga/log.md`, digest spools, recurring state) on the existing
  task-state sync path.
- Push the branch to the configured remote. If the remote/auth path fails, keep
  the worktree and report the exact recovery command/path rather than deleting
  anything.
- Update the live ticket blackboard with the branch, worktree, commit, and base
  ref, then run the normal Coga state sync.
- Keep the existing `code/open-pr` step responsible for turning the pushed
  branch into a PR; this change only guarantees durable branch persistence and
  discoverability.

## Out of Scope

- Opening a PR from launch cleanup.
- Merging or pushing directly to `main`.
- Replacing the normal `code/implement` feature-worktree convention.
- Persisting ignored files or files outside the git checkout.

## Context

The intended code workflow still uses a separate feature worktree recorded
under `## Dev`. This ticket hardens the failure mode where work lands in the
launch isolation worktree anyway. The invariant is: if Coga is about to delete
a launch worktree, non-Coga work from that checkout must already exist on a
pushed branch and the ticket must say where it is.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
