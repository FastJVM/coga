---
name: bootstrap/dream/scan/knowledge-scan
description: Scan Dream's full corpus and return extract, stale, and gap findings for durable follow-up.
---

# Knowledge Scan

It is the single full-corpus read of the run: the subagent reads every ticket
body and blackboard, and every context, skill, and workflow file, and compares
them. Running it in the decide half, before Phase 5 deletes any done ticket,
means no evidence is lost.

Return only a classified findings list; raw ticket and blackboard contents stay
inside the subagent. Classify each finding as exactly one of:

- `extract` — a done ticket holds durable knowledge that belongs in a context
  or skill. Record the ticket slug and the context/skill area it touches.
- `stale` — an existing context or skill contradicts current repo reality.
  Name the file and state the contradiction.
- `gap` — a repeated pattern (recurring task knowledge, repeated process
  struggle, or an ad-hoc workflow sequence) with no context, skill, or
  workflow to carry it.

Write the findings to the Dream task's blackboard under `## Findings`: short
title, class, target file or ticket, one paragraph describing the change, and
draft content when a new file is proposed. Group the `extract` findings by the
context/skill area they touch — Phase 5 uses that grouping to batch coherent
PRs.
