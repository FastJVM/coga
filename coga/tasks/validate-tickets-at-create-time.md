---
slug: validate-tickets-at-create-time
title: Validate tickets at create time
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

Newly created tickets are not validated at creation: neither `coga create`
nor `create_task` runs any schema check after writing, so a malformed ticket
(bad frontmatter, broken refs, missing fence) sits undetected until someone
happens to run `coga validate` much later. Worse, the `coga/cli` context
already *claims* this exists ("Coga-owned commands that mutate a task — draft,
ticket-authoring exit, mark, bump, launch-time transitions, recurring/retire
scaffolding — run that same task-scoped check after the write and before
reporting success") — code-vs-context drift. Implement the task-scoped
post-write validation on every mutating command as the context describes
(`coga validate --task <slug>` semantics, fail at the edge of the edit), or
audit which commands actually have it and fix the gap + the context together.

## Context

Reported by nicktoper (2026-07-09): tickets created during the retest session
were only checked when a full `coga validate` was run by hand, which is how
the legacy install/ schema drift went unnoticed. Touchpoints:
`src/coga/commands/create.py`, `src/coga/tasks.py` (`create_task`),
`src/coga/validate.py` (single-task scope), the other mutating commands
(`mark`, `bump`, `ticket` exit), and the `coga/cli` context section quoted
above.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
