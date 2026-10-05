---
title: Branch sweep
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 280131ac-9285-4915-ad01-7dfe1a653b50
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
   [dev/checkout-cleanup](context:dev/checkout-cleanup). Failed archival
   preserves the refs and worktree and records a failing sweep outcome.
   Then it removes the eligible worktree, reported under `removed worktree`,
   and deletes the local branch and/or remote ref per the same landing policy
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

Generated: 2026-10-05T18:29:03+00:00
Task: `recurring/branch-sweep`

Result: 0 local and 0 remote branch(es) deleted, 0 worktree(s) removed, 0 skipped-worktree-pinned, 20 skipped.
- skipped: autoclose-retires-durable-home, bloated-blackboard-remedy, codex/retro-recurring-branch-sweep-knowledge, dream-w40-testing-baseline, fix/codex-peer-review-in-sandbox, fix/hash-blob-eol-filters, fix/recurring-sweep-staged-period-state, guard-reauthor-in-progress, nicktoper-patch-1, publish-off-control, recurring-crlf-lease, recurring-ledger-from-log, retire-worklist-linked-only, scrub-sa-token, shebang-exec-check, slack-important-alert, split-ticket-contract, usage-report-flow, v2-premise-adjudication, wedge-ticket-admin-reproduction

### Decisions

- Branch cleanup: local 'autoclose-retires-durable-home' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'bloated-blackboard-remedy' has merged PR #856 at 449bf55590e8, but the ref carries commits touching coga/contexts/coga/architecture/SKILL.md, coga/contexts/coga/blackboard/SKILL.md, src/coga/dream_validate_drift.py (+3 more) — left in place.
- Branch cleanup: local 'bloated-blackboard-remedy' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'codex/retro-recurring-branch-sweep-knowledge' has merged PR #859 at 9b9e80d36a05, but the ref carries commits touching coga/skills/coga/branch-sweep/sweep/SKILL.md, src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md — left in place.
- Branch cleanup: local 'codex/retro-recurring-branch-sweep-knowledge' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'coga/skill-update' is the shared skill-update branch — left in place.
- Branch sweep: 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/dream-w40-testing-baseline (no merged PR).
- Branch cleanup: skipping remote origin/fix/codex-peer-review-in-sandbox (no merged PR).
- Branch cleanup: skipping remote origin/fix/hash-blob-eol-filters (no merged PR).
- Branch cleanup: skipping remote origin/fix/recurring-sweep-staged-period-state (no merged PR).
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/nicktoper-patch-1 (no merged PR).
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'recover-state-only-divergence' is recorded on a live ticket — left in place.
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch cleanup: local 'scrub-sa-token' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'shebang-exec-check' has merged PR #800 at a02e2930511f, but the ref carries commits touching coga/skills/anthropic/skill-creator/eval-viewer/generate_review.py, coga/skills/clarity/scripts/validate_package.py, src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/gmail.py (+1 more) — left in place.
- Branch cleanup: local 'shebang-exec-check' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch cleanup: local 'split-ticket-contract' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/usage-report-flow (no merged PR).
- Branch cleanup: skipping remote origin/v2-premise-adjudication (no merged PR).
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).
