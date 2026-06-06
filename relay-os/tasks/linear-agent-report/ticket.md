---
title: linear-agent-report
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

This is a Google doc explaining my experience using linear-agent for my deliverability build project. It's answers 3 questions: 

1. How long did the project take using the service?
2. What were the strengths of the service?
3. What were the weaknesses of the service?

Answers:

1. End-to-end the project took me 3.5 hours (one of the services that took me the longest to finish the project)

2. The strengths of the service: Linear issues served as "tickets" so they were easy to edit on the fly, When things are broken up by issue on Linear it makes it easy to know what done looks like (for just that task, not the whole 'project) and helps you understand which part is ready to be committed

3. The weaknesses of the service: At first, I thought Linear Agent produced a well-organized task list that addressed the gotchas with Playwright automations...not only did it entirely leave out the frontend testing process for the selectors, but once all of the issues were created, it made it very difficult to know exactly where I needed to edit tasks, I gave the agent very clear instructions to test Playwright selectors exhaustively before the dry-run but it completely left that process out...all of the testing got pushed to the backend when it should have been ready, Again the lack of workflows for specific tasks results in half-done work and headaches when you think the project is successfully built. The most important parts of the Playwright flow (fetchnewestmessage, fetch raw source, and send reply) all went untested. I ran out of time. 

## Context

- The title of this document should be "Linear Agent Report".
- Target Drive folder: "Relay Competition Tests" (`1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`) — same folder as the Dust, Conductor, and Backlog Report docs, so the series lands side by side.
- This is one of a series of tool-evaluation Google Docs. Match the structure of the prior reports: intro verdict, three numbered sections, closing thought, bolded bullet leads.
- Time baselines for the same deliverability project on other services: Dust 2 hours, Conductor 2 hours, Backlog 2.5 hours — these are the comparison points behind "3.5 hours was one of the longest" (see the conductor-report and backlog-report tasks).
- Keep the Playwright flow terms (fetchnewestmessage, fetch raw source, send reply, dry-run) as-is in the doc — no need to gloss them for the reader.