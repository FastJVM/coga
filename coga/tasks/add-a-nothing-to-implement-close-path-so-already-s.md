---
slug: add-a-nothing-to-implement-close-path-so-already-s
title: Add a nothing-to-implement close path so already-satisfied tickets don't park
  as blocked
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
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
secrets: null
script: null
step: 3 (pr)
---

## Description

When an agent runs an implement-step ticket and finds there is **nothing to
implement** — every checklist item already landed via other merged work, so
there is no branch and no diff — it currently has no legitimate way to close the
ticket. `coga bump` refuses to close final-step tickets (`bump.py:132-138`),
`coga mark done` is owner-reserved by the `code/with-self-review` contract, and
no skill covers the empty-work case. The only escape hatch the implement skill
gives is `coga block` (`code/implement/SKILL.md:47-55`), so the agent overloads
`block` — whose real semantics are "I need a concrete human answer to proceed" —
to mean "there's nothing to do, please close this." The already-complete ticket
then parks at `status: blocked` and pollutes the `coga status --blocked` queue
until the owner manually unblocks + marks done.

Real example that motivated this: `coga-rename-follow-ups-post-repo-rename` —
the agent verified all items had landed, created a follow-up tracking ticket,
and then had to `block` for closure. It showed up as a spurious "blocker" in the
queue even though nothing was actually blocking anything.

Goal: give the flow a first-class "already satisfied / nothing to implement →
close" path so this outcome lands as done (or a distinct resolved state), not as
`blocked`.

## Approach options (decide during authoring)

1. **Skill guidance + distinct closure request.** Teach `code/implement` (and
   `code/self-qa`) the empty-work case: write the per-item evidence to the
   blackboard and raise a *closure request* that is visually/statefully distinct
   from a `block` (not shown in the blocked queue as a "reason"), which the owner
   confirms into `done`.
2. **New status/transition.** Add an agent-allowed transition (e.g.
   `coga mark superseded` / `resolved:obsolete`, or an agent "propose done" that
   the owner one-tap confirms) so already-landed work doesn't masquerade as
   blocked. Keep `done` owner-gated but make the proposal explicit.

Either way, the `coga status --blocked` view should stop surfacing
"nothing-to-do" tickets as blockers.

## Touchpoints

- `src/coga/commands/bump.py` (final-step close refusal, chaining)
- `src/coga/commands/mark.py` (`_DONE_FROM`, owner gating), `commands/block.py`
- `coga/skills/code/implement/SKILL.md`, `coga/skills/code/self-qa/SKILL.md`
- `coga/workflows/code/with-self-review.md` (owner-controlled review gate)
- Keep the shipped copies in sync: `src/coga/resources/templates/coga/...`
- Update the matching `coga/contexts/coga/` context if behavior changes.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/already-satisfied-close
worktree: /tmp/coga-already-satisfied-close

## Implement notes

- Read ticket plus Coga principles, architecture, codebase, current-direction, and project-stage contexts.
- Chosen shape: add a first-class already-satisfied closure command that marks the task done with required evidence, instead of overloading `blocked` or adding a new status.
- Implemented `coga mark already-satisfied <slug> --evidence "..."` in commit `131fac39` on `codex/already-satisfied-close`.
- The command appends `## Already satisfied` evidence, re-reads the ticket, marks it `done`, posts a done-style notification, and emits the supervisor done sentinel.
- Updated live and packaged `code/implement`, `code/self-qa`, `code/with-self-review`, and Coga CLI/architecture contexts so agents use this path instead of `coga block` for no-diff already-satisfied tickets.
- Verification:
  - `PYTHONPATH=/tmp/coga-already-satisfied-close/src python -m pytest -q tests/test_mark.py tests/test_notification_messages.py tests/test_done_marker_emission.py tests/test_git.py` -> 137 passed.
  - `PYTHONPATH=/tmp/coga-already-satisfied-close/src python -m pytest -q` -> 1071 passed, 1 skipped.
  - `PYTHONPATH=/tmp/coga-already-satisfied-close/src python -m coga.cli validate --task add-a-nothing-to-implement-close-path-so-already-s --json` -> ok_count 1, no issues.
  - `git diff --check` and staged `git diff --cached --check` clean.

## Self-QA

- Ran `/code-review` (high-effort, 8-angle finder + verify) and `/simplify` (reuse/simplification/efficiency/altitude) against `codex/already-satisfied-close` vs `main`.
- `/code-review`: two candidate findings, both rejected as non-bugs — the `agent:{assignee}` actor attribution and the append-then-transition ordering are the *exact* established pattern from `block.py` (`already_satisfied` is a deliberate structural mirror of `block`). No correctness changes.
- `/simplify`: rejected the "delete the re-read" finding as a **false positive** — `mark_done` calls `ticket.write()` which re-renders the whole file, so the re-read is load-bearing (dropping it would clobber the just-appended `## Already satisfied` evidence and fail `test_mark_already_satisfied_closes_with_evidence`). Skipped the `_finish_done`/`actor_for` helper-extraction findings: they'd rework the untouched `done` command and `block.py`, against this file's standalone-command convention and self-QA's "don't sweep adjacent files" scope. Skipped the whitespace-collapse note (intentional single-line entry).
- Applied (in-scope, contained to the changed file): fixed the `mark.py` module docstring that still claimed "three subcommands" with a strict verb↔status mapping; added a comment explaining the agent actor attribution; added `test_mark_already_satisfied_workflowless_collapses_transition` covering the previously-untested `prev is None` (no-workflow) transition-collapse branch.
- Doc sync verified clean: live vs packaged copies of `implement`, `self-qa`, `with-self-review`, and `architecture` are byte-identical on the already-satisfied hunks (`cli/SKILL.md` has no maintained live counterpart — packaged-only, pre-existing).
- Committed as `032ec2d0` (self-qa).
- Verification (python3.12): full suite `1072 passed, 1 skipped`; targeted mark/notification/marker/git tests `138 passed`; `validate --task ...` ok_count 1, no issues; `git diff --check` clean.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":5354752,"cli":"codex","input_tokens":182128,"model":"gpt-5.5","output_tokens":23728,"provider":"openai","schema":1,"session_id":"019f2e42-ca29-7463-9591-bc988369d555","slug":"add-a-nothing-to-implement-close-path-so-already-s","step":"implement","title":"Add a nothing-to-implement close path so already-satisfied tickets don't park as blocked","ts":"2026-07-04T18:02:10.602430Z","usage_status":"ok"}
