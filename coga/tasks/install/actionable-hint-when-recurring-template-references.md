---
slug: install/actionable-hint-when-recurring-template-references
title: Actionable hint when recurring template references a removed bundled skill
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- dev/code
- coga/recurring
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
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

Keep recognition and message construction shared where practical so the
recurring-sweep and validation diagnostics cannot drift. Validation should
inspect materialized recurring templates and resolve the skills referenced by
their workflow steps; checking only generated active tasks is insufficient.
Emit the deletion advice only for the exact removed `coga/megalaunch/run` ref,
so a locally customized template with another missing skill retains the generic
diagnostic. Tests should assert both the actionable known-removal message and
the checked-path details for an unrelated missing skill. The known-removal
message may replace the checked-path list for megalaunch; retaining checked
paths is required for unknown missing skills.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
