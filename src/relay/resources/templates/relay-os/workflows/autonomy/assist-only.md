---
name: autonomy/assist-only
description: Triage routes a task here when a machine can assist but conventional output is not enough. The agent drafts the deliverable; the human finishes and owns the result.
steps:
  - name: agent-produces
    assignee: agent
  - name: human-owns-and-finishes
    assignee: human
  - name: report-to-relay
    assignee: agent
---

## agent-produces

Draft the deliverable as useful input for the human. The task is machine-feasible, so do not run the feasibility downgrade ladder from the automated tiers; the reason for this workflow is quality, taste, or differentiating judgment. Make the output easy to inspect and edit, and call out assumptions or weak spots rather than hiding them.

## human-owns-and-finishes

The human edits the agent output to the required quality bar, makes the final judgment calls, and owns the result. The agent's draft is support material, not the delivered work.

## report-to-relay

Record what was produced, what the human changed or decided, and where the final artifact landed. If the result is compact, include it inline; if it is large, record the path or link.
