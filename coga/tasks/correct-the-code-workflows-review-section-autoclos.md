---
title: 'Correct the code workflows'' review section: autoclose now disposes of checkouts'
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
launch_generation: pending:82f85e0f-75dd-4e48-8bb6-dbdbd35e3c9d
---

## Description

Filed by Dream 2026-W41, Phase 6 (contract audit, shard ca-05, class drift). Target: src/coga/resources/templates/coga/bootstrap/workflows/code/{design-then-implement,with-review,with-self-review}.md, the `## review` section. Filed as a draft instead of a proposal PR because open PR #950 (https://github.com/FastJVM/coga/pull/950, Codex peer review) edits with-review.md and does not carry this finding; apply after #950 lands or rebase onto it.

`design-then-implement.md` line 78, `with-review.md` line 151, and `with-self-review.md` line 76 (all under `src/coga/resources/templates/coga/bootstrap/workflows/code/`, the `## review` section) state that a done ticket's feature branch and recorded worktree "outlive the close: neither the sweep nor `coga bump` disposes of them, because destructive behavior is never implicit", leaving disposal solely to `coga retire <slug>`. Code reality contradicts this: `coga.autoclose.run_autoclose_recipe` calls `_dispose_checkouts`, which disposes of each closed ticket's recorded `branch:`/`worktree:` (and every open `retires.md` worklist entry) under the shared `coga.checkout_disposal` proofs, and `coga/skills/coga/autoclose/sweep/SKILL.md` ("The retire follow-up", lines 37-45) documents that the sweep "now runs the deterministic, narrow, named rule itself" because the named-only design built an unworked backlog. Source of truth: `src/coga/autoclose.py` (`_dispose_checkouts`, `run_autoclose_recipe`). The three workflow `## review` sections should say the autoclose sweep disposes of provably-safe checkouts on close and that `coga retire` remains the path for the retro and for checkouts a proof preserved.

Done when the three shipped workflow review sections say the autoclose sweep disposes of provably-safe checkouts on close (src/coga/autoclose.py _dispose_checkouts) and that `coga retire` remains the path for the retro and for checkouts a proof preserved; tests/test_packaging.py passes.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
