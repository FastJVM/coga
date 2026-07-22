---
slug: allow-open-pr-when-the-recorded-worktree-is-the-pr
title: Allow open-pr when the recorded worktree is the primary checkout
status: in_progress
owner: nick
human: nick
agent: claude
assignee: claude
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
step: 3 (open-pr)
---

## Description

`coga open-pr` is jointly unsatisfiable when a repo develops in its primary checkout instead
of a linked worktree:

- `commands/open_pr.py::_require_control_checkout` refuses unless `cfg.repo_root` is checked
  out on the control branch.
- `open_pr.py::open_pr` refuses unless the recorded `## Dev` `worktree:` is checked out on the
  recorded feature branch.

When the recorded worktree *is* the primary checkout, those are the same git checkout: on the
control branch the recipe's branch check fails, on the feature branch the wrapper's gate fails.
The command can never run, and the workflow's `open-pr` step dead-ends in a blocker.

This is not an edge case: worktree-based development is being retired, so the recorded
`worktree:` being the primary checkout is the standard layout going forward, and open-pr's
control-checkout gate is a worktree-era assumption.

Fix: in `_require_control_checkout`, when the task's recorded `worktree:` resolves to the same
checkout as `cfg.repo_root`, skip the control-branch requirement — with a single checkout there
is no second copy of the ticket for blackboard writes to diverge from, which is the trap the
gate exists to prevent. Legacy cross-worktree layouts keep the existing gate. Cover both
layouts with tests, and audit open-pr's docstrings/messages for the retired worktree≠checkout
assumption while there.

## Context

- Hit for real by `staticization/capture-and-correlate-generated-classes` in the magicator2
  repo (blocker id=20260720T183536): that repo's `AGENTS.md` forbids linked worktrees and
  fallback clones, so `## Dev` records the primary checkout path as `worktree:` and the
  feature branch is checked out there.
- The rest of the workflow already tolerates single-checkout mode: implement, peer-review, and
  every `coga bump`/`coga block` on that ticket ran from the primary checkout while on the
  feature branch, committing ticket state onto it. Only `open-pr` hard-gates on the control
  branch.
- The recipe's freshness check (`check_branch_contains_control`) already accepts
  non-overlapping generated `coga/tasks/**` / `coga/log.md` drift between branches, so
  accepting the same-checkout layout is consistent with the existing contract.
- The wrapper docstring states the design assumption to revisit: it "operates on the `## Dev`
  feature branch by name, pushing from the recorded worktree rather than the process's own
  checkout" — which presumes worktree ≠ control checkout.
- Not a one-line conditional: `_require_control_checkout(cfg)` runs *before* task resolution
  and only sees `cfg`, so the fix must resolve the ticket first (from a checkout possibly on
  the feature branch) and compare checkouts robustly — path equality is not enough; use
  `realpath` or `git rev-parse --git-common-dir` comparison.
- `pr:` write-back gap (most likely place to go subtly wrong): `open_pr` writes `pr: <url>`
  to the blackboard *after* pushing (open_pr.py:324–330). In single-checkout mode that
  dirties the feature-branch working tree, so (1) the pushed PR lacks its own `pr:` record
  until committed, and (2) a re-run hits the command's own "uncommitted changes" refusal
  (open_pr.py:202–207), breaking its advertised idempotency. The fix must commit the `pr:`
  write in single-checkout mode or exempt the ticket file from the dirty check — and state
  which in the PR.
- Safety argument to make explicit in code/docs: in single-checkout mode the feature-branch
  copy of the ticket is the *live* one (bumps commit onto it), which is why reading it from
  the feature branch is sound. `check_branch_contains_control` may accept the preceding
  bump's byte-identical copy of this ticket on the control branch, but must hard-fail if the
  two copies diverge.
- Self-reference trap: this ticket's own `open-pr` workflow step runs `coga open-pr`. Develop
  this ticket in a **linked feature worktree** (the classic layout) so the step runs the
  installed, unpatched code on the satisfiable two-gate path; a single-checkout dev layout
  would dead-end in exactly the bug being fixed unless the install is editable and patched.
- Tests live in `tests/test_open_pr.py` and `tests/test_open_pr_command.py` — put the
  two-layout coverage there.
- Out of scope: `coga/contexts/dev/code/SKILL.md` (and its packaged copy under
  `src/coga/resources/templates/`) still instructs "do code changes in a feature worktree",
  contradicting the worktree-retirement premise. Updating that context for the retirement is
  a separate follow-up ticket — don't absorb it here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: fix/open-pr-primary-checkout
worktree: /tmp/coga-open-pr-primary-checkout

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

The first `codex review --base main` found three must-fix gaps despite the green suite:

- A real single-checkout `peer-review -> open-pr` bump writes byte-identical ticket state to
  both the feature branch and the control branch; the freshness check then rejects that path
  overlap before `open-pr` can run.
- An independent fallback clone has `git-dir == git-common-dir` too, so checkout-local Git
  identity alone misclassifies it as the primary checkout and writes `pr:` to a non-authoritative
  ticket copy.
- A recorded path inside the checkout (for example `/repo/coga`) is accepted as the same
  checkout, but the generated ticket commit uses a repo-root-relative pathspec from that nested
  directory and fails after creating the PR.

Applied all three fixes. The recipe now receives single-checkout authority only from the CLI's
launch-path proof, the freshness probe subtracts only explicitly allowed overlaps whose blobs
are identical at `HEAD` and fetched control, and both the ticket commit and push run from the
resolved checkout root. Divergent ticket state, linked worktrees, fallback clones, and unproven
manual feature-checkout invocations retain the control gate.

A fresh review of those fixes found two more lifecycle gaps:

- Generated ticket/log commits could make `main..HEAD` non-empty without implementation work.
- The required PR-gated bump advanced only the control ticket, leaving the PR branch's
  `step:` / `assignee:` state stale and conflict-prone.

The single-checkout recipe now requires a committed path outside generated task/log state, and
the generic `requires: pr` policy republishes its successful transition commit to the PR branch.

A final `codex review --base origin/main` found three supervised-execution gaps:

- the pending tracked launch-log append tripped the checkout-cleanliness preflight;
- byte-identical directory-form task siblings and other tickets on a multi-ticket branch still
  counted as unsafe overlaps; and
- the usage record committed after the gated bump stayed local-only, leaving the local branch
  tip different from the merged PR head.

All three are fixed. `coga open-pr` commits exactly the pending generated log before checking
for any remaining dirt; freshness accepts byte-identical generated task/log overlaps but still
hard-fails every divergent blob; and teardown after a done-signalled, durably advanced artifact
gate publishes its trailing union-safe usage commit to the already-open branch. Blocks, crashes,
natural exits, and rewinds keep the ordinary local-only feature-log behavior.

Final peer-review handoff:

- Commits: `175a4f6c` (implementation), `9216b5f5`, `2c0c7daa`, and `3ea4ffc3`
  (three peer-review hardening passes).
- Rebased cleanly onto fetched `origin/main` at `a031faab`; the feature worktree is clean and
  four commits ahead.
- Focused open-pr, command, git-sync, and launch coverage: 219 passed.
- Post-rebase `python -m pytest`: 1,392 passed, 1 skipped.
- Task-scoped validation: the primary checkout reports 1 ok, 0 issues; the linked worktree
  reports 1 ok, 0 errors plus the expected `missing-user` warning because it intentionally
  lacks its gitignored `coga.local.toml`.
- Test commands explicitly cleared inherited `COGA_TASK_*` metadata; two stale synthetic Dream
  fixture sections found on the live blackboard were removed again.

## PR

Allow `coga open-pr` to publish from a primary checkout on its recorded feature branch while
preserving the control-checkout gate for linked worktrees, independent fallback clones, and
unproven ticket copies. The command uses the launcher's exact task path as the authority proof,
commits its pending generated launch log, rejects lifecycle-only branches, and accepts only
byte-identical generated task/log overlaps. It commits and pushes the generated `pr:` record,
then the PR-gated bump and launch teardown publish the final ticket and usage state so the PR
stays mergeable, retries stay clean, and local/remote feature tips remain aligned. Documentation
and real-Git coverage describe and exercise both checkout layouts and the supervised handoff.

Test plan: `python -m pytest` (1,392 passed, 1 skipped); task-scoped
`coga validate --json` (1 ok, 0 errors).
