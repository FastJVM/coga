---
title: Document parent-orchestrates-child-script-tasks pattern in relay/patterns
status: draft
mode: interactive
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

Gap finding from the Dream 2026-W24 run (knowledge scan): the
parent-orchestrates-child-script-tasks shape that Dream uses is the canonical
template for multi-step housekeeping loops, but no context or pattern
documents it. Future maintenance-task authors re-derive it ad hoc.

Proposed: add a section to `relay/patterns` describing the shape —

- a parent task body acts as the dispatch contract (ordered phases; a failed
  phase is recorded, never replaced inline);
- deterministic phases run as child `mode: script` tasks, each with a
  one-step workflow referencing a worker skill (`relay draft … --mode script
  --workflow <ns>/<worker>` then `relay launch`);
- each worker reads its `## Known Skill Contract`, stays inside its declared
  scope, and appends a `## Dream Skill: <name>`-style result section to the
  child task's blackboard;
- the parent summarizes each child result into its own blackboard and routes
  findings to durable artifacts (PRs, draft tickets, markers) in a final
  disposition phase;
- judgment phases are delegated to subagents with prompt-only scan skills,
  returning classified findings only.

Design judgment needed on where it lives (`relay/patterns` vs
`relay/architecture`), how generic vs Dream-specific the writeup should be,
and whether the live + packaged copies both carry it.

## Context
