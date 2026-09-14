---
title: Triage five review comments that merged unanswered in Aug-Sep 2026
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

Found by verify-the-pr-review-comment-loop-once-the-review phase 2 (2026-09-13). Five codex-connector review threads merged with no reply, no code change at the flagged line, and no later ticket. Each needs a human verdict (fix / won't fix / already moot) and, for a fix, its own ticket. (1) PR 699 P1 src/coga/recurring_runner.py near the _LEDGER_LOADED = 'yes' mark: cache marked loaded after the pre-scan catch-up, so a competing checkout that publishes the same period between the catch-up and the first create sync can trigger a double launch; the code still marks the cache loaded unconditionally. (2) PR 704 P2 src/coga/config.py context artifact check accepts any symlink (path.is_file() or path.is_symlink()) including ones whose target is outside the checkout, so another clone composes a different prompt. (3) PR 705 P2 - confirmed live: the recurring ticket.py shims finish via plain coga bump, so headless completions are logged as [human:nicktoper] task done (see recurring/autoclose-merged entries on 2026-09-10 and 09-11); the comment asked for a system-attributed completion path. (4) PR 747 P2 src/coga/commands/launch.py released-witness reconciliation captures FileMutationRollback after the control fetch instead of from the validated current_bytes, so a concurrent manual ticket edit made during the fetch can be overwritten by the stale released revision. (5) PR 755 P2 coga/contexts/dev/code/SKILL.md Design pivots section moves the superseded design below the blackboard fence, where a 600+ char entry trips prelaunch_blackboard_synthesis_reason_text and a shorter one composes into every future prompt; the comment asked to keep the archive above the fence. Two more dropped threads were overtaken out-of-band and need nothing: PR 696 (fixed by ticket a-slack-repo-without-important-webhook-can-abort-t, PR 761) and PR 706 (scripts/human_minutes.py PR regex rewritten by PR 784).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
