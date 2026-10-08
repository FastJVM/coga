---
title: Move Coga-development rules out of the shipped base prompt
status: draft
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
---

## Description

The shipped base prompt (src/coga/resources/prompt.md) is composed into every launch in every user's repo, but its "Keep Coga small and legible" section (lines 98-116) only concerns developing Coga itself: it opens "When changing Coga itself" and talks about src/coga/, runner.RECIPES and wheel-owned edge modules. In someone else's repo it is noise on every launch and a possible source of confusion for an agent on an unrelated project. The base prompt was written for the Coga repo because that is the only place it has been used.

Fix: move that section out of the packaged base prompt into this repo's own coga/context.md, so it still applies when working on Coga and disappears for everyone else. No override mechanism is needed for this (that is overload-base-text-prompt-etc, which stays useful but comes after this one).

Then re-read the rest of the base prompt with one question: does each rule make sense in someone else's repo? Move or rewrite any other Coga-development-only rule the same way (candidates to check: references to coga/packaging, dev/design-history, coga.toml editing rules, Coga-specific topic names). Keep the packaged copy and any twin in sync, and update the owning topic (coga/prompt-composition) if it describes the base prompt's contents.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
