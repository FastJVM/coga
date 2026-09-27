---
name: coga/ticket/finalize
description: Finalize guided authoring by validating tasks, publishing changed task paths, and reporting knowledge edits for review.
---

# Ticket Authoring Finalize

`coga ticket` calls the shared `coga.authoring.finalize_authored` helper after
a successful authoring interview. It reports context and skill edits for a
branch and human-reviewed PR, validates authored tasks, and publishes changed
task paths. The full contract, including unchanged targets and failures, lives
in [coga/internals/state-publication](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/internals/state-publication/SKILL.md).

The command owns this lifecycle directly; this skill documents the shared
behavior and does not provide an executable entry point.
