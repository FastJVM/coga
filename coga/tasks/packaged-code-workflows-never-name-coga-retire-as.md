---
title: Packaged code workflows never name coga retire as the closing act
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
step: 2 (peer-review)
agent: claude
launch_generation: pending:baa2e472-856f-4f7c-8f09-8cd1d74283ae
---

## Description

The review step of the packaged code/with-review workflow ends at autoclose and never tells the owner to run coga retire, so checkout-bearing done tickets pile up in consuming repos. Add the closing-act instruction to the packaged review sections so every installation gets it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: review-closing-act
worktree: /home/n/Code/claude/coga-review-closing-act

## Implement

Changed (one commit, `Name coga retire as the closing act in packaged review
sections`):

- `src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md`,
  `code/with-self-review.md`, `code/design-then-implement.md`, and
  `docs/with-review.md`: appended a paragraph to each `## review` section after
  the autoclose sentence. It says `done` is not the end of the ticket, that
  neither the sweep nor `coga bump` disposes of the recorded checkout/branch
  (destruction is never implicit), names `coga retire <slug>` as the owner's
  closing act, summarizes what retire does (worktree removal, branch prune,
  `retro/done-ticket` launch), and points at the `coga/cli` context for what
  retire proves and refuses. Retire's semantics stay owned by `coga/cli`; the
  workflow only names the act.
- `tests/test_bootstrap_workflow_review_sections.py`: parametrized
  template-content test over the four workflows, in the style of
  `tests/test_code_implement_skill.py`, asserting each `## review` section
  names `autoclose-merged`, `run \`coga retire <slug>\``, and
  `retro/done-ticket`.

Decisions:

- Included `docs/with-review` even though the ticket title says "code
  workflows": its implement step records `branch:`/`worktree:` under `## Dev`
  exactly like the code workflows, so its `done` tickets pile up the same way.
  Leaving it out would keep the gap in one of four packaged checkout-bearing
  workflows.
- No live `coga/workflows/code/` or `coga/workflows/docs/` twin exists (per
  `coga/codebase`, the packaged copy is what this repo resolves and freezes),
  so there is no live copy to sync; `tests/test_packaging.py` still passes.
- No context edit needed: `coga/cli` already specifies `coga retire`, and
  `dev/code` already states "You do not remove your own feature checkout".

Verification: `.venv/bin/python -m pytest` in the feature worktree — 2565
passed, run before and again after rebasing onto `origin/main` (three
ticket-state commits came in; nothing broke). Branch is clean and contains
current `origin/main`. Not pushed; no PR.
