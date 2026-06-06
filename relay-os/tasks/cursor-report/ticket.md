---
title: cursor-report
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

I'm creating a google doc explaining my experience using cursor to build my deliverability project. These are the questions it will answer: 

1. How long did the project take while using the service?
2. What were the strengths of the service?
3. What were the weaknesses of the service?

1. The project took me 2.5 hours and I still wasn't able to finish it
2. The strengths of the service: Connects directly to GitHub and gives easy visibility for which branch you are on, I like the drop-down of agents you can select (frontier models all available on the pro plan), Builds out task list for you when you describe the project, Auto-creates and switches branches for you as it moves through the different tasks (separates commits into reasonable blocks), There's a default model selection where you can set the model that carries out work across all projects, Creates clickable boxes in the agent conversation that allows you to click into work that it did (I could see that Playwright got downloaded and which version)
3. The weaknesses of the service: The built-in terminal was confusing. I didn't know what I could run there and what I couldn't. In Conductor, I could run tests directly in their built-in terminal but for Cursor it wouldn't let me run the auth login to save my Gmail login (I had to run it in my computer's terminal), Same issues with needing to run tests on the backend to fix the Playwright selectors (lack of workflow upfront seems to push fixing the selectors to when you think you're ready to test the project), Project was said to be done but the live-run of actually sending the email resulted in more tests to find the send button

## Context
Title of the document is Cursor Report
The document should be saved to the Relay Competition Tests in my drive
Mirror the section structure of the Conductor Report doc in the same folder for series consistency
Final state of the project: the email never ended up sending — the project was left unfinished after 2.5 hours
