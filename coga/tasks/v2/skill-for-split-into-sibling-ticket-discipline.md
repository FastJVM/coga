---
slug: v2/skill-for-split-into-sibling-ticket-discipline
title: Skill for split-into-sibling-ticket discipline
status: draft
mode: agent
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

Surfaced by Dream W22 Phase 2 knowledge scan (G9).

The done `move-automerge-out-of-relay-status` ticket and its sibling
`remove-the-post-merge-automerge-git-hook` (since subsumed by the
standalone-automerge retirement) show a repeated
discipline: when a design grows beyond one PR's worth, the agent splits it
into ≥2 sibling tickets and records the split in the blackboard under a
`## Split` heading, cross-linking the siblings.

The `code/implement` and `code/design` skills both say "stop and split the
ticket on the blackboard" but neither defines the split mechanic — what
filename, what blackboard section, what cross-link convention, when to
sequence (`## Sequencing`) vs co-equal split.

Draft outline:

- Open a new `relay-os/skills/code/split-ticket/SKILL.md` (or extend
  `code/design` with a "Splitting a ticket" section).
- Bullets covering: when to split (PR too big, two concerns coupling); how
  (create sibling drafts, point at each other under `## Sequencing` /
  `## Split`); the cross-link convention.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
