---
title: Measure Relay prompt scope and agent precision
status: draft
mode: interactive
owner: nick
human: nick
agent: codex
assignee: codex
contexts:
- relay/principles
- relay/codebase
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    assignee: owner
step: 1 (implement)
---

## Description

Add a lightweight way to measure Relay's prompt scope and compare the practical
cost/precision tradeoff against an ordinary agent session.

The goal is not to prove a universal benchmark claim. The useful claim is
narrower: Relay should spend tokens on explicit task context, workflow state,
and blackboard continuity only when those tokens reduce rediscovery, wrong
turns, human correction, or failed handoffs. Build enough measurement to catch
prompt bloat and to support an honest internal answer about when Relay is
cheaper or more precise.

## Context

This came from the question: does Relay reduce token/cost and increase precision
versus a normal agent? The current answer is "precision likely improves; token
cost depends on whether scoped context avoids enough rediscovery and rework."

Important nuance: Relay's intended model is not "include every context in every
launch." A ticket should select the relevant contexts, and the workflow step
should select the relevant skill. Today, this repo may still include broad or
all canonical Relay context as a temporary product-stage baseline. Treat that
as something to measure and control, not as the final design.

Do not build a heavy academic benchmark first. Prefer a small measurement/report
surface that can run against real Relay tasks and answer:

- How many approximate tokens come from each composed prompt layer?
- Which contexts and skills were included, and why?
- Is the blackboard growing large enough to hurt launch quality?
- How many tool calls/turns/human corrections were needed before completion?
- Could a cold relaunch continue correctly from ticket + blackboard + selected
  contexts alone?

## Acceptance criteria

- [ ] Add or document a lightweight prompt-scope report for composed launches,
      split by layer: base rules, repo context, ticket contexts, workflow skill,
      blackboard, and ticket body.
- [ ] The report names the exact context and skill refs included for a task.
- [ ] Token counting is dependency-light and good enough for comparison; exact
      tokenizer parity is not required unless the implementation already has a
      local tokenizer available.
- [ ] Capture the current broad/all-context behavior as a temporary baseline and
      document the intended scoped-context direction.
- [ ] Define a small real-task comparison protocol: Relay launch versus normal
      agent session, tracking total turns/tool calls, human corrections, PR
      review misunderstandings, and relaunch continuity.
- [ ] Add focused tests if the implementation touches `compose.py`, launch
      output, validation, or prompt-surface behavior.
- [ ] Do not claim Relay is always cheaper. The output should distinguish
      precision, up-front prompt size, total task cost, and avoided rework.

## Out of scope

- Paper-grade benchmarking.
- Claims about all repos or all agent models.
- A server, database, telemetry daemon, or opaque usage tracker.
- Replacing ticket-selected contexts with a global context dump as the desired
  long-term behavior.
