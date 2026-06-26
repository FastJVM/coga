---
slug: document-the-automerge-bare-pr-line-format-require
title: 'Document the automerge bare pr: line format requirement'
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

`relay automerge` only recognizes a PLAIN `pr: <url>` line under `## Dev` when
deciding whether a ticket's linked PR has merged. It does NOT recognize a
`- pr: <url>` list-item bullet. Across at least 6 done tickets, reviewers
repeatedly had to hand-add a bare `pr:` line to a ticket before a merged PR
would auto-close it.

This is a doc task for a human to design and place: the `dev/code` context owns
the `pr:` convention and should explicitly state the bare-line requirement (a
plain `pr: <url>` under `## Dev`, not a `- pr:` bullet) so authors and reviewers
write the line in the form `automerge` actually parses.

## Context

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
