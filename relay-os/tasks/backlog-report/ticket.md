---
title: backlog-report
status: done
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
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

This is a google doc describing my experience using backlog.md. The doc should be titled "Backlog Report". It should answer 3 questions: 

1. How long did the project take me while using the service? 
2. What are the strengths of the service?
3. What are the weaknesses of the service? 

Answers:

1. The deliverability project took me 2.5 hours to complete using backlog, against the 2-hour baseline from building the same project on Conductor. The 30 minutes over were a result of getting used to the cli and because I was tightening up my deliverability project a bit. 

2. The strengths of the service: Expansive README on how to use the CLI with a natural flow. Quick description of what Backlog is and immediately gets into how to create your first task, Ability to add many elements to the task at creation (ie description, Definition of done, acceptance criterias) can all be built at the cli task creation, Onboarding tasks (5 to be exact) that are meant to get you used to using the service (creating your first task, launching their board, editing a task within the Kanban board) the onboarding tasks prepared me to immediately start using the cli. 

3. The weaknesses of the service: The Kanban board gives the appearance of organization when there aren't many tasks, but once the board gets extremely filled it becomes more overwhelming than organized (same problem we saw with Pylon's task page), Tasks are markdown files on disk but you can't edit them from the file itself — you HAVE to edit through the cli or through the Kanban board, Acceptance criteria was the main thing I used to explain a definition of done. They also had a definition of done but it seemed like redundancy and I didn't use it one time through all of the deliverability tasks. 

## Context

- This is one of a series of tool-evaluation Google Docs (Dust Report, Conductor Report, this one). Match the structure of the prior reports: intro verdict, three numbered sections, closing thought, bolded bullet leads.
- Target Drive folder: "Relay Competition Tests" (`1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`) — same folder as the "Dust Report" and "Conductor Report" docs, so the series lands side by side. (Preflight 2026-06-04: the reports moved here from parent `0AI38XlSataDrUk9PVA`; Zach confirmed the subfolder is the target.)
- The doc's audience may not know Pylon — make the Kanban-board point standalone (looks organized when sparse, overwhelming when full) rather than leaning on the Pylon comparison.
- The 2-hour baseline is the same deliverability project built on Conductor (see the conductor-report task).
