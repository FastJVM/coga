---
title: Preserve edits during released claim recovery
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
launch_generation: 1333126c-d74c-4a1b-8378-0277e2582484
---

## Description

Preserve a manual ticket edit made while released-launch recovery fetches control. Reconciliation currently validates one local revision, fetches remotely, then captures a fresh rollback snapshot and overwrites that later revision with the earlier admitted form.

This is a provisional P2 fix scope from [the triage](triage-five-review-comments-that-merged-unanswered.md). Owner verdict is unset; keep the draft unactivated.

### Evidence and source

Original [PR 747 comment](https://github.com/FastJVM/coga/pull/747#discussion_r3932656206); source ticket: [megalaunch-activates-picks-before-preflight](megalaunch-activates-picks-before-preflight.md). Assessed 2026-09-18 at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

A real local-Git recovery probe inserted a manual correction during `_control_base_for_attempt`. For both an exact pending remote claim and an already-admitted remote claim, recovery returned success, removed the correction locally, and published without it. Git history shows the helper's relevant body unchanged since PR 747. The Coga publication barrier does not serialize an ordinary editor.

### Expected behavior and scope

Fix `src/coga/commands/launch.py::_reconcile_released_launch_admission` at the boundary between its validated `current_bytes` and the write. Use `git.FileMutationRollback` with the validated revision as its baseline, or compare those exact bytes immediately before writing; do not bless the intervening editor revision by capturing it after fetch.

Keep remote compare-and-set and the pending/admitted distinction intact. On changed local bytes, fail loudly without admitting, publishing, restoring over, or spawning from the stale ticket. Preserve the local released witness and manual correction so an operator can inspect and retry deliberately. This closes the reported fetch window; do not promise a filesystem-wide atomic editor lock.

### Acceptance and focused verification

- Inject a manual body/blackboard edit during the real control fetch, with matching pending control bytes. Reconciliation refuses and preserves the edit and released generation.
- Repeat when control already has the matching admitted revision.
- Confirm unchanged local bytes still allow both existing recovery cases.
- Preserve refusal on mismatched remote bytes, publication-failure recovery and barrier-protected rollback semantics.
- Extend `tests/test_launch.py` next to `test_released_launch_admission_reconciles_control_ticket`; use a local bare remote, no real agent process. Add a focused rollback test only if shared rollback behavior changes.
- Update the released-witness recovery invariant in `coga/contexts/coga/launch-internals/SKILL.md`, the PR 747 gotcha in `coga/codebase`, and their packaged twins; run packaging checks.

Tradeoff: a concurrent manual correction causes a recoverable refusal and another operator retry. That is preferable to silently discarding the correction. Out of scope: changing claim formats, redesigning all launch transactions, or addressing the other already-resolved PR 747 threads.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
