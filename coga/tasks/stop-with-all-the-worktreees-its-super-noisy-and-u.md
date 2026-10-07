---
title: stop with all the worktreees its super noisy and useless
status: canceled
owner: nicktoper
workflow: null
---

## Description

Obsolete: ordinary code-ticket work already runs in the invoking checkout,
without creating a linked worktree per ticket. No implementation work remains.

## Context

`dev/checkouts` (`docs/contexts/dev/checkouts/SKILL.md`) owns the current
checkout policy. Recurring background jobs may still create temporary control
worktrees through `recurring_runner._service_from_control_worktree`; the owner
explicitly confirmed that this exception is acceptable.

<!-- coga:blackboard -->

2026-10-06: Reviewed the current checkout policy and remaining worktree creation
in the recurring runner with the owner. The original concern is already
addressed, and the remaining recurring-job exception is accepted. Cancel as
superseded; no workflow or code changes are needed.
