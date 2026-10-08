---
name: coga/ticket/finalize
description: Finalize guided authoring by validating tasks, then publishing changed task paths and knowledge edits under the Coga and contexts roots together.
---

# Ticket Authoring Finalize

`coga ticket` calls the shared `coga.authoring.finalize_authored` helper after
a successful authoring interview. It validates authored tasks, then
publishes changed task paths together with every changed context, skill,
workflow, or config file under the Coga and contexts roots; a failed publish
keeps the edits and fails the command. The full contract, including unchanged targets and failures, lives
in [coga/internals/state-publication](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/internals/state-publication/SKILL.md).

The command owns this lifecycle directly; this skill documents the shared
behavior and does not provide an executable entry point.
