---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: f5cd4a8f-79f0-4eac-8e9a-48c4b64f7c11
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
   keyed by task slug.

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
ones discharged — worktree directory gone and local branch gone. The rules
are in the `coga/autoclose/sweep` skill.

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

Generated: 2026-09-23T17:42:10+00:00
Task: `recurring/autoclose-merged`

8 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (worklist backlog): worktree `/home/n/Code/claude/coga-resources-pkg-init`, branch `resources-pkg-init`
- `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo` (worklist backlog): worktree `/home/n/Code/claude/coga-init-bare-slack-env`, branch `init-bare-slack-env`
- `define-the-recipe-reporting-contract-report-durabi` (worklist backlog): worktree `/home/n/Code/claude/coga-recipe-reporting-contract`, branch `recipe-reporting-contract`
- `document-when-to-attach-a-large-context-versus-cit` (worklist backlog): worktree `/home/n/Code/claude/coga-attach-vs-cite`, branch `attach-vs-cite`
- `packaged-code-workflows-never-name-coga-retire-as` (worklist backlog): worktree `/home/n/Code/claude/coga-review-closing-act`, branch `review-closing-act`
- `record-dochub-s-why-not-the-api-answer-that-browse` (worklist backlog): worktree `/home/n/Code/claude/coga-dochub-api-answer`, branch `dochub-api-answer`
- `state-which-branch-is-canonical-for-machine-genera` (worklist backlog): worktree `/home/n/Code/claude/coga-sync-canonical-policy`, branch `sync-canonical-policy`
- `ticket-specs-should-cite-symbols-not-line-numbers` (worklist backlog): worktree `/home/n/Code/claude/coga-design-cite-symbols`, branch `design-cite-symbols`

9 checkout(s) preserved — a proof refused; each stays on the worklist until a human acts:

- `adjudicate-parked-and-active-tickets-whose-premise` (worklist backlog): worktree `/home/n/Code/claude/coga-adjudicate-moved-premises`, branch `adjudicate-moved-premises` — branch 'adjudicate-moved-premises' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place. (`coga retire adjudicate-parked-and-active-tickets-whose-premise`)
  - Worktree cleanup: local 'adjudicate-moved-premises' advanced past the merged PR head ee178b909780 — preserving it.
  - Worktree cleanup: branch 'adjudicate-moved-premises' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place.
  - Branch cleanup: local 'adjudicate-moved-premises' advanced past the merged PR head ee178b909780 — preserving it.
  - Branch cleanup: local 'adjudicate-moved-premises' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/adjudicate-moved-premises because the local branch remains.
- `agent-usage-report` (worklist backlog): worktree `/home/n/Code/codex/coga-usage-report`, branch `usage-report` — '/home/n/Code/codex/coga-usage-report' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`coga retire agent-usage-report`)
  - Worktree cleanup: '/home/n/Code/codex/coga-usage-report' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'usage-report' not present.
  - Branch cleanup: remote origin/usage-report already gone.
- `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `quiet-first-run` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`coga retire cleanup/quiet-the-first-run-noise-from-recurring-jobs-and`)
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'quiet-first-run' not present.
  - Branch cleanup: remote origin/quiet-first-run already gone.
- `document-the-remedy-for-a-bloated-blackboard-sibli` (worklist backlog): worktree `/home/n/Code/claude/coga-bloated-blackboard-remedy`, branch `bloated-blackboard-remedy` — branch 'bloated-blackboard-remedy' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place. (`coga retire document-the-remedy-for-a-bloated-blackboard-sibli`)
  - Worktree cleanup: local 'bloated-blackboard-remedy' advanced past the merged PR head 449bf55590e8 — preserving it.
  - Worktree cleanup: branch 'bloated-blackboard-remedy' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place.
  - Branch cleanup: local 'bloated-blackboard-remedy' advanced past the merged PR head 449bf55590e8 — preserving it.
  - Branch cleanup: local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/bloated-blackboard-remedy because the local branch remains.
- `installer-managed-skills-the-local-adaptation-guar` (worklist backlog): worktree `/home/n/Code/coga`, branch `gh-backed-readonly-context` — '/home/n/Code/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`coga retire installer-managed-skills-the-local-adaptation-guar`)
  - Worktree cleanup: '/home/n/Code/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'gh-backed-readonly-context' not present.
  - Branch cleanup: remote origin/gh-backed-readonly-context already gone.
- `persist-autoclose-retire-follow-ups` (worklist backlog): worktree `/home/n/Code/claude/coga-autoclose-retire-worklist`, branch `autoclose-retire-worklist` — branch 'autoclose-retire-worklist' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place. (`coga retire persist-autoclose-retire-follow-ups`)
  - Worktree cleanup: local 'autoclose-retire-worklist' advanced past the merged PR head 5bfd5348ed22 — preserving it.
  - Worktree cleanup: branch 'autoclose-retire-worklist' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place.
  - Branch cleanup: local 'autoclose-retire-worklist' advanced past the merged PR head 5bfd5348ed22 — preserving it.
  - Branch cleanup: local 'autoclose-retire-worklist' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/autoclose-retire-worklist because the local branch remains.
- `record-or-clear-the-standing-repo-wide-coga-valida` (worklist backlog): worktree `/home/n/Code/claude/coga-validate-baseline`, branch `validate-baseline` — branch 'validate-baseline' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place. (`coga retire record-or-clear-the-standing-repo-wide-coga-valida`)
  - Worktree cleanup: local 'validate-baseline' advanced past the merged PR head 2782fc74dcd8 — preserving it.
  - Worktree cleanup: branch 'validate-baseline' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place.
  - Branch cleanup: local 'validate-baseline' advanced past the merged PR head 2782fc74dcd8 — preserving it.
  - Branch cleanup: local 'validate-baseline' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/validate-baseline because the local branch remains.
- `reuse-the-existing-control-worktree-for-recurring` (worklist backlog): worktree `/home/n/Code/codex/coga-recurring-control-worktree`, branch `recurring-control-worktree` — '/home/n/Code/codex/coga-recurring-control-worktree' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`coga retire reuse-the-existing-control-worktree-for-recurring`)
  - Worktree cleanup: '/home/n/Code/codex/coga-recurring-control-worktree' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'recurring-control-worktree' advanced past the merged PR head 22d39a2588f7 — preserving it.
  - Branch cleanup: local 'recurring-control-worktree' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/recurring-control-worktree because the local branch remains.
- `the-period-task-context-never-covers-the-determini` (worklist backlog): worktree `/home/n/Code/claude/coga-period-task-recipe-firing`, branch `period-task-recipe-firing` — branch 'period-task-recipe-firing' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place. (`coga retire the-period-task-context-never-covers-the-determini`)
  - Worktree cleanup: local 'period-task-recipe-firing' advanced past the merged PR head 92d62d5bbaa9 — preserving it.
  - Worktree cleanup: branch 'period-task-recipe-firing' has not landed on 'main' and its current refs do not exactly match the recorded merged PR — left in place.
  - Branch cleanup: local 'period-task-recipe-firing' advanced past the merged PR head 92d62d5bbaa9 — preserving it.
  - Branch cleanup: local 'period-task-recipe-firing' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/period-task-recipe-firing because the local branch remains.
