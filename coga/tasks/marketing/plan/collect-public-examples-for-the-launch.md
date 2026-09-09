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

**Current brief: make and decide the launch story and examples.** The owner
corrected the earlier collection brief on 2026-09-09. Develop concrete options
for how to explain Coga, make the examples that let the reader understand each
option, and recommend which story to lead with. The existing task ref is retained
for continuity; the job is editorial creation and a decision with the owner.

Start from the owner's direction: managing the intent, instructions, knowledge
and working state an AI session works from, with those inputs visible and
editable in the user's repo. Decide what the reader should recognize, understand
and want to try. Existing material can help; the available log entries do not
determine the story.

## Context

### Make the options

Develop a few distinct story/example treatments. For each, draft:

- the reader's felt problem, the one claim and the opening situation;
- a concrete worked example or demonstration of the interaction, including
  what the human can inspect or change and what carries into later work;
- why this example makes the claim understandable and what it leaves out; and
- what is already observed, what is an authored illustration, and what would
  need a real demonstration before being described as an observed result.

Examples may be newly authored. They can be an explanation, a sample
ticket/context, or a proposed walkthrough. Clearly identify their form; never
present an invented scene, quotation, execution result or history as observed.
A new public demonstration is a valid way to make an example when it serves
the chosen story. This task does not require a quota of historical incidents.

The governing owner direction is recorded under "Owner's pitch direction and
proposed authority" and "Managed-prompt clarification and claim check" in
`coga/tasks/redo-documentation-dir-and-merge-it-with-context-b.md`.
`marketing/map` locates related material. Use the managed-input direction,
ownership, honest limits and personal internal-tool/open-source posture.

### Decide, then hand off

Recommend the strongest treatment and explain the tradeoff against the others.
At the human step, settle the central story, the examples to use, and what to
leave out. The decision must say what the later writer is being asked to write;
an unranked collection of links does not complete the task.

Draft options and the recommendation on this blackboard. At step 3, record the
owner's chosen story and worked examples in
`coga/contexts/marketing/positioning/examples.md`, link it from
`marketing/positioning`, and hand it to
`marketing/plan/write-the-pitch-and-narrative`. Keep short reasons for rejected
options and any evidence still needed for factual claims. This is a supporting
reference, not a new automatically composed context.

The pitch ticket turns that decision into finished copy. It can use clearly
identified illustrations while real-event claims require public support.
The existing `marketing/build-the-launch-plan` owner gate decides resulting
campaign/keep/drop changes; this task does not cancel the retained posts.

### Evidence and boundaries

For claims about what actually happened, use public Coga-on-Coga tickets, log
entries, contexts, diffs or PRs with dates and stable references. A context in a
prompt proves delivery; later work is needed to support a claim of actual reuse.
Private-repo quotations from the old audit are excluded even though the
attachment is tracked in this repo. Do not inspect those private repos.

The owner dropped token/time measurement: no paired experiment, numeric
efficiency result or invented launch threshold. External publication, product
fixes, confidential-attachment cleanup and the proposed context-root migration
remain with their own tickets.

Use `draft-for-human`: the agent makes concrete options and a recommendation,
the owner decides and edits, and the agent records the selected story/examples.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
