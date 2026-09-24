---
title: Verify Dream under codex on the real repo (W40)
status: draft
owner: nicktoper
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
step: 1 (brief-and-hand-off)
---

## Description

Confirmation run for make-dream-run-correctly-under-codex, after its PR merges. The owner applies the .codex/config.toml grant recipe from coga/codebase to this checkout and launches W40 with coga dream --agent codex, attended, against FastJVM/coga. Done when the run completes all six phases, routes findings to PRs, draft tickets and markers, records usage_status: ok, and its summary is recorded on this blackboard next to the W39 claude baseline (validate-drift 50 issues / 3 class drafts, 4 knowledge PRs + 7 deletes, 6 stale/drift PRs, 12 drafts, ~1 h). Any new gap gets a fix or a filed ticket, never left only on the blackboard. Do not launch before make-dream-run-correctly-under-codex is merged.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
