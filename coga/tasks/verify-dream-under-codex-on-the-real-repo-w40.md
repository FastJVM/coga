---
title: Verify Dream under codex on the real repo (first period after merge)
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

This is the confirmation run for `make-dream-run-correctly-under-codex`,
done on the real repo once that ticket's PR merges. That ticket's
implement step already got a codex Dream run clean in the scratch repo
`FastJVM/coga-dream-scratch`. This run confirms the same result on
`FastJVM/coga`.

Use the first Dream period after the merge, not a fixed week. The
scheduled sweep may already run an earlier period under claude. The owner:
1. applies the `.codex/config.toml` grant recipe from `coga/codebase`
   (`## Sandbox and cross-machine dev loop`) to their primary checkout and
   trusts it in codex;
2. runs `coga dream --agent codex` attended, before the sweep takes that
   period.

**Done** when the run passes the preflight and finishes all six phases, and
it routes findings to real PRs, draft tickets, and markers. Its run record
must show `usage_status: ok`. Its summary goes on this blackboard, next to
the W39 claude baseline and the scratch run recorded on the parent ticket.
The `verify-read-only` step lists every new gap as a proposed ticket with
evidence; the owner files each one or rejects it. No gap is left only on the
blackboard.

Do not launch before `make-dream-run-correctly-under-codex` has merged.

## Context

- **Parent ticket:** `make-dream-run-correctly-under-codex`. The run/fix
  loop log on its blackboard shows what the scratch runs hit and how each
  was fixed.
- **W39 claude baseline (2026-09-21):**
  - validate-drift: 50 issues, 3 class drafts;
  - 4 knowledge PRs and 7 deletes;
  - 6 stale/drift PRs;
  - 12 drafts;
  - about 1 hour and 94 agent turns.
- The grant applies to every codex session in the repo; the owner accepted
  that on 2026-09-22.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
