---
slug: unblock-rewind
title: unblock-rewind
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

There needs to be a cleaner way to rewind the ticket. Sometimes the evaluator uncovers legitimate design changes for which you'll want to go through the implementation stage again. 

Now, the only way you can do it is by launching and immediately exiting the REPL to put the ticket back in_progress. 

You should be able to rewind an active ticket (or really a ticket in any state.)

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
