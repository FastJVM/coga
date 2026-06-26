---
slug: v2/document-workflow-less-concept-capture-drafts-as-s
title: Document workflow-less concept-capture drafts as supported state
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
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
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Surfaced by Dream W22 Phase 2 knowledge scan (G5).

Every Dream `validate-drift` run is dominated by `missing-workflow` warnings on
concept-capture drafts — Dream W21 reported 12, Dream W22 reported 14. These
drafts are an intentionally authored state (the human stashes an idea before
deciding how to do the work), not authoring drift, and the validator keeps
re-flagging them every run.

Open ticket `resolve-missing-workflow-validator-vs-concept-capt` proposes a
validator-level fix; this one is the documentation half — until the validator
is taught about concept-capture, nothing in the live contexts tells a future
agent (or a human reading validate-drift output) that "workflow-less draft" is
a supported product state. Document the shape.

Draft outline (one possible shape, human decides):

- Add a heading **"Workflow-less drafts (concept capture)"** under
  `relay-os/contexts/relay/architecture/SKILL.md`'s `## Two state machines per
  ticket`, or open a new `relay-os/contexts/relay/draft-shapes/SKILL.md`.
- 2-3 bullets covering: drafts may legitimately have no workflow; `relay mark
  active` refuses them; concept-capture is the normal use-case until
  exploration → spawn happens; the validator currently flags them and that is
  the gap, not the draft.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
