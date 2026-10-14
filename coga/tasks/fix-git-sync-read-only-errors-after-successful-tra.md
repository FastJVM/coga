---
title: Fix Git sync read-only errors after successful transitions
status: draft
owner: nicktoper
workflow: null
---

## Description

Investigate and fix automatic Git sync failing after a successful local workflow transition in an agent session. Preserve the completed transition and make recovery actionable without describing the whole repository as read-only.

Observed on 2026-10-14 in /home/n/Code/codex/multiply:
Command: coga bump v0/add-a-harness-inspection-and-manual-run-debug-tool
The command reported step 3 (review-design) assigned to nicktoper and exited 0, then printed two sync failures:
[git] sync failed: `git hash-object` failed: error: unable to create temporary file: Read-only file system
fatal: Unable to add coga/tasks/v0/add-a-harness-inspection-and-manual-run-debug-tool.md to database.
The messages were labeled Ticket: ... — step 3 (review-design) and Sync coga state.

Ticket editing and the local transition succeeded. The exact failing Git write path and root cause were not investigated. A sandbox or shared Git-directory permission boundary is a hypothesis, not an established diagnosis.

A subsequent attempt to create this draft in /home/n/Code/coga, with escalated execution requested, also failed: atomic_write_text could not create /home/n/Code/coga/coga/tasks/.fix-git-sync-read-only-errors-after-successful-tra.md.<random>.tmp (Errno 30). The session listed /home/n/Code/coga/.git as writable, but not the Coga working tree. This second failure does not establish the cause of the earlier Git object-write failure.

### Acceptance criteria
- Reproduce or explain the object-write failure using the checkout/common-Git-directory layout and agent permissions; identify the unavailable location and cause.
- Fix any Coga path or permission-integration defect found. If external sandbox policy causes the refusal, provide supported recovery guidance without bypassing it.
- Distinguish successful local transitions from failed Git publication; report the failed operation, relevant resolved location and underlying error.
- Provide and test recovery that publishes already-recorded state without rerunning bump, advancing another step, losing changes or duplicating the transition.
- Cover partial transition/sync failure and subsequent recovery with focused tests; update the owning Git/lifecycle documentation where necessary.

### Investigation pointers
src/coga/git.py::_hash_blob invokes git hash-object -w --path=... --stdin and forwards stderr without naming the resolved repository/object location. Sync failure reporting also appears in src/coga/mark.py and src/coga/git.py. Inspect the actual callers before selecting a fix.

The canceled coga/tasks/fix-git-sync-failure.md concerns control-branch divergence and fast-forward refresh failures, a distinct issue. No production-state reproduction or permission change has been performed.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
