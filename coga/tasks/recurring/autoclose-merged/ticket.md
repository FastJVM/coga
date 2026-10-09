---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: b6109e94-26ec-4130-a3fc-e511590946cc
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
workflow is at its final step, then sweep landed branches without live tickets.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `coga mark done`. Once a day this recurring task fires. Its
`ticket.py` runs the existing merged-ticket sweep, which:

1. scans active and in-progress tickets,
2. reads the `pr:` line under each ticket blackboard's `## Dev` section,
3. checks the linked PR state with `gh pr view`,
4. leaves non-final-step tickets alone as suspicious, and
5. marks final-step or workflow-less tickets `done` when the PR is merged,
6. disposes of the feature checkout of each ticket it closed that still
   records a `branch:` or `worktree:`, and of every open entry in the durable
   worklist `retires.md` beside this template — worktree removed, then local
   branch, then remote branch, each under the same safety proofs `coga retire`
   runs (same-repo linked worktree on the recorded branch, locally pristine,
   no other live ticket claiming it, no open PR, landed or at the merged PR's
   exact head), and
7. reports what it disposed of and what a proof refused, with the reason: the
   refusals go to the coga-important Slack channel and into `retires.md`,
   keyed by task slug, and
8. name unresolved, non-outdated review threads with only their opening
   comment on each closed PR in the closure audit line, sweep report, and
   Slack summary. Report only: never resolve or reply.

Step 6 is a direct destructive change, declared here on purpose: the proofs
are deterministic, narrow, and named in the `coga/autoclose/sweep` skill, and
the earlier design — only *naming* a `coga retire` follow-up — left a
ten-entry backlog nobody typed. It runs only when the checkout is on the
control branch (a hand run elsewhere preserves everything and says so) and
only touches worktrees linked to the clone it runs from. Dream preserves
checkout-bearing done tickets rather than deleting the `## Dev` evidence the
proofs need. The worklist is what keeps the *list* of refused checkouts
actionable: this period task is deleted at the next period boundary, so step 7
writes the entries to `coga/recurring/<name>/retires.md` for the template this
task was minted from; every run re-judges the open entries (an entry whose
ticket is gone is proven by the merged PRs for its branch name) and drops the
ones discharged — local branch gone (in the owning repository, for a
worktree another clone owns), and worktree directory gone or this
repository's own primary checkout (a ticket worked in the single-checkout
layout records it; nobody disposes of it, so it is never debt). The rules are
in the `coga/autoclose/sweep` skill.

This sweep is the sole trigger for auto-closing merged tickets — there is
no manual `automerge` command. The recurring task only changes when the
sweep runs; it does not change which tickets are safe to close.

Done events produced by the sweep go through the shared `mark_done` finalizer,
so each closure posts live to Slack exactly as a manual `coga mark done` would.
After the autoclose recipe succeeds, `ticket.py` runs the registered
`branch-sweep` recipe, even when no ticket closed. It then bumps only if both
recipes succeeded. The daily cadence and reporting contract live in
[coga/recurring/scheduling](context:coga/recurring/scheduling); the deletion
proofs and worktree opt-in remain those in
[dev/checkout-cleanup](context:dev/checkout-cleanup).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-10-09T20:47:41+00:00
Task: `recurring/autoclose-merged`

5 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `autofix-write-ups-lose-their-body-to-h2-headings` "Autofix tickets launch without their write-up when the analyst uses H2 headings": branch `ticket-body-sections`
- `move-coga-development-rules-out-of-the-shipped-bas` "Move Coga-development rules out of the shipped base prompt": branch `base-prompt-coga-rules`
- `overload-base-text-prompt-etc` "overload base text; prompt, etc.": branch `repo-resource-overrides`
- `publish-all-coga-and-context-files-automatically` "Publish all Coga and context files automatically": branch `publish-coga-roots`
- `skip-inactive-repo-recurring-templates-without-str` "Skip inactive-repo recurring templates without strict validation": branch `inactive-lenient-template-skip`

## Branch Sweep

Generated: 2026-10-09T20:47:54+00:00
Task: `recurring/autoclose-merged`

Result: 0 local and 0 remote branch(es) deleted, 0 worktree(s) removed, 0 skipped-worktree-pinned, 20 skipped.
- skipped: autoclose-retires-durable-home, bloated-blackboard-remedy, codex/retro-recurring-branch-sweep-knowledge, dream-w40-testing-baseline, fence-aware-section-splitter, fix/codex-peer-review-in-sandbox, guard-reauthor-in-progress, nicktoper-patch-1, peer-review-caveat, publish-off-control, recurring-crlf-lease, recurring-ledger-from-log, retire-worklist-linked-only, scrub-sa-token, shebang-exec-check, slack-important-alert, split-ticket-contract, terminal-branch-cleanup, warn-on-bootstrap-unpublished-edits, wedge-ticket-admin-reproduction

### Decisions

- Branch sweep: terminal ticket 'define-the-split-a-ticket-mechanic-shared-by-code' records checkout '/home/n/Code/coga' outside this repository or unavailable — its branch records grant no cleanup authority here.
- Branch sweep: terminal ticket 'document-the-remedy-for-a-bloated-blackboard-sibli' records checkout '/home/n/Code/claude/coga-bloated-blackboard-remedy' outside this repository or unavailable — its branch records grant no cleanup authority here.
- Branch sweep: terminal ticket 'scrub-the-service-account-token-from-the-launch-ch' records checkout '/home/n/Code/claude/coga-scrub-sa-token' outside this repository or unavailable — its branch records grant no cleanup authority here.
- Branch sweep: terminal ticket 'validate-that-committed-skill-scripts-with-a-sheba' records checkout '/home/n/Code/claude/coga-shebang-exec-check' outside this repository or unavailable — its branch records grant no cleanup authority here.
- Branch cleanup: local 'autoclose-retires-durable-home' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'bloated-blackboard-remedy' has merged PR #856 at 449bf55590e8, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/blackboard/SKILL.md, src/coga/dream_validate_drift.py (+3 more) — left in place.
- Branch cleanup: local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'codex/retro-recurring-branch-sweep-knowledge' has merged PR #859 at 9b9e80d36a05, but the ref carries commits touching coga/skills/coga/branch-sweep/sweep/SKILL.md, src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md — left in place.
- Branch cleanup: local 'codex/retro-recurring-branch-sweep-knowledge' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'coga/skill-update' is the shared skill-update branch — left in place.
- Branch sweep: 'docs/correct-prompt-report-readme' is recorded on a live ticket — left in place.
- Branch sweep: 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/dream-w40-testing-baseline (no merged PR).
- Branch cleanup: skipping remote origin/fence-aware-section-splitter (no merged PR).
- Branch cleanup: skipping remote origin/fix/codex-peer-review-in-sandbox (no merged PR).
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/nicktoper-patch-1 (no merged PR).
- Branch sweep: 'onboarding-publish-before-handoff' is recorded on a live ticket — left in place.
- Branch sweep: 'one-line-audit-events' is recorded on a live ticket — left in place.
- Branch sweep: 'owned-mac-clean-install' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/peer-review-caveat (no merged PR).
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch cleanup: local 'scrub-sa-token' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'self-qa-stale-ticket-and-state-side-effects' is recorded on a live ticket — left in place.
- Branch sweep: 'shebang-exec-check' has merged PR #800 at a02e2930511f, but the ref carries commits touching coga/skills/anthropic/skill-creator/eval-viewer/generate_review.py, coga/skills/clarity/scripts/validate_package.py, src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/gmail.py (+1 more) — left in place.
- Branch cleanup: local 'shebang-exec-check' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch cleanup: local 'split-ticket-contract' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/terminal-branch-cleanup (no merged PR).
- Branch cleanup: skipping remote origin/warn-on-bootstrap-unpublished-edits (no merged PR).
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).
