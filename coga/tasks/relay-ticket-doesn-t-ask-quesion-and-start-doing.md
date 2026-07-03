---
slug: relay-ticket-doesn-t-ask-quesion-and-start-doing
title: coga ticket doesn't ask questions and starts doing the work
status: done
mode: agent
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
---

## Description

Bug in guided ticket authoring: `coga ticket` (the `bootstrap/ticket`
interview skill) is supposed to interview the human — one question at a time,
then edit the ticket — but instead the agent skips the questions and starts
doing the work directly. Reproduce with `coga ticket "<some title>"`, find why
the interview framing doesn't hold (the skill body, how the authoring prompt
is composed/passed as system context vs first message, or the greet-first
`kickoff` token), and fix the skill/prompt so the session reliably interviews
first and only ever edits the ticket — never implements it. Add or adjust
whatever test/fixture coverage exists for prompt composition of the authoring
path. (Ticket predates the rename — "relay ticket" means `coga ticket`.)

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
