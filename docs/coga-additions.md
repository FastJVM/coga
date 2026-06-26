<!-- Exported from the Google Doc "Coga Additions" (Coga Wishlist/ Bucket Comparison), 2026-06-06.
     Source: https://docs.google.com/document/d/17dZmEwnjLpKpv9lIpr2hFydcKGK0OhQlJR-vQo9_Qc8 -->

# **Coga Additions**

This document distills hands-on evaluations of eight tools — **Linear Agent, Conductor, Dust, Superset, Backlog.md, OpenClaw, Paperclip, and Cursor** — into the features I'd genuinely like to see in Coga. Not every tool contributed a standalone item: the eight are what was evaluated, and the list below is what's worth keeping. The per-tool detail lives in the competition reports; this is a forward-looking wishlist, not a summary of them.

## **1\. Conversation & workspace UI**

*Seeing the agent's work where you already are.*

1. **All-in-one workspace (Conductor)** — The agent conversation, a built-in terminal, and a GitHub access box all live in one place. You never have to leave the surface where the agent is working to run a command or check the repo. In Coga: a launch surface where the session, a terminal, and gh access sit together, instead of being spread across windows.  
2. **Clickable agent work boxes (multiple services)** — When tools are called, things are downloaded, or runs are started, a collapsible box appears in the conversation; click into it and you see exactly the work the agent is doing. In Coga: the same mid-run legibility, rather than reconstructing what happened afterward from the blackboard or log.  
3. **Live file diffs in the UI (Conductor, Superset, Cursor)** — All file additions and deletions for a given task are visible as you go, so you know exactly what is being committed and which branch you're on. In Coga: a per-task view of pending changes and the current branch, so review can start before the PR exists.  
4. **Tools run directly in the conversation (OpenClaw)** — No need to open another terminal window; the agent conversation runs tool commands for you when asked. In Coga: ask for a command inside the session and it executes right there.

## **2\. From vision to running work**

*Planning that turns into parallel execution.*

1. **Vision to task list (Paperclip, among others)** — You explain a project and it gets turned into logical, step-by-step tasks. Several services did this; Paperclip's implementation was the coolest. In Coga: describe a project once and get draft tickets out of it — Descriptions and Context written — ready for human review, rather than hand-authoring each ticket.  
2. **Automatic agent assignment (Paperclip)** — When a project description becomes a task list, agents automatically get assigned to each open issue and work in parallel. In Coga: created tickets that launch their own agents, instead of a human running a launch once per task.

## **3\. Task lifecycle automation**

*Fewer manual state transitions.*

1. **Auto-branch after merge (Conductor)** — Once a task was completed and merged, a new branch was automatically created for you. In Coga: the next unit of work starts with its branch already in place — one less manual git step between tasks.  
2. **Auto-completion of tasks (Paperclip)** — Agents identify when an issue is "done" and automatically move it into a done state. In Coga: tasks that move themselves to done when the work is verifiably finished, rather than waiting on a manual pass.

## **4\. Status visibility & unblocking**

*Knowing what needs you.*

1. **Task inbox (Paperclip)** — An inbox showing which tasks are completed, which need your attention, and which are blocked by other dependencies. In Coga: one cross-task view of done / needs-you / blocked, instead of reading per-task tickets or scrolling channel history.  
2. **Blocking-issue identification (Paperclip)** — Issues get flagged as blocked, and the agent tells you exactly what's needed of you to unblock them. In Coga: blocked tasks that surface the precise unblock ask, as a queue a human can work through.  
3. **Agent-to-agent conversation (Paperclip)** — Agents queried other agents, so you knew exactly which agent would provide unblocking details or which issue to keep an eye on. In Coga: agents on sibling tasks asking each other directly, instead of routing every cross-task question through the human.

## **5\. CLI & onboarding**

*The first-hour experience.*

1. **CLI onboarding document (Backlog.md)** — An easy-to-read CLI onboarding document with a flow that gets you immediately used to the CLI. In Coga: a first-read walkthrough that takes a new user through creating, launching, and advancing a toy task.  
2. **Extended CLI task creation (Backlog.md)** — Tasks can carry full detail from the point of creation (-d "description", \-c "context block", \--workflow to attach one), so tickets are ready to launch the moment they're created. In Coga: creation flags for description, context, and workflow, so a fully specified ticket comes out of one command with no post-creation editing pass.  
3. **Onboarding tasks (Backlog.md)** — Easy-to-follow initial tasks a new user can do to start getting used to the CLI. In Coga: a fresh repo seeded with a few starter tasks that teach the loop by doing it.  
4. **Permission-free flow by default (Superset)** — Defaulted to dangerously skipping permissions: an entire task flowed end-to-end without having to click yes at all. In Coga: launches that default to non-interactive permission handling, so a run isn't punctuated by approval clicks.

*What to build first is deliberately out of scope here — a follow-up will turn these items into ticket-ready specs once the team has reacted.*
