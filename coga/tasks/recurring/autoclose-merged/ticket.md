---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: ec1d9db2-c1ea-4ad8-a059-d62f099adabb
workflow:
  name: autoclose-merged/sweep
  steps:
  - name: sweep
    skills:
    - coga/autoclose/sweep
    assignee: agent
---

## Description

Close Coga tickets whose linked GitHub PR has already merged and whose Coga
workflow is at its final step.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `coga mark done`. Once a day this recurring task fires. Its
`ticket.py` runs the existing merged-ticket sweep, which:

1. scans active and in-progress tickets,
2. reads the `pr:` line under each ticket blackboard's `## Dev` section,
3. checks the linked PR state with `gh pr view`,
4. leaves non-final-step tickets alone as suspicious, and
5. marks final-step or workflow-less tickets `done` when the PR is merged, and
6. names the `coga retire` follow-up for each ticket it closed that still
   records a `branch:` or `worktree:`, and records it in the durable worklist
   `retires.md` beside this template, keyed by task slug.

Autoclose never disposes of a checkout itself — `coga retire` owns those safety
proofs. Without step 6 an auto-closed ticket's worktree and branch outlive it
silently. Dream preserves checkout-bearing done tickets rather than deleting
the `## Dev` evidence the named command needs, so that debt stays actionable
until a human retires it. The worklist is what keeps the *list* of that debt
actionable: this period task is deleted at the next period boundary, so step 6
writes the entries to `coga/recurring/<name>/retires.md` for the template this
task was minted from and, on every run, drops the entries already discharged —
worktree directory gone and local branch gone. The rules are in the
`coga/autoclose/sweep` skill.

This sweep is the sole trigger for auto-closing merged tickets — there is
no manual `automerge` command. The recurring task only changes when the
sweep runs; it does not change which tickets are safe to close.

Done events produced by the sweep go through the shared `mark_done` finalizer,
so each closure posts live to Slack exactly as a manual `coga mark done` would.
A quiet day with no merged final-step tickets exits successfully and changes
nothing.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-09-18T15:33:47+00:00
Task: `recurring/autoclose-merged`

10 auto-closed ticket(s) still have a recorded feature checkout. Autoclose never removes one — `coga retire` owns the worktree and branch safety proofs:

- `adjudicate-parked-and-active-tickets-whose-premise` "Adjudicate parked and active tickets whose premises have moved": worktree `/home/n/Code/claude/coga-adjudicate-moved-premises`, branch `adjudicate-moved-premises` — `coga retire adjudicate-parked-and-active-tickets-whose-premise`
- `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo` "Handle a bare SLACK_WEBHOOK_URL during empty-repo init": worktree `/home/n/Code/claude/coga-init-bare-slack-env`, branch `init-bare-slack-env` — `coga retire cleanup/handle-a-bare-slack-webhook-url-during-empty-repo`
- `define-the-recipe-reporting-contract-report-durabi` "Define the recipe reporting contract: report durability and failure surface": worktree `/home/n/Code/claude/coga-recipe-reporting-contract`, branch `recipe-reporting-contract` — `coga retire define-the-recipe-reporting-contract-report-durabi`
- `document-when-to-attach-a-large-context-versus-cit` "Document when to attach a large context versus cite it for direct reading": worktree `/home/n/Code/claude/coga-attach-vs-cite`, branch `attach-vs-cite` — `coga retire document-when-to-attach-a-large-context-versus-cit`
- `persist-autoclose-retire-follow-ups` "Persist autoclose retire follow-ups": worktree `/home/n/Code/claude/coga-autoclose-retire-worklist`, branch `autoclose-retire-worklist` — `coga retire persist-autoclose-retire-follow-ups`
- `record-dochub-s-why-not-the-api-answer-that-browse` "Record DocHub's why-not-the-API answer that browser api-first requires": worktree `/home/n/Code/claude/coga-dochub-api-answer`, branch `dochub-api-answer` — `coga retire record-dochub-s-why-not-the-api-answer-that-browse`
- `record-or-clear-the-standing-repo-wide-coga-valida` "Record or clear the standing repo-wide coga validate baseline": worktree `/home/n/Code/claude/coga-validate-baseline`, branch `validate-baseline` — `coga retire record-or-clear-the-standing-repo-wide-coga-valida`
- `state-which-branch-is-canonical-for-machine-genera` "State which branch is canonical for machine-generated Coga state": worktree `/home/n/Code/claude/coga-sync-canonical-policy`, branch `sync-canonical-policy` — `coga retire state-which-branch-is-canonical-for-machine-genera`
- `the-period-task-context-never-covers-the-determini` "The period-task context never covers the deterministic ticket.py firing": worktree `/home/n/Code/claude/coga-period-task-recipe-firing`, branch `period-task-recipe-firing` — `coga retire the-period-task-context-never-covers-the-determini`
- `the-v2-parking-area-premise-check-has-four-holes` "The v2 parking-area premise check has four holes": worktree `/tmp/coga-v2-premise-review.5AX4MD/repo`, branch `v2-premise-holes` — `coga retire the-v2-parking-area-premise-check-has-four-holes`

Recorded in the durable worklist `/home/n/Code/claude/coga/coga/recurring/autoclose-merged/retires.md`; this period task is deleted at the next period boundary.
