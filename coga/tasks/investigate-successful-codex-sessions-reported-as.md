---
title: Investigate successful Codex sessions reported as failed
status: draft
owner: nicktoper
workflow: null
---

## Description

Determine why apparently successful Codex sessions receive failed status, and correct classification only where lifecycle and process evidence prove it wrong. A success-looking final message alone is not proof of successful completion.

Reproduce a reported example and capture the launch target, process exit code, supervisor outcome, done sentinel, and expected workflow progress. Cover ordinary tickets and bootstrap or stateless sessions; preserve real failures, interrupts, timeouts, and no-progress failures. Add a regression for the confirmed mechanism and document the status meaning. The suspected Codex exit code at shutdown is a hypothesis, not an established cause.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
