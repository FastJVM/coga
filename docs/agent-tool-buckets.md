# Agent Tool Buckets — Is Coga Better?

> Source: [Google Doc](https://docs.google.com/document/d/1IbQ4qh17rK2SZNFIGrMZVkvc_qSSHHiAFvANs7a60eU/edit), produced by the `bucket-comparison-document` task (`coga-os/tasks/bucket-comparison-document/`). The Doc is the editable original; this is a repo snapshot.

This doc sorts the agent tools I've tested into three buckets — agent replacements, overlays, and autonomous tools — and then answers the question: is Coga better?

## Bucket 1: Tools that try to replace the agent — Linear Agent, Dust, Cursor

This never worked well. Agents that these services created always gave the pre-feeling that they were doing a wonderful job at creating the steps to a task. As the agents moved through tasks, they still feigned being comprehensive at task completion.

My experience with every one of these "agent replacements" was that they labelled a project as done before it was actually done. Testing and failures that should have been resolved early in the project were instead pushed to the point when I thought the project was done. Without workflows that coached these proprietary agents on the correct way to structure a task, time and time again, failure management was injected into the situation at the worst possible time.

## Bucket 2: Overlays on top of the agent — Superset, Backlog, Conductor

These were essentially pretty wrappers for Claude Code. Services in this bucket structured the project in a much more efficient way than the agent-replacement bucket, but I came to the realization that the reason for proper project structure — addressing failures before a built project — had nothing to do with these overlays. The credit should be given to Claude Code.

## Bucket 3: Autonomous — Paperclip, OpenClaw

These tools provided the best testing result, but also with some variance. OpenClaw completed the project perfectly on the first try, but then I reset the state and turned off Claude's memory and chat-reference settings (which probably over-constrained it) and it was not able to complete the project the second time. In fact, the autonomous nature of the tool became a hindrance as it went through 35 failed cycles of trying to find proper Playwright selectors before I had to manually shut it off.

Paperclip provided the best project outcome. It tested the selectors at the right time, it handled issues in parallel — making for a much faster workable automation — and it flagged issues as blocking. In comparison, Paperclip needed less human intervention than any other tool while producing the best (and fastest) project outcome.

## Is Coga Better?

Coga isn't trying to replace agents. My testing showed that that was consistently a losing game. Claude Code was always better at structuring projects than the agent replacements. What Coga offers is opportunities for the human to identify better ways of completing a task, and guide the agent in that direction.

Every part of Coga's system is viewable and editable therefore it allows the human to fill gaps and remove the variance that I saw in bucket 3. When a human finds a better way to guide AI through a task, not only does it increase productivity for the human that found it — that value (a new skill, a new context block, a new workflow) can then be reused by other teammates.

I think Coga is better than other services because there's no black box. No unseen project structure that can lead to inconsistent outcomes when AI alone is asked to build the same project twice. Keeping the human in the loop — in every loop — gives the opportunity to attach workflows that largely remove variance.
