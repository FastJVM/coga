---
slug: relay-build
title: relay-build
status: active
autonomy: interactive
owner: new-user
human: new-user
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: build/onboarding
  steps:
  - name: gather-and-spec
    skills: []
    assignee: agent
  - name: generate-batch
    skills: []
    assignee: agent
step: 1 (gather-and-spec)
---

## Description

First-run onboarding. One scripted question — "What do you want to build?" —
then an agent-led chat draws out the rest, ending in a short vision you sign off
on and a flat batch of draft tickets you can immediately `relay launch`. Empty
repos only; no scan. Launching this ticket starts the chat.

## Context

Empty until the `gather-and-spec` step runs at first launch — the agreed vision
is written to `relay-os/contexts/product/vision/SKILL.md` and raw intake notes
stay on the blackboard.

<!-- relay:blackboard -->

The blackboard is a notepad for the human and agent to use while working
through this task. For onboarding it holds the raw intake from the
gather-and-spec chat — the working notes behind the vision, which stay here
rather than in the durable `contexts/product/vision` doc.
