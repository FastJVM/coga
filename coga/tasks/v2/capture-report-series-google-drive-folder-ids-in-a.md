---
slug: v2/capture-report-series-google-drive-folder-ids-in-a
title: Capture report-series Google Drive folder IDs in a context
status: draft
mode: llm
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

Created by a Dream run (gap finding F2). Needs human design judgment —
**do not assume the answer is "add a context."**

The report doc series re-resolves the same Google Drive folder IDs in every
ticket, and several got them wrong the same way. Across the eight `*-report`
tickets plus `relay-additions` and `bucket-comparison-document`, the same
folder facts were re-discovered each time:

- **Relay Competition Tests** (target for per-tool `*-report` docs):
  `1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`.
- The trap: `0AI38XlSataDrUk9PVA` is the **My Drive root** (the folder's
  parent), wrongly cited as the target in the early dust/conductor/superset
  tickets.
- **Relay Wishlist/ Bucket Comparison** (wishlist / bucket-comparison docs):
  `1W3cjsWsmMn_OysmjTYIuaoeEF9RRobat`. The slash and trailing space are part
  of the single folder's literal name — not a nested path.

Open question for the human: this is **project data**, not a Relay mechanism,
so a context (`relay-os/contexts/docs/drive-folders/SKILL.md`?) is one option,
but folder IDs may belong in config or a doc-series skill instead — or may not
be worth durably capturing at all. The repeated wrong-answer cost is the
reason to consider it; the decision is yours.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
