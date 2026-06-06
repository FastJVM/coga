<!-- Exported from the Google Doc "Paperclip Report" (Relay Competition Tests), 2026-06-06.
     Source: https://docs.google.com/document/d/1Ql5XiCpyVsWsWrnY8hHGktVnQOJTJ_pVPNRx6PNXK-o -->

# **Paperclip Report**

This report reflects on my experience building the dns-checker project with Paperclip. It covers three questions: how long the project took, where the service was genuinely strong, and where it fell short. The short version is that Paperclip was fast — about an hour and a half, one of the quicker services in this series — and its org-chart approach (a CEO agent, auto-assigned employees, an inbox) automated away most of the coordination work, but slow single-issue response times and an unclear “how do I get this issue moving again” interaction added friction.

## **1\. How long did the project take?**

The dns-checker project took about 1.5 hours to build using Paperclip — one of the faster services I’ve used.

## **2\. Strengths of the service**

Paperclip’s strengths cluster around its company metaphor: it treats the project like an org, with context-gathering up front, issues as the unit of work, and agents as employees who assign, unblock, and report on themselves. The standout strengths:

* **Company context up front.** Paperclip immediately asks for company context — what is your mission? what does your company do? — a very easy and very valuable context block to add at the start.  
* **Automatic work separation.** It separated the work automatically by building issues.  
* **Auto-assigned agents.** Agents get auto-assigned to open issues, which lowered the time to finish the project.  
* **Blocking-issue awareness.** Issues get auto-flagged as blocking, and the agents alerted me to what was needed on the human side to unblock them.  
* **The “hiring process.”** I’m not sure it added value, but it was really cool seeing the “CEO” agent run a hiring process to bring in a differently specialized agent to start working on a task — two engineers were spawned.  
* **Legible agent-to-agent conversation.** It was easy to follow the agents’ conversations with each other — the CEO queried the engineer on the exact command line that needed to be run.  
* **Agents take over human commands.** When I was confused, the agent was able to take over some commands I was supposed to run — I never had to leave the UI.  
* **Knows when work is done.** It identifies when issues are done, auto-completes them, and gives a final breakdown of what “done” meant on a completed issue.  
* **Inbox alerts.** It alerts you via an inbox when issues are done or need your attention.

## **3\. Weaknesses of the service**

The complaints are few, and both trace to how the service communicates: it wasn’t always clear how to talk back to it, and when it talked back to me, it took its time. The friction points:

* **Unclear how to get issues moving again.** I didn’t take the time to read up on the workings of the service, but it was a little hard to figure out that I needed to reply in a comment and assign an “employee” to restart a stalled issue.  
* **Slow replies.** Replies took an inordinate amount of time to complete. I think the total time was minimized because agents were working in parallel across issues, but single issues seemed to take a very long time to generate a response.

## **Closing thought**

Paperclip leans all the way into the company metaphor — a CEO that hires, employees that get assigned, an inbox that pings you — and the result is one of the fastest builds in this series, with coordination work (splitting issues, assigning agents, flagging blockers, closing out done work) handled almost entirely by the service. The gap is in the conversational loop: stalled issues don’t make it obvious that a comment-plus-assignment is what restarts them, and individual replies are slow even when parallelism keeps the overall clock down. Smoothing that loop would make the org-chart approach close to frictionless.
