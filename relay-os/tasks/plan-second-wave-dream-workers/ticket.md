---
title: Plan second-wave Dream workers
status: draft
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts:
  - relay/architecture
  - relay/principles
  - relay/codebase
  - relay/current-direction
  - relay/project-stage
  - dev/code
---

## Description

Plan the second wave of Dream workers after the orchestration contract and first
workers exist.

Do not implement these before the first wave has proven the worker shape. This
ticket is a parking lot for useful maintenance tasks that should stay
independent instead of being folded into a giant Dream script.

## Candidate workers

- **Dependency drift.** Check dependency and lockfile freshness using the
  project-standard tool, then propose upgrades or tickets.
- **CI drift.** Compare local test/docs instructions against CI workflows.
- **Spec/API drift.** Compare docs/specs against implemented CLI or API
  behavior and open correction PRs.
- **Workflow mismatch review.** Find recurring cases where bootstrap selected
  the wrong workflow, contexts, owner, or assignee.
- **Known flaky test retry.** Rerun known flaky tests and refresh evidence.
- **Small maintenance PR queue.** Pick small cleanup PRs that are safe to do
  in background sessions.
- **Template drift.** Compare project `relay-os/` files against upstream
  managed templates and identify intended vs accidental divergence.

## Acceptance criteria

- [ ] First-wave Dream tickets have landed or produced enough evidence to
      finalize the worker contract.
- [ ] Each second-wave worker is split into its own ticket with clear safety
      and idempotency rules.
- [ ] Workers that touch external systems or destructive state require human
      review by default.
