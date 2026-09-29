---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: c9921314-1db7-478f-a95b-544da0169f72
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

Generated: 2026-09-29T16:05:32+00:00
Task: `recurring/autoclose-merged`

9 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `apply-12-context-and-skill-corrections-blocked-by` "Apply 12 context and skill corrections blocked by open PRs (codebase, sync, current-direction, open-pr)": branch `fix-stale-testing-skill-docs`
- `autofix/keep-cross-clone-retire-follow-ups-from-being-disc` "Keep cross-clone retire follow-ups from being discharged silently": branch `retire-worklist-owner`
- `autofix/make-dream-block-instead-of-done-when-its-retro-ch` "Make Dream block instead of done when its Retro checkout can't land": branch `dream-block-on-stranded-retro`
- `coga-build-fails-after-init-on-a-github-scaffolded` "coga build fails after init on a GitHub-scaffolded repo": branch `init-hosting-scaffold-empty`
- `four-docs-cite-positioning-context-sections-that-w` "Four docs cite positioning-context sections that were never committed": branch `fix-positioning-owner-links`
- `keep-agent-edits-to-contexts-and-skills-off-the-co` "Keep agent edits to contexts and skills off the control branch without a merge": branch `fix-authoring-publication`
- `record-four-repeated-dev-loop-verification-gotchas` "Record four repeated dev-loop verification gotchas in the coga codebase context": branch `record-dev-loop-verification-gotchas`
- `settle-whether-megalaunch-is-the-only-unclassified` "Settle whether megalaunch is the only unclassified verb: extension-model vs the CLI extension audit": branch `docs/command-classification`
- `stop-recurring-on-inactive-repo` "stop recurring on inactive repo": branch `stop-recurring-inactive`

9 checkout(s) preserved — a proof refused; each stays on the worklist until a human acts:

- `add-an-agent-picker-for-recurring` (worklist backlog): worktree `/home/n/Code/coga`, branch `authoring-agent-picker` — '/home/n/Code/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand)
  - Worktree cleanup: '/home/n/Code/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'authoring-agent-picker' not present.
  - Branch cleanup: remote origin/authoring-agent-picker already gone.
- `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `quiet-first-run` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand)
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'quiet-first-run' not present.
  - Branch cleanup: remote origin/quiet-first-run already gone.
- `document-how-to-recover-a-retired-ticket-s-body-fr` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `retired-ticket-recovery` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand)
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'retired-ticket-recovery' not present.
  - Branch cleanup: remote origin/retired-ticket-recovery already gone.
- `document-the-remedy-for-a-bloated-blackboard-sibli` (worklist backlog): worktree `/home/n/Code/claude/coga-bloated-blackboard-remedy`, branch `bloated-blackboard-remedy` — local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place. (the worktree is already gone; then `coga retire document-the-remedy-for-a-bloated-blackboard-sibli` for branch `bloated-blackboard-remedy`)
  - Worktree cleanup: recorded worktree '/home/n/Code/claude/coga-bloated-blackboard-remedy' is already gone.
  - Branch cleanup: local 'bloated-blackboard-remedy' advanced past the merged PR head 449bf55590e8 — preserving it.
  - Branch cleanup: local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/bloated-blackboard-remedy because the local branch remains.
- `installer-managed-skills-the-local-adaptation-guar` (worklist backlog): worktree `/home/n/Code/coga`, branch `gh-backed-readonly-context` — '/home/n/Code/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand)
  - Worktree cleanup: '/home/n/Code/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'gh-backed-readonly-context' not present.
  - Branch cleanup: remote origin/gh-backed-readonly-context already gone.
- `make-dream-run-correctly-under-codex` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `dream-under-codex` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand)
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'dream-under-codex' not present.
  - Branch cleanup: remote origin/dream-under-codex already gone.
- `record-or-clear-the-standing-repo-wide-coga-valida` (worklist backlog): worktree `/home/n/Code/claude/coga-validate-baseline`, branch `validate-baseline` — local 'validate-baseline' has unmerged work and no merged PR vouching for it — left in place. (the worktree is already gone; then `coga retire record-or-clear-the-standing-repo-wide-coga-valida` for branch `validate-baseline`)
  - Worktree cleanup: recorded worktree '/home/n/Code/claude/coga-validate-baseline' is already gone.
  - Branch cleanup: local 'validate-baseline' advanced past the merged PR head 2782fc74dcd8 — preserving it.
  - Branch cleanup: local 'validate-baseline' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/validate-baseline because the local branch remains.
- `reuse-the-existing-control-worktree-for-recurring` (worklist backlog): worktree `/home/n/Code/codex/coga-recurring-control-worktree`, branch `recurring-control-worktree` — local 'recurring-control-worktree' has unmerged work and no merged PR vouching for it — left in place. (the worktree is already gone; then `coga retire reuse-the-existing-control-worktree-for-recurring` for branch `recurring-control-worktree`)
  - Worktree cleanup: recorded worktree '/home/n/Code/codex/coga-recurring-control-worktree' is already gone.
  - Branch cleanup: local 'recurring-control-worktree' advanced past the merged PR head 22d39a2588f7 — preserving it.
  - Branch cleanup: local 'recurring-control-worktree' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/recurring-control-worktree because the local branch remains.
- `run-the-landed-branch-sweep-daily-from-autoclose` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `daily-autoclose-branches` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand)
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'daily-autoclose-branches' not present.
  - Branch cleanup: remote origin/daily-autoclose-branches already gone.

## Branch Sweep

Generated: 2026-09-29T16:05:57+00:00
Task: `recurring/autoclose-merged`

Result: 1 local and 0 remote branch(es) deleted, 0 worktree(s) removed, 0 skipped-worktree-pinned, 21 skipped.
- deleted local: validate-baseline
- skipped: autoclose-retires-durable-home, bloated-blackboard-remedy, branch-sweep-landed, codex/retro-recurring-branch-sweep-knowledge, doc-context-boundary, dream-w38-extract-backlog, guard-reauthor-in-progress, publish-off-control, recurring-crlf-lease, recurring-ledger-from-log, recurring-missing-workflow, retire-worklist-linked-only, scrub-sa-token, shebang-exec-check, skill-update-per-skill, slack-important-alert, split-ticket-contract, sweep-abandoned-record, title-only-validator, v2-premise-holes, wedge-ticket-admin-reproduction

### Decisions

- Branch sweep: 'attended-ticket-switch-recipe' is recorded on a live ticket — left in place.
- Branch cleanup: local 'autoclose-retires-durable-home' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'bloated-blackboard-remedy' has merged PR #856 at 449bf55590e8, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/blackboard/SKILL.md, src/coga/dream_validate_drift.py (+3 more) — left in place.
- Branch cleanup: local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'branch-sweep-landed' has merged PR #811 at ccc5e0a3ae97, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, coga/contexts/dev/code/SKILL.md, coga/recurring/branch-sweep/ticket.md (+11 more) — left in place.
- Branch cleanup: local 'branch-sweep-landed' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'ci-posture' is recorded on a live ticket — left in place.
- Branch sweep: 'codex/retro-recurring-branch-sweep-knowledge' has merged PR #859 at 9b9e80d36a05, but the ref carries commits touching coga/skills/coga/branch-sweep/sweep/SKILL.md, src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md — left in place.
- Branch cleanup: local 'codex/retro-recurring-branch-sweep-knowledge' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'coga/skill-update' is recorded on a live ticket — left in place.
- Branch sweep: 'doc-context-boundary' has merged PR #790 at a9fce62cea59, but the ref carries commits touching AGENTS.md, CLAUDE.md, coga/contexts/_template/SKILL.md (+8 more) — left in place.
- Branch cleanup: local 'doc-context-boundary' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'doc-tmp-checkouts-ephemeral' is recorded on a live ticket — left in place.
- Branch sweep: 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place.
- Branch sweep: 'dream-w38-extract-backlog' has merged PR #812 at 35b9b60909bf, but the ref carries commits touching AGENTS.md, CLAUDE.md, coga/contexts/coga/codebase/SKILL.md (+5 more) — left in place.
- Branch cleanup: local 'dream-w38-extract-backlog' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'fix-recurring-git-hygiene' is recorded on a live ticket — left in place.
- Branch sweep: 'fix/claude-synthetic-model' is recorded on a live ticket — left in place.
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'launch-normalizes-checkout' is recorded on a live ticket — left in place.
- Branch sweep: 'linux-clean-install-harness' is recorded on a live ticket — left in place.
- Branch sweep: 'no-parent-ticket-guidance' is recorded on a live ticket — left in place.
- Branch sweep: 'preserve-no-action-decisions' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch sweep: 'recurring-missing-workflow' has merged PR #814 at 4d1bafcb78b5, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, src/coga/recurring.py, src/coga/recurring_runner.py (+2 more) — left in place.
- Branch cleanup: local 'recurring-missing-workflow' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch cleanup: local 'scrub-sa-token' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'shebang-exec-check' has merged PR #800 at a02e2930511f, but the ref carries commits touching coga/skills/anthropic/skill-creator/eval-viewer/generate_review.py, coga/skills/clarity/scripts/validate_package.py, src/coga/dream_validate_drift.py (+6 more) — left in place.
- Branch cleanup: local 'shebang-exec-check' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'skill-update-per-skill' has merged PR #796 at e925ff14626c, but the ref carries commits touching coga/contexts/coga/codebase/SKILL.md, coga/recurring/skill-update/ticket.md, coga/skills/code/self-qa/SKILL.md (+11 more) — left in place.
- Branch cleanup: local 'skill-update-per-skill' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch sweep: 'slack-oserror-delivery-miss' is recorded on a live ticket — left in place.
- Branch cleanup: local 'split-ticket-contract' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'sweep-abandoned-record' has merged PR #813 at d321c6a45a27, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, src/coga/recurring_runner.py, src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md (+1 more) — left in place.
- Branch cleanup: local 'sweep-abandoned-record' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'title-only-validator' has merged PR #815 at 64101866c918, but the ref carries commits touching coga/contexts/coga/roadmap/SKILL.md, src/coga/commands/create.py, src/coga/dream_validate_drift.py (+4 more) — left in place.
- Branch cleanup: local 'title-only-validator' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'v2-premise-adjudication' is recorded on a live ticket — left in place.
- Branch sweep: 'v2-premise-holes' has merged PR #819 at 49cfcb941ee6, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/roadmap/SKILL.md, coga/recurring/dream/ticket.md (+5 more) — left in place.
- Branch cleanup: local 'v2-premise-holes' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: force-deleted local 'validate-baseline' (was 01ff2ce801eab97fc290942f9acd93bbf064252d) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: New context: another clone's primary checkout never leaves the autoclose worklist
