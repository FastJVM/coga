---
title: autoclose-preserved-checkout-remedies
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (open-pr)
agent: claude
---

## Description

Replaces closed PRs #870 and #849, both of which patched the pre-#839 'autoclose only names a retire follow-up' design. Since #839, `coga run autoclose` runs the shared disposal proofs itself (`_dispose_checkouts` over `checkout_disposal` / `branchcleanup`) and reports each refusal with `CheckoutOutcome.disposal.reason` and `CheckoutOutcome.manual_command`. Two refusals still produce advice a human cannot act on:

1. **Cross-repo worktree (#870's case).** A ticket whose recorded `worktree:` belongs to another git repository is refused as 'not a linked worktree of this repository' and `manual_command` still says `coga retire <slug>` — which fails the same proof from this repo, and the task does not exist in the owning repo. Resolve the recorded path to its owning checkout (the `--git-common-dir` comparison retire already makes) and name that checkout plus the by-hand `git -C <owner> worktree remove` / `branch -d` there; a path gone from disk or not a git worktree should say so and point at branch-only cleanup.

2. **Primary checkout recorded as `worktree:` (#849's case).** In the single-checkout layout the ticket records the primary checkout itself. The proof refuses it forever (the primary checkout is always a directory and never a linked worktree), so the entry is preserved, re-posted to coga-important on every run, and once retro deletes the ticket the worklist header tells a human to dispose of it by hand — which here means the repo. Such an entry should not count as retire debt: drop the worktree half when it is provably not a linked worktree retire could remove (a tri-state `git.is_linked_worktree_of`, so retire keeps its own preserve-on-doubt fail-safe), leaving a branch-only follow-up or none.

The closed PRs carry reviewed prose and tests for both rules (autoclose/sweep skill, `test_autoclose.py`, `test_retire_worklist.py`) that can be re-applied on top of the disposal-phase design. Keep the live and packaged twins of the autoclose/sweep skill and the autoclose-merged template in sync.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: autoclose-checkout-remedies
worktree: /home/n/Code/coga-autoclose-remedies

## Decisions

- Debt rule (asked the human, 2026-09-22): only **this repo's primary
  checkout** drops the worktree half. A foreign-linked worktree or an
  independent clone stays on the worklist (it's the only durable trace), with
  an owner-named remedy. So the probe is a classifier
  (`git.classify_checkout` → primary / linked / foreign-linked / standalone /
  None), not a bare tri-state bool; retire still requires `linked` and
  preserves on every other verdict, unknown included.

## Implemented (commit c79c20e01, rebased on origin/main d4d6dd95a; 2747 passed after rebase)

- `git.classify_checkout(root, path)` → `CheckoutRelation(kind, owner)`:
  `primary` / `linked` / `foreign-linked` (owner = that repo's main worktree)
  / `standalone`, or None (unreadable, a subdir rather than a checkout root,
  missing). Compares common dirs, so it holds from a recurring control worktree.
- `branchcleanup._is_linked_worktree_of` delegates to it (only `linked`
  passes); `WorktreeCleanupResult.not_linked` flags that refusal.
- `retire_worklist.is_primary_checkout` is the one debt exception: used by
  `autoclose._recorded_worktree` (closure time), the backlog walk in
  `_dispose_checkouts` (entry with nothing left → skipped), and `is_discharged`.
- `CheckoutOutcome.manual_command` names owner-specific `git -C` commands for
  foreign-linked, "remove by hand" for standalone/unreadable, and branch-only
  cleanup for a worktree already gone; the coga-important line carries the
  remedy for not-linked refusals.
- Prose: sweep skill (new "primary checkout is not debt" + "Remedies"
  sections), recurring context, packaged cli context, autoclose-merged
  template, docs/operations.md — live and packaged twins byte-identical.
- Tests: test_git (classifier), test_retire_worklist (discharge), 
  test_autoclose_dispose (cross-repo, clone, primary closure, primary backlog
  entry), test_autoclose (manual_command variants). Full suite: 2747 passed
  (one packaging test first failed only because the fresh uv venv had no pip).

## Adjacent staleness

- Peer review corrected the pre-#839 disposal descriptions in
  `coga/workflows/autoclose-merged/sweep.md` (+ packaged twin) and
  `docs/operations.md`, with the attending human's approval. Both now summarize
  the disposal phase and point to the sweep skill that owns the rules.
- The live `coga/recurring/autoclose-merged/retires.md` keeps its old header
  prose (the header is written only when the file is minted); left alone to
  avoid union-merge churn on a control-branch-written file.

## Peer review

- `codex review --base main` **returned** on 2026-09-22: no actionable
  regressions; its targeted runs passed 325 tests across autoclose, git,
  branch cleanup/sweep, retire, worklists, and packaging.
- Approved documentation correction committed as `916cfdc6c`; implementation
  is now `630ae1615`. Ran `git fetch origin main` and `git rebase FETCH_HEAD`
  unconditionally; clean rebase onto `8219bd4a8`. Feature worktree is clean.
- Full post-rebase `.venv/bin/python -m pytest`: **2747 passed** in 247.85s.
  `git diff --check` passed; feature worktree remains clean and committed.
- Inspected generated cross-repo Slack summary: it includes the owner checkout,
  the explanation that retire here cannot help, and both owner-scoped git
  commands. A real-git probe also classified an owner path containing a space
  and non-ASCII character correctly. The attending human chose to verify the
  actual Slack rendering. On request, sent the representative generated
  summary via `coga slack --task autoclose-preserved-checkout-remedies
  --important --message ...`, explicitly labeled TEST. The CLI reported
  `posted`, and the human pasted the received message and confirmed it was
  in coga-important. Owner paths and both git commands are present/readable.
  No cleanup was performed by the sample.
- The Slack command's separate state sync refused because this control
  checkout lagged the remote activation (remote step 1, local step 2 from
  the prior implement bump). `git pull --rebase --autostash origin main`
  fast-forwarded control to `8219bd4a8` and reapplied the local changes
  without conflicts, preserving the CLI-written step and review notes.

## PR

Autoclose now gives owner-scoped manual cleanup commands when a recorded
worktree belongs to another repository, and explains independent-clone,
unreadable-path, and missing-worktree follow-ups. Only this repository's
proven primary checkout stops counting as worktree debt; foreign checkouts and
unknown paths remain preserved. Existing primary-checkout worklist entries
clear once their local branch is gone.

The shared checkout classifier keeps retire's preserve-on-doubt proof intact.
Regression coverage exercises real repositories, and the sweep contract,
recurring template, and live/packaged twins document the behavior. Corrected
stale workflow and operations prose that still described pre-disposal autoclose.

Test plan: `codex review --base main` returned with no findings; post-rebase
`.venv/bin/python -m pytest` passed all 2747 tests; `git diff --check` passed;
owner confirmed the TEST summary received in coga-important with readable
owner paths and cleanup commands.
