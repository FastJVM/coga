---
title: Fix or baseline the two known pre-existing test failures
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Dream 2026-W21 (knowledge scan, Phase 2) found a recurring `gap`: several done
tickets recorded the same two tests failing *before* any change was made —
`test_bump_unsupervised_prints_no_hint` and
`test_status_narrow_terminal_keeps_each_task_on_one_line`. Each agent had to
independently re-investigate and decide the failures were pre-existing and
unrelated to its work. Nothing records a known-failing baseline, so the same
red tests get re-litigated every run.

Two ways to close it — the human picks:

1. **Fix the tests.** Investigate the two failures and make the suite green,
   so "all tests pass" stays a meaningful gate.
2. **Baseline them.** If the failures are environmental / known-acceptable,
   record a short "known pre-existing failures" note in
   `relay-os/contexts/relay/codebase/SKILL.md` so future agents distinguish a
   real regression from inherited noise without re-deriving it.

Fixing is preferable if feasible; this is a `gap` ticket so the design
judgment happens here.

## Context

