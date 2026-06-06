<!-- Exported from the Google Doc "Linear Agent Report" (Relay Competition Tests), 2026-06-06.
     Source: https://docs.google.com/document/d/1bGjN_EuKrKlt41FqPNVG8UfhsJDqaHQTuHlbO4KU3oM -->

# **Linear Agent Report**

This report reflects on my experience building a project with Linear Agent. It covers three questions: how long the project took, where the service was genuinely strong, and where it fell short. The short version is that Linear's issue model made individual tasks easy to edit and easy to finish, but the agent's planning dropped explicitly requested testing work — and at 3.5 hours, this was one of the services that took me the longest, against 2 hours on Dust, 2 hours on Conductor, and 2.5 hours on Backlog.

## **1\. How long did the project take?**

The deliverability project took 3.5 hours end-to-end using Linear Agent — one of the longest in this series. The same project came in at 2 hours on Dust, 2 hours on Conductor, and 2.5 hours on Backlog.

## **2\. Strengths of the service**

Linear's strengths come from its issue model: work breaks down into units that are easy to edit and easy to reason about. The standout strengths:

* **Linear issues double as tickets.** Issues served as the project's tickets, so they were easy to edit on the fly.  
* **Per-issue breakdown makes "done" legible.** When things are broken up by issue, it's easy to know what done looks like — for just that task, not the whole project — and to understand which part is ready to be committed.

## **3\. Weaknesses of the service**

The weaknesses show up in the agent's planning and in course-correcting after the fact. The main friction points:

* **The task list looked complete but wasn't.** At first, Linear Agent produced what seemed like a well-organized task list that addressed the gotchas with Playwright automations — but it entirely left out the frontend testing process for the selectors.  
* **Hard to know where edits belong.** Once all of the issues were created, it was very difficult to know exactly where I needed to edit tasks.  
* **Explicit instructions got dropped.** I gave the agent very clear instructions to test Playwright selectors exhaustively before the dry-run, and it completely left that process out. Instead, I was left under the impression the project was complete — and only then discovered how much testing was still ahead of me. The most important parts of the Playwright flow (fetchnewestmessage, fetch raw source, and send reply) all went untested. I ran out of time.  
* **No workflows for specific tasks.** The lack of workflows for specific tasks results in half-done work — and headaches when you think the project is successfully built.

## **Closing thought**

Linear Agent's best quality is the issue model itself: tickets that are easy to edit, and a per-issue definition of done that tells you what's finished and what's ready to commit. The problem is what the agent did with it — a plan that looked organized but silently dropped explicitly requested selector testing, an issue pile that resisted course-correction, and a project that presented as complete at 3.5 hours while the core Playwright flow (fetchnewestmessage, fetch raw source, send reply) was still untested. Good bones for tracking work; not yet trustworthy for planning it.
