---
title: Branch-sweep never clears rebased-copy branches
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
step: 1 (implement)
agent: claude
launch_generation: 1a95b92f-f923-452d-984a-a67a27900901
---

## Description

Filed by Dream 2026-W40, Phase 6 (shard ks-23, class gap; targets `src/coga/branchsweep.py::merged_pr_verdict` and `coga/skills/coga/branch-sweep/sweep/SKILL.md`). The branch-sweep skill's step 4 documents that a local ref whose commits were rebased in another checkout and then merged is refused "on every pass, until a human deletes it", and says neither the manual clearance (`git cherry` proof + `git branch -D` / `git push --delete`) nor a patch-id extension of `merged_pr_verdict` "is owned by a ticket yet". The 2026-09-28 sweep still skipped the six refs listed on 2026-09-21 (`branch-sweep-landed` #811, `dream-w38-extract-backlog` #812, `sweep-abandoned-record` #813, `recurring-missing-workflow` #814, `title-only-validator` #815, `v2-premise-holes` #819) and added five more (`bloated-blackboard-remedy` #856, `codex/retro-recurring-branch-sweep-knowledge` #859, `doc-context-boundary` #790, `shebang-exec-check` #800, `skill-update-per-skill` #796); the set grows weekly and is re-reported daily by autoclose's branch pass. Decide: extend `merged_pr_verdict` with a patch-id / `git cherry` equivalence check for merged PRs, or own the recurring manual clearance. Open PR #914 edits `branchsweep.py` for other reasons (it does not address this); coordinate with it. Owner search found only the done `branch-sweep-strands-squash-merged-branches-whose` (lagging refs, not rebases).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
