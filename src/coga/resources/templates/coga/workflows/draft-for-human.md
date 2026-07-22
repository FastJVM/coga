---
name: draft-for-human
description: Agent drafts support material; human finishes, makes the final judgment calls, and owns the result.
steps:
  - name: agent-produces
    assignee: agent
  - name: human-owns-and-finishes
    assignee: human
  - name: report-to-coga
    assignee: agent
---

## agent-produces

Draft the deliverable as useful input for the human. Make the output easy to
inspect and edit, and call out assumptions or weak spots rather than hiding
them.

## human-owns-and-finishes

The human edits the agent output to the required quality bar, makes the final
judgment calls, and owns the result. The agent's draft is support material, not
the delivered work.

## report-to-coga

Record what was produced, what the human changed or decided, and where the final
artifact landed. If the result is compact, include it inline; if it is large,
record the path or link.
