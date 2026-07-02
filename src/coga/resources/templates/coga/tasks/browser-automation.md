---
slug: browser-automation
title: Browser automation
status: draft
mode: llm
owner: new-user
human: new-user
agent: claude
assignee: claude
contexts:
- browser/api-first
skills: []
workflow:
  name: browser/build-automation
  steps:
  - name: understand-task
    skills: []
    assignee: agent
  - name: choose-approach
    skills: []
    assignee: agent
  - name: triage-tier
    skills: []
    assignee: agent
  - name: emit-and-launch
    skills: []
    assignee: agent
step: 1 (understand-task)
---

## Description

Turn a described browser task into a working Playwright automation. This ticket runs the build-automation methodology end to end, then emits and launches a concrete tier-bound automation ticket that executes it. The plug-and-play entry point: launch it, give it the task, get a working automation.

## Context

Generalizes browser-automation creation so anyone can go from a plain-English task to a working automation with no bespoke setup. The methodology lives in the build-automation workflow; the how (CLI commands, snapshot-first, fail-loud) in browser/playwright; the approach gate and DOM standard in browser/api-first and browser/dom-backed. Output is one of the three run tiers (fully-automated / human-verify / human-only) wired to the discovered plan. Provide the task as the first turn after launch (coga launch takes a slug, not free text, so the agent takes the task at start).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
