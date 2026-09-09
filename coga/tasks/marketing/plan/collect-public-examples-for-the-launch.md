---
slug: marketing/plan/collect-public-examples-for-the-launch
title: Collect public examples for the launch
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: draft-for-human
secrets: null
---

## Description

Collect a small, public source packet that makes Coga's interaction and
correction loop concrete. The owner wants the pitch and narrative grounded in
real examples before marketing cleanup. The working direction is managing the
intent, instructions, knowledge and state an AI session works from, with those
inputs visible and editable in the user's repo.

Find 2–4 examples collectively covering a real task from rough intent to
execution, a human correction to governing guidance, and a later session using
previously recorded understanding. One example may cover more than one role.
Report any shortfall honestly; the target count never justifies inventing a
scene or weakening the evidence standard.

## Context

### Source boundary

Use public Coga-on-Coga material: this repo's tickets, log, contexts, skills,
diffs and merged PRs. Do not inspect private repos or use the private-repo
quotations in the old audit's `narrative-candidates.md`, even though that
attachment is tracked here. The owner ruled those quotations unpublishable.

The relevant owner direction is recorded under "Owner's pitch direction and
proposed authority" and "Managed-prompt clarification and claim check" in
`coga/tasks/redo-documentation-dir-and-merge-it-with-context-b.md`.
`marketing/map` indexes the rest of the marketing material. For this task the
needed fact is the managed-input interaction above; the whole launch plan and
distribution runbook need not be composed.

### Deliverable and acceptance

Draft the packet on this ticket's blackboard. Each example must include:

- the task and what the human/agent was trying to do;
- the dated source path and stable revision or public commit/PR reference;
- a short literal excerpt or precise description of the relevant action;
- for a correction, the prior behavior, governing edit and later behavior;
- for reuse, the exact context, the question it already answered and the later
  session record that shows the answer in use; and
- the claim the example supports, its limits, and any missing evidence.

A prompt containing a context proves delivery only. Code implementing a rule
does not by itself show a human correction changing later agent behavior.
Keep those distinctions explicit so the writer cannot turn a plausible
mechanism into an observed result.

The owner reviews selection and public suitability at step 2. At step 3,
record the accepted packet in
`coga/contexts/marketing/positioning/examples.md` and link it from
`marketing/positioning`. Mark accepted examples and unresolved gaps
individually. This is a supporting reference, not a new automatically composed
context. Hand it to `marketing/plan/write-the-pitch-and-narrative`.

### Out of scope and workflow

No token/time experiment, paired task execution, numeric efficiency result or
new launch threshold. The owner dropped that measurement on 2026-09-09.
No publication, product fixes, confidential-attachment cleanup, context-root
migration, or changes to the three-post sequence.

Use `draft-for-human`: the agent drafts the packet, the owner selects and
corrects it, and the agent records the final public sources. This authoring
ticket is separate from essay production. If no example supports one of the
desired claims, the final packet must expose that gap for the pitch decision.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
