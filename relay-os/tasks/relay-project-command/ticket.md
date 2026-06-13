---
title: relay-project-command
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Build a project command in Relay. "Relay project" interviews a human about a project--goal, scope, constraints, acceptance criteria--through a short series of questions. 

From the answers, it creates an ordered set of draft tickets, one per each step. 

It can also seed the interview from an existing vision doc instead of starting from scratch (covers the deleted vision-to-plan ticket).

## Interview design (settled at design step)

Four beats, asked one at a time, recorded verbatim — borrowing the
`init/setup` interview discipline (short, the agent does the
decomposition, the human supplies only what the agent can't infer).

1. **Outcome (always first, never skipped):** "When this is done, what
   exists that doesn't today? How would you demo it?" → definition of
   done; the final ticket's review bar. Asked even when a doc exists,
   because confirming the concrete done-state is cheap and getting it
   wrong breaks the whole decomposition.
2. **Prior art (gap-filler, not a branch):** "Is there a doc — vision,
   spec, notes — with the details? Point me to it." The agent reads it
   and uses it to skip later *gaps* it genuinely fills (tech, deadlines,
   sequence). It does not let the agent skip Q1. Covers the deleted
   vision-to-plan path.
3. **Constraints:** "What's already fixed — deadlines, tech you've
   committed to, anything that mustn't change?" → ticket Context.
4. **Dependencies & sign-off:** "What has to happen before what? Include
   anything you're blocked on from outside (access, accounts, another
   team), who has to approve or hand off, and any order the agent
   couldn't guess from the goal." → the dependency graph + human
   assignees. The part only the human can supply.

**Then — review before scaffold (a required workflow step, not a
question):** the agent presents the proposed ordered ticket list (titles
+ one-liners) and asks "Anything here that shouldn't be a ticket, and
anything missing?" before creating any drafts. This is the real scope
and granularity gate — the human reacts to a concrete list rather than
predicting boundaries up front. Reuses the `init/setup`
`scan-and-generate` → `review-and-sign-off` pattern.

There is deliberately no standalone "what's out of scope?" question: the
review step bounds scope (over- and under-) more cheaply by reaction.
Cutting it is only safe *because* the review step is built — if that
step is dropped, reinstate a scope question.

## Context

Design rationale, the evaluation that produced this shape, and the open
implementation questions live on the blackboard.

