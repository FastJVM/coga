---
slug: v2/dev-loop-git-hygiene-lift-sync-with-main-into-code
title: 'Dev-loop git hygiene: lift sync-with-main into code/open-pr + add recurring
  merged-branch cleanup'
status: draft
mode: agent
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - coga/codebase
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Make the "sync the feature branch with `main` after the PR is opened" step
uniform across every dev workflow, and add a recurring task that prunes
merged local branches and leftover feature worktrees.

### Background (already verified — do not re-derive)

The branch-first convention is fine: `code/implement` (step 2) tells the
agent to `git worktree add ../relay-<branch> -b <branch> main` and record
`branch:` / `worktree:` under `## Dev`. All three workflows use it.

The **sync-with-main-after-PR** step is the problem. It currently lives
**only** in the inline `## pr` body of
`relay-os/workflows/dev/with-self-review.md` — checking `gh pr view
<PR#> --json mergeable,mergeStateStatus`, merging/rebasing `main` in,
resolving conflicts, re-running `python -m pytest`, pushing, then
bumping. The shared `relay-os/skills/code/open-pr/SKILL.md` does **not**
contain it. So the other two PR-opening workflows —
`code/design-then-implement` and `code/with-review`, both of which use
the `code/open-pr` skill — never tell the agent to sync with `main`
before handing off. That's the gap.

### Work

1. **Lift sync-with-main into `code/open-pr`.** Move the mergeable-check /
   sync-with-`main` / resolve-conflicts / re-test / push instruction into
   `relay-os/skills/code/open-pr/SKILL.md` so every workflow that opens a
   PR inherits it. Then thin out the duplicated paragraph in
   `relay-os/workflows/dev/with-self-review.md` `## pr` so it relies on the
   skill instead of restating it. Keep the ticket-`## PR`-section write
   wherever it ends up reading naturally.
2. **Recurring merged-branch cleanup.** Add a template under
   `relay-os/recurring/<name>/` that finds local branches already merged
   into `main` (and their stale `../relay-*` feature worktrees from
   `git worktree list`) and prunes them. Follow the existing recurring
   templates (`digest/`, `skill-update/`) for shape and schedule. Deletion
   of git refs is destructive — gate it: report/propose by default, and
   only auto-delete branches that are provably merged into `main`. Never
   touch the current branch or `main`. Mirror the change into the packaged
   copy under `src/relay/resources/templates/relay-os/` per CLAUDE.md.

### Acceptance

- `relay-os/skills/code/open-pr/SKILL.md` contains the sync-with-`main`
  step; `dev/with-self-review.md` no longer duplicates it.
- All three dev workflows now route an agent through a sync-with-`main`
  step before the human review handoff.
- A recurring cleanup template exists, is schedule-driven, prunes only
  provably-merged branches/worktrees, and never deletes `main` or the
  checked-out branch.
- Live `relay-os/` and packaged `src/relay/resources/templates/relay-os/`
  copies stay in sync.

## Context

Source layout and test expectations are in the attached `relay/codebase`
context. Key files:

- `relay-os/skills/code/open-pr/SKILL.md` — shared PR-opening skill (target
  of change 1).
- `relay-os/workflows/dev/with-self-review.md` — currently the only home of
  the sync step (de-duplicate).
- `relay-os/workflows/code/with-review.md`,
  `relay-os/workflows/code/design-then-implement.md` — the workflows that
  inherit the fix via `code/open-pr`.
- `relay-os/recurring/digest/`, `relay-os/recurring/skill-update/` — shape
  references for the new cleanup template.
- `relay.toml` `[git]` table — `control_branch` (default `main`) is the
  base to test "merged into" against; don't hardcode `main`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
