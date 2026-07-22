---
slug: validate-that-a-frozen-workflow-name-still-resolve
title: Validate that a frozen workflow.name still resolves
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

`coga validate` never checks that a ticket's frozen `workflow.name` still
resolves to a workflow file. Add that check, so deleting or renaming a workflow
surfaces the tickets it strands instead of degrading them silently at launch.

The rule: for every ticket whose `workflow` is frozen, `resolve_workflow_path`
must find a file for `workflow.name`. A dangling ref on a live ticket
(`active` / `in_progress` / `paused`) is an **error** — the same reasoning
`active-no-workflow` already uses, since the ticket composes a placeholder
instead of its step instructions. A `done` ticket is finished and immutable;
leave it alone.

Worth deciding while implementing: whether a frozen step *name* that matches no
`## <step-name>` section in the resolved workflow deserves the same treatment.
It produces the sibling failure ("*No instructions attached to this step.*") and
was present on a live ticket for some time without anyone noticing.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
