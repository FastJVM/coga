---
title: Absorb Compound Engineering leaf skills as a Coga method library
status: draft
owner: nicktoper
workflow: null
---

## Description

Study, then decide, whether Coga should absorb Compound Engineering's leaf skills (ce-brainstorm, ce-plan, ce-code-review, ce-simplify-code, ce-debug, ce-doc-review, ce-pov, ce-strategy, ce-prototype, ce-polish) through the existing managed-skill manifest and a workflow that uses them as step skills — while explicitly not absorbing CE's loop layer (lfg, ce-work's run controller, ce-compound, ce-compound-refresh, ce-sweep), which duplicates the ticket lifecycle or contradicts memory-via-PR. Parked: this is a design study to be picked up later, not an approved implementation. The competitive finding behind it (2026-09-16): CE is a method library that runs inside the agent (35 skills, 14 hosts, MIT, no telemetry); Coga is a runtime that runs outside the agent and spawns it. Where Coga leads CE it is all runtime (ticket lifecycle, enforced per-step human ownership, blocker parks and the queue continues, scheduling, deterministic context delivery, mid-task rewind); where CE leads it is everything that is not the runtime (vendor breadth, method breadth, non-code and front-of-loop skills, install path, audience). ce-work's Return-to-Caller mode is designed to hand its remaining gates to an outer orchestrator, i.e. to something like Coga. Absorbing the leaves fills the acknowledged method-breadth gap without touching what is distinctive; absorbing the loop would make Coga a worse CE.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
