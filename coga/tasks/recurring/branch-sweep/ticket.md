---
title: Branch sweep
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 3dce4963-67ee-4982-9e36-cbfad8f1899c
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
---

## Description

Delete local and remote git branches whose work has already landed, as the
safety net behind `coga retire`'s branch deletion.

`coga retire` disposes of a finished ticket's branch when it runs from the
control branch, and exits 2 rather than delete the ticket when the proofs
keep it. But it skips that cleanup off the control branch or after a Git
error, and a branch also leaks when a ticket is deleted without going
through retire, or a session dies mid-flight. Branches are clone-local: a sweep run from one
clone never sees another clone's refs. So this template is `scope: clone` —
every clone that runs `coga recurring` services it once a day for itself.
Scope and cadence are owned by
[coga/recurring/scheduling](context:coga/recurring/scheduling).

Once a day, in each clone, this template's `ticket.py` runs the branch sweep,
which:

1. prunes registrations for worktrees whose directories are gone, then
   enumerates the branches held by the remaining live worktrees,
2. enumerates every local branch and every branch on the configured git remote,
3. skips the configured control branch, the checked-out branch, the shared
   skill-update branch, and any
   branch a non-terminal ticket names anywhere in its task files — the
   ticket body, its blackboard, or an attachment — not only under a `## Dev`
   `branch:` line; a mere mention pins, because a false positive only defers
   a delete until the next pass. A recurring period task pins only its `## Dev`
   `branch:`, since its blackboard is generated reports naming branches,
4. for the rest, authorizes deletion two independent ways — the local tip
   being reachable from the control branch, a merge-commit or fast-forward
   landing that needs no PR at all, or a merged PR for that head branch name
   with no PR currently open for it, where the merged PR vouches for the
   local ref only if every commit on the ref that neither the merged head nor
   the control branch (local or remote-tracking) contains touches only Coga
   task/log state. That admits
   the exact merged tip, a ref that lags the merged head because the last
   commit was pushed from another checkout (the merged head is fetched from
   `refs/pull/<n>/head` when it is not local), and a ref that walked past the
   merged head through Coga's own state-sync commits; a ref carrying real
   unmerged source commits stays, with the offending paths named. The remote
   ref takes only a merged PR at its exact tip,
5. for a branch whose local tip landed either way but is still held by a live worktree,
   preserves both refs and reports the distinct, non-fatal
   `skipped-worktree-pinned` outcome — unless `[git].worktrees_ticket_owned`
   is `true`, the repo's declaration that every linked worktree of its git
   repository belongs to a Coga ticket. With no open PR, a landed worktree linked
   to the clone this sweep runs from, checked out on that branch, locally
   pristine (no tracked or untracked files; ignored regenerable caches are
   fine), and recorded by no non-terminal ticket qualifies for removal in
   step 6; a worktree that
   fails any of those proofs stays `skipped-worktree-pinned` with the reason,
6. publishes the retirement tag before removing the worktree or deleting
   either ref, under the archive gate in
   [dev/checkout-cleanup/branch-sweep](context:dev/checkout-cleanup/branch-sweep). Failed archival
   preserves the refs and worktree and records a failing sweep outcome.
   Then it removes the eligible worktree, reported under `removed worktree`,
   and deletes the local branch and/or remote ref under the local-before-remote
   deletion rules in
   [dev/checkout-cleanup/proofs](context:dev/checkout-cleanup/proofs) that
   `coga retire` also follows, skipping and reporting anything unmerged with no
   merged PR,
7. from the control branch, disposes of the `retires.md` entries that record
   this clone as `owner` under the
   [checkout proofs](context:dev/checkout-cleanup/proofs) autoclose runs, and
   publishes just that worklist when it discharged or refreshed one — the
   only commit this clone-scoped run makes, and
8. prints a `## Branch Sweep` report — the outcome lists and every
   per-branch decision. A clone-scoped run has no period blackboard, so the
   report is kept in the clone's `.coga/recurring-clone/branch-sweep.log` and
   in the sweep's run record for the autofix analyst.

The sweep is defined in `coga.branchsweep.sweep_branches`. The worktree
removal is a direct destructive change gated on a repo-level opt-in; the
`dev/checkout-cleanup/branch-sweep` context states the assumption the key asserts, and the
`coga/branch-sweep/sweep` skill names the proofs. Its first run
also prunes the merged part of the branch backlog that accumulated before
retire-time deletion shipped — abandoned no-PR branches are skipped and
reported by design, so expect a residual manual pass rather than a fully
clean slate. A failure to prune or list worktree state fails the sweep before
any branch deletion.

The sweep runs on this schedule via `coga recurring` in each clone, on
demand via `coga recurring launch branch-sweep`, or directly with
`coga run branch-sweep`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Branch Sweep

Generated: 2026-10-19T17:46:55+00:00
Task: `recurring/branch-sweep`

Result: 4 local and 11 remote branch(es) deleted, 0 worktree(s) removed, 0 skipped-worktree-pinned, 20 skipped.
- deleted local: docs/fold-foreign-ownership, drop-root-claude-md, pr1034, revert-leaked-clone-scope-recurring
- deleted remote: codex/audit-bounded-clone-scripts, codex/audit-launch-api, codex/audit-launch-phases, codex/audit-unique-prompt-files, codex/audit-workflow-errors, docs/archive-reading-opt-in, docs/consolidate-design-history, docs/self-document-ticket-fields, drop-root-claude-md, revert-leaked-clone-scope-recurring, v1-microkernel-cleanup-and-hackability-demo
- skipped: archive-stale-docs, autoclose-retires-durable-home, bloated-blackboard-remedy, codex/retro-recurring-branch-sweep-knowledge, dream-w40-testing-baseline, fence-aware-section-splitter, fix/codex-peer-review-in-sandbox, guard-reauthor-in-progress, nicktoper-patch-1, publish-off-control, recurring-crlf-lease, recurring-ledger-from-log, retire-worklist-linked-only, scrub-sa-token, shebang-exec-check, slack-important-alert, split-ticket-contract, terminal-branch-cleanup, warn-on-bootstrap-unpublished-edits, wedge-ticket-admin-reproduction

### Decisions

- Branch sweep: terminal ticket 'define-the-split-a-ticket-mechanic-shared-by-code' records checkout '/home/n/Code/coga' outside this repository or unavailable — its branch records grant no cleanup authority here.
- Branch sweep: terminal ticket 'document-the-remedy-for-a-bloated-blackboard-sibli' records checkout '/home/n/Code/claude/coga-bloated-blackboard-remedy' outside this repository or unavailable — its branch records grant no cleanup authority here.
- Branch sweep: terminal ticket 'scrub-the-service-account-token-from-the-launch-ch' records checkout '/home/n/Code/claude/coga-scrub-sa-token' outside this repository or unavailable — its branch records grant no cleanup authority here.
- Branch sweep: terminal ticket 'validate-that-committed-skill-scripts-with-a-sheba' records checkout '/home/n/Code/claude/coga-shebang-exec-check' outside this repository or unavailable — its branch records grant no cleanup authority here.
- Branch sweep: 'archive-stale-docs' has merged PR #1004 at 691d88740f13, but the ref carries commits touching coga/skills/marketing/write-post/SKILL.md, docs/README.md, docs/archive/cli-extension-audit.md (+70 more) — left in place.
- Branch cleanup: local 'archive-stale-docs' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'autoclose-retires-durable-home' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'bloated-blackboard-remedy' has merged PR #856 at 449bf55590e8, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/blackboard/SKILL.md, src/coga/dream_validate_drift.py (+3 more) — left in place.
- Branch cleanup: local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'clone-discharge-retires' is recorded on a live ticket — left in place.
- Branch sweep: 'codex-sigint-interrupted' is recorded on a live ticket — left in place.
- Branch sweep: archived 'codex/audit-bounded-clone-scripts' at 63417441a785fdd502ddc5e1c0449681e811ed8f as 'retired/codex/audit-bounded-clone-scripts' on origin.
- Branch cleanup: deleted remote origin/codex/audit-bounded-clone-scripts.
- Branch sweep: archived 'codex/audit-launch-api' at f6140b51d2dadd25f9157bdd0231ab5767e5654a as 'retired/codex/audit-launch-api' on origin.
- Branch cleanup: deleted remote origin/codex/audit-launch-api.
- Branch sweep: archived 'codex/audit-launch-phases' at 06df6cf1867269271101a28cf912b4fcda3445f9 as 'retired/codex/audit-launch-phases' on origin.
- Branch cleanup: deleted remote origin/codex/audit-launch-phases.
- Branch sweep: archived 'codex/audit-unique-prompt-files' at aaafe7fec943251fefff497698d7ac5ed63ce5e4 as 'retired/codex/audit-unique-prompt-files' on origin.
- Branch cleanup: deleted remote origin/codex/audit-unique-prompt-files.
- Branch sweep: archived 'codex/audit-workflow-errors' at fcccd9daf22b54e6792f2697cbe189becb08380d as 'retired/codex/audit-workflow-errors' on origin.
- Branch cleanup: deleted remote origin/codex/audit-workflow-errors.
- Branch sweep: 'codex/retro-recurring-branch-sweep-knowledge' has merged PR #859 at 9b9e80d36a05, but the ref carries commits touching coga/skills/coga/branch-sweep/sweep/SKILL.md, src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md — left in place.
- Branch cleanup: local 'codex/retro-recurring-branch-sweep-knowledge' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'coga/skill-update' is the shared skill-update branch — left in place.
- Branch sweep: archived 'docs/archive-reading-opt-in' at 89a8a391f6dc54ff22da8655d4eeeb300458709b as 'retired/docs/archive-reading-opt-in' on origin.
- Branch cleanup: deleted remote origin/docs/archive-reading-opt-in.
- Branch sweep: archived 'docs/consolidate-design-history' at 7f2b7cde4f1d0825e812d801927449c07fc0034a as 'retired/docs/consolidate-design-history' on origin.
- Branch cleanup: deleted remote origin/docs/consolidate-design-history.
- Branch sweep: archived 'docs/fold-foreign-ownership' at dd1d959368f065bd44fa928e3ab7b86c5dec26c5 as 'retired/docs/fold-foreign-ownership' on origin.
- Branch cleanup: deleted local 'docs/fold-foreign-ownership'.
- Branch sweep: archived 'docs/self-document-ticket-fields' at 574602db2cbc15e4b36189612543fa85796f2f01 as 'retired/docs/self-document-ticket-fields' on origin.
- Branch cleanup: deleted remote origin/docs/self-document-ticket-fields.
- Branch sweep: 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/dream-w40-testing-baseline (no merged PR).
- Branch sweep: archived 'drop-root-claude-md' at 658b36c6971a6250fa056f947cff9d66f6247221 as 'retired/drop-root-claude-md' on origin.
- Branch cleanup: deleted local 'drop-root-claude-md'.
- Branch cleanup: deleted remote origin/drop-root-claude-md.
- Branch cleanup: skipping remote origin/fence-aware-section-splitter (no merged PR).
- Branch cleanup: skipping remote origin/fix/codex-peer-review-in-sandbox (no merged PR).
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'install-walk-findings' is recorded on a live ticket — left in place.
- Branch sweep: 'marketing/readme-top' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/nicktoper-patch-1 (no merged PR).
- Branch sweep: 'owned-mac-clean-install' is recorded on a live ticket — left in place.
- Branch sweep: archived 'pr1034' at b6dacc0043c2445de264618d20f05102f6889c03 as 'retired/pr1034' on origin.
- Branch cleanup: deleted local 'pr1034'.
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch sweep: 'retire-command-ticket' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch sweep: archived 'revert-leaked-clone-scope-recurring' at 28cba8f70bc254e6566abd0d4aa7bd2ff1fbf105 as 'retired/revert-leaked-clone-scope-recurring' on origin.
- Branch cleanup: deleted local 'revert-leaked-clone-scope-recurring'.
- Branch cleanup: deleted remote origin/revert-leaked-clone-scope-recurring.
- Branch cleanup: local 'scrub-sa-token' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'self-qa-stale-ticket-and-state-side-effects' is recorded on a live ticket — left in place.
- Branch sweep: 'shebang-exec-check' has merged PR #800 at a02e2930511f, but the ref carries commits touching coga/skills/anthropic/skill-creator/eval-viewer/generate_review.py, coga/skills/clarity/scripts/validate_package.py, src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/gmail.py (+1 more) — left in place.
- Branch cleanup: local 'shebang-exec-check' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch cleanup: local 'split-ticket-contract' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/terminal-branch-cleanup (no merged PR).
- Branch sweep: archived 'v1-microkernel-cleanup-and-hackability-demo' at faa395462a120d91c8d102bbfcf7b5070d222a65 as 'retired/v1-microkernel-cleanup-and-hackability-demo' on origin.
- Branch cleanup: deleted remote origin/v1-microkernel-cleanup-and-hackability-demo.
- Branch cleanup: skipping remote origin/warn-on-bootstrap-unpublished-edits (no merged PR).
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).
- Branch sweep: 'windows-ec2-harness' is recorded on a live ticket — left in place.
