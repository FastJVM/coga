---
title: dust-report
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

Create a Google doc explaining the Dust experience. The main questions that should be answered are:

1. How long did the project take you to complete?
2. What were the strengths of the service? 
3. What were the weaknesses of the service?

The title of the document should be Dust Report

The total time for building the project was ~3 hours. I wanted to finish, but 2 hours was supposed to be my cutoff. 

Strengths of the service: The agent turned a step by step vision of the project into a comprehensive task list, Pods act as directories: agents build context here and it's easy to pull in files that better explain a task, I thought it was really cool that tasks auto-mark as done. I would share messages from my terminal explaining that a step of the project was done and Dust would auto-mark it as complete, It did create tasks very granularly...it walked me through testing every aspect of the project before moving on (and would provide next recommendations that are easily copied when a batch of code didn't work), It was actually a great learning experience to be able to build my own directory with its code recommendations

Weaknesses of the service: I didn't find a way that let you click into the tasks and edit them directly (It seemed as if all of that work needed to be done by the agent, For a complex task (such as finding the correct Playwright selectors to drive a project) it was an exhausting process...I had to work on a trial and error basis with code deletions and additions, The absence of workflows (which better explains the previous weakness) made for a very inefficient work process, I think it created more complexity than it needed to: Backlog and linear agent were both able to finish the deliverability project in 2 hours...but the trial and error process (which I think is a product of having to build your own directory) resulted in a much longer process, When you want to add things that the agent learned through the process: you had to be very specific or else it seemed to batch grab a lot of things that didn't matter. 

## Context

