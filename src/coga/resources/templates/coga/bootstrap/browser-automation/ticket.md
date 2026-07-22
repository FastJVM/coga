---
title: Build a browser automation
assignee: claude
contexts:
  - browser/api-first
skills:
  - browser/build-automation
---

## Description

Stateless entry point for turning a described browser task into a concrete
automation ticket. Run `coga launch bootstrap/browser-automation`, describe the
task when the agent asks, and let the `browser/build-automation` skill choose
the implementation path and matching workflow handoffs.

## Context

This bootstrap target is orchestration, not standing work. It has no status,
workflow, step, owner, blackboard, or audit lifecycle, and launching it does not
create a generic browser task. Only the concrete automation ticket created
after the task is understood becomes durable Coga work.

`browser/build-automation` owns routing and ticket creation.
`browser/playwright` is the separate lower-level browser runner and is attached
to the concrete ticket only when browser execution is actually required.
