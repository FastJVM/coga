---
title: Branch sweep
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 54df4a62-3c28-4476-affd-4d8d3913590e
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
past it. The daily autoclose template now also invokes this same branch pass;
this standalone weekly run remains an independent retry. Cadence is owned by
[coga/recurring/scheduling](context:coga/recurring/scheduling).

Once a week this recurring task's `ticket.py` runs the branch sweep,
which:

1. prunes registrations for worktrees whose directories are gone, then
   enumerates the branches held by the remaining live worktrees,
2. enumerates every local branch and every branch on the configured git remote,
3. skips the configured control branch, the checked-out branch, and any
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
   fine), and recorded by no non-terminal ticket is removed first, reported
   under `removed worktree`, and its refs continue to step 6; a worktree that
   fails any of those proofs stays `skipped-worktree-pinned` with the reason,
6. deletes the remote ref and/or local branch per the same policy
   `coga retire` uses (plain `git branch -d` when the tip is reachable from
   the control branch; log the tip SHA and force with `-D` for the
   squash-merge case a merged PR vouches for; skip and report anything
   unmerged with no merged PR), and
7. writes a `## Branch Sweep` report — the outcome lists and every
   per-branch decision — to this period task's blackboard, so the run has a
   durable record for the recurring sweep's autofix analyst; run outside a
   task, the report goes to stdout instead.

The sweep is defined in `coga.branchsweep.sweep_branches`. The worktree
removal is a direct destructive change gated on a repo-level opt-in; the
`dev/checkout-cleanup` context states the assumption the key asserts, and the
`coga/branch-sweep/sweep` skill names the proofs. Its first run
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

Generated: 2026-09-28T15:51:59+00:00
Task: `recurring/branch-sweep`

Result: 27 local and 19 remote branch(es) deleted, 0 worktree(s) removed, 0 skipped-worktree-pinned, 20 skipped.
- deleted local: adjudicate-moved-premises, autoclose-retire-worklist, autoclose-unanswered-threads, autofix-analyst-fixes, blackboard-writer-contract, codex/retro-recurring-blocker-reminders-knowledge, codex/retro-test-recurring-create-is-silent-fixture-fix-is-hal-knowledge, codex/retro-triage-five-review-comments-that-merged-unanswered-knowledge, dream-routing-holes, dream-w36-extract-backlog, dream-w39/distribution-telemetry-decision, dream-w39/docs-dream-run-summary-links, dream-w39/roadmap-v2-parking-decision, dream-w39/self-qa-single-checkout-layout, dream-w39/skill-creator-attribution-posture, dream-w39/skill-template-name-field, feature-branch-state-boundary, fresh-checkout-lacks, init-clone-setup, period-task-recipe-firing, recurring-twin-note, remove-build-project, remove-digest, resolve-step-one-assignee, scan-alert-nonfatal, sync-context-preflight, triage-inverted-premises
- deleted remote: blackboard-writer-contract, codex/retro-recurring-blocker-reminders-knowledge, codex/retro-test-recurring-create-is-silent-fixture-fix-is-hal-knowledge, codex/retro-triage-five-review-comments-that-merged-unanswered-knowledge, dream-routing-holes, dream-w36-extract-backlog, dream-w39/distribution-telemetry-decision, dream-w39/docs-dream-run-summary-links, dream-w39/roadmap-v2-parking-decision, dream-w39/self-qa-single-checkout-layout, dream-w39/skill-creator-attribution-posture, dream-w39/skill-template-name-field, human-workflows-runtime-fallback, recurring-done-serviced-no-tty, recurring-twin-note, recurring-verify-skill, resolve-conflicts-default-agent, sync-context-preflight, triage-inverted-premises
- skipped: autoclose-retires-durable-home, bloated-blackboard-remedy, branch-sweep-landed, codex/retro-recurring-branch-sweep-knowledge, doc-context-boundary, dream-w38-extract-backlog, guard-reauthor-in-progress, publish-off-control, recurring-crlf-lease, recurring-ledger-from-log, recurring-missing-workflow, retire-worklist-linked-only, scrub-sa-token, shebang-exec-check, skill-update-per-skill, slack-important-alert, sweep-abandoned-record, title-only-validator, v2-premise-holes, wedge-ticket-admin-reproduction

### Decisions

- Branch cleanup: force-deleted local 'adjudicate-moved-premises' (was c3805432da79a4c0aa65788d89cba47e90890dc5) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'autoclose-retire-worklist' (was 8d30ad626ec8e4bfe0e5ee99b9038c6e9fb47b66) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: local 'autoclose-retires-durable-home' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: force-deleted local 'autoclose-unanswered-threads' (was 88176e8daf37aaa915a2ed052c8fbd32ffaf32d7) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'autofix-analyst-fixes' (was 4a5502a5fd9156f4a7caca6a1d9432a50b6c39ca) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: force-deleted local 'blackboard-writer-contract' (was 2a15d11ff56e22d2884e100ff7a10d885159c388) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/blackboard-writer-contract.
- Branch sweep: 'bloated-blackboard-remedy' has merged PR #856 at 449bf55590e8, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/blackboard/SKILL.md, src/coga/dream_validate_drift.py (+3 more) — left in place.
- Branch cleanup: local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'branch-sweep-landed' has merged PR #811 at ccc5e0a3ae97, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, coga/contexts/dev/code/SKILL.md, coga/recurring/branch-sweep/ticket.md (+11 more) — left in place.
- Branch cleanup: local 'branch-sweep-landed' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'ci-posture' is recorded on a live ticket — left in place.
- Branch cleanup: force-deleted local 'codex/retro-recurring-blocker-reminders-knowledge' (was 72f00f420b54a02009670a97a8e90c3641e25986) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/codex/retro-recurring-blocker-reminders-knowledge.
- Branch sweep: 'codex/retro-recurring-branch-sweep-knowledge' has merged PR #859 at 9b9e80d36a05, but the ref carries commits touching coga/skills/coga/branch-sweep/sweep/SKILL.md, src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md — left in place.
- Branch cleanup: local 'codex/retro-recurring-branch-sweep-knowledge' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: force-deleted local 'codex/retro-test-recurring-create-is-silent-fixture-fix-is-hal-knowledge' (was 2c64872614eccb6c0e0984ab29103e20631d5383) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/codex/retro-test-recurring-create-is-silent-fixture-fix-is-hal-knowledge.
- Branch cleanup: force-deleted local 'codex/retro-triage-five-review-comments-that-merged-unanswered-knowledge' (was 6383b20ec9c67e8d29ef62711eb4f183ee7c44b4) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/codex/retro-triage-five-review-comments-that-merged-unanswered-knowledge.
- Branch sweep: 'coga/skill-update' is recorded on a live ticket — left in place.
- Branch sweep: 'doc-context-boundary' has merged PR #790 at a9fce62cea59, but the ref carries commits touching AGENTS.md, CLAUDE.md, coga/contexts/_template/SKILL.md (+8 more) — left in place.
- Branch cleanup: local 'doc-context-boundary' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'docs/command-classification' is recorded on a live ticket — left in place.
- Branch sweep: 'dream-block-on-stranded-retro' is recorded on a live ticket — left in place.
- Branch cleanup: force-deleted local 'dream-routing-holes' (was 0b140fc5b46298d4b345bdc5ef2a5c33f29d0f6b) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-routing-holes.
- Branch cleanup: force-deleted local 'dream-w36-extract-backlog' (was 901a9909a038902b42e0b904dbaa1636cec59213) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-w36-extract-backlog.
- Branch sweep: 'dream-w38-extract-backlog' has merged PR #812 at 35b9b60909bf, but the ref carries commits touching AGENTS.md, CLAUDE.md, coga/contexts/coga/codebase/SKILL.md (+5 more) — left in place.
- Branch cleanup: local 'dream-w38-extract-backlog' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: force-deleted local 'dream-w39/distribution-telemetry-decision' (was e104c2dc307bd5367727f89fa0fdb7b64c909ef5) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-w39/distribution-telemetry-decision.
- Branch cleanup: force-deleted local 'dream-w39/docs-dream-run-summary-links' (was 2a223ceec21471aae8e84b410f1b4de9d4913dee) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-w39/docs-dream-run-summary-links.
- Branch cleanup: force-deleted local 'dream-w39/roadmap-v2-parking-decision' (was 71cf19c188dc7aa1b5de520c2c4b418c7e3e0fae) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-w39/roadmap-v2-parking-decision.
- Branch cleanup: force-deleted local 'dream-w39/self-qa-single-checkout-layout' (was 0d3acfba3a4b8d86f24fa4af712e705212b6e7a4) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-w39/self-qa-single-checkout-layout.
- Branch cleanup: force-deleted local 'dream-w39/skill-creator-attribution-posture' (was ccac81a8893022fe0ac8b1a7aa3ec03615e66192) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-w39/skill-creator-attribution-posture.
- Branch cleanup: force-deleted local 'dream-w39/skill-template-name-field' (was f00c1fff48ef1dfb0a90f4f091efa5201f9d5cf6) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-w39/skill-template-name-field.
- Branch cleanup: force-deleted local 'feature-branch-state-boundary' (was 71ca71a20f58ecd02414319bae3da9c2245904d8) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'fix-authoring-publication' is recorded on a live ticket — left in place.
- Branch sweep: 'fix-positioning-owner-links' is recorded on a live ticket — left in place.
- Branch sweep: 'fix-stale-testing-skill-docs' is recorded on a live ticket — left in place.
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch cleanup: force-deleted local 'fresh-checkout-lacks' (was d4f754ee39ebe4a03df7f9589c892b8f6456e258) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: deleted remote origin/human-workflows-runtime-fallback.
- Branch cleanup: force-deleted local 'init-clone-setup' (was 237aadd52cf06c9c25a427919b6fc1d5f999fc0f) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'init-hosting-scaffold-empty' is recorded on a live ticket — left in place.
- Branch cleanup: force-deleted local 'period-task-recipe-firing' (was 20a71bc475a7186f8de1a6036a77ed37d4db0dbc) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'record-dev-loop-verification-gotchas' is recorded on a live ticket — left in place.
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: deleted remote origin/recurring-done-serviced-no-tty.
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch sweep: 'recurring-missing-workflow' has merged PR #814 at 4d1bafcb78b5, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, src/coga/recurring.py, src/coga/recurring_runner.py (+2 more) — left in place.
- Branch cleanup: local 'recurring-missing-workflow' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'recurring-sync-wedge' is recorded on a live ticket — left in place.
- Branch cleanup: force-deleted local 'recurring-twin-note' (was c16e34cfac17c649d94a5025185a5dbef0bc514d) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/recurring-twin-note.
- Branch cleanup: deleted remote origin/recurring-verify-skill.
- Branch cleanup: deleted local 'remove-build-project'.
- Branch cleanup: force-deleted local 'remove-digest' (was 9cb0231885dd7f86b067f251bfd8d62f80ee4cbe) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/resolve-conflicts-default-agent.
- Branch cleanup: force-deleted local 'resolve-step-one-assignee' (was 63c530eab8becefca0da941f1d03545d74fe4a5c) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch sweep: 'retire-worklist-owner' is recorded on a live ticket — left in place.
- Branch cleanup: force-deleted local 'scan-alert-nonfatal' (was db42f80d2b8d8c27acd69f756a19f0cdbf59023a) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: local 'scrub-sa-token' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'shebang-exec-check' has merged PR #800 at a02e2930511f, but the ref carries commits touching coga/skills/anthropic/skill-creator/eval-viewer/generate_review.py, coga/skills/clarity/scripts/validate_package.py, src/coga/dream_validate_drift.py (+6 more) — left in place.
- Branch cleanup: local 'shebang-exec-check' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'skill-update-per-skill' has merged PR #796 at e925ff14626c, but the ref carries commits touching coga/contexts/coga/codebase/SKILL.md, coga/recurring/skill-update/ticket.md, coga/skills/code/self-qa/SKILL.md (+11 more) — left in place.
- Branch cleanup: local 'skill-update-per-skill' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch sweep: 'split-ticket-contract' is recorded on a live ticket — left in place.
- Branch sweep: 'stop-recurring-inactive' is recorded on a live ticket — left in place.
- Branch sweep: 'sweep-abandoned-record' has merged PR #813 at d321c6a45a27, but the ref carries commits touching coga/contexts/coga/recurring/SKILL.md, src/coga/recurring_runner.py, src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md (+1 more) — left in place.
- Branch cleanup: local 'sweep-abandoned-record' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: force-deleted local 'sync-context-preflight' (was ab4d2b8e35ca067a72ea4cc839d3a5273a391fe3) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/sync-context-preflight.
- Branch sweep: 'ticket-relationships' is recorded on a live ticket — left in place.
- Branch sweep: 'title-only-validator' has merged PR #815 at 64101866c918, but the ref carries commits touching coga/contexts/coga/roadmap/SKILL.md, src/coga/commands/create.py, src/coga/dream_validate_drift.py (+4 more) — left in place.
- Branch cleanup: local 'title-only-validator' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: force-deleted local 'triage-inverted-premises' (was bb23768aa1e919429d552f1a7285bef746423890) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/triage-inverted-premises.
- Branch sweep: 'v2-premise-holes' has merged PR #819 at 49cfcb941ee6, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/roadmap/SKILL.md, coga/recurring/dream/ticket.md (+5 more) — left in place.
- Branch cleanup: local 'v2-premise-holes' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'validate-baseline' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).
