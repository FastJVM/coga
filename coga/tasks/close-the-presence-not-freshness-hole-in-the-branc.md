---
title: Close the presence-not-freshness hole in the branch gate
status: draft
owner: nicktoper
workflow: null
---

## Description

The 'requires: branch' completion gate (step_gate.STEP_GATES['branch']) checks that '## Dev' records a usable 'branch:' and 'worktree:', not that they describe the current attempt: on a retried or relaunched implement the primary ticket copy still carries the earlier attempt's lines, so the gate passes while this attempt's write strands in the feature checkout — and the retry is exactly where stranding is most likely. detect-stranded-ticket-writes-across-checkouts left this out deliberately (its comparator compares ticket bytes, not linkage freshness). The closer is a separate cheap guard at the same bump site: does the recorded branch exist in this repository, and does the recorded worktree currently hold it ('git worktree list --porcelain', or 'git -C <worktree> rev-parse --abbrev-ref HEAD'). Decide warn-versus-refuse explicitly — the existing gate refuses, the stranded-write check warns — and keep the independent /tmp clone case honest: its branch is invisible to this repository, so 'unknown' must not read as 'stale'.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
