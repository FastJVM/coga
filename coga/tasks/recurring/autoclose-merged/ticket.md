---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: cfeb5bd5-f0c2-4762-9e43-135f8a999d3a
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
workflow is at its final step, and dispose of their recorded checkouts.

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
   branch, then remote branch, each under the
   [checkout proofs](context:coga/checkout-cleanup) `coga retire` also
   runs, and
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
After the autoclose recipe succeeds, `ticket.py` bumps. Landed branches with
no live ticket are the clone-scoped `branch-sweep` template's, which every
clone runs daily for its own refs; closure stays here, serviced once per
period for the whole repository. The daily cadence and reporting contract live in
[coga/recurring/scheduling](context:coga/recurring/scheduling); the deletion
proofs and the rules for primary checkouts and other clones are in
[coga/checkout-cleanup](context:coga/checkout-cleanup).

### Upgrading an older template

When adopting this template in an older repo, read the persistent
template's [worklist setup guide](https://github.com/FastJVM/coga/blob/main/coga/recurring/autoclose-merged/operations.md). This is an upgrade
procedure, not an action to repeat each period.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-11-07T22:03:27+00:00
Task: `recurring/autoclose-merged`

16 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `v1/06-fix-coga-git-sync-failures-that-leave-main-diverge` "Fix coga git sync failures that leave main diverged from origin": branch `coga/v1-06-fix-coga-git-sync-failures-that-leave-main-1212e6`
- `v1/07-lifecycle-writes-read-control-s-ticket-before-modi` "Lifecycle writes read control's ticket before modifying it": branch `coga/v1-07-lifecycle-writes-read-control-s-ticket-bef-5b096f`
- `v1/10-preflight-dirty-tracked-files-before-skill-update` "Preflight dirty tracked files before skill-update PR checkout": branch `coga/v1-10-preflight-dirty-skill-update`
- `v1/11-skill-update-rebuilds-its-branch-and-discards-hand-pushed-commits` "Skill update rebuilds its PR branch every period and silently discards hand-pushed commits": branch `coga/v1-11-skill-update-rebuilds-its-branch-and-disca-0af198`
- `v1/12-fix-release-env-fixture-interpreter-symlink-in-fre` "Fix release_env fixture interpreter symlink in fresh venvs": branch `coga/v1-12-release-env-interpreter`
- `v1/13-repair-ci-and-resume-with-release-focused-triggers` "Repair CI and resume with release-focused triggers": branch `coga/v1-13-repair-ci-and-resume-with-release-focused--a448a8`
- `v1/15-uninstall-recovery-hints-use-posix-env-syntax-on-w` "Uninstall recovery hints use POSIX env syntax on Windows": branch `coga/v1-15-uninstall-recovery-hints-use-posix-env-syn-9a5041`
- `v1/23-scan-for-an-existing-repo-during-install` "Scan for an existing repo during install": branch `coga/v1-23-repo-prerequisite`
- `v1/24-mention-coga-build-in-the-install-flow` "Mention coga build in the install flow": branch `coga/v1-24-mention-coga-build-install`
- `v1/26-make-the-readme-install-section-the-only-install-p` "Retire the coga/install topic": branch `coga/v1-26-retire-install-topic`
- `v1/34-prevent-duplicate-session-usage-records-from-infla` "Prevent duplicate session usage records from inflating totals": branch `coga/v1-34-prevent-duplicate-session-usage-records-fr-666e38`
- `v1/36-usage-report-name-the-human-split-per-agent-show-c` "Usage report: name the human, split per agent, show cache reads separately": branch `usage-report-name-human-agent-split`
- `v1/40-state-the-hatchling-prerequisite-in-the-clean-whee` "State the hatchling prerequisite in the clean-wheel proof": branch `coga/v1-40-hatchling-prerequisite`
- `v1/filter-by-user-for-megalaunch` "filter by user for megalaunch": branch `coga/v1-filter-by-user-for-megalaunch-85c239`
- `v1/honor-codex-home-when-locating-codex-rollouts` "Honor CODEX_HOME when locating Codex rollouts": branch `coga/v1-honor-codex-home-when-locating-codex-rollouts-5b4cd1`
- `v1/human-review-pr-for-ambiguous-lifecycle-status-con` "Human-review PR for ambiguous lifecycle status conflicts": branch `coga/v1-human-review-pr-for-ambiguous-lifecycle-statu-a4ef81`
