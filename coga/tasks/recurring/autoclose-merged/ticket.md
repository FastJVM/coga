---
title: Autoclose merged tickets
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 63866837-3fbd-4196-9454-1ed762ad2058
workflow:
  name: autoclose-merged/sweep
  steps:
  - name: sweep
    skills:
    - coga/autoclose/sweep
    assignee: agent
step: 1 (sweep)
launch_generation: 39f44909-a84a-426e-80a5-940aa867e26d
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

Generated: 2026-09-30T16:59:57+00:00
Task: `recurring/autoclose-merged`

4 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `launch-moves-the-checkout-to-main-before-and-after` (worklist backlog): branch `launch-normalizes-checkout`
- `marketing/fix-installer/linux-clean-install-harness` (worklist backlog): branch `linux-clean-install-harness`
- `prevent-parent-ticket-assumptions-during-task-spli` (worklist backlog): branch `no-parent-ticket-guidance`
- `record-the-attended-ticket-switch-recipe-launch-do` (worklist backlog): branch `attended-ticket-switch-recipe`

4 checkout(s) preserved — a proof refused; each stays on the worklist until a human acts:

- `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `quiet-first-run` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand, unless it is another clone's primary checkout in active use: then never remove it; verify the branch is gone in that clone and delete this `retires.md` line by hand (see `dev/checkout-cleanup`))
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'quiet-first-run' not present.
  - Branch cleanup: remote origin/quiet-first-run already gone.
- `document-how-to-recover-a-retired-ticket-s-body-fr` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `retired-ticket-recovery` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand, unless it is another clone's primary checkout in active use: then never remove it; verify the branch is gone in that clone and delete this `retires.md` line by hand (see `dev/checkout-cleanup`))
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'retired-ticket-recovery' not present.
  - Branch cleanup: remote origin/retired-ticket-recovery already gone.
- `make-dream-run-correctly-under-codex` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `dream-under-codex` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand, unless it is another clone's primary checkout in active use: then never remove it; verify the branch is gone in that clone and delete this `retires.md` line by hand (see `dev/checkout-cleanup`))
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'dream-under-codex' not present.
  - Branch cleanup: remote origin/dream-under-codex already gone.
- `run-the-landed-branch-sweep-daily-from-autoclose` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `daily-autoclose-branches` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand, unless it is another clone's primary checkout in active use: then never remove it; verify the branch is gone in that clone and delete this `retires.md` line by hand (see `dev/checkout-cleanup`))
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'daily-autoclose-branches' not present.
  - Branch cleanup: remote origin/daily-autoclose-branches already gone.

## Branch Sweep

Generated: 2026-09-30T17:00:12+00:00
Task: `recurring/autoclose-merged`

Result: partial sweep — Branch sweep: 'codex/retro-independent-clone-worklist-knowledge' could not publish 'retired/codex/retro-independent-clone-worklist-knowledge': To https://github.com/FastJVM/coga/
 ! [rejected]            retired/codex/retro-independent-clone-worklist-knowledge -> retired/codex/retro-independent-clone-worklist-knowledge (already exists)
error: failed to push some refs to 'https://github.com/FastJVM/coga/'
hint: Updates were rejected because the tag already exists in the remote. — left in place.
Counts: 1 local and 0 remote branch(es) deleted, 0 worktree(s) removed, 0 skipped-worktree-pinned, 13 skipped.
- deleted local: ci-posture
- skipped: autoclose-retires-durable-home, codex/retro-independent-clone-worklist-knowledge, dream-w40-testing-baseline, guard-reauthor-in-progress, publish-off-control, recurring-crlf-lease, recurring-ledger-from-log, retire-worklist-linked-only, scrub-sa-token, slack-important-alert, split-ticket-contract, v2-premise-adjudication, wedge-ticket-admin-reproduction

### Decisions

- Branch cleanup: local 'autoclose-retires-durable-home' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'bloated-blackboard-remedy' is recorded on a live ticket — left in place.
- Branch sweep: 'branch-sweep-landed' is recorded on a live ticket — left in place.
- Branch sweep: archived 'ci-posture' at 1c1e5255d0b542d07b58904bd4bd68663d252cc9 as 'retired/ci-posture' on origin.
- Branch cleanup: force-deleted local 'ci-posture' (was 1c1e5255d0b542d07b58904bd4bd68663d252cc9) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'codex/retro-independent-clone-worklist-knowledge' could not publish 'retired/codex/retro-independent-clone-worklist-knowledge': To https://github.com/FastJVM/coga/
 ! [rejected]            retired/codex/retro-independent-clone-worklist-knowledge -> retired/codex/retro-independent-clone-worklist-knowledge (already exists)
error: failed to push some refs to 'https://github.com/FastJVM/coga/'
hint: Updates were rejected because the tag already exists in the remote. — left in place.
- Branch sweep: 'codex/retro-recurring-branch-sweep-knowledge' is recorded on a live ticket — left in place.
- Branch sweep: 'coga/skill-update' is the shared skill-update branch — left in place.
- Branch sweep: 'doc-context-boundary' is recorded on a live ticket — left in place.
- Branch sweep: 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place.
- Branch sweep: 'docs/w40-workflow-corrections' is recorded on a live ticket — left in place.
- Branch sweep: 'dream-w38-extract-backlog' is recorded on a live ticket — left in place.
- Branch sweep: 'dream-w40-doc-corrections' is recorded on a live ticket — left in place.
- Branch sweep: 'dream-w40-notification-skill-docs' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/dream-w40-testing-baseline (no merged PR).
- Branch sweep: 'fix-autoclose-clone-primary' is recorded on a live ticket — left in place.
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch sweep: 'recurring-missing-workflow' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch cleanup: local 'scrub-sa-token' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'shebang-exec-check' is recorded on a live ticket — left in place.
- Branch sweep: 'skill-update-per-skill' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch cleanup: local 'split-ticket-contract' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'sweep-abandoned-record' is recorded on a live ticket — left in place.
- Branch sweep: 'title-only-validator' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/v2-premise-adjudication (no merged PR).
- Branch sweep: 'v2-premise-holes' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).

## Recipe Failure

Recipe: `branch-sweep`
Exit: 2
Task: `recurring/autoclose-merged`
Recorded: 2026-09-30T17:00:12+00:00

    [branch-sweep] Branch sweep: 'codex/retro-independent-clone-worklist-knowledge' could not publish 'retired/codex/retro-independent-clone-worklist-knowledge': To https://github.com/FastJVM/coga/
     ! [rejected]            retired/codex/retro-independent-clone-worklist-knowledge -> retired/codex/retro-independent-clone-worklist-knowledge (already exists)
    error: failed to push some refs to 'https://github.com/FastJVM/coga/'
    hint: Updates were rejected because the tag already exists in the remote. — left in place.
