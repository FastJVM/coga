---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: b4ee4c87-d307-46f3-9cc8-6bf8cae5fd87
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
   records a `branch:` or `worktree:`.

Autoclose never disposes of a checkout itself — `coga retire` owns those safety
proofs. Without step 6 an auto-closed ticket's worktree and branch outlive it
silently. Dream preserves checkout-bearing done tickets rather than deleting
the `## Dev` evidence the named command needs, so that debt stays actionable
until a human retires it.

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

Generated: 2026-09-15T16:56:14+00:00
Task: `recurring/autoclose-merged`

13 auto-closed ticket(s) still have a recorded feature checkout. Autoclose never removes one — `coga retire` owns the worktree and branch safety proofs:

- `autofix/report-per-skill-outcomes-from-gh-skill-update-in` "Report per-skill outcomes from gh skill update in skill-update": worktree `/home/n/Code/claude/coga-skill-update-per-skill`, branch `skill-update-per-skill` — `coga retire autofix/report-per-skill-outcomes-from-gh-skill-update-in`
- `cloning-a-coga-repo-has-no-setup-path` "Cloning a coga repo has no setup path": worktree `/home/n/Code/claude/coga-init-clone-setup`, branch `init-clone-setup` — `coga retire cloning-a-coga-repo-has-no-setup-path`
- `document-the-ticket-blackboard-writer-s-contract` "Document the ticket-blackboard writer's contract": worktree `/home/n/Code/claude/coga-blackboard-writer-contract`, branch `blackboard-writer-contract` — `coga retire document-the-ticket-blackboard-writer-s-contract`
- `dream-2026-w36-extract-backlog-18-findings-phase-4` "Dream 2026-W36 extract backlog: 18 findings Phase 4 could not consume": worktree `/home/n/Code/claude/coga-dream-w36-extract-backlog`, branch `dream-w36-extract-backlog` — `coga retire dream-2026-w36-extract-backlog-18-findings-phase-4`
- `dream-findings-have-three-routing-holes-that-lose` "Dream findings have three routing holes that lose work every run": worktree `/home/n/Code/claude/coga-dream-routing-holes`, branch `dream-routing-holes` — `coga retire dream-findings-have-three-routing-holes-that-lose`
- `four-parked-tickets-carry-premises-that-have-since` "Four parked tickets carry premises that have since inverted": worktree `/home/n/Code/claude/coga-triage-inverted-premises`, branch `triage-inverted-premises` — `coga retire four-parked-tickets-carry-premises-that-have-since`
- `isolated-checkouts-nothing-says-what-a-fresh-workt` "Isolated checkouts: nothing says what a fresh worktree lacks": worktree `/home/n/Code/claude/coga-fresh-checkout-lacks`, branch `fresh-checkout-lacks` — `coga retire isolated-checkouts-nothing-says-what-a-fresh-workt`
- `no-context-records-the-ci-posture-publish-only-rel` "No context records the CI posture: publish-only release workflow, no test gate": worktree `/home/n/Code/claude/coga-ci-posture`, branch `ci-posture` — `coga retire no-context-records-the-ci-posture-publish-only-rel`
- `no-rule-says-ticket-context-must-cite-symbols-not` "No rule says ticket Context must cite symbols, not line numbers": worktree `/home/n/Code/claude/coga`, branch `cite-symbols-rule` — `coga retire no-rule-says-ticket-context-must-cite-symbols-not`
- `recurring-context-never-mentions-the-packaged-twin` "Recurring context never mentions the packaged twin every template has": worktree `/home/n/Code/claude/coga-recurring-twin-note`, branch `recurring-twin-note` — `coga retire recurring-context-never-mentions-the-packaged-twin`
- `sync-context-omits-preflight-post-from-the-notific` "Sync context omits preflight_post from the notification contract": worktree `/home/n/Code/claude/coga-sync-context-preflight`, branch `sync-context-preflight` — `coga retire sync-context-omits-preflight-post-from-the-notific`
- `the-human-doc-vs-agent-context-boundary-is-decided` "The human-doc vs agent-context boundary is decided per ticket and recorded nowhere": worktree `/home/n/Code/claude/coga-doc-context-boundary`, branch `doc-context-boundary` — `coga retire the-human-doc-vs-agent-context-boundary-is-decided`
- `validate-that-committed-skill-scripts-with-a-sheba` "Validate that committed skill scripts with a shebang are executable": worktree `/home/n/Code/claude/coga-shebang-exec-check`, branch `shebang-exec-check` — `coga retire validate-that-committed-skill-scripts-with-a-sheba`
