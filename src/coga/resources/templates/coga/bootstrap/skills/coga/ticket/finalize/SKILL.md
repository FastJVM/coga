---
name: coga/ticket/finalize
description: Finalize guided authoring by validating tasks, then publishing changed task paths and knowledge edits under the Coga and contexts roots together.
---

# Ticket Authoring Finalize

`coga ticket` calls the shared `coga.authoring.finalize_authored` helper after
a successful authoring interview. It validates authored tasks, then
publishes changed task paths together with every changed context, skill,
workflow, or config file under the Coga and contexts roots in one guarded
publish. An authored change to the Git destination (`[git]` enabled, remote,
or control branch) refuses, and a refused or failed publish keeps every edit
on disk and fails the command. The user contract lives in
[coga/state-publication](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/state-publication/SKILL.md#when-coga-publishes);
finalization internals, including unchanged targets, live in
[coga-dev/internals/state-publication](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/state-publication/SKILL.md#guided-authoring-finalization).

The command owns this lifecycle directly; this skill documents the shared
behavior and does not provide an executable entry point.
