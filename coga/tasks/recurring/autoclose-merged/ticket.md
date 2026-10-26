---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 9bbe2ae4-048c-40c6-b905-1a1f948c33e5
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

Generated: 2026-10-26T17:18:33+00:00
Task: `recurring/autoclose-merged`

1 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window` "Core port: CLI and test suite pass on native Windows": branch `coga/windows-native-01-core-port-cli-and-test-suite-p-2e174f`

2 checkout(s) preserved — a proof refused; each stays on the worklist until a human acts:

- `blocks/06-collapse-state-publication-into-one-user-topic` (worklist backlog): branch `blocks-06-collapse-state-publication` — local 'blocks-06-collapse-state-publication' has unmerged work and no merged PR vouching for it — left in place. (`coga retire blocks/06-collapse-state-publication-into-one-user-topic`)
  - Branch cleanup: local 'blocks-06-collapse-state-publication' advanced past the merged PR head 55c24d2fe48f — preserving it.
  - Branch cleanup: local 'blocks-06-collapse-state-publication' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/blocks-06-collapse-state-publication because the local branch remains.
  - Branch sweep: 'blocks-06-collapse-state-publication' has merged PR #1086 at 55c24d2fe48f, but the ref carries commits touching coga/skills/coga/ticket/finalize/SKILL.md, docs/README.md, docs/contexts/coga-dev/codebase/SKILL.md (+29 more) — left in place.
  - Branch cleanup: local 'blocks-06-collapse-state-publication' has unmerged work and no merged PR vouching for it — left in place.
- `blocks/08-trim-launch-prompt-and-workflow-topics` (worklist backlog): branch `coga/blocks-08-trim-launch-prompt-workflow` — local 'coga/blocks-08-trim-launch-prompt-workflow' has unmerged work and no merged PR vouching for it — left in place. (`coga retire blocks/08-trim-launch-prompt-and-workflow-topics`)
  - Branch cleanup: local 'coga/blocks-08-trim-launch-prompt-workflow' advanced past the merged PR head 61537ef1eed8 — preserving it.
  - Branch cleanup: local 'coga/blocks-08-trim-launch-prompt-workflow' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/coga/blocks-08-trim-launch-prompt-workflow because the local branch remains.
  - Branch sweep: 'coga/blocks-08-trim-launch-prompt-workflow' has merged PR #1089 at 61537ef1eed8, but the ref carries commits touching coga/skills/code/open-pr/SKILL.md, docs/README.md, docs/contexts/coga-dev/codebase/gotchas/SKILL.md (+36 more) — left in place.
  - Branch cleanup: local 'coga/blocks-08-trim-launch-prompt-workflow' has unmerged work and no merged PR vouching for it — left in place.

## Autoclose Sweep: unanswered review threads

Generated: 2026-10-26T17:18:34+00:00
Task: `recurring/autoclose-merged`

1 auto-closed ticket(s) merged with a review thread that is unresolved, not outdated, and got no reply. Autoclose only names them — reading, resolving, or replying stays with a human:

- `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window` "Core port: CLI and test suite pass on native Windows" — PR #1093:
  - `src/coga/branchsweep.py:1443` by @chatgpt-codex-connector: "P2 Badge Preserve non-UTF-8 Git ref and worktree names" — https://github.com/FastJVM/coga/pull/1093#discussion_r4362623990
