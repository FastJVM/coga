---
slug: recurring/watchdog-example
title: Watchdog recovery example
status: paused
owner: marc
human: marc
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
step: 1 (execute)
secrets: null
---

## Description

Demonstrate recovery of an interrupted recurring run. Preserve its findings
and finish the recorded step when explicitly resumed.

## Context

The watchdog pause is identified by its system actor in the repo audit log.
An ordinary scan must retain this period even after the next weekly firing.

<!-- coga:blackboard -->

## Findings

The scan completed before the timeout. These findings still need disposition;
resume this step or route them into a durable follow-up before closing the run.
