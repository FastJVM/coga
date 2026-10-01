---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 48c316e9-ef10-4d6f-abf6-1d07e705c99b
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

Generated: 2026-10-01T17:48:19+00:00
Task: `recurring/autoclose-merged`

6 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `apply-three-dream-w40-notification-and-skill-manag` "Apply three Dream W40 notification and skill-management corrections after PR 914 lands": branch `dream-w40-notification-skill-docs`
- `apply-three-dream-w40-skill-and-context-correction` "Apply three Dream W40 skill and context corrections after PR 909 lands": branch `dream-w40-doc-corrections`
- `apply-three-dream-w40-workflow-and-v2-readme-corre` "Apply three Dream W40 workflow and v2 README corrections after PR 912 lands": branch `docs/w40-workflow-corrections`
- `autofix/make-branch-sweep-retirement-survive-an-existing-r` "Make branch-sweep retirement survive an existing remote retired/ tag": branch `branch-sweep-retired-tag-collision`
- `branch-sweep-never-clears-rebased-copy-branches` "Branch-sweep never clears rebased-copy branches": branch `branch-sweep-cherry-pick`
- `record-that-contexts-linking-tickets-by-path-break` "Record that contexts linking tickets by path break at retirement after PR 918 lands": branch `knowledge-ticket-links-at-retirement`

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

Generated: 2026-10-01T17:49:17+00:00
Task: `recurring/autoclose-merged`

Result: 9 local and 2 remote branch(es) deleted, 0 worktree(s) removed, 0 skipped-worktree-pinned, 16 skipped.
- deleted local: branch-sweep-landed, codex/retro-independent-clone-worklist-knowledge, doc-context-boundary, dream-w38-extract-backlog, recurring-missing-workflow, skill-update-per-skill, sweep-abandoned-record, title-only-validator, v2-premise-holes
- deleted remote: doc-context-boundary, skill-update-per-skill
- skipped: autoclose-retires-durable-home, bloated-blackboard-remedy, codex/retro-recurring-branch-sweep-knowledge, dream-w40-testing-baseline, guard-reauthor-in-progress, init-offers-dependency-installs, publish-off-control, recurring-crlf-lease, recurring-ledger-from-log, retire-worklist-linked-only, scrub-sa-token, shebang-exec-check, slack-important-alert, split-ticket-contract, v2-premise-adjudication, wedge-ticket-admin-reproduction

### Decisions

- Branch cleanup: local 'autoclose-retires-durable-home' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'bloated-blackboard-remedy' has merged PR #856 at 449bf55590e8, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/blackboard/SKILL.md, src/coga/dream_validate_drift.py (+3 more) — left in place.
- Branch cleanup: local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: archived 'branch-sweep-landed' at ccbd35ee31eac7a88636794303e9631e9e6daff7 as 'retired/branch-sweep-landed' on origin.
- Branch cleanup: force-deleted local 'branch-sweep-landed' (was ccbd35ee31eac7a88636794303e9631e9e6daff7) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'codex/retro-independent-clone-worklist-knowledge' at 2d1ee292a16f76376c7e6b555664d8c060f9f4a2 is already archived by 'retired/codex/retro-independent-clone-worklist-knowledge' on origin.
- Branch cleanup: force-deleted local 'codex/retro-independent-clone-worklist-knowledge' (was 2d1ee292a16f76376c7e6b555664d8c060f9f4a2) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'codex/retro-recurring-branch-sweep-knowledge' has merged PR #859 at 9b9e80d36a05, but the ref carries commits touching coga/skills/coga/branch-sweep/sweep/SKILL.md, src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md — left in place.
- Branch cleanup: local 'codex/retro-recurring-branch-sweep-knowledge' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'coga/skill-update' is the shared skill-update branch — left in place.
- Branch sweep: 'doc-context-boundary' tips diverge; a9fce62cea59 at refs/pull/790/head stays on origin as the merged PR head.
- Branch sweep: archived 'doc-context-boundary' at e90557b95f90371f412c364e1e844c6d849f3180 as 'retired/doc-context-boundary' on origin.
- Branch cleanup: force-deleted local 'doc-context-boundary' (was e90557b95f90371f412c364e1e844c6d849f3180) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/doc-context-boundary.
- Branch sweep: 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place.
- Branch sweep: archived 'dream-w38-extract-backlog' at 1d23cb4cc2e214cb54252d9c220a4db459207e78 as 'retired/dream-w38-extract-backlog' on origin.
- Branch cleanup: force-deleted local 'dream-w38-extract-backlog' (was 1d23cb4cc2e214cb54252d9c220a4db459207e78) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/dream-w40-testing-baseline (no merged PR).
- Branch sweep: 'edge-wheel-upgrades' is recorded on a live ticket — left in place.
- Branch sweep: 'fix-autoclose-clone-primary' is recorded on a live ticket — left in place.
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/init-offers-dependency-installs (no merged PR).
- Branch sweep: 'macos-clean-install-harness' is recorded on a live ticket — left in place.
- Branch sweep: 'phone-home-record-failure-caller' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch sweep: archived 'recurring-missing-workflow' at e62d818f2be5e4a81da8a11f15bfbb81d7804976 as 'retired/recurring-missing-workflow' on origin.
- Branch cleanup: force-deleted local 'recurring-missing-workflow' (was e62d818f2be5e4a81da8a11f15bfbb81d7804976) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch cleanup: local 'scrub-sa-token' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'shebang-exec-check' has merged PR #800 at a02e2930511f, but the ref carries commits touching coga/skills/anthropic/skill-creator/eval-viewer/generate_review.py, coga/skills/clarity/scripts/validate_package.py, src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/gmail.py (+1 more) — left in place.
- Branch cleanup: local 'shebang-exec-check' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'skill-update-per-skill' tips diverge; e925ff14626c at refs/pull/796/head stays on origin as the merged PR head.
- Branch sweep: archived 'skill-update-per-skill' at b8bfb8bf4fd02b602aeaec6da21c53be02723499 as 'retired/skill-update-per-skill' on origin.
- Branch cleanup: force-deleted local 'skill-update-per-skill' (was b8bfb8bf4fd02b602aeaec6da21c53be02723499) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/skill-update-per-skill.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch cleanup: local 'split-ticket-contract' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: archived 'sweep-abandoned-record' at bb2d017f0e5a04d91cfd25a580a0b5a5b03dc1ef as 'retired/sweep-abandoned-record' on origin.
- Branch cleanup: force-deleted local 'sweep-abandoned-record' (was bb2d017f0e5a04d91cfd25a580a0b5a5b03dc1ef) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: archived 'title-only-validator' at d1a27208d932c5a2686d29c557e423e9229d143b as 'retired/title-only-validator' on origin.
- Branch cleanup: force-deleted local 'title-only-validator' (was d1a27208d932c5a2686d29c557e423e9229d143b) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'uninstall-uv-tool' is recorded on a live ticket — left in place.
- Branch sweep: 'usage-report-flow' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/v2-premise-adjudication (no merged PR).
- Branch sweep: archived 'v2-premise-holes' at 59f3fb56374d32ae9960ed841a5013e880526e96 as 'retired/v2-premise-holes' on origin.
- Branch cleanup: force-deleted local 'v2-premise-holes' (was 59f3fb56374d32ae9960ed841a5013e880526e96) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).
