---
name: admin/script
description: Single-step script-mode workflow. The step references a skill whose bundled script is executed directly by relay launch — no agent reasoning, no LLM token cost. Use for deterministic automations (scrapers, downloaders, API-driven reconciliation).
steps:
  - name: run
    skill: admin/xero-reconcile
---

## run

Executed by `relay launch` in script mode. The skill referenced above
is the default — override by editing the ticket frontmatter after
creation if a different script should run.

For each recurring automation that shares this pattern, create its
own skill under `skills/admin/<name>/` and either (a) clone this
workflow to a new file that references the new skill, or (b) keep
using this file and edit the ticket's frozen workflow snapshot
post-creation to point at the right skill.
