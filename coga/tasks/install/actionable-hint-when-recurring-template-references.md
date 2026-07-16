---
slug: install/actionable-hint-when-recurring-template-references
title: Actionable hint when recurring template references a removed bundled skill
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Upgrading the coga package can strand a repo's materialized copies of
recurring templates (and their workflows) whose bundled skills the new
release removed. Observed live in magicator2: PR #550 made megalaunch
on-demand only and dropped the bundled `coga/megalaunch/run` skill, but the
repo still carried `coga/recurring/megalaunch/`, `coga/workflows/megalaunch/`,
and an `active` generated period task. Every `coga recurring` sweep then
failed on that template with a generic "no skill file exists" error and
exit 2, with no hint that the cause was an upstream removal.

Give the failure an actionable migration hint, in the same spirit as the
removed-config-key migration errors (`install/add-migration-errors-for-
removed-config-keys`): when a template's workflow step references a skill
that no longer resolves locally or in the package, and that ref matches a
known-removed bundled skill, say so — name the removal ("megalaunch is now
on-demand only; delete `coga/recurring/megalaunch/` and
`coga/workflows/megalaunch/`") instead of only listing the paths checked.

Scope questions to settle during implementation:

- Where the known-removed list lives (a small table next to the removed
  config-key migrations seems natural) and whether a generic "this ref was
  once package-shipped" fallback message is enough for future removals.
- Whether `coga validate` should flag stranded templates too, so the drift
  surfaces before a scheduled sweep hits it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
