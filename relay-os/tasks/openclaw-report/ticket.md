---
title: openclaw-report
status: done
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: docs/create-google-doc
  steps:
  - name: preflight
    skills: []
    assignee: agent
  - name: draft
    skills: []
    assignee: agent
  - name: revise
    skills: []
    assignee: agent
  - name: sign-off
    skills: []
    assignee: owner
---

## Description

I'm creating a google doc describing my experience using OpenClaw to build the deliverability project. 

The document needs to answer 3 questions: 

1. How long did the project take me to build using the service?
2. What were the strengths of the service? 
3. What were the weaknesses of the service? 

1. The project took me two hours to build using OpenClaw and I still was unable to finish
2. The strengths of the service: OpenClaw can run tools directly in the conversation meaning I rarely had to leave it's UI (No opening terminals to run commands), It does run auto-retries better than most other services when it knows it hadn't found the correct selector yet, It provided a good natural flow of agent (automated)-->Handoff to human (for a command you could run directly in the running chat)-->Then back to agent again
3. The weaknesses of the service: The setup is intimidating and not very explanatory (I had to consult Claude with which options to choose at setup), It told me repeatedly that it would be notified when a task finished but it wasn't (I had to keep prompting it when, say, the login of Gmail had been saved), After the state reset the service completely failed to complete the dns-checker project. It was stuck in a continuous loop of selecting the wrong emails (selected a google security email repeatedly, selected playstation invoices repeatedly, etc.), I had to interfere with the loop to stop it after 30+ cycles. It kept telling me, authoritatively, it had the answer to fix the incorrect selection but would start another never-ending loop of selecting the wrong emails. OpenClaw tried to be automated on a task that it should have involved the human in long before.

## Context

This is the 7th in a series of tool-evaluation reports (see the other
`*-report` tasks: dust, conductor, cursor, backlog, linear-agent, superset).

- Title of the report: **OpenClaw Report**.
- Save it into the **Relay Competition Tests** folder in Google Drive —
  the same folder the prior report Docs live in (`parentId`
  `0AI38XlSataDrUk9PVA`, confirmed on the conductor-report task).
- Follow the basic structure of the **Conductor Report** document (and the
  other reports in that folder): read it from Drive before drafting.

The Description above already contains the full answers to the three
questions — the draft step should shape that raw material into the doc,
not re-interview for it.
