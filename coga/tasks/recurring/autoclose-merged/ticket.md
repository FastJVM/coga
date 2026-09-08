---
slug: recurring/autoclose-merged
title: Autoclose merged tickets
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
period_generation: 1ef11eda-11c9-4cc5-8689-a3574bacf883
workflow:
  name: autoclose-merged/sweep
  steps:
  - name: sweep
    skills:
    - coga/autoclose/sweep
    assignee: agent
secrets: null
---

## Description

Close Coga tickets whose linked GitHub PR has already merged and whose Coga
workflow is at its final step.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `coga mark done`. Once a day this recurring task fires before
the daily digest. Its `ticket.py` runs the existing merged-ticket sweep,
which:

1. scans active and in-progress tickets,
2. reads the `pr:` line under each ticket blackboard's `## Dev` section,
3. checks the linked PR state with `gh pr view`,
4. leaves non-final-step tickets alone as suspicious, and
5. marks final-step or workflow-less tickets `done` when the PR is merged, and
6. names the `coga retire` follow-up for each ticket it closed that still
   records a `branch:` or `worktree:`.

Autoclose never disposes of a checkout itself — `coga retire` owns those safety
proofs. Without step 6 an auto-closed ticket's worktree and branch outlive it
silently. Dream preserves checkout-bearing done tickets rather than deleting
the `## Dev` evidence the named command needs, so that debt stays actionable
until a human retires it.

This sweep is the sole trigger for auto-closing merged tickets — there is
no manual `automerge` command. The recurring task only changes when the
sweep runs; it does not change which tickets are safe to close.

Done events produced by the sweep go through `coga mark done`, so they are
spooled into the daily digest when `recurring/digest/` is installed. Running at
8am keeps those closures visible in the same day's 9am digest. A quiet day with
no merged final-step tickets exits successfully and changes nothing.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-09-08T23:50:09+00:00
Task: `recurring/autoclose-merged`

13 auto-closed ticket(s) still have a recorded feature checkout. Autoclose never removes one — `coga retire` owns the worktree and branch safety proofs:

- `carry-adjacent-bugs-out-of-a-blackboard-before-ret` "Carry adjacent bugs out of a blackboard before Retro deletes it": worktree `/tmp/coga-retro-adjacent-bugs`, branch `retro-adjacent-bugs` — `coga retire carry-adjacent-bugs-out-of-a-blackboard-before-ret`
- `cleanup/add-a-debug-mode-to-init-for-vendoring-from-source` "Vendor the init venv from PyPI only, dropping source-install paths": worktree `/home/n/Code/codex/coga-vendor-pypi-only`, branch `vendor-pypi-only` — `coga retire cleanup/add-a-debug-mode-to-init-for-vendoring-from-source`
- `cleanup/detect-the-current-git-branch-instead-of-hard-codi` "Detect the current git branch instead of hard-coding control branch main": worktree `/home/n/Code/coga-init-control-branch`, branch `init-control-branch` — `coga retire cleanup/detect-the-current-git-branch-instead-of-hard-codi`
- `dream-reconciliation-must-count-distinct-shard-ids` "Dream reconciliation must count distinct shard ids, not completion lines": worktree `/home/n/Code/codex/coga-dream-reconcile-distinct-shards`, branch `dream-reconcile-distinct-shards` — `coga retire dream-reconciliation-must-count-distinct-shard-ids`
- `give-a-ticket-s-superseded-design-one-documented-h` "Give a ticket's superseded design one documented home": worktree `/home/n/Code/codex/coga-superseded-design-doc`, branch `docs/superseded-design-home` — `coga retire give-a-ticket-s-superseded-design-one-documented-h`
- `launch-activates-before-preflight` "Launch activates a draft before its preflight checks refuse it": worktree `/home/n/Code/claude/coga-defer-launch-activation`, branch `defer-launch-activation` — `coga retire launch-activates-before-preflight`
- `live-and-packaged-twin-pairs-are-edited-together-b` "Live and packaged twin pairs are edited together by convention but not enforced by any test": worktree `/home/n/Code/codex/coga-derive-twin-sync`, branch `derive-twin-sync` — `coga retire live-and-packaged-twin-pairs-are-edited-together-b`
- `megalaunch-activates-picks-before-preflight` "Megalaunch activates picked tickets before its preflight checks refuse them": worktree `/home/n/Code/claude/coga-megalaunch-defer-activation`, branch `megalaunch-defer-activation` — `coga retire megalaunch-activates-picks-before-preflight`
- `no-comms-writing-skill-the-process-is-smeared-thro` "No comms-writing skill; the process is smeared through marketing plan": worktree `/home/n/Code/claude/coga-write-post-skill`, branch `write-post-skill` — `coga retire no-comms-writing-skill-the-process-is-smeared-thro`
- `no-skill-exists-for-the-cold-evaluator-review-of-a` "No skill exists for the cold evaluator review of a design spec": worktree `/tmp/coga-cold-design-review`, branch `cold-design-review` — `coga retire no-skill-exists-for-the-cold-evaluator-review-of-a`
- `packaged-repos-ship-recurring-templates-without-th` "Packaged repos ship recurring templates without the coga recurring context": worktree `/home/n/Code/claude/coga-package-recurring-context`, branch `package-recurring-context` — `coga retire packaged-repos-ship-recurring-templates-without-th`
- `retire-never-removes-a-worktree-that-ran-the-tests` "Retire never removes a worktree that ran the tests": worktree `/home/n/Code/claude/coga-retire-cache-worktrees`, branch `retire-cache-worktrees` — `coga retire retire-never-removes-a-worktree-that-ran-the-tests`
- `service-recurring-from-a-temp-control-worktree-ins` "Service recurring from a temp control worktree instead of failing the repo": worktree `/home/n/Code/claude/coga-recurring-control-worktree`, branch `recurring-control-worktree` — `coga retire service-recurring-from-a-temp-control-worktree-ins`
