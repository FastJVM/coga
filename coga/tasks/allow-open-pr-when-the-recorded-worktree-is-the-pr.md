---
slug: allow-open-pr-when-the-recorded-worktree-is-the-pr
title: Allow open-pr when the recorded worktree is the primary checkout
status: in_progress
owner: nick
human: nick
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

`coga open-pr` still encodes a linked-worktree development model: its wrapper requires the
primary checkout on the control branch, while its recipe requires a separately recorded
`worktree:` on the feature branch. Repositories are moving to ordinary branches in the primary
checkout only, so those joint gates make the command impossible to run in the supported layout.

Fix: make `branch:` the only development-location input to `open-pr`. Run from the primary
checkout on that recorded feature branch, then apply the existing cleanliness, ahead-of-main,
freshness, authentication, push, and PR-recording checks there. Remove `worktree:` from the
command's operational contract; legacy lines may remain as inert task history during migration,
but the command must neither require nor inspect them. Update shipped rules and tests to describe
and exercise branch-only development rather than retaining a second worktree mode.

## Context

- Hit for real by `staticization/capture-and-correlate-generated-classes` and again by
  `staticization/classify-captured-definitions-against-the-approved` in the magicator2 repo:
  that repo's `AGENTS.md` permits ordinary branches in the primary checkout only.
- The rest of the workflow already tolerates single-checkout mode: implement, peer-review, and
  every `coga bump`/`coga block` on that ticket ran from the primary checkout while on the
  feature branch, committing ticket state onto it. Only `open-pr` hard-gates on the control
  branch.
- The recipe's freshness check (`check_branch_contains_control`) already handles generated
  `coga/tasks/**` / `coga/log.md` drift. Branch-only mode must continue to accept only the
  byte-identical task overlap produced by the preceding bump and reject divergent ticket state.
- `pr:` write-back gap (most likely place to go subtly wrong): `open_pr` writes `pr: <url>`
  to the blackboard *after* pushing (open_pr.py:324–330). In single-checkout mode that
  dirties the feature-branch working tree, so (1) the pushed PR lacks its own `pr:` record
  until committed, and (2) a re-run hits the command's own "uncommitted changes" refusal
  (open_pr.py:202–207), breaking its advertised idempotency. The fix must commit the `pr:`
  write in single-checkout mode or exempt the ticket file from the dirty check — and state
  which in the PR.
- Safety argument to make explicit in code/docs: in branch-only mode the feature-branch
  copy of the ticket is the *live* one (bumps commit onto it), which is why reading it from
  the feature branch is sound. `check_branch_contains_control` may accept the preceding
  bump's byte-identical copy of this ticket on the control branch, but must hard-fail if the
  two copies diverge.
- This ticket's own publication must use the branch-only path once the editable install contains
  the fix, or use the same explicit manual publication fallback as the two magicator incidents;
  do not create a linked worktree to escape the bug.
- Tests live in `tests/test_open_pr.py` and `tests/test_open_pr_command.py`. Replace two-layout
  expectations with branch-only success plus wrong-branch, stale-state, dirty-tree, fallback-clone,
  and missing-authority failures.
- Update both live and packaged development guidance that still instructs agents to create feature
  worktrees. Leaving those rules intact would recreate the unsupported topology.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: fix/open-pr-primary-checkout

## Owner direction superseding the implementation below — 2026-07-21

- Branch-only for now. Do not preserve or document a linked-worktree execution path.
- Remove `worktree:` from `open-pr` inputs and revise the current dual-mode implementation before
  publication. The existing implementation and peer-review notes below are retained as history,
  not as the accepted design.

## Implementation notes

- Preserve the existing control-branch gate for distinct control and feature checkouts.
- Resolve the ticket before applying that gate so a primary-checkout feature branch can be
  recognized from its recorded `worktree:` metadata.
- In the single-checkout layout, commit the generated `pr:` blackboard write to the feature
  branch so the PR contains its linkage and a retry does not fail the clean-tree preflight.

Implemented checkout-aware gating with two independent checks: resolved Git toplevels must
match, and the command checkout's Git directory must equal its common directory. The second
check preserves the legacy refusal when the command is accidentally run inside a linked
feature worktree, whose recorded path would otherwise look like the same checkout.

The recipe now commits the generated `pr:` line as `Ticket: <slug> — PR opened` and pushes
that commit in single-checkout mode. This keeps the live feature checkout clean, makes a
retry idempotent, and ensures the PR branch contains its own ticket linkage. Legacy
cross-worktree URL writes remain on the control checkout for the usual Coga state sync.

Regression status: `tests/test_open_pr.py` + `tests/test_open_pr_command.py` pass (27 tests),
including a symlinked primary-checkout path, linked-worktree refusal, clean retry, and remote
verification of the committed `pr:` record.

## Implement handoff

- Commit: `aa142bc3` (`Allow open-pr from the primary feature checkout`).
- Final freshness: rebased cleanly onto `origin/main` at `94ee0782`; branch is one commit
  ahead and the linked feature worktree is clean.
- Final verification after rebase: `python -m pytest` → 1,384 passed, 1 skipped.
- Task-scoped `coga validate --json` → 1 ok, 0 issues.
- Updated the live/packaged open-pr skill, packaged code workflows, live/packaged architecture
  context, and command reference for both layouts. Per ticket scope, did not change the broader
  worktree guidance in `coga/contexts/dev/code/SKILL.md` or its packaged copy.

## Follow-up found

- The pytest environment isolation does not clear inherited `COGA_TASK_*` variables. Three
  full-suite runs caused Dream validate-drift fixture output to append to this live ticket;
  the synthetic sections were removed. Fixing that test-harness leak is unrelated to open-pr
  and should be ticketed separately.

## Peer review

`codex review --base main` found three must-fix gaps despite the green suite:

- A real single-checkout `peer-review -> open-pr` bump writes byte-identical ticket state to
  both the feature branch and the control branch; the freshness check then rejects that path
  overlap before `open-pr` can run.
- An independent fallback clone has `git-dir == git-common-dir` too, so checkout-local Git
  identity alone misclassifies it as the primary checkout and writes `pr:` to a non-authoritative
  ticket copy.
- A recorded path inside the checkout (for example `/repo/coga`) is accepted as the same
  checkout, but the generated ticket commit uses a repo-root-relative pathspec from that nested
  directory and fails after creating the PR.

Planned fixes: permit only byte-identical generated ticket overlap in single-checkout mode;
use the launcher's exact `COGA_TASK_TICKET` path as the authority proof so an independent clone
cannot claim the exception; and commit from the resolved Git toplevel. Add real-Git regressions
for all three.

Applied all three fixes. The recipe now receives single-checkout authority only from the CLI's
launch-path proof, the freshness probe subtracts only explicitly allowed overlaps whose blobs
are identical at `HEAD` and fetched control, and both the ticket commit and push run from the
resolved checkout root. Divergent ticket state, linked worktrees, fallback clones, and unproven
manual feature-checkout invocations retain the control gate.

Pre-rebase verification: `python -m pytest` -> 1,388 passed, 1 skipped; focused open-pr and
GitHub-preflight coverage -> 82 passed. Test runs explicitly cleared inherited `COGA_TASK_*`
metadata, so the known harness leak did not mutate this live ticket again.

Final peer-review handoff:

- Review-fix commit after the mandatory rebase: `512bc8d4` (`peer-review: harden
  primary-checkout open-pr`); implementation commit: `66f2e372`.
- Rebased cleanly onto fetched `origin/main` at `f4f5e98d`; the feature branch is clean and two
  commits ahead.
- Post-rebase `python -m pytest` -> 1,388 passed, 1 skipped.
- Task-scoped validation -> 1 ok, 0 errors; the linked feature checkout has the expected
  `missing-user` warning because its gitignored `coga.local.toml` is intentionally absent.

## PR

Superseded by the 2026-07-21 owner direction. Do not publish the current dual-mode implementation;
rewrite this section after the branch-only rework and its verification are complete.
