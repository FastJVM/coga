---
title: Branch sweep
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 129e4615-d3c2-4ecb-8d55-2245ba94e752
workflow:
  name: branch-sweep/sweep
  steps:
  - name: sweep
    skills:
    - coga/branch-sweep/sweep
    assignee: agent
---

## Description

Delete local and remote git branches whose work has already landed, as the
safety net behind `coga retire`'s branch deletion.

`coga retire` deletes a finished ticket's branch immediately, but that
cleanup is best-effort — `git`/`gh` failures are swallowed there, and a
branch also leaks when a ticket is deleted without going through retire, or
a session dies mid-flight. Retire covers the common path daily (in effect,
every time a ticket finishes); this sweep runs weekly to catch what leaks
past it.

Once a week this recurring task's `ticket.py` runs the branch sweep,
which:

1. prunes registrations for worktrees whose directories are gone, then
   enumerates the branches held by the remaining live worktrees,
2. enumerates every local branch and every branch on the configured git remote,
3. skips the configured control branch, the checked-out branch, and any
   branch a non-terminal ticket names anywhere in its task files — the
   ticket body, its blackboard, or an attachment — not only under a `## Dev`
   `branch:` line; a mere mention pins, because a false positive only defers
   a delete by a week. A recurring period task pins only its `## Dev`
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
5. preserves both refs for a branch that landed either way but is still held
   by a live worktree and reports the distinct, non-fatal
   `skipped-worktree-pinned` outcome,
6. deletes the remote ref and/or local branch per the same policy
   `coga retire` uses (plain `git branch -d` when the tip is reachable from
   the control branch; log the tip SHA and force with `-D` for the
   squash-merge case a merged PR vouches for; skip and report anything
   unmerged with no merged PR), and
7. writes a `## Branch Sweep` report — the outcome lists and every
   per-branch decision — to this period task's blackboard, so the run has a
   durable record for the recurring sweep's autofix analyst; run outside a
   task, the report goes to stdout instead.

The sweep is defined in `coga.branchsweep.sweep_branches`. Its first run
also prunes the merged part of the branch backlog that accumulated before
retire-time deletion shipped — abandoned no-PR branches are skipped and
reported by design, so expect a residual manual pass rather than a fully
clean slate. A failure to prune or list worktree state fails the sweep before
any branch deletion.

The sweep runs on this schedule via `coga recurring`, on demand via
`coga recurring launch branch-sweep`, or directly with
`coga run branch-sweep`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Branch Sweep

Generated: 2026-09-21T17:01:34+00:00
Task: `recurring/branch-sweep`

Result: 14 local and 12 remote branch(es) deleted, 27 skipped-worktree-pinned, 14 skipped.
- deleted local: cite-symbols-rule, dream/architecture-1788913097, dream/bootstrapskills-1788913097, dream/codebase-1788913097, dream/devcode-1788913097, dream/dreamscan-1788913097, dream/launch-internals-1788913097, dream/positioning-1788913097, dream/recurring-1788913097, dream/skillupdate-1788913097, dream/sync-1788913097, dream/templates-1788913097, fix/watchdog-pauses, sweep-republishes-stranded-claim-release
- deleted remote: cite-symbols-rule, codex/retro-filter-coga-s-own-log-sync-commits-out-of-the-dige-knowledge, codex/retro-verify-the-pr-review-comment-loop-once-the-review-knowledge, dream-w38/cli-context-derived-operator, dream-w38/codebase-context-skill-installer, dream-w38/docs-with-review-skills, dream-w38/orient-agent-guide, dream-w38/recurring-templates, dream-w38/small-contract-drifts, dream-w38/sync-context, sweep-republishes-stranded-claim-release, ticket-recurring-scan-workflow-error
- skipped-worktree-pinned: adjudicate-moved-premises, attach-vs-cite, autoclose-retire-worklist, autofix-analyst-fixes, blackboard-writer-contract, ci-posture, doc-context-boundary, dochub-api-answer, dream-routing-holes, dream-w36-extract-backlog, feature-branch-state-boundary, fresh-checkout-lacks, init-bare-slack-env, init-clone-setup, period-task-recipe-firing, recipe-reporting-contract, recurring-twin-note, remove-build-project, remove-digest, resolve-step-one-assignee, scan-alert-nonfatal, shebang-exec-check, skill-update-per-skill, sync-canonical-policy, sync-context-preflight, triage-inverted-premises, validate-baseline
- skipped: autoclose-retires-durable-home, branch-sweep-landed, dream-w38-extract-backlog, guard-reauthor-in-progress, publish-off-control, recurring-all-child-sweep, recurring-crlf-lease, recurring-ledger-from-log, recurring-missing-workflow, retire-worklist-linked-only, slack-important-alert, sweep-abandoned-record, title-only-validator, v2-premise-holes

### Decisions

- Branch sweep: 'address-pr-comments-sweep' is recorded on a live ticket — left in place.
- Branch sweep: 'adjudicate-moved-premises' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-adjudicate-moved-premises' — left in place.
- Branch sweep: 'attach-vs-cite' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-attach-vs-cite' — left in place.
- Branch sweep: 'autoclose-retire-worklist' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-autoclose-retire-worklist' — left in place.
- Branch cleanup: local 'autoclose-retires-durable-home' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'autoclose-unanswered-threads' is recorded on a live ticket — left in place.
- Branch sweep: 'autofix-analyst-fixes' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-autofix-analyst-fixes' — left in place.
- Branch sweep: 'blackboard-writer-contract' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-blackboard-writer-contract' — left in place.
- Branch sweep: 'bloated-blackboard-remedy' is recorded on a live ticket — left in place.
- Branch sweep: 'branch-sweep-landed' has merged PR #811 at ccc5e0a3ae97, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, coga/contexts/dev/code/SKILL.md, coga/recurring/branch-sweep/ticket.md (+11 more) — left in place.
- Branch cleanup: local 'branch-sweep-landed' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'ci-posture' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-ci-posture' — left in place.
- Branch cleanup: force-deleted local 'cite-symbols-rule' (was fe8d88459a879907e91505e682cf3af673a80e71) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/cite-symbols-rule.
- Branch sweep: 'client-repo-dream' is recorded on a live ticket — left in place.
- Branch sweep: 'codex/exclude-superseded-designs' is recorded on a live ticket — left in place.
- Branch cleanup: deleted remote origin/codex/retro-filter-coga-s-own-log-sync-commits-out-of-the-dige-knowledge.
- Branch cleanup: deleted remote origin/codex/retro-verify-the-pr-review-comment-loop-once-the-review-knowledge.
- Branch sweep: 'coga/skill-update' is recorded on a live ticket — left in place.
- Branch sweep: 'design-cite-symbols' is recorded on a live ticket — left in place.
- Branch sweep: 'dispose-checkouts' is recorded on a live ticket — left in place.
- Branch sweep: 'doc-context-boundary' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-doc-context-boundary' — left in place.
- Branch sweep: 'dochub-api-answer' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-dochub-api-answer' — left in place.
- Branch sweep: 'docs/contributing' is recorded on a live ticket — left in place.
- Branch sweep: 'dream-routing-holes' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-dream-routing-holes' — left in place.
- Branch sweep: 'dream-w36-extract-backlog' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-dream-w36-extract-backlog' — left in place.
- Branch sweep: 'dream-w38-extract-backlog' has merged PR #812 at 35b9b60909bf, but the ref carries commits touching AGENTS.md, CLAUDE.md, coga/contexts/coga/codebase/SKILL.md (+5 more) — left in place.
- Branch cleanup: local 'dream-w38-extract-backlog' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: deleted remote origin/dream-w38/cli-context-derived-operator.
- Branch cleanup: deleted remote origin/dream-w38/codebase-context-skill-installer.
- Branch cleanup: deleted remote origin/dream-w38/docs-with-review-skills.
- Branch cleanup: deleted remote origin/dream-w38/orient-agent-guide.
- Branch cleanup: deleted remote origin/dream-w38/recurring-templates.
- Branch cleanup: deleted remote origin/dream-w38/small-contract-drifts.
- Branch cleanup: deleted remote origin/dream-w38/sync-context.
- Branch cleanup: force-deleted local 'dream/architecture-1788913097' (was d8ac2c12d2da6acbe80cf2203b226427750e763e) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/bootstrapskills-1788913097' (was d596d54715c51a1223d880fac2f026f1b1b16488) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/codebase-1788913097' (was 5d8853e93abadfefdd49198f441b964e9168d6a6) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/devcode-1788913097' (was 0e45372e8aedc7dd4a638c393e929f8a3ce25830) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/dreamscan-1788913097' (was 7fdf062f668b329b2a028749f53276154f6b0767) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/launch-internals-1788913097' (was a7c5462d7866532075df866800803c5cc0583943) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/positioning-1788913097' (was cb3fbd17384908baa233bd34bd04318baa471a3f) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/recurring-1788913097' (was f30025b7a0504234a3ab0634fa0273bc8cb0fcae) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/skillupdate-1788913097' (was 7a9e39d320d07c3686992fc783439448ccc1fbd5) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/sync-1788913097' (was ea067997c465fb1f9be812a7857a6f6e4667ad88) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'dream/templates-1788913097' (was 82f355e325f67a82297c5925201c3ac791ea327f) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'feature-branch-state-boundary' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-feature-branch-state-boundary' — left in place.
- Branch sweep: 'fix/context-artifacts' is recorded on a live ticket — left in place.
- Branch sweep: 'fix/headless-completion-system' is recorded on a live ticket — left in place.
- Branch sweep: 'fix/recurring-ledger-freshness' is recorded on a live ticket — left in place.
- Branch sweep: 'fix/released-claim-edits' is recorded on a live ticket — left in place.
- Branch cleanup: force-deleted local 'fix/watchdog-pauses' (was 3c6468689d577a378c08eccd2a85e6a08ade7fb4) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'fresh-checkout-lacks' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-fresh-checkout-lacks' — left in place.
- Branch sweep: 'gh-backed-readonly-context' is recorded on a live ticket — left in place.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'init-bare-slack-env' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-init-bare-slack-env' — left in place.
- Branch sweep: 'init-clone-setup' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-init-clone-setup' — left in place.
- Branch sweep: 'packaged-context-states' is recorded on a live ticket — left in place.
- Branch sweep: 'period-task-recipe-firing' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-period-task-recipe-firing' — left in place.
- Branch sweep: 'propagate-local-config' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'publish-sync' is recorded on a live ticket — left in place.
- Branch sweep: 'quiet-first-run' is recorded on a live ticket — left in place.
- Branch sweep: 'recipe-reporting-contract' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-recipe-reporting-contract' — left in place.
- Branch sweep: 'reconcile-audit-lifecycle' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-all-child-sweep (no merged PR).
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch sweep: 'recurring-missing-workflow' has merged PR #814 at 4d1bafcb78b5, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, src/coga/recurring.py, src/coga/recurring_runner.py (+2 more) — left in place.
- Branch cleanup: local 'recurring-missing-workflow' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'recurring-twin-note' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-recurring-twin-note' — left in place.
- Branch sweep: 'reminders-harness' is recorded on a live ticket — left in place.
- Branch sweep: 'remove-build-project' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-remove-build-project' — left in place.
- Branch sweep: 'remove-digest' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-remove-digest' — left in place.
- Branch sweep: 'remove-narrative-candidates' is recorded on a live ticket — left in place.
- Branch sweep: 'resolve-step-one-assignee' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-resolve-step-one-assignee' — left in place.
- Branch sweep: 'resources-pkg-init' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch sweep: 'review-closing-act' is recorded on a live ticket — left in place.
- Branch sweep: 'scan-alert-nonfatal' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-scan-alert-nonfatal' — left in place.
- Branch sweep: 'scrub-sa-token' is recorded on a live ticket — left in place.
- Branch sweep: 'shebang-exec-check' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-shebang-exec-check' — left in place.
- Branch sweep: 'skill-update-per-skill' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-skill-update-per-skill' — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch sweep: 'split-ticket-contract' is recorded on a live ticket — left in place.
- Branch sweep: 'stranded-ticket-writes' is recorded on a live ticket — left in place.
- Branch sweep: 'sweep-abandoned-record' has merged PR #813 at d321c6a45a27, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, src/coga/recurring_runner.py, src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md (+1 more) — left in place.
- Branch cleanup: local 'sweep-abandoned-record' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: force-deleted local 'sweep-republishes-stranded-claim-release' (was ee36ca64a544d039a5df83bf12c035c31650c214) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/sweep-republishes-stranded-claim-release.
- Branch sweep: 'sync-canonical-policy' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-sync-canonical-policy' — left in place.
- Branch sweep: 'sync-context-preflight' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-sync-context-preflight' — left in place.
- Branch sweep: 'ticket-done-criteria' is recorded on a live ticket — left in place.
- Branch cleanup: deleted remote origin/ticket-recurring-scan-workflow-error.
- Branch sweep: 'ticket-relationships' is recorded on a live ticket — left in place.
- Branch sweep: 'title-only-validator' has merged PR #815 at 64101866c918, but the ref carries commits touching coga/contexts/coga/roadmap/SKILL.md, src/coga/commands/create.py, src/coga/dream_validate_drift.py (+4 more) — left in place.
- Branch cleanup: local 'title-only-validator' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'triage-inverted-premises' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-triage-inverted-premises' — left in place.
- Branch sweep: 'usage-report' is recorded on a live ticket — left in place.
- Branch sweep: 'v2-premise-holes' has merged PR #819 at 49cfcb941ee6, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/roadmap/SKILL.md, coga/recurring/dream/ticket.md (+5 more) — left in place.
- Branch cleanup: local 'v2-premise-holes' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'v2-stale-surfaces' is recorded on a live ticket — left in place.
- Branch sweep: 'validate-baseline' has a landed ref but is checked out in worktree '/home/n/Code/claude/coga-validate-baseline' — left in place.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: New skill note: branch sweep refuses a merged branch whose commits were rebased in another checkout
