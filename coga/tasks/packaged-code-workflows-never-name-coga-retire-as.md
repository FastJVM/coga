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
step: 3 (open-pr)
agent: claude
---

## Description

The review step of the packaged code/with-review workflow ends at autoclose and never tells the owner to run coga retire, so checkout-bearing done tickets pile up in consuming repos. Add the closing-act instruction to the packaged review sections so every installation gets it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/847
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

## Peer review

`codex review --base main` **returned** successfully from the recorded feature
worktree on `review-closing-act` with no findings. Its focused verification
passed all 28 tests in `tests/test_bootstrap_workflow_review_sections.py`,
`tests/test_packaging.py`, and `tests/test_retire.py` using the primary
checkout's test interpreter with `PYTHONPATH` set to the feature checkout's
absolute `src` path. No must-fix changes were needed.

Manually read all four owner-facing review sections against the packaged
`coga/cli` retirement contract and `src/coga/commands/retire.py`: they name the
explicit owner action after `done` and retain the command reference as the
semantics owner. Confirmed there are no live workflow twins. This diff changes
plain markdown instructions and a content test; no terminal, pager, TTY prompt,
or rendered notification behavior changed.

Ran `git fetch origin main` then `git rebase FETCH_HEAD` in the feature
worktree. The rebase onto `f9c9182d` succeeded without conflicts; the four
incoming commits change only this ticket and the log. Full-suite verification
on the rebased branch passed:

- `PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  from the feature worktree — **2565 passed** in 273.54 seconds. The only
  warning was pytest's inability to write its optional cache in the read-only
  worktree; no tests failed. Confirmed `import coga` resolves to the feature
  checkout's `src/coga/__init__.py`.
- `coga validate --task packaged-code-workflows-never-name-coga-retire-as --json`
  from the primary checkout — one valid task, no issues.
- `git diff --check main...HEAD` — clean.

The feature worktree is clean and contains one committed change ahead of
`origin/main` (`170c7b98`); there are no incoming commits relative to the fetched
base. No separate review-fix commit was necessary. The branch remains
unpushed, with no PR; the next step owns publication.

## PR

Packaged code and docs review steps currently stop at marking a ticket `done`,
leaving owners without the closing instruction for its recorded checkout and
branch. Name `coga retire <slug>` as the owner's next action in all four
checkout-bearing workflows, explain the cleanup and retro handoff, and keep
detailed command semantics in the `coga/cli` context. A parametrized content
test covers every affected review section.

Test plan: `PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m pytest` (2565 passed); `coga validate --task packaged-code-workflows-never-name-coga-retire-as --json` (no issues); `git diff --check main...HEAD` (clean).

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `packaged-code-workflows-never-name-coga-retire-as`
Recorded: 2026-09-20T21:53:30+00:00

    Branch 'review-closing-act' is not safe to publish. current branch does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase FETCH_HEAD`. Reconcile it and relaunch, or `coga block --task packaged-code-workflows-never-name-coga-retire-as`.
