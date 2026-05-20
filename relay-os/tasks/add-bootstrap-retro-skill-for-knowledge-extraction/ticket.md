---
title: Add bootstrap/retro skill for knowledge extraction on done tickets
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills:
- bootstrap/ticket
workflow: null
---

## Description

Proposed retitle: **Make Dream a per-project recurring maintenance
orchestrator**.

Dream should not live under `bootstrap/`. Bootstrap shims are stateless
launch helpers. Dream is ongoing project maintenance: a recurring,
per-project loop that inventories background work, runs independent
maintenance units when safe, and opens reviewable PRs for anything that
changes durable repo state.

Each repo owns its own Dream. In Relay's current model, a project is a
repo with its own `relay-os/`; there is no global cross-repo daemon.
Shared Dream tasks can ship as templates, but the active schedule,
enabled task list, and project-specific checks live in that repo.

## Desired shape

- `relay-os/recurring/weekly-dream.md` schedules the recurring run.
- `relay-os/workflows/dream/run.md` defines the workflow for one Dream run.
- `relay-os/skills/dream/orchestrate/SKILL.md` inventories work and
  dispatches independent tasks.
- `relay-os/skills/dream/tasks/*/SKILL.md` defines individual maintenance
  units with clear inputs, outputs, safety rules, and idempotency rules.
- Existing `bootstrap/dream` material moves or is replaced by the Dream
  workflow/skill shape above.

## Independent Dream tasks

### Relay core tasks

- **Validate drift.** Run `relay validate --json`, classify broken refs,
  stale locks, invalid state, and stuck active tickets. Output proposals
  or small fix PRs.
- **Retro done ticket.** Read one done ticket's `ticket.md`, `blackboard.md`,
  and `log.md`; extract durable knowledge into contexts, skills, or
  workflows; delete the task directory in the same PR. Git history is the
  archive after extraction.
- **Cleanup stale lock.** Clear only locks that validation proves stale
  under a documented age/running-process rule. This should be deterministic
  and narrow.
- **Context/skill staleness review.** Compare recent tickets and
  blackboards against existing contexts and skills. Output a proposal PR,
  not silent direct edits.
- **Workflow mismatch review.** Find tickets where selected workflow,
  contexts, owner, or assignee were wrong in practice. Output tuning
  proposals for bootstrap selection rules, workflow docs, or skills.
- **Recurring scaffolding check.** Run or verify `relay recurring check`
  and surface missed schedules or broken recurring templates.

### Dev project tasks

These are examples of per-project Dream tasks for a code repo:

- **Run unit tests.** Run the repo's configured unit test command and
  ticket or summarize failures with exact commands and failing tests.
- **Check CI drift.** Compare local test/docs instructions against CI
  workflows and flag mismatches.
- **Remove stale branches.** Identify merged local branches, stale remote
  tracking branches, and old topic branches. Propose deletion first unless
  the branch is proven merged and covered by a conservative rule.
- **Dependency drift.** Check dependency/lockfile freshness where the repo
  has a standard tool for it.
- **Spec/API drift.** Compare docs/specs against implemented CLI or API
  behavior and open small correction PRs.

## Orchestration rules

- Dream is an inventory and dispatcher, not a giant monolithic cleanup
  script.
- Each task must be independently runnable and idempotent.
- Each task must define whether it can edit directly, must open a PR, or
  should only write proposals to the Dream run blackboard.
- Destructive changes, especially deleting done task dirs or removing
  branches, require reviewable evidence. Prefer a PR or explicit proposal
  unless the rule is deterministic and low-risk.
- A Dream run should summarize what it did and what it deferred in Slack
  with one short line.

## First milestone

Implement the per-project Dream structure and migrate the current
`bootstrap/dream` skill into it. The first enabled worker should be
**retro done ticket**, because it gives Relay its cleanup story without
throwing away knowledge:

1. Find done tickets that have not had a retro PR.
2. Run one retro per ticket.
3. Extract useful knowledge into contexts/skills/workflows.
4. Delete that ticket directory in the same PR.
5. Post a short summary with the PR link.

## Child tickets

First wave, active:

- `move-dream-out-of-bootstrap` - move Dream into the project-owned
  recurring maintenance namespace.
- `define-dream-worker-contract` - define worker discovery, dispatch,
  safety, output, and idempotency rules.
- `implement-retro-done-ticket-worker` - implement one-ticket retro
  extraction and cleanup.
- `track-retro-completion-for-dream` - prevent duplicate retros for the
  same done ticket.
- `implement-validate-drift-dream-worker` - turn validation into an
  independent Dream worker.
- `add-dev-unit-test-dream-worker` - add a dev/code unit-test worker
  template.
- `add-dev-stale-branch-dream-worker` - add a dev/code stale-branch worker
  template.
- `update-dream-docs-and-current-direction` - make the new Dream model
  canonical in docs and contexts.

Second wave, draft:

- `plan-second-wave-dream-workers` - park dependency drift, CI drift,
  spec/API drift, workflow mismatch review, flaky-test retry, small
  maintenance PR queue, and template drift until the first-wave worker
  contract has proven itself.

## Open questions

- How does Dream track that a done ticket already had a retro PR: marker in
  the PR body, branch naming convention, a tiny metadata file, or git log?
- Should Dream run one worker per recurring task, or can one Dream run
  dispatch several independent workers before bumping?
- Which actions are allowed to commit directly, and which must always open
  a PR?
- Should project-specific Dream tasks be selected by context files,
  workflow config, or simply by files present under `skills/dream/tasks/`?

## Out of scope

- Auto-merging Dream PRs. Human review stays required.
- Cross-repo Dream orchestration. Each project/repo runs its own Dream.
- A daemon, service, queue, or database. Recurring tasks and git remain the
  operating model.
