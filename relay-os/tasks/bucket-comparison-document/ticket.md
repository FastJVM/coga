---
title: bucket-comparison-document
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
---

## Description

I'm creating a google doc that categorizing each of the tools that I've used into 3 buckets:

1. Those that try and replace the agent: Linear Agent, Dust, Cursor

a. This never worked well. Agents that these services created always gave the pre-feeling that they were doing a wonderful job at creating the steps to a task. As the agents moved through tasks, still they feigned being comprehensive at task completion. My experience with every one of these "agent replacements" was that they labelled a project as done before it was actually done. Testing and failures that should have been resolved early in the project were instead pushed to the point of when I thought the project was done. Without workflows that coached these proprietary agents on the correct way to structure a task, time and time again, failure management was injected into the situation at the worst possible time. 

2. Those that are overlays on top of the agent: Superset, Backlog, Conductor

a. These were essentially pretty wrappers for Claude Code. Services in this bucket structured the project in a much more efficient way than the agent replacement bucket, but I came to the realization that the reason for proper project structure (addressing failures before a built project) had nothing to do with these overlays. The credit should be given to Claude Code. 

3. Autonomous: Paperclip, OpenClaw 

a. These tools provided the best testing result, but also with some variance. OpenClaw completed the project perfectly on the first try, but then I reset the state and turned off Claude's memory and chat reference settings (which probably over-constrained it) and it was not able to complete the project the second time. In fact, the autonomous nature of the tool became a hindrance as it went through 35 failed cycles of trying to find proper Playwright selectors before I had to manually shut it off. Paperclip provided the best project outcome. It tested the selectors at the right time, it handled issues in parallel making for a much faster workable automation, and flagged issues as blocking. In comparison, Paperclip needed less human intervention than any other tool while producing the best (and fastest) project outcome. 

--After the tool categorization, I am to answer the question of "Is Relay Better?"--

Relay isn't trying to replace agents. My testing showed that that was consistently a losing game. Claude Code was always better at structuring projects than the agent replacements. What Relay offers is opportunities for the human to identify better ways of completing a task, and guide the agent in that direction. Because every part of Relay's system is viewable and editable, it allows for the human to fill gaps and remove the variance that I saw in bucket 3. When a human finds a better way to guide AI through a task, not only does it increase productivity for the human that found it, but that value (a new skill, a new context block, a new workflow) can then be reused by other teammates. I think Relay is better than other services because there's no black box. No unseen project structure that can lead to inconsistent outcomes when AI alone is asked to build the same project twice. Keeping the human in the loop...in every loop...gives the opportunity to attach workflows that largely remove variance. 

## Context
The agent running this task should create a short and concise title that's appropriate based on the content
The document is to be saved to the Relay Wishlist/ Bucket Comparison folder on my G-Drive — that is the literal name of a single folder (the slash is part of the title, not a path separator)
Treat the Description as verbatim source material: the tool names and anecdotes are the author's own assertions — do not soften, embellish, or fact-check them into different claims
This is an internal doc — write for teammates, not external readers
For the first draft, produce two versions so the human can compare: one structured around a comparison table across tools/buckets, one as pure narrative sections. The human picks the structure in the revise loop
