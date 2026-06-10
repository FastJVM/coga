---
title: Wire autonomy triage into impl-ready workflows
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Wire the general `autonomy/triage` test into the impl-ready path so every
appropriate ticket gets classified before implementation begins.

This follows `automation-triage`, which shipped the reusable rubric context and
the four tier workflows:

- `autonomy/fully-automated`
- `autonomy/assist-only`
- `autonomy/human-verify`
- `autonomy/human-only`

The design question for this ticket is timing and surface area. The previous
ticket intentionally did **not** wire the test into authoring time; the target is
impl-ready, with a thin triage step backed by `autonomy/triage`.

## Acceptance Criteria

- A thin autonomy-triage step is designed and added at the correct impl-ready
  point.
- The general workflows that should classify work before implementation are
  updated consistently.
- The seeded `_template` workflow is updated if the design says new tickets
  should inherit this path.
- The change does not merge or replace `browser/build-automation`'s separate
  browser-specific failure-radius triage.
- `relay validate --json` passes.
- Tests covering workflow/prompt behavior are updated if the implementation
  changes prompt composition or seeded workflow semantics.

## Out of Scope

- Rewriting the autonomy rubric or tier workflows shipped by
  `automation-triage`.
- Adding an `assist-only` branch to `browser/build-automation`.
- Moving the test to draft-time ticket authoring.

## Context

The upstream split was deliberate: `autonomy/triage` and the `autonomy/` tier
workflows are library artifacts until this follow-up attaches them to the
general implementation path.
