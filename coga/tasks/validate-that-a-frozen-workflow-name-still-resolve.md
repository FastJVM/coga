---
slug: validate-that-a-frozen-workflow-name-still-resolve
title: Validate that a frozen workflow.name still resolves
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
  - coga/codebase
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

`coga validate` never checks that a ticket's frozen `workflow.name` still
resolves to a workflow file. Add that check, so deleting or renaming a workflow
surfaces the tickets it strands instead of degrading them silently at launch.

Two rules, both **errors**, both scoped to live tickets
(`active` / `in_progress` / `paused`) with a frozen `workflow`. A `done` ticket
is finished and immutable; leave it alone. The severity matches
`active-no-workflow`: in every case below the ticket composes a placeholder
instead of its step instructions.

1. **Dangling workflow name.** `resolve_workflow_path` must find a file for
   `workflow.name`. A miss means the workflow file was deleted or renamed, and
   every step of that ticket composes
   `*Workflow definition not found; using frozen snapshot only.*`
   (`src/coga/compose.py:360`).

2. **Dangling step name.** For a frozen step with an **empty `skills:` list**,
   the resolved workflow must contain a matching `## <step-name>` section.
   A step with no skills draws its instructions solely from that inline prose
   (`compose._step_layers`, `src/coga/compose.py:352`); when the heading is
   absent the step composes `*No instructions attached to this step.*`
   (`src/coga/compose.py:375`) and the agent launches with no idea what the
   step is for.

Rule 2's `skills:`-empty condition is the whole subtlety and must not be
dropped: a step whose instructions come from `skills:` refs legitimately has no
`## <step-name>` section, so an unconditional heading check would fire on most
steps in the repo. Only the skill-less steps depend on the heading. Note also
that rule 2 can fire while rule 1 passes — the workflow file is present, but a
step was renamed or its prose removed after the ticket froze.

Scope note: rule 2 compares the *frozen* step names against the *current*
workflow file. Broader frozen-vs-current drift (steps added, removed, or
reordered; `assignee` or `requires` changed) is a real question but is out of
scope here — this ticket only covers the two cases that strip instructions from
a composed prompt.

## Context

Found while reviewing PR #627 (`remove-autonomy-triage`), which deleted the
`autonomy/*` workflows. Three live tickets were still frozen on them, and
nothing flagged it — `coga validate --json` output was byte-identical before
and after the deletion.

Why it degrades silently: `Workflow.freeze()` (`src/coga/workflow.py:84`)
snapshots only each step's `name` / `skills` / `assignee` / `requires`. The
inline `## <step-name>` prose is **not** frozen — `compose._step_layers`
(`src/coga/compose.py:326`) re-resolves the workflow file by name at launch and
falls back to `*Workflow definition not found; using frozen snapshot only.*`
(`src/coga/compose.py:360`) when it is missing. So a deleted workflow silently
strips step instructions from every frozen ticket pointing at it.

`_check_frozen_workflow` (`src/coga/validate.py:750-780`) resolves step
`skills:` refs and warns on an unfrozen (string) workflow, but never checks
`workflow.name` itself. `resolve_workflow_path` (`src/coga/paths.py:32`) is a
pure path lookup with no alias or rename map, so a rename is indistinguishable
from a deletion for an already-frozen ticket.

The three stranded tickets were migrated by hand in PR #627; this ticket is
about catching the next one at validate time rather than at launch.

A live example of rule 2's blast radius: `code/with-review` declares a
`peer-review` step with no `skills:`, so its entire instruction set is the
`## peer-review` section of the workflow file. Renaming that heading would leave
every ticket already frozen on `code/with-review` composing an empty peer-review
step, with `resolve_workflow_path` still succeeding.

`_check_frozen_workflow` is the natural home for both checks — it already walks
frozen steps and resolves their `skills:` refs, and rule 2 needs exactly the
`skills:`-empty branch it is already looking at. Rule 1 needs `Workflow.load` (or
just `resolve_workflow_path`) rather than a path check alone if you want the
inline headings; `inline_instructions` is parsed by `Workflow.load`
(`src/coga/workflow.py:71`), so one load serves both rules.

Regression test to beat: the bug's signature was that `coga validate --json` was
byte-identical before and after the workflow deletion. A test that freezes a
ticket on a workflow, deletes the file, and asserts a new error appears in the
JSON output covers rule 1; the same shape with a renamed `##` heading covers
rule 2.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
