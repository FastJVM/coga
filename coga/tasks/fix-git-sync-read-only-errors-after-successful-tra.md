---
title: Fix Git sync read-only errors after successful transitions
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

Investigate and fix automatic Git sync failing after a successful local workflow transition in an agent session. Preserve the completed transition, and make the failure message say what failed and how to recover. Today it shows only Git's raw `Read-only file system` stderr, which reads as if the whole checkout is read-only even though the ticket write just succeeded.

Observed on 2026-10-14 in /home/n/Code/codex/multiply:
Command: coga bump v0/add-a-harness-inspection-and-manual-run-debug-tool
The command reported step 3 (review-design) assigned to nicktoper and exited 0, then printed two sync failures:
[git] sync failed: `git hash-object` failed: error: unable to create temporary file: Read-only file system
fatal: Unable to add coga/tasks/v0/add-a-harness-inspection-and-manual-run-debug-tool.md to database.
The messages were labeled Ticket: ... — step 3 (review-design) and Sync coga state.

Ticket editing and the local transition succeeded. The exact failing Git write path and root cause were not investigated. A sandbox or shared Git-directory permission boundary is a hypothesis, not an established diagnosis.

A later attempt to create this draft in another sandboxed session hit EROFS on the working tree while `.git` was writable. That is the reverse pattern and does not explain the first failure.

### Done when
- The object-write failure is reproduced or explained against the checkout/common-Git-directory layout and the agent's permissions: name the location Git could not write and why. A synthetic reproduction is enough, for example a read-only objects directory or `GIT_OBJECT_DIRECTORY`; re-running the original Codex session is not required.
- Any Coga path or permission-integration defect found is fixed. If an external sandbox policy causes the refusal, Coga gives supported recovery guidance and does not try to bypass the sandbox.
- Output distinguishes a successful local transition from failed Git publication, naming the failed operation, the resolved location (repo / object directory) and the underlying error.
- A tested recovery path publishes already-recorded state without rerunning `bump`, advancing another step, losing changes or duplicating the transition (an existing command may satisfy this if the design shows it does).
- Focused tests cover partial transition/sync failure and the subsequent recovery, and the owning Git/lifecycle docs are updated where behavior changed.

## Context

### Code pointers (verify against current source)
- `git._hash_blob` runs `git -C <root> hash-object -w --path=<rel> --stdin` and raises `GitError` with Git's stderr only. It doesn't name the resolved repository or object directory. This is where the reported message comes from.
- `[git] sync failed: ... Message was: ...` is written to stderr and appended to the log by `git.sync_task_state`, the repo-wide sweep sync in `git` (the "Sync coga state" message), `mark` (task sync after `mark`/`bump`) and several places in `recurring_runner`, plus `commands/delete.py` and `commands/recurring.py`, which print `[git] sync failed` without the message suffix. Inspect the real callers before choosing where to change reporting. A shared helper is likely better than editing each copy.
- The canceled `fix-git-sync-failure` ticket covered control-branch divergence and fast-forward refresh failures. That is a separate issue, so don't fold it in.

### Existing recovery (leading hypothesis: already sufficient)
The end-of-command sweep is documented as the retry for every earlier miss. The observed second failure, "Sync coga state", was that sweep already retrying in the same process. Any later sweeping command run where `.git` is writable republishes the dirty ticket and log. A likely small fix: enrich object-write `GitError`s with the resolved location (for example `git rev-parse --git-path objects`), route the duplicated reporting through one helper, and add a remedy line. Design should confirm this before proposing anything larger.

`coga run publish-state [--message M] [PATH...]` (`publish_state.run_publish_state_recipe`) already exists. It fetches the remote control branch, runs one `publish` over the Coga roots with the named files required, and exits 0 only when every named file is on control. It is excluded from the exit sweep. Decide in design whether it already meets the recovery criterion: it records no new transition, and the failure message could point to it. Only add something new if it falls short.

### Docs (cited, not attached)
- `coga/internals/state-publication` (`docs/contexts/coga/internals/state-publication/SKILL.md`) owns `publish`, the end-of-command sweep, strict versus best-effort paths and `run publish-state`. Read the sections on best-effort sync failure and `run publish-state`. It is the likely doc to update, so read it from disk rather than attaching it.
- `coga/sync` states the rule: a failed push of a durable write surfaces the miss, keeps the file as written and never undoes the transition. The fix must preserve this.
- `coga/testing` → "Restricted sandboxes" already says state-changing commands fail when the sandbox forbids `.git/index.lock`, and to rerun unsandboxed or grant `.git` write access. If a sandbox policy is the cause, extend that bullet to cover object writes rather than adding a new entry.
- `dev/checkouts` (`docs/contexts/dev/checkouts/SKILL.md`) explains what a bump printing `[git] sync failed` means for launch's checkout return. Keep any wording change consistent with it.

### Diagnosis hypothesis (unverified)
`/home/n/Code/codex/multiply/.git` is a plain directory, not a worktree gitfile, so a shared common Git directory is unlikely there. Codex's `workspace-write` sandbox is known to keep `.git` read-only inside writable roots. That matches `hash-object -w` failing with EROFS while the ticket file write succeeded. Confirm against the Codex version and sandbox config before relying on it. No production-state reproduction or permission change has been made. 

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Verdict: Ready to launch after minor edits. Code claims accurate (`_hash_blob`, `sync_task_state`, `sync_coga_state`, `mark._publish`, four `recurring_runner` sites, `run_publish_state_recipe`). Gaps applied: missing callers `commands/delete.py` and `commands/recurring.py`; existing Restricted-sandboxes `.git/index.lock` bullet and `dev/checkouts` cited; exit sweep is the automatic retry (the observed "Sync coga state" failure was that retry); "whole repo read-only" clause made concrete; synthetic repro declared acceptable; second-failure paragraph trimmed. Workflow fits; cite-not-attach correct; no layer over 40% of the ~3.5k-token prompt; scope fine as one ticket.
