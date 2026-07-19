---
slug: install/actionable-hint-when-recurring-template-references
title: Actionable hint when recurring template references a removed bundled skill
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
  - dev/code
  - coga/recurring
skills: []
workflow: code/with-review
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

The implementation may choose the smallest maintainable mechanism for
recognizing this known removal. A generic historical fallback for arbitrary
formerly bundled skills is not required.

### Acceptance criteria

- A recurring template whose workflow references the removed bundled
  `coga/megalaunch/run` skill reports that megalaunch is now on-demand only
  and tells the operator to delete `coga/recurring/megalaunch/` and
  `coga/workflows/megalaunch/`.
- `coga validate` reports the same stranded-template migration problem, so it
  is discoverable before a scheduled recurring sweep reaches the template.
- Missing skills that are not known removals retain useful generic diagnostics,
  including the paths Coga checked.
- Tests cover both the recurring sweep failure and validation diagnostic.

## Context

The generic missing-skill diagnostic is produced in `src/coga/compose.py`,
while workflow skill resolution is shared through `src/coga/paths.py`.
Recurring template loading and task creation live in `src/coga/recurring.py`;
structural validation lives in `src/coga/validate.py`. Keep any durable
behavioral explanation synchronized with the relevant live context under
`coga/contexts/coga/` and its packaged copy under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/`.

The desired behavior is deliberately narrow: recognize the known megalaunch
removal and preserve the generic missing-skill path for unrelated refs. There
is no requirement to infer whether an arbitrary missing ref shipped in an
older Coga release.

<!-- coga:blackboard -->

## Ticket authoring notes

- Human chose `code/with-review`; the design is considered settled.
- `coga validate` must surface stranded recurring templates.
- No generic historical fallback is required for arbitrary formerly bundled
  skills; implementation details for the known megalaunch recognition are left
  to the implementer.

## Evaluator review

The ticket is clear and implementation-ready: it identifies the concrete failure path, fixes the design choices that matter (known megalaunch removal, validation parity, preservation of generic diagnostics), and leaves only the mechanism flexible. `code/with-review` fits a user-facing diagnostic change spanning composition, recurring behavior, validation, tests, and likely durable documentation.

The attached contexts are relevant. `dev/code` is appropriate for the PR workflow. `coga/recurring` is broad, but this change crosses template loading, period-task behavior, and validation, so carrying the full recurring contract is defensible; no additional broad context appears necessary because the ticket supplies focused source pointers and AGENTS.md supplies repository conventions.

Scope is reasonable for one ticket, though validation and recurring sweep may reach the same failure through different code paths; the implementer should centralize recognition/message construction if practical so the diagnostics cannot drift. Tests should assert both the actionable known-removal text and retention of checked-path details for an unrelated missing skill.

Two assumptions merit checking during implementation: define precisely what `coga validate` scans (materialized recurring templates and their resolved workflow steps, not merely generated active tasks), and ensure the deletion advice is only emitted for the exact known ref so a locally customized template with another missing skill is not misdiagnosed. It would also help to confirm whether the known-removal diagnostic supplements or replaces the checked-path text for megalaunch; the acceptance criteria explicitly preserve paths only for unknown removals.
