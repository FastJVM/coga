---
title: Triage five review comments that merged unanswered in Aug-Sep 2026
status: in_progress
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
agent: claude
launch_generation: dc6c93dc-b535-4790-8e11-94594af87ec6
---

## Description

Triage the five unanswered review comments identified by phase 2 of
`verify-the-pr-review-comment-loop-once-the-review` on 2026-09-13. Recheck each
concern against current code and later work, recommend **fix / won't fix /
already moot**, and prepare a separate follow-up draft for each proposed fix.
`nicktoper` makes the final verdicts; completion means all five have an explicit
owner decision with supporting evidence and every accepted fix has its own
scoped ticket. Implementation belongs to those follow-up tickets.

## Context

### Workflow and deliverable

1. **agent-produces:** Read the original review threads, current source, and
   existing tickets/Git history for later fixes. Record the assessment date and
   control-branch commit. On the blackboard, produce five rows: exact comment
   URL; original priority; current evidence; recommendation and tradeoff;
   follow-up link; owner verdict (initially unset). Start with PR 699's P1.
   Distinguish verified behavior from plausible concerns; an outdated thread
   or merged PR alone does not prove a fix.

   Use `coga create` for a separate **draft** per proposed fix, or reuse an
   equivalent follow-up. Include the original comment, this ticket,
   module/symbol pointers, expected behavior, scope, acceptance criteria and
   focused verification. Use `code/with-review` for a code or context change;
   preserve the owner's workflow choice for existing tickets. Keep new drafts
   unactivated.
2. **human-owns-and-finishes:** `nicktoper` chooses each verdict, edits or
   approves fix scopes, and decides whether rejected drafts should be revised
   or canceled. Advance this owner gate only when explicitly asked.
3. **report-to-coga:** Record dated owner verdicts, reasons and ticket links.
   Apply requested draft revisions and explicitly authorized cancellations
   (using the CLI for lifecycle changes). Verify that every accepted fix has
   a separate actionable ticket and every provisional draft has a disposition.
   Ask the owner about missing decisions or follow-ups before closing.

For **already moot**, cite the fixing change and evidence covering the original
scenario. Partial fixes still need a verdict on the residual concern. For
**won't fix**, preserve the owner's reason and accepted consequence.

This task covers triage and ticket preparation. Code fixes, live recurring
runs, GitHub replies or thread resolution, and changes to merge policy are
outside its scope. The separate
`coga/tasks/autoclose-should-name-unanswered-review-threads-on.md` owns automatic
reporting of unanswered threads; this task does not depend on it shipping or
on the live review queue becoming empty.

### Findings to recheck

These are historical audit findings to recheck. PR links are starting points;
capture exact comment URLs during triage. Recover the source ticket from Git
history if it has been retired.

| PR / priority | Original concern and source pointer |
| --- | --- |
| [699](https://github.com/FastJVM/coga/pull/699) / P1 | `recurring_runner._broadcast_scan` in `src/coga/recurring_runner.py` marks `_LEDGER_LOADED` after pre-scan catch-up. The reported race lets another checkout publish the same period before the first create sync, while the cached ledger prevents a fresh check and permits a duplicate launch. Follow the create-sync and `_validate_control_serviced_period` paths when reassessing. |
| [704](https://github.com/FastJVM/coga/pull/704) / P2 | `config._require_trackable_context_entry` in `src/coga/config.py` accepts `path.is_file() or path.is_symlink()`. The concern is acceptance of a context artifact whose symlink target is outside the checkout, so another clone can compose a different prompt. Check actual artifact validation as well as root validation. |
| [705](https://github.com/FastJVM/coga/pull/705) / P2 | Recurring `ticket.py` shims, including `coga/recurring/autoclose-merged/ticket.py`, finish through plain `coga bump`. The audit observed `[human:nicktoper] task done` for headless completions on 2026-09-10 and 09-11 in `coga/log.md`; the comment requested system attribution. Inspect attribution through the child process, not just the shim's command spelling. |
| [747](https://github.com/FastJVM/coga/pull/747) / P2 | `commands.launch._reconcile_released_launch_admission` in `src/coga/commands/launch.py` captures `git.FileMutationRollback` after the control fetch instead of against the validated `current_bytes`. The reported window can overwrite a manual ticket edit made during that fetch with the earlier released revision. |
| [755](https://github.com/FastJVM/coga/pull/755) / P2 | `dev/code`, “Design pivots and superseded plans,” keeps superseded designs below the blackboard fence, so the archive enters future prompts. The original report also raised the synthesis gate for a long archive; the current documented mitigation excludes exact `## Superseded designs` sections in `blackboard.prelaunch_blackboard_synthesis_reason_text`. Recheck that mitigation separately from the remaining prompt-composition concern; moving the archive above the fence is the comment's proposal, not an approved design. |

PR 696 and PR 706 are excluded: the audit found them overtaken by PR 761
(`a-slack-repo-without-important-webhook-can-abort-t`) and PR 784
(`scripts/human_minutes.py` PR-regex rewrite), respectively.

### Focused reading

`coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`) is cited rather than
attached: read the “Five bot review threads merged unanswered” bullet under
“Gotchas when editing coga's own code.” It preserves the original audit and
the partial PR 755 mitigation; treat its claim that no follow-up exists as
something to recheck against current tickets.

`dev/code` (`coga/contexts/dev/code/SKILL.md`) is cited rather than attached:
read “Review threads that merge unanswered” and “Design pivots and superseded
plans.” The owner retains merge and thread-resolution decisions, and archived
designs currently remain part of the composed blackboard. Any follow-up that
changes this behavior must update the owning context and its packaged twin in
the same PR; list those touchpoints in that draft.

<!-- coga:blackboard -->

## Assessment in progress — 2026-09-18

Control checkout: `main` at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`
(`origin/main` matched at the start). Scope is triage and unactivated draft
preparation only; owner verdicts remain unset.

- Read the five original GitHub threads through the read-only GraphQL API.
  Each target thread still has one comment, is unresolved, and is not outdated;
  neither that state nor the merged PR establishes whether the concern survives.
- PR 699 first: the pre-scan ledger remains marked loaded and both create-sync
  guards reuse it. `_validate_control_serviced_period` also trusts a loaded
  snapshot. Checking the competing-checkout/reaped-task scenario in isolation.
- PR 755 is partial: the exact archive section is excluded from draft synthesis
  checks, while composition still includes it. The proposal to move it above
  the fence has not been approved.
- The source PR tickets remain present. The retired audit is recoverable at
  `6c305673^:coga/tasks/verify-the-pr-review-comment-loop-once-the-review.md`.
  Existing-ticket/history search and focused probes are in progress.
