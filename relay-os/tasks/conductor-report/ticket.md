---
title: conductor-report
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

I'm creating a google document for my experience using Conductor. The three main questions that should be answered: 

1. How long did the project take to build using this service? 
2. What were the strengths of the program? 
3. What are the weaknesses of the program? 

1. The project took me 2 hours to complete, end to end. It worked its way through the Playwright selector problems twice as fast as Dust. 

2. The strengths of the service are: Being able to create PR's directly in the ui (amazing for someone who's not very proficient with gh), offered full accessibility to Opus (where Dust only offered Sonnet), It was very good at recognizing that something had been merged so it could create and move you to a new branch, auto-creates new branch and git worktree for new task, Having a built in terminal directly in the UI made testing seamless. It could give me something to run, the terminal auto-connected to the current branch, and I was able to quickly test from there, It made keeping branches and PR's organized very easy, There was a time when I wasn't sure if a PR had been merged (so I could start on a new task) and I was able to check right there in the UI (it recognized and allowed me to merge as well as moving me to a new branch and task), 

3. The weaknesses of the service are: End state of the project wasn't the real end state (there was further testing required when the process was supposed to be fully live), The lack of robust workflows again pushed a lot of the testing to the backend of the project (when it should have been ready to run live), It wasn't as granular as Dust was so I think that's a big part of why so much testing was pushed to the backend, Not a lot of complaints with this service other than the usual lack of workflows making the Playwright selector process very tedious. 

## Context

