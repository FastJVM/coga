---
title: relay-additions
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

Produce a Google Doc titled "Relay Additions" describing which aspects of each evaluated tool I'd genuinely like to have as part of Relay. The information comes from my experience using: Linear Agent, Conductor, Dust, Superset, Backlog.md, OpenClaw, Paperclip, and Cursor (not in that order).

The additions:

a. Conductor's UI: Agent conversation, built-in terminal, and gh access box all in one 	place
b. Conductor's flow: Auto-created a new branch for you once a task was completed and merged 
c. Vision to task list: This was part of multiple services, the coolest one being Paperclip. You explained a project and it turned it into logical step by step tasks 
d. Automatic agent assignment (Paperclip): When a project description gets turned into a task list, agents automatically get assigned to each open issue (working in parallel)
e. Clickable agent work boxes in the conversation (Multiple services): When tools are called, things are downloaded,  Runs are started, a box shows up in the conversation as a drop down that you can click into and see exactly the work the agent is doing 
f. CLI onboarding document (Backlog): Backlog had an easy to read cli onboarding document that had a flow which got you immediately used to using their CLI
g. Extended CLI task creation (Backlog): You could create tasks with a lot of detail from the point of creation (-d "description", -c "context block", -workflow "attach a workflow") Tickets are ready to launch once they're created 
h. Onboarding tasks (Backlog): Easy to follow initial tasks that a user can do to start getting used to the CLI
i. Defaulted to dangerously skip permissions (Superset): Flowed entirely through a task without having to click yes at all 
j. Live file diffs right in the ui (A few services: Conductor, Superset, Cursor): You can see all of your file additions and deletions for a given task (so you know exactly what is being committed and which branch you are on)
k. Tools run directly in the initial conversation (OpenClaw): No need to open another terminal window. The agent conversation runs tool commands for you when asked 
l. Auto-completion of tasks (Paperclip): Agents were able to identify when as issue was "done" and automatically moved them into a done state. 
m. (Paperclip): Some sort of inbox so you can see which tasks are completed, which need your attention, (which are blocked by other dependencies?)
n. Blocking-issue ID (Paperclip): Issues get flagged as blocked and the agent tells you exactly what's needed of you to unblock them. 
o. Agent-to-agent conversation (Paperclip): In Paperclip, agents queried others so you knew exactly which agent would provide you with unblocking details or which issue to keep an eye on




## Context

- Doc title: "Relay Additions". Audience: the Relay team / Nico — readers know Relay but not the evaluated tools, so each item needs enough explanation to stand alone as a feature proposal.
- Upload to the existing Drive folder "Relay Wishlist/ Bucket Comparison" (ID `1W3cjsWsmMn_OysmjTYIuaoeEF9RRobat`). Not the "Relay Competition Tests" folder.
- Structure: the agent proposes a categorization of the items (they cluster naturally — e.g. UI/conversation, task lifecycle/automation, CLI/onboarding, permissions, agent-to-agent) and the human approves or adjusts it in the revise loop.
- The Description already contains the full content (items a–o) — the draft step should shape that raw material into the doc, not re-interview for it.
- The item list is final. The eight tools named are everything evaluated; not every tool contributed a standalone item, and that's intentional.
- The per-tool detail behind these items lives in the sibling `*-report` tasks (`relay-os/tasks/conductor-report`, `paperclip-report`, …) and their Docs in the "Relay Competition Tests" Drive folder — useful corroboration, not a dependency. This doc is a forward-looking wishlist, not a summary of the reports.
- A follow-up ticket (relay-additions-spec) will turn these items into ticket-seeding specs after this doc ships and the team has reacted. Out of scope here.
