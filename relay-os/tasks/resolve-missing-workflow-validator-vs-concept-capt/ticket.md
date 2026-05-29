---
title: Resolve missing-workflow validator vs concept-capture drafts
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Dream-2026-W21 Phase 1 (validate-drift) returned 12 `missing-workflow` warnings
on draft tickets, all of which are legitimate concept-capture design drafts:
they're an authored design state, not authoring drift. Examples include
`autotrigger-ticket-type`, `use-slack-as-a-sync-channel-for-tickets`,
`plan-second-wave-dream-workers`, `add-always-on-context-tier`,
`launch-tasks-in-container-or-vm`, etc.

`bootstrap/ticket` already says "if genuinely nothing fits, tell the human" —
so leaving a draft without a workflow is a supported state. But every
`relay validate` run since then re-flags these same drafts indefinitely, and
the validator's only output is "this draft can't be activated" — which the
author already knows because they intentionally left the workflow open.

Two ways to fix this; pick one:

1. **Add an exploration workflow.** Define a `concept/explore-then-spawn`
   workflow (or similar) with steps `explore → owner-review → spawn-or-close`.
   Drafts that want concept-capture set this workflow and the validator stops
   complaining.

2. **Relax the validator.** Have `relay validate` suppress the
   `missing-workflow` warning when a ticket explicitly opts into "exploration"
   mode (frontmatter flag, dedicated status, or by being older than N days
   with intentional human acknowledgement). The validator stops re-flagging
   what the author already chose.

Either is fine — the current state (validator warns on every legitimate
exploration ticket forever) is the gap.

Acceptance:

- Pick (1) or (2) and ship it.
- Re-run validate-drift on this repo and confirm legitimate exploration
  drafts no longer surface in `human-needed`.
- Update `relay/cli` and `bootstrap/ticket` to document the chosen path so
  future authors know how to mark exploration intent.

This finding came out of the Dream-2026-W21 knowledge scan as gap G3.

## Context

