---
title: paperclip-report
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

I'm writing a google document describing my experience building the deliverability project using paperclip. The document is supposed to answer 3 questions: 

1. How long did the project take to complete using the service? 
2. What are the strengths of the service? 
3. What are the weaknesses of the service? 

1. The dns-checker project took me about 1.5 hours to build using paperclip. One of the faster services I've used. 

2. The strengths of the service: Immediately asks for company context (what is your mission? What does your company do?) Very easy and very valuable context block to add at the start, Separated work automatically by building issues, Agents get auto-assigned to open issues which lowered the time to finish the project, Issues get auto-flagged as blocking and the agents alerted me to what was needed on the human side to unblock the issue, I'm not sure it added value but it was really cool seeing the "CEO" agent run a "hiring process" to bring a differently specialized agent to start working on a task (2 engineers were spawned), Easy to follow the agent conversation with each other (CEO queried the engineer on the exact command line that needs to be run), The agent was able to take over some commands that I was supposed to run when I was confused (never had to leave the ui), ID's when issues are done and auto-completes them, Gives a final break down of what "done" was on a completed issues. Alerts you via an inbox when issues are done or need your attention. 

3. Weaknesses of the service: It was a little unclear on how to get issues moving again (I didn't take time reading up on the working of the service, but it was a little hard to figure out that I needed to reply in a comment and assign an "employee"), Replies took an inordinate amount of time to complete (I think the time was minimized because agents were working in parallel across issues, but single issues seemed to take a very long time to generate a response), 

## Context

This is the 8th in a series of tool-evaluation reports (see the other
`*-report` tasks: dust, conductor, cursor, backlog, linear-agent,
superset, openclaw).

- Title of the report: **Paperclip Report**.
- Save it into the **Relay Competition Tests** folder in Google Drive —
  folder ID `1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`, verified 2026-06-05:
  all 7 prior report Docs live directly in it. (Sibling tickets cite
  `0AI38XlSataDrUk9PVA`, but that is the My Drive root — the folder's
  parent, not the folder.)
- Call the project the **dns-checker project** throughout the doc
  (the Description also says "deliverability project" — use
  dns-checker consistently).
- Follow the general structure and tone of the other reports in that
  folder: read one (e.g. the Conductor Report) from Drive before
  drafting.

The Description above already contains the full answers to the three
questions — the draft step should shape that raw material into the doc,
not re-interview for it.
