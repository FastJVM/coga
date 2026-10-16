---
title: Discharge retires.md entries in the clone that owns them
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
---

## Description

Follow-up to run-clone-local-recurring-work-in-every-clone (owner decision 2026-10-16: kept out of that PR). Branch-sweep is now `scope: clone` and runs daily in every clone, but re-judging the autoclose-merged `retires.md` worklist still happens only in whichever clone services the repo-scoped autoclose-merged period. An entry whose `owner` is another clone (a foreign primary, or a foreign linked worktree) is reported for manual cleanup there and never discharges unless that clone happens to run autoclose. Wanted: a clone-scoped pass that judges and disposes of the entries owned by the sweeping clone, through the existing proofs in `checkout_disposal.dispose_checkout` and `retire_worklist`, and discharges them. Open design question: discharging edits `retires.md`, which is committed (`merge=union`, CAS-written). That breaks the 'clone scope commits nothing' property, so the pass needs its own publish path (for example `git.publish` of just that file, as upstream-coga does for its cursor). Related: autoclose-re-posts-another-clone-s-primary-checkou.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
