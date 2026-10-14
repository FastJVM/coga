---
title: Fix Git sync read-only errors after successful transitions
status: draft
owner: nicktoper
workflow: code/design-then-implement
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

### Done when
- The object-write failure is reproduced or explained against the checkout/common-Git-directory layout and the agent's permissions: name the location Git could not write and why.
- Any Coga path or permission-integration defect found is fixed. If an external sandbox policy causes the refusal, Coga gives supported recovery guidance and does not try to bypass the sandbox.
- Output distinguishes a successful local transition from failed Git publication, naming the failed operation, the resolved location (repo / object directory) and the underlying error.
- A tested recovery path publishes already-recorded state without rerunning `bump`, advancing another step, losing changes or duplicating the transition (an existing command may satisfy this if the design shows it does).
- Focused tests cover partial transition/sync failure and the subsequent recovery, and the owning Git/lifecycle docs are updated where behavior changed.

## Context

### Code pointers (verify against current source)
- `git._hash_blob` runs `git -C <root> hash-object -w --path=<rel> --stdin` and raises `GitError` with Git's stderr only. It doesn't name the resolved repository or object directory. This is where the reported message comes from.
- `[git] sync failed: ... Message was: ...` is written to stderr and appended to the log by `git.sync_task_state`, the repo-wide sweep sync in `git` (the "Sync coga state" message), `mark` (task sync after `mark`/`bump`) and several places in `recurring_runner`. Inspect the real callers before choosing where to change reporting. A shared helper is likely better than editing each copy.
- The canceled `fix-git-sync-failure` ticket covered control-branch divergence and fast-forward refresh failures. That is a separate issue, so don't fold it in.

### Existing recovery candidate
`coga run publish-state [--message M] [PATH...]` (`publish_state.run_publish_state_recipe`) already exists. It fetches the remote control branch, runs one `publish` over the Coga roots with the named files required, and exits 0 only when every named file is on control. It is excluded from the exit sweep. Decide in design whether it already meets the recovery criterion: it records no new transition, and the failure message could point to it. Only add something new if it falls short.

### Docs (cited, not attached)
- `coga/internals/state-publication` (`docs/contexts/coga/internals/state-publication/SKILL.md`) owns `publish`, the end-of-command sweep, strict versus best-effort paths and `run publish-state`. Read the sections on best-effort sync failure and `run publish-state`. It is the likely doc to update, so read it from disk rather than attaching it.
- `coga/sync` states the rule: a failed push of a durable write surfaces the miss, keeps the file as written and never undoes the transition. The fix must preserve this.
- `coga/testing` → "Restricted sandboxes" records Codex sandbox limits seen in this repo. Add the finding there if the root cause is a sandbox policy.

### Diagnosis hypothesis (unverified)
`/home/n/Code/codex/multiply/.git` is a plain directory, not a worktree gitfile, so a shared common Git directory is unlikely there. Codex's `workspace-write` sandbox is known to keep `.git` read-only inside writable roots. That matches `hash-object -w` failing with EROFS while the ticket file write succeeded. Confirm against the Codex version and sandbox config before relying on it. No production-state reproduction or permission change has been made. The second failure, in `/home/n/Code/coga` (`.git` writable but the working tree not), is the reverse pattern. It shows the sandbox's writable roots vary by session, not the cause of the first failure.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
